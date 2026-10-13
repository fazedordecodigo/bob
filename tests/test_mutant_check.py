"""O check passa cada argumento até o relatório. Um None no meio muda o JSON."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from bob_quality.check import _assemble, _measure, run_check
from bob_quality.config import Config
from bob_quality.models import (
    Clone,
    DepViolation,
    FunctionMetric,
    GateResult,
    MissingPackage,
    RowBlock,
    SupplyReport,
)
from bob_quality.mutate import MutationOutcome
from helpers import init_python_repo

_SUPPLY = SupplyReport(
    ("python",),
    (),
    (RowBlock(MissingPackage("pypi", "no-such-pkg", "pyproject.toml", 4)),),
)
_WAIVER = {
    "id": "kept-visible",
    "reason": "one line",
    "author": "ada",
    "date": "2026-10-12",
}


def _metric(name: str, crap: float, changed: bool) -> FunctionMetric:
    return FunctionMetric(
        lang="python",
        module="app",
        name=name,
        file=f"src/{name}.py",
        start_line=1,
        end_line=4,
        cc=2,
        coverage=0.0,
        crap=crap,
        changed=changed,
    )


def test_measure_passes_the_base_into_supply(tmp_path: Path) -> None:
    from bob_quality import check as check_mod

    seen: dict[str, object] = {}

    def supply(cwd: Path, config: Config, diff_lines: dict[str, set[int]], base: str):
        seen["args"] = (cwd, config, diff_lines, base)
        return GateResult("supply", "failed", "missing pypi package no-such-pkg"), 1, {"deptry": "0.25.1"}, _SUPPLY

    check_mod_supply = supply
    original = check_mod.run_supply_gate
    check_mod.run_supply_gate = check_mod_supply
    try:
        state = _measure(
            tmp_path,
            Config(),
            {"pyproject.toml": {4}},
            10.0,
            None,
            ["supply"],
            tmp_path / "out",
            None,
            "origin/main",
        )
    finally:
        check_mod.run_supply_gate = original

    assert seen["args"] == (tmp_path, Config(), {"pyproject.toml": {4}}, "origin/main")
    assert state.supply is _SUPPLY
    assert state.exit_code == 1
    assert state.versions == {"deptry": "0.25.1"}
    assert [(gate.name, gate.status) for gate in state.gates] == [("supply", "failed")]


def test_assemble_keeps_every_report_field() -> None:
    from bob_quality.check import _Measured

    changed = _metric("fresh", 8.0, True)
    stale = _metric("old", 12.0, False)
    clone = Clone("src/fresh.py", 1, 4, "src/old.py", 1, 4, 4, 20)
    in_diff = DepViolation("app", "legacy", "cycle", True)
    parked = DepViolation("app", "old", "layer", False)
    survivor = {"id": "m1", "file": "src/fresh.py", "waiver": None, "blocking": True}
    measured = _Measured(
        versions={"lizard": "1.24.1"},
        gates=[GateResult("crap", "passed")],
        metrics=[changed, stale],
        clones=[clone],
        violations=[in_diff, parked],
        exit_code=0,
        mutation=MutationOutcome(
            result=GateResult("mutate", "failed", "survivor"),
            exit_code=3,
            versions={"mutmut": "3.8.0"},
            waivers=[_WAIVER],
            survivors=[survivor],
            summary={"remutated": ["src/fresh.py::fresh"], "reused": []},
        ),
        supply=_SUPPLY,
    )

    report = _assemble(measured, "abc123", "origin/main", {"src/fresh.py": {1}}, 15.0, "bob check")

    assert report.schema_version == 1
    assert report.commit == "abc123"
    assert report.base == "origin/main"
    assert report.generated_at.endswith("+00:00")
    assert report.tool_versions == {"lizard": "1.24.1"}
    assert report.top_crap[0]["name"] == "fresh"
    assert report.old_debt == []
    assert report.dependencies == [{"origin": "app", "destination": "legacy", "rule": "cycle"}]
    assert report.old_dependencies == [{"origin": "app", "destination": "old", "rule": "layer"}]
    assert report.clones == [clone]
    assert report.reproduce == "bob check"
    assert report.waivers == [_WAIVER]
    assert report.survivors == [survivor]
    assert report.mutation == {"remutated": ["src/fresh.py::fresh"], "reused": []}
    assert report.supply is _SUPPLY
    assert report.focus[0]["file"] == "src/fresh.py"
    assert report.focus[0]["risk"] == 108.0


def test_assemble_without_mutation_keeps_empty_survivors_and_loaded_waivers() -> None:
    from bob_quality.check import _Measured

    measured = _Measured(
        metrics=[_metric("old", 12.0, False)],
        loaded_waivers=[_WAIVER],
    )

    report = _assemble(measured, "abc123", "origin/main", {}, 10.0, "bob check")

    assert report.survivors == []
    assert report.mutation is None
    assert report.waivers == [_WAIVER]
    assert report.old_debt[0]["name"] == "old"


def test_run_check_records_the_threshold_base_and_default_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bob_quality import check as check_mod

    repo = init_python_repo(tmp_path / "repo")
    coverage = tmp_path / "coverage.json"
    coverage.write_text("{}\n")
    seen: dict[str, object] = {}

    def crap(**kwargs: object):
        seen["crap"] = kwargs
        return GateResult("crap", "passed"), [_metric("old", 12.0, False)], 0, {"lizard": "1.24.1"}, 0

    def dry(**kwargs: object):
        return GateResult("dry", "passed"), [], 0, {}

    def deps(cwd: Path, config: Config, files: set[str]):
        return (
            GateResult("deps", "passed"),
            0,
            {},
            [DepViolation("app", "legacy", "cycle", True), DepViolation("app", "old", "layer", False)],
        )

    def supply(cwd: Path, config: Config, diff_lines: dict[str, set[int]], base: str):
        seen["supply_base"] = base
        return GateResult("supply", "passed"), 0, {"deptry": "0.25.1"}, _SUPPLY

    def mutate(**kwargs: object):
        seen["mutate"] = kwargs
        return MutationOutcome(
            result=GateResult("mutate", "passed"),
            exit_code=0,
            versions={"mutmut": "3.8.0"},
            waivers=[],
            survivors=[],
            summary={"remutated": [], "reused": []},
        )

    monkeypatch.setattr(check_mod, "run_crap_gate", crap)
    monkeypatch.setattr(check_mod, "run_dry_gate", dry)
    monkeypatch.setattr(check_mod, "run_deps_gate", deps)
    monkeypatch.setattr(check_mod, "run_supply_gate", supply)
    monkeypatch.setattr(check_mod, "run_mutate_gate", mutate)

    code = run_check(
        repo,
        base="main",
        gates=["crap", "dry", "deps", "supply", "mutate"],
        out_dir=repo / ".bob",
        fmt="json",
        threshold=15.0,
        coverage_file=coverage,
        max_workers=3,
    )
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

    assert code == 0
    assert payload["schema_version"] == 1
    assert payload["commit"] == head
    assert payload["base"] == "main"
    assert payload["reproduce"] == "bob check"
    assert payload["old_debt"] == []
    assert payload["dependencies"] == [{"origin": "app", "destination": "legacy", "rule": "cycle"}]
    assert payload["old_dependencies"] == [{"origin": "app", "destination": "old", "rule": "layer"}]
    assert payload["supply"]["findings"][0]["name"] == "no-such-pkg"
    assert seen["supply_base"] == "main"
    assert seen["crap"]["coverage_file"] == coverage
    assert seen["crap"]["max_crap"] == 15.0
    assert seen["mutate"]["max_workers"] == 3
    assert seen["mutate"]["baseline"] == 0


def test_run_check_without_gates_uses_the_default_three(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from bob_quality import check as check_mod

    repo = init_python_repo(tmp_path / "repo")
    names: list[str] = []

    def crap(**kwargs: object):
        names.append("crap")
        return GateResult("crap", "passed"), [], 0, {}, 0

    def dry(**kwargs: object):
        names.append("dry")
        return GateResult("dry", "passed"), [], 0, {}

    def deps(cwd: Path, config: Config, files: set[str]):
        names.append("deps")
        return GateResult("deps", "passed"), 0, {}, []

    monkeypatch.setattr(check_mod, "run_crap_gate", crap)
    monkeypatch.setattr(check_mod, "run_dry_gate", dry)
    monkeypatch.setattr(check_mod, "run_deps_gate", deps)

    code = run_check(repo, base="main", out_dir=repo / ".bob", fmt="json")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert code == 0
    assert names == ["crap", "dry", "deps"]
    assert [gate["name"] for gate in payload["gates"]] == ["crap", "dry", "deps"]


def test_run_check_loads_idle_waivers_when_mutation_did_not_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bob_quality import check as check_mod

    repo = init_python_repo(tmp_path / "repo")
    bob = repo / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text(
        "waivers:\n"
        "- id: kept-visible\n"
        "  reason: one line\n"
        "  author: ada\n"
        "  date: '2026-10-12'\n"
    )

    def crap(**kwargs: object):
        return GateResult("crap", "passed"), [], 0, {}, 0

    monkeypatch.setattr(check_mod, "run_crap_gate", crap)

    code = run_check(repo, base="main", gates=["crap"], out_dir=bob, fmt="json")
    payload = json.loads((bob / "report.json").read_text())

    assert code == 0
    assert payload["waivers"] == [_WAIVER]


def test_a_directory_without_git_still_records_the_default_command(tmp_path: Path) -> None:
    out = tmp_path / "out"

    code = run_check(tmp_path, base="main", gates=["crap"], out_dir=out, fmt="json")
    payload = json.loads((out / "report.json").read_text())

    assert code == 4
    assert payload["reproduce"] == "bob check"
    assert payload["gates"][0]["name"] == "crap"
    assert payload["gates"][0]["status"] == "not_run"


def test_broken_waivers_are_written_to_the_requested_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bob_quality import check as check_mod

    repo = init_python_repo(tmp_path / "repo")
    bob = repo / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text("[]\n")
    out = tmp_path / "out"

    def crap(**kwargs: object):
        return GateResult("crap", "passed"), [], 0, {}, 0

    monkeypatch.setattr(check_mod, "run_crap_gate", crap)

    code = run_check(repo, base="main", gates=["crap"], out_dir=out, fmt="both", lang="en")
    markdown = (out / "report.md").read_text()
    payload = json.loads((out / "report.json").read_text())

    assert code == 4
    assert ".bob/waivers.yaml must be a mapping" in markdown
    assert payload["gates"][0]["reason"] == ".bob/waivers.yaml must be a mapping"
    assert payload["reproduce"] == "bob check"
    assert payload["base"] == "main"
    assert payload["exit_code"] == 4
    assert payload["gates"][0]["name"] == "crap"
