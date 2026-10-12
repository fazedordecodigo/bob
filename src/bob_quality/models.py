"""Modelo de domínio. O núcleo não conhece ferramentas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from bob_quality.messages import Text

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


MutantStatus = Literal["killed", "survived", "timeout", "no_coverage"]


@dataclass(frozen=True)
class Mutant:
    """Mutante. Produzido pelo adaptador mutmut a partir da saída bruta."""

    id: str
    function: str
    file: str
    line: int
    operator: str
    status: MutantStatus
    waiver: str | None = None


@dataclass(frozen=True)
class Clone:
    """Par duplicado. Produzido pelo adaptador jscpd a partir do JSON."""

    first_file: str
    first_start: int
    first_end: int
    second_file: str
    second_start: int
    second_end: int
    lines: int
    tokens: int
    similarity: float | None = None
    kind: str = ""


@dataclass(frozen=True)
class DepViolation:
    """Aresta proibida ou de ciclo. `origin → destination`."""

    origin: str
    destination: str
    rule: Text
    in_diff: bool


@dataclass(frozen=True)
class GateResult:
    name: str
    status: GateStatus
    reason: Text | None = None


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
    clones: list[Clone] = field(default_factory=list)
    reproduce: str = ""
    exit_code: int = 0
    waivers: list[dict[str, object]] = field(default_factory=list)
    survivors: list[dict[str, object]] = field(default_factory=list)
    mutation: dict[str, object] | None = None


SupplyLanguage = Literal["python", "typescript"]
SupplyIndex = Literal["pypi", "npm"]
FailSeverity = Literal["HIGH", "CRITICAL"]
Severity = Literal["CRITICAL", "HIGH", "MODERATE", "LOW"]
UndecidedCause = Literal["timeout", "dns", "undecided"]


@dataclass(frozen=True)
class MissingPackage:
    index: SupplyIndex
    name: str
    file: str
    line: int
    kind: Literal["missing"] = "missing"


@dataclass(frozen=True)
class UndeclaredImport:
    file: str
    module: str
    line: int
    kind: Literal["undeclared"] = "undeclared"


@dataclass(frozen=True)
class Advisory:
    advisory_id: str
    index: SupplyIndex
    name: str
    severity: Severity
    file: str
    line: int
    kind: Literal["advisory"] = "advisory"


@dataclass(frozen=True)
class UnverifiedExistence:
    index: SupplyIndex
    name: str
    file: str
    line: int
    cause: UndecidedCause
    kind: Literal["unverified"] = "unverified"
    question: Literal["existence"] = "existence"


@dataclass(frozen=True)
class UnverifiedAdvisory:
    index: SupplyIndex
    name: str
    file: str
    line: int
    cause: UndecidedCause
    advisory_id: str | None = None
    kind: Literal["unverified"] = "unverified"
    question: Literal["advisory"] = "advisory"


SupplyFinding = (
    MissingPackage | UndeclaredImport | Advisory | UnverifiedExistence | UnverifiedAdvisory
)
Waiverable = MissingPackage | UndeclaredImport | Advisory
Warner = UnverifiedExistence | UnverifiedAdvisory | Advisory


@dataclass(frozen=True)
class RowBlock:
    finding: Waiverable
    effect: Literal["block"] = "block"


@dataclass(frozen=True)
class RowWarn:
    finding: Warner
    effect: Literal["warn"] = "warn"


@dataclass(frozen=True)
class RowWaived:
    finding: Waiverable
    waiver_id: str
    effect: Literal["waived"] = "waived"


SupplyRow = RowBlock | RowWarn | RowWaived


@dataclass(frozen=True)
class SupplyReport:
    measured: tuple[SupplyLanguage, ...]
    skipped: tuple[SupplyLanguage, ...]
    rows: tuple[SupplyRow, ...]
