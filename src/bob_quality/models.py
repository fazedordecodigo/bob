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


def qualified_name(name: str, owner: str | None) -> str:
    """`nome` sem dono, `Dono.nome` com dono. O ponto entre classe e método só nasce aqui."""
    return name if owner is None else f"{owner}.{name}"


@dataclass(frozen=True)
class MutationTarget:
    """Função que o gate de mutação mira. Só `adapters.mutmut.mutation_targets` dá `owner`.

    `owner` é a classe que tem o `def` no corpo. Só o método direto de uma classe
    do topo do módulo tem o nome simples da classe, a grafia que o mutmut 3.8 gera.
    Todo outro dono tem ponto e não casa com id nenhum do mutmut.
    `start_line` é a primeira linha que o `mutmut show` imprime. Num método é o
    primeiro decorador. No resto é o `def` medido pelo lizard. `end_line` é a do lizard.
    `qualname` e `key` são métodos, não `@property`, porque o mutmut 3.8 não
    gera mutante para `@property` e o gate deste repositório muta este arquivo.
    """

    file: str
    name: str
    start_line: int
    end_line: int
    owner: str | None = None

    def qualname(self) -> str:
        """`Mutant.function` dos mutantes do alvo, e o nome que o waiver cita."""
        return qualified_name(self.name, self.owner)

    def key(self) -> str:
        """`arquivo::qualname`. Chave do cache, rótulo do relatório e id de waiver."""
        return f"{self.file}::{self.qualname()}"


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
