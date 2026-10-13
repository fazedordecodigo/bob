"""`run_mutation_gate` no mesmo processo, com o mutmut trocado por um falso.

Os testes da CLI rodam o bob num subprocesso, que importa o pacote instalado e não o mutante.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import bob_quality.mutate as mutate
from bob_quality.config import Config
from bob_quality.diff import changed_lines
from bob_quality.models import GateResult
from bob_quality.mutate import CACHE_NAME, run_mutation_gate
from bob_quality.tools import ToolError
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


def _gate(repo: Path, baseline: int | None = 0) -> mutate.MutationOutcome:
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
