"""Chave do cache de mutação: a função, a impressão da suíte e a versão do mutmut.

Seams:

1. CLI `bob mutate` sobre o fixture Python e o cache `.bob/mutation-cache.json`.
2. `suite_fingerprint` num repositório git temporário: quais arquivos mudam a
   impressão e quando ela é erro de ferramenta.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from bob_quality.adapters.mutmut import mutmut_stats_key
from bob_quality.mutate import MutationOutcome, _safe_fingerprint
from bob_quality.suite_fingerprint import suite_fingerprint
from bob_quality.tools import ToolError
from helpers import commit_on_branch, commit_on_main, init_python_repo, run_bob

FIXTURE = Path(__file__).parent / "fixtures" / "python_app"
ADD_AND_SCALE = (FIXTURE / "cases" / "add_and_scale.py").read_text()
ADD_TOUCHED = (FIXTURE / "cases" / "add_touched.py").read_text()
BOTH_TOUCHED = ADD_TOUCHED.replace("return value * 2", "return value * 2  # dobro")
SCALE_TEST = "from app.safe import scale\n\n\ndef test_scale() -> None:\n    assert scale(3) == 6\n"
ADD_TEST_WITH_FIXTURE = (
    "from app.safe import add\n\n\ndef test_add(check_sum) -> None:\n    check_sum(add(1, 2))\n"
)
CONFTEST = """\
import pytest


@pytest.fixture
def check_sum():
    def check(value: int) -> None:
        assert value == 3

    return check
"""
WEAK_CONFTEST = CONFTEST.replace("assert value == 3", "assert value is not None")
ADD = "src/app/safe.py::add"
SCALE = "src/app/safe.py::scale"


def test_stats_key_is_the_mutant_prefix_without_the_mutmut_suffix() -> None:
    assert mutmut_stats_key("src/app/safe.py", "add") == "app.safe.x_add"
    assert mutmut_stats_key("pkg/mod.py", "fn") == "pkg.mod.x_fn"


def _repo(tmp_path: Path, source: str = ADD_TOUCHED) -> Path:
    """`add` coberto por tests/test_safe.py e `scale` por tests/test_scale.py."""
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/safe.py", ADD_AND_SCALE, "add and scale")
    commit_on_main(repo, "tests/test_scale.py", SCALE_TEST, "test scale")
    commit_on_branch(repo, "touch", "src/app/safe.py", source, "touch the diff")
    return repo


def _mutate(repo: Path) -> tuple[int, dict, dict]:
    code = run_bob(repo, "mutate", "--base", "main").returncode
    report = json.loads((repo / ".bob" / "report.json").read_text())
    cache = json.loads((repo / ".bob" / "mutation-cache.json").read_text())
    return code, report, cache


def _edit_cache(repo: Path, edit: Callable[[dict], None]) -> None:
    path = repo / ".bob" / "mutation-cache.json"
    cache = json.loads(path.read_text())
    edit(cache)
    path.write_text(json.dumps(cache, indent=2) + "\n")


def _mark(cache: dict) -> None:
    """Um mutante reaproveitado mantém a marca. Um remutado volta com o operador do mutmut."""
    for entry in cache["functions"].values():
        entry["mutants"][0]["operator"] = "SENTINEL"


def _operators(cache: dict, key: str) -> list[str]:
    return [row["operator"] for row in cache["functions"][key]["mutants"]]


def test_a_weakened_conftest_remutates_the_unchanged_function(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    commit_on_branch(repo, "touch", "tests/conftest.py", CONFTEST, "check_sum fixture")
    commit_on_branch(repo, "touch", "tests/test_safe.py", ADD_TEST_WITH_FIXTURE, "use check_sum")
    first_code, first, _cache = _mutate(repo)

    commit_on_branch(repo, "touch", "tests/conftest.py", WEAK_CONFTEST, "weaken check_sum")
    code, report, _cache = _mutate(repo)

    assert first_code == 0
    assert first["mutation"]["remutated"] == [ADD]
    assert code == 3
    assert report["mutation"]["remutated"] == [ADD]
    assert report["mutation"]["reused"] == []
    assert [row["id"] for row in report["survivors"]] == ["app.safe.x_add__mutmut_1"]


USER_MUTMUT_CONFIG = '[tool.mutmut]\nsource_paths = ["src"]\nalso_copy = ["pytest.ini", "data"]\n'


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ({}, {"tests/test_extra.py": "def test_extra() -> None:\n    assert True\n"}),
        ({}, {"pyproject.toml": '[tool.pytest.ini_options]\nmarkers = ["slow"]\n'}),
        (
            {"pyproject.toml": USER_MUTMUT_CONFIG, "data/notes.txt": "v1\n"},
            {"data/notes.txt": "v2\n"},
        ),
    ],
    ids=["new-test-file", "pytest-setting-in-pyproject", "also-copy-file"],
)
def test_a_change_to_what_the_suite_reads_remutates_the_unchanged_function(
    tmp_path: Path, before: dict[str, str], after: dict[str, str]
) -> None:
    repo = _repo(tmp_path)
    _write(repo, before)
    first_code = _mutate(repo)[0]
    _edit_cache(repo, _mark)

    _write(repo, after)
    code, report, cache = _mutate(repo)

    assert first_code == 0
    assert code == 0
    assert report["mutation"]["remutated"] == [ADD]
    assert report["mutation"]["reused"] == []
    assert _operators(cache, ADD) == [""]


def test_an_unrelated_source_change_keeps_the_cached_function(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    first_code = _mutate(repo)[0]
    _edit_cache(repo, _mark)

    commit_on_branch(repo, "touch", "src/app/safe.py", BOTH_TOUCHED, "touch scale too")
    code, report, cache = _mutate(repo)

    assert first_code == 0
    assert code == 0
    assert report["mutation"]["remutated"] == [SCALE]
    assert report["mutation"]["reused"] == [ADD]
    assert _operators(cache, ADD) == ["SENTINEL"]
    assert sorted(cache) == ["functions", "mutmut", "suite"]
    assert cache["mutmut"] == "3.8.0"
    assert cache["suite"] == suite_fingerprint(repo)


@pytest.mark.parametrize(
    ("field", "stale"),
    [("mutmut", "3.7.0"), ("mutmut", None), ("suite", "0" * 64), ("suite", None)],
    ids=["other-mutmut", "no-mutmut", "other-suite", "no-suite"],
)
def test_a_cache_with_another_key_is_fully_remutated(
    tmp_path: Path, field: str, stale: str | None
) -> None:
    repo = _repo(tmp_path, BOTH_TOUCHED)
    first_code, _first, first_cache = _mutate(repo)

    def with_another_key(cache: dict) -> None:
        _mark(cache)
        del cache[field]
        if stale is not None:
            cache[field] = stale

    _edit_cache(repo, with_another_key)
    code, report, cache = _mutate(repo)

    assert first_code == 0
    assert code == 0
    assert report["mutation"]["remutated"] == [ADD, SCALE]
    assert report["mutation"]["reused"] == []
    assert cache[field] == first_cache[field]
    assert _operators(cache, ADD) == [""]
    assert _operators(cache, SCALE) == ["", ""]


def _write(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def _git_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    repo = tmp_path / "suite"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    _write(repo, {"src/app/safe.py": ADD_AND_SCALE, **files})
    return repo


SUITE_FILES = {
    "tests/data.json": ("{}\n", "[]\n"),
    "test/fixture.txt": ("a\n", "b\n"),
    "pkg/tests/case.txt": ("a\n", "b\n"),
    "conftest.py": ("A = 1\n", "A = 2\n"),
    "src/app/conftest_db.py": ("A = 1\n", "A = 2\n"),
    "test_root.py": ("A = 1\n", "A = 2\n"),
    "src/app/safe_test.py": ("A = 1\n", "A = 2\n"),
    "pytest.ini": ("[pytest]\n", "[pytest]\naddopts = -q\n"),
    "tox.ini": ("[tox]\n", "[tox]\nenvlist = py\n"),
    "setup.cfg": ("[metadata]\nname = a\n", "[metadata]\nname = b\n"),
    "pyproject.toml": ('[project]\nname = "a"\n', '[project]\nname = "b"\n'),
    "uv.lock": ("a\n", "b\n"),
    "poetry.lock": ("a\n", "b\n"),
    "Pipfile.lock": ("a\n", "b\n"),
    "pdm.lock": ("a\n", "b\n"),
}


@pytest.mark.parametrize("name", sorted(SUITE_FILES))
def test_a_suite_file_changes_the_fingerprint_when_added_or_edited(
    tmp_path: Path, name: str
) -> None:
    repo = _git_repo(tmp_path, {})
    first, second = SUITE_FILES[name]
    without = suite_fingerprint(repo)

    _write(repo, {name: first})
    added = suite_fingerprint(repo)
    _write(repo, {name: second})
    edited = suite_fingerprint(repo)

    assert len({without, added, edited}) == 3


@pytest.mark.parametrize(
    "name",
    [
        "src/app/safe.py",
        "README.md",
        "docs/test_plan.md",
        "mutants/tests/test_safe.py",
        ".bob/conftest.py",
        "tests/__pycache__/test_safe.cpython-312.pyc",
        "src/app/__pycache__/conftest.cpython-312.pyc",
        "tests/ignored.txt",
    ],
)
def test_other_files_leave_the_fingerprint_alone(tmp_path: Path, name: str) -> None:
    repo = _git_repo(tmp_path, {".gitignore": "tests/ignored.txt\n", "tests/test_safe.py": "A = 1\n"})
    before = suite_fingerprint(repo)

    _write(repo, {name: "changed\n"})

    assert suite_fingerprint(repo) == before


def test_renaming_or_deleting_a_staged_test_changes_the_fingerprint(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path, {"tests/test_a.py": "A = 1\n"})
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    staged = suite_fingerprint(repo)

    (repo / "tests" / "test_a.py").rename(repo / "tests" / "test_b.py")
    renamed = suite_fingerprint(repo)
    (repo / "tests" / "test_b.py").unlink()
    deleted = suite_fingerprint(repo)

    assert len({staged, renamed, deleted}) == 3


ALSO_COPY_CONFIGS = {
    "pyproject": {"pyproject.toml": '[tool.mutmut]\nalso_copy = ["data", "notes.txt"]\n'},
    "setup.cfg": {"setup.cfg": "[mutmut]\nalso_copy =\n    data\n    notes.txt\n"},
}


@pytest.mark.parametrize("config", sorted(ALSO_COPY_CONFIGS))
@pytest.mark.parametrize(
    ("name", "counted"),
    [
        ("data/a.txt", True),
        ("data/deep/b.txt", True),
        ("notes.txt", True),
        ("other.txt", False),
        ("datafile.txt", False),
    ],
)
def test_the_user_also_copy_entries_join_the_fingerprint(
    tmp_path: Path, config: str, name: str, counted: bool
) -> None:
    repo = _git_repo(tmp_path, ALSO_COPY_CONFIGS[config])
    before = suite_fingerprint(repo)

    _write(repo, {name: "changed\n"})

    assert (suite_fingerprint(repo) != before) is counted


def test_a_mutmut_section_in_pyproject_hides_the_setup_cfg_one(tmp_path: Path) -> None:
    repo = _git_repo(
        tmp_path,
        {
            "pyproject.toml": '[tool.mutmut]\nsource_paths = ["src"]\n',
            "setup.cfg": "[mutmut]\nalso_copy =\n    data\n",
        },
    )
    before = suite_fingerprint(repo)

    _write(repo, {"data/a.txt": "changed\n"})

    assert suite_fingerprint(repo) == before


@pytest.mark.parametrize(
    ("files", "message"),
    [
        ({"pyproject.toml": "[tool.mutmut\n"}, r"^pyproject\.toml ilegível: "),
        ({"setup.cfg": "also_copy = data\n"}, r"^setup\.cfg ilegível: "),
    ],
    ids=["pyproject", "setup.cfg"],
)
def test_an_unreadable_config_is_a_tool_error(
    tmp_path: Path, files: dict[str, str], message: str
) -> None:
    repo = _git_repo(tmp_path, files)

    with pytest.raises(ToolError, match=message):
        suite_fingerprint(repo)


def test_outside_a_git_repository_the_fingerprint_is_a_tool_error(tmp_path: Path) -> None:
    with pytest.raises(ToolError, match=r"^git ls-files falhou: fatal: not a git repository"):
        suite_fingerprint(tmp_path)


def test_without_git_the_fingerprint_is_a_missing_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _git_repo(tmp_path, {})
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    with pytest.raises(ToolError) as caught:
        suite_fingerprint(repo)

    assert str(caught.value) == "ferramenta ausente: git"


def test_the_gate_stops_with_exit_4_when_the_fingerprint_fails(tmp_path: Path) -> None:
    versions = {"mutmut": "3.8.0"}
    waivers = [{"id": "keep-me", "reason": "porque"}]

    failed = _safe_fingerprint(tmp_path, versions, waivers)

    assert isinstance(failed, MutationOutcome)
    assert failed.exit_code == 4
    assert failed.result.status == "not_run"
    assert failed.result.reason.startswith("git ls-files falhou: fatal: not a git repository")
    assert failed.versions == versions
    assert failed.waivers == waivers
