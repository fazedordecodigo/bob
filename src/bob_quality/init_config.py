"""Gerador do bob.yaml (C05, CT7): padrões do README e paths.include derivado."""

import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from bob_quality import suite_fingerprint
from bob_quality.config import DEFAULT_EXCLUDE, _SUFFIX_LANGUAGE, _excluded, load_config
from bob_quality.yaml_text import parse_yaml

CONFIG_NAME = "bob.yaml"
ConfigState = Literal["created", "preserved", "created_no_code"]


@dataclass(frozen=True)
class ConfigResult:
    state: ConfigState
    include: tuple[str, ...]


_BODY = """\
base: origin/main
language: en
paths:
  include: {include}
  exclude: [tests, node_modules, dist]
crap:
  max_per_function: 10
  scope: changed
duplication:
  min_tokens: 50
  new_clones: warn
  max_new_clones: 0
  min_similarity: 0
  min_lines: 0
coverage:
  min_percent: 80
dependencies:
  python: .importlinter
  typescript: .dependency-cruiser.cjs
"""


def render_config(include: Sequence[str]) -> str:
    listed = ", ".join(_render_item(item) for item in include)
    return _BODY.format(include="[" + listed + "]")


def write_default_config(project: Path) -> ConfigResult:
    """Cria bob.yaml se não existe (CT7). Nunca altera um existente."""
    target = project / CONFIG_NAME
    if _already_there(target):
        return ConfigResult("preserved", ())
    include, state = _selection(project)
    _publish(project, target, include)
    return ConfigResult(state, include)


def _render_item(item: str) -> str:
    if item == ".":
        return '"."'
    if _plain(item):
        return item
    return _quote(item)


def _quote(item: str) -> str:
    encoder = json.JSONEncoder(ensure_ascii=False)
    if encoder.ensure_ascii is not False: raise RuntimeError
    return encoder.encode(item)


def _plain(item: str) -> bool:
    try:
        parsed = parse_yaml("[" + item + "]")
    except yaml.YAMLError:
        return False
    return parsed == [item]


def _already_there(target: Path) -> bool:
    return target.exists() or target.is_symlink()


def _selection(project: Path) -> tuple[tuple[str, ...], ConfigState]:
    folders, root_code = _places(project)
    if "src" in folders:
        return ("src",), "created"
    if folders:
        return tuple(sorted(folders)), "created"
    return (".",), _dot_state(root_code)


def _dot_state(root_code: bool) -> ConfigState:
    states: dict[bool, ConfigState] = {True: "created", False: "created_no_code"}
    return states[root_code]


def _places(project: Path) -> tuple[set[str], bool]:
    folders: set[str] = set()
    root_code = False
    for name in suite_fingerprint._listed_files(project):
        if _is_code(project, name):
            root_code = _absorb(folders, name, root_code)
    return folders, root_code


def _absorb(folders: set[str], name: str, root_code: bool) -> bool:
    if "/" not in name:
        return True
    folder = name.split("/")[0]
    if not folder.startswith("."):
        folders.add(folder)
    return root_code


def _is_code(project: Path, name: str) -> bool:
    path = project / name
    if Path(name).suffix not in _SUFFIX_LANGUAGE:
        return False
    if not path.is_file() or path.is_symlink():
        return False
    return not _excluded(Path(name), tuple(DEFAULT_EXCLUDE))


def _publish(project: Path, target: Path, include: tuple[str, ...]) -> None:
    tmp = project / f"bob.yaml.tmp-{os.getpid()}"
    try:
        tmp.write_bytes(render_config(include).encode())
        load_config(tmp, project)
        os.replace(tmp, target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
