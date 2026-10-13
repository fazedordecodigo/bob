"""O dispatcher grava o retorno de cada gate. Um argumento trocado muda o relatório."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from bob_quality.check import _Measured, _absorb, _assemble
from bob_quality.config import Config
from bob_quality.messages import msg
from bob_quality.models import Clone, DepViolation, FunctionMetric, GateResult
from bob_quality.mutate import MutationOutcome

DIFF = {"src/a.py": {3}}
CLONE = Clone("src/a.py", 1, 2, "src/b.py", 3, 4, 2, 10, 0.9, "python")


def _forbid(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("este gate não foi pedido")

    for name in (
        "run_crap_gate",
        "run_dry_gate",
        "run_deps_gate",
        "run_mutate_gate",
        "run_typing_gate",
    ):
        monkeypatch.setattr("bob_quality.check." + name, boom)


def test_unknown_gate_is_not_run_and_leaves_the_others_alone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _forbid(monkeypatch)
    state = _Measured()

    _absorb(state, "nope", tmp_path, Config(), DIFF, 10.0, None, tmp_path, None)

    assert state.gates == [
        GateResult("nope", "not_run", msg("check.gate_not_implemented"))
    ]
    assert state.exit_code == 0
    assert state.metrics == []
    assert state.clones == []
    assert state.violations == []
    assert state.mutation is None
    assert state.typing is None
    assert state.baseline is None


def test_crap_records_metrics_baseline_and_the_exact_arguments(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _forbid(monkeypatch)
    config = Config()
    coverage = tmp_path / "coverage.json"
    result = GateResult("crap", "passed", None)

    def fake(**kwargs: object) -> tuple[object, ...]:
        assert kwargs == {
            "cwd": tmp_path,
            "config": config,
            "diff_lines": DIFF,
            "max_crap": 10.0,
            "coverage_file": coverage,
        }
        return result, ["metric"], 0, {"lizard": "1.24.1"}, 7

    monkeypatch.setattr("bob_quality.check.run_crap_gate", fake)
    state = _Measured()

    _absorb(state, "crap", tmp_path, config, DIFF, 10.0, coverage, tmp_path, 2)

    assert state.metrics == ["metric"]
    assert state.baseline == 7
    assert state.gates == [result]
    assert state.versions == {"lizard": "1.24.1"}
    assert state.exit_code == 0


def test_dry_records_the_clones(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _forbid(monkeypatch)
    config = Config()
    result = GateResult("dry", "warn", None)

    def fake(**kwargs: object) -> tuple[object, ...]:
        assert kwargs == {"cwd": tmp_path, "config": config, "diff_lines": DIFF}
        return result, [CLONE], 0, {"jscpd": "5.4.1"}

    monkeypatch.setattr("bob_quality.check.run_dry_gate", fake)
    state = _Measured()

    _absorb(state, "dry", tmp_path, config, DIFF, 10.0, None, tmp_path, None)

    assert state.clones == [CLONE]
    assert state.gates == [result]
    assert state.versions == {"jscpd": "5.4.1"}


def test_deps_records_the_violation_set(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _forbid(monkeypatch)
    config = Config()
    result = GateResult("deps", "failed", None)

    def fake(cwd: Path, got: Config, files: set[str]) -> tuple[object, ...]:
        assert cwd == tmp_path
        assert got is config
        assert files == set(DIFF)
        return result, 1, {"grimp": "3"}, ["edge"]

    monkeypatch.setattr("bob_quality.check.run_deps_gate", fake)
    state = _Measured()

    _absorb(state, "deps", tmp_path, config, DIFF, 10.0, None, tmp_path, None)

    assert state.violations == ["edge"]
    assert state.gates == [result]
    assert state.exit_code == 1


def test_mutate_keeps_the_baseline_and_the_worker_count(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _forbid(monkeypatch)
    config = Config()
    out = tmp_path / "out"
    outcome = MutationOutcome(
        result=GateResult("mutate", "passed", None),
        exit_code=0,
        versions={"mutmut": "3.8.0"},
        waivers=[{"id": "w"}],
        survivors=[{"id": "s"}],
        summary={"remutated": ["fn"]},
    )

    def fake(**kwargs: object) -> MutationOutcome:
        assert kwargs == {
            "cwd": tmp_path,
            "config": config,
            "diff_lines": DIFF,
            "out_dir": out,
            "max_workers": 2,
            "baseline": 7,
        }
        return outcome

    monkeypatch.setattr("bob_quality.check.run_mutate_gate", fake)
    state = _Measured(baseline=7)

    _absorb(state, "mutate", tmp_path, config, DIFF, 10.0, None, out, 2)

    assert state.mutation is outcome
    assert state.gates == [outcome.result]
    assert state.versions == {"mutmut": "3.8.0"}
    assert state.exit_code == 0


def test_typing_records_the_json_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _forbid(monkeypatch)
    config = Config()
    result = GateResult("typing", "failed", None)
    found = {"findings": [{"file": "src/a.py"}]}

    def fake(cwd: Path, got: Config, diff_lines: dict[str, set[int]]) -> tuple[object, ...]:
        assert cwd == tmp_path
        assert got is config
        assert diff_lines == DIFF
        return result, 1, {"mypy": "1"}, found

    monkeypatch.setattr("bob_quality.check.run_typing_gate", fake)
    state = _Measured()

    _absorb(state, "typing", tmp_path, config, DIFF, 10.0, None, tmp_path, None)

    assert state.typing == found
    assert state.gates == [result]
    assert state.versions == {"mypy": "1"}
    assert state.exit_code == 1


def _patch_report_parts(monkeypatch: pytest.MonkeyPatch, clone: Clone) -> None:
    def files_by_risk(metrics: object, clones: object, files: object) -> list[dict[str, object]]:
        assert metrics == ["metric"]
        assert clones == [clone]
        assert files == {"src/a.py"}
        return [{"file": "src/a.py", "risk": 9}]

    def top_changed_crap(metrics: object) -> list[str]:
        assert metrics == ["metric"]
        return ["top-metric"]

    def informational_debt(metrics: object, limit: object) -> list[str]:
        assert metrics == ["metric"]
        assert limit == 10.0
        return ["debt-metric"]

    def metric_row(item: object) -> dict[str, object]:
        assert item in {"top-metric", "debt-metric"}
        return {"name": item}

    def violation_rows(items: object, *, in_diff: object) -> list[dict[str, object]]:
        assert items == ["edge"]
        assert in_diff in {True, False}
        return [{"edge": "new"}] if in_diff is True else [{"edge": "old"}]

    monkeypatch.setattr("bob_quality.check.files_by_risk", files_by_risk)
    monkeypatch.setattr("bob_quality.check.top_changed_crap", top_changed_crap)
    monkeypatch.setattr("bob_quality.check.informational_debt", informational_debt)
    monkeypatch.setattr("bob_quality.check.metric_row", metric_row)
    monkeypatch.setattr("bob_quality.check.violation_rows", violation_rows)


def test_assemble_without_mutation_keeps_idle_waivers_and_empty_survivors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_report_parts(monkeypatch, CLONE)
    measured = _Measured(
        versions={"lizard": "1.24.1"},
        gates=[GateResult("crap", "passed", None)],
        metrics=cast(list[FunctionMetric], ["metric"]),
        clones=[CLONE],
        violations=cast(list[DepViolation], ["edge"]),
        exit_code=4,
        loaded_waivers=[{"id": "idle"}],
    )

    report = _assemble(measured, "abc", "main", DIFF, 10.0, "bob check")

    assert report.schema_version == 1
    assert report.commit == "abc"
    assert report.base == "main"
    assert report.generated_at.endswith("+00:00")
    assert report.tool_versions == {"lizard": "1.24.1"}
    assert report.gates == [GateResult("crap", "passed", None)]
    assert report.focus == [{"file": "src/a.py", "risk": 9}]
    assert report.top_crap == [{"name": "top-metric"}]
    assert report.old_debt == [{"name": "debt-metric"}]
    assert report.dependencies == [{"edge": "new"}]
    assert report.old_dependencies == [{"edge": "old"}]
    assert report.clones == [CLONE]
    assert report.reproduce == "bob check"
    assert report.exit_code == 4
    assert report.waivers == [{"id": "idle"}]
    assert report.survivors == []
    assert report.mutation is None
    assert report.typing is None


def test_assemble_with_mutation_replaces_waivers_and_keeps_typing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_report_parts(monkeypatch, CLONE)

    def focus_with_survivors(
        current: list[dict[str, object]], rows: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        assert current == [{"file": "src/a.py", "risk": 9}]
        assert rows == [{"id": "survivor"}]
        return [{"file": "src/a.py", "risk": 9, "survivors": 1}]

    monkeypatch.setattr("bob_quality.check.focus_with_survivors", focus_with_survivors)
    found = {"findings": [{"file": "src/a.py"}]}
    measured = _Measured(
        versions={"mutmut": "3.8.0"},
        gates=[GateResult("mutate", "passed", None)],
        metrics=cast(list[FunctionMetric], ["metric"]),
        clones=[CLONE],
        violations=cast(list[DepViolation], ["edge"]),
        exit_code=3,
        loaded_waivers=[{"id": "idle"}],
        mutation=MutationOutcome(
            result=GateResult("mutate", "passed", None),
            exit_code=3,
            versions={"mutmut": "3.8.0"},
            waivers=[{"id": "held"}],
            survivors=[{"id": "survivor"}],
            summary={"remutated": ["fn"]},
        ),
        typing=found,
    )

    report = _assemble(measured, "def", "origin/main", DIFF, 10.0, "bob check --gates mutate")

    assert report.generated_at.endswith("+00:00")
    assert report.focus == [{"file": "src/a.py", "risk": 9, "survivors": 1}]
    assert report.waivers == [{"id": "held"}]
    assert report.survivors == [{"id": "survivor"}]
    assert report.mutation == {"remutated": ["fn"]}
    assert report.typing == found
    assert report.exit_code == 3
    assert report.reproduce == "bob check --gates mutate"
