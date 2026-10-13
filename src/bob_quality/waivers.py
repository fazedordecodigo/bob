"""Waivers versionados em `.bob/waivers.yaml`."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from pathlib import Path

import yaml

from bob_quality.messages import msg
from bob_quality.models import Mutant, MutantStatus
from bob_quality.yaml_text import parse_yaml


class WaiverError(Exception):
    """Waiver sem motivo de uma linha, ou arquivo inválido."""


@dataclass(frozen=True)
class Waiver:
    id: str
    reason: str
    author: str
    date: str

    def as_dict(self) -> dict[str, str]:
        return {item.name: getattr(self, item.name) for item in fields(Waiver)}


_ENTRY_KEYS = frozenset(item.name for item in fields(Waiver))


def waivers_path(cwd: Path) -> Path:
    return cwd / ".bob" / "waivers.yaml"


def _one_line(text: str) -> bool:
    return "\n" not in text and "\r" not in text and text.strip() != ""


def normalize_reason(reason: str | None) -> str:
    if reason is None or not _one_line(reason):
        raise WaiverError(msg("waiver.no_reason"))
    return reason.strip()


_WAIVER_FILE = ".bob/waivers.yaml"
_TOP_LEVEL_KEYS = frozenset({"waivers"})


def load_waivers(cwd: Path) -> list[Waiver]:
    path = waivers_path(cwd)
    if not path.is_file():
        return []
    loaded: list[Waiver] = []
    seen: dict[str, int] = {}
    for index, entry in enumerate(_waiver_entries(path)):
        waiver = _waiver_from_entry(entry, index)
        earlier = seen.get(waiver.id)
        if earlier is not None:
            raise WaiverError(
                msg(
                    "waiver.duplicate_id",
                    path=_WAIVER_FILE,
                    field=_item_field(index, "id"),
                    earlier=_item_field(earlier, "id"),
                )
            )
        seen[waiver.id] = index
        loaded.append(waiver)
    return loaded


def reject_waiver_syntax(cwd: Path) -> None:
    if waivers_path(cwd).is_file():
        load_waivers(cwd)


def _waiver_entries(path: Path) -> list[object]:
    loaded = _load_yaml(path)
    if loaded is None:
        return []
    if not isinstance(loaded, dict):
        raise WaiverError(msg("waiver.file_not_mapping", path=_WAIVER_FILE))
    for key in loaded:
        if key not in _TOP_LEVEL_KEYS:
            raise WaiverError(msg("file.unknown_key", path=_WAIVER_FILE, key=key))
    if "waivers" not in loaded or loaded["waivers"] is None:
        return []
    entries = loaded["waivers"]
    if not isinstance(entries, list):
        raise WaiverError(msg("waiver.list_required", path=_WAIVER_FILE, field="waivers"))
    return entries


def _load_yaml(path: Path) -> object:
    try:
        return parse_yaml(path.read_text())
    except yaml.YAMLError as exc:
        detail = str(exc).strip().splitlines()[0].strip()
        raise WaiverError(
            msg("waiver.invalid_yaml", path=_WAIVER_FILE, detail=detail)
        ) from exc


def _waiver_from_entry(entry: object, index: int) -> Waiver:
    if not isinstance(entry, dict):
        raise WaiverError(
            msg("waiver.entry_mapping", path=_WAIVER_FILE, field=_item_field(index))
        )
    for key in entry:
        if key not in _ENTRY_KEYS:
            raise WaiverError(
                msg("file.unknown_key", path=_WAIVER_FILE, key=_item_field(index, key))
            )
    return Waiver(
        id=_required_text(entry, "id", index),
        reason=_reason_text(entry, index),
        author=_required_text(entry, "author", index),
        date=_required_text(entry, "date", index),
    )


def _reason_text(entry: dict[str, object], index: int) -> str:
    value = entry.get("reason")
    name = _item_field(index, "reason")
    if not isinstance(value, str):
        raise WaiverError(msg("waiver.field_string", path=_WAIVER_FILE, field=name))
    if not _one_line(value):
        raise WaiverError(msg("waiver.reason_line", path=_WAIVER_FILE, field=name))
    return value.strip()


def _required_text(entry: dict[str, object], key: str, index: int) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise WaiverError(
            msg("waiver.field_string", path=_WAIVER_FILE, field=_item_field(index, key))
        )
    return value.strip()


def _item_field(index: int, key: str | None = None) -> str:
    field = f"waivers[{index}]"
    if key is None:
        return field
    return f"{field}.{key}"


def add_waiver(cwd: Path, target: str, reason: str | None) -> Waiver:
    text = normalize_reason(reason)
    target_id = target.strip()
    if not target_id:
        raise WaiverError(msg("waiver.no_target"))
    _reject_orphan(cwd, target_id)
    waiver = Waiver(
        id=target_id,
        reason=text,
        author=_author(cwd),
        date=datetime.now(timezone.utc).date().isoformat(),
    )
    current = load_waivers(cwd)
    replaced = [item for item in current if item.id != waiver.id]
    replaced.append(waiver)
    path = waivers_path(cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"waivers": [item.as_dict() for item in replaced]}
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False))
    return waiver


def apply_waivers(mutants: list[Mutant], waivers: list[Waiver]) -> list[Mutant]:
    applied: list[Mutant] = []
    for mutant in mutants:
        reason = _matching_reason(mutant, waivers)
        if reason == mutant.waiver:
            applied.append(mutant)
            continue
        applied.append(
            Mutant(
                id=mutant.id,
                function=mutant.function,
                file=mutant.file,
                line=mutant.line,
                operator=mutant.operator,
                status=mutant.status,
                waiver=reason,
            )
        )
    return applied


def _matching_reason(mutant: Mutant, waivers: list[Waiver]) -> str | None:
    keys = _match_keys(mutant)
    for waiver in waivers:
        if waiver.id in keys:
            return waiver.reason
    return None


def _match_keys(mutant: Mutant) -> set[str]:
    return {
        mutant.id,
        mutant.function,
        f"{mutant.file}:{mutant.function}",
        f"{mutant.file}::{mutant.function}",
    }


_CACHE_NAME = ".bob/mutation-cache.json"
_STATUSES: frozenset[str] = frozenset({"killed", "survived", "timeout", "no_coverage"})


def _reject_orphan(cwd: Path, target: str) -> None:
    mutants = _cache_mutants(cwd)
    if mutants is None:
        return
    if any(item.status == "survived" and target in _match_keys(item) for item in mutants):
        return
    if any(item.status == "no_coverage" and target in _match_keys(item) for item in mutants):
        raise WaiverError(msg("waiver.not_a_test", target=target))
    raise WaiverError(msg("waiver.not_survivor", target=target))


def _cache_mutants(cwd: Path) -> list[Mutant] | None:
    path = cwd / _CACHE_NAME
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WaiverError(msg("mutate.cache_invalid", detail=str(exc))) from None
    if not isinstance(raw, dict):
        raise WaiverError(msg("mutate.cache_invalid", detail="not a mapping"))
    functions = raw.get("functions")
    if not isinstance(functions, dict):
        return []
    found: list[Mutant] = []
    for key, entry in functions.items():
        found.extend(_entry_mutants(entry, _label_from_key(key)))
    return found


def _label_from_key(key: object) -> tuple[str, str]:
    if not isinstance(key, str) or "::" not in key:
        return "", ""
    file, function = key.split("::", 1)
    return file, function


def _entry_mutants(entry: object, label: tuple[str, str] = ("", "")) -> list[Mutant]:
    if not isinstance(entry, dict):
        return []
    rows = entry.get("mutants")
    if not isinstance(rows, list):
        return []
    file, function = label
    found: list[Mutant] = []
    for row in rows:
        mutant = _row_mutant(row)
        if mutant is not None:
            found.append(_with_label(mutant, file, function))
    return found


def _with_label(mutant: Mutant, file: str, function: str) -> Mutant:
    if mutant.file and mutant.function:
        return mutant
    return Mutant(
        id=mutant.id,
        function=mutant.function or function,
        file=mutant.file or file,
        line=mutant.line,
        operator=mutant.operator,
        status=mutant.status,
        waiver=mutant.waiver,
    )


def _row_mutant(row: object) -> Mutant | None:
    if not isinstance(row, dict):
        return None
    mutant_id = row.get("id")
    status = row.get("status")
    if not isinstance(mutant_id, str) or not isinstance(status, str) or status not in _STATUSES:
        return None
    function = row.get("function")
    file = row.get("file")
    return Mutant(
        id=mutant_id,
        function=function if isinstance(function, str) else "",
        file=file if isinstance(file, str) else "",
        line=0,
        operator="",
        status=_status(status),
    )


def _status(value: str) -> MutantStatus:
    if value == "killed":
        return "killed"
    if value == "timeout":
        return "timeout"
    if value == "no_coverage":
        return "no_coverage"
    return "survived"


def _author(cwd: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "config", "user.name"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        completed = None
    if completed is not None and completed.stdout.strip():
        return completed.stdout.strip()
    return os.environ.get("USER") or "unknown"
