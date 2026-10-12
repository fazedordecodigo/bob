from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypeGuard

import yaml

from bob_quality.messages import DEFAULT_LANGUAGE, LANGUAGES, Language, msg

DEFAULT_EXCLUDE = ["tests", "node_modules", "dist"]

SourceLanguage = Literal["python", "typescript"]
CrapScope = Literal["changed", "all"]

SOURCE_LANGUAGES: tuple[SourceLanguage, ...] = ("python", "typescript")
CRAP_SCOPES: tuple[CrapScope, ...] = ("changed", "all")

_CheckKind = Literal[
    "string",
    "string_list",
    "mapping",
    "number",
    "finite",
    "gt",
    "integer",
    "at_least",
    "one_of",
    "language",
]


@dataclass(frozen=True)
class _Check:
    kind: _CheckKind
    bound: int | float | None = None
    choices: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind in {"gt", "at_least"}:
            bound = self.bound
            if isinstance(bound, bool) or not isinstance(bound, (int, float)):
                raise ValueError(self.kind)
        if self.kind == "one_of" and len(self.choices) != 2:
            raise ValueError(self.kind)


@dataclass(frozen=True)
class _Node:
    key: str
    attr: str | None
    checks: tuple[_Check, ...]
    children: tuple[_Node, ...] = ()
    empty_is_default: bool = False
    null_is_default: bool = True


_SCHEMA = _Node(
    key="",
    attr=None,
    checks=(_Check("mapping"),),
    children=(
        _Node("base", "base", (_Check("string"),), empty_is_default=True),
        _Node("language", "language", (_Check("language"),), empty_is_default=True),
        _Node(
            "languages",
            "languages",
            (_Check("string_list"), _Check("one_of", choices=SOURCE_LANGUAGES)),
            empty_is_default=True,
        ),
        _Node(
            "paths",
            None,
            (_Check("mapping"),),
            children=(
                _Node("include", "include", (_Check("string_list"),), empty_is_default=True),
                _Node("exclude", "exclude", (_Check("string_list"),), empty_is_default=True),
            ),
        ),
        _Node(
            "crap",
            None,
            (_Check("mapping"),),
            children=(
                _Node(
                    "max_per_function",
                    "max_crap",
                    (_Check("number"), _Check("finite"), _Check("gt", bound=0)),
                ),
                _Node(
                    "scope",
                    "crap_scope",
                    (_Check("string"), _Check("one_of", choices=CRAP_SCOPES)),
                    empty_is_default=True,
                ),
            ),
        ),
        _Node(
            "duplication",
            None,
            (_Check("mapping"),),
            children=(
                _Node(
                    "min_tokens",
                    "min_tokens",
                    (_Check("integer"), _Check("at_least", bound=0)),
                    null_is_default=False,
                ),
            ),
        ),
        _Node(
            "dependencies",
            None,
            (_Check("mapping"),),
            children=(
                _Node("python", "python_deps_config", (_Check("string"),), empty_is_default=True),
                _Node(
                    "typescript",
                    "typescript_deps_config",
                    (_Check("string"),),
                    empty_is_default=True,
                ),
            ),
        ),
    ),
)


@dataclass(frozen=True)
class Config:
    """max_crap é finito e maior que 0. min_tokens é um int >= 0.

    crap_scope é changed ou all. Cada item de languages é python ou typescript.
    Um gate confia nisso.
    """

    base: str = "origin/main"
    languages: tuple[SourceLanguage, ...] = ("python",)
    include: tuple[str, ...] = ("src",)
    exclude: tuple[str, ...] = tuple(DEFAULT_EXCLUDE)
    max_crap: float = 10.0
    crap_scope: CrapScope = "changed"
    python_deps_config: str = ".importlinter"
    typescript_deps_config: str = ".dependency-cruiser.cjs"
    min_tokens: int = 50
    language: Language | None = None

    def __post_init__(self) -> None:
        for name in ("languages", "include", "exclude"):
            value = getattr(self, name)
            if isinstance(value, list):
                object.__setattr__(self, name, tuple(value))
        _guard(self)


class ConfigError(Exception):
    """YAML ausente com --config explícito, ou inválido."""


def load_config(path: Path | None, cwd: Path) -> Config:
    config_path = path if path is not None else cwd / "bob.yaml"
    if not config_path.is_file():
        if path is not None:
            raise ConfigError(msg("config.not_found", path=config_path))
        return Config()
    return _config_from_file(config_path, cwd)


def reject_config_types(path: Path | None, cwd: Path) -> None:
    config_path = path if path is not None else cwd / "bob.yaml"
    if not config_path.is_file():
        return
    _config_from_file(config_path, cwd)


def configured_language(path: Path | None, cwd: Path) -> Language | None:
    config_path = path if path is not None else cwd / "bob.yaml"
    if not config_path.is_file():
        return None
    raw = _read_mapping(config_path, cwd)
    node = _child(_SCHEMA, "language")
    if "language" not in raw or raw["language"] is None:
        return None
    value = raw["language"]
    if node.empty_is_default and _empty(node, value):
        return None
    return _as_language(_checked(node, value, _config_label(config_path, cwd), node.key))


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


def _config_from_file(config_path: Path, cwd: Path) -> Config:
    raw = _read_mapping(config_path, cwd)
    values = _read_node(_SCHEMA, raw, _config_label(config_path, cwd), "")
    return Config(**values)


def _read_mapping(config_path: Path, cwd: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(config_path.read_text())
    except yaml.YAMLError as exc:
        detail = str(exc).strip().splitlines()[0].strip()
        raise ConfigError(
            msg("config.invalid_yaml", path=_config_label(config_path, cwd), detail=detail)
        ) from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ConfigError(msg("config.not_mapping"))
    return loaded


def _config_label(config_path: Path, cwd: Path) -> str:
    if config_path == cwd / "bob.yaml":
        return "bob.yaml"
    return config_path.as_posix()


def _read_node(node: _Node, raw: dict[str, Any], label: str, prefix: str) -> dict[str, object]:
    allowed = {child.key for child in node.children}
    for key in raw:
        if key not in allowed:
            dotted = key if prefix == "" else f"{prefix}.{key}"
            raise ConfigError(msg("file.unknown_key", path=label, key=dotted))
    values: dict[str, object] = {}
    for child in node.children:
        dotted = child.key if prefix == "" else f"{prefix}.{child.key}"
        if child.key not in raw:
            continue
        value = raw[child.key]
        if value is None and child.null_is_default:
            continue
        if child.empty_is_default and _empty(child, value):
            continue
        if child.children:
            if not isinstance(value, dict):
                raise ConfigError(msg("config.key_mapping", path=label, key=dotted))
            values.update(_read_node(child, value, label, dotted))
            continue
        attr = child.attr
        if attr is None:
            raise ValueError(child.key)
        values[attr] = _checked(child, value, label, dotted)
    return values


def _checked(child: _Node, value: object, label: str, dotted: str) -> object:
    for check in child.checks:
        if check.kind == "one_of" and _has(child, "string_list"):
            if not _string_items(value):
                raise ConfigError(msg("config.key_string_list", path=label, key=dotted))
            for index, item in enumerate(value):
                if item not in check.choices:
                    raise ConfigError(
                        msg(
                            "config.key_one_of",
                            path=label,
                            key=f"{dotted}[{index}]",
                            left=check.choices[0],
                            right=check.choices[1],
                        )
                    )
            continue
        failure = _failure(check, value)
        if failure is None:
            continue
        key, params = failure
        if key == "config.invalid_language":
            raise ConfigError(msg(key, **params))
        raise ConfigError(msg(key, path=label, key=dotted, **params))
    if _has(child, "number") and _real_number(value):
        return float(value)
    if _has(child, "string_list") and _string_items(value):
        return tuple(value)
    if _has(child, "language"):
        if not isinstance(value, str) or value == "":
            return None
        return value
    return value


def _failure(check: _Check, value: object) -> tuple[str, dict[str, object]] | None:
    kind = check.kind
    if kind == "string":
        if not isinstance(value, str):
            return ("config.key_string", {})
        return None
    if kind == "string_list":
        if not _string_items(value):
            return ("config.key_string_list", {})
        return None
    if kind == "number":
        if not _real_number(value):
            return ("config.key_number", {})
        return None
    if kind == "finite":
        if not _real_number(value) or not math.isfinite(value):
            return ("config.key_finite", {})
        return None
    if kind == "gt":
        bound = _required_bound(check)
        if not _real_number(value) or not value > bound:
            return ("config.key_greater_than", {"bound": bound})
        return None
    if kind == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return ("config.key_integer", {})
        return None
    if kind == "at_least":
        bound = _required_bound(check)
        if not isinstance(value, int) or isinstance(value, bool) or value < bound:
            return ("config.key_at_least", {"bound": bound})
        return None
    if kind == "one_of":
        if value not in check.choices:
            return (
                "config.key_one_of",
                {"left": check.choices[0], "right": check.choices[1]},
            )
        return None
    if kind == "language":
        if value is None or value == "":
            return None
        if not isinstance(value, str) or value not in LANGUAGES:
            shown = '""' if value == "" else value
            return ("config.invalid_language", {"value": shown})
        return None
    if kind == "mapping":
        return None
    raise ValueError(kind)


def _guard(config: Config) -> None:
    for node in _leaves(_SCHEMA):
        attr = node.attr
        if attr is None:
            continue
        _guard_value(node, getattr(config, attr), attr)


def _guard_value(node: _Node, value: object, attr: str) -> None:
    for check in node.checks:
        if check.kind == "one_of" and _has(node, "string_list"):
            if not _string_items(value):
                raise ValueError(attr)
            for item in value:
                if item not in check.choices:
                    raise ValueError(attr)
            continue
        if _failure(check, value) is not None:
            raise ValueError(attr)


def _leaves(node: _Node):
    if not node.children:
        yield node
        return
    for child in node.children:
        yield from _leaves(child)


def _empty(node: _Node, value: object) -> bool:
    if _has(node, "string_list"):
        return value == []
    return value == ""


def _has(node: _Node, kind: _CheckKind) -> bool:
    return any(check.kind == kind for check in node.checks)


def _child(node: _Node, key: str) -> _Node:
    for child in node.children:
        if child.key == key:
            return child
    raise ValueError(key)


def _as_language(value: object) -> Language | None:
    if value is None:
        return None
    for language in LANGUAGES:
        if value == language:
            return language
    shown = '""' if value == "" else value
    raise ConfigError(msg("config.invalid_language", value=shown))


def _real_number(value: object) -> TypeGuard[int | float]:
    return not isinstance(value, bool) and isinstance(value, (int, float))


def _string_items(value: object) -> TypeGuard[list[str] | tuple[str, ...]]:
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        return False
    return all(isinstance(item, str) for item in value)


def _required_bound(check: _Check) -> int | float:
    bound = check.bound
    if not _real_number(bound):
        raise ValueError(check.kind)
    return bound
