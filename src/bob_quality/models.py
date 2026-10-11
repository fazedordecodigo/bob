"""Modelo de domínio. O núcleo não conhece ferramentas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

GateStatus = Literal["passed", "warn", "failed", "not_run"]


@dataclass(frozen=True)
class CyclomaticFunction:
    """Função com CC. Produzido pelo adaptador lizard a partir da saída bruta."""

    file: str
    name: str
    start_line: int
    end_line: int
    cc: int


@dataclass(frozen=True)
class FileCoverage:
    """Cobertura por linha de um arquivo. Produzido pelo adaptador coverage.py."""

    executed_lines: frozenset[int]
    missing_lines: frozenset[int]


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
class DepViolation:
    """Aresta proibida ou de ciclo. `origin → destination`."""

    origin: str
    destination: str
    rule: str
    in_diff: bool


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
    dependencies: list[dict[str, object]] = field(default_factory=list)
    old_dependencies: list[dict[str, object]] = field(default_factory=list)
    reproduce: str = ""
    exit_code: int = 0
