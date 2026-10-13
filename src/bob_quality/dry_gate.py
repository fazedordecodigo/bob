"""Gate de duplicação: jscpd pinado, só clones novos no diff, sempre aviso."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from bob_quality.adapters.jscpd import JscpdParseError, parse_jscpd_json
from bob_quality.config import Config
from bob_quality.diff import function_is_changed
from bob_quality.exit_codes import PASSED
from bob_quality.messages import Text, msg, reason
from bob_quality.models import Clone, GateResult
from bob_quality.npm_tools import installed_npm_version, node_missing_message, npm_prefix
from bob_quality.tools import ToolError, spawn_clean

_FORMATS = {
    "python": ("python",),
    "typescript": ("typescript", "javascript"),
}
_ALWAYS_IGNORE = ("node_modules", "dist", ".git", ".bob")
_Dry = tuple[GateResult, list[Clone], int, dict[str, str]]


def run_dry_gate(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
) -> _Dry:
    versions, skipped = _tooling()
    if skipped is not None:
        return skipped
    try:
        found = parse_jscpd_json(_run_jscpd(cwd, config, npm_prefix()))
    except (ToolError, JscpdParseError) as exc:
        return _skipped(reason(exc), versions)
    return _verdict(_new_clones(cwd, found, diff_lines), versions)


def _tooling() -> tuple[dict[str, str], _Dry | None]:
    if node_missing_message() is not None:
        return {}, _skipped(msg("dry.node_missing"))
    try:
        version = installed_npm_version(npm_prefix(), "jscpd")
    except ToolError:
        return {}, _skipped(msg("dry.deps_missing"))
    return {"jscpd": version}, None


def _verdict(fresh: list[Clone], versions: dict[str, str]) -> _Dry:
    if not fresh:
        return GateResult("dry", "passed", None), [], PASSED, versions
    count = len(fresh)
    key = "dry.clone" if count == 1 else "dry.clones"
    return GateResult("dry", "warn", msg(key, count=count)), fresh, PASSED, versions


def _skipped(why: Text, versions: dict[str, str] | None = None) -> _Dry:
    return GateResult("dry", "not_run", why), [], PASSED, versions or {}


def _new_clones(
    cwd: Path,
    found: list[Clone],
    diff_lines: dict[str, set[int]],
) -> list[Clone]:
    fresh: list[Clone] = []
    for clone in found:
        relative = _relativize(cwd, clone)
        if _inside_repo(cwd, relative) and _touches(relative, diff_lines):
            fresh.append(relative)
    return fresh


def _touches(clone: Clone, diff_lines: dict[str, set[int]]) -> bool:
    sides = (
        (clone.first_file, clone.first_start, clone.first_end),
        (clone.second_file, clone.second_start, clone.second_end),
    )
    return any(
        function_is_changed(file, start, end, diff_lines) for file, start, end in sides
    )


def _run_jscpd(cwd: Path, config: Config, prefix: Path) -> str:
    roots = _roots(cwd, config)
    with tempfile.TemporaryDirectory(prefix="bob-jscpd-") as tmp:
        out = Path(tmp)
        completed = spawn_clean(cwd, _args(config, prefix, roots, out), prefix)
        return _read_report(out, completed)


def _roots(cwd: Path, config: Config) -> list[Path]:
    roots = [(cwd / path).resolve() for path in (config.include or ["src"])]
    missing = [str(path) for path in roots if not path.is_dir()]
    if missing:
        raise ToolError(msg("dry.include_missing", paths=", ".join(missing)))
    return roots


def _args(config: Config, prefix: Path, roots: list[Path], out: Path) -> list[str]:
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
    return args


def _read_report(out: Path, completed: subprocess.CompletedProcess[str]) -> str:
    report = out / "jscpd-report.json"
    if report.is_file():
        return report.read_text()
    raw = completed.stderr or completed.stdout
    raise ToolError(raw.strip() if raw else msg("dry.no_report"))


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
    return ",".join(f"**/{name}/**" for name in names)


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
    if not path.is_absolute():
        return _strip_dot(path.as_posix())
    try:
        return path.relative_to(cwd.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _strip_dot(text: str) -> str:
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
    try:
        (root / path).resolve().relative_to(root)
    except ValueError:
        return False
    return True
