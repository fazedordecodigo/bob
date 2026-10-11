"""Adaptador mutmut: saída bruta da versão pinada → Mutant.

Não importa mutmut. O contrato é o texto de `mutmut results --all true`,
de `mutmut show <id>` e de `mutants/mutmut-stats.json` (mutmut==3.8.0).
"""

from __future__ import annotations

import json
import re

from bob_quality.models import Mutant, MutantStatus

_RESULT_RE = re.compile(r"^\s+(\S+):\s+(.+?)\s*$")
_FUNCTION_RE = re.compile(r"(?:^|\.)x_(?P<name>.+?)__mutmut_\d+$")
_METHOD_RE = re.compile(r"(?:^|\.)xǁ(?P<class_name>.+)ǁ(?P<name>.+?)__mutmut_\d+$")
_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")

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


def mutmut_id_prefix(file: str, name: str) -> str:
    """Prefixo do id que o mutmut 3.8 gera para uma função de topo.

    Espelha a regra pública `src.` + `x_<função>__mutmut`, sem copiar o código.
    """
    module = file.removesuffix(".py").replace("\\", "/").replace("/", ".")
    if module.startswith("src."):
        module = module[len("src.") :]
    return f"{module}.x_{name}__mutmut"


def mutmut_stats_key(file: str, name: str) -> str:
    """Chave da função em `tests_by_mangled_function_name` do mutmut 3.8."""
    return mutmut_id_prefix(file, name).removesuffix("__mutmut")


def covering_test_files(stats_raw: str) -> dict[str, set[str]]:
    """Arquivos de teste que cobrem cada função, pela chave de `mutmut_stats_key`."""
    try:
        stats = json.loads(stats_raw)
    except json.JSONDecodeError as exc:
        raise MutmutParseError(f"stats do mutmut ilegível: {exc}") from exc
    tests = stats.get("tests_by_mangled_function_name") if isinstance(stats, dict) else None
    if not isinstance(tests, dict):
        raise MutmutParseError("stats do mutmut sem tests_by_mangled_function_name")
    return {str(key): _test_files(node_ids) for key, node_ids in tests.items()}


def _test_files(node_ids: object) -> set[str]:
    if not isinstance(node_ids, list) or not all(isinstance(item, str) for item in node_ids):
        raise MutmutParseError(f"testes fora do contrato no stats do mutmut: {node_ids!r}")
    return {item.partition("::")[0] for item in node_ids}


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
            raise MutmutParseError(f"status desconhecido do mutmut: {label!r}")
        found.append((mutant_id, status))
    return found


def _function_name(mutant_id: str) -> str:
    method = _METHOD_RE.search(mutant_id)
    if method:
        return method.group("name")
    function = _FUNCTION_RE.search(mutant_id)
    if function:
        return function.group("name")
    raise MutmutParseError(f"id de mutante fora do contrato: {mutant_id}")


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
