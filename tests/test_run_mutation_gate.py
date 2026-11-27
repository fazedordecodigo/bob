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
from helpers import commit_on_branch, commit_on_main, init_python_repo

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


def test_a_waived_function_carried_past_a_suite_change_is_remeasured_back_in_scope(
    repo: Path, runs: list[tuple[Path, list[str], int | None]]
) -> None:
    _gate(repo)
    (repo / "tests" / "test_extra.py").write_text("def test_extra():\n    assert True\n")
    with mutate.since_last_run(True):
        run_mutation_gate(repo, CONFIG, {}, repo / ".bob", max_workers=2, baseline=0)
    back = _gate(repo, since_last_run=True)

    assert len(runs) == 2
    assert back.summary["remutated"] == ["src/app/weak.py::classify"]


def test_since_last_run_remeasures_survivors_when_production_code_is_unreadable(
    repo: Path, runs: list[tuple[Path, list[str], int | None]], monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / ".bob" / "waivers.yaml").unlink()
    _gate(repo)

    def unreadable(_cwd: Path) -> str:
        raise PermissionError("vendor/internal.py")

    monkeypatch.setattr(mutate, "source_fingerprint", unreadable)
    again = _gate(repo, since_last_run=True)

    assert len(runs) == 2
    assert again.exit_code == 3
    assert again.summary["remutated"] == ["src/app/weak.py::classify"]


def test_a_latin1_local_edit_outside_python_still_reaches_a_verdict(
    repo: Path, runs: list[tuple[Path, list[str], int | None]]
) -> None:
    (repo / ".bob" / "waivers.yaml").unlink()
    commit_on_branch(repo, "weak", "docs/notes.txt", "cafe\n", "notes")
    (repo / "docs" / "notes.txt").write_bytes("café\n".encode("latin-1"))

    outcome = _gate(repo)

    assert len(runs) == 1
    assert outcome.exit_code == 3


def test_a_removal_whose_anchor_was_deleted_locally_still_mutates_the_function(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    runs: list[tuple[Path, list[str], int | None]],
) -> None:
    monkeypatch.setattr(mutate, "mutmut_version", lambda: VERSIONS["mutmut"])
    repo = init_python_repo(tmp_path / "repo")
    flow = "def flow(n: int) -> bool:\n    x = n\n    print(x)\n    return x > 0\n"
    commit_on_main(repo, "src/app/flow.py", flow, "add flow")
    commit_on_branch(repo, "work", "src/app/flow.py", flow.replace("    print(x)\n", ""), "drop print")
    (repo / "src" / "app" / "flow.py").write_text("def flow(n: int) -> bool:\n    return n > 0\n")

    _gate(repo)

    assert len(runs) == 1


def test_a_changed_function_swapped_with_a_comment_locally_is_still_mutated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    runs: list[tuple[Path, list[str], int | None]],
) -> None:
    monkeypatch.setattr(mutate, "mutmut_version", lambda: VERSIONS["mutmut"])
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/flow.py", "def f():\n    return 1\n# old note\n", "add f")
    commit_on_branch(repo, "work", "src/app/flow.py", "def f():\n    return 2\n# old note\n", "f=2")
    (repo / "src" / "app" / "flow.py").write_text("# a brand new note\ndef f():\n    return 3\n")

    _gate(repo)

    assert len(runs) == 1


def test_a_branch_function_deleted_locally_does_not_mutate_its_neighbour(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    runs: list[tuple[Path, list[str], int | None]],
) -> None:
    monkeypatch.setattr(mutate, "mutmut_version", lambda: VERSIONS["mutmut"])
    repo = init_python_repo(tmp_path / "repo")
    old = "def old():\n    return 1\n"
    commit_on_main(repo, "src/app/flow.py", old, "add old")
    commit_on_branch(repo, "work", "src/app/flow.py", old + "\n\ndef new():\n    return 2\n", "add new")
    (repo / "src" / "app" / "flow.py").write_text(old)

    outcome = _gate(repo)

    assert runs == []
    assert outcome.exit_code == 0


def test_a_waived_function_carried_under_the_same_key_is_reused_back_in_scope(
    repo: Path, runs: list[tuple[Path, list[str], int | None]]
) -> None:
    _gate(repo)
    with mutate.since_last_run(True):
        run_mutation_gate(repo, CONFIG, {}, repo / ".bob", max_workers=2, baseline=0)
    back = _gate(repo, since_last_run=True)

    assert len(runs) == 1
    assert back.summary["remutated"] == []


def test_a_function_inserted_above_locally_does_not_take_the_branch_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    runs: list[tuple[Path, list[str], int | None]],
) -> None:
    monkeypatch.setattr(mutate, "mutmut_version", lambda: VERSIONS["mutmut"])
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/flow.py", "def f(n):\n    return n > 0\n", "add f")
    commit_on_branch(repo, "work", "src/app/flow.py", "def f(n):\n    return n > 1\n", "f>1")
    (repo / "src" / "app" / "flow.py").write_text(
        "def g(n):\n    return n < 0\n\n\ndef f(n):\n    return n > 1\n"
    )

    _gate(repo)

    patterns = " ".join(runs[0][1])
    assert "x_f" in patterns
    assert "x_g" not in patterns


def test_the_baseline_runs_in_the_repo_when_no_exit_is_given(
    repo: Path, monkeypatch: pytest.MonkeyPatch, runs: list[tuple[Path, list[str], int | None]]
) -> None:
    seen: list[Path] = []
    monkeypatch.setattr(mutate, "pytest_exit_code", lambda cwd: seen.append(cwd) or 0)

    _gate(repo, baseline=None)

    assert seen == [repo]


def test_a_baseline_that_cannot_run_keeps_versions_and_waivers(
    repo: Path, monkeypatch: pytest.MonkeyPatch, runs: list[tuple[Path, list[str], int | None]]
) -> None:
    def broken(_cwd: Path) -> int:
        raise ToolError("pytest is gone")

    monkeypatch.setattr(mutate, "pytest_exit_code", broken)

    outcome = _gate(repo, baseline=None)

    assert outcome.exit_code == 4
    assert outcome.versions == VERSIONS
    assert [row["id"] for row in outcome.waivers] == [WAIVER["id"]]


def test_a_mutmut_failure_keeps_versions_and_waivers(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(_cwd: Path, _patterns: list[str], _workers: int | None) -> None:
        raise ToolError("mutmut is gone")

    monkeypatch.setattr(mutate, "run_mutmut", broken)

    outcome = _gate(repo)

    assert outcome.exit_code == 4
    assert outcome.versions == VERSIONS
    assert [row["id"] for row in outcome.waivers] == [WAIVER["id"]]


def test_a_waived_function_that_no_longer_exists_leaves_the_cache(
    repo: Path, runs: list[tuple[Path, list[str], int | None]]
) -> None:
    _gate(repo)
    (repo / "src" / "app" / "weak.py").unlink()

    run_mutation_gate(repo, CONFIG, {}, repo / ".bob", max_workers=2, baseline=0)

    cache = json.loads((repo / ".bob" / CACHE_NAME).read_text())
    assert "src/app/weak.py::classify" not in cache["functions"]
