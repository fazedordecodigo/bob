"""Carrega `bob.yaml`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Config:
    base: str = "origin/main"
    languages: list[str] = field(default_factory=lambda: ["python"])
    include: list[str] = field(default_factory=lambda: ["src"])
    exclude: list[str] = field(default_factory=lambda: ["tests"])
    max_crap: float = 10.0
    crap_scope: str = "changed"
    min_tokens: int = 50


class ConfigError(Exception):
    """YAML ausente com --config explícito, ou inválido."""


def load_config(path: Path | None, cwd: Path) -> Config:
    config_path = path if path is not None else cwd / "bob.yaml"
    if not config_path.is_file():
        if path is not None:
            raise ConfigError(f"arquivo de configuração não encontrado: {config_path}")
        return Config()
    raw = yaml.safe_load(config_path.read_text()) or {}
    if not isinstance(raw, dict):
        raise ConfigError("bob.yaml deve ser um mapeamento")
    return _from_dict(raw)


def _from_dict(raw: dict[str, Any]) -> Config:
    paths = raw.get("paths") or {}
    crap = raw.get("crap") or {}
    duplication = raw.get("duplication") or {}
    if not isinstance(duplication, dict):
        raise ConfigError("duplication deve ser um mapeamento")
    include = paths.get("include") or ["src"]
    exclude = paths.get("exclude") or ["tests"]
    try:
        min_tokens = int(duplication.get("min_tokens", 50))
    except (TypeError, ValueError) as exc:
        raise ConfigError("duplication.min_tokens deve ser um inteiro") from exc
    return Config(
        base=str(raw.get("base") or "origin/main"),
        languages=list(raw.get("languages") or ["python"]),
        include=list(include),
        exclude=list(exclude),
        max_crap=float(crap.get("max_per_function", 10)),
        crap_scope=str(crap.get("scope") or "changed"),
        min_tokens=min_tokens,
    )
