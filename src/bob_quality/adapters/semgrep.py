from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bob_quality.messages import msg
from bob_quality.models import Finding, Severity

LABELS = ("CRITICAL", "HIGH", "ERROR", "MEDIUM", "WARNING", "LOW", "INFO")
_DROPPED = frozenset({"EXPERIMENT", "INVENTORY"})


class SemgrepParseError(Exception):
    """JSON do Semgrep fora do contrato da versão pinada."""


def parse_semgrep(stdout: str, root: Path) -> tuple[Finding, ...]:
    payload = _object(stdout)
    results = payload.get("results")
    if not isinstance(results, list):
        raise SemgrepParseError(msg("semgrep.no_results"))
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
        raise SemgrepParseError(msg("semgrep.invalid_json")) from exc
    if not isinstance(payload, dict):
        raise SemgrepParseError(msg("semgrep.no_results"))
    return payload


def _finding(item: Any, root: Path) -> Finding | None:
    if not isinstance(item, dict):
        raise SemgrepParseError(msg("semgrep.malformed"))
    rule = item.get("check_id")
    filename = item.get("path")
    extra = item.get("extra")
    if not isinstance(rule, str) or not isinstance(filename, str) or not isinstance(extra, dict):
        raise SemgrepParseError(msg("semgrep.malformed"))
    label = extra.get("severity")
    if not isinstance(label, str):
        raise SemgrepParseError(msg("semgrep.malformed"))
    if label in _DROPPED:
        return None
    if label not in LABELS:
        raise SemgrepParseError(msg("semgrep.malformed"))
    relative = _relative(filename, root)
    if relative is None:
        return None
    line, end_line = _span(item)
    return Finding(
        tool="semgrep",
        rule=rule,
        file=relative,
        line=line,
        end_line=end_line,
        severity=Severity(label),
    )


def _span(item: dict[str, Any]) -> tuple[int, int]:
    try:
        line = int(item["start"]["line"])
        end_line = int(item["end"]["line"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SemgrepParseError(msg("semgrep.malformed")) from exc
    return line, end_line


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
