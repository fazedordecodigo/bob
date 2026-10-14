from __future__ import annotations

import importlib.metadata
import json
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from bob_quality.config import Config, SourceLanguage
from bob_quality.core import below_floor
from bob_quality.exit_codes import BASELINE_BROKEN, CONFIG_OR_TOOL, GATE_FAILED, PASSED
from bob_quality.messages import Text, msg, reason
from bob_quality.models import DiffCoverage, DiffLine, GateResult, LanguageDiff
from bob_quality.suite_memo import (
    HoldBroken,
    HoldUnavailable,
    PythonHold,
    SuiteMemo,
    TypescriptHold,
)
from bob_quality.tools import ToolError
from bob_quality.waivers import Waiver, WaiverError, load_waivers, with_prefix

DIFF_COVER_MODULE = "diff_cover.diff_cover_tool"
_COVERAGE_PREFIX = "coverage:"
MissKind = Literal["baseline", "tool"]


def diff_cover_version() -> str | None:
    try:
        return importlib.metadata.version("diff-cover")
    except importlib.metadata.PackageNotFoundError:
        return None


@dataclass(frozen=True)
class LanguageMiss:
    language: SourceLanguage
    kind: MissKind
    reason: Text


LanguageSlot = LanguageDiff | LanguageMiss


@dataclass(frozen=True)
class FileLines:
    covered: frozenset[int]
    uncovered: frozenset[int]


@dataclass(frozen=True)
class DiffPercent:
    value: float


@dataclass(frozen=True)
class DroppedFile:
    file: str


@dataclass(frozen=True)
class DroppedLine:
    file: str
    line: int


Drop = DroppedFile | DroppedLine


@dataclass(frozen=True)
class CoverageOutcome:
    result: GateResult
    exit_code: int
    versions: dict[str, str]
    diff_coverage: DiffCoverage | None


def run_coverage_gate(
    cwd: Path,
    config: Config,
    base: str,
    coverage_file: Path | None,
    memo: SuiteMemo,
) -> CoverageOutcome:
    version = diff_cover_version()
    if version is None:
        return _stopped(msg("tool.missing", tool="diff-cover"), CONFIG_OR_TOOL, {})
    try:
        waivers = load_waivers(cwd)
    except WaiverError as exc:
        return _stopped(reason(exc), CONFIG_OR_TOOL, {})
    versions = {"diff-cover": version}
    drops = _coverage_drops(waivers)
    try:
        with tempfile.TemporaryDirectory(prefix="bob-diff-cover-") as tmp:
            patch = Path(tmp) / "patch.diff"
            _write_patch(cwd, base, patch)
            slots = _collect(cwd, config, coverage_file, memo, patch, drops)
    except ToolError as exc:
        return _stopped(reason(exc), CONFIG_OR_TOOL, versions)
    judged = _judge(slots, config.coverage_min_percent)
    return replace(judged, versions=versions)


def _stopped(why: Text, code: int, versions: dict[str, str]) -> CoverageOutcome:
    return CoverageOutcome(GateResult("coverage", "not_run", why), code, versions, None)


def _collect(
    cwd: Path,
    config: Config,
    coverage_file: Path | None,
    memo: SuiteMemo,
    patch: Path,
    drops: Sequence[Drop],
) -> tuple[LanguageSlot, ...]:
    slots: list[LanguageSlot] = []
    for language in config.languages:
        slot = _slot(language, cwd, config, coverage_file, memo, patch, drops)
        slots.append(slot)
        if isinstance(slot, LanguageMiss) and slot.kind == "baseline":
            break
    return tuple(slots)


def _slot(
    language: SourceLanguage,
    cwd: Path,
    config: Config,
    coverage_file: Path | None,
    memo: SuiteMemo,
    patch: Path,
    drops: Sequence[Drop],
) -> LanguageSlot:
    if language == "python":
        return _python_slot(cwd, config, coverage_file, memo, patch, drops)
    return _typescript_slot(cwd, config, memo, patch, drops)


def _python_slot(
    cwd: Path,
    config: Config,
    coverage_file: Path | None,
    memo: SuiteMemo,
    patch: Path,
    drops: Sequence[Drop],
) -> LanguageSlot:
    hold = memo.python_hold(cwd, config.include, coverage_file)
    if not isinstance(hold, PythonHold):
        return _hold_miss("python", hold)
    try:
        xml = memo.python_xml(cwd, config.include, coverage_file)
    except ToolError as exc:
        return LanguageMiss("python", "tool", reason(exc))
    artifact = _written_text(patch.parent / "coverage.xml", xml)
    if artifact is None:
        return LanguageMiss("python", "tool", msg("coverage.no_xml"))
    return _measured("python", cwd, artifact, patch, drops)


def _typescript_slot(
    cwd: Path,
    config: Config,
    memo: SuiteMemo,
    patch: Path,
    drops: Sequence[Drop],
) -> LanguageSlot:
    hold = memo.typescript_hold(cwd, config.include, config.exclude)
    if not isinstance(hold, TypescriptHold):
        return _hold_miss("typescript", hold)
    artifact = hold.reports / "lcov.info"
    if not artifact.is_file() or artifact.stat().st_size == 0:
        return LanguageMiss("typescript", "tool", msg("coverage.no_lcov"))
    return _measured("typescript", cwd, artifact, patch, drops)


def _hold_miss(language: SourceLanguage, hold: object) -> LanguageMiss:
    if isinstance(hold, HoldBroken):
        return LanguageMiss(language, "baseline", msg("probe.baseline_failed"))
    if isinstance(hold, HoldUnavailable):
        return LanguageMiss(language, "tool", hold.reason)
    return LanguageMiss(language, "tool", msg("coverage.unreadable"))


def _written_text(dest: Path, text: str) -> Path | None:
    if not text.strip():
        return None
    dest.write_text(text)
    return dest


def _measured(
    language: SourceLanguage,
    cwd: Path,
    artifact: Path,
    patch: Path,
    drops: Sequence[Drop],
) -> LanguageSlot:
    try:
        files = _run_diff_cover(cwd, artifact, patch)
    except ToolError as exc:
        return LanguageMiss(language, "tool", reason(exc))
    percent = _adjusted_percent(files, drops)
    return LanguageDiff(language, percent.value, _remaining_uncovered(files, drops))


def _judge(slots: Sequence[LanguageSlot], floor: float) -> CoverageOutcome:
    baseline = _first_baseline(slots)
    if baseline is not None:
        return _baseline_outcome(baseline)
    measured = tuple(slot for slot in slots if isinstance(slot, LanguageDiff))
    misses = tuple(slot for slot in slots if isinstance(slot, LanguageMiss))
    if not measured:
        return _unmeasured(misses)
    return _from_percents(measured, misses, floor)


def _first_baseline(slots: Sequence[LanguageSlot]) -> LanguageMiss | None:
    for slot in slots:
        if isinstance(slot, LanguageMiss) and slot.kind == "baseline":
            return slot
    return None


def _baseline_outcome(miss: LanguageMiss) -> CoverageOutcome:
    return CoverageOutcome(
        GateResult("coverage", "not_run", miss.reason),
        BASELINE_BROKEN,
        {},
        None,
    )


def _unmeasured(misses: Sequence[LanguageMiss]) -> CoverageOutcome:
    return CoverageOutcome(
        GateResult("coverage", "not_run", _miss_reason(misses)),
        CONFIG_OR_TOOL,
        {},
        None,
    )


def _from_percents(
    measured: Sequence[LanguageDiff],
    misses: Sequence[LanguageMiss],
    floor: float,
) -> CoverageOutcome:
    failing = tuple(item for item in measured if below_floor(item.percent, floor))
    skip = _skip_reason(misses)
    if failing:
        return _failed(failing, floor, skip, measured)
    return CoverageOutcome(
        GateResult("coverage", "passed", skip),
        PASSED,
        {},
        DiffCoverage(measured),
    )


def _failed(
    failing: Sequence[LanguageDiff],
    floor: float,
    skip: Text | None,
    measured: Sequence[LanguageDiff],
) -> CoverageOutcome:
    why: Text = _fail_reason(failing, floor)
    if skip is not None:
        why = msg("probe.joined", first=why, second=skip)
    return CoverageOutcome(
        GateResult("coverage", "failed", why),
        GATE_FAILED,
        {},
        DiffCoverage(tuple(measured)),
    )


def _fail_reason(items: Sequence[LanguageDiff], floor: float) -> str:
    label = _floor_label(floor)
    return "; ".join(f"{item.language} {item.percent:.2f}% < {label}" for item in items)


def _floor_label(floor: float) -> str:
    return f"{floor:g}"


def _skip_reason(misses: Sequence[LanguageMiss]) -> Text | None:
    notes = [
        msg("coverage.skipped", language=miss.language, reason=miss.reason) for miss in misses
    ]
    if not notes:
        return None
    joined: Text = notes[0]
    for note in notes[1:]:
        joined = msg("probe.joined", first=joined, second=note)
    return joined


def _miss_reason(misses: Sequence[LanguageMiss]) -> Text:
    if not misses:
        return msg("tool.missing", tool="diff-cover")
    joined: Text = misses[0].reason
    for miss in misses[1:]:
        joined = msg("probe.joined", first=joined, second=miss.reason)
    return joined


def _coverage_drops(waivers: Sequence[Waiver]) -> tuple[Drop, ...]:
    chosen = with_prefix(waivers, _COVERAGE_PREFIX)
    return tuple(_drop(item.id[len(_COVERAGE_PREFIX) :]) for item in chosen)


def _drop(rest: str) -> Drop:
    head, sep, tail = rest.rpartition(":")
    if sep and head and tail.isdigit():
        return DroppedLine(head, int(tail))
    return DroppedFile(rest)


def _apply_drops(files: Mapping[str, FileLines], drops: Sequence[Drop]) -> dict[str, FileLines]:
    dropped_files, dropped_lines = _split_drops(drops)
    return {
        file: _without(lines, dropped_lines.get(file, frozenset()))
        for file, lines in files.items()
        if file not in dropped_files
    }


def _split_drops(drops: Sequence[Drop]) -> tuple[set[str], dict[str, frozenset[int]]]:
    files = {drop.file for drop in drops if isinstance(drop, DroppedFile)}
    lines: dict[str, set[int]] = {}
    for drop in drops:
        if isinstance(drop, DroppedLine):
            lines.setdefault(drop.file, set()).add(drop.line)
    return files, {file: frozenset(numbers) for file, numbers in lines.items()}


def _without(lines: FileLines, gone: frozenset[int]) -> FileLines:
    return FileLines(
        covered=frozenset(line for line in lines.covered if line not in gone),
        uncovered=frozenset(line for line in lines.uncovered if line not in gone),
    )


def _adjusted_percent(files: Mapping[str, FileLines], drops: Sequence[Drop]) -> DiffPercent:
    covered = 0
    measured = 0
    for lines in _apply_drops(files, drops).values():
        covered += len(lines.covered)
        measured += len(lines.covered) + len(lines.uncovered)
    if measured == 0:
        return DiffPercent(100.0)
    return DiffPercent(round(100.0 * covered / measured, 2))


def _remaining_uncovered(
    files: Mapping[str, FileLines], drops: Sequence[Drop]
) -> tuple[DiffLine, ...]:
    rows: list[DiffLine] = []
    for file, lines in _apply_drops(files, drops).items():
        for line in lines.uncovered:
            rows.append(DiffLine(file, line))
    return tuple(sorted(rows, key=lambda row: (row.file, row.line)))


def _load_files(raw: str) -> dict[str, FileLines]:
    try:
        return _parse_report(raw)
    except (ValueError, TypeError, KeyError) as exc:
        raise ToolError(msg("coverage.unreadable")) from exc


def _parse_report(raw: str) -> dict[str, FileLines]:
    stats = _src_stats(json.loads(raw))
    return {name.replace("\\", "/"): _file_lines(entry) for name, entry in stats.items()}


def _src_stats(payload: object) -> dict[str, dict[str, object]]:
    if not isinstance(payload, dict):
        raise ValueError("diff-cover json")
    stats = payload.get("src_stats", {})
    if not isinstance(stats, dict):
        raise ValueError("src_stats")
    files: dict[str, dict[str, object]] = {}
    for name, entry in stats.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            raise ValueError("src_stats")
        files[name] = entry
    return files


def _file_lines(entry: Mapping[str, object]) -> FileLines:
    return FileLines(
        covered=_line_numbers(entry.get("covered_lines")),
        uncovered=_line_numbers(entry.get("violation_lines")),
    )


def _line_numbers(value: object) -> frozenset[int]:
    if not isinstance(value, list):
        raise ValueError("lines")
    numbers: set[int] = set()
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ValueError("lines")
        numbers.add(item)
    return frozenset(numbers)


def _diff_cover_argv(artifact: Path, patch: Path, json_path: Path) -> list[str]:
    return [
        str(artifact),
        "--diff-file",
        str(patch),
        "--fail-under",
        "0",
        "--total-percent-float",
        "--format",
        f"json:{json_path}",
    ]


def _run_diff_cover(cwd: Path, artifact: Path, patch: Path) -> dict[str, FileLines]:
    json_path = artifact.parent / f"{artifact.name}.diff-cover.json"
    completed = subprocess.run(
        [sys.executable, "-m", DIFF_COVER_MODULE, *_diff_cover_argv(artifact, patch, json_path)],
        cwd=cwd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    if completed.returncode not in {0, 1} or not json_path.is_file():
        detail = (completed.stderr or completed.stdout).strip()
        raise ToolError(detail or msg("coverage.unreadable"))
    try:
        return _load_files(json_path.read_text())
    except OSError as exc:
        raise ToolError(msg("coverage.unreadable")) from exc


def _write_patch(cwd: Path, base: str, dest: Path) -> None:
    completed = subprocess.run(
        [
            "git",
            "-c",
            "diff.noprefix=no",
            "-c",
            "diff.mnemonicprefix=no",
            "diff",
            "--no-color",
            "--no-ext-diff",
            "--unified=0",
            f"{base}...HEAD",
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise ToolError(detail or msg("coverage.unreadable"))
    dest.write_text(completed.stdout)
