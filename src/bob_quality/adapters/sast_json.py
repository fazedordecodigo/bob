import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bob_quality.adapters.paths import repo_relative
from bob_quality.messages import Text
from bob_quality.models import Finding, Severity


def parsed_results(
    stdout: str,
    error: type[Exception],
    invalid: Text,
    missing: Text,
    one: Callable[[Any], Finding | None],
) -> tuple[Finding, ...]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise error(invalid) from exc
    if not isinstance(payload, dict):
        raise error(missing)
    results = payload.get("results")
    if not isinstance(results, list):
        raise error(missing)
    found: list[Finding] = []
    for item in results:
        finding = one(item)
        if finding is not None:
            found.append(finding)
    return tuple(found)


def at(
    tool: str,
    rule: str,
    filename: str,
    root: Path,
    line: int,
    end_line: int,
    label: str,
) -> Finding | None:
    relative = repo_relative(filename, root)
    if relative is None:
        return None
    return Finding(
        tool=tool,
        rule=rule,
        file=relative,
        line=line,
        end_line=end_line,
        severity=Severity(label),
    )
