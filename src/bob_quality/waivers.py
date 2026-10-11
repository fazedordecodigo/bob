"""Waivers versionados em `.bob/waivers.yaml`."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

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
        raise WaiverError("waiver sem motivo: informe --reason com uma linha")
    text = reason.strip()
    if not text:
        raise WaiverError("waiver sem motivo: informe --reason com uma linha")
    return text


def load_waivers(cwd: Path) -> list[Waiver]:
    path = waivers_path(cwd)
    if not path.is_file():
        return []
    raw = yaml.safe_load(path.read_text()) or {}
    if not isinstance(raw, dict):
        raise WaiverError("waivers.yaml deve ser um mapeamento")
    entries = raw.get("waivers") or []
    if not isinstance(entries, list):
        raise WaiverError("waivers.yaml: 'waivers' deve ser uma lista")
    loaded: list[Waiver] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise WaiverError("waiver inválido")
        reason = normalize_reason(entry.get("reason") if isinstance(entry.get("reason"), str) else None)
        target = entry.get("id")
        author = entry.get("author")
        date = entry.get("date")
        if not isinstance(target, str) or not target.strip():
            raise WaiverError("waiver sem alvo")
        if not isinstance(author, str) or not author.strip():
            raise WaiverError("waiver sem autor")
        if not isinstance(date, str) or not date.strip():
            raise WaiverError("waiver sem data")
        loaded.append(
            Waiver(
                id=target.strip(),
                reason=reason,
                author=author.strip(),
                date=date.strip(),
            )
        )
    return loaded


def add_waiver(cwd: Path, target: str, reason: str | None) -> Waiver:
    text = normalize_reason(reason)
    if not target.strip():
        raise WaiverError("waiver sem alvo")
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
