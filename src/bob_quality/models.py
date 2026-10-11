"""Modelo de domínio. O núcleo não conhece ferramentas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

GateStatus = Literal["passed", "warn", "failed", "not_run"]
GATE_MARK = {
    "passed": "✅",
    "warn": "⚠️",
    "failed": "❌",
    "not_run": "⏭️",
}


@dataclass(frozen=True)
class FunctionMetric:
    lang: str
    module: str
    name: str
    file: str
    start_line: int
    end_line: int
    cc: int
    coverage: float
    crap: float
    changed: bool
    delta: float | None = None


@dataclass(frozen=True)
class GateResult:
    name: str
    status: GateStatus
    reason: str | None = None


@dataclass
class Report:
    schema_version: int
    commit: str
    base: str
    generated_at: str
    tool_versions: dict[str, str]
    gates: list[GateResult]
    focus: list[dict[str, object]]
    top_crap: list[dict[str, object]]
    old_debt: list[dict[str, object]] = field(default_factory=list)
    reproduce: str = ""
    exit_code: int = 0
