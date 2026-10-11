"""Gate de dependências: regras do repo + proibição de ciclo."""

from __future__ import annotations

import configparser
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from bob_quality.adapters.dependency_cruiser import parse_dependency_cruiser
from bob_quality.adapters.import_linter import parse_import_linter
from bob_quality.config import Config
from bob_quality.core import deps_verdict, unique_violations
from bob_quality.exit_codes import CONFIG_OR_TOOL
from bob_quality.models import DepViolation, GateResult
from bob_quality.npm_tools import installed_npm_version, node_missing_message, npm_prefix
from bob_quality.tools import ToolError

_LINT_RUNNER = """\
import sys
from importlinter.cli import lint_imports
raise SystemExit(
    lint_imports(config_filename=sys.argv[1], no_cache=True, no_logo=True)
)
"""
_TS_EXTENSIONS = ("ts", "tsx", "js", "jsx", "mjs", "cjs")
_CYCLE_RULE = "Proibido ciclo de dependência"


@dataclass(frozen=True)
class _Package:
    name: str
    source_root: Path


def run_deps_gate(
    cwd: Path,
    config: Config,
) -> tuple[GateResult, int, dict[str, str], list[DepViolation]]:
    violations: list[DepViolation] = []
    versions: dict[str, str] = {}
    try:
        if "python" in config.languages:
            violations.extend(_python_violations(cwd, config, versions))
        if "typescript" in config.languages:
            violations.extend(_typescript_violations(cwd, config, versions))
    except ToolError as exc:
        return GateResult("deps", "not_run", str(exc)), CONFIG_OR_TOOL, versions, []
    verdict, code = deps_verdict(violations)
    return verdict, code, versions, violations


def _python_violations(
    cwd: Path,
    config: Config,
    versions: dict[str, str],
) -> list[DepViolation]:
    versions["import-linter"] = _import_linter_version()
    found: list[DepViolation] = []
    user = _resolve(cwd, config.python_deps_config)
    if user.is_file():
        found.extend(_lint(cwd, config, user))
    roots = _python_roots(cwd, config)
    if roots:
        found.extend(_lint_cycles(cwd, config, roots))
    return unique_violations(found)


def _typescript_violations(
    cwd: Path,
    config: Config,
    versions: dict[str, str],
) -> list[DepViolation]:
    missing = node_missing_message()
    if missing:
        raise ToolError(missing)
    prefix = npm_prefix()
    versions["dependency-cruiser"] = installed_npm_version(prefix, "dependency-cruiser")
    patterns = _cruise_patterns(cwd, config.include)
    if not patterns:
        return []
    user = _resolve(cwd, config.typescript_deps_config)
    with tempfile.TemporaryDirectory(prefix="bob-deps-") as tmp:
        config_path = Path(tmp) / "deps.cjs"
        config_path.write_text(_cruiser_config(user), encoding="utf-8")
        return _cruise(cwd, config, prefix, config_path, patterns)


def _import_linter_version() -> str:
    completed = subprocess.run(
        [sys.executable, "-c", "import importlinter; print(importlinter.__version__)"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    if completed.returncode != 0:
        raise ToolError("ferramenta ausente: import-linter")
    return completed.stdout.strip()


def _lint(cwd: Path, config: Config, config_path: Path) -> list[DepViolation]:
    completed = _run_linter(cwd, config, config_path)
    return _import_linter_violations(completed)


def _lint_cycles(cwd: Path, config: Config, roots: list[str]) -> list[DepViolation]:
    with tempfile.TemporaryDirectory(prefix="bob-import-linter-") as tmp:
        path = Path(tmp) / ".importlinter"
        path.write_text(_cycle_ini(roots), encoding="utf-8")
        return _lint(cwd, config, path)


def _run_linter(cwd: Path, config: Config, config_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", _LINT_RUNNER, str(config_path)],
        cwd=cwd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=_python_env(cwd, config),
    )


def _import_linter_violations(completed: subprocess.CompletedProcess[str]) -> list[DepViolation]:
    text = f"{completed.stdout}\n{completed.stderr}"
    if _linter_failed(text, completed.returncode):
        raise ToolError(_short(completed.stderr or completed.stdout))
    return parse_import_linter(completed.stdout)


def _linter_failed(text: str, code: int) -> bool:
    if "Traceback (most recent call last)" in text or "not configured correctly" in text:
        return True
    if "Could not import" in text and "->" not in text:
        return True
    return code not in {0, 1}


def _python_roots(cwd: Path, config: Config) -> list[str]:
    user = _resolve(cwd, config.python_deps_config)
    if user.is_file():
        declared = _ini_roots(user)
        if declared:
            return declared
    return [package.name for package in _discover_packages(cwd, config.include)]


def _ini_roots(path: Path) -> list[str]:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(path, encoding="utf-8")
    if not parser.has_section("importlinter"):
        return []
    raw = parser.get("importlinter", "root_packages", fallback="")
    if not raw.strip():
        raw = parser.get("importlinter", "root_package", fallback="")
    return [part.strip() for part in raw.replace(",", "\n").splitlines() if part.strip()]


def _discover_packages(cwd: Path, include: list[str]) -> list[_Package]:
    found: list[_Package] = []
    for raw in include:
        root = cwd / raw
        if root.is_dir():
            found.extend(_packages_under(root))
    return found


def _packages_under(root: Path) -> list[_Package]:
    if (root / "__init__.py").is_file():
        return [_Package(root.name, root.parent)]
    return [
        _Package(child.name, root)
        for child in sorted(root.iterdir())
        if child.is_dir() and (child / "__init__.py").is_file()
    ]


def _cycle_ini(roots: list[str]) -> str:
    packages = "\n".join(f"    {name}" for name in roots)
    return (
        "[importlinter]\n"
        "root_packages =\n"
        f"{packages}\n"
        "\n"
        "[importlinter:contract:bob-no-cycles]\n"
        f"name = {_CYCLE_RULE}\n"
        "type = acyclic_siblings\n"
        "ancestors =\n"
        f"{packages}\n"
    )


def _python_env(cwd: Path, config: Config) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}
    roots = [str(cwd.resolve())]
    packages = _discover_packages(cwd, config.include)
    roots.extend(str(package.source_root.resolve()) for package in packages)
    previous = env.get("PYTHONPATH", "")
    if previous:
        roots.append(previous)
    env["PYTHONPATH"] = os.pathsep.join(roots)
    env["NO_COLOR"] = "1"
    return env


def _cruise(
    cwd: Path,
    config: Config,
    prefix: Path,
    config_path: Path,
    patterns: list[str],
) -> list[DepViolation]:
    args = [
        "npx",
        "--prefix",
        str(prefix),
        "--no-install",
        "dependency-cruiser",
        "--config",
        str(config_path),
        "--output-type",
        "json",
        "--no-progress",
    ]
    exclude = _exclude_pattern(config.exclude)
    if exclude:
        args.extend(["--exclude", exclude])
    args.append("--")
    args.extend(patterns)
    completed = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=_node_env(prefix),
    )
    return _cruise_violations(completed)


def _cruise_violations(completed: subprocess.CompletedProcess[str]) -> list[DepViolation]:
    try:
        return parse_dependency_cruiser(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ToolError(_short(completed.stderr or completed.stdout)) from exc


def _cruiser_config(user: Path) -> str:
    if user.is_file():
        return _cruiser_wrapper(user)
    return _cruiser_base()


def _cruiser_base() -> str:
    return """\
module.exports = {
  forbidden: [
    { name: "bob-no-circular", severity: "error", from: {}, to: { circular: true } },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    enhancedResolveOptions: {
      extensions: [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"],
    },
  },
};
"""


def _cruiser_wrapper(user: Path) -> str:
    quoted = json.dumps(str(user.resolve()))
    return f"""\
const user = require({quoted});
const cycle = {{
  name: "bob-no-circular",
  severity: "error",
  from: {{}},
  to: {{ circular: true }},
}};
const forbidden = Array.isArray(user.forbidden) ? user.forbidden.concat([cycle]) : [cycle];
const options = {{ ...(user.options || {{}}) }};
const resolve = {{ ...(options.enhancedResolveOptions || {{}}) }};
const extensions = new Set(resolve.extensions || []);
for (const ext of [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]) extensions.add(ext);
resolve.extensions = Array.from(extensions);
options.enhancedResolveOptions = resolve;
if (!options.doNotFollow) options.doNotFollow = {{ path: "node_modules" }};
module.exports = {{ ...user, forbidden, options }};
"""


def _cruise_patterns(cwd: Path, include: list[str]) -> list[str]:
    patterns: list[str] = []
    for raw in include:
        if (cwd / raw).is_dir():
            patterns.extend(f"{raw}/**/*.{ext}" for ext in _TS_EXTENSIONS)
    return patterns


def _exclude_pattern(exclude: list[str]) -> str:
    parts = [re.escape(name.strip("/")) for name in exclude if name.strip("/")]
    if not parts:
        return ""
    return "|".join(f"(^|/){part}(/|$)" for part in parts)


def _node_env(prefix: Path) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}
    bindir = prefix / "node_modules" / ".bin"
    env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    return env


def _resolve(cwd: Path, configured: str) -> Path:
    path = Path(configured)
    if path.is_absolute():
        return path
    return cwd / path


def _short(text: str) -> str:
    compact = " ".join(text.split())
    if not compact:
        return "ferramenta de dependência falhou"
    return compact[:300]
