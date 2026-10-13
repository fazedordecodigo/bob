from __future__ import annotations

import json
import re
from collections.abc import Mapping
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
from bob_quality.npm_tools import npm_prefix
from bob_quality.tools import ToolError

_VERSION = re.compile(r"\d+\.\d+(?:\.\d+)?")
_SKIP_KEYS = frozenset({"file", "owners"})


@dataclass(frozen=True)
class KnipHit:
    name: str
    line: int | None
    column: int | None


@dataclass(frozen=True)
class KnipFile:
    file: str
    by_type: Mapping[str, tuple[KnipHit, ...]]


@dataclass(frozen=True)
class KnipDocument:
    version: str
    files: tuple[KnipFile, ...]


@dataclass(frozen=True)
class KnipCapture:
    exit_code: int | None
    parsed: bool
    document: KnipDocument | None
    detail: Text


def parse_knip_json(raw: str) -> tuple[KnipFile, ...] | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("issues"), list):
        return None
    files: list[KnipFile] = []
    for item in payload["issues"]:
        parsed = _file(item)
        if parsed is None:
            return None
        files.append(parsed)
    return tuple(files)


def run_knip(
    cwd: Path,
    timeout_seconds: int,
    runner: Runner = default_runner,
) -> KnipCapture:
    try:
        prefix = str(npm_prefix())
    except ToolError as exc:
        detail = exc.args[0] if exc.args else str(exc)
        return KnipCapture(None, False, None, detail)
    version = _version(cwd, timeout_seconds, runner, prefix)
    args = ["npx", "--no-install", "--prefix", prefix, "knip", "--reporter", "json"]
    result = runner(args, cwd, timeout_seconds)
    if isinstance(result, ProcessFault):
        return KnipCapture(None, False, None, result.detail)
    files = parse_knip_json(result.stdout)
    if files is None:
        return KnipCapture(result.code, False, None, msg("supply.knip_json"))
    return KnipCapture(result.code, True, KnipDocument(version, files), "")


def _version(cwd: Path, timeout: int, runner: Runner, prefix: str) -> str:
    args = ["npx", "--no-install", "--prefix", prefix, "knip", "--version"]
    result = runner(args, cwd, timeout)
    if not isinstance(result, ProcessExit):
        return "unknown"
    return banner_version(result, _VERSION)


def _file(item: object) -> KnipFile | None:
    if not isinstance(item, dict) or not isinstance(item.get("file"), str):
        return None
    by_type: dict[str, tuple[KnipHit, ...]] = {}
    for key, value in item.items():
        if key in _SKIP_KEYS:
            continue
        hits = _hits(value)
        if hits is None:
            return None
        by_type[key] = hits
    return KnipFile(item["file"], by_type)


def _hits(value: object) -> tuple[KnipHit, ...] | None:
    hits: list[KnipHit] = []
    if not _collect(value, hits):
        return None
    return tuple(hits)


def _collect(value: object, hits: list[KnipHit]) -> bool:
    if not isinstance(value, list):
        return False
    for item in value:
        if isinstance(item, list):
            if not _collect(item, hits):
                return False
            continue
        parsed = _hit(item)
        if parsed is None:
            return False
        hits.append(parsed)
    return True


def _hit(item: object) -> KnipHit | None:
    if not isinstance(item, dict) or not isinstance(item.get("name"), str):
        return None
    return KnipHit(item["name"], _number(item.get("line")), _number(item.get("col")))


def _number(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None
