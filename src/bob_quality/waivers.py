"""Waivers versionados em `.bob/waivers.yaml`."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from bob_quality.messages import Message, msg
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


def normalize_reason(reason: str | None) -> str:
    if reason is None or "\n" in reason or "\r" in reason:
        raise WaiverError(msg("waiver.no_reason"))
    text = reason.strip()
    if not text:
        raise WaiverError(msg("waiver.no_reason"))
    return text


def load_waivers(cwd: Path) -> list[Waiver]:
    path = waivers_path(cwd)
    if not path.is_file():
        return []
    return [_waiver_from_entry(entry) for entry in _waiver_entries(path)]


def _waiver_entries(path: Path) -> list[object]:
    raw = yaml.safe_load(path.read_text()) or {}
    if not isinstance(raw, dict):
        raise WaiverError(msg("waiver.file_not_mapping"))
    entries = raw.get("waivers") or []
    if not isinstance(entries, list):
        raise WaiverError(msg("waiver.list_required"))
    return entries


def _waiver_from_entry(entry: object) -> Waiver:
    if not isinstance(entry, dict):
        raise WaiverError(msg("waiver.invalid"))
    reason_raw = entry.get("reason")
    reason = normalize_reason(reason_raw if isinstance(reason_raw, str) else None)
    return Waiver(
        id=_required_text(entry, "id", msg("waiver.no_target")),
        reason=reason,
        author=_required_text(entry, "author", msg("waiver.no_author")),
        date=_required_text(entry, "date", msg("waiver.no_date")),
    )


def _required_text(entry: dict[str, object], key: str, message: Message) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise WaiverError(message)
    return value.strip()


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
