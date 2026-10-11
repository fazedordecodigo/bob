"""Carrega `bob.yaml`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_EXCLUDE = ["tests", "node_modules", "dist"]


@dataclass
class Config:
    base: str = "origin/main"
    languages: list[str] = field(default_factory=lambda: ["python"])
    include: list[str] = field(default_factory=lambda: ["src"])
    exclude: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDE))
    max_crap: float = 10.0
    crap_scope: str = "changed"


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
    include = paths.get("include") or ["src"]
    exclude = paths.get("exclude") or list(DEFAULT_EXCLUDE)
    return Config(
        base=str(raw.get("base") or "origin/main"),
        languages=list(raw.get("languages") or ["python"]),
        include=list(include),
        exclude=list(exclude),
        max_crap=float(crap.get("max_per_function", 10)),
        crap_scope=str(crap.get("scope") or "changed"),
    )
