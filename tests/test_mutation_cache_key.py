"""Chave do cache de mutação: a função, a impressão da suíte e a versão do mutmut.

Seams:

1. CLI `bob mutate` sobre o fixture Python e o cache `.bob/mutation-cache.json`.
2. `suite_fingerprint` num repositório git temporário: quais arquivos mudam a
   impressão e quando ela é erro de ferramenta.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

import pytest

from bob_quality.adapters.mutmut import mutmut_stats_key
from bob_quality.mutate import (
    MutationOutcome,
    _Cache,
    _CacheLineError,
    _CacheView,
    _cached_mutants,
    _mutant_from_row,
    _read_cache,
    _safe_cache,
    _safe_fingerprint,
    _view_cache,
    _write_cache,
)
from bob_quality.suite_fingerprint import suite_fingerprint
from bob_quality.tools import ToolError
from helpers import commit_on_branch, commit_on_main, in_both, init_python_repo, run_bob

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
OFFSET = "src/app/safe.py::offset"
CLAMP = "src/app/safe.py::clamp"
REMOVED = "src/app/safe.py::removed"
OUTSIDE = """
def offset(value: int) -> int:
    return value + 1


def clamp(value: int) -> int:
    return value if value < 10 else 10
"""
EXTRA_TEST = "def test_extra() -> None:\n    assert True\n"
CLAMP_WAIVER = """\
waivers:
  - id: src/app/safe.py::clamp
    reason: o limite já está coberto
    author: ada
    date: '2026-10-11'
  - id: src/app/safe.py::removed
    reason: a função não está mais no arquivo
    author: ada
    date: '2026-10-11'
"""


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


def _plant(repo: Path, cache: dict[str, object]) -> Path:
    path = repo / ".bob" / "mutation-cache.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache) + "\n")
    return path


def _assert_invalid_cache(repo: Path, path: Path, before: bytes, detail: str) -> None:
    result = run_bob(repo, "mutate", "--base", "main")
    assert result.returncode == 4, result.stderr
    report = json.loads((repo / ".bob" / "report.json").read_text())
    mutate = next(gate for gate in report["gates"] if gate["name"] == "mutate")
    assert report["exit_code"] == 4
    assert mutate["status"] == "not_run"
    assert mutate["reason"] == f"invalid mutation cache: {detail}"
    assert path.read_bytes() == before


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


def _cached_row(name: str, status: str) -> dict:
    return {
        "file": "src/app/safe.py",
        "name": name,
        "mutants": [
            {
                "id": f"{name}-planted",
                "function": name,
                "file": "src/app/safe.py",
                "line": 1,
                "operator": "SENTINEL",
                "status": status,
            }
        ],
    }


def test_a_new_suite_file_remutates_an_unwaived_survivor_outside_the_diff(
    tmp_path: Path,
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/safe.py", ADD_AND_SCALE + OUTSIDE, "functions outside the diff")
    commit_on_main(repo, "tests/test_scale.py", SCALE_TEST, "test scale")
    commit_on_branch(repo, "touch", "src/app/safe.py", ADD_TOUCHED + OUTSIDE, "touch add")
    first_code, _first, first_cache = _mutate(repo)

    def plant(cache: dict) -> None:
        cache["functions"][ADD]["mutants"][0]["operator"] = "SENTINEL"
        cache["functions"][SCALE] = _cached_row("scale", "survived")
        cache["functions"][OFFSET] = _cached_row("offset", "killed")
        cache["functions"][CLAMP] = _cached_row("clamp", "survived")
        cache["functions"][REMOVED] = _cached_row("removed", "survived")

    _edit_cache(repo, plant)
    (repo / ".bob" / "waivers.yaml").write_text(CLAMP_WAIVER, encoding="utf-8")
    _write(repo, {"tests/test_extra.py": EXTRA_TEST})
    code, report, cache = _mutate(repo)

    assert first_code == 0
    assert sorted(first_cache["functions"]) == [ADD]
    assert code == 0
    assert report["mutation"]["remutated"] == [ADD, SCALE]
    assert report["mutation"]["reused"] == []
    assert sorted(cache["functions"]) == [ADD, CLAMP, SCALE]
    assert _operators(cache, ADD) == [""]
    assert "SENTINEL" not in _operators(cache, SCALE)
    assert cache["functions"][CLAMP] == _cached_row("clamp", "survived")
    assert cache["suite"] == suite_fingerprint(repo)
    assert cache["mutmut"] == first_cache["mutmut"]
    assert OFFSET not in report["mutation"]["remutated"]
    assert CLAMP not in report["mutation"]["remutated"]
    assert CLAMP not in report["mutation"]["reused"]
    assert REMOVED not in report["mutation"]["remutated"]
    assert OFFSET not in cache["functions"]
    assert REMOVED not in cache["functions"]

    again_code, again_report, again_cache = _mutate(repo)

    assert again_code == 0
    assert again_report["mutation"]["remutated"] == []
    assert again_report["mutation"]["reused"] == [ADD]
    assert sorted(again_cache["functions"]) == [ADD, CLAMP]
    assert again_cache["functions"][CLAMP] == _cached_row("clamp", "survived")
    assert _operators(again_cache, ADD) == [""]
    assert OFFSET not in again_cache["functions"]
    assert SCALE not in again_cache["functions"]
    assert REMOVED not in again_cache["functions"]


def test_a_non_numeric_mutant_line_exits_4_and_leaves_the_cache_file(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    assert _mutate(repo)[0] == 0
    path = repo / ".bob" / "mutation-cache.json"

    def corrupt(cache: dict) -> None:
        cache["functions"][ADD]["mutants"][0]["line"] = "nope"

    _edit_cache(repo, corrupt)
    before = path.read_bytes()

    result = run_bob(repo, "mutate", "--base", "main")
    assert result.returncode == 4, result.stderr
    report = json.loads((repo / ".bob" / "report.json").read_text())
    mutate = next(gate for gate in report["gates"] if gate["name"] == "mutate")

    assert report["exit_code"] == 4
    assert mutate["status"] == "not_run"
    assert mutate["reason"] == (
        "invalid mutation cache: invalid literal for int() with base 10: 'nope'"
    )
    assert path.read_bytes() == before
    assert sorted(path.parent.glob("mutation-cache.json*")) == [path]
    with pytest.raises(_CacheLineError) as caught:
        _mutant_from_row({"id": "add-planted", "line": "nope"})
    assert str(caught.value) == "invalid literal for int() with base 10: 'nope'"
    assert _mutant_from_row({"id": "add-planted", "line": 4}).line == 4
    assert _mutant_from_row({"id": "add-planted"}).line == 0


@pytest.mark.parametrize(
    ("line", "detail"),
    [
        ([1], "int() argument must be a string, a bytes-like object or a real number, not 'list'"),
        (
            {"a": 1},
            "int() argument must be a string, a bytes-like object or a real number, not 'dict'",
        ),
    ],
    ids=["list", "object"],
)
def test_a_non_scalar_mutant_line_exits_4_and_leaves_the_cache_file(
    tmp_path: Path, line: object, detail: str
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    path = _plant(
        repo,
        {
            "mutmut": "3.8.0",
            "suite": "abc",
            "functions": {
                ADD: {"mutants": [{"id": "add-planted", "line": line, "status": "killed"}]}
            },
        },
    )
    before = path.read_bytes()

    _assert_invalid_cache(repo, path, before, detail)
    with pytest.raises(_CacheLineError) as caught:
        _mutant_from_row({"id": "add-planted", "line": line})
    assert str(caught.value) == detail


def test_a_non_utf8_cache_exits_4_and_leaves_the_file(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    path = repo / ".bob" / "mutation-cache.json"
    path.parent.mkdir()
    path.write_bytes(b"\xff")
    before = path.read_bytes()
    detail = "'utf-8' codec can't decode byte 0xff in position 0: invalid start byte"

    _assert_invalid_cache(repo, path, before, detail)
    versions = {"mutmut": "3.8.0"}
    waivers = [{"id": "kept"}]
    view, broken = _safe_cache(_Cache(path, {"mutmut": "3.8.0", "suite": "abc"}), versions, waivers)
    assert broken is not None
    assert view == _CacheView({}, False)
    assert broken.exit_code == 4
    assert broken.result.status == "not_run"
    assert broken.versions == versions
    assert broken.waivers == waivers
    assert in_both(broken.result.reason or "")[0] == f"invalid mutation cache: {detail}"
    assert path.read_bytes() == before

    absent = _read_cache(_Cache(tmp_path / "missing.json", {"mutmut": "3.8.0", "suite": "abc"}))
    assert absent == _CacheView({}, True)
    alien = _view_cache(["nope"], {"mutmut": "3.8.0", "suite": "abc"})
    assert alien == _CacheView({}, True)
    key = {"mutmut": "3.8.0", "suite": "abc"}
    weird = _view_cache({"functions": ["nope"], **key}, key)
    assert weird == _CacheView({}, True)
    parsed = _cached_mutants(
        {
            "mutants": [
                {"id": "add-planted", "line": 4, "status": "killed"},
                {"id": 3, "line": 1},
                "skip",
            ]
        }
    )
    assert [(item.id, item.line, item.status) for item in parsed] == [("add-planted", 4, "killed")]
    assert _cached_mutants({}) == []

    valid = tmp_path / "valid" / "mutation-cache.json"
    valid.parent.mkdir()
    stored = {"mutmut": "3.8.0", "suite": "abc", "functions": {ADD: {"hash": "x"}}}
    valid.write_bytes(json.dumps(stored).encode())
    view, ok = _safe_cache(_Cache(valid, key), versions, waivers)
    assert ok is None
    assert view == _CacheView({ADD: {"hash": "x"}}, True)


def test_a_publish_fsyncs_a_private_temp_and_ignores_a_tmp_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "mutation-cache.json"
    path.write_text('{"kept": true}\n')
    cache = _Cache(path, {"mutmut": "3.8.0", "suite": "abc"})
    stored = {"src/app/safe.py::add": {"hash": "x"}}
    expected = json.dumps({"mutmut": "3.8.0", "suite": "abc", "functions": stored}, indent=2) + "\n"
    sentinel = tmp_path / "sentinel"
    sentinel.write_text("keep")
    planted = path.with_name("mutation-cache.json.tmp")
    planted.symlink_to(sentinel)
    synced: list[int] = []
    real_fsync = os.fsync
    real_replace = os.replace

    def spy_fsync(fd: int) -> None:
        synced.append(os.fstat(fd).st_ino)
        real_fsync(fd)

    def spy_replace(src: str, dst: str) -> None:
        assert synced == [os.stat(src).st_ino]
        assert Path(src).parent == Path(dst).parent
        real_replace(src, dst)

    monkeypatch.setattr(os, "fsync", spy_fsync)
    monkeypatch.setattr(os, "replace", spy_replace)
    _write_cache(cache, stored)

    assert path.read_text() == expected
    assert not path.is_symlink()
    assert sentinel.read_text() == "keep"
    assert planted.is_symlink()
    assert sorted(item.name for item in path.parent.iterdir()) == [
        "mutation-cache.json",
        "mutation-cache.json.tmp",
        "sentinel",
    ]
    assert synced


def test_concurrent_publishes_leave_one_complete_cache(tmp_path: Path) -> None:
    path = tmp_path / "mutation-cache.json"
    path.write_text("{}\n")
    cache = _Cache(path, {"mutmut": "3.8.0", "suite": "abc"})
    errors: list[BaseException] = []

    def publish(mark: int) -> None:
        try:
            _write_cache(cache, {f"src/app/safe.py::f{mark}": {"hash": str(mark)}})
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=publish, args=(mark,)) for mark in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    loaded = json.loads(path.read_text())
    assert errors == []
    assert loaded["mutmut"] == "3.8.0"
    assert loaded["suite"] == "abc"
    assert list(loaded["functions"]) in [[f"src/app/safe.py::f{mark}"] for mark in range(8)]
    assert list(path.parent.iterdir()) == [path]


def test_a_failed_publish_leaves_the_previous_file_and_a_successful_publish_replaces_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "mutation-cache.json"
    path.write_text('{"mutmut": "3.8.0", "suite": "abc", "functions": {}}\n')
    before = path.read_bytes()
    cache = _Cache(path, {"mutmut": "3.8.0", "suite": "abc"})
    stored = {"src/app/safe.py::add": {"hash": "x"}}
    expected = {"mutmut": "3.8.0", "suite": "abc", "functions": stored}
    spilled: dict[str, object] = {}

    def fail_replace(src: str, dst: str) -> None:
        spilled["text"] = Path(src).read_text()
        spilled["parent"] = str(Path(src).parent)
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)
    caught: OSError | None = None
    try:
        _write_cache(cache, stored)
    except OSError as exc:
        caught = exc

    assert path.read_bytes() == before, "write_text truncated the destination"
    assert str(caught) == "replace failed"
    assert json.loads(str(spilled["text"])) == expected
    assert spilled["parent"] == str(path.parent)
    assert list(path.parent.iterdir()) == [path]

    monkeypatch.undo()
    nested = tmp_path / "fresh" / "deeper" / "mutation-cache.json"
    _write_cache(_Cache(nested, cache.key), stored)
    expected_text = json.dumps(expected, indent=2) + "\n"

    assert nested.read_text() == expected_text
    assert list(nested.parent.iterdir()) == [nested]


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
    "pyproject": {
        "pyproject.toml": '[tool.mutmut]\nalso_copy = ["data", "notes.txt", "shared data"]\n'
    },
    "setup.cfg": {"setup.cfg": "[mutmut]\nalso_copy =\n    data\n    notes.txt\n    shared data\n"},
}


@pytest.mark.parametrize("config", sorted(ALSO_COPY_CONFIGS))
@pytest.mark.parametrize(
    ("name", "counted"),
    [
        ("data/a.txt", True),
        ("data/deep/b.txt", True),
        ("notes.txt", True),
        ("shared data/a.txt", True),
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
    ("files", "english", "portuguese", "detail"),
    [
        (
            {"pyproject.toml": "[tool.mutmut\n"},
            "unreadable pyproject.toml: ",
            "pyproject.toml ilegível: ",
            "Expected ']' at the end of a table declaration",
        ),
        (
            {"setup.cfg": "also_copy = data\n"},
            "unreadable setup.cfg: ",
            "setup.cfg ilegível: ",
            "File contains no section headers",
        ),
    ],
    ids=["pyproject", "setup.cfg"],
)
def test_an_unreadable_config_is_a_tool_error(
    tmp_path: Path, files: dict[str, str], english: str, portuguese: str, detail: str
) -> None:
    repo = _git_repo(tmp_path, files)

    with pytest.raises(ToolError) as caught:
        suite_fingerprint(repo)

    rendered = in_both(caught.value)
    assert rendered[0].startswith(english)
    assert rendered[1].startswith(portuguese)
    assert detail in rendered[0]
    assert detail in rendered[1]


def test_outside_a_git_repository_the_fingerprint_is_a_tool_error(tmp_path: Path) -> None:
    with pytest.raises(ToolError) as caught:
        suite_fingerprint(tmp_path)

    english, portuguese = in_both(caught.value)
    assert english.startswith("git ls-files failed: fatal: not a git repository")
    assert portuguese.startswith("git ls-files falhou: fatal: not a git repository")


def test_without_git_the_fingerprint_is_a_missing_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _git_repo(tmp_path, {})
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    with pytest.raises(ToolError) as caught:
        suite_fingerprint(repo)

    assert in_both(caught.value) == ("missing tool: git", "ferramenta ausente: git")


def test_the_gate_stops_with_exit_4_when_the_fingerprint_fails(tmp_path: Path) -> None:
    versions = {"mutmut": "3.8.0"}
    waivers = [{"id": "keep-me", "reason": "porque"}]

    failed = _safe_fingerprint(tmp_path, versions, waivers)

    assert isinstance(failed, MutationOutcome)
    assert failed.exit_code == 4
    assert failed.result.status == "not_run"
    assert in_both(failed.result.reason)[0].startswith(
        "git ls-files failed: fatal: not a git repository"
    )
    assert failed.versions == versions
    assert failed.waivers == waivers
