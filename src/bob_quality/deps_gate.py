"""Gate de dependências: regras do repo + proibição de ciclo."""

from __future__ import annotations

import configparser
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from bob_quality.adapters.dependency_cruiser import parse_dependency_cruiser
from bob_quality.adapters.import_linter import broken_contract_name, parse_import_linter
from bob_quality.config import Config
from bob_quality.core import deps_verdict, unique_violations
from bob_quality.cycles import strongly_connected
from bob_quality.exit_codes import CONFIG_OR_TOOL, GATE_FAILED, PASSED
from bob_quality.messages import DEFAULT_LANGUAGE, Language, Text, msg, reason, t
from bob_quality.models import DepViolation, GateResult
from bob_quality.npm_tools import node_missing_message, npm_prefix
from bob_quality.tools import ToolError

_LINT_RUNNER = """\
import sys
from importlinter.cli import lint_imports
raise SystemExit(
    lint_imports(config_filename=sys.argv[1], no_cache=True, no_logo=True)
)
"""
_TS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
_NODE_MISSING = msg("deps.node_missing")
_CRUISER_MISSING = msg("tool.missing", tool="dependency-cruiser")
_GRAPH_RUNNER = """\
import json, os, sys, grimp
for entry in sys.argv[1].split(os.pathsep):
    if entry and entry not in sys.path:
        sys.path.insert(0, entry)
roots = json.loads(sys.argv[2])
graph = grimp.build_graph(*roots, cache_dir=None)
edges = {}
for module in graph.modules:
    imported = [
        name
        for name in graph.find_modules_directly_imported_by(module)
        if name in graph.modules
    ]
    edges[module] = imported
sys.stdout.write(json.dumps(edges))
"""


@dataclass(frozen=True)
class _Package:
    name: str
    source_root: Path


def run_deps_gate(
    cwd: Path,
    config: Config,
    changed_files: set[str] | None = None,
    lang: Language = DEFAULT_LANGUAGE,
) -> tuple[GateResult, int, dict[str, str], list[DepViolation]]:
    violations: list[DepViolation] = []
    versions: dict[str, str] = {}
    python_measured = "python" in config.languages
    try:
        components = _cycle_components(cwd, config) if python_measured else []
        if python_measured:
            violations.extend(_python_violations(cwd, config, versions, t(lang, "deps.cycle_rule")))
        skip = _collect_typescript(
            enabled="typescript" in config.languages,
            python_measured=python_measured,
            measure=lambda: _typescript_violations(cwd, config, versions),
            sink=violations,
        )
    except ToolError as exc:
        return GateResult("deps", "not_run", reason(exc)), CONFIG_OR_TOOL, versions, []
    except UnparsedBreak as exc:
        return GateResult("deps", "failed", exc.reason), GATE_FAILED, versions, []
    marked = _mark_diff(
        violations,
        changed_files or set(),
        components,
        _source_roots(cwd, config),
    )
    verdict, code = deps_verdict(marked)
    verdict, code = _note_typescript_skipped(verdict, code, skip)
    return verdict, code, versions, marked


def _collect_typescript(
    *,
    enabled: bool,
    python_measured: bool,
    measure: Callable[[], list[DepViolation]],
    sink: list[DepViolation],
) -> Text | None:
    """Mede o TypeScript. Sem Node, e com Python no repo, devolve o motivo do pulo."""
    if not enabled:
        return None
    try:
        sink.extend(measure())
    except NodeMissing as exc:
        if not python_measured:
            raise
        return reason(exc)
    return None


def _note_typescript_skipped(
    result: GateResult,
    code: int,
    skipped: Text | None,
) -> tuple[GateResult, int]:
    """Aviso no veredito. Exit 1 continua 1; o passe vira aviso e não sai 4."""
    if not skipped:
        return result, code
    note = msg("probe.typescript_skipped", reason=skipped)
    if result.status == "failed":
        detail = msg("probe.joined", first=result.reason, second=note) if result.reason else note
        return GateResult("deps", "failed", detail), code
    if code != PASSED:
        return result, code
    return GateResult("deps", "warn", note), code


def _mark_diff(
    violations: list[DepViolation],
    changed_files: set[str],
    components: list[frozenset[str]],
    source_roots: list[str],
) -> list[DepViolation]:
    by_module = _components_by_module(components)
    return [
        DepViolation(
            item.origin,
            item.destination,
            item.rule,
            _edge_in_diff(item, changed_files, by_module, source_roots),
        )
        for item in violations
    ]


def _components_by_module(components: list[frozenset[str]]) -> dict[str, frozenset[str]]:
    indexed: dict[str, frozenset[str]] = {}
    for component in components:
        for module in component:
            indexed[module] = component
    return indexed


def _edge_in_diff(
    item: DepViolation,
    changed_files: set[str],
    components: dict[str, frozenset[str]],
    source_roots: list[str],
) -> bool:
    if _endpoint_in_diff(item.origin, changed_files, source_roots) or _endpoint_in_diff(
        item.destination, changed_files, source_roots
    ):
        return True
    return _component_in_diff(item, changed_files, components, source_roots)


def _component_in_diff(
    item: DepViolation,
    changed_files: set[str],
    components: dict[str, frozenset[str]],
    source_roots: list[str],
) -> bool:
    component = components.get(item.origin)
    if component is None or item.destination not in component:
        return False
    return any(
        _endpoint_in_diff(module, changed_files, source_roots) for module in component
    )


def _cycle_components(cwd: Path, config: Config) -> list[frozenset[str]]:
    roots = _python_roots(cwd, config)
    return strongly_connected(_import_edges(cwd, config, roots))


def _import_edges(cwd: Path, config: Config, roots: list[str]) -> dict[str, list[str]]:
    if not roots:
        return {}
    env = _python_env(cwd, config)
    completed = subprocess.run(
        [sys.executable, "-c", _GRAPH_RUNNER, env.get("PYTHONPATH", ""), json.dumps(roots)],
        cwd=cwd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=env,
    )
    if completed.returncode != 0:
        detail = _short(completed.stderr or completed.stdout)
        raise ToolError(msg("deps.grimp_failed", detail=detail))
    try:
        return _parse_edges(completed.stdout)
    except ValueError as exc:
        raise ToolError(msg("deps.grimp_unreadable")) from exc


def _parse_edges(raw: str) -> dict[str, list[str]]:
    if not raw.strip():
        raise ValueError("grafo vazio")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("grafo ilegível") from exc
    if not isinstance(data, dict):
        raise ValueError("grafo ilegível")
    edges: dict[str, list[str]] = {}
    for origin, destinations in data.items():
        if not isinstance(destinations, list):
            raise ValueError("grafo ilegível")
        edges[str(origin)] = [str(item) for item in destinations]
    return edges


def _endpoint_in_diff(endpoint: str, changed_files: set[str], source_roots: list[str]) -> bool:
    path = endpoint.replace("\\", "/")
    if path in changed_files:
        return True
    if "/" in path:
        return False
    return any(candidate in changed_files for candidate in _module_paths(path, source_roots))


def _module_paths(module: str, source_roots: list[str]) -> list[str]:
    relative = module.replace(".", "/")
    names = (f"{relative}.py", f"{relative}/__init__.py")
    paths: list[str] = []
    for root in source_roots:
        prefix = root.strip("/")
        for name in names:
            paths.append(f"{prefix}/{name}" if prefix else name)
    return paths


def _source_roots(cwd: Path, config: Config) -> list[str]:
    found: list[str] = []
    for package in _discover_packages(cwd, config.include):
        relative = _relative_root(cwd, package.source_root)
        if relative not in found:
            found.append(relative)
    return found or [""]


def _relative_root(cwd: Path, source_root: Path) -> str:
    try:
        relative = source_root.resolve().relative_to(cwd.resolve()).as_posix()
    except ValueError:
        return source_root.as_posix()
    return "" if relative == "." else relative


def _python_violations(
    cwd: Path,
    config: Config,
    versions: dict[str, str],
    cycle_rule: str,
) -> list[DepViolation]:
    versions["import-linter"] = _import_linter_version()
    found: list[DepViolation] = []
    user = _resolve(cwd, config.python_deps_config)
    if user.is_file():
        found.extend(_lint(cwd, config, user))
    roots = _python_roots(cwd, config)
    if roots:
        found.extend(_lint_cycles(cwd, config, roots, cycle_rule))
    return unique_violations(found)


def _typescript_violations(
    cwd: Path,
    config: Config,
    versions: dict[str, str],
) -> list[DepViolation]:
    if node_missing_message() is not None:
        raise NodeMissing(_NODE_MISSING)
    prefix = npm_prefix()
    versions["dependency-cruiser"] = _cruiser_version(prefix)
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
        raise ToolError(msg("tool.missing", tool="import-linter"))
    return completed.stdout.strip()


def _lint(cwd: Path, config: Config, config_path: Path) -> list[DepViolation]:
    completed = _run_linter(cwd, config, config_path)
    return _import_linter_violations(completed)


def _lint_cycles(
    cwd: Path, config: Config, roots: list[str], cycle_rule: str
) -> list[DepViolation]:
    with tempfile.TemporaryDirectory(prefix="bob-import-linter-") as tmp:
        path = Path(tmp) / ".importlinter"
        path.write_text(_cycle_ini(roots, cycle_rule), encoding="utf-8")
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


class NodeMissing(ToolError):
    """Node não está disponível; o TypeScript deste gate não pode ser medido."""


class UnparsedBreak(Exception):
    """import-linter saiu quebrado e o texto não trouxe aresta origem → destino."""

    def __init__(self, reason: Text) -> None:
        self.reason = reason
        super().__init__(reason)


def _import_linter_violations(completed: subprocess.CompletedProcess[str]) -> list[DepViolation]:
    text = f"{completed.stdout}\n{completed.stderr}"
    if _linter_failed(text, completed.returncode):
        raise ToolError(_short(completed.stderr or completed.stdout))
    parsed = parse_import_linter(completed.stdout)
    if completed.returncode == 1 and not parsed:
        name = broken_contract_name(completed.stdout) or "import-linter"
        raise UnparsedBreak(msg("deps.contract_broken", name=name))
    return parsed


def _cruiser_version(prefix: Path) -> str:
    pkg = prefix / "node_modules" / "dependency-cruiser" / "package.json"
    if not pkg.is_file():
        raise ToolError(_CRUISER_MISSING)
    try:
        return str(json.loads(pkg.read_text())["version"])
    except (json.JSONDecodeError, KeyError) as exc:
        raise ToolError(_CRUISER_MISSING) from exc


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
    parser.read(path, encoding=sys.getdefaultencoding())
    if not parser.has_section("importlinter"):
        return []
    options = dict(parser.items("importlinter"))
    raw = options.get("root_packages", "")
    if not raw.strip():
        raw = options.get("root_package", "")
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


def _cycle_ini(roots: list[str], cycle_rule: str) -> str:
    packages = "\n".join(f"    {name}" for name in roots)
    return (
        "[importlinter]\n"
        "root_packages =\n"
        f"{packages}\n"
        "\n"
        "[importlinter:contract:bob-no-cycles]\n"
        f"name = {cycle_rule}\n"
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
    extensions = ", ".join(json.dumps(ext) for ext in _TS_EXTENSIONS)
    return f"""\
module.exports = {{
  forbidden: [
    {{ name: "bob-no-circular", severity: "error", from: {{}}, to: {{ circular: true }} }},
  ],
  options: {{
    doNotFollow: {{ path: "node_modules" }},
    enhancedResolveOptions: {{
      extensions: [{extensions}],
    }},
  }},
}};
"""


def _cruiser_wrapper(user: Path) -> str:
    quoted = json.dumps(str(user.resolve()))
    extensions = ", ".join(json.dumps(ext) for ext in _TS_EXTENSIONS)
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
for (const ext of [{extensions}]) extensions.add(ext);
resolve.extensions = Array.from(extensions);
options.enhancedResolveOptions = resolve;
if (!options.doNotFollow) options.doNotFollow = {{ path: "node_modules" }};
module.exports = {{ ...user, forbidden, options }};
"""


def _cruise_patterns(cwd: Path, include: list[str]) -> list[str]:
    patterns: list[str] = []
    for raw in include:
        if (cwd / raw).is_dir():
            patterns.extend(f"{raw}/**/*{ext}" for ext in _TS_EXTENSIONS)
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


def _short(text: str) -> Text:
    compact = " ".join(text.split())
    if not compact:
        return msg("deps.tool_failed")
    return compact[:300]
