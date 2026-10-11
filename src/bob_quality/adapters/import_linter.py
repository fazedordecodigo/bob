"""Adaptador do import-linter: texto da CLI → `DepViolation`."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bob_quality.core import unique_violations
from bob_quality.models import DepViolation

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_RELATIVE = re.compile(r"^\s*-\s+(\.\w+(?:\.\w+)*)\s+->\s+(\.\w+(?:\.\w+)*)")
_ABSOLUTE = re.compile(r"^\s*-\s+(\w+(?:\.\w+)*)\s+->\s+(\w+(?:\.\w+)*)")
_CYCLE_PACKAGE = "No cycles are allowed in "
_SKIP_HEADINGS = {"Contracts", "Broken contracts"}


@dataclass
class _ParseState:
    rule: str = "import-linter"
    package: str = ""
    found: list[DepViolation] = field(default_factory=list)


def broken_contract_name(raw: str) -> str | None:
    """Nome do contrato quando o relatório diz BROKEN e não há aresta `->`."""
    for line in _ANSI.sub("", raw).splitlines():
        stripped = line.strip()
        if stripped.endswith(" BROKEN"):
            name = stripped[: -len(" BROKEN")].strip()
            return name or "import-linter"
    return None


def parse_import_linter(raw: str) -> list[DepViolation]:
    lines = _ANSI.sub("", raw).splitlines()
    state = _ParseState()
    for index, line in enumerate(lines):
        _consume(state, lines, index, line)
    return unique_violations(state.found)


def _consume(state: _ParseState, lines: list[str], index: int, line: str) -> None:
    stripped = line.strip()
    if _is_heading(lines, index) and stripped not in _SKIP_HEADINGS:
        state.rule = stripped
    package = _cycle_package(stripped)
    if package:
        state.package = package
    edge = _edge(stripped, state.package)
    if edge is not None:
        state.found.append(DepViolation(edge[0], edge[1], state.rule))


def _is_heading(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    underline = lines[index + 1].strip()
    return bool(underline) and set(underline) == {"-"}


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
