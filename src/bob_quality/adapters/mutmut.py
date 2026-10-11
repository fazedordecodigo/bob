"""Adaptador mutmut: saída bruta da versão pinada → Mutant.

Não importa mutmut. O contrato é o texto de `mutmut results --all true`
e de `mutmut show <id>` (mutmut==3.8.0).
"""

from __future__ import annotations

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


def _parse_show(raw: str) -> tuple[str, int, str]:
    file = ""
    removed: list[str] = []
    added: list[str] = []
    new_line = 0
    change_line = 0
    in_hunk = False
    for line in raw.splitlines():
        if line.startswith("--- "):
            file = line[4:].strip()
            if file.startswith("a/"):
                file = file[2:]
            continue
        if line.startswith("+++ ") or line.startswith("\\"):
            continue
        hunk = _HUNK_RE.match(line)
        if hunk:
            new_line = int(hunk.group(1))
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if line.startswith("+"):
            if change_line == 0:
                change_line = new_line
            added.append(line[1:].strip())
            new_line += 1
            continue
        if line.startswith("-"):
            removed.append(line[1:].strip())
            continue
        new_line += 1
    operator = ""
    if removed or added:
        operator = f"{' ; '.join(removed)} -> {' ; '.join(added)}"
    return file, change_line, operator
