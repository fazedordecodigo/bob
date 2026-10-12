"""Adaptador knip: JSON do reporter 6.41.0 → símbolos do núcleo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import get_args

from bob_quality.diff import as_diff_path
from bob_quality.messages import msg
from bob_quality.models import KnipKind, TypeScriptDead

_KNIP_KINDS: dict[str, KnipKind] = {
    "exports": "export",
    "types": "type",
    "enumMembers": "enum_member",
    "namespaceMembers": "namespace_member",
    "nsExports": "ns_export",
    "nsTypes": "ns_type",
}


class KnipParseError(Exception):
    """Documento fora do JSON do knip 6.41.0."""

    def __init__(self) -> None:
        super().__init__(msg("dead.unreadable", tool="knip"))


def typescript_symbols(raw: str, cwd: Path) -> tuple[TypeScriptDead, ...]:
    found: list[TypeScriptDead] = []
    for issue in _issues(raw):
        found.extend(_issue_symbols(issue, cwd))
    return tuple(found)


def _issues(raw: str) -> list[object]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise KnipParseError() from exc
    if not isinstance(payload, dict):
        raise KnipParseError()
    issues = payload.get("issues")
    if not isinstance(issues, list):
        raise KnipParseError()
    return issues


def _issue_symbols(issue: object, cwd: Path) -> tuple[TypeScriptDead, ...]:
    if not isinstance(issue, dict):
        raise KnipParseError()
    file = issue.get("file")
    if not isinstance(file, str):
        raise KnipParseError()
    relative = as_diff_path(cwd, file)
    found: list[TypeScriptDead] = []
    for key, kind in _KNIP_KINDS.items():
        if key not in issue:
            continue
        items = issue[key]
        if not isinstance(items, list):
            raise KnipParseError()
        for item in items:
            symbol = _symbol(item, relative, kind)
            if symbol is not None:
                found.append(symbol)
    return tuple(found)


def _symbol(item: object, relative: str | None, kind: KnipKind) -> TypeScriptDead | None:
    if not isinstance(item, dict):
        raise KnipParseError()
    name = item.get("name")
    line = item.get("line")
    if not isinstance(name, str) or not _line(line):
        raise KnipParseError()
    qualified = _qualified(item, name)
    if relative is None:
        return None
    return TypeScriptDead(relative, line, qualified, kind)


def _line(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _qualified(item: dict[str, object], name: str) -> str:
    if "namespace" not in item or item["namespace"] is None:
        return name
    namespace = item["namespace"]
    if not isinstance(namespace, str):
        raise KnipParseError()
    if namespace == "":
        return name
    return f"{namespace}.{name}"


assert set(_KNIP_KINDS.values()) == set(get_args(KnipKind))
