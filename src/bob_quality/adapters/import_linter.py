"""Adaptador do import-linter: texto da CLI → `DepViolation`."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bob_quality.core import unique_violations
from bob_quality.models import DepViolation

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_EMPTY_REPORT = re.compile(r"^Contracts: \d+ kept, 0 broken\.$")
_RELATIVE = re.compile(r"^\s*-\s+(\.\w+(?:\.\w+)*)\s+->\s+(\.\w+(?:\.\w+)*)")
_ABSOLUTE = re.compile(r"^\s*-\s+(\w+(?:\.\w+)*)\s+->\s+(\w+(?:\.\w+)*)")
_CYCLE_PACKAGE = "No cycles are allowed in "
_SKIP_HEADINGS = {"Contracts", "Broken contracts"}


@dataclass
class _ParseState:
    rule: str = "import-linter"
    package: str = ""
    previous: str = ""
    found: list[DepViolation] = field(default_factory=list)


def is_empty_report(raw: str) -> bool:
    """Verdadeiro quando o texto traz a linha `N kept, 0 broken`."""
    for line in _ANSI.sub("", raw).splitlines():
        if _EMPTY_REPORT.match(line.strip()):
            return True
    return False


def broken_contract_name(raw: str) -> str | None:
    """Nome do contrato quando o relatório diz BROKEN e não há aresta `->`."""
    for line in _ANSI.sub("", raw).splitlines():
        stripped = line.strip()
        if stripped.endswith(" BROKEN"):
            name = stripped[: -len(" BROKEN")].strip()
            return name
    return None


def parse_import_linter(raw: str) -> list[DepViolation]:
    state = _ParseState()
    for line in _ANSI.sub("", raw).splitlines():
        _consume(state, line.strip())
    return unique_violations(state.found)


def _consume(state: _ParseState, stripped: str) -> None:
    if _is_underline(stripped) and state.previous and state.previous not in _SKIP_HEADINGS:
        state.rule = state.previous
    state.previous = stripped
    package = _cycle_package(stripped)
    if package:
        state.package = package
    edge = _edge(stripped, state.package)
    if edge is not None:
        state.found.append(DepViolation(edge[0], edge[1], state.rule, False))


def _is_underline(line: str) -> bool:
    return bool(line) and set(line) == {"-"}


def _cycle_package(line: str) -> str:
    if line.startswith(_CYCLE_PACKAGE) and line.endswith("."):
        return line[len(_CYCLE_PACKAGE) : -1].strip()
    return ""


def _edge(line: str, package: str) -> tuple[str, str] | None:
    relative = _RELATIVE.match(line)
    if relative:
        return _qualify(relative.group(1), package), _qualify(relative.group(2), package)
    absolute = _ABSOLUTE.match(line)
    if absolute:
        return absolute.group(1), absolute.group(2)
    return None


def _qualify(name: str, package: str) -> str:
    if not name.startswith("."):
        return name
    suffix = name[1:]
    if package:
        return f"{package}.{suffix}"
    return suffix
