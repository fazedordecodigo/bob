"""Gate de duplicação: jscpd pinado, só clones novos no diff, sempre aviso."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from bob_quality.adapters.jscpd import JscpdParseError, parse_jscpd_json
from bob_quality.config import Config
from bob_quality.core import clones_touching_diff
from bob_quality.exit_codes import CONFIG_OR_TOOL, PASSED
from bob_quality.models import Clone, GateResult
from bob_quality.npm_tools import installed_npm_version, node_missing_message, npm_prefix
from bob_quality.tools import ToolError

_FORMATS = {
    "python": ("python",),
    "typescript": ("typescript", "javascript"),
}
_ALWAYS_IGNORE = ("node_modules", "dist", ".git", ".bob")


def run_dry_gate(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
) -> tuple[GateResult, list[Clone], int, dict[str, str]]:
    if node_missing_message() is not None:
        return _skipped("Node ausente: instale Node.js para rodar o jscpd")
    try:
        prefix = npm_prefix()
        version = installed_npm_version(prefix, "jscpd")
    except ToolError:
        return _skipped(
            "dependências npm do plugin ausentes: rode npm ci na raiz "
            "(jscpd fixado no package.json)"
        )
    versions = {"jscpd": version}
    try:
        raw = _run_jscpd(cwd, config, prefix)
        found = parse_jscpd_json(raw)
    except ToolError as exc:
        return _skipped(str(exc), versions)
    except JscpdParseError as exc:
        return _skipped(str(exc), versions)
    located = []
    for clone in found:
        relative = _relativize(cwd, clone)
        if _inside_repo(cwd, relative):
            located.append(relative)
    fresh = clones_touching_diff(located, diff_lines)
    if not fresh:
        return GateResult("dry", "passed", None), [], PASSED, versions
    count = len(fresh)
    noun = "clone novo" if count == 1 else "clones novos"
    return GateResult("dry", "warn", f"{count} {noun} no diff"), fresh, PASSED, versions


def _skipped(
    reason: str,
    versions: dict[str, str] | None = None,
) -> tuple[GateResult, list[Clone], int, dict[str, str]]:
    return GateResult("dry", "not_run", reason), [], CONFIG_OR_TOOL, versions or {}


def _run_jscpd(cwd: Path, config: Config, prefix: Path) -> str:
    roots = [(cwd / path).resolve() for path in (config.include or ["src"])]
    missing = [str(path) for path in roots if not path.is_dir()]
    if missing:
        raise ToolError("jscpd: caminho de include ausente: " + ", ".join(missing))
    with tempfile.TemporaryDirectory(prefix="bob-jscpd-") as tmp:
        out = Path(tmp)
        args = [
            "npx",
            "--no-install",
            "--prefix",
            str(prefix),
            "jscpd",
            "--min-tokens",
            str(config.min_tokens),
            "--reporters",
            "json",
            "--output",
            str(out),
            "--absolute",
            "--silent",
            "--ignore",
            _ignore(config),
        ]
        formats = _formats(config.languages)
        if formats:
            args.extend(["--format", ",".join(formats)])
        args.extend(str(path) for path in roots)
        env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}
        bindir = prefix / "node_modules" / ".bin"
        env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            env=env,
        )
        report = out / "jscpd-report.json"
        if not report.is_file():
            detail = (completed.stderr or completed.stdout or "jscpd não gravou o JSON").strip()
            raise ToolError(detail)
        return report.read_text()


def _formats(languages: list[str]) -> list[str]:
    chosen: list[str] = []
    for language in languages:
        for name in _FORMATS.get(language, ()):
            if name not in chosen:
                chosen.append(name)
    return chosen


def _ignore(config: Config) -> str:
    names: list[str] = []
    for name in [*config.exclude, *_ALWAYS_IGNORE]:
        if name not in names:
            names.append(name)
    globs = [f"**/{name}/**" for name in names]
    return ",".join(globs)


def _relativize(cwd: Path, clone: Clone) -> Clone:
    return Clone(
        first_file=_relative(cwd, clone.first_file),
        first_start=clone.first_start,
        first_end=clone.first_end,
        second_file=_relative(cwd, clone.second_file),
        second_start=clone.second_start,
        second_end=clone.second_end,
        lines=clone.lines,
        tokens=clone.tokens,
        similarity=clone.similarity,
        kind=clone.kind,
    )


def _relative(cwd: Path, name: str) -> str:
    path = Path(name)
    if path.is_absolute():
        try:
            path = path.relative_to(cwd.resolve())
        except ValueError:
            return path.as_posix()
    text = path.as_posix()
    if text.startswith("./"):
        return text[2:]
    return text


def _inside_repo(cwd: Path, clone: Clone) -> bool:
    root = cwd.resolve()
    return _stays_inside(root, clone.first_file) and _stays_inside(root, clone.second_file)


def _stays_inside(root: Path, relative: str) -> bool:
    path = Path(relative)
    if path.is_absolute():
        return False
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return False
    return True
