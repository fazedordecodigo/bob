"""TypeScript ausente no mutate: um GateResult, o exit do Python fica."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bob_quality.check import run_check
from bob_quality.messages import msg
from bob_quality.models import GateResult
from bob_quality.mutate import MutationOutcome
from bob_quality.npm_tools import shutil as npm_shutil
from bob_quality.tools import ToolError
from helpers import init_mixed_repo, init_ts_repo

_NODE = "Node missing: install Node.js to measure TypeScript (c8 and vitest via npx)"
_SKIP = f"TypeScript skipped: {_NODE}"
_CORE = "plugin npm dependencies missing: npm ci --prefix plugin"


def _hide_node(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(npm_shutil, "which", lambda _name: None)


def _gate(repo: Path) -> dict[str, object]:
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    found = [gate for gate in payload["gates"] if gate["name"] == "mutate"]
    assert len(found) == 1
    return found[0]


def test_mixed_repo_missing_node_warns_and_keeps_a_python_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_mixed_repo(tmp_path / "repo")
    _hide_node(monkeypatch)

    code = run_check(repo, base="main", gates=["mutate"])

    assert code == 0
    assert _gate(repo) == {"name": "mutate", "status": "warn", "reason": _SKIP}


def test_mixed_repo_missing_node_keeps_python_exit_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bob_quality import mutate_gate

    repo = init_mixed_repo(tmp_path / "repo")
    _hide_node(monkeypatch)

    def python_survivor(*_args: object, **_kwargs: object) -> MutationOutcome:
        return MutationOutcome(
            result=GateResult(
                "mutate",
                "failed",
                msg("mutate.unwaived", mutants="classify@src/app/weak.py:2"),
            ),
            exit_code=3,
            versions={"mutmut": "3.8.0"},
            waivers=[],
            survivors=[
                {
                    "id": "app.weak.x_classify__mutmut_1",
                    "function": "classify",
                    "file": "src/app/weak.py",
                    "line": 2,
                    "operator": "AOR",
                    "status": "survived",
                    "waiver": None,
                }
            ],
            summary={
                "remutated": ["src/app/weak.py::classify"],
                "reused": [],
                "no_coverage": {"total": 0, "functions": []},
            },
        )

    monkeypatch.setattr(mutate_gate, "run_mutation_gate", python_survivor)

    code = run_check(repo, base="main", gates=["mutate"])

    assert code == 3
    assert _gate(repo) == {
        "name": "mutate",
        "status": "failed",
        "reason": f"survivor without waiver: classify@src/app/weak.py:2; {_SKIP}",
    }


def test_mixed_repo_missing_stryker_core_warns_on_a_python_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bob_quality import stryker_gate

    repo = init_mixed_repo(tmp_path / "repo")

    def missing(_prefix: Path, package: str) -> str:
        if package == "@stryker-mutator/core":
            raise ToolError(msg("npm.deps_missing", hint="npm ci --prefix plugin"))
        return "10.0.0"

    monkeypatch.setattr(stryker_gate, "installed_npm_version", missing)

    code = run_check(repo, base="main", gates=["mutate"])

    assert code == 0
    assert _gate(repo) == {
        "name": "mutate",
        "status": "warn",
        "reason": f"TypeScript skipped: {_CORE}",
    }


def test_typescript_only_missing_node_exits_4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    _hide_node(monkeypatch)

    code = run_check(repo, base="main", gates=["mutate"])

    assert code == 4
    assert _gate(repo) == {"name": "mutate", "status": "not_run", "reason": _NODE}
