"""Núcleo: CRAP, limiares e veredito. Não conhece ferramentas."""

from __future__ import annotations

from pathlib import Path

from bob_quality.crap import calculate_crap
from bob_quality.exit_codes import GATE_FAILED, PASSED
from bob_quality.models import (
    Clone,
    CyclomaticFunction,
    DepViolation,
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
    lang: str = "python",
) -> FunctionMetric:
    covered = line_coverage(coverage, item.start_line, item.end_line)
    crap = calculate_crap(item.cc, covered)
    return FunctionMetric(
        lang=lang,
        module=_module_name(file),
        name=item.name,
        file=file,
        start_line=item.start_line,
        end_line=item.end_line,
        cc=item.cc,
        coverage=covered,
        crap=crap,
        changed=changed,
    )


def _module_name(file: str) -> str:
    path = Path(file)
    name = path.name
    for suffix in (".ts", ".py"):
        if name.endswith(suffix):
            path = path.with_name(name[: -len(suffix)])
            break
    return path.as_posix().replace("/", ".")


def crap_verdict(
    metrics: list[FunctionMetric],
    max_crap: float,
    scope: str = "changed",
) -> tuple[GateResult, int]:
    considered = [
        item for item in metrics if scope != "changed" or item.changed
    ]
    blockers = [item for item in considered if item.crap >= max_crap]
    if not blockers:
        return GateResult("crap", "passed", None), PASSED
    names = ", ".join(f"{item.name}@{item.file}:{item.start_line}" for item in blockers)
    return (
        GateResult("crap", "failed", f"CRAP >= {max_crap}: {names}"),
        GATE_FAILED,
    )


def below_floor(percent: float, floor: float) -> bool:
    return percent < floor


def informational_debt(
    metrics: list[FunctionMetric], max_crap: float
) -> list[FunctionMetric]:
    return [item for item in metrics if not item.changed and item.crap >= max_crap]


def top_changed_crap(metrics: list[FunctionMetric], limit: int = 5) -> list[FunctionMetric]:
    changed = [item for item in metrics if item.changed]
    return sorted(changed, key=lambda item: item.crap, reverse=True)[:limit]


def files_by_risk(
    metrics: list[FunctionMetric],
    clones: list[Clone],
    changed_files: set[str],
) -> list[dict[str, object]]:
    by_file: dict[str, float] = {}
    for item in metrics:
        if item.changed:
            by_file[item.file] = max(by_file.get(item.file, 0.0), item.crap)
    cloned = _clone_files_in_diff(clones, changed_files)
    for file in cloned:
        by_file.setdefault(file, 0.0)
    ordered = sorted(by_file.items(), key=lambda pair: pair[1], reverse=True)
    return [_focus_row(file, risk, file in cloned) for file, risk in ordered]


def _clone_files_in_diff(clones: list[Clone], changed_files: set[str]) -> set[str]:
    found: set[str] = set()
    for clone in clones:
        for file in (clone.first_file, clone.second_file):
            if file in changed_files:
                found.add(file)
    return found


def _focus_row(file: str, risk: float, cloned: bool) -> dict[str, object]:
    row: dict[str, object] = {"file": file, "risk": risk}
    if cloned:
        row["clone"] = True
    return row


def deps_verdict(violations: list[DepViolation]) -> tuple[GateResult, int]:
    """Só a aresta com origem ou destino no diff bloqueia."""
    blocking = [item for item in violations if item.in_diff]
    if not blocking:
        return GateResult("deps", "passed"), PASSED
    first = blocking[0]
    return (
        GateResult("deps", "failed", f"{first.origin} → {first.destination}"),
        GATE_FAILED,
    )


def unique_violations(items: list[DepViolation]) -> list[DepViolation]:
    seen: set[tuple[str, str, object]] = set()
    unique: list[DepViolation] = []
    for item in items:
        key = (item.origin, item.destination, item.rule)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def coverage_for(coverage_by_file: dict[str, FileCoverage], rel: str) -> FileCoverage | None:
    if rel in coverage_by_file:
        return coverage_by_file[rel]
    for key, value in coverage_by_file.items():
        normalized = key.replace("\\", "/")
        if normalized == rel or normalized.endswith("/" + rel):
            return value
    return None
