"""O dispatcher grava o retorno de cada gate. Um argumento trocado muda o relatório."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

import bob_quality.check as check
from bob_quality.check import _Measured, _absorb, _assemble
from bob_quality.churn import ChurnUnavailable
from bob_quality.config import Config
from bob_quality.dead_code import WarningOnly
from bob_quality.messages import msg, render
from bob_quality.models import (
    Clone,
    DeadSection,
    DepViolation,
    FunctionMetric,
    GateResult,
    SecretLedger,
    SecretRow,
)
from bob_quality.mutate import MutationOutcome
from bob_quality.secrets_gate import SecretsRun

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
        "run_security_gate",
        "run_secrets_gate",
        "run_dead_code_gate",
    ):
        monkeypatch.setattr("bob_quality.check." + name, boom)


def test_unknown_gate_is_not_run_and_leaves_the_others_alone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _forbid(monkeypatch)
    state = _Measured()

    _absorb(state, "nope", tmp_path, Config(), "main", DIFF, 10.0, None, tmp_path, None, False, None)

    assert state.gates == [
        GateResult("nope", "not_run", msg("check.gate_not_implemented"))
    ]
    assert state.exit_code == 0
    assert state.metrics == []
    assert state.clones == []
    assert state.violations == []
    assert state.mutation is None
    assert state.typing is None
    assert state.security is None
    assert state.secrets is None
    assert state.dead_code is None
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

    _absorb(state, "crap", tmp_path, config, "main", DIFF, 10.0, coverage, tmp_path, 2, False, None)

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
        assert kwargs == {
            "cwd": tmp_path,
            "config": config,
            "diff_lines": DIFF,
            "dry_fail": False,
            "max_new_clones": None,
        }
        return result, [CLONE], 0, {"jscpd": "5.4.1"}

    monkeypatch.setattr("bob_quality.check.run_dry_gate", fake)
    state = _Measured()

    _absorb(state, "dry", tmp_path, config, "main", DIFF, 10.0, None, tmp_path, None, False, None)

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

    _absorb(state, "deps", tmp_path, config, "main", DIFF, 10.0, None, tmp_path, None, False, None)

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

    _absorb(state, "mutate", tmp_path, config, "main", DIFF, 10.0, None, out, 2, False, None)

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

    _absorb(state, "typing", tmp_path, config, "main", DIFF, 10.0, None, tmp_path, None, False, None)

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

    report = _assemble(measured, "abc", "main", DIFF, 10.0, "bob check", ChurnUnavailable())

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
    assert report.security is None
    assert report.secrets is None
    assert report.dead_code is None
    assert report.churn == ChurnUnavailable()


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

    report = _assemble(
        measured, "def", "origin/main", DIFF, 10.0, "bob check --gates mutate", ChurnUnavailable()
    )

    assert report.generated_at.endswith("+00:00")
    assert report.focus == [{"file": "src/a.py", "risk": 9, "survivors": 1}]
    assert report.waivers == [{"id": "held"}]
    assert report.survivors == [{"id": "survivor"}]
    assert report.mutation == {"remutated": ["fn"]}
    assert report.typing == found
    assert report.churn == ChurnUnavailable()
    assert report.exit_code == 3
    assert report.reproduce == "bob check --gates mutate"

def test_absorb_records_each_gate_from_the_arguments_it_received(monkeypatch) -> None:
    cwd = Path("/repo")
    config = Config()
    diff = {"src/app.py": {3}}
    coverage = Path("/cov.json")
    out = Path("/out")
    metric = _metric("add", "src/app.py", changed=True, crap=4.0)
    violation = DepViolation("pkg.a", "pkg.b", "cycle", True)
    ledger = SecretLedger(blocking=(SecretRow("src/app.py", 3, "aws-access-token"),))
    mutation = MutationOutcome(
        GateResult("mutate", "failed"),
        3,
        {"mutmut": "3.8.0"},
        [{"id": "m"}],
        [{"id": "m", "file": "src/app.py"}],
        {"remutated": ["src/app.py::add"]},
    )
    seen: dict[str, object] = {}

    def crap(**kwargs: object) -> tuple[GateResult, list[FunctionMetric], int, dict[str, str], int]:
        seen["crap"] = kwargs
        return GateResult("crap", "failed"), [metric], 1, {"lizard": "1.24.1"}, 0

    def dry(**kwargs: object) -> tuple[GateResult, list[Clone], int, dict[str, str]]:
        seen["dry"] = kwargs
        return GateResult("dry", "passed"), [_clone()], 0, {"jscpd": "5.4.1"}

    def deps(*args: object) -> tuple[GateResult, int, dict[str, str], list[DepViolation]]:
        seen["deps"] = args
        return GateResult("deps", "failed"), 1, {"import-linter": "2.15"}, [violation]

    def mutate(**kwargs: object) -> MutationOutcome:
        seen["mutate"] = kwargs
        return mutation

    def secrets(**kwargs: object) -> SecretsRun:
        seen["secrets"] = kwargs
        return SecretsRun(
            GateResult("secrets", "failed", "1 new secret in the diff"),
            ledger,
            1,
            {"gitleaks": "8.30.1"},
        )

    monkeypatch.setattr(check, "run_crap_gate", crap)
    monkeypatch.setattr(check, "run_dry_gate", dry)
    monkeypatch.setattr(check, "run_deps_gate", deps)
    monkeypatch.setattr(check, "run_mutate_gate", mutate)
    monkeypatch.setattr(check, "run_secrets_gate", secrets)

    state = _Measured()
    _absorb(state, "crap", cwd, config, "main", diff, 10.0, coverage, out, 2, True, 0)
    assert seen["crap"] == {
        "cwd": cwd,
        "config": config,
        "diff_lines": diff,
        "max_crap": 10.0,
        "coverage_file": coverage,
    }
    assert state.metrics == [metric]
    assert state.baseline == 0
    assert state.exit_code == 1
    assert state.versions == {"lizard": "1.24.1"}
    assert state.gates == [GateResult("crap", "failed")]
    assert set(seen) == {"crap"}

    _absorb(state, "dry", cwd, config, "main", diff, 10.0, coverage, out, 2, True, 0)
    assert seen["dry"] == {
        "cwd": cwd,
        "config": config,
        "diff_lines": diff,
        "dry_fail": True,
        "max_new_clones": 0,
    }
    assert state.clones == [_clone()]
    assert state.versions["jscpd"] == "5.4.1"
    assert set(seen) == {"crap", "dry"}

    _absorb(state, "deps", cwd, config, "main", diff, 10.0, coverage, out, 2, True, 0)
    assert seen["deps"] == (cwd, config, {"src/app.py"})
    assert state.violations == [violation]
    assert set(seen) == {"crap", "dry", "deps"}

    _absorb(state, "mutate", cwd, config, "main", diff, 10.0, coverage, out, 2, True, 0)
    assert seen["mutate"] == {
        "cwd": cwd,
        "config": config,
        "diff_lines": diff,
        "out_dir": out,
        "max_workers": 2,
        "baseline": 0,
    }
    assert state.mutation == mutation
    assert state.exit_code == 3
    assert set(seen) == {"crap", "dry", "deps", "mutate"}

    _absorb(state, "secrets", cwd, config, "main", diff, 10.0, coverage, out, 2, True, 0)
    assert seen["secrets"] == {"cwd": cwd, "config": config, "diff_lines": diff}
    assert state.secrets == ledger
    assert state.versions["gitleaks"] == "8.30.1"
    assert [gate.name for gate in state.gates] == ["crap", "dry", "deps", "mutate", "secrets"]
    assert state.gates[-1].status == "failed"
    assert set(seen) == {"crap", "dry", "deps", "mutate", "secrets"}


def test_absorb_unknown_gate_stays_not_run_and_exit_0() -> None:
    state = _Measured()
    _absorb(state, "nope", Path("/repo"), Config(), "main", {}, 10.0, None, Path("/out"), None, False, None)

    assert state.exit_code == 0
    assert state.versions == {}
    assert state.metrics == []
    assert state.clones == []
    assert state.violations == []
    assert state.mutation is None
    assert state.secrets is None
    assert len(state.gates) == 1
    gate = state.gates[0]
    assert gate.name == "nope"
    assert gate.status == "not_run"
    assert render(gate.reason, "en") == "gate not implemented in this slice"
    assert render(gate.reason, "pt-BR") == "gate não implementado nesta fatia"


def test_assemble_copies_measurement_and_keeps_secrets() -> None:
    metric = _metric("add", "src/app.py", changed=True, crap=4.0)
    debt = _metric("old", "src/old.py", changed=False, crap=30.0)
    clone = _clone()
    inside = DepViolation("pkg.in", "pkg.dst", "cycle", True)
    outside = DepViolation("pkg.out", "pkg.dst", "cycle", False)
    ledger = SecretLedger(
        blocking=(
            SecretRow("src/a.py", 1, "aws-access-token"),
            SecretRow("src/a.py", 2, "aws-access-token"),
        )
    )
    survivor = {"id": "m", "file": "src/app.py", "waiver": None, "blocking": True}
    summary = {"remutated": ["src/app.py::add"], "reused": []}
    waivers = [{"id": "kept"}]
    measured = _Measured(
        versions={"lizard": "1.24.1"},
        gates=[GateResult("crap", "passed"), GateResult("secrets", "failed")],
        metrics=[metric, debt],
        clones=[clone],
        violations=[inside, outside],
        exit_code=1,
        mutation=MutationOutcome(
            GateResult("mutate", "failed"),
            3,
            {"mutmut": "3.8.0"},
            waivers,
            [survivor],
            summary,
        ),
        secrets=ledger,
        loaded_waivers=[{"id": "idle"}],
        baseline=0,
    )

    report = _assemble(
        measured,
        "abc123",
        "origin/main",
        {"src/app.py": {1}},
        10.0,
        "bob check",
        ChurnUnavailable(),
    )

    assert report.schema_version == 1
    assert report.commit == "abc123"
    assert report.base == "origin/main"
    assert report.generated_at.endswith("+00:00")
    assert "T" in report.generated_at
    assert report.tool_versions == {"lizard": "1.24.1"}
    assert report.gates == measured.gates
    assert report.focus[0]["file"] == "src/app.py"
    assert report.focus[0]["risk"] == 104.0
    assert report.top_crap[0]["name"] == "add"
    assert report.old_debt[0]["name"] == "old"
    assert report.dependencies[0]["origin"] == "pkg.in"
    assert report.old_dependencies[0]["origin"] == "pkg.out"
    assert report.clones == [clone]
    assert report.reproduce == "bob check"
    assert report.exit_code == 1
    assert report.waivers == waivers
    assert report.survivors == [survivor]
    assert report.mutation == summary
    assert report.secrets == ledger
    assert report.churn == ChurnUnavailable()
    assert report.security is None


def _metric(name: str, file: str, *, changed: bool, crap: float) -> FunctionMetric:
    return FunctionMetric("python", "app", name, file, 1, 4, 2, 1.0, crap, changed)


def _clone() -> Clone:
    return Clone("src/app.py", 1, 3, "src/other.py", 1, 3, 3, 20, 1.0, "python")


def test_dead_code_records_the_warning(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    section = DeadSection()
    advisory = WarningOnly("warn", msg("dead.one", count=1), section, (("vulture", "2.16"),))

    def fake(cwd: Path, config: Config, diff_lines: dict[str, set[int]]) -> WarningOnly:
        assert cwd == tmp_path
        assert diff_lines == DIFF
        return advisory

    monkeypatch.setattr("bob_quality.check.run_dead_code_gate", fake)
    state = _Measured()
    _absorb(state, "dead_code", tmp_path, Config(), "main", DIFF, 10.0, None, tmp_path, None, False, None)

    assert state.dead_code == section
    assert state.gates == [advisory.as_gate()]
    assert state.versions == {"vulture": "2.16"}
    assert state.exit_code == 0

