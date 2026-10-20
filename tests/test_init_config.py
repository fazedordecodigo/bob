"""init_config (CT7): bob.yaml gerado, include derivado e preservação."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from bob_quality import init_config, suite_fingerprint
from bob_quality.config import ConfigError, load_config
from bob_quality.init_config import ConfigResult, render_config, write_default_config
from bob_quality.messages import reason
from bob_quality.tools import ToolError
from bob_quality.yaml_text import parse_yaml

_CT7 = """\
base: origin/main
language: en
paths:
  include: <INCLUDE>
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


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    project.mkdir()
    _git(project, "init", "-q")
    _git(project, "config", "user.email", "t@t")
    _git(project, "config", "user.name", "t")
    _git(project, "config", "commit.gpgsign", "false")
    return project.resolve()


def _write(repo: Path, rel: str, text: str = "x\n") -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _temps(repo: Path) -> list[Path]:
    return list(repo.glob("bob.yaml.tmp-*"))


@pytest.mark.parametrize(
    ("include", "rendered"),
    [
        (("src",), "[src]"),
        (("app", "lib"), "[app, lib]"),
        ((".",), '["."]'),
    ],
)
def test_render_config_is_the_ct7_text(include: tuple[str, ...], rendered: str) -> None:
    text = render_config(include)
    assert text == _CT7.replace("<INCLUDE>", rendered)
    assert text.endswith("\n")
    assert len(text.splitlines()) == 19
    assert "languages" not in text
    assert "\r" not in text


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        ("app_1.x-y", "app_1.x-y"),
        ("módulo", "módulo"),
        ("a b", "a b"),
        ("true", '"true"'),
        ("1.0", '"1.0"'),
        ("a,b", '"a,b"'),
        ("#x", '"#x"'),
        ("é,b", '"é,b"'),
        ("null", '"null"'),
    ],
)
def test_render_config_quotes_items_that_are_not_plain(item: str, expected: str) -> None:
    text = render_config((item,))
    assert text.splitlines()[3] == f"  include: [{expected}]"
    assert parse_yaml(text)["paths"]["include"] == [item]


def test_write_creates_src_when_src_has_code(repo: Path) -> None:
    _write(repo, "src/app.py")
    _write(repo, "app/main.py")
    _write(repo, "web/x.ts")
    assert write_default_config(repo) == ConfigResult("created", ("src",))
    assert (repo / "bob.yaml").read_bytes() == render_config(("src",)).encode("utf-8")


def test_write_lists_every_code_folder_in_code_point_order(repo: Path) -> None:
    _write(repo, "zeta/a.py")
    _write(repo, "web/b.ts")
    _write(repo, "app/c.js")
    _write(repo, "Lib/d.py")
    assert write_default_config(repo) == ConfigResult("created", ("Lib", "app", "web", "zeta"))
    text = (repo / "bob.yaml").read_text(encoding="utf-8")
    assert "  include: [Lib, app, web, zeta]\n" in text


@pytest.mark.parametrize("suffix", [".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"])
def test_each_code_suffix_counts(repo: Path, suffix: str) -> None:
    _write(repo, f"pkg/m{suffix}")
    assert write_default_config(repo) == ConfigResult("created", ("pkg",))


def test_other_suffixes_do_not_count(repo: Path) -> None:
    _write(repo, "docs/a.md")
    _write(repo, "cfg/a.json")
    _write(repo, "data/a.pyc")
    _write(repo, "types/a.d")
    _write(repo, "scripts/run.sh")
    assert write_default_config(repo) == ConfigResult("created_no_code", (".",))


def test_excluded_folders_do_not_count(repo: Path) -> None:
    _write(repo, "tests/test_a.py")
    _write(repo, "node_modules/x/i.js")
    _write(repo, "dist/b.js")
    _write(repo, "app/tests/c.py")
    _write(repo, "lib/d.py")
    assert write_default_config(repo) == ConfigResult("created", ("lib",))


@pytest.mark.parametrize(
    ("files", "expected"),
    [
        (
            (".github/s.js", ".agents/skills/x/run.py", "tool/a.py"),
            ConfigResult("created", ("tool",)),
        ),
        (
            (".github/s.js", ".agents/skills/x/run.py"),
            ConfigResult("created_no_code", (".",)),
        ),
    ],
)
def test_dot_folders_do_not_count(
    repo: Path, files: tuple[str, ...], expected: ConfigResult
) -> None:
    for rel in files:
        _write(repo, rel)
    assert write_default_config(repo) == expected


def test_code_only_in_the_root_is_dot(repo: Path) -> None:
    _write(repo, "main.py")
    _write(repo, ".eslintrc.cjs")
    _write(repo, "docs/a.md")
    assert write_default_config(repo) == ConfigResult("created", (".",))
    text = (repo / "bob.yaml").read_text(encoding="utf-8")
    assert "  include: [\".\"]\n" in text


@pytest.mark.parametrize("files", [(), ("README.md",)])
def test_no_code_is_dot_and_created_no_code(repo: Path, files: tuple[str, ...]) -> None:
    for rel in files:
        _write(repo, rel)
    assert write_default_config(repo) == ConfigResult("created_no_code", (".",))
    assert (repo / "bob.yaml").read_text(encoding="utf-8") == render_config((".",))


def test_untracked_count_and_ignored_do_not(repo: Path) -> None:
    _write(repo, ".gitignore", "vendor/\nbuild/\n")
    _write(repo, "vendor/v.py")
    _write(repo, "build/b.py")
    _write(repo, "new/n.py")
    _git(repo, "add", "-f", "vendor/v.py")
    assert write_default_config(repo) == ConfigResult("created", ("new", "vendor"))


def test_symlinks_do_not_count(repo: Path) -> None:
    _write(repo, "real/notes.txt")
    (repo / "link").mkdir()
    os.symlink("../real/notes.txt", repo / "link" / "a.py")
    os.symlink("real", repo / "ext")
    assert write_default_config(repo) == ConfigResult("created_no_code", (".",))


def test_listed_but_deleted_files_do_not_count(repo: Path) -> None:
    _write(repo, "gone/a.py")
    _write(repo, "here/b.py")
    _git(repo, "add", "gone/a.py", "here/b.py")
    _git(repo, "commit", "-qm", "init")
    (repo / "gone" / "a.py").unlink()
    assert write_default_config(repo) == ConfigResult("created", ("here",))


def test_non_ascii_folder_names_are_read(repo: Path) -> None:
    _write(repo, "módulo/a.py")
    _git(repo, "add", "módulo/a.py")
    assert write_default_config(repo) == ConfigResult("created", ("módulo",))
    text = (repo / "bob.yaml").read_text(encoding="utf-8")
    assert "  include: [módulo]\n" in text


@pytest.mark.parametrize("kind", ["file", "link", "dir"])
def test_existing_bob_yaml_is_preserved(
    repo: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    target = repo / "bob.yaml"
    if kind == "file":
        target.write_bytes(b"base: [\n")
    elif kind == "link":
        os.symlink("nao-existe.yaml", target)
    else:
        target.mkdir()

    def boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError

    monkeypatch.setattr(suite_fingerprint, "_listed_files", boom)
    monkeypatch.setattr(init_config, "load_config", boom)
    assert write_default_config(repo) == ConfigResult("preserved", ())
    if kind == "file":
        assert target.read_bytes() == b"base: [\n"
    elif kind == "link":
        assert os.readlink(target) == "nao-existe.yaml"
    else:
        assert target.is_dir()
    assert _temps(repo) == []


def test_validates_the_temporary_file_before_renaming(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(repo, "src/a.py")
    seen: list[tuple[Path, Path, str, bool]] = []
    real = init_config.load_config

    def spy(path: Path, cwd: Path) -> object:
        seen.append((path, cwd, path.read_text(encoding="utf-8"), (cwd / "bob.yaml").exists()))
        return real(path, cwd)

    monkeypatch.setattr(init_config, "load_config", spy)
    write_default_config(repo)
    assert seen == [
        (
            repo / f"bob.yaml.tmp-{os.getpid()}",
            repo,
            render_config(("src",)),
            False,
        )
    ]
    assert (repo / "bob.yaml").is_file()
    assert _temps(repo) == []


def test_config_error_removes_the_temporary(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(repo, "src/a.py")

    def boom(_path: Path, _cwd: Path) -> None:
        raise ConfigError("x")

    monkeypatch.setattr(init_config, "load_config", boom)
    with pytest.raises(ConfigError):
        write_default_config(repo)
    assert not (repo / "bob.yaml").exists()
    assert _temps(repo) == []


def test_rename_error_removes_the_temporary(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(repo, "src/a.py")

    def boom(_src: Path, _dst: Path) -> None:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(init_config.os, "replace", boom)
    with pytest.raises(PermissionError):
        write_default_config(repo)
    assert not (repo / "bob.yaml").exists()
    assert _temps(repo) == []


def test_write_error_leaves_no_temporary(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(repo, "src/a.py")

    def boom(_self: Path, _data: bytes) -> None:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "write_bytes", boom)
    with pytest.raises(PermissionError):
        write_default_config(repo)
    assert not (repo / "bob.yaml").exists()
    assert _temps(repo) == []


@pytest.mark.parametrize(
    ("rel", "include"),
    [
        ("src/a.py", ("src",)),
        ("app/a.py", ("app",)),
        ("README.md", (".",)),
    ],
)
def test_generated_files_pass_load_config(
    repo: Path, rel: str, include: tuple[str, ...]
) -> None:
    _write(repo, rel)
    write_default_config(repo)
    config = load_config(None, repo)
    assert config.include == include
    assert config.exclude == ("tests", "node_modules", "dist")
    assert config.base == "origin/main"
    assert config.language == "en"


def test_files_come_from_the_suite_fingerprint_listing(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(repo, "lib/x.py")
    _write(repo, "src/y.py")
    seen: list[Path] = []

    def spy(project: Path) -> list[str]:
        seen.append(project)
        return ["lib/x.py"]

    monkeypatch.setattr(suite_fingerprint, "_listed_files", spy)
    assert write_default_config(repo) == ConfigResult("created", ("lib",))
    assert seen == [repo]


def test_git_failure_is_a_tool_error(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    _write(plain, "src/a.py")
    with pytest.raises(ToolError) as caught:
        write_default_config(plain)
    assert reason(caught.value).key == "git.ls_files_failed"
    assert not (plain / "bob.yaml").exists()


def test_second_write_is_preserved_and_changes_nothing(repo: Path) -> None:
    _write(repo, "src/a.py")
    assert write_default_config(repo) == ConfigResult("created", ("src",))
    target = repo / "bob.yaml"
    data = target.read_bytes()
    mtime = target.stat().st_mtime_ns
    assert write_default_config(repo) == ConfigResult("preserved", ())
    assert target.read_bytes() == data
    assert target.stat().st_mtime_ns == mtime


def test_quote_passes_ensure_ascii_false(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, object]] = []
    real = json.dumps

    def spy(item: object, **kwargs: object) -> str:
        seen.append(kwargs)
        return real(item, **kwargs)

    monkeypatch.setattr(init_config.json, "dumps", spy)
    text = render_config(("true",))
    assert len(seen) == 1
    assert seen[0]["ensure_ascii"] is False
    assert text.splitlines()[3] == '  include: ["true"]'
