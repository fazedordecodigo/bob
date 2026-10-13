"""Modelo de domínio. O núcleo não conhece ferramentas."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Literal

from bob_quality.messages import Text

GateStatus = Literal["passed", "warn", "failed", "not_run"]
CognitiveLanguage = Literal["python", "typescript"]


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
class CognitiveFunction:
    """Função medida.

    O arquivo é posix relativo ao repositório. start_line e end_line são
    inclusivos e cobrem a função inteira. O id de waiver é
    cognitive:<arquivo>:<nome>.
    """

    file: str
    name: str
    start_line: int
    end_line: int
    score: int
    language: CognitiveLanguage

    def __post_init__(self) -> None:
        _reject_cognitive_file(self.file)
        _reject_cognitive_name(self.name)
        _reject_cognitive_span(self.start_line, self.end_line, self.score)

    def waiver_id(self) -> str:
        return f"cognitive:{self.file}:{self.name}"


def _reject_cognitive_file(file: str) -> None:
    path = PurePosixPath(file)
    if path.is_absolute():
        raise ValueError("file must be repo-relative")
    if ".." in path.parts:
        raise ValueError("file must not contain ..")
    if file.startswith("./"):
        raise ValueError("file must not start with ./")


def _reject_cognitive_name(name: str) -> None:
    if name == "":
        raise ValueError("name must not be empty")
    if "\n" in name or "\r" in name:
        raise ValueError("name must not contain a newline")


def _reject_cognitive_span(start_line: int, end_line: int, score: int) -> None:
    if start_line < 1:
        raise ValueError("start_line must be positive")
    if end_line < start_line:
        raise ValueError("end_line must not precede start_line")
    if score < 0:
        raise ValueError("score must not be negative")


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
    cognitive: list[CognitiveFunction] = field(default_factory=list)
