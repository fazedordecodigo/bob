"""O mutmut roda em `<out>/mutmut`. O repositório só é lido."""

from __future__ import annotations

from pathlib import Path

from bob_quality.config import Config
from bob_quality.messages import render
from bob_quality.models import CyclomaticFunction
from bob_quality.mutate import _collect_fresh, _mutmut_workdir

INJECTED = "[mutmut]\nsource_paths =\n    src\nalso_copy =\n    pytest.ini\n"


def _repo(root: Path) -> Path:
    for folder in (".git", "mutants", "src/app", "tests", "node_modules"):
        (root / folder).mkdir(parents=True)
    (root / "mutants" / "marker").write_text("root mutants")
    (root / "src" / "app" / "m.py").write_text("def f():\n    return 1\n")
    (root / "pytest.ini").write_text("[pytest]\n")
    return root


def _entries(work: Path) -> dict[str, str]:
    return {
        entry.name: str(entry.readlink()) if entry.is_symlink() else "file"
        for entry in sorted(work.iterdir())
        if entry.name != "mutants"
    }


def test_workdir_links_each_top_level_entry_except_git_mutants_and_the_out_dir(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path / "repo")
    real = repo.resolve()

    work = _mutmut_workdir(repo, repo / ".bob", ["src"])

    assert work == repo / ".bob" / "mutmut"
    assert _entries(work) == {
        "node_modules": str(real / "node_modules"),
        "pytest.ini": str(real / "pytest.ini"),
        "setup.cfg": "file",
        "src": str(real / "src"),
        "tests": str(real / "tests"),
    }
    assert (work / "setup.cfg").read_text() == INJECTED
    assert (work / "mutants" / "node_modules").readlink() == real / "node_modules"
    assert not (repo / "setup.cfg").exists()
    assert sorted(path.name for path in (repo / "mutants").iterdir()) == ["marker"]


def test_workdir_appends_the_block_to_the_repo_setup_cfg_without_writing_it(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path / "repo")
    (repo / "setup.cfg").write_text("[metadata]\nname = app\n\n")

    work = _mutmut_workdir(repo, repo / ".bob", ["lib", "pkg"])

    assert not (work / "setup.cfg").is_symlink()
    assert (work / "setup.cfg").read_text() == (
        "[metadata]\nname = app\n\n"
        "[mutmut]\nsource_paths =\n    lib\n    pkg\nalso_copy =\n    pytest.ini\n"
    )
    assert (repo / "setup.cfg").read_text() == "[metadata]\nname = app\n\n"


def test_workdir_defaults_the_source_path_to_src(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")

    work = _mutmut_workdir(repo, repo / ".bob", [])

    assert (work / "setup.cfg").read_text() == INJECTED


def test_workdir_links_setup_cfg_when_the_repo_configures_mutmut(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    (repo / "setup.cfg").write_text("[mutmut]\nsource_paths =\n    lib\n")

    work = _mutmut_workdir(repo, repo / ".bob", ["src"])

    assert (work / "setup.cfg").readlink() == repo.resolve() / "setup.cfg"
    assert (repo / "setup.cfg").read_text() == "[mutmut]\nsource_paths =\n    lib\n"


def test_rebuilding_the_workdir_follows_the_repo_and_keeps_mutants(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    work = _mutmut_workdir(repo, repo / ".bob", ["src"])
    (work / "mutants" / "kept").write_text("mutmut state")
    (repo / "pytest.ini").unlink()
    (repo / "notes.txt").write_text("new")
    (repo / "setup.cfg").write_text("[metadata]\n")
    (repo / "pyproject.toml").write_text("[tool.mutmut]\nsource_paths = ['src']\n")

    again = _mutmut_workdir(repo, repo / ".bob", ["src"])

    real = repo.resolve()
    assert again == work
    assert _entries(work) == {
        "node_modules": str(real / "node_modules"),
        "notes.txt": str(real / "notes.txt"),
        "pyproject.toml": str(real / "pyproject.toml"),
        "setup.cfg": str(real / "setup.cfg"),
        "src": str(real / "src"),
        "tests": str(real / "tests"),
    }
    assert (work / "mutants" / "kept").read_text() == "mutmut state"


def test_an_out_dir_outside_the_repo_links_every_entry_but_git_and_mutants(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path / "repo")
    (repo / ".bob").mkdir()

    work = _mutmut_workdir(repo, tmp_path / "elsewhere", ["src"])

    assert work == tmp_path / "elsewhere" / "mutmut"
    assert sorted(_entries(work)) == [
        ".bob",
        "node_modules",
        "pytest.ini",
        "setup.cfg",
        "src",
        "tests",
    ]


def test_a_workdir_that_cannot_be_built_is_a_tool_error(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    out = repo / ".bob"
    out.mkdir()
    (out / "mutmut").write_text("not a directory")
    changed = [CyclomaticFunction("src/app/m.py", "f", 1, 2, 1)]
    rows = [{"id": "src/app/m.py::f", "reason": "r", "author": "a", "date": "d"}]

    outcome = _collect_fresh(repo, Config(), out, changed, None, {"mutmut": "3.8.0"}, rows, [])

    assert not isinstance(outcome, list)
    assert outcome.exit_code == 4
    assert outcome.result.status == "not_run"
    assert render(outcome.result.reason, "en") == (
        f"could not prepare the mutmut workdir {out / 'mutmut'}:"
        f" [Errno 17] File exists: '{out / 'mutmut'}'"
    )
    assert outcome.versions == {"mutmut": "3.8.0"}
    assert outcome.waivers == rows
