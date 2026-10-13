"""Modelo de domínio. O núcleo não conhece ferramentas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from bob_quality.messages import Text

GateStatus = Literal["passed", "warn", "failed", "not_run"]

SECRET_PREFIX = "secret:"


@dataclass(frozen=True)
class SecretRow:
    file: str
    line: int
    rule_id: str

    def waiver_id(self) -> str:
        return f"{SECRET_PREFIX}{self.rule_id}:{self.file}:{self.line}"


@dataclass(frozen=True)
class SecretLedger:
    blocking: tuple[SecretRow, ...] = ()
    outside_diff: tuple[SecretRow, ...] = ()

    def __post_init__(self) -> None:
        rows = (*self.blocking, *self.outside_diff)
        ids = [row.waiver_id() for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate secret row")
        _require_sorted(self.blocking)
        _require_sorted(self.outside_diff)
        for row in rows:
            if row.line < 1:
                raise ValueError("secret line")


def _require_sorted(rows: tuple[SecretRow, ...]) -> None:
    ordered = tuple(sorted(rows, key=lambda row: (row.file, row.line, row.rule_id)))
    if ordered != rows:
        raise ValueError("secret rows are unsorted")


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


VultureKind = Literal[
    "attribute",
    "class",
    "function",
    "import",
    "method",
    "property",
    "variable",
    "unreachable_code",
]

KnipKind = Literal[
    "export",
    "type",
    "enum_member",
    "namespace_member",
    "ns_export",
    "ns_type",
]


@dataclass(frozen=True)
class PythonDead:
    file: str
    line: int
    name: str
    kind: VultureKind
    confidence: int


@dataclass(frozen=True)
class TypeScriptDead:
    file: str
    line: int
    name: str
    kind: KnipKind


DeadSymbol = PythonDead | TypeScriptDead


@dataclass(frozen=True)
class LedgerRow:
    """Definição no diff. `waiver` é o id `dead:` ou None quando a linha conta para o aviso."""

    symbol: DeadSymbol
    waiver: str | None


@dataclass(frozen=True)
class DeadSection:
    """Presente no relatório quando o gate rodou. `rows` vazio continua verdadeiro."""

    rows: tuple[LedgerRow, ...] = ()


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
    secrets: SecretLedger | None = None
    dead_code: DeadSection | None = None
