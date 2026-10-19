"""install_project_skills (CT4): posse, .bob-version e idempotência."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

import pytest

from bob_quality import install_skills
from bob_quality.install_skills import SkillsResult, install_project_skills


@pytest.fixture
def plugin(tmp_path: Path) -> Path:
    root = tmp_path / "plugin"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / "LICENSE").write_bytes(b"MIT test\n")
    (root / ".claude-plugin" / "plugin.json").write_bytes(
        b'{"skills": ["./skills/alpha", "./skills/beta"]}'
    )
    alpha = root / "skills" / "alpha"
    (alpha / "refs").mkdir(parents=True)
    (alpha / "SKILL.md").write_bytes(b"# alpha\n")
    (alpha / "refs" / "notes.md").write_bytes(b"notes\n")
    beta = root / "skills" / "beta"
    beta.mkdir(parents=True)
    (beta / "SKILL.md").write_bytes(b"# beta\n")
    return root


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    return root


def _digest(root: Path) -> dict[str, tuple[str, int, str]]:
    found: dict[str, tuple[str, int, str]] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(dirpath)
        if base != root:
            found[str(base.relative_to(root))] = _digest_entry(base)
        for name in dirnames:
            path = base / name
            if path.is_symlink():
                found[str(path.relative_to(root))] = _digest_entry(path)
        for name in filenames:
            found[str((base / name).relative_to(root))] = _digest_entry(base / name)
    return found


def _digest_entry(path: Path) -> tuple[str, int, str]:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        kind = "symlink"
        payload = os.readlink(path).encode()
    elif stat.S_ISDIR(info.st_mode):
        kind = "dir"
        payload = b""
    else:
        kind = "file"
        payload = path.read_bytes()
    return kind, info.st_mtime_ns, hashlib.sha256(payload).hexdigest()


def _files(root: Path) -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    for dirpath, _, filenames in os.walk(root, followlinks=False):
        base = Path(dirpath)
        for name in filenames:
            path = base / name
            found[path.relative_to(root).as_posix()] = path.read_bytes()
    return found


def _dest(project_root: Path) -> Path:
    return project_root / ".agents" / "skills"


def test_install_creates_each_skill_with_license_and_marker(plugin: Path, project: Path) -> None:
    result = install_project_skills(project, "1.2.3", source=plugin)

    dest = _dest(project)
    assert result == SkillsResult(
        installed=("alpha", "beta"),
        unchanged=(),
        preserved=(),
        duplicates=(),
    )
    assert _files(dest / "alpha") == {
        "SKILL.md": b"# alpha\n",
        "refs/notes.md": b"notes\n",
        "LICENSE": b"MIT test\n",
        ".bob-version": b"1.2.3\n",
    }
    assert _files(dest / "beta") == {
        "SKILL.md": b"# beta\n",
        "LICENSE": b"MIT test\n",
        ".bob-version": b"1.2.3\n",
    }


def test_install_creates_only_agents_skills(plugin: Path, project: Path) -> None:
    install_project_skills(project, "1.2.3", source=plugin)

    assert sorted(path.name for path in project.iterdir()) == [".agents"]
    assert sorted(path.name for path in (project / ".agents").iterdir()) == ["skills"]
    assert sorted(path.name for path in _dest(project).iterdir()) == ["alpha", "beta"]
    for dirpath, dirnames, filenames in os.walk(project, followlinks=False):
        for name in [*dirnames, *filenames]:
            assert not (Path(dirpath) / name).is_symlink()


def test_second_install_writes_nothing(plugin: Path, project: Path) -> None:
    install_project_skills(project, "1.2.3", source=plugin)
    before = _digest(project)

    result = install_project_skills(project, "1.2.3", source=plugin)

    assert result == SkillsResult(
        installed=(), unchanged=("alpha", "beta"), preserved=(), duplicates=()
    )
    assert _digest(project) == before


def test_changed_file_rewrites_the_skill(plugin: Path, project: Path) -> None:
    install_project_skills(project, "1.2.3", source=plugin)
    skill = _dest(project) / "alpha" / "SKILL.md"
    skill.write_bytes(b"edited\n")

    result = install_project_skills(project, "1.2.3", source=plugin)

    assert result == SkillsResult(
        installed=("alpha",), unchanged=("beta",), preserved=(), duplicates=()
    )
    assert skill.read_bytes() == b"# alpha\n"


def test_extra_file_in_an_owned_skill_is_removed(plugin: Path, project: Path) -> None:
    install_project_skills(project, "1.2.3", source=plugin)
    extra = _dest(project) / "alpha" / "extra.txt"
    extra.write_bytes(b"extra\n")

    result = install_project_skills(project, "1.2.3", source=plugin)

    assert result == SkillsResult(
        installed=("alpha",), unchanged=("beta",), preserved=(), duplicates=()
    )
    assert not extra.exists()


def test_new_version_rewrites_the_marker(plugin: Path, project: Path) -> None:
    install_project_skills(project, "1.2.3", source=plugin)

    result = install_project_skills(project, "1.2.4", source=plugin)

    assert result == SkillsResult(
        installed=("alpha", "beta"), unchanged=(), preserved=(), duplicates=()
    )
    dest = _dest(project)
    assert (dest / "alpha" / ".bob-version").read_bytes() == b"1.2.4\n"
    assert (dest / "beta" / ".bob-version").read_bytes() == b"1.2.4\n"


def test_unmarked_folder_is_preserved_and_reported(plugin: Path, project: Path) -> None:
    dest = _dest(project)
    (dest / "alpha").mkdir(parents=True)
    (dest / "alpha" / "SKILL.md").write_bytes(b"mine\n")

    result = install_project_skills(project, "1.2.3", source=plugin)

    assert result == SkillsResult(
        installed=("beta",),
        unchanged=(),
        preserved=(dest / "alpha",),
        duplicates=(),
        unmarked=(dest / "alpha",),
    )
    assert (dest / "alpha" / "SKILL.md").read_bytes() == b"mine\n"
    assert [path.name for path in (dest / "alpha").iterdir()] == ["SKILL.md"]


def test_foreign_folder_is_preserved_byte_for_byte(plugin: Path, project: Path) -> None:
    dest = _dest(project)
    (dest / "outra").mkdir(parents=True)
    (dest / "outra" / "SKILL.md").write_bytes(b"other\n")
    before = _digest(dest / "outra")

    result = install_project_skills(project, "1.2.3", source=plugin)

    assert result == SkillsResult(
        installed=("alpha", "beta"),
        unchanged=(),
        preserved=(dest / "outra",),
        duplicates=(),
    )
    assert _digest(dest / "outra") == before


def test_symlink_and_file_at_a_skill_name_are_preserved(
    tmp_path: Path, plugin: Path, project: Path
) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "SKILL.md").write_bytes(b"# elsewhere\n")
    dest = _dest(project)
    dest.mkdir(parents=True)
    (dest / "alpha").symlink_to(elsewhere)
    (dest / "beta").write_bytes(b"x")
    before_link = os.readlink(dest / "alpha")
    before_file = (dest / "beta").read_bytes()
    before_elsewhere = _digest(elsewhere)

    result = install_project_skills(project, "1.2.3", source=plugin)

    assert result == SkillsResult(
        installed=(),
        unchanged=(),
        preserved=(dest / "alpha", dest / "beta"),
        duplicates=(),
    )
    assert os.readlink(dest / "alpha") == before_link
    assert (dest / "beta").read_bytes() == before_file
    assert _digest(elsewhere) == before_elsewhere


def test_retired_owned_skill_is_removed(plugin: Path, project: Path) -> None:
    dest = _dest(project)
    (dest / "gamma").mkdir(parents=True)
    (dest / "gamma" / "SKILL.md").write_bytes(b"# gamma\n")
    (dest / "gamma" / ".bob-version").write_bytes(b"1.0.0\n")

    result = install_project_skills(project, "1.2.3", source=plugin)

    assert not (dest / "gamma").exists()
    assert result == SkillsResult(
        installed=("alpha", "beta"), unchanged=(), preserved=(), duplicates=()
    )


def test_leftover_temporary_folders_are_removed(plugin: Path, project: Path) -> None:
    dest = _dest(project)
    (dest / ".alpha.bob-tmp-123").mkdir(parents=True)
    (dest / ".alpha.bob-tmp-123" / "x.txt").write_bytes(b"tmp\n")
    (dest / ".beta.bob-old-9").mkdir(parents=True)
    (dest / ".beta.bob-old-9" / "y.txt").write_bytes(b"old\n")
    (dest / ".keep").write_bytes(b"keep\n")

    result = install_project_skills(project, "1.2.3", source=plugin)

    assert not (dest / ".alpha.bob-tmp-123").exists()
    assert not (dest / ".beta.bob-old-9").exists()
    assert (dest / ".keep").read_bytes() == b"keep\n"
    assert result == SkillsResult(
        installed=("alpha", "beta"), unchanged=(), preserved=(), duplicates=()
    )


def test_copies_in_claude_and_github_skills_are_reported_as_duplicates(
    plugin: Path, project: Path
) -> None:
    claude = project / ".claude" / "skills" / "alpha"
    claude_beta = project / ".claude" / "skills" / "beta"
    github_beta = project / ".github" / "skills" / "beta"
    github_other = project / ".github" / "skills" / "other"
    claude.mkdir(parents=True)
    claude_beta.mkdir(parents=True)
    github_beta.mkdir(parents=True)
    github_other.mkdir(parents=True)
    (claude / "SKILL.md").write_bytes(b"# claude\n")
    (claude_beta / "notes.md").write_bytes(b"no skill\n")
    (github_beta / "SKILL.md").write_bytes(b"# github\n")
    (github_other / "SKILL.md").write_bytes(b"# other\n")
    before = (
        _files(claude),
        _files(claude_beta),
        _files(github_beta),
        _files(github_other),
    )

    result = install_project_skills(project, "1.2.3", source=plugin)

    assert result == SkillsResult(
        installed=("alpha", "beta"),
        unchanged=(),
        preserved=(),
        duplicates=(claude, github_beta),
    )
    assert (
        _files(claude),
        _files(claude_beta),
        _files(github_beta),
        _files(github_other),
    ) == before


def test_write_error_propagates_as_oserror(
    monkeypatch: pytest.MonkeyPatch, plugin: Path, project: Path
) -> None:
    seen: list[Path] = []

    def _deny(_src: object, dst: object, **_kwargs: object) -> None:
        seen.append(Path(str(dst)))
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(install_skills.shutil, "copy2", _deny)

    with pytest.raises(PermissionError):
        install_project_skills(project, "1.2.3", source=plugin)
    assert not (_dest(project) / "alpha").exists()
    assert any(f".alpha.bob-tmp-{os.getpid()}" in path.parts for path in seen)


@pytest.mark.parametrize("version", ["v1.2.3", "1.2", "1.2.3-rc1", ""])
def test_invalid_version_fails_before_writing(plugin: Path, project: Path, version: str) -> None:
    with pytest.raises(ValueError) as caught:
        install_project_skills(project, version, source=plugin)

    assert str(caught.value) == f"versão inválida: {version!r}"
    assert list(project.iterdir()) == []


def test_invalid_source_fails_before_writing(plugin: Path, project: Path) -> None:
    (plugin / ".claude-plugin" / "plugin.json").write_bytes(b"[]")

    with pytest.raises(install_skills.SourceError):
        install_project_skills(project, "1.2.3", source=plugin)
    assert list(project.iterdir()) == []


def test_default_source_installs_the_three_bob_skills(project: Path) -> None:
    result = install_project_skills(project, "0.0.1")

    assert result.installed == ("bob-check", "harden", "review-report")
    for name in result.installed:
        folder = _dest(project) / name
        assert (folder / "SKILL.md").is_file()
        assert (folder / "LICENSE").is_file()
        assert (folder / ".bob-version").read_bytes() == b"0.0.1\n"


def test_install_project_skills_prints_nothing(
    plugin: Path, project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = _dest(project)
    (dest / "outra").mkdir(parents=True)
    (dest / "outra" / "SKILL.md").write_bytes(b"other\n")
    duplicate = project / ".claude" / "skills" / "alpha"
    duplicate.mkdir(parents=True)
    (duplicate / "SKILL.md").write_bytes(b"# dup\n")

    install_project_skills(project, "1.2.3", source=plugin)
    install_project_skills(project, "1.2.3", source=plugin)

    assert capsys.readouterr() == ("", "")
