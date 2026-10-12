from __future__ import annotations

import json
from typing import Any

from bob_quality.core import unique_violations
from bob_quality.messages import Text, msg
from bob_quality.models import DepViolation

_BLOCKING = {"error", "warn"}


class CruiserParseError(Exception):
    pass


def parse_dependency_cruiser(raw: str) -> list[DepViolation]:
    data = json.loads(raw)
    found: list[DepViolation] = []
    for item in _violation_items(data):
        found.extend(_violations_for(item))
    return unique_violations(found)


def _violation_items(data: object) -> list[object]:
    if not isinstance(data, dict):
        raise CruiserParseError(msg("deps.cruiser_no_list"))
    summary = data.get("summary")
    if isinstance(summary, dict) and isinstance(summary.get("violations"), list):
        return list(summary["violations"])
    violations = data.get("violations")
    if isinstance(violations, list):
        return list(violations)
    raise CruiserParseError(msg("deps.cruiser_no_list"))


def _violations_for(item: object) -> list[DepViolation]:
    if not isinstance(item, dict):
        return []
    rule_name, severity = _rule(item)
    if severity not in _BLOCKING:
        return []
    cycle = _cycle_edges(item.get("cycle"), rule_name)
    if cycle:
        return cycle
    origin = str(item.get("from") or "")
    destination = str(item.get("to") or "")
    if origin and destination:
        return [DepViolation(origin, destination, rule_name, False)]
    return []


def _rule(item: dict[str, Any]) -> tuple[Text, str]:
    rule = item.get("rule")
    if not isinstance(rule, dict):
        return msg("deps.unnamed"), "error"
    name = rule.get("name")
    shown: Text = str(name) if name else msg("deps.unnamed")
    return shown, str(rule.get("severity") or "error")


def _cycle_edges(cycle: object, rule: Text) -> list[DepViolation]:
    names = _cycle_names(cycle)
    if len(names) < 2:
        return []
    ring = [*names, names[0]]
    return [
        DepViolation(origin, destination, rule, False)
        for origin, destination in zip(names, ring[1:])
    ]


def _cycle_names(cycle: object) -> list[str]:
    if not isinstance(cycle, list):
        return []
    names: list[str] = []
    for step in cycle:
        name = _cycle_name(step)
        if name:
            names.append(name)
    return names


def _cycle_name(step: object) -> str:
    if isinstance(step, dict):
        return str(step.get("name") or "")
    if isinstance(step, str):
        return step
    return ""
