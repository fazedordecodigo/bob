from __future__ import annotations

import re
from pathlib import Path
from typing import get_args

from bob_quality.diff import as_diff_path
from bob_quality.messages import msg
from bob_quality.models import PythonDead, VultureKind

_UNUSED_KIND: dict[str, VultureKind] = {
    "attribute": "attribute",
    "class": "class",
    "function": "function",
    "import": "import",
    "method": "method",
    "property": "property",
    "variable": "variable",
}
_VULTURE_UNUSED: tuple[str, ...] = tuple(_UNUSED_KIND)
_SIZE = r"(?:, \d+ lines?)?"
_TAIL = rf"\((?P<confidence>\d+)% confidence{_SIZE}\)"
_UNUSED_RE = re.compile(
    rf"^(?P<path>.+):(?P<line>\d+): unused (?P<kind>{'|'.join(_VULTURE_UNUSED)}) "
    rf"'(?P<name>[^']*)' {_TAIL}$"
)
_AFTER_RE = re.compile(
    rf"^(?P<path>.+):(?P<line>\d+): unreachable code after '(?P<name>[^']*)' {_TAIL}$"
)
_BLOCK_RE = re.compile(
    rf"^(?P<path>.+):(?P<line>\d+): unreachable '(?P<name>[^']*)' (?:block|expression) {_TAIL}$"
)
_CONDITION_RE = re.compile(
    rf"^(?P<path>.+):(?P<line>\d+): unsatisfiable '(?P<name>[^']*)' condition {_TAIL}$"
)
_REDUNDANT_RE = re.compile(
    rf"^(?P<path>.+):(?P<line>\d+): redundant if-condition {_TAIL}$"
)


class VultureParseError(Exception):
    def __init__(self) -> None:
        super().__init__(msg("dead.unreadable", tool="vulture"))


def python_symbols(stdout: str, cwd: Path) -> tuple[PythonDead, ...]:
    found: list[PythonDead] = []
    for raw in stdout.splitlines():
        text = raw.strip()
        if text == "":
            continue
        symbol = _symbol(text, cwd)
        if symbol is not None:
            found.append(symbol)
    return tuple(found)


def _symbol(text: str, cwd: Path) -> PythonDead | None:
    unused = _UNUSED_RE.match(text)
    if unused is not None:
        return _build(unused, cwd, _UNUSED_KIND[unused.group("kind")], unused.group("name"))
    for pattern in (_AFTER_RE, _BLOCK_RE, _CONDITION_RE):
        matched = pattern.match(text)
        if matched is not None:
            return _build(matched, cwd, "unreachable_code", matched.group("name"))
    redundant = _REDUNDANT_RE.match(text)
    if redundant is not None:
        return _build(redundant, cwd, "unreachable_code", "if")
    raise VultureParseError()


def _build(
    matched: re.Match[str], cwd: Path, kind: VultureKind, name: str
) -> PythonDead | None:
    confidence = int(matched.group("confidence"))
    if not 0 <= confidence <= 100:
        raise VultureParseError()
    relative = as_diff_path(cwd, matched.group("path"))
    if relative is None:
        return None
    return PythonDead(relative, int(matched.group("line")), name, kind, confidence)


assert set(_VULTURE_UNUSED) | {"unreachable_code"} == set(get_args(VultureKind))
