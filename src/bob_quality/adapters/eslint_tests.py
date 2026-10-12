"""Adaptador eslint: JSON `--format json` → hits `jest/` e `vitest/`."""

from __future__ import annotations

import json
from dataclasses import dataclass

from bob_quality.messages import msg

_PREFIXES = ("jest/", "vitest/")


class EslintParseError(Exception):
    """A saída não é a lista JSON deste gate."""


@dataclass(frozen=True)
class EslintHit:
    file: str
    line: int
    rule: str


def parse_eslint_json(raw: str) -> tuple[EslintHit, ...]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EslintParseError(msg("test_smells.eslint_unparsed")) from exc
    if not isinstance(payload, list):
        raise EslintParseError(msg("test_smells.eslint_unparsed"))
    hits: list[EslintHit] = []
    for item in payload:
        hits.extend(_file_hits(item))
    return tuple(hits)


def _file_hits(item: object) -> list[EslintHit]:
    if not isinstance(item, dict):
        return []
    path = item.get("filePath")
    messages = item.get("messages")
    if not isinstance(path, str) or not isinstance(messages, list):
        return []
    found: list[EslintHit] = []
    for message in messages:
        hit = _hit(path, message)
        if hit is not None:
            found.append(hit)
    return found


def _hit(path: str, message: object) -> EslintHit | None:
    if not isinstance(message, dict):
        return None
    rule = message.get("ruleId")
    line = message.get("line")
    if not isinstance(rule, str) or not rule.startswith(_PREFIXES):
        return None
    if isinstance(line, bool) or not isinstance(line, int) or line < 1:
        return None
    return EslintHit(path, line, rule)
