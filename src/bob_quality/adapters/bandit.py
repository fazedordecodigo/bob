from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bob_quality.messages import msg
from bob_quality.models import Finding, Severity

LABELS = ("HIGH", "MEDIUM", "LOW", "UNDEFINED")


class BanditParseError(Exception):
    """JSON do Bandit fora do contrato da versão pinada."""


def parse_bandit(stdout: str, root: Path) -> tuple[Finding, ...]:
    payload = _object(stdout)
    results = payload.get("results")
    if not isinstance(results, list):
        raise BanditParseError(msg("bandit.no_results"))
    found: list[Finding] = []
    for item in results:
        finding = _finding(item, root)
        if finding is not None:
            found.append(finding)
    return tuple(found)


def _object(stdout: str) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise BanditParseError(msg("bandit.invalid_json")) from exc
    if not isinstance(payload, dict):
        raise BanditParseError(msg("bandit.no_results"))
    return payload


def _finding(item: Any, root: Path) -> Finding | None:
    if not isinstance(item, dict):
        raise BanditParseError(msg("bandit.malformed"))
    rule = item.get("test_id")
    filename = item.get("filename")
    label = item.get("issue_severity")
    if not isinstance(rule, str) or not isinstance(filename, str) or not isinstance(label, str):
        raise BanditParseError(msg("bandit.malformed"))
    if label not in LABELS:
        raise BanditParseError(msg("bandit.malformed"))
    relative = _relative(filename, root)
    if relative is None:
        return None
    line, end_line = _span(item)
    return Finding(
        tool="bandit",
        rule=rule,
        file=relative,
        line=line,
        end_line=end_line,
        severity=Severity(label),
    )


def _span(item: dict[str, Any]) -> tuple[int, int]:
    try:
        line = int(item["line_number"])
    except (KeyError, TypeError, ValueError) as exc:
        raise BanditParseError(msg("bandit.malformed")) from exc
    raw = item.get("line_range", [line])
    if isinstance(raw, list) and raw:
        try:
            numbers = [int(number) for number in raw]
        except (TypeError, ValueError) as exc:
            raise BanditParseError(msg("bandit.malformed")) from exc
        return line, max([line, *numbers])
    if raw == []:
        return line, line
    raise BanditParseError(msg("bandit.malformed"))


def _relative(filename: str, root: Path) -> str | None:
    path = Path(filename)
    if not path.is_absolute() and ".." not in path.parts:
        text = path.as_posix().removeprefix("./")
        return text or None
    try:
        if path.is_absolute():
            relative = path.resolve().relative_to(root.resolve())
        else:
            relative = (root / path).resolve().relative_to(root.resolve())
    except ValueError:
        return None
    text = relative.as_posix()
    if text in {"", "."} or text.startswith("../"):
        return None
    return text
