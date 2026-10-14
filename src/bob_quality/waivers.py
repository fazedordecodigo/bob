"""Waivers versionados em `.bob/waivers.yaml`."""

from __future__ import annotations

import math
import os
import subprocess
from collections import Counter
from dataclasses import dataclass, fields, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

import yaml

from bob_quality.messages import msg
from bob_quality.models import Mutant
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


def add_waiver(
    cwd: Path,
    target: str,
    reason: str | None,
    known: frozenset[str],
    untested: frozenset[str] = frozenset(),
) -> Waiver:
    """`known` são os alvos dos sobreviventes do último relatório de mutação.

    `untested` são os `arquivo::função` sem teste.
    """
    text = normalize_reason(reason)
    wanted = target.strip()
    if not wanted:
        raise WaiverError(msg("waiver.no_target"))
    if wanted not in known and wanted in untested:
        raise WaiverError(msg("waiver.not_a_test", target=wanted))
    if wanted not in known:
        raise WaiverError(msg("waiver.unknown_target", target=wanted))
    waiver = Waiver(
        id=wanted,
        reason=text,
        author=_author(cwd),
        date=datetime.now(timezone.utc).date().isoformat(),
    )
    write_waivers(cwd, [item for item in load_waivers(cwd) if item.id != wanted] + [waiver])
    return waiver


class _WaiverDumper(yaml.SafeDumper):
    """A ordem dos campos é a do dataclass. O dump padrão do PyYAML ordenaria as chaves."""


def _represent_ordered_dict(dumper: yaml.SafeDumper, data: dict[str, object]) -> yaml.Node:
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())


_WaiverDumper.add_representer(dict, _represent_ordered_dict)


def write_waivers(cwd: Path, waivers: list[Waiver]) -> None:
    """O único escritor do `.bob/waivers.yaml`. A largura infinita deixa um id longo numa linha."""
    path = waivers_path(cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"waivers": [item.as_dict() for item in waivers]}
    path.write_text(yaml.dump(payload, Dumper=_WaiverDumper, allow_unicode=True, width=math.inf))


class SurvivorTargets(NamedTuple):
    """Os dois ids de waiver que cobrem um sobrevivente."""

    function: str
    """`arquivo::função`. Cobre todo sobrevivente da função."""

    exact: str | None
    """`arquivo::função::<descrição>`. None quando a descrição não separa este sobrevivente."""


def survivor_targets(mutants: list[Mutant]) -> dict[str, SurvivorTargets]:
    """Alvos de cada sobrevivente, pelo id do mutante.

    Só sobrevivente com arquivo tem entrada. A unicidade da descrição é julgada dentro da função,
    então `mutants` traz todos os sobreviventes de cada função que toca.
    """
    survivors = [item for item in mutants if item.status == "survived" and item.file]
    text = {item.id: item.operator.strip() for item in survivors}
    count = Counter((item.file, item.function, text[item.id]) for item in survivors)
    targets: dict[str, SurvivorTargets] = {}
    for item in survivors:
        function = f"{item.file}::{item.function}"
        unique = text[item.id] and count[(item.file, item.function, text[item.id])] == 1
        exact = f"{function}::{text[item.id]}" if unique else None
        targets[item.id] = SurvivorTargets(function, exact)
    return targets


def apply_waivers(mutants: list[Mutant], waivers: list[Waiver]) -> list[Mutant]:
    targets = survivor_targets(mutants)
    return [
        replace(item, waiver=_matching_reason(targets.get(item.id), waivers)) for item in mutants
    ]


def _matching_reason(targets: SurvivorTargets | None, waivers: list[Waiver]) -> str | None:
    """Um id prefixado de outro gate (ADR 0005) nunca começa com o caminho do arquivo."""
    if targets is None:
        return None
    keys = {targets.function, targets.exact}
    return next((item.reason for item in waivers if item.id in keys), None)


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
