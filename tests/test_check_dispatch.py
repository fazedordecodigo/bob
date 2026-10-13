"""O mutmut só vê chamada no processo. Estes testes seguram _absorb e _assemble."""

from __future__ import annotations

from pathlib import Path

import bob_quality.check as check
from bob_quality.check import _Measured, _absorb, _assemble
from bob_quality.config import Config
from bob_quality.messages import render
from bob_quality.models import (
    Clone,
    DepViolation,
    FunctionMetric,
    GateResult,
    SecretLedger,
    SecretRow,
)
from bob_quality.mutate import MutationOutcome
from bob_quality.secrets_gate import SecretsRun
from bob_quality.suite_memo import SuiteMemo


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
    memo = SuiteMemo(want_lcov=False)
    base = "origin/main"
    try:
        _absorb(state, "crap", cwd, config, diff, 10.0, coverage, out, 2, base, memo)
    finally:
        memo.close()
    assert seen["crap"] == {
        "cwd": cwd,
        "config": config,
        "diff_lines": diff,
        "max_crap": 10.0,
        "coverage_file": coverage,
        "memo": memo,
    }
    assert state.metrics == [metric]
    assert state.baseline == 0
    assert state.exit_code == 1
    assert state.versions == {"lizard": "1.24.1"}
    assert state.gates == [GateResult("crap", "failed")]
    assert set(seen) == {"crap"}

    _absorb(state, "dry", cwd, config, diff, 10.0, coverage, out, 2, base, memo)
    assert seen["dry"] == {"cwd": cwd, "config": config, "diff_lines": diff}
    assert state.clones == [_clone()]
    assert state.versions["jscpd"] == "5.4.1"
    assert set(seen) == {"crap", "dry"}

    _absorb(state, "deps", cwd, config, diff, 10.0, coverage, out, 2, base, memo)
    assert seen["deps"] == (cwd, config, {"src/app.py"})
    assert state.violations == [violation]
    assert set(seen) == {"crap", "dry", "deps"}

    _absorb(state, "mutate", cwd, config, diff, 10.0, coverage, out, 2, base, memo)
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

    _absorb(state, "secrets", cwd, config, diff, 10.0, coverage, out, 2, base, memo)
    assert seen["secrets"] == {"cwd": cwd, "config": config, "diff_lines": diff}
    assert state.secrets == ledger
    assert state.versions["gitleaks"] == "8.30.1"
    assert [gate.name for gate in state.gates] == ["crap", "dry", "deps", "mutate", "secrets"]
    assert state.gates[-1].status == "failed"
    assert set(seen) == {"crap", "dry", "deps", "mutate", "secrets"}


def test_absorb_unknown_gate_stays_not_run_and_exit_0() -> None:
    state = _Measured()
    memo = SuiteMemo(want_lcov=False)
    try:
        _absorb(
            state,
            "nope",
            Path("/repo"),
            Config(),
            {},
            10.0,
            None,
            Path("/out"),
            None,
            "origin/main",
            memo,
        )
    finally:
        memo.close()

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

    report = _assemble(measured, "abc123", "origin/main", {"src/app.py": {1}}, 10.0, "bob check")

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


def test_assemble_without_mutation_keeps_idle_waivers_and_empty_survivors() -> None:
    measured = _Measured(loaded_waivers=[{"id": "idle"}], exit_code=0)
    report = _assemble(measured, "abc", "main", {}, 10.0, "bob check")

    assert report.survivors == []
    assert report.mutation is None
    assert report.waivers == [{"id": "idle"}]
    assert report.secrets is None
    assert report.focus == []
    assert report.top_crap == []
    assert report.old_debt == []
    assert report.dependencies == []
    assert report.old_dependencies == []
    assert report.exit_code == 0


def _metric(name: str, file: str, *, changed: bool, crap: float) -> FunctionMetric:
    return FunctionMetric("python", "app", name, file, 1, 4, 2, 1.0, crap, changed)


def _clone() -> Clone:
    return Clone("src/app.py", 1, 3, "src/other.py", 1, 3, 3, 20, 1.0, "python")
