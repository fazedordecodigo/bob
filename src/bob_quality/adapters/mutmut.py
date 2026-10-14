"""Adaptador mutmut: saída bruta da versão pinada → Mutant, e o nome que o mutmut dá a cada alvo.

Não importa mutmut. O contrato é o texto de `mutmut results --all true`
e de `mutmut show <id>` (mutmut==3.8.0).
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass

from bob_quality.exit_codes import pytest_passed
from bob_quality.messages import msg
from bob_quality.models import (
    CyclomaticFunction,
    Mutant,
    MutantStatus,
    MutationTarget,
    qualified_name,
)

_RESULT_RE = re.compile(r"^\s+(\S+):\s+(.+?)\s*$")
_FUNCTION_RE = re.compile(r"(?:^|\.)x_(?P<name>.+?)__mutmut_\d+$")
_METHOD_RE = re.compile(r"(?:^|\.)xǁ(?P<class_name>.+)ǁ(?P<name>.+?)__mutmut_\d+$")
_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")
# Linhas que `mutmut run` 3.8 imprime antes de sair 1 quando a suíte falha.
_STATS_FAILED_RE = re.compile(r"failed to collect stats\. runner returned (\d+)")
_CLEAN_FAILED = "Failed to run clean test"

# Status impressos por mutmut 3.8 (`status_by_exit_code`). O mapa é nosso.
_STATUS: dict[str, MutantStatus] = {
    "killed": "killed",
    "caught by type check": "killed",
    "survived": "survived",
    "suspicious": "survived",
    "segfault": "survived",
    "timeout": "timeout",
    "no tests": "no_coverage",
    "skipped": "no_coverage",
    "not checked": "no_coverage",
    "check was interrupted by user": "no_coverage",
}


class MutmutParseError(Exception):
    """Saída do mutmut fora do contrato da versão pinada."""


def suite_failed(output: str) -> bool:
    """A suíte falhou dentro do `mutmut run`. Exit 5 do pytest (nada coletado) não conta."""
    if _CLEAN_FAILED in output:
        return True
    return any(not pytest_passed(int(code)) for code in _STATS_FAILED_RE.findall(output))


def ids_for_show(mutants: list[Mutant]) -> list[str]:
    """Diff só de sobrevivente e timeout. O status já veio do results."""
    return [item.id for item in mutants if item.status in {"survived", "timeout"}]


def mutants_from_raw(results_raw: str, shows: dict[str, str]) -> list[Mutant]:
    """Junta `results` com os `show` correspondentes e devolve o modelo."""
    mutants: list[Mutant] = []
    for mutant_id, status in _parse_results(results_raw):
        file, line, operator = ("", 0, "")
        show = shows.get(mutant_id)
        if show is not None:
            file, line, operator = _parse_show(show)
        mutants.append(
            Mutant(
                id=mutant_id,
                function=_function_name(mutant_id),
                file=file,
                line=line,
                operator=operator,
                status=status,
            )
        )
    return mutants


def mutation_targets(
    functions: list[CyclomaticFunction], sources: Mapping[str, str]
) -> list[MutationTarget]:
    """Dá a cada função medida pelo lizard o nome que o mutmut 3.8 gera.

    `sources` leva cada `function.file` ao texto do arquivo. A junção com o `ast`
    é a linha do `def`, que é o `start_line` do lizard. Um `def` no corpo de uma
    classe vira método dela. O resto sai como o lizard mediu, sem `owner`, e o
    nome com ponto do lizard (`outer.inner`) também. Levanta `MutmutParseError`
    quando o `ast` não lê um arquivo, ou quando um nome sem ponto começa dentro
    de uma classe e não casa com nenhum `def` dela.
    """
    files = {item.file for item in functions}
    indexes = {file: _class_index(sources[file], file) for file in files}
    return [_target(item, indexes[item.file]) for item in functions]


def mutmut_id_prefix(file: str, name: str) -> str:
    """Prefixo do id que o mutmut 3.8 gera.

    Sem ponto, função de topo: `x_<nome>`. Com ponto, o último ponto separa o
    dono do método (`Box.open`, `Box.Inner.open`): `xǁ<dono>ǁ<nome>`. O nome
    aninhado do lizard (`outer.inner`) tem a mesma forma e não é um id que o
    mutmut emite.
    """
    module = file.removesuffix(".py").replace("\\", "/").replace("/", ".")
    if module.startswith("src."):
        module = module[len("src.") :]
    if "." not in name:
        return f"{module}.x_{name}__mutmut"
    owner, method = name.rsplit(".", 1)
    return f"{module}.xǁ{owner}ǁ{method}__mutmut"


def id_matches_function(mutant_id: str, file: str, name: str) -> bool:
    return _prefix_match(mutant_id, mutmut_id_prefix(file, name))


def _prefix_match(mutant_id: str, prefix: str) -> bool:
    if not prefix:
        return False
    return mutant_id == prefix or mutant_id.startswith(f"{prefix}_")


def mutmut_stats_key(file: str, name: str) -> str:
    """Chave da função em `tests_by_mangled_function_name` do mutmut 3.8."""
    return mutmut_id_prefix(file, name).removesuffix("__mutmut")


def mutmut_run_patterns(file: str, name: str) -> list[str]:
    """Padrões do `mutmut run`: os mutantes da função e a chave dela no stats.

    O mutmut 3.8 escolhe os testes da execução limpa casando cada padrão com `*`
    contra as chaves do stats, por fnmatch. Sem o segundo padrão nada casa, e a
    execução limpa roda a suíte inteira.
    """
    return [f"{mutmut_id_prefix(file, name)}*", f"*{mutmut_stats_key(file, name)}"]


_NESTED = "nested"


@dataclass(frozen=True)
class _ClassMethod:
    owner: str
    name: str
    first_line: int


@dataclass(frozen=True)
class _ClassIndex:
    methods: dict[int, _ClassMethod]
    bodies: list[range]

    def encloses(self, line: int) -> bool:
        return any(line in body for body in self.bodies)


def _target(function: CyclomaticFunction, index: _ClassIndex) -> MutationTarget:
    found = index.methods.get(function.start_line)
    if found is not None and found.name == function.name:
        return MutationTarget(
            function.file, function.name, found.first_line, function.end_line, found.owner
        )
    if "." not in function.name and index.encloses(function.start_line):
        raise MutmutParseError(
            msg(
                "mutmut.unmatched_method",
                name=function.name,
                file=function.file,
                line=function.start_line,
            )
        )
    return MutationTarget(function.file, function.name, function.start_line, function.end_line)


def _class_index(source: str, file: str) -> _ClassIndex:
    """Linha do `def` para cada `def` no escopo de uma classe, e as linhas de cada classe.

    Espelha a regra de nomes do mutmut 3.8. Só o `def` direto no corpo de uma
    classe direta do módulo tem como dono o nome simples da classe. Todo outro
    dono tem ponto, e o padrão dele não casa com id do mutmut: `Box.Inner` numa
    classe dentro de classe, `nested.Late` numa classe fora do corpo do módulo e
    `Box.nested` num `def` sob `if` ou `try` no corpo da classe. Nenhum decorador
    muda a regra. A primeira linha do método é o primeiro decorador.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise MutmutParseError(
            msg("mutmut.unreadable_source", file=file, line=exc.lineno, detail=exc.msg)
        ) from exc
    methods: dict[int, _ClassMethod] = {}
    bodies: list[range] = []
    for cls, owner in _class_owners(tree):
        bodies.append(range(cls.lineno, (cls.end_lineno or cls.lineno) + 1))
        for node, method_owner in _scope_defs(cls.body, owner):
            first = min([node.lineno, *(item.lineno for item in node.decorator_list)])
            methods[node.lineno] = _ClassMethod(method_owner, node.name, first)
    return _ClassIndex(methods, bodies)


def _class_owners(tree: ast.Module) -> Iterator[tuple[ast.ClassDef, str]]:
    """Cada classe com o dono dos métodos dela. O `ast.walk` visita o pai antes do filho."""
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    owners: dict[ast.AST, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            parent = parents[node]
            scope = None if parent is tree else owners.get(parent, _NESTED)
            owners[node] = qualified_name(node.name, scope)
            yield node, owners[node]


def _scope_defs(
    nodes: Iterable[ast.AST], owner: str
) -> Iterator[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]]:
    """Os `def` do escopo de uma classe. Sob `if` ou `try`, o dono ganha `nested`."""
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node, owner
        elif not isinstance(node, ast.ClassDef):
            yield from _scope_defs(ast.iter_child_nodes(node), qualified_name(_NESTED, owner))


def _parse_results(raw: str) -> list[tuple[str, MutantStatus]]:
    found: list[tuple[str, MutantStatus]] = []
    for line in raw.splitlines():
        match = _RESULT_RE.match(line)
        if not match:
            continue
        mutant_id, label = match.group(1), match.group(2)
        if "__mutmut_" not in mutant_id:
            continue
        status = _STATUS.get(label)
        if status is None:
            raise MutmutParseError(msg("mutmut.unknown_status", label=label))
        found.append((mutant_id, status))
    return found


def _function_name(mutant_id: str) -> str:
    """`x_nome` dá `nome`. `xǁClasseǁnome` dá `Classe.nome`, igual a `MutationTarget.qualname()`."""
    method = _METHOD_RE.search(mutant_id)
    if method:
        return qualified_name(method.group("name"), method.group("class_name"))
    function = _FUNCTION_RE.search(mutant_id)
    if function:
        return function.group("name")
    raise MutmutParseError(msg("mutmut.bad_id", mutant_id=mutant_id))


class _ShowState:
    def __init__(self) -> None:
        self.file = ""
        self.removed: list[str] = []
        self.added: list[str] = []
        self.new_line = 0
        self.change_line = 0
        self.in_hunk = False


def _parse_show(raw: str) -> tuple[str, int, str]:
    state = _ShowState()
    for line in raw.splitlines():
        _consume_show_line(state, line)
    return state.file, state.change_line, _operator(state.removed, state.added)


def _consume_show_line(state: _ShowState, line: str) -> None:
    if _consume_show_header(state, line):
        return
    if state.in_hunk:
        _consume_hunk_line(state, line)


def _consume_show_header(state: _ShowState, line: str) -> bool:
    if line.startswith("--- "):
        state.file = line[4:].strip().removeprefix("a/")
        return True
    if line.startswith("+++ ") or line.startswith("\\"):
        return True
    hunk = _HUNK_RE.match(line)
    if hunk:
        state.new_line = int(hunk.group(1))
        state.in_hunk = True
        return True
    return False


def _consume_hunk_line(state: _ShowState, line: str) -> None:
    if line.startswith("+"):
        if state.change_line == 0:
            state.change_line = state.new_line
        state.added.append(line[1:].strip())
        state.new_line += 1
        return
    if line.startswith("-"):
        state.removed.append(line[1:].strip())
        return
    state.new_line += 1


def _operator(removed: list[str], added: list[str]) -> str:
    if not removed and not added:
        return ""
    return f"{' ; '.join(removed)} -> {' ; '.join(added)}"
