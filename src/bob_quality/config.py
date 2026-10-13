from __future__ import annotations

import math
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Literal, TypeGuard

import yaml

from bob_quality.messages import DEFAULT_LANGUAGE, LANGUAGES, Language, msg
from bob_quality.yaml_text import parse_yaml

DEFAULT_EXCLUDE = ["tests", "node_modules", "dist"]

SourceLanguage = Literal["python", "typescript"]
CrapScope = Literal["changed", "all"]
NewClonesMode = Literal["warn", "fail"]

SOURCE_LANGUAGES: tuple[SourceLanguage, ...] = ("python", "typescript")
CRAP_SCOPES: tuple[CrapScope, ...] = ("changed", "all")
NEW_CLONES_MODES: tuple[NewClonesMode, ...] = ("warn", "fail")
_SUFFIX_LANGUAGE: dict[str, SourceLanguage] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".jsx": "typescript",
    ".mjs": "typescript",
    ".cjs": "typescript",
}

_CheckKind = Literal[
    "string",
    "string_list",
    "number",
    "finite",
    "integer",
    "confidence",
    "one_of",
    "members",
    "language",
]
_BoundKind = Literal["gt", "at_least", "at_most"]
_Failure = tuple[str, str, dict[str, object]]


@dataclass(frozen=True)
class _Check:
    kind: _CheckKind
    choices: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind in {"one_of", "members", "language"} and len(self.choices) != 2:
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
    mapping: bool = False

    def __post_init__(self) -> None:
        if self.mapping and (self.children or self.attr or self.checks):
            raise ValueError(self.key)


_SCHEMA = _Node(
    key="",
    attr="",
    checks=(),
    children=(
        _Node("base", "base", (_Check("string"),), empty_is_default=True),
        _Node(
            "language",
            "language",
            (_Check("language", choices=LANGUAGES),),
            empty_is_default=True,
        ),
        _Node(
            "languages",
            "languages",
            (_Check("members", choices=SOURCE_LANGUAGES),),
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
                    (_Check("integer"), _Bound("gt", 0)),
                    null_is_default=False,
                ),
                _Node(
                    "new_clones",
                    "new_clones",
                    (_Check("string"), _Check("one_of", choices=NEW_CLONES_MODES)),
                    empty_is_default=True,
                ),
                _Node(
                    "max_new_clones",
                    "max_new_clones",
                    (_Check("integer"), _Bound("at_least", 0)),
                ),
                _Node(
                    "min_similarity",
                    "min_similarity",
                    (
                        _Check("number"),
                        _Check("finite"),
                        _Bound("at_least", 0),
                        _Bound("at_most", 100),
                    ),
                ),
                _Node("min_lines", "min_lines", (_Check("integer"), _Bound("at_least", 0))),
            ),
        ),
        _Node(
            "coverage",
            "",
            (),
            children=(
                _Node(
                    "min_percent",
                    "coverage_min_percent",
                    (
                        _Check("number"),
                        _Check("finite"),
                        _Bound("at_least", 0),
                        _Bound("at_most", 100),
                    ),
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
        _Node("typing", "", (), mapping=True),
        _Node("secrets", "", (), mapping=True),
        _Node(
            "dead_code",
            "",
            (),
            children=(
                _Node("min_confidence", "dead_code_min_confidence", (_Check("confidence"),)),
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
    new_clones: NewClonesMode = "warn"
    max_new_clones: int = 0
    min_similarity: float = 0.0
    min_lines: int = 0
    coverage_min_percent: float = 80.0
    dead_code_min_confidence: int | None = None
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
        return _detected(Config(), cwd)
    return _config_from_file(config_path, cwd)


def detect_languages(
    cwd: Path, include: tuple[str, ...], exclude: tuple[str, ...]
) -> tuple[SourceLanguage, ...]:
    found: set[SourceLanguage] = set()
    for root in include:
        _scan(cwd / root, cwd, exclude, found)
    return tuple(language for language in SOURCE_LANGUAGES if language in found)


def reject_config_types(path: Path | None, cwd: Path) -> None:
    load_config(path, cwd)


def resolve_language(flag: str | None, config_path: Path | None, cwd: Path) -> Language:
    if flag is not None:
        chosen = _parse_language(flag)
    else:
        env = os.environ.get("BOB_LANG")
        chosen = None if env is None else _parse_language(env)
    # --lang ou BOB_LANG válido ainda lê o bob.yaml para um arquivo inválido continuar falhando.
    configured = _configured_language(config_path, cwd)
    if chosen is not None:
        return chosen
    if configured is None:
        return DEFAULT_LANGUAGE
    return configured


def _configured_language(path: Path | None, cwd: Path) -> Language | None:
    config_path = path if path is not None else cwd / "bob.yaml"
    if not config_path.is_file():
        return None
    raw = _read_mapping(config_path, cwd)
    child = next(item for item in _SCHEMA.children if item.key == "language")
    values = _read_child(child, raw, _config_label(config_path, cwd), "")
    found = values.get("language")
    if not isinstance(found, str):
        return None
    return _parse_language(found)


def _parse_language(value: str) -> Language:
    for language in LANGUAGES:
        if value == language:
            return language
    shown = '""' if value == "" else value
    raise ConfigError(msg("config.invalid_language", value=shown))


def _config_from_file(config_path: Path, cwd: Path) -> Config:
    raw = _read_mapping(config_path, cwd)
    label = _config_label(config_path, cwd)
    values = _read_node(_SCHEMA, raw, label, "")
    _reject_missing_include(values.get("include"), label, cwd)
    config = Config(**values)
    if "languages" in values:
        return config
    return _detected(config, cwd)


def _detected(config: Config, cwd: Path) -> Config:
    found = detect_languages(cwd, config.include, config.exclude)
    if not found:
        return config
    return replace(config, languages=found)


def _scan(
    base: Path, cwd: Path, exclude: tuple[str, ...], found: set[SourceLanguage]
) -> None:
    if base.is_symlink():
        return
    if _excluded(_inside(base, cwd), exclude):
        return
    if base.is_file():
        _note(base, found)
        return
    if not base.is_dir():
        return
    for child in base.iterdir():
        _scan(child, cwd, exclude, found)


def _inside(path: Path, cwd: Path) -> Path:
    try:
        return path.relative_to(cwd)
    except ValueError:
        return path


def _note(path: Path, found: set[SourceLanguage]) -> None:
    suffix = path.suffix
    if suffix not in _SUFFIX_LANGUAGE:
        return
    found.add(_SUFFIX_LANGUAGE[suffix])


def _excluded(relative: Path, exclude: tuple[str, ...]) -> bool:
    text = relative.as_posix()
    for item in exclude:
        pattern = item.strip("/")
        if text == pattern or text.startswith(pattern + "/"):
            return True
        if pattern in relative.parts:
            return True
    return False


def _reject_missing_include(include: object, label: str, cwd: Path) -> None:
    if not _string_items(include):
        return
    missing = [item for item in include if not (cwd / item).exists()]
    if not missing:
        return
    raise ConfigError(msg("config.include_missing", path=label, missing=", ".join(missing)))


def _read_mapping(config_path: Path, cwd: Path) -> dict[str, Any]:
    try:
        loaded = parse_yaml(config_path.read_text())
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


def _is_mapping(node: _Node) -> bool:
    return node.mapping or bool(node.children)


def _read_present(child: _Node, value: object, label: str, dotted: str) -> dict[str, object]:
    if _is_mapping(child):
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
        return _float_or_none(value)
    return value


def _reject(child: _Node, value: object, label: str, dotted: str) -> None:
    for rule in child.checks:
        failure = _failure_for(rule, value)
        if failure is None:
            continue
        catalog, suffix, params = failure
        raise ConfigError(msg(catalog, path=label, key=f"{dotted}{suffix}", **params))


def _failure_for(rule: _Rule, value: object) -> _Failure | None:
    if isinstance(rule, _Bound):
        return _BOUNDED[rule.kind](value, rule.bound)
    return _UNBOUND[rule.kind](rule, value)


def _greater(value: object, bound: int | float) -> _Failure | None:
    if value > bound:
        return None
    return ("config.key_greater_than", "", {"bound": bound})


def _at_least(value: object, bound: int | float) -> _Failure | None:
    if value >= bound:
        return None
    return ("config.key_at_least", "", {"bound": bound})


def _at_most(value: object, bound: int | float) -> _Failure | None:
    if value <= bound:
        return None
    return ("config.key_at_most", "", {"bound": bound})


def _text(check: _Check, value: object) -> _Failure | None:
    if isinstance(value, str):
        return None
    return ("config.key_string", "", {})


def _texts(check: _Check, value: object) -> _Failure | None:
    if _string_items(value):
        return None
    return ("config.key_string_list", "", {})


def _number(check: _Check, value: object) -> _Failure | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return None
    return ("config.key_number", "", {})


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)
    except OverflowError:
        return None


def _finite(check: _Check, value: object) -> _Failure | None:
    number = _float_or_none(value)
    if number is not None and math.isfinite(number):
        return None
    return ("config.key_finite", "", {})


def _integer(check: _Check, value: object) -> _Failure | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return None
    return ("config.key_integer", "", {})


def _confidence(check: _Check, value: object) -> _Failure | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return ("config.key_integer", "", {})
    if 0 <= value <= 100:
        return None
    return ("config.key_between", "", {"low": 0, "high": 100})


def _one_of(check: _Check, value: object) -> _Failure | None:
    if value in check.choices:
        return None
    return (
        "config.key_one_of",
        "",
        {"left": check.choices[0], "right": check.choices[1]},
    )


def _members(check: _Check, value: object) -> _Failure | None:
    if not _string_items(value):
        return ("config.key_string_list", "", {})
    return _member_at(check, value)


def _member_at(check: _Check, value: list[str] | tuple[str, ...]) -> _Failure | None:
    if len(value) == 0:
        return ("config.key_non_empty", "", {})
    seen: set[str] = set()
    for index, item in enumerate(value):
        if item not in check.choices:
            return (
                "config.key_one_of",
                f"[{index}]",
                {"left": check.choices[0], "right": check.choices[1]},
            )
        if item in seen:
            return ("config.repeated_member", f"[{index}]", {"value": item})
        seen.add(item)
    return None


def _language(check: _Check, value: object) -> _Failure | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return ("config.key_string", "", {})
    if value in check.choices:
        return None
    return (
        "config.key_one_of",
        "",
        {"left": check.choices[0], "right": check.choices[1]},
    )


_FailFn = Callable[[_Check, object], _Failure | None]
_BoundFn = Callable[[object, int | float], _Failure | None]

_BOUNDED: dict[_BoundKind, _BoundFn] = {
    "gt": _greater,
    "at_least": _at_least,
    "at_most": _at_most,
}

_UNBOUND: dict[_CheckKind, _FailFn] = {
    "string": _text,
    "string_list": _texts,
    "number": _number,
    "finite": _finite,
    "integer": _integer,
    "confidence": _confidence,
    "one_of": _one_of,
    "members": _members,
    "language": _language,
}


def _guard(config: Config) -> None:
    for node in _leaves(_SCHEMA):
        _guard_value(node, getattr(config, node.attr), node.attr)


def _guard_value(node: _Node, value: object, attr: str) -> None:
    for rule in node.checks:
        if _failure_for(rule, value) is not None:
            raise ValueError(attr)


def _leaves(node: _Node):
    if _is_mapping(node):
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
