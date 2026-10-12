"""Waivers versionados em `.bob/waivers.yaml`."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from bob_quality.messages import msg
from bob_quality.models import Mutant


class WaiverError(Exception):
    """Waiver sem motivo de uma linha, ou arquivo inválido."""


@dataclass(frozen=True)
class Waiver:
    id: str
    reason: str
    author: str
    date: str

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "reason": self.reason,
            "author": self.author,
            "date": self.date,
        }


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
    return [
        _waiver_from_entry(entry, index)
        for index, entry in enumerate(_waiver_entries(path))
    ]


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
        return yaml.safe_load(path.read_text())
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
    if not target.strip():
        raise WaiverError(msg("waiver.no_target"))
    waiver = Waiver(
        id=target.strip(),
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
    keys = {
        mutant.id,
        mutant.function,
        f"{mutant.file}:{mutant.function}",
        f"{mutant.file}::{mutant.function}",
    }
    for waiver in waivers:
        if waiver.id in keys:
            return waiver.reason
    return None


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
