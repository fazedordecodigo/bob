from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, TypeGuard

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
    "number",
    "finite",
    "integer",
    "one_of",
    "members",
    "language",
]
_BoundKind = Literal["gt", "at_least"]
_Failure = tuple[str, str, dict[str, object]]


@dataclass(frozen=True)
class _Check:
    kind: _CheckKind
    choices: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind in {"one_of", "members"} and len(self.choices) != 2:
            raise ValueError(self.kind)


@dataclass(frozen=True)
class _Bound:
    kind: _BoundKind
    bound: int | float

    def __post_init__(self) -> None:
        if isinstance(self.bound, bool) or not isinstance(self.bound, (int, float)):
            raise ValueError(self.kind)


_Rule = _Check | _Bound


@dataclass(frozen=True)
class _Node:
    key: str
    attr: str
    checks: tuple[_Rule, ...]
    children: tuple[_Node, ...] = ()
    empty_is_default: bool = False
    null_is_default: bool = True


_SCHEMA = _Node(
    key="",
    attr="",
    checks=(),
    children=(
        _Node("base", "base", (_Check("string"),), empty_is_default=True),
        _Node("language", "language", (_Check("language"),), empty_is_default=True),
        _Node(
            "languages",
            "languages",
            (_Check("members", choices=SOURCE_LANGUAGES),),
            empty_is_default=True,
        ),
        _Node(
            "paths",
            "",
            (),
            children=(
                _Node("include", "include", (_Check("string_list"),), empty_is_default=True),
                _Node("exclude", "exclude", (_Check("string_list"),), empty_is_default=True),
            ),
        ),
        _Node(
            "crap",
            "",
            (),
            children=(
                _Node(
                    "max_per_function",
                    "max_crap",
                    (_Check("number"), _Check("finite"), _Bound("gt", 0)),
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
            "",
            (),
            children=(
                _Node(
                    "min_tokens",
                    "min_tokens",
                    (_Check("integer"), _Bound("at_least", 0)),
                    null_is_default=False,
                ),
            ),
        ),
        _Node(
            "dependencies",
            "",
            (),
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
    if "language" not in raw:
        return None
    return _optional_language(raw["language"])


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


def _optional_language(value: object) -> Language | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return parse_language(value)
    raise ConfigError(msg("config.invalid_language", value=value))


def _read_node(node: _Node, raw: dict[str, Any], label: str, prefix: str) -> dict[str, object]:
    _reject_unknown(raw, _allowed(node), label, prefix)
    values: dict[str, object] = {}
    for child in node.children:
        values.update(_read_child(child, raw, label, prefix))
    return values


def _allowed(node: _Node) -> set[str]:
    return {child.key for child in node.children}


def _reject_unknown(raw: dict[str, Any], allowed: set[str], label: str, prefix: str) -> None:
    for key in raw:
        if key not in allowed:
            raise ConfigError(msg("file.unknown_key", path=label, key=_join(prefix, key)))


def _read_child(child: _Node, raw: dict[str, Any], label: str, prefix: str) -> dict[str, object]:
    if child.key not in raw:
        return {}
    value = raw[child.key]
    if _skipped(child, value):
        return {}
    return _read_present(child, value, label, _join(prefix, child.key))


def _skipped(child: _Node, value: object) -> bool:
    if child.null_is_default and value is None:
        return True
    if child.empty_is_default and _empty(child, value):
        return True
    return False


def _read_present(child: _Node, value: object, label: str, dotted: str) -> dict[str, object]:
    if child.children:
        return _read_nested(child, value, label, dotted)
    return {child.attr: _apply(child, value, label, dotted)}


def _read_nested(child: _Node, value: object, label: str, dotted: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ConfigError(msg("config.key_mapping", path=label, key=dotted))
    return _read_node(child, value, label, dotted)


def _join(prefix: str, key: str) -> str:
    if prefix == "":
        return key
    return f"{prefix}.{key}"


def _apply(child: _Node, value: object, label: str, dotted: str) -> object:
    _reject(child, value, label, dotted)
    if _has_kind(child, "number"):
        return float(value)
    return value


def _reject(child: _Node, value: object, label: str, dotted: str) -> None:
    for rule in child.checks:
        failure = _failure_for(rule, value, dotted)
        if failure is None:
            continue
        catalog, field, params = failure
        raise ConfigError(msg(catalog, path=label, key=field, **params))


def _failure_for(rule: _Rule, value: object, field: str) -> _Failure | None:
    if isinstance(rule, _Bound):
        return _bound_failure(rule, value, field)
    return _UNBOUND[rule.kind](rule, value, field)


def _bound_failure(rule: _Bound, value: object, field: str) -> _Failure | None:
    if rule.kind == "gt":
        return _greater(value, rule.bound, field)
    return _at_least(value, rule.bound, field)


def _greater(value: object, bound: int | float, field: str) -> _Failure | None:
    if value > bound:
        return None
    return ("config.key_greater_than", field, {"bound": bound})


def _at_least(value: object, bound: int | float, field: str) -> _Failure | None:
    if value >= bound:
        return None
    return ("config.key_at_least", field, {"bound": bound})


def _text(check: _Check, value: object, field: str) -> _Failure | None:
    if isinstance(value, str):
        return None
    return ("config.key_string", field, {})


def _texts(check: _Check, value: object, field: str) -> _Failure | None:
    if _string_items(value):
        return None
    return ("config.key_string_list", field, {})


def _number(check: _Check, value: object, field: str) -> _Failure | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return None
    return ("config.key_number", field, {})


def _finite(check: _Check, value: object, field: str) -> _Failure | None:
    if math.isfinite(value):
        return None
    return ("config.key_finite", field, {})


def _integer(check: _Check, value: object, field: str) -> _Failure | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return None
    return ("config.key_integer", field, {})


def _one_of(check: _Check, value: object, field: str) -> _Failure | None:
    if value in check.choices:
        return None
    return (
        "config.key_one_of",
        field,
        {"left": check.choices[0], "right": check.choices[1]},
    )


def _members(check: _Check, value: object, field: str) -> _Failure | None:
    if not _string_items(value):
        return ("config.key_string_list", field, {})
    return _member_at(check, value, field)


def _member_at(
    check: _Check, value: list[str] | tuple[str, ...], field: str
) -> _Failure | None:
    for index, item in enumerate(value):
        if item not in check.choices:
            return (
                "config.key_one_of",
                f"{field}[{index}]",
                {"left": check.choices[0], "right": check.choices[1]},
            )
    return None


def _language(check: _Check, value: object, field: str) -> _Failure | None:
    if value is None or value == "" or value in LANGUAGES:
        return None
    return ("config.invalid_language", field, {"value": value})


_FailFn = Callable[[_Check, object, str], _Failure | None]

_UNBOUND: dict[_CheckKind, _FailFn] = {
    "string": _text,
    "string_list": _texts,
    "number": _number,
    "finite": _finite,
    "integer": _integer,
    "one_of": _one_of,
    "members": _members,
    "language": _language,
}


def _guard(config: Config) -> None:
    for node in _leaves(_SCHEMA):
        _guard_value(node, getattr(config, node.attr), node.attr)


def _guard_value(node: _Node, value: object, attr: str) -> None:
    for rule in node.checks:
        if _failure_for(rule, value, attr) is not None:
            raise ValueError(attr)


def _leaves(node: _Node):
    if node.children:
        for child in node.children:
            yield from _leaves(child)
        return
    yield node


def _empty(node: _Node, value: object) -> bool:
    if _has_kind(node, "string") or _has_kind(node, "language"):
        return value == ""
    return value == []


def _has_kind(node: _Node, kind: _CheckKind) -> bool:
    return any(isinstance(check, _Check) and check.kind == kind for check in node.checks)


def _string_items(value: object) -> TypeGuard[list[str] | tuple[str, ...]]:
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        return False
    return all(isinstance(item, str) for item in value)
