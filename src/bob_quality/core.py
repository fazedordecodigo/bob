"""Núcleo: CRAP, limiares e veredito. Não conhece ferramentas."""

from __future__ import annotations

from bob_quality.crap import calculate_crap
from bob_quality.exit_codes import GATE_FAILED, PASSED
from bob_quality.models import (
    CyclomaticFunction,
    FileCoverage,
    FunctionMetric,
    GateResult,
)


def line_coverage(coverage: FileCoverage | None, start_line: int, end_line: int) -> float:
    """Cobertura de linhas executáveis no intervalo da função, fração [0, 1]."""
    if coverage is None:
        return 0.0
    statements = {
        line
        for line in coverage.executed_lines | coverage.missing_lines
        if start_line <= line <= end_line
    }
    if not statements:
        return 1.0
    return len(statements & coverage.executed_lines) / len(statements)


def to_metric(
    item: CyclomaticFunction,
    file: str,
    coverage: FileCoverage | None,
    changed: bool,
) -> FunctionMetric:
    covered = line_coverage(coverage, item.start_line, item.end_line)
    crap = calculate_crap(item.cc, covered)
    return FunctionMetric(
        lang="python",
        module=file.replace("/", ".").removesuffix(".py"),
        name=item.name,
        file=file,
        start_line=item.start_line,
        end_line=item.end_line,
        cc=item.cc,
        coverage=covered,
        crap=crap,
        changed=changed,
    )


def crap_verdict(
    metrics: list[FunctionMetric], max_crap: float
) -> tuple[GateResult, int]:
    blockers = [item for item in metrics if item.changed and item.crap > max_crap]
    if not blockers:
        return GateResult("crap", "passed", None), PASSED
    names = ", ".join(f"{item.name}@{item.file}:{item.start_line}" for item in blockers)
    return (
        GateResult("crap", "failed", f"CRAP > {max_crap}: {names}"),
        GATE_FAILED,
    )


def informational_debt(
    metrics: list[FunctionMetric], max_crap: float
) -> list[FunctionMetric]:
    return [item for item in metrics if not item.changed and item.crap > max_crap]


def top_changed_crap(metrics: list[FunctionMetric], limit: int = 5) -> list[FunctionMetric]:
    changed = [item for item in metrics if item.changed]
    return sorted(changed, key=lambda item: item.crap, reverse=True)[:limit]


def files_by_risk(metrics: list[FunctionMetric]) -> list[dict[str, object]]:
    by_file: dict[str, float] = {}
    for item in metrics:
        if not item.changed:
            continue
        by_file[item.file] = max(by_file.get(item.file, 0.0), item.crap)
    ordered = sorted(by_file.items(), key=lambda pair: pair[1], reverse=True)
    return [{"file": file, "risk": risk} for file, risk in ordered]


def coverage_for(coverage_by_file: dict[str, FileCoverage], rel: str) -> FileCoverage | None:
    if rel in coverage_by_file:
        return coverage_by_file[rel]
    for key, value in coverage_by_file.items():
        normalized = key.replace("\\", "/")
        if normalized == rel or normalized.endswith("/" + rel):
            return value
    return None
