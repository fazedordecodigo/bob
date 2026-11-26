"""`run_mutation_gate` no mesmo processo, com o mutmut trocado por um falso.

Os testes da CLI rodam o bob num subprocesso, que importa o pacote instalado e não o mutante.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import bob_quality.mutate as mutate
from bob_quality.config import Config
from bob_quality.diff import changed_lines
from bob_quality.models import CyclomaticFunction, GateResult
from bob_quality.mutate import CACHE_NAME, run_mutation_gate
from bob_quality.tools import ToolError
from bob_quality.waivers import Waiver
from helpers import commit_on_branch, init_python_repo

FIXTURE = Path(__file__).parent / "fixtures" / "python_app"
CLASSIFY = (FIXTURE / "cases" / "survive_classify.py").read_text()
WEAK_TEST = (FIXTURE / "cases" / "test_classify_weak.py").read_text()
CONFIG = Config(include=("src/app",))
VERSIONS = {"mutmut": "3.8.0"}
WAIVER = {
    "id": "src/app/weak.py::classify",
    "reason": "o contrato exige estritamente maior que zero",
    "author": "ada",
    "date": "2026-10-12",
}
RESULTS = (
    "    app.weak.x_classify__mutmut_1: survived\n"
    "    app.weak.x_classify__mutmut_2: killed\n"
    "    app.other.x_elsewhere__mutmut_1: survived\n"
)
SHOW = "--- src/app/weak.py\n+++ src/app/weak.py\n@@ -2 +2 @@\n-    if n > 0:\n+    if n >= 0:\n"
SURVIVOR = {
    "id": "app.weak.x_classify__mutmut_1",
    "function": "classify",
    "file": "src/app/weak.py",
    "line": 2,
    "operator": "if n > 0: -> if n >= 0:",
    "status": "survived",
    "waiver": WAIVER["reason"],
    "blocking": False,
    "target": "src/app/weak.py::classify::if n > 0: -> if n >= 0:",
}


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "weak", "src/app/weak.py", CLASSIFY, "add classify")
    commit_on_branch(repo, "weak", "tests/test_classify.py", WEAK_TEST, "weak classify test")
    (repo / ".bob").mkdir()
    (repo / ".bob" / "waivers.yaml").write_text(
        "waivers:\n"
        f"  - id: {WAIVER['id']}\n"
        f"    reason: {WAIVER['reason']}\n"
        f"    author: {WAIVER['author']}\n"
        f"    date: '{WAIVER['date']}'\n"
    )
    monkeypatch.setattr(mutate, "mutmut_version", lambda: VERSIONS["mutmut"])
    return repo


@pytest.fixture
def runs(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, list[str], int | None]]:
    seen: list[tuple[Path, list[str], int | None]] = []

    def fake_run(cwd: Path, patterns: list[str], max_workers: int | None) -> None:
        seen.append((cwd, list(patterns), max_workers))

    monkeypatch.setattr(mutate, "run_mutmut", fake_run)
    monkeypatch.setattr(mutate, "mutmut_results", lambda _cwd: RESULTS)
    monkeypatch.setattr(mutate, "mutmut_show", lambda _cwd, _mutant_id: SHOW)
    return seen


def _gate(
    repo: Path, baseline: int | None = 0, since_last_run: bool = False
) -> mutate.MutationOutcome:
    with mutate.since_last_run(since_last_run):
        return run_mutation_gate(
            repo, CONFIG, changed_lines(repo, "main"), repo / ".bob", max_workers=2, baseline=baseline
        )


def test_a_fresh_run_mutates_in_the_workdir_and_caches_what_it_found(
    repo: Path, runs: list[tuple[Path, list[str], int | None]]
) -> None:
    outcome = _gate(repo)
    work = repo / ".bob" / "mutmut"
    cache = json.loads((repo / ".bob" / CACHE_NAME).read_text())

    assert runs == [(work, ["app.weak.x_classify__mutmut*", "*app.weak.x_classify"], 2)]
    assert "source_paths =\n    src/app\n" in (work / "setup.cfg").read_text()
    assert outcome.exit_code == 0
    assert outcome.result == GateResult("mutate", "passed")
    assert outcome.versions == VERSIONS
    assert outcome.waivers == [WAIVER]
    assert outcome.survivors == [SURVIVOR]
    assert outcome.summary["remutated"] == ["src/app/weak.py::classify"]
    assert outcome.summary["reused"] == []
    assert list(cache["functions"]) == ["src/app/weak.py::classify"]
    assert [row["id"] for row in cache["functions"]["src/app/weak.py::classify"]["mutants"]] == [
        "app.weak.x_classify__mutmut_1",
        "app.weak.x_classify__mutmut_2",
    ]


def test_a_waived_unchanged_function_is_reused_without_running_mutmut(
    repo: Path, runs: list[tuple[Path, list[str], int | None]]
) -> None:
    first = _gate(repo)
    cached = (repo / ".bob" / CACHE_NAME).read_text()

    second = _gate(repo)

    assert len(runs) == 1
    assert second.exit_code == 0
    assert second.versions == VERSIONS
    assert second.waivers == [WAIVER]
    assert second.survivors == first.survivors
    assert second.summary["remutated"] == []
    assert second.summary["reused"] == ["src/app/weak.py::classify"]
    assert json.loads((repo / ".bob" / CACHE_NAME).read_text()) == json.loads(cached)


def test_since_last_run_reuses_an_unchanged_survivor_and_remutates_an_edited_one(
    repo: Path, runs: list[tuple[Path, list[str], int | None]]
) -> None:
    (repo / ".bob" / "waivers.yaml").unlink()
    first = _gate(repo)
    default = _gate(repo)

    assert first.exit_code == 3
    assert default.summary["remutated"] == ["src/app/weak.py::classify"]
    assert len(runs) == 2

    reused = _gate(repo, since_last_run=True)

    assert len(runs) == 2
    assert reused.exit_code == 3
    assert reused.result.status == "failed"
    assert reused.summary["remutated"] == []
    assert reused.summary["reused"] == ["src/app/weak.py::classify"]
    assert [row["id"] for row in reused.survivors] == ["app.weak.x_classify__mutmut_1"]
    assert reused.survivors[0]["blocking"] is True

    weak = repo / "src" / "app" / "weak.py"
    weak.write_text(weak.read_text().replace('"pos"', '"positive"'))
    edited = _gate(repo, since_last_run=True)

    assert len(runs) == 3
    assert edited.summary["remutated"] == ["src/app/weak.py::classify"]
    assert edited.summary["reused"] == []


def test_since_last_run_does_not_outlive_its_command(
    repo: Path, runs: list[tuple[Path, list[str], int | None]]
) -> None:
    (repo / ".bob" / "waivers.yaml").unlink()
    _gate(repo)
    _gate(repo, since_last_run=True)
    after = _gate(repo)

    assert len(runs) == 2
    assert after.summary["remutated"] == ["src/app/weak.py::classify"]


def test_since_last_run_remeasures_a_survivor_when_other_production_code_changes(
    repo: Path, runs: list[tuple[Path, list[str], int | None]], monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / ".bob" / "waivers.yaml").unlink()
    flags = repo / "src" / "app" / "flags.py"
    flags.write_text("BLOCK = True\n")
    first = _gate(repo)
    flags.write_text("BLOCK = False\n")
    monkeypatch.setattr(
        mutate, "mutmut_results", lambda _cwd: RESULTS.replace("mutmut_1: survived", "mutmut_1: killed")
    )
    second = _gate(repo, since_last_run=True)

    assert first.exit_code == 3
    assert len(runs) == 2
    assert second.exit_code == 0
    assert second.summary["remutated"] == ["src/app/weak.py::classify"]
    assert second.survivors == []


def test_a_reused_waived_survivor_follows_its_function_down_the_file(
    repo: Path, runs: list[tuple[Path, list[str], int | None]]
) -> None:
    first = _gate(repo)
    weak = repo / "src" / "app" / "weak.py"
    weak.write_text("# classify\n\n" + weak.read_text())
    moved = _gate(repo, since_last_run=True)

    assert len(runs) == 1
    assert moved.summary["reused"] == ["src/app/weak.py::classify"]
    assert [row["line"] for row in moved.survivors] == [row["line"] + 2 for row in first.survivors]


def test_waived_rows_carried_past_a_cache_key_change_are_remeasured_later() -> None:
    key = "src/app/weak.py::classify"
    row = {key_: SURVIVOR[key_] for key_ in ("id", "function", "file", "line", "operator", "status")}
    entry: dict[str, object] = {"hash": "h", "mutants": [row]}
    waivers = [Waiver(**WAIVER)]
    functions = cast("dict[str, CyclomaticFunction]", {key: None})

    stale = mutate._carried_rows(mutate._CacheView({key: entry}, False), functions, waivers)
    kept = mutate._carried_rows(mutate._CacheView({key: entry}, True), functions, waivers)

    assert stale[key]["stale"] is True
    assert "stale" not in kept[key]
    assert mutate._needs_remutation(stale[key], "h", waivers, "") is True
    assert mutate._needs_remutation(kept[key], "h", waivers, "") is False


def test_a_mutmut_failure_keeps_the_versions_and_the_waivers(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(_cwd: Path, _patterns: list[str], _max_workers: int | None) -> None:
        raise ToolError("mutmut broke")

    monkeypatch.setattr(mutate, "run_mutmut", boom)

    outcome = _gate(repo)

    assert outcome.exit_code == 4
    assert outcome.result == GateResult("mutate", "not_run", "mutmut broke")
    assert outcome.versions == VERSIONS
    assert outcome.waivers == [WAIVER]
    assert not (repo / ".bob" / CACHE_NAME).exists()


@pytest.mark.parametrize("baseline", [None, 1])
def test_a_broken_baseline_stops_before_mutmut(
    repo: Path,
    runs: list[tuple[Path, list[str], int | None]],
    monkeypatch: pytest.MonkeyPatch,
    baseline: int | None,
) -> None:
    measured: list[Path] = []

    def failing_suite(cwd: Path) -> int:
        measured.append(cwd)
        return 1

    monkeypatch.setattr(mutate, "pytest_exit_code", failing_suite)

    outcome = _gate(repo, baseline)

    assert measured == ([repo] if baseline is None else [])
    assert runs == []
    assert outcome.exit_code == 2
    assert outcome.result.status == "not_run"
    assert outcome.versions == VERSIONS
    assert outcome.waivers == [WAIVER]
