"""Versão das skills do bob no projeto (CT8, CT11; ADR 0024)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from bob_quality import install_skills
from bob_quality.messages import Message, msg

SkillsState = Literal["installed", "not_installed", "mixed"]

_SKILLS_DIR = Path(".agents") / "skills"
_VERSION_RE = re.compile(rb"\d+\.\d+\.\d+\n")
_SEP = ", "
_DOT = "."


@dataclass(frozen=True)
class ProjectSkills:
    state: SkillsState
    versions: tuple[str, ...] = ()
    missing: bool = False


def _numeric(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split(_DOT))


def _read_version(path: Path) -> str | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if _VERSION_RE.fullmatch(raw) is None:
        return None
    return raw[:-1].decode()


def read_project_skills(
    project: Path, names: Sequence[str] | None = None
) -> ProjectSkills:
    if names is None:
        try:
            names = install_skills.manifest_skill_names()
        except install_skills.SourceError:
            return ProjectSkills("not_installed")
    found = [
        _read_version(project / _SKILLS_DIR / name / install_skills.BOB_VERSION_FILE)
        for name in names
    ]
    missing = None in found
    distinct = tuple(sorted({value for value in found if value is not None}, key=_numeric))
    if not distinct:
        return ProjectSkills("not_installed")
    if len(distinct) == 1 and not missing:
        return ProjectSkills("installed", distinct)
    return ProjectSkills("mixed", distinct, missing)


def skills_text(skills: ProjectSkills) -> Message:
    if skills.state == "installed":
        return msg("version.at", version=skills.versions[0])
    if skills.state == "not_installed":
        return msg("version.not_installed")
    key = "version.mixed_missing" if skills.missing else "version.mixed"
    return msg(key, versions=_SEP.join(skills.versions))


def skills_line(project: Path) -> Message:
    return msg("version.skills", state=skills_text(read_project_skills(project)))
