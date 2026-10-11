"""Adaptador jscpd: JSON da ferramenta pinada → modelo do núcleo."""

from __future__ import annotations

import json
from typing import Any

from bob_quality.messages import msg
from bob_quality.models import Clone


class JscpdParseError(Exception):
    """JSON do jscpd fora do contrato da versão pinada."""


def parse_jscpd_json(raw: str) -> list[Clone]:
    """Recebe o `jscpd-report.json` (versão pinada) e devolve os clones."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise JscpdParseError(msg("jscpd.invalid_json")) from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("duplicates"), list):
        raise JscpdParseError(msg("jscpd.no_duplicates"))
    return [_clone(item) for item in payload["duplicates"]]


def _clone(item: Any) -> Clone:
    if not isinstance(item, dict):
        raise JscpdParseError(msg("jscpd.malformed"))
    first = _side(item, "firstFile")
    second = _side(item, "secondFile")
    try:
        lines = int(item["lines"])
        tokens = int(item["tokens"])
    except (KeyError, TypeError, ValueError) as exc:
        raise JscpdParseError(msg("jscpd.no_size")) from exc
    similarity = item.get("similarity")
    if similarity is not None:
        try:
            similarity = float(similarity)
        except (TypeError, ValueError) as exc:
            raise JscpdParseError(msg("jscpd.invalid_similarity")) from exc
    kind = item.get("kind")
    return Clone(
        first_file=first[0],
        first_start=first[1],
        first_end=first[2],
        second_file=second[0],
        second_start=second[1],
        second_end=second[2],
        lines=lines,
        tokens=tokens,
        similarity=similarity,
        kind=str(kind) if isinstance(kind, str) else "",
    )


def _side(item: dict[str, Any], key: str) -> tuple[str, int, int]:
    side = item.get(key)
    if not isinstance(side, dict):
        raise JscpdParseError(msg("jscpd.missing_side", key=key))
    name = side.get("name")
    if not isinstance(name, str) or not name:
        raise JscpdParseError(msg("jscpd.side_no_name", key=key))
    try:
        start = int(side["start"])
        end = int(side["end"])
    except (KeyError, TypeError, ValueError) as exc:
        raise JscpdParseError(msg("jscpd.side_no_lines", key=key)) from exc
    return name, start, end
