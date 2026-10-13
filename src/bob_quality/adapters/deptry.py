from __future__ import annotations

import json
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from bob_quality.adapters.runner import (
    ProcessExit,
    ProcessFault,
    Runner,
    banner_version,
    default_runner,
)
from bob_quality.messages import Text, msg

_VERSION = re.compile(r"\d+\.\d+(?:\.\d+)?")
_IGNORE = "DEP002,DEP004,DEP005"


@dataclass(frozen=True)
class DeptryViolation:
    code: str
    module: str
    file: str
    line: int | None


@dataclass(frozen=True)
class DeptryRun:
    version: str
    violations: tuple[DeptryViolation, ...]


@dataclass(frozen=True)
class DeptryCapture:
    exit_code: int | None
    parsed: bool
    document: DeptryRun | None
    detail: Text


def parse_deptry_json(raw: str) -> tuple[DeptryViolation, ...] | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list):
        return None
    violations: list[DeptryViolation] = []
    for item in payload:
        parsed = _violation(item)
        if parsed is None:
            return None
        violations.append(parsed)
    return tuple(violations)


def run_deptry(
    cwd: Path,
    include: tuple[str, ...],
    timeout_seconds: int,
    runner: Runner = default_runner,
) -> DeptryCapture:
    version = _version(cwd, timeout_seconds, runner)
    with tempfile.TemporaryDirectory(prefix="bob-deptry-") as tmp:
        out = Path(tmp) / "deptry.json"
        args = [
            sys.executable,
            "-m",
            "deptry",
            *include,
            "--json-output",
            str(out),
            "--ignore",
            _IGNORE,
        ]
        result = runner(args, cwd, timeout_seconds)
        if isinstance(result, ProcessFault):
            return DeptryCapture(None, False, None, result.detail)
        violations = _read(out)
        if violations is None:
            return DeptryCapture(result.code, False, None, msg("supply.deptry_json"))
        return DeptryCapture(
            result.code,
            True,
            DeptryRun(version, violations),
            "",
        )


def _version(cwd: Path, timeout: int, runner: Runner) -> str:
    result = runner([sys.executable, "-m", "deptry", "--version"], cwd, timeout)
    if not isinstance(result, ProcessExit):
        return "unknown"
    return banner_version(result, _VERSION)


def _read(path: Path) -> tuple[DeptryViolation, ...] | None:
    if not path.is_file():
        return None
    return parse_deptry_json(path.read_text())


def _violation(item: object) -> DeptryViolation | None:
    if not isinstance(item, dict):
        return None
    error = item.get("error")
    location = item.get("location")
    module = item.get("module")
    if not isinstance(error, dict) or not isinstance(location, dict):
        return None
    if not isinstance(module, str) or not isinstance(error.get("code"), str):
        return None
    file = location.get("file")
    if not isinstance(file, str):
        return None
    return DeptryViolation(error["code"], module, file, _line(location.get("line")))


def _line(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None
