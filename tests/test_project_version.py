"""Versão das skills do projeto (CT8, CT11; ADR 0024)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bob_quality import install_skills, project_version
from bob_quality.install_skills import SourceError, manifest_skill_names
from bob_quality.messages import render, t
from bob_quality.project_version import (
    ProjectSkills,
    read_project_skills,
    skills_line,
    skills_text,
)

NAMES = ("bob-check", "harden", "review-report")

_INVALID = {
    "no_newline": b"0.1.0",
    "two_newlines": b"0.1.0\n\n",
    "prefix_v": b"v0.1.0\n",
    "two_parts": b"0.1\n",
    "crlf": b"0.1.0\r\n",
    "space": b" 0.1.0\n",
    "four_parts": b"0.1.0.1\n",
    "empty": b"",
}


def _put(project: Path, name: str, raw: bytes) -> Path:
    path = project / ".agents" / "skills" / name / ".bob-version"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def test_manifest_skill_names_are_the_packaged_skills() -> None:
    manifest = install_skills.default_source() / install_skills.MANIFEST
    packaged = tuple(
        Path(entry).name
        for entry in json.loads(manifest.read_text(encoding="utf-8"))["skills"]
    )
    assert manifest_skill_names() == NAMES
    assert manifest_skill_names() == packaged


def test_manifest_skill_names_reads_the_given_source(tmp_path: Path) -> None:
    src = tmp_path / "plugin"
    manifest = src / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"skills": ["./skills/a", "x/b"]}', encoding="utf-8")
    assert manifest_skill_names(src) == ("a", "b")


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(None, id="missing"),
        pytest.param([], id="not_object"),
        pytest.param({"skills": "x"}, id="not_list"),
    ],
)
def test_manifest_skill_names_rejects_a_bad_manifest(
    tmp_path: Path, body: object
) -> None:
    src = tmp_path / "plugin"
    if body is not None:
        manifest = src / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(SourceError):
        manifest_skill_names(src)


def test_every_skill_with_the_same_version_is_installed(tmp_path: Path) -> None:
    for name in NAMES:
        _put(tmp_path, name, b"0.1.0\n")
    assert read_project_skills(tmp_path) == ProjectSkills("installed", ("0.1.0",), False)


@pytest.mark.parametrize(
    "case",
    ["no_folder", "all_invalid", "no_names", "bad_manifest"],
)
def test_not_installed_cases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    if case == "all_invalid":
        for name in NAMES:
            _put(tmp_path, name, b"x\n")
    if case == "bad_manifest":

        def _boom() -> tuple[str, ...]:
            raise SourceError("x")

        monkeypatch.setattr(install_skills, "manifest_skill_names", _boom)
    if case == "no_names":
        found = read_project_skills(tmp_path, ())
    else:
        found = read_project_skills(tmp_path)
    assert found == ProjectSkills("not_installed")


def test_mixed_versions_sort_numerically(tmp_path: Path) -> None:
    _put(tmp_path, "bob-check", b"0.10.0\n")
    _put(tmp_path, "harden", b"0.9.0\n")
    _put(tmp_path, "review-report", b"0.10.0\n")
    skills = read_project_skills(tmp_path)
    assert skills == ProjectSkills("mixed", ("0.9.0", "0.10.0"), False)
    assert render(skills_text(skills), "en") == "mixed (0.9.0, 0.10.0)"


@pytest.mark.parametrize(
    ("files", "versions", "text"),
    [
        pytest.param(
            {"harden": b"0.1.0\n"},
            ("0.1.0",),
            "mixed (0.1.0, not installed)",
            id="one_version",
        ),
        pytest.param(
            {"bob-check": b"0.2.0\n", "harden": b"0.1.0\n"},
            ("0.1.0", "0.2.0"),
            "mixed (0.1.0, 0.2.0, not installed)",
            id="two_versions",
        ),
    ],
)
def test_partial_install_is_mixed_with_missing(
    tmp_path: Path,
    files: dict[str, bytes],
    versions: tuple[str, ...],
    text: str,
) -> None:
    for name, raw in files.items():
        _put(tmp_path, name, raw)
    skills = read_project_skills(tmp_path)
    assert skills == ProjectSkills("mixed", versions, True)
    assert render(skills_text(skills), "en") == text


def _plant_invalid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    if case in _INVALID:
        _put(tmp_path, "harden", _INVALID[case])
        return
    skill = tmp_path / ".agents" / "skills" / "harden"
    if case == "folder":
        (skill / ".bob-version").mkdir(parents=True)
        return
    if case == "symlink":
        target = tmp_path / "outside"
        target.write_bytes(b"0.1.0\n")
        skill.mkdir(parents=True)
        (skill / ".bob-version").symlink_to(target)
        return
    path = _put(tmp_path, "harden", b"0.1.0\n")
    original = Path.read_bytes

    def _read(self: Path) -> bytes:
        if self == path:
            raise OSError(13, "x")
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", _read)


@pytest.mark.parametrize(
    "case",
    [
        "no_newline",
        "two_newlines",
        "prefix_v",
        "two_parts",
        "crlf",
        "space",
        "four_parts",
        "empty",
        "folder",
        "symlink",
        "unreadable",
    ],
)
def test_invalid_version_files_count_as_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    _put(tmp_path, "bob-check", b"0.1.0\n")
    _put(tmp_path, "review-report", b"0.1.0\n")
    _plant_invalid(tmp_path, monkeypatch, case)
    assert read_project_skills(tmp_path) == ProjectSkills("mixed", ("0.1.0",), True)


@pytest.mark.parametrize(
    ("lang", "skills", "line"),
    [
        ("en", ProjectSkills("installed", ("0.1.0",)), "project skills: 0.1.0 (.agents/skills)"),
        ("en", ProjectSkills("not_installed"), "project skills: not installed"),
        (
            "en",
            ProjectSkills("mixed", ("0.1.0", "0.2.0")),
            "project skills: mixed (0.1.0, 0.2.0)",
        ),
        (
            "en",
            ProjectSkills("mixed", ("0.1.0",), True),
            "project skills: mixed (0.1.0, not installed)",
        ),
        (
            "pt-BR",
            ProjectSkills("installed", ("0.1.0",)),
            "skills do projeto: 0.1.0 (.agents/skills)",
        ),
        ("pt-BR", ProjectSkills("not_installed"), "skills do projeto: não instaladas"),
        (
            "pt-BR",
            ProjectSkills("mixed", ("0.1.0", "0.2.0")),
            "skills do projeto: misturadas (0.1.0, 0.2.0)",
        ),
        (
            "pt-BR",
            ProjectSkills("mixed", ("0.1.0",), True),
            "skills do projeto: misturadas (0.1.0, não instaladas)",
        ),
    ],
)
def test_skills_text_in_both_languages(
    lang: str, skills: ProjectSkills, line: str
) -> None:
    assert t(lang, "version.skills", state=skills_text(skills)) == line


def test_skills_line_reads_the_project(tmp_path: Path) -> None:
    for name in NAMES:
        _put(tmp_path, name, b"0.1.0\n")
    assert render(skills_line(tmp_path), "en") == "project skills: 0.1.0 (.agents/skills)"


_CATALOG = (
    ("en", "version.skills", "project skills: S"),
    ("en", "version.at", "V (.agents/skills)"),
    ("en", "version.not_installed", "not installed"),
    ("en", "version.mixed", "mixed (A, B)"),
    ("en", "version.mixed_missing", "mixed (A, B, not installed)"),
    ("pt-BR", "version.skills", "skills do projeto: S"),
    ("pt-BR", "version.at", "V (.agents/skills)"),
    ("pt-BR", "version.not_installed", "não instaladas"),
    ("pt-BR", "version.mixed", "misturadas (A, B)"),
    ("pt-BR", "version.mixed_missing", "misturadas (A, B, não instaladas)"),
)


@pytest.mark.parametrize(("lang", "key", "line"), _CATALOG)
def test_version_messages_exist_in_both_languages(lang: str, key: str, line: str) -> None:
    assert t(lang, key, state="S", version="V", versions="A, B") == line
