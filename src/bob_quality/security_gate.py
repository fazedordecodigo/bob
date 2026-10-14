from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from bob_quality.adapters.bandit import BanditParseError
from bob_quality.adapters.semgrep import SemgrepParseError
from bob_quality.config import Config
from bob_quality.diff import function_is_changed
from bob_quality.exit_codes import CONFIG_OR_TOOL, GATE_FAILED, PASSED
from bob_quality.messages import Text, msg, reason
from bob_quality.models import (
    Fail,
    Finding,
    GateResult,
    GateStatus,
    Judged,
    Measured,
    OffDiff,
    SecurityReport,
    Severity,
    Unmeasured,
    Waived,
    Warn,
)
from bob_quality.security_scanners import (
    DetachedHead,
    InPlace,
    ScanContext,
    Scanner,
    distribution_version,
    scanners_for,
)
from bob_quality.waivers import Waiver, WaiverError, load_waivers

_SCAN_TIMEOUT = 180
_PARSE_ERRORS = (BanditParseError, SemgrepParseError)


@dataclass(frozen=True)
class _JudgedRow:
    kind: type[Judged]
    status: GateStatus
    rank: int


_JUDGED: tuple[_JudgedRow, ...] = (
    _JudgedRow(Fail, "failed", 2),
    _JudgedRow(Warn, "warn", 1),
    _JudgedRow(Waived, "passed", 0),
    _JudgedRow(OffDiff, "passed", 0),
)
_RANK = {row.kind: row.rank for row in _JUDGED}


@dataclass(frozen=True)
class FailSeverities:
    values: frozenset[Severity]

    def fails(self, severity: Severity) -> bool:
        return severity in self.values


class _PrepError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail


def run_security_gate(
    cwd: Path,
    config: Config,
    base: str,
    diff_lines: dict[str, set[int]],
) -> tuple[GateResult, int, dict[str, str], SecurityReport]:
    try:
        waivers = tuple(load_waivers(cwd))
    except WaiverError as exc:
        return (
            GateResult("security", "not_run", reason(exc)),
            CONFIG_OR_TOOL,
            {},
            SecurityReport((), ()),
        )
    policy = FailSeverities(frozenset(Severity(label) for label in config.fail_severities))
    rows = scanners_for(config.languages)
    baseline, baseline_error = _baseline(cwd, base, rows)
    scans = tuple(_scan_row(cwd, config, row, baseline, baseline_error) for row in rows)
    return _fold(scans, diff_lines, policy, waivers)


def judge(
    finding: Finding,
    diff_lines: dict[str, set[int]],
    policy: FailSeverities,
    waivers: tuple[Waiver, ...],
) -> Judged:
    start = min(finding.line, finding.end_line)
    end = max(finding.line, finding.end_line)
    on_diff = function_is_changed(finding.file, start, end, diff_lines)
    specific = _waiver(waivers, _specific_id(finding))
    if specific is not None:
        return Waived(finding, specific.reason)
    if not on_diff:
        return OffDiff(finding)
    broad = _waiver(waivers, _broad_id(finding))
    if broad is not None:
        return Waived(finding, broad.reason)
    if policy.fails(finding.severity):
        return Fail(finding)
    return Warn(finding)


def security_verdict(judged: tuple[Judged, ...]) -> tuple[GateResult, int]:
    if not judged:
        return GateResult("security", "passed"), PASSED
    worst = max(_RANK[type(item)] for item in judged)
    status = _status(worst)
    exit_code = GATE_FAILED if status == "failed" else PASSED
    return GateResult("security", status, _verdict_reason(judged, status)), exit_code


def _status(rank: int) -> GateStatus:
    for row in _JUDGED:
        if row.rank == rank:
            return row.status
    raise KeyError(rank)


def _verdict_reason(judged: tuple[Judged, ...], status: GateStatus) -> Text | None:
    if status == "failed":
        return msg("security.failed", count=sum(isinstance(item, Fail) for item in judged))
    if status == "warn":
        return msg("security.warn", count=sum(isinstance(item, Warn) for item in judged))
    return None


def _broad_id(finding: Finding) -> str:
    return f"sast:{finding.tool}:{finding.rule}"


def _specific_id(finding: Finding) -> str:
    return f"{_broad_id(finding)}:{finding.file}:{finding.line}"


def _waiver(waivers: tuple[Waiver, ...], waiver_id: str) -> Waiver | None:
    for waiver in waivers:
        if waiver.id == waiver_id:
            return waiver
    return None


def _baseline(
    cwd: Path, base: str, rows: tuple[Scanner, ...]
) -> tuple[str | None, Text | None]:
    if not any(row.needs_baseline for row in rows):
        return None, None
    try:
        return _merge_base(cwd, base), None
    except _PrepError as exc:
        return None, msg("security.worktree_failed", detail=exc.detail)


def _merge_base(cwd: Path, base: str) -> str:
    completed = _git(cwd, "merge-base", base, "HEAD")
    if completed.returncode != 0:
        raise _PrepError(_git_detail(completed))
    return completed.stdout.strip()


def _scan_row(
    cwd: Path,
    config: Config,
    row: Scanner,
    baseline: str | None,
    baseline_error: Text | None,
) -> Measured | Unmeasured:
    if not row.installed():
        return Unmeasured(row.tool, msg("tool.missing", tool=row.tool))
    if row.needs_baseline and baseline is None:
        return Unmeasured(row.tool, baseline_error or msg("security.worktree_failed", detail=""))
    opened = _scan_root(row.root, cwd)
    try:
        try:
            root = next(opened)
        except _PrepError as exc:
            return Unmeasured(row.tool, msg("security.worktree_failed", detail=exc.detail))
        return _scan_at(root, config, row, baseline or "")
    finally:
        opened.close()


def _scan_root(plan: InPlace | DetachedHead, cwd: Path) -> Iterator[Path]:
    yield from _ROOT_OPEN[type(plan)](cwd)


def _in_place(cwd: Path) -> Iterator[Path]:
    yield cwd


def _detached(cwd: Path) -> Iterator[Path]:
    parent = Path(tempfile.mkdtemp(prefix="bob-semgrep-"))
    root = parent / "head"
    try:
        completed = _git(cwd, "worktree", "add", "--detach", str(root), "HEAD")
        if completed.returncode != 0:
            raise _PrepError(_git_detail(completed))
        try:
            yield root
        finally:
            _git(cwd, "worktree", "remove", "--force", str(root))
            _git(cwd, "worktree", "prune")
    finally:
        shutil.rmtree(parent, ignore_errors=True)


_ROOT_OPEN = {
    InPlace: _in_place,
    DetachedHead: _detached,
}


def _scan_at(root: Path, config: Config, row: Scanner, baseline: str) -> Measured | Unmeasured:
    if row.rules_dir is not None and not _rules_ready(root / row.rules_dir):
        return Unmeasured(row.tool, msg("security.rules_missing"))
    version = distribution_version(row.distribution) or ""
    targets = _targets(root, config.include)
    if not targets:
        return Measured(row.tool, version, ())
    with _empty_ini() as ini:
        ctx = ScanContext(
            exclude=tuple(config.exclude),
            targets=targets,
            merge_base=baseline,
            scan_root=root,
            empty_ini=ini,
            suffixes=row.suffixes or (),
        )
        try:
            completed = subprocess.run(
                row.argv(ctx),
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                timeout=_SCAN_TIMEOUT,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return Unmeasured(row.tool, msg("tool.detail", tool=row.tool, detail=str(exc)))
    if completed.returncode not in row.measurement_exits:
        return Unmeasured(
            row.tool,
            msg("tool.detail", tool=row.tool, detail=f"exit {completed.returncode}"),
        )
    try:
        findings = row.parse(completed.stdout, root)
    except _PARSE_ERRORS as exc:
        return Unmeasured(row.tool, reason(exc))
    return Measured(row.tool, version, findings)


def _rules_ready(directory: Path) -> bool:
    if not directory.is_dir():
        return False
    for path in directory.rglob("*"):
        if path.is_file() and path.suffix in {".yml", ".yaml"}:
            return True
    return False


def _targets(root: Path, include: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(item for item in include if (root / item).exists())


@contextmanager
def _empty_ini() -> Iterator[Path]:
    parent = Path(tempfile.mkdtemp(prefix="bob-bandit-"))
    path = parent / "empty.ini"
    path.write_text("#\n")
    try:
        yield path
    finally:
        shutil.rmtree(parent, ignore_errors=True)


def _fold(
    scans: tuple[Measured | Unmeasured, ...],
    diff_lines: dict[str, set[int]],
    policy: FailSeverities,
    waivers: tuple[Waiver, ...],
) -> tuple[GateResult, int, dict[str, str], SecurityReport]:
    measured, missed = _partition(scans)
    if not measured:
        return _nothing_measured(missed)
    judged = _ordered(_judge_all(measured, diff_lines, policy, waivers))
    result, code = security_verdict(judged)
    if missed:
        result, code = _note_dropped(result, code, [item.reason for item in missed])
    return result, code, _versions(measured), SecurityReport(judged, _tool_names(missed))


def _partition(
    scans: tuple[Measured | Unmeasured, ...],
) -> tuple[tuple[Measured, ...], tuple[Unmeasured, ...]]:
    measured = tuple(item for item in scans if isinstance(item, Measured))
    missed = tuple(item for item in scans if isinstance(item, Unmeasured))
    return measured, missed


def _nothing_measured(
    missed: tuple[Unmeasured, ...],
) -> tuple[GateResult, int, dict[str, str], SecurityReport]:
    return (
        GateResult("security", "not_run", _join([item.reason for item in missed])),
        CONFIG_OR_TOOL,
        {},
        SecurityReport((), _tool_names(missed)),
    )


def _judge_all(
    measured: tuple[Measured, ...],
    diff_lines: dict[str, set[int]],
    policy: FailSeverities,
    waivers: tuple[Waiver, ...],
) -> list[Judged]:
    return [
        judge(finding, diff_lines, policy, waivers)
        for item in measured
        for finding in item.findings
    ]


def _versions(measured: tuple[Measured, ...]) -> dict[str, str]:
    return {item.tool: item.version for item in measured if item.version}


def _tool_names(missed: tuple[Unmeasured, ...]) -> tuple[str, ...]:
    return tuple(item.tool for item in missed)


def _ordered(judged: list[Judged]) -> tuple[Judged, ...]:
    return tuple(
        sorted(judged, key=lambda item: (-_RANK[type(item)], item.finding.file, item.finding.line))
    )


def _note_dropped(
    result: GateResult, code: int, skipped: list[Text]
) -> tuple[GateResult, int]:
    note = _join(skipped)
    if result.status == "failed":
        detail = msg("probe.joined", first=result.reason, second=note) if result.reason else note
        return GateResult("security", "failed", detail), code
    if code != PASSED:
        return result, code
    return GateResult("security", "warn", note), code


def _join(parts: list[Text]) -> Text:
    if not parts:
        return msg("tool.missing", tool="security")
    folded = parts[0]
    for part in parts[1:]:
        folded = msg("probe.joined", first=folded, second=part)
    return folded


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _git_detail(completed: subprocess.CompletedProcess[str]) -> str:
    text = (completed.stderr or completed.stdout).strip()
    if text:
        return text.splitlines()[-1]
    return f"exit {completed.returncode}"
