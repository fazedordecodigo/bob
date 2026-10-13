from __future__ import annotations

import importlib.metadata
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

from bob_quality.adapters.knip import KnipParseError, typescript_symbols
from bob_quality.adapters.vulture import VultureParseError, python_symbols
from bob_quality.config import Config
from bob_quality.diff import line_is_changed
from bob_quality.messages import Text, msg, reason
from bob_quality.models import (
    DeadSection,
    DeadSymbol,
    GateResult,
    LedgerRow,
    PythonDead,
    TypeScriptDead,
)
from bob_quality.npm_tools import installed_npm_version, node_missing_message, npm_prefix
from bob_quality.tools import ToolError
from bob_quality.waivers import Waiver, load_waivers

DeadStatus = Literal["passed", "warn", "not_run"]


@dataclass(frozen=True)
class MeasuredPython:
    symbols: tuple[PythonDead, ...]
    version: str


@dataclass(frozen=True)
class MeasuredTypeScript:
    symbols: tuple[TypeScriptDead, ...]
    version: str


@dataclass(frozen=True)
class Dark:
    reason: Text


@dataclass(frozen=True)
class Quiet:
    pass


@dataclass(frozen=True)
class WarningOnly:
    status: DeadStatus
    reason: Text | None
    section: DeadSection
    versions: tuple[tuple[str, str], ...]

    def as_gate(self) -> GateResult:
        return GateResult("dead_code", self.status, self.reason)


def definition_is_new(symbol: DeadSymbol, changed: Mapping[str, Set[int]]) -> bool:
    return line_is_changed(symbol.file, symbol.line, changed)


def in_measurement(symbol: DeadSymbol, config: Config) -> bool:
    path = PurePosixPath(symbol.file)
    if path.is_absolute() or ".." in path.parts:
        return False
    if any(part in config.exclude for part in path.parts):
        return False
    return any(
        path == PurePosixPath(root) or PurePosixPath(root) in path.parents
        for root in config.include
    )


def waiver_id(symbol: DeadSymbol) -> str:
    return f"dead:{symbol.file}:{symbol.line}:{symbol.name}"


def settle(
    python: MeasuredPython | Dark | Quiet,
    typescript: MeasuredTypeScript | Dark | Quiet,
    changed: Mapping[str, Set[int]],
    config: Config,
    waivers: Sequence[Waiver],
) -> WarningOnly:
    dark = _dark_reasons(python, typescript)
    if not _any_measured(python, typescript):
        why = _joined(dark) if dark else msg("dead.no_language")
        return WarningOnly("not_run", why, DeadSection(), ())
    rows = _ledger(python, typescript, changed, config, waivers)
    versions = _versions(python, typescript)
    unwaived = sum(row.waiver is None for row in rows)
    if unwaived:
        key = "dead.one" if unwaived == 1 else "dead.many"
        return WarningOnly(
            "warn",
            _joined((msg(key, count=unwaived), *dark)),
            DeadSection(rows),
            versions,
        )
    return WarningOnly("passed", _joined(dark) if dark else None, DeadSection(rows), versions)


def vulture_command(config: Config, include: Sequence[str]) -> list[str]:
    command = [sys.executable, "-m", "vulture", *include]
    if config.dead_code_min_confidence is not None:
        command.extend(["--min-confidence", str(config.dead_code_min_confidence)])
    return command


def knip_command(prefix: Path) -> list[str]:
    return [
        "npx",
        "--no-install",
        "--prefix",
        str(prefix),
        "knip",
        "--reporter",
        "json",
        "--no-progress",
    ]


def run_dead_code_gate(
    cwd: Path,
    config: Config,
    changed: Mapping[str, Set[int]],
) -> WarningOnly:
    return settle(
        read_vulture(cwd, config),
        read_knip(cwd, config),
        changed,
        config,
        load_waivers(cwd),
    )


def read_vulture(cwd: Path, config: Config) -> MeasuredPython | Dark | Quiet:
    if "python" not in config.languages:
        return Quiet()
    blocked = _vulture_blocked(cwd, config)
    if blocked is not None:
        return blocked
    try:
        completed = _spawn(cwd, vulture_command(config, config.include))
    except OSError:
        return Dark(msg("tool.missing", tool="vulture"))
    return _vulture_half(completed, cwd)


def read_knip(cwd: Path, config: Config) -> MeasuredTypeScript | Dark | Quiet:
    if "typescript" not in config.languages:
        return Quiet()
    prefix = _knip_prefix()
    if isinstance(prefix, Dark):
        return prefix
    try:
        completed = _spawn(cwd, knip_command(prefix), prefix)
    except OSError:
        return Dark(msg("tool.missing", tool="knip"))
    return _knip_half(completed, cwd, prefix)


def _vulture_blocked(cwd: Path, config: Config) -> Dark | None:
    if _vulture_version() is None:
        return Dark(msg("tool.missing", tool="vulture"))
    missing = [path for path in config.include if not (cwd / path).is_dir()]
    if missing:
        return Dark(msg("dead.include_missing", tool="vulture", paths=", ".join(missing)))
    return None


def _vulture_half(
    completed: subprocess.CompletedProcess[str], cwd: Path
) -> MeasuredPython | Dark:
    version = _vulture_version()
    if version is None:
        return Dark(msg("tool.missing", tool="vulture"))
    if completed.returncode == 0 and completed.stdout.strip() == "":
        return MeasuredPython((), version)
    if completed.returncode != 3:
        return Dark(msg("dead.unreadable", tool="vulture"))
    return _parsed_vulture(completed.stdout, cwd, version)


def _parsed_vulture(stdout: str, cwd: Path, version: str) -> MeasuredPython | Dark:
    try:
        symbols = python_symbols(stdout, cwd)
    except VultureParseError as exc:
        return Dark(reason(exc))
    return MeasuredPython(symbols, version)


def _knip_prefix() -> Path | Dark:
    if node_missing_message() is not None:
        return Dark(msg("dead.node_missing"))
    try:
        prefix = npm_prefix()
    except ToolError as exc:
        return Dark(reason(exc))
    if not (prefix / "node_modules" / "knip" / "package.json").is_file():
        return Dark(msg("tool.missing", tool="knip"))
    return prefix


def _knip_half(
    completed: subprocess.CompletedProcess[str], cwd: Path, prefix: Path
) -> MeasuredTypeScript | Dark:
    if completed.returncode not in {0, 1} or completed.stdout.strip() == "":
        return Dark(msg("dead.unreadable", tool="knip"))
    parsed = _parsed_knip(completed.stdout, cwd)
    if isinstance(parsed, Dark):
        return parsed
    try:
        version = installed_npm_version(prefix, "knip")
    except ToolError as exc:
        return Dark(reason(exc))
    return MeasuredTypeScript(parsed, version)


def _parsed_knip(stdout: str, cwd: Path) -> tuple[TypeScriptDead, ...] | Dark:
    try:
        return typescript_symbols(stdout, cwd)
    except KnipParseError as exc:
        return Dark(reason(exc))


def _vulture_version() -> str | None:
    try:
        return importlib.metadata.version("vulture")
    except importlib.metadata.PackageNotFoundError:
        return None


def _spawn(
    cwd: Path, args: Sequence[str], prefix: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}
    if prefix is not None:
        bindir = prefix / "node_modules" / ".bin"
        env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=env,
    )


def _any_measured(
    python: MeasuredPython | Dark | Quiet,
    typescript: MeasuredTypeScript | Dark | Quiet,
) -> bool:
    return isinstance(python, MeasuredPython) or isinstance(typescript, MeasuredTypeScript)


def _dark_reasons(
    python: MeasuredPython | Dark | Quiet,
    typescript: MeasuredTypeScript | Dark | Quiet,
) -> tuple[Text, ...]:
    reasons: list[Text] = []
    if isinstance(python, Dark):
        reasons.append(python.reason)
    if isinstance(typescript, Dark):
        reasons.append(typescript.reason)
    return tuple(reasons)


def _versions(
    python: MeasuredPython | Dark | Quiet,
    typescript: MeasuredTypeScript | Dark | Quiet,
) -> tuple[tuple[str, str], ...]:
    versions: list[tuple[str, str]] = []
    if isinstance(python, MeasuredPython):
        versions.append(("vulture", python.version))
    if isinstance(typescript, MeasuredTypeScript):
        versions.append(("knip", typescript.version))
    return tuple(versions)


def _joined(parts: Sequence[Text]) -> Text:
    joined = parts[0]
    for part in parts[1:]:
        joined = msg("probe.joined", first=joined, second=part)
    return joined


def _ledger(
    python: MeasuredPython | Dark | Quiet,
    typescript: MeasuredTypeScript | Dark | Quiet,
    changed: Mapping[str, Set[int]],
    config: Config,
    waivers: Sequence[Waiver],
) -> tuple[LedgerRow, ...]:
    rows = [
        LedgerRow(symbol, _matched_waiver(symbol, waivers))
        for symbol in _symbols(python, typescript)
        if in_measurement(symbol, config) and definition_is_new(symbol, changed)
    ]
    return tuple(sorted(rows, key=_row_key))


def _symbols(
    python: MeasuredPython | Dark | Quiet,
    typescript: MeasuredTypeScript | Dark | Quiet,
) -> tuple[DeadSymbol, ...]:
    found: list[DeadSymbol] = []
    if isinstance(python, MeasuredPython):
        found.extend(python.symbols)
    if isinstance(typescript, MeasuredTypeScript):
        found.extend(typescript.symbols)
    return tuple(found)


def _matched_waiver(symbol: DeadSymbol, waivers: Sequence[Waiver]) -> str | None:
    wanted = waiver_id(symbol)
    for waiver in waivers:
        if waiver.id == wanted:
            return wanted
    return None


def _row_key(row: LedgerRow) -> tuple[str, int, str, str, str]:
    symbol = row.symbol
    return (symbol.file, symbol.line, symbol.name, symbol.kind, _language(symbol))


def _language(symbol: DeadSymbol) -> str:
    if isinstance(symbol, PythonDead):
        return "python"
    if isinstance(symbol, TypeScriptDead):
        return "typescript"
    raise TypeError(type(symbol).__name__)
