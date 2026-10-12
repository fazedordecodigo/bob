"""Política do gate supply. Pura: sem processo, sem HTTP, sem relógio."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from bob_quality.exit_codes import CONFIG_OR_TOOL, GATE_FAILED, PASSED
from bob_quality.messages import Text, msg
from bob_quality.models import (
    Advisory,
    GateResult,
    MissingPackage,
    RowBlock,
    RowWarn,
    RowWaived,
    SupplyFinding,
    SupplyLanguage,
    SupplyRow,
    UndeclaredImport,
    UnverifiedAdvisory,
    UnverifiedExistence,
    Waiverable,
)
from bob_quality.waivers import Waiver


@dataclass(frozen=True)
class Judgment:
    """Saída de `judge`. O exit aqui é 0 ou 1. O 4 nasce só em `finish`."""

    status: Literal["passed", "warn", "failed"]
    exit_code: Literal[0, 1]
    reason: Text | None
    rows: tuple[SupplyRow, ...]


def waiver_id(finding: Waiverable) -> str:
    if isinstance(finding, MissingPackage):
        return f"supply:missing:{finding.index}:{finding.name}"
    if isinstance(finding, UndeclaredImport):
        return f"supply:undeclared:{finding.file}:{finding.module}"
    return f"supply:osv:{finding.advisory_id}"


def supply_waiver_ids(waivers: tuple[Waiver, ...]) -> frozenset[str]:
    return frozenset(item.id for item in waivers if item.id.startswith("supply:"))


def judge(
    findings: tuple[SupplyFinding, ...],
    diff_lines: Mapping[str, set[int]],
    fail_severities: frozenset[str],
    waiver_ids: frozenset[str],
) -> Judgment:
    return _judgment(_rows(findings, diff_lines, fail_severities, waiver_ids))


def finish(
    judgment: Judgment,
    languages_measured: tuple[SupplyLanguage, ...],
) -> tuple[GateResult, Literal[0, 1, 4]]:
    if languages_measured:
        return _copy(judgment)
    return GateResult("supply", "not_run", msg("supply.unmeasured")), CONFIG_OR_TOOL


def tool_measured(exit_code: int, parsed: bool, found_exits: frozenset[int]) -> bool:
    if not parsed:
        return False
    return exit_code == 0 or exit_code in found_exits


def _rows(
    findings: tuple[SupplyFinding, ...],
    diff_lines: Mapping[str, set[int]],
    fail_severities: frozenset[str],
    waiver_ids: frozenset[str],
) -> tuple[SupplyRow, ...]:
    seen: set[tuple[object, ...]] = set()
    rows: list[SupplyRow] = []
    for finding in findings:
        if not _on_diff(finding, diff_lines):
            continue
        key = _dedupe_key(finding)
        if key in seen:
            continue
        seen.add(key)
        rows.append(_row(finding, fail_severities, waiver_ids))
    return tuple(rows)


def _on_diff(finding: SupplyFinding, diff_lines: Mapping[str, set[int]]) -> bool:
    return finding.line in diff_lines.get(finding.file, ())


def _dedupe_key(finding: SupplyFinding) -> tuple[object, ...]:
    if isinstance(finding, (MissingPackage, UnverifiedExistence)):
        return ("package", finding.index, finding.name)
    if isinstance(finding, UndeclaredImport):
        return ("undeclared", finding.file, finding.module, finding.line)
    if isinstance(finding, Advisory):
        return ("advisory", finding.advisory_id)
    return ("unverified-advisory", finding.index, finding.name, finding.advisory_id)


def _row(
    finding: SupplyFinding,
    fail_severities: frozenset[str],
    waiver_ids: frozenset[str],
) -> SupplyRow:
    if isinstance(finding, UnverifiedExistence):
        return RowWarn(finding)
    if isinstance(finding, UnverifiedAdvisory):
        return RowWarn(finding)
    if isinstance(finding, Advisory):
        return _advisory_row(finding, fail_severities, waiver_ids)
    return _block_or_waive(finding, waiver_ids)


def _advisory_row(
    finding: Advisory,
    fail_severities: frozenset[str],
    waiver_ids: frozenset[str],
) -> SupplyRow:
    if finding.severity in fail_severities:
        return _block_or_waive(finding, waiver_ids)
    return _warn_or_waive(finding, waiver_ids)


def _block_or_waive(finding: Waiverable, waiver_ids: frozenset[str]) -> RowBlock | RowWaived:
    identifier = waiver_id(finding)
    if identifier in waiver_ids:
        return RowWaived(finding, identifier)
    return RowBlock(finding)


def _warn_or_waive(finding: Advisory, waiver_ids: frozenset[str]) -> RowWarn | RowWaived:
    identifier = waiver_id(finding)
    if identifier in waiver_ids:
        return RowWaived(finding, identifier)
    return RowWarn(finding)


def _judgment(rows: tuple[SupplyRow, ...]) -> Judgment:
    blocked = _first_block(rows)
    if blocked is not None:
        return Judgment("failed", GATE_FAILED, _block_reason(blocked), rows)
    warnings = _warn_count(rows)
    if warnings:
        return Judgment("warn", PASSED, _warn_reason(warnings), rows)
    return Judgment("passed", PASSED, None, rows)


def _first_block(rows: tuple[SupplyRow, ...]) -> RowBlock | None:
    for row in rows:
        if isinstance(row, RowBlock):
            return row
    return None


def _warn_count(rows: tuple[SupplyRow, ...]) -> int:
    return sum(1 for row in rows if isinstance(row, RowWarn))


def _warn_reason(warnings: int) -> Text:
    if warnings == 1:
        return msg("supply.warn_one")
    return msg("supply.warn_many", count=warnings)


def _block_reason(row: RowBlock) -> Text:
    finding = row.finding
    if isinstance(finding, MissingPackage):
        return msg(
            "supply.block_missing",
            index=finding.index,
            name=finding.name,
            file=finding.file,
            line=finding.line,
        )
    if isinstance(finding, UndeclaredImport):
        return msg(
            "supply.block_undeclared",
            module=finding.module,
            file=finding.file,
            line=finding.line,
        )
    return msg(
        "supply.block_advisory",
        severity=finding.severity,
        advisory=finding.advisory_id,
        name=finding.name,
        file=finding.file,
        line=finding.line,
    )


def _copy(judgment: Judgment) -> tuple[GateResult, Literal[0, 1]]:
    return GateResult("supply", judgment.status, judgment.reason), judgment.exit_code
