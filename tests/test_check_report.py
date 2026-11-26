from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

import pytest

from bob_quality.check import _Measured, _assemble, run_check
from bob_quality.churn import ChurnMeasured, ChurnWindow, FileChurn, Hotspot
from bob_quality.models import Clone, DepViolation, FunctionMetric, GateResult
from bob_quality.mutate import MutationOutcome
from bob_quality.report import to_json


def test_omitted_gates_and_reproduce_use_the_defaults(tmp_path: Path) -> None:
    repo, base, _tip = _function_repo(tmp_path)

    assert run_check(repo, base=base) == 0

    payload = _payload(repo)
    assert payload["gates"] == [
        {"name": "crap", "status": "passed", "reason": None},
        {"name": "dry", "status": "passed", "reason": None},
        {"name": "deps", "status": "passed", "reason": None},
    ]
    assert payload["reproduce"] == "bob check"
    assert payload["generated_at"].endswith("+00:00")


def test_threshold_is_the_crap_limit_for_changed_and_old_functions(tmp_path: Path) -> None:
    repo, base, tip = _function_repo(tmp_path)

    assert run_check(repo, base=base, threshold=1.0, gates=["crap"]) == 1

    payload = _payload(repo)
    assert payload["schema_version"] == 1
    assert payload["commit"] == tip
    assert payload["base"] == base
    assert payload["exit_code"] == 1
    assert payload["reproduce"] == "bob check"
    assert payload["generated_at"].endswith("+00:00")
    assert payload["gates"] == [
        {
            "name": "crap",
            "status": "failed",
            "reason": "CRAP >= 1.0: fresh@src/new.py:1",
        }
    ]
    assert payload["focus"] == [{"file": "src/new.py", "risk": 2.0}]
    assert payload["top_crap"] == [
        {
            "lang": "python",
            "module": "src.new",
            "name": "fresh",
            "file": "src/new.py",
            "start_line": 1,
            "end_line": 2,
            "cc": 1,
            "coverage": 0.0,
            "crap": 2.0,
            "changed": True,
            "delta": None,
        }
    ]
    assert payload["old_debt"] == [
        {
            "lang": "python",
            "module": "src.old",
            "name": "old",
            "file": "src/old.py",
            "start_line": 1,
            "end_line": 2,
            "cc": 1,
            "coverage": 0.0,
            "crap": 2.0,
            "changed": False,
            "delta": None,
        }
    ]
    assert payload["churn"]["window_days"] == 90
    assert payload["churn"]["files"] == [{"path": "src/new.py", "commits": 2, "relative": 0.5}]
    assert payload["churn"]["hotspots"] == [
        {
            "file": "src/new.py",
            "function": "fresh",
            "start_line": 1,
            "cc": 1,
            "commits": 2,
            "hotspot": 2,
        }
    ]


def test_a_missing_coverage_file_stays_a_tool_failure(tmp_path: Path) -> None:
    repo, base, _tip = _function_repo(tmp_path)

    assert (
        run_check(repo, base=base, gates=["crap"], coverage_file=repo / "missing.coverage")
        == 4
    )

    assert _payload(repo)["gates"] == [
        {
            "name": "crap",
            "status": "not_run",
            "reason": "coverage.py: No data to report.\n",
        }
    ]


def test_a_repo_without_code_skips_crap_and_coverage_and_exits_0(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "bob-test@example.com")
    _git(repo, "config", "user.name", "bob-test")
    _write(repo, "README.md", "# leia\n")
    _write(repo, "bob.yaml", 'paths:\n  include: ["."]\n')
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")

    assert run_check(repo, base="HEAD", gates=["crap", "coverage"]) == 0

    assert _payload(repo)["gates"] == [
        {"name": "crap", "status": "not_run", "reason": "no code to measure"},
        {"name": "coverage", "status": "not_run", "reason": "no code to measure"},
    ]
    assert _payload(repo)["exit_code"] == 0
    lines = (repo / ".bob" / "report.md").read_text(encoding="utf-8").splitlines()
    assert "- ⏭️ `crap`: not run (no code to measure)" in lines
    assert "- ⏭️ `coverage`: not run (no code to measure)" in lines

    assert run_check(repo, base="HEAD", lang="pt-BR") == 0

    assert [gate["name"] for gate in _payload(repo)["gates"]] == ["crap", "dry", "deps"]
    assert _payload(repo)["gates"][0]["status"] == "not_run"
    assert _payload(repo)["exit_code"] == 0
    lines = (repo / ".bob" / "report.md").read_text(encoding="utf-8").splitlines()
    assert "- ⏭️ `crap`: não executado (nenhum código a medir)" in lines


def test_a_missing_coverage_file_keeps_the_coverage_gate_a_tool_failure(
    tmp_path: Path,
) -> None:
    repo, base, _tip = _function_repo(tmp_path)

    assert (
        run_check(
            repo, base=base, gates=["coverage"], coverage_file=repo / "missing.coverage"
        )
        == 4
    )

    gate = _payload(repo)["gates"][0]
    assert gate["name"] == "coverage"
    assert gate["status"] == "not_run"
    assert gate["reason"].strip() == "No data to report."


def test_missing_config_keeps_the_requested_base_and_command(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    missing = repo / "missing.yaml"

    assert (
        run_check(
            repo,
            base="origin/feature",
            gates=["crap", "deps"],
            config_path=missing,
            reproduce="bob check --config missing.yaml",
        )
        == 4
    )

    payload = _payload(repo)
    assert payload["generated_at"].endswith("+00:00")
    payload["generated_at"] = "STAMP"
    assert payload == {
        "schema_version": 1,
        "commit": "",
        "base": "origin/feature",
        "generated_at": "STAMP",
        "tool_versions": {},
        "gates": [
            {
                "name": "crap",
                "status": "not_run",
                "reason": f"config file not found: {missing}",
            },
            {
                "name": "deps",
                "status": "not_run",
                "reason": f"config file not found: {missing}",
            },
        ],
        "focus": [],
        "top_crap": [],
        "old_debt": [],
        "dependencies": [],
        "old_dependencies": [],
        "clones": [],
        "waivers": [],
        "survivors": [],
        "mutation": None,
        "churn": {"kind": "unavailable"},
        "reproduce": "bob check --config missing.yaml",
        "exit_code": 4,
    }


def test_missing_config_without_a_base_stays_blank(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    assert run_check(repo, config_path=repo / "missing.yaml", gates=["crap"]) == 4

    payload = _payload(repo)
    assert payload["base"] == ""
    assert payload["commit"] == ""
    assert payload["reproduce"] == "bob check"
    assert payload["schema_version"] == 1
    assert payload["tool_versions"] == {}
    assert payload["focus"] == []
    assert payload["top_crap"] == []
    assert payload["churn"] == {"kind": "unavailable"}
    assert payload["generated_at"].endswith("+00:00")


def test_invalid_waivers_replace_the_measured_report(tmp_path: Path) -> None:
    repo, base, _tip = _function_repo(tmp_path)
    bob = repo / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text("waivers: [5]\n")

    assert (
        run_check(
            repo,
            base=base,
            gates=["nope"],
            reproduce="bob check --base main",
        )
        == 4
    )

    payload = _payload(repo)
    assert payload["base"] == base
    assert payload["reproduce"] == "bob check --base main"
    assert payload["exit_code"] == 4
    assert payload["gates"] == [
        {
            "name": "nope",
            "status": "not_run",
            "reason": ".bob/waivers.yaml: waivers[0] must be a mapping",
        }
    ]
    assert payload["churn"] == {"kind": "unavailable"}


def test_max_workers_and_mutation_fields_reach_the_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, base, _tip = _function_repo(tmp_path)
    seen: dict[str, object] = {}

    def fake(
        cwd: Path,
        config: object,
        diff_lines: dict[str, set[int]],
        out_dir: Path,
        max_workers: int | None,
        baseline: int | None,
    ) -> MutationOutcome:
        seen["max_workers"] = max_workers
        return MutationOutcome(
            result=GateResult("mutate", "failed", "survivor"),
            exit_code=3,
            versions={"mutmut": "3.8.0"},
            waivers=[
                {
                    "id": "used",
                    "reason": "equivalent",
                    "author": "ada",
                    "date": "2020-01-02",
                }
            ],
            survivors=[
                {
                    "id": "bob_quality.new.x_fresh__mutmut_1",
                    "function": "fresh",
                    "file": "src/new.py",
                    "line": 1,
                    "operator": "x",
                    "status": "survived",
                    "blocking": True,
                }
            ],
            summary={
                "remutated": ["src/new.py:fresh"],
                "reused": [],
                "no_coverage": {"total": 0, "functions": []},
            },
        )

    monkeypatch.setattr("bob_quality.check.run_mutate_gate", fake)

    assert run_check(repo, base=base, gates=["mutate"], max_workers=3) == 3

    payload = _payload(repo)
    assert seen["max_workers"] == 3
    assert payload["exit_code"] == 3
    assert payload["tool_versions"] == {"mutmut": "3.8.0"}
    assert payload["mutation"] == {
        "remutated": ["src/new.py:fresh"],
        "reused": [],
        "no_coverage": {"total": 0, "functions": []},
    }
    assert payload["waivers"] == [
        {"id": "used", "reason": "equivalent", "author": "ada", "date": "2020-01-02"}
    ]
    assert payload["survivors"] == [
        {
            "id": "bob_quality.new.x_fresh__mutmut_1",
            "function": "fresh",
            "file": "src/new.py",
            "line": 1,
            "operator": "x",
            "status": "survived",
            "blocking": True,
        }
    ]
    assert payload["focus"] == [{"file": "src/new.py", "risk": 100.0}]
    assert payload["gates"] == [
        {"name": "mutate", "status": "failed", "reason": "survivor"}
    ]


def test_assemble_copies_every_measured_field() -> None:
    changed = FunctionMetric(
        lang="python",
        module="src.new",
        name="fresh",
        file="src/new.py",
        start_line=1,
        end_line=2,
        cc=2,
        coverage=0.5,
        crap=4.0,
        changed=True,
        delta=1.0,
    )
    unchanged = FunctionMetric(
        lang="python",
        module="src.old",
        name="old",
        file="src/old.py",
        start_line=1,
        end_line=4,
        cc=5,
        coverage=0.0,
        crap=30.0,
        changed=False,
    )
    clone = Clone(
        first_file="src/new.py",
        first_start=1,
        first_end=2,
        second_file="src/old.py",
        second_start=1,
        second_end=4,
        lines=2,
        tokens=8,
    )
    measured = _Measured(
        versions={"lizard": "1.24.1"},
        gates=[GateResult("crap", "failed", "CRAP >= 10: fresh@src/new.py:1")],
        metrics=[changed, unchanged],
        clones=[clone],
        violations=[
            DepViolation("src.new", "src.old", "blocked", True),
            DepViolation("src.old", "src.other", "legacy", False),
        ],
        exit_code=1,
        mutation=MutationOutcome(
            result=GateResult("mutate", "failed", "survivor"),
            exit_code=3,
            versions={"mutmut": "3.8.0"},
            waivers=[
                {
                    "id": "used",
                    "reason": "equivalent",
                    "author": "ada",
                    "date": "2020-01-02",
                }
            ],
            survivors=[
                {
                    "id": "kept",
                    "function": "fresh",
                    "file": "src/new.py",
                    "line": 1,
                    "operator": "x",
                    "status": "survived",
                    "blocking": True,
                }
            ],
            summary={"remutated": ["src/new.py:fresh"], "reused": [], "no_coverage": {}},
        ),
        loaded_waivers=[
            {"id": "idle", "reason": "no", "author": "bea", "date": "2020-01-01"}
        ],
    )
    section = ChurnMeasured(
        ChurnWindow(7, date(2020, 1, 2)),
        (FileChurn("src/new.py", 4, None),),
        (Hotspot("src/new.py", "fresh", 1, 2, 4),),
    )

    report = _assemble(
        measured,
        "abc123",
        "main",
        {"src/new.py": {2}},
        10.0,
        "bob check --gates mutate",
        section,
    )

    payload = to_json(report)
    assert payload["generated_at"].endswith("+00:00")
    payload["generated_at"] = "STAMP"
    assert payload == {
        "schema_version": 1,
        "commit": "abc123",
        "base": "main",
        "generated_at": "STAMP",
        "tool_versions": {"lizard": "1.24.1"},
        "gates": [
            {
                "name": "crap",
                "status": "failed",
                "reason": "CRAP >= 10: fresh@src/new.py:1",
            }
        ],
        "focus": [{"file": "src/new.py", "risk": 104.0, "clone": True}],
        "top_crap": [
            {
                "lang": "python",
                "module": "src.new",
                "name": "fresh",
                "file": "src/new.py",
                "start_line": 1,
                "end_line": 2,
                "cc": 2,
                "coverage": 0.5,
                "crap": 4.0,
                "changed": True,
                "delta": 1.0,
            }
        ],
        "old_debt": [
            {
                "lang": "python",
                "module": "src.old",
                "name": "old",
                "file": "src/old.py",
                "start_line": 1,
                "end_line": 4,
                "cc": 5,
                "coverage": 0.0,
                "crap": 30.0,
                "changed": False,
                "delta": None,
            }
        ],
        "dependencies": [
            {"origin": "src.new", "destination": "src.old", "rule": "blocked"}
        ],
        "old_dependencies": [
            {"origin": "src.old", "destination": "src.other", "rule": "legacy"}
        ],
        "clones": [
            {
                "first_file": "src/new.py",
                "first_start": 1,
                "first_end": 2,
                "second_file": "src/old.py",
                "second_start": 1,
                "second_end": 4,
                "lines": 2,
                "tokens": 8,
                "similarity": None,
                "kind": "",
            }
        ],
        "waivers": [
            {"id": "used", "reason": "equivalent", "author": "ada", "date": "2020-01-02"}
        ],
        "survivors": [
            {
                "id": "kept",
                "function": "fresh",
                "file": "src/new.py",
                "line": 1,
                "operator": "x",
                "status": "survived",
                "blocking": True,
            }
        ],
        "mutation": {"remutated": ["src/new.py:fresh"], "reused": [], "no_coverage": {}},
        "churn": {
            "kind": "measured",
            "window_days": 7,
            "ends_on": "2020-01-02",
            "files": [{"path": "src/new.py", "commits": 4, "relative": None}],
            "hotspots": [
                {
                    "file": "src/new.py",
                    "function": "fresh",
                    "start_line": 1,
                    "cc": 2,
                    "commits": 4,
                    "hotspot": 8,
                }
            ],
            "diffusion": {"files": 1, "modules": 1},
        },
        "reproduce": "bob check --gates mutate",
        "exit_code": 1,
    }


def _payload(repo: Path) -> dict[str, object]:
    return json.loads((repo / ".bob" / "report.json").read_text())


def _function_repo(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "bob-test@example.com")
    _git(repo, "config", "user.name", "bob-test")
    _write(repo, "src/old.py", "def old():\n    return 1\n")
    _write(repo, "src/new.py", "def fresh():\n    return 1\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    _write(repo, "src/new.py", "def fresh():\n    return 2\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "change")
    return repo, base, _git(repo, "rev-parse", "HEAD")


def _write(repo: Path, path: str, text: str) -> None:
    file = repo / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text)


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()
