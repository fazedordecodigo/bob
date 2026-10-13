from __future__ import annotations

from pathlib import Path
from typing import Any

from bob_quality.adapters.sast_json import at, parsed_results
from bob_quality.messages import msg
from bob_quality.models import Finding

LABELS = ("CRITICAL", "HIGH", "ERROR", "MEDIUM", "WARNING", "LOW", "INFO")
_DROPPED = frozenset({"EXPERIMENT", "INVENTORY"})


class SemgrepParseError(Exception):
    """JSON do Semgrep fora do contrato da versão pinada."""


def parse_semgrep(stdout: str, root: Path) -> tuple[Finding, ...]:
    return parsed_results(
        stdout,
        SemgrepParseError,
        msg("semgrep.invalid_json"),
        msg("semgrep.no_results"),
        lambda item: _finding(item, root),
    )


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
    line, end_line = _span(item)
    return at("semgrep", rule, filename, root, line, end_line, label)


def _span(item: dict[str, Any]) -> tuple[int, int]:
    try:
        line = int(item["start"]["line"])
        end_line = int(item["end"]["line"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SemgrepParseError(msg("semgrep.malformed")) from exc
    return line, end_line

