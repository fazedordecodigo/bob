"""Argv do Stryker incremental e o que acontece quando o relatório não vem."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from bob_quality.config import load_config
from bob_quality.deps_gate import _TS_EXTENSIONS
from bob_quality.diff import changed_lines
from helpers import commit_on_branch, in_both, init_ts_repo

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(__file__).parent / "fixtures" / "raw"
PLUGIN = ROOT / "src" / "bob_quality" / "js" / "stryker-vitest5-plugin.mjs"
DRY_RUN = (RAW / "stryker-initial-test-run.txt").read_text()

def _only_stryker(monkeypatch: pytest.MonkeyPatch, fake):
    from bob_quality import stryker_gate

    real_run = subprocess.run

    def wrapped(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if args and args[0] == "npx":
            return fake(args, **kwargs)
        return real_run(args, **kwargs)

    monkeypatch.setattr(stryker_gate.subprocess, "run", wrapped)


SAFE_TS = """\
export function add(left: number, right: number): number {
  return left + right;
}

export function scale(value: number): number {
  return value * 2;
}
"""
TYPES_D_TS = "export function ghost(value: number): number;\n"

_KILLED = json.dumps(
    {
        "files": {
            "src/safe.ts": {
                "mutants": [
                    {
                        "id": "0",
                        "mutatorName": "ArithmeticOperator",
                        "status": "Killed",
                        "location": {
                            "start": {"line": 2, "column": 10},
                            "end": {"line": 2, "column": 11},
                        },
                    }
                ]
            }
        }
    }
)


_WAIVER = {
    "id": "src/safe.ts:9",
    "reason": "kept so the waiver list is observable",
    "author": "test",
    "date": "2026-10-12",
}


def _repo(tmp_path: Path) -> Path:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(repo, "change", "src/safe.ts", SAFE_TS, "change safe")
    commit_on_branch(repo, "change", "src/types.d.ts", TYPES_D_TS, "add types")
    bob = repo / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text(
        "waivers:\n"
        "- id: src/safe.ts:9\n"
        "  reason: kept so the waiver list is observable\n"
        "  author: test\n"
        "  date: '2026-10-12'\n"
    )
    return repo


def _assert_carried(outcome) -> None:
    assert outcome.versions["stryker"] == "10.0.0"
    assert outcome.versions["stryker-vitest-runner"] == "10.0.0"
    assert outcome.waivers == [_WAIVER]
    assert outcome.result.name == "mutate"


def test_mutate_extensions_match_the_dependency_gate() -> None:
    from bob_quality.stryker_gate import MUTATE_EXTENSIONS

    assert MUTATE_EXTENSIONS == _TS_EXTENSIONS


def test_preload_keeps_node_options_and_adds_the_import_once() -> None:
    from bob_quality.stryker_gate import _preload_vitest_hook

    plugin = str(PLUGIN.resolve())
    fresh: dict[str, str] = {}
    _preload_vitest_hook(fresh)
    assert fresh == {"NODE_OPTIONS": f"--import {plugin}"}

    existing = {"NODE_OPTIONS": "--no-warnings"}
    _preload_vitest_hook(existing)
    assert existing == {"NODE_OPTIONS": f"--no-warnings --import {plugin}"}

    present = {"NODE_OPTIONS": f"--no-warnings --import {plugin}"}
    _preload_vitest_hook(present)
    assert present == {"NODE_OPTIONS": f"--no-warnings --import {plugin}"}

    prefix = {"NODE_OPTIONS": f"--import {plugin}-extra"}
    _preload_vitest_hook(prefix)
    assert prefix == {"NODE_OPTIONS": f"--import {plugin}-extra --import {plugin}"}


def test_incremental_argv_deletes_a_stale_report_and_ignores_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    report = repo / ".bob" / "stryker-report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text('{"stale": true}\n')
    seen: list[bool] = []
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        seen.append(report.exists())
        report.write_text(_KILLED)
        assert kwargs["cwd"] == repo
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["stdin"] is subprocess.DEVNULL
        assert f"--import {PLUGIN.resolve()}" in kwargs["env"]["NODE_OPTIONS"]
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

    _only_stryker(monkeypatch, fake_run)
    from bob_quality.mutate_gate import run_mutate_gate

    outcome = run_mutate_gate(
        repo,
        load_config(None, repo),
        changed_lines(repo, "main"),
        repo / ".bob",
        max_workers=7,
        baseline=2,
    )

    assert seen == [False]
    assert outcome.exit_code == 0
    assert outcome.result.status == "passed"
    args = calls[0]
    prefix = args[2]
    assert args == [
        "npx",
        "--prefix",
        prefix,
        "stryker",
        "run",
        ".bob/stryker.config.json",
        "--incremental",
        "--incrementalFile",
        ".bob/stryker-incremental.json",
        "--mutate",
        "src/safe.ts:1-5,src/safe.ts:5-7",
    ]
    assert "--force" not in args
    assert "--concurrency" not in args
    assert "--maxConcurrentTestRunners" not in args
    assert "7" not in args
    assert json.loads((Path(prefix) / "package.json").read_text())["name"] == "bob-quality-tools"
    written = (repo / ".bob" / "stryker.config.json").read_text()
    assert written == json.dumps(json.loads(written), indent=2) + "\n"
    _assert_carried(outcome)
    assert json.loads(written) == {
        "plugins": ["@stryker-mutator/*", str(PLUGIN.resolve())],
        "testRunner": "vitest",
        "vitest": {
            "related": False,
            "configFile": str((repo / "vitest.config.mjs").resolve()),
        },
        "coverageAnalysis": "perTest",
        "disableTypeChecks": True,
        "thresholds": {"break": None},
        "reporters": ["json"],
        "jsonReporter": {"fileName": ".bob/stryker-report.json"},
        "tempDirName": ".bob/stryker-tmp",
        "incremental": True,
        "incrementalFile": ".bob/stryker-incremental.json",
    }


def test_missing_report_retries_once_after_deleting_the_incremental_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    incremental = repo / ".bob" / "stryker-incremental.json"
    report = repo / ".bob" / "stryker-report.json"
    incremental.parent.mkdir(parents=True, exist_ok=True)
    incremental.write_text("{}\n")
    report.write_text('{"stale": true}\n')
    states: list[tuple[bool, bool]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["cwd"] == repo
        states.append((report.exists(), incremental.exists()))
        if len(states) == 2:
            report.write_text(_KILLED)
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

    _only_stryker(monkeypatch, fake_run)
    from bob_quality.mutate_gate import run_mutate_gate

    outcome = run_mutate_gate(
        repo,
        load_config(None, repo),
        changed_lines(repo, "main"),
        repo / ".bob",
    )

    assert states == [(False, True), (False, False)]
    assert outcome.exit_code == 0
    assert outcome.result.status == "passed"
    _assert_carried(outcome)


def test_a_second_missing_report_exits_4(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _repo(tmp_path)
    incremental = repo / ".bob" / "stryker-incremental.json"
    incremental.parent.mkdir(parents=True, exist_ok=True)
    incremental.write_text("{}\n")
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

    _only_stryker(monkeypatch, fake_run)
    from bob_quality.mutate_gate import run_mutate_gate

    outcome = run_mutate_gate(
        repo,
        load_config(None, repo),
        changed_lines(repo, "main"),
        repo / ".bob",
    )

    assert len(calls) == 2
    assert outcome.exit_code == 4
    assert outcome.result.status == "not_run"
    _assert_carried(outcome)
    assert in_both(outcome.result.reason) == (
        "Stryker did not write the report",
        "o Stryker não gravou o relatório",
    )


def test_dry_run_failure_exits_2_and_does_not_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert "There were failed tests in the initial test run." in DRY_RUN
    repo = _repo(tmp_path)
    incremental = repo / ".bob" / "stryker-incremental.json"
    incremental.parent.mkdir(parents=True, exist_ok=True)
    incremental.write_text("{}\n")
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 1, stdout="", stderr=DRY_RUN)

    _only_stryker(monkeypatch, fake_run)
    from bob_quality.mutate_gate import run_mutate_gate

    outcome = run_mutate_gate(
        repo,
        load_config(None, repo),
        changed_lines(repo, "main"),
        repo / ".bob",
    )

    assert len(calls) == 1
    assert incremental.is_file()
    assert outcome.exit_code == 2
    assert outcome.result.status == "not_run"
    _assert_carried(outcome)
    assert in_both(outcome.result.reason) == (
        "baseline tests failed before measuring",
        "testes da baseline falharam antes de medir",
    )
