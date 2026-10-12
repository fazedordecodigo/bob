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
    raw = _read_mapping(config_path, cwd)
    label = _config_label(config_path, cwd)
    parsed = _parsed(raw, label)
    parsed.min_tokens = _min_tokens(raw.get("duplication"))
    parsed.language = _language(raw.get("language"))
    return parsed


def reject_config_types(path: Path | None, cwd: Path) -> None:
    config_path = path if path is not None else cwd / "bob.yaml"
    if not config_path.is_file():
        return
    raw = _read_mapping(config_path, cwd)
    _parsed(raw, _config_label(config_path, cwd))


def configured_language(path: Path | None, cwd: Path) -> Language | None:
    config_path = path if path is not None else cwd / "bob.yaml"
    if not config_path.is_file():
        return None
    return _language(_read_mapping(config_path, cwd).get("language"))


def resolve_language(
    flag: str | None, env: str | None, configured: Language | None
) -> Language:
    if flag is not None:
        return parse_language(flag)
    if env is not None:
        return parse_language(env)
    if configured is None:
        return DEFAULT_LANGUAGE
    return configured


def parse_language(value: str) -> Language:
    for language in LANGUAGES:
        if value == language:
            return language
    shown = '""' if value == "" else value
    raise ConfigError(msg("config.invalid_language", value=shown))


def _read_mapping(config_path: Path, cwd: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(config_path.read_text())
    except yaml.YAMLError as exc:
        detail = str(exc).strip().splitlines()[0].strip()
        raise ConfigError(
            msg("config.invalid_yaml", path=_config_label(config_path, cwd), detail=detail)
        ) from exc
    raw = loaded or {}
    if not isinstance(raw, dict):
        raise ConfigError(msg("config.not_mapping"))
    return raw


def _config_label(config_path: Path, cwd: Path) -> str:
    if config_path == cwd / "bob.yaml":
        return "bob.yaml"
    return config_path.as_posix()


def _parsed(raw: dict[str, Any], label: str) -> Config:
    paths = _mapping(raw, "paths", label)
    crap = _mapping(raw, "crap", label)
    dependencies = _mapping(raw, "dependencies", label)
    return Config(
        base=_string(raw, "base", label) or "origin/main",
        languages=_string_list(raw, "languages", label) or ["python"],
        include=_string_list(paths, "include", label, "paths.include") or ["src"],
        exclude=_string_list(paths, "exclude", label, "paths.exclude") or list(DEFAULT_EXCLUDE),
        max_crap=_number(crap, "max_per_function", label, "crap.max_per_function", 10.0),
        crap_scope=_string(crap, "scope", label, "crap.scope") or "changed",
        python_deps_config=_string(dependencies, "python", label, "dependencies.python")
        or ".importlinter",
        typescript_deps_config=_string(
            dependencies, "typescript", label, "dependencies.typescript"
        )
        or ".dependency-cruiser.cjs",
    )


def _language(raw: Any) -> Language | None:
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        raise ConfigError(msg("config.invalid_language", value=raw))
    return parse_language(raw)


def _mapping(raw: dict[str, Any], key: str, label: str) -> dict[str, Any]:
    if key not in raw or raw[key] is None:
        return {}
    value = raw[key]
    if not isinstance(value, dict):
        raise ConfigError(msg("config.key_mapping", path=label, key=key))
    return value


def _string(
    raw: dict[str, Any], key: str, label: str, dotted: str | None = None
) -> str | None:
    if key not in raw or raw[key] is None:
        return None
    value = raw[key]
    if not isinstance(value, str):
        raise ConfigError(msg("config.key_string", path=label, key=dotted or key))
    return value


def _string_list(
    raw: dict[str, Any], key: str, label: str, dotted: str | None = None
) -> list[str] | None:
    if key not in raw or raw[key] is None:
        return None
    value = raw[key]
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ConfigError(msg("config.key_string_list", path=label, key=dotted or key))
    return value


def _number(
    raw: dict[str, Any], key: str, label: str, dotted: str, default: float
) -> float:
    if key not in raw or raw[key] is None:
        return default
    value = raw[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(msg("config.key_number", path=label, key=dotted))
    return float(value)


def _min_tokens(duplication: Any) -> int:
    if not duplication:
        return 50
    if not isinstance(duplication, dict):
        raise ConfigError(msg("config.duplication_not_mapping"))
    try:
        return int(duplication.get("min_tokens", 50))
    except (TypeError, ValueError) as exc:
        raise ConfigError(msg("config.min_tokens_not_integer")) from exc
