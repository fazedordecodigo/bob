from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from bob_quality.messages import DEFAULT_LANGUAGE, LANGUAGES, Language, msg

DEFAULT_EXCLUDE = ["tests", "node_modules", "dist"]


@dataclass
class Config:
    base: str = "origin/main"
    languages: list[str] = field(default_factory=lambda: ["python"])
    include: list[str] = field(default_factory=lambda: ["src"])
    exclude: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDE))
    max_crap: float = 10.0
    crap_scope: str = "changed"
    python_deps_config: str = ".importlinter"
    typescript_deps_config: str = ".dependency-cruiser.cjs"
    min_tokens: int = 50
    language: Language | None = None


class ConfigError(Exception):
    """YAML ausente com --config explícito, ou inválido."""


def load_config(path: Path | None, cwd: Path) -> Config:
    config_path = path if path is not None else cwd / "bob.yaml"
    if not config_path.is_file():
        if path is not None:
            raise ConfigError(msg("config.not_found", path=config_path))
        return Config()
    raw = yaml.safe_load(config_path.read_text()) or {}
    if not isinstance(raw, dict):
        raise ConfigError(msg("config.not_mapping"))
    return _from_dict(raw)


def configured_language(path: Path | None, cwd: Path) -> Language | None:
    config_path = path if path is not None else cwd / "bob.yaml"
    if not config_path.is_file():
        return None
    raw = yaml.safe_load(config_path.read_text()) or {}
    if not isinstance(raw, dict):
        return None
    try:
        return _language(raw.get("language"))
    except ConfigError:
        return None


def resolve_language(
    flag: str | None, env: str | None, configured: Language | None
) -> Language:
    for candidate in (flag, env):
        if candidate is not None and candidate != "":
            return parse_language(candidate)
    if configured is None:
        return DEFAULT_LANGUAGE
    return configured


def parse_language(value: str) -> Language:
    for language in LANGUAGES:
        if value == language:
            return language
    raise ConfigError(msg("config.invalid_language", value=value))


def _from_dict(raw: dict[str, Any]) -> Config:
    paths = raw.get("paths") or {}
    crap = raw.get("crap") or {}
    include = paths.get("include") or ["src"]
    exclude = paths.get("exclude") or list(DEFAULT_EXCLUDE)
    python_deps, typescript_deps = _dependency_paths(raw)
    return Config(
        base=str(raw.get("base") or "origin/main"),
        languages=list(raw.get("languages") or ["python"]),
        include=list(include),
        exclude=list(exclude),
        max_crap=float(crap.get("max_per_function", 10)),
        crap_scope=str(crap.get("scope") or "changed"),
        python_deps_config=python_deps,
        typescript_deps_config=typescript_deps,
        min_tokens=_min_tokens(raw.get("duplication")),
        language=_language(raw.get("language")),
    )


def _language(raw: Any) -> Language | None:
    if raw is None or raw == "":
        return None
    return parse_language(str(raw))


def _dependency_paths(raw: dict[str, Any]) -> tuple[str, str]:
    dependencies = raw.get("dependencies") or {}
    python = str(dependencies.get("python") or ".importlinter")
    typescript = str(dependencies.get("typescript") or ".dependency-cruiser.cjs")
    return python, typescript


def _min_tokens(duplication: Any) -> int:
    if not duplication:
        return 50
    if not isinstance(duplication, dict):
        raise ConfigError(msg("config.duplication_not_mapping"))
    try:
        return int(duplication.get("min_tokens", 50))
    except (TypeError, ValueError) as exc:
        raise ConfigError(msg("config.min_tokens_not_integer")) from exc
