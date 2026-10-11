"""Junta CC e cobertura numa métrica. Não invoca ferramentas."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from bob_quality.core import coverage_for, to_metric
from bob_quality.diff import function_is_changed
from bob_quality.models import (
    CyclomaticFunction,
    FileCoverage,
    FunctionMetric,
    GateResult,
)


@dataclass
class ProbeResult:
    metrics: list[FunctionMetric] = field(default_factory=list)
    versions: dict[str, str] = field(default_factory=dict)
    gate: GateResult | None = None
    exit_code: int | None = None


def relative_path(cwd: Path, path: str) -> str:
    resolved = Path(path)
    try:
        return resolved.resolve().relative_to(cwd.resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def build_metrics(
    cwd: Path,
    functions: list[CyclomaticFunction],
    coverage_files: dict[str, FileCoverage],
    diff_lines: dict[str, set[int]],
    lang: str,
) -> list[FunctionMetric]:
    metrics: list[FunctionMetric] = []
    for item in functions:
        rel = relative_path(cwd, item.file)
        metrics.append(
            to_metric(
                item,
                rel,
                coverage_for(coverage_files, rel),
                function_is_changed(rel, item.start_line, item.end_line, diff_lines),
                lang=lang,
            )
        )
    return metrics
