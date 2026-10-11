"""Chave do cache de mutação: função, testes que a cobrem e versão do mutmut.

Seams:

1. CLI `bob mutate` sobre o fixture Python e o cache `.bob/mutation-cache.json`.
2. Adaptador mutmut: o texto de `mutants/mutmut-stats.json` (mutmut==3.8.0)
   vira os arquivos de teste de cada função.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

import pytest

import bob_quality.mutate as mutate_module
from bob_quality.adapters.mutmut import MutmutParseError, covering_test_files, mutmut_stats_key
from bob_quality.config import load_config
from bob_quality.diff import changed_lines
from bob_quality.mutate import run_mutation_gate
from bob_quality.mutmut_tool import mutmut_stats
from bob_quality.tools import ToolError
from helpers import commit_on_branch, commit_on_main, init_python_repo, run_bob

FIXTURE = Path(__file__).parent / "fixtures" / "python_app"
ADD_AND_SCALE = (FIXTURE / "cases" / "add_and_scale.py").read_text()
ADD_TOUCHED = (FIXTURE / "cases" / "add_touched.py").read_text()
BOTH_TOUCHED = ADD_TOUCHED.replace("return value * 2", "return value * 2  # dobro")
ADD_TEST = (FIXTURE / "tests" / "test_safe.py").read_text()
WEAK_ADD_TEST = "from app.safe import add\n\n\ndef test_add() -> None:\n    assert add(1, 2) is not None\n"
SCALE_TEST = "from app.safe import scale\n\n\ndef test_scale() -> None:\n    assert scale(3) == 6\n"
ADD = "src/app/safe.py::add"
SCALE = "src/app/safe.py::scale"

STATS = """\
{
    "tests_by_mangled_function_name": {
        "app.safe.x_add": [
            "tests/test_safe.py::test_add",
            "tests/test_param.py::test_add_param[1]",
            "tests/test_param.py::test_add_param[a::b]",
            "tests/test_box.py::TestBox::test_add"
        ],
        "app.safe.x_scale": []
    },
    "duration_by_test": {},
    "stats_time": 0.1
}
"""


def test_stats_key_is_the_mutant_prefix_without_the_mutmut_suffix() -> None:
    assert mutmut_stats_key("src/app/safe.py", "add") == "app.safe.x_add"
    assert mutmut_stats_key("pkg/mod.py", "fn") == "pkg.mod.x_fn"


def test_covering_test_files_keep_the_file_of_each_node_id() -> None:
    assert covering_test_files(STATS) == {
        "app.safe.x_add": {"tests/test_safe.py", "tests/test_param.py", "tests/test_box.py"},
        "app.safe.x_scale": set(),
    }


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("{", r"^stats do mutmut ilegível: Expecting property name"),
        ("[]", r"^stats do mutmut sem tests_by_mangled_function_name$"),
        ('{"duration_by_test": {}}', r"^stats do mutmut sem tests_by_mangled_function_name$"),
        (
            '{"tests_by_mangled_function_name": []}',
            r"^stats do mutmut sem tests_by_mangled_function_name$",
        ),
        (
            '{"tests_by_mangled_function_name": {"app.safe.x_add": "tests/test_safe.py"}}',
            r"^testes fora do contrato no stats do mutmut: 'tests/test_safe.py'$",
        ),
        (
            '{"tests_by_mangled_function_name": {"app.safe.x_add": ["tests/a.py::t", 1]}}',
            r"^testes fora do contrato no stats do mutmut: \['tests/a.py::t', 1\]$",
        ),
    ],
)
def test_stats_outside_the_pinned_shape_are_rejected(raw: str, message: str) -> None:
    with pytest.raises(MutmutParseError, match=message):
        covering_test_files(raw)


def test_mutmut_stats_reads_the_file_that_mutmut_run_writes(tmp_path: Path) -> None:
    (tmp_path / "mutants").mkdir()
    (tmp_path / "mutants" / "mutmut-stats.json").write_text(STATS)

    assert mutmut_stats(tmp_path) == STATS


def test_missing_mutmut_stats_is_a_tool_error(tmp_path: Path) -> None:
    with pytest.raises(ToolError) as caught:
        mutmut_stats(tmp_path)

    assert str(caught.value) == "stats do mutmut ausente: mutants/mutmut-stats.json"


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


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def test_a_changed_covering_test_remutates_the_unchanged_function(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    first_code, first, first_cache = _mutate(repo)

    (repo / "tests" / "test_safe.py").write_text(WEAK_ADD_TEST)
    code, report, cache = _mutate(repo)

    assert first_code == 0
    assert first["mutation"]["remutated"] == [ADD]
    assert code == 3
    assert report["mutation"]["remutated"] == [ADD]
    assert report["mutation"]["reused"] == []
    assert [row["id"] for row in report["survivors"]] == ["app.safe.x_add__mutmut_1"]
    assert first_cache["functions"][ADD]["tests"] == {"tests/test_safe.py": _sha(ADD_TEST)}
    assert cache["functions"][ADD]["tests"] == {"tests/test_safe.py": _sha(WEAK_ADD_TEST)}


def test_a_changed_unrelated_test_keeps_the_cached_function(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    first_code = _mutate(repo)[0]
    _edit_cache(repo, _mark)

    (repo / "tests" / "test_scale.py").write_text(SCALE_TEST.replace("scale(3) == 6", "scale(4) == 8"))
    code, report, cache = _mutate(repo)

    assert first_code == 0
    assert code == 0
    assert report["mutation"]["remutated"] == []
    assert report["mutation"]["reused"] == [ADD]
    assert _operators(cache, ADD) == ["SENTINEL"]
    assert cache["functions"][ADD]["tests"] == {"tests/test_safe.py": _sha(ADD_TEST)}


@pytest.mark.parametrize("stale", [{"mutmut": "3.7.0"}, {}], ids=["other-version", "no-version"])
def test_a_cache_from_another_mutmut_version_is_fully_remutated(
    tmp_path: Path, stale: dict[str, str]
) -> None:
    repo = _repo(tmp_path, BOTH_TOUCHED)
    first_code, _first, first_cache = _mutate(repo)

    def from_another_version(cache: dict) -> None:
        _mark(cache)
        del cache["mutmut"]
        cache.update(stale)

    _edit_cache(repo, from_another_version)
    code, report, cache = _mutate(repo)

    assert first_code == 0
    assert first_cache["mutmut"] == "3.8.0"
    assert sorted(first_cache["functions"]) == [ADD, SCALE]
    assert code == 0
    assert report["mutation"]["remutated"] == [ADD, SCALE]
    assert report["mutation"]["reused"] == []
    assert cache["mutmut"] == "3.8.0"
    assert _operators(cache, ADD) == [""]
    assert _operators(cache, SCALE) == ["", ""]


def test_an_entry_without_tests_from_the_old_format_is_remutated(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    first_code = _mutate(repo)[0]

    def old_format(cache: dict) -> None:
        _mark(cache)
        del cache["functions"][ADD]["tests"]

    _edit_cache(repo, old_format)
    code, report, cache = _mutate(repo)

    assert first_code == 0
    assert code == 0
    assert report["mutation"]["remutated"] == [ADD]
    assert report["mutation"]["reused"] == []
    assert _operators(cache, ADD) == [""]
    assert cache["functions"][ADD]["tests"] == {"tests/test_safe.py": _sha(ADD_TEST)}


def test_a_moved_covering_test_remutates_and_records_the_new_file(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    first_code = _mutate(repo)[0]

    (repo / "tests" / "test_safe.py").rename(repo / "tests" / "test_add.py")
    code, report, cache = _mutate(repo)

    assert first_code == 0
    assert code == 0
    assert report["mutation"]["remutated"] == [ADD]
    assert report["mutation"]["reused"] == []
    assert cache["functions"][ADD]["tests"] == {"tests/test_add.py": _sha(ADD_TEST)}


@pytest.mark.parametrize(
    ("files", "reason"),
    [
        ({}, "stats do mutmut ausente: mutants/mutmut-stats.json"),
        (
            {"mutants/mutmut-stats.json": "{}"},
            "stats do mutmut sem tests_by_mangled_function_name",
        ),
    ],
    ids=["missing", "bad-shape"],
)
def test_unreadable_stats_after_a_successful_run_is_a_tool_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, files: dict[str, str], reason: str
) -> None:
    repo = _repo(tmp_path)
    for relative, text in files.items():
        (repo / relative).parent.mkdir(parents=True, exist_ok=True)
        (repo / relative).write_text(text)
    monkeypatch.setattr(mutate_module, "run_mutmut", lambda *_args: None)
    monkeypatch.setattr(
        mutate_module, "mutmut_results", lambda _cwd: "    app.safe.x_add__mutmut_1: killed\n"
    )

    outcome = run_mutation_gate(
        repo, load_config(None, repo), changed_lines(repo, "main"), repo / ".bob"
    )

    assert outcome.exit_code == 4
    assert outcome.result.status == "not_run"
    assert outcome.result.reason == reason
    assert not (repo / ".bob" / "mutation-cache.json").exists()
