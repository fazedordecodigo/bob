from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from bob_quality.config import load_config
from bob_quality.coverage_gate import _line_numbers, _load_files, run_coverage_gate
from bob_quality.tools import ToolError
from bob_quality.messages import render
from bob_quality.python_probe import measure_python
from bob_quality.suite_memo import SuiteMemo

from helpers import commit_on_branch, commit_on_main, init_mixed_repo, init_python_repo, init_ts_repo, run_bob

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "src/bob_quality/schemas/report_v1.json").read_text()
)
STUB = "def gap(flag: bool) -> int:\n    return 1\n"
GAP_75 = """\
def gap(flag: bool) -> int:
    one = 1
    if flag:
        return one
    return 0
"""
GAP_75_TEST = """\
from app.gap import gap


def test_gap() -> None:
    assert gap(True) == 1
"""
GAP_80 = """\
def gap(flag: bool) -> int:
    one = 1
    two = 2
    if flag:
        return one + two
    return 0
"""
GAP_80_TEST = """\
from app.gap import gap


def test_gap() -> None:
    assert gap(True) == 3
"""
KEPT = "def kept() -> int:\n    extra = 1\n    return 1\n"
KEPT_SHORTER = "def kept() -> int:\n    return 1\n"
KEPT_TEST = """\
from app.kept import kept


def test_kept() -> None:
    assert kept() == 1
"""
BROKEN_TEST = "from app.safe import add\n\n\ndef test_add() -> None:\n    assert add(1, 2) == 0\n"
TOUCHED_ADD = "def add(left: int, right: int) -> int:\n    return left + right  # soma\n"
RUN_LOGGER = """\
from pathlib import Path


def test_logs_the_run() -> None:
    where = "mutants" if "mutants" in Path(__file__).parts else "repo"
    with Path({log!r}).open("a") as runs:
        runs.write(where + "\\n")
"""
TS_MISSED = "export function missed(): number {\n  return 9;\n}\n"
TS_TOUCHED = """\
export function add(left: number, right: number): number {
  // soma
  return left + right;
}
"""
TS_LOG_TEST = """\
import { appendFileSync } from "node:fs";
import { expect, test } from "vitest";
import { add } from "../src/safe";

test("add", () => {
  appendFileSync(process.env.BOB_VITEST_LOG ?? "", "vitest\\n");
  expect(add(1, 2)).toBe(3);
});
"""
NODE_MISSING = (
    "Node missing: install Node.js to measure TypeScript (c8 and vitest via npx)"
)


def _payload(repo: Path) -> tuple[dict[str, object], str]:
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    return payload, markdown


def _coverage(payload: dict[str, object]) -> dict[str, object]:
    gates = payload["gates"]
    assert isinstance(gates, list)
    return next(gate for gate in gates if gate["name"] == "coverage")


def _python_gap(tmp_path: Path, source: str, test: str) -> Path:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/gap.py", STUB, "stub gap")
    commit_on_main(repo, "tests/test_gap.py", test, "test gap")
    commit_on_branch(repo, "gap", "src/app/gap.py", source, "cover gap")
    return repo


def _waive(repo: Path, waiver_id: str) -> None:
    path = repo / ".bob" / "waivers.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "waivers:\n"
        f"  - id: {waiver_id}\n"
        "    reason: generated table\n"
        "    author: ada\n"
        "    date: '2026-10-12'\n"
    )


def _without_node(repo: Path, gates: str) -> subprocess.CompletedProcess[str]:
    bindir = repo.parent / "bin"
    bindir.mkdir()
    git = shutil.which("git")
    assert git is not None
    os.symlink(git, bindir / "git")
    env = {key: value for key, value in os.environ.items() if key != "BOB_LANG"}
    env["PATH"] = str(bindir)
    return subprocess.run(
        [sys.executable, "-m", "bob_quality", "check", "--base", "main", "--gates", gates],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def test_eighty_percent_passes(tmp_path: Path) -> None:
    repo = _python_gap(tmp_path, GAP_80, GAP_80_TEST)

    result = run_bob(repo, "check", "--base", "main", "--gates", "coverage", bob_lang="pt-BR")
    payload, markdown = _payload(repo)

    assert result.returncode == 0, result.stderr
    assert payload["exit_code"] == 0
    assert _coverage(payload) == {"name": "coverage", "status": "passed", "reason": None}
    assert payload["diff_coverage"] == {
        "python": 80.0,
        "uncovered": [{"file": "src/app/gap.py", "line": 6}],
    }
    Draft202012Validator(SCHEMA).validate(payload)
    assert "## Cobertura do diff" in markdown
    assert "| python | 80.00% |" in markdown
    assert "`src/app/gap.py:6`" in markdown


def test_seventy_five_percent_fails_on_the_uncovered_line(tmp_path: Path) -> None:
    repo = _python_gap(tmp_path, GAP_75, GAP_75_TEST)

    result = run_bob(repo, "check", "--base", "main", "--gates", "coverage")
    payload, markdown = _payload(repo)

    assert result.returncode == 1, result.stderr
    assert payload["exit_code"] == 1
    assert _coverage(payload) == {
        "name": "coverage",
        "status": "failed",
        "reason": "python 75.00% < 80",
    }
    assert payload["diff_coverage"] == {
        "python": 75.0,
        "uncovered": [{"file": "src/app/gap.py", "line": 5}],
    }
    Draft202012Validator(SCHEMA).validate(payload)
    assert "## Diff coverage" in markdown
    assert "| python | 75.00% |" in markdown
    assert "`src/app/gap.py:5`" in markdown
    assert markdown.index("## Diff coverage") < markdown.index("## How to reproduce")


def test_a_line_waiver_of_the_uncovered_line_passes_at_100(tmp_path: Path) -> None:
    repo = _python_gap(tmp_path, GAP_75, GAP_75_TEST)
    _waive(repo, "coverage:src/app/gap.py:5")

    result = run_bob(repo, "check", "--base", "main", "--gates", "coverage")
    payload, _markdown = _payload(repo)

    assert result.returncode == 0, result.stderr
    assert _coverage(payload)["status"] == "passed"
    assert payload["diff_coverage"] == {"python": 100.0, "uncovered": []}


def test_a_file_waiver_passes_at_100(tmp_path: Path) -> None:
    repo = _python_gap(tmp_path, GAP_75, GAP_75_TEST)
    _waive(repo, "coverage:src/app/gap.py")

    result = run_bob(repo, "check", "--base", "main", "--gates", "coverage")
    payload, _markdown = _payload(repo)

    assert result.returncode == 0, result.stderr
    assert payload["diff_coverage"] == {"python": 100.0, "uncovered": []}


def test_a_pure_deletion_passes_at_100(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/kept.py", KEPT, "kept")
    commit_on_main(repo, "tests/test_kept.py", KEPT_TEST, "test kept")
    commit_on_branch(repo, "drop", "src/app/kept.py", KEPT_SHORTER, "delete extra")

    result = run_bob(repo, "check", "--base", "main", "--gates", "coverage")
    payload, _markdown = _payload(repo)

    assert result.returncode == 0, result.stderr
    assert payload["diff_coverage"] == {"python": 100.0, "uncovered": []}


def test_a_broken_pytest_exits_2_and_omits_diff_coverage(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "break", "tests/test_safe.py", BROKEN_TEST, "break the suite")

    result = run_bob(repo, "check", "--base", "main", "--gates", "coverage")
    payload, markdown = _payload(repo)

    assert result.returncode == 2, result.stderr
    assert payload["exit_code"] == 2
    assert "diff_coverage" not in payload
    assert _coverage(payload) == {
        "name": "coverage",
        "status": "not_run",
        "reason": "baseline tests failed before measuring",
    }
    assert "## Diff coverage" in markdown
    assert "baseline tests failed before measuring" in markdown
    assert "| Language | Percent |" not in markdown


def test_typescript_only_without_node_exits_4(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(repo, "touch", "src/safe.ts", TS_TOUCHED, "touch add")

    result = _without_node(repo, "coverage")
    payload, _markdown = _payload(repo)

    assert result.returncode == 4, result.stderr
    assert "diff_coverage" not in payload
    assert _coverage(payload) == {
        "name": "coverage",
        "status": "not_run",
        "reason": NODE_MISSING,
    }


def test_mixed_without_node_follows_the_python_percent(tmp_path: Path) -> None:
    repo = init_mixed_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/gap.py", STUB, "stub gap")
    commit_on_main(repo, "tests/test_gap.py", GAP_75_TEST, "test gap")
    commit_on_branch(repo, "gap", "src/app/gap.py", GAP_75, "cover gap")

    result = _without_node(repo, "coverage")
    payload, _markdown = _payload(repo)
    diff_coverage = payload["diff_coverage"]

    assert result.returncode == 1, result.stderr
    assert isinstance(diff_coverage, dict)
    assert diff_coverage == {
        "python": 75.0,
        "uncovered": [{"file": "src/app/gap.py", "line": 5}],
    }
    assert "typescript" not in diff_coverage
    assert _coverage(payload) == {
        "name": "coverage",
        "status": "failed",
        "reason": f"python 75.00% < 80; typescript skipped: {NODE_MISSING}",
    }


def test_crap_and_coverage_run_pytest_once(tmp_path: Path) -> None:
    counts: dict[str, int] = {}
    codes: dict[str, int] = {}
    for gates in ("crap,coverage", "coverage,crap"):
        log = tmp_path / f"{gates}.log"
        repo = init_python_repo(tmp_path / gates.replace(",", "-"))
        commit_on_main(repo, "tests/test_runs.py", RUN_LOGGER.format(log=str(log)), "log runs")
        commit_on_branch(repo, "touch", "src/app/safe.py", TOUCHED_ADD, "comment inside add")
        codes[gates] = run_bob(repo, "check", "--base", "main", "--gates", gates).returncode
        counts[gates] = log.read_text().splitlines().count("repo")

    assert codes == {"crap,coverage": 0, "coverage,crap": 0}
    assert counts == {"crap,coverage": 1, "coverage,crap": 1}


def test_crap_and_coverage_run_vitest_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    counts: dict[str, int] = {}
    codes: dict[str, int] = {}
    for gates in ("crap,coverage", "coverage,crap"):
        log = tmp_path / f"{gates}.log"
        monkeypatch.setenv("BOB_VITEST_LOG", str(log))
        repo = init_ts_repo(tmp_path / gates.replace(",", "-"))
        commit_on_main(repo, "tests/safe.test.ts", TS_LOG_TEST, "log vitest")
        commit_on_branch(repo, "touch", "src/safe.ts", TS_TOUCHED, "comment inside add")
        codes[gates] = run_bob(repo, "check", "--base", "main", "--gates", gates).returncode
        counts[gates] = log.read_text().splitlines().count("vitest")

    assert codes == {"crap,coverage": 0, "coverage,crap": 0}
    assert counts == {"crap,coverage": 1, "coverage,crap": 1}


def test_missing_diff_cover_exits_4_and_crap_still_measures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("bob_quality.coverage_gate.diff_cover_version", lambda: None)
    log = tmp_path / "runs.log"
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "tests/test_runs.py", RUN_LOGGER.format(log=str(log)), "log runs")
    commit_on_branch(repo, "touch", "src/app/safe.py", TOUCHED_ADD, "comment inside add")
    config = load_config(None, repo)
    memo = SuiteMemo(want_lcov=True, want_json=True)

    outcome = run_coverage_gate(repo, config, "main", None, memo)

    assert outcome.exit_code == 4
    assert outcome.diff_coverage is None
    assert outcome.result.status == "not_run"
    assert render(outcome.result.reason, "en") == "missing tool: diff-cover"
    assert not log.exists()
    probed = measure_python(repo, config, {}, None, memo)
    assert probed.exit_code is None
    assert probed.gate is None
    assert log.read_text().splitlines().count("repo") == 1
    memo.close()


def test_a_fractional_floor_uses_the_measured_percent(tmp_path: Path) -> None:
    repo = _python_gap(tmp_path, GAP_80, GAP_80_TEST)
    (repo / "bob.yaml").write_text("coverage:\n  min_percent: 80.5\n")

    result = run_bob(repo, "check", "--base", "main", "--gates", "coverage")
    payload, _markdown = _payload(repo)

    assert result.returncode == 1, result.stderr
    assert _coverage(payload)["reason"] == "python 80.00% < 80.5"


def test_unreadable_diff_cover_json_is_a_tool_error() -> None:
    with pytest.raises(ToolError):
        _load_files("nope")
    with pytest.raises(ToolError):
        _load_files("[]")
    with pytest.raises(ToolError):
        _load_files('{"src_stats": []}')
    with pytest.raises(ToolError):
        _load_files('{"src_stats": {"a.py": []}}')


def test_line_numbers_reject_a_boolean_and_a_string() -> None:
    with pytest.raises(ValueError):
        _line_numbers([True])
    with pytest.raises(ValueError):
        _line_numbers(["4"])
    with pytest.raises(ValueError):
        _line_numbers(1)

    assert _line_numbers([4, 4]) == frozenset({4})


def test_typescript_diff_coverage_reports_the_uncovered_lines(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(repo, "gap", "src/missed.ts", TS_MISSED, "untested file")

    result = run_bob(repo, "check", "--base", "main", "--gates", "coverage")
    payload, markdown = _payload(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert _coverage(payload) == {
        "name": "coverage",
        "status": "failed",
        "reason": "typescript 0.00% < 80",
    }
    assert payload["diff_coverage"] == {
        "typescript": 0.0,
        "uncovered": [
            {"file": "src/missed.ts", "line": 1},
            {"file": "src/missed.ts", "line": 2},
            {"file": "src/missed.ts", "line": 3},
        ],
    }
    assert "`src/missed.ts:2`" in markdown
