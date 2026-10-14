from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from bob_quality.adapters.lizard import LizardParseError, parse_lizard_csv
from bob_quality.config import Config, load_config
from bob_quality.core import below_floor
from bob_quality.coverage_gate import (
    DroppedFile,
    DroppedLine,
    _coverage_drops,
    _drop,
    _line_numbers,
    _load_files,
    _src_stats,
    diff_cover_version,
    run_coverage_gate,
)
from bob_quality.exit_codes import BASELINE_BROKEN, CONFIG_OR_TOOL
from bob_quality.messages import msg, render
import bob_quality.python_probe as python_probe
from bob_quality.python_probe import measure_python
from bob_quality.suite_memo import (
    HoldBroken,
    HoldUnavailable,
    PythonHold,
    SuiteMemo,
    _export_name,
    _write_python_export,
)
from bob_quality.tools import PythonStarted, ToolError
from bob_quality.waivers import Waiver
from helpers import (
    commit_on_branch,
    commit_on_main,
    in_both,
    init_mixed_repo,
    init_python_repo,
    init_ts_repo,
    run_bob,
)

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

    assert outcome.exit_code == CONFIG_OR_TOOL
    assert outcome.versions == {}
    assert outcome.diff_coverage is None
    assert outcome.result.name == "coverage"
    assert outcome.result.status == "not_run"
    assert render(outcome.result.reason, "en") == "missing tool: diff-cover"
    assert not log.exists()
    probed = measure_python(repo, config, {}, None, memo)
    assert probed.exit_code is None
    assert probed.gate is None
    assert probed.baseline == 0
    assert probed.versions == {"lizard": "1.24.1", "coverage.py": "7.16.2"}
    assert any(metric.name == "add" and metric.lang == "python" for metric in probed.metrics)
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
    for raw in ("nope", "[]", '{"src_stats": []}', '{"src_stats": {"a.py": []}}'):
        with pytest.raises(ToolError) as caught:
            _load_files(raw)
        assert in_both(caught.value) == (
            "diff-cover returned an unreadable report",
            "diff-cover devolveu um relatório ilegível",
        )


def test_a_windows_path_and_duplicate_lines_survive_the_parser() -> None:
    raw = json.dumps(
        {
            "src_stats": {
                "dir\\mod.py": {"covered_lines": [1, 1], "violation_lines": [3]},
            }
        }
    )

    files = _load_files(raw)

    assert set(files) == {"dir/mod.py"}
    assert files["dir/mod.py"].covered == frozenset({1})
    assert files["dir/mod.py"].uncovered == frozenset({3})
    assert _load_files("{}") == {}
    assert _src_stats({}) == {}
    assert _src_stats({"src_stats": {"a.py": {"covered_lines": []}}}) == {
        "a.py": {"covered_lines": []}
    }


def test_src_stats_names_the_broken_shape() -> None:
    with pytest.raises(ValueError, match="^diff-cover json$"):
        _src_stats([])
    with pytest.raises(ValueError, match="^src_stats$"):
        _src_stats({"src_stats": []})
    with pytest.raises(ValueError, match="^src_stats$"):
        _src_stats({"src_stats": {1: {}}})
    with pytest.raises(ValueError, match="^src_stats$"):
        _src_stats({"src_stats": {"a.py": []}})


def test_line_numbers_reject_a_boolean_and_a_string() -> None:
    with pytest.raises(ValueError, match="^lines$"):
        _line_numbers([True])
    with pytest.raises(ValueError, match="^lines$"):
        _line_numbers(["4"])
    with pytest.raises(ValueError, match="^lines$"):
        _line_numbers(1)

    assert _line_numbers([4, 4]) == frozenset({4})
    assert _line_numbers([]) == frozenset()


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


class _Memo:
    def __init__(self, hold: object, raw: object = "{}") -> None:
        self.hold = hold
        self.raw = raw
        self.hold_args: tuple[object, ...] | None = None
        self.json_args: tuple[object, ...] | None = None

    def python_hold(self, cwd: Path, include: tuple[str, ...], coverage_file: Path | None) -> object:
        self.hold_args = (cwd, include, coverage_file)
        return self.hold

    def python_json(self, cwd: Path, include: tuple[str, ...], coverage_file: Path | None) -> str:
        self.json_args = (cwd, include, coverage_file)
        if isinstance(self.raw, Exception):
            raise self.raw
        return str(self.raw)


def _probe_config() -> Config:
    return Config(include=("src",), exclude=("tests",))


def test_measure_python_names_a_missing_tool(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def missing(module: str, pattern: str) -> str:
        raise ToolError(module)

    monkeypatch.setattr("bob_quality.python_probe.tool_version", missing)
    probed = measure_python(tmp_path, _probe_config(), {}, None, _Memo(HoldBroken(1)))

    assert probed.exit_code == CONFIG_OR_TOOL
    assert probed.versions == {}
    assert probed.baseline is None
    assert probed.gate is not None
    assert probed.gate.name == "crap"
    assert probed.gate.status == "not_run"
    assert render(probed.gate.reason, "en") == "missing tool: lizard"


def test_measure_python_reports_a_broken_baseline(tmp_path: Path) -> None:
    memo = _Memo(HoldBroken(4))

    probed = measure_python(tmp_path, _probe_config(), {}, None, memo)

    assert memo.hold_args == (tmp_path, ("src",), None)
    assert memo.json_args is None
    assert probed.exit_code == BASELINE_BROKEN
    assert probed.baseline == 4
    assert probed.versions == {"lizard": "1.24.1", "coverage.py": "7.16.2"}
    assert probed.gate is not None
    assert probed.gate.name == "crap"
    assert probed.gate.status == "not_run"
    assert render(probed.gate.reason, "en") == "baseline tests failed before measuring"


def test_measure_python_reports_an_unavailable_hold(tmp_path: Path) -> None:
    reason = msg("tool.missing", tool="coverage")
    memo = _Memo(HoldUnavailable(reason))

    probed = measure_python(tmp_path, _probe_config(), None, tmp_path / "data", memo)

    assert memo.hold_args == (tmp_path, ("src",), tmp_path / "data")
    assert probed.exit_code == CONFIG_OR_TOOL
    assert probed.versions == {"lizard": "1.24.1", "coverage.py": "7.16.2"}
    assert probed.gate is not None
    assert render(probed.gate.reason, "en") == "coverage.py: missing tool: coverage"


def test_measure_python_reports_an_export_failure(tmp_path: Path) -> None:
    started = PythonStarted(0, tmp_path / "coverage.rc")
    memo = _Memo(PythonHold(started), ToolError(msg("coverage.no_xml")))
    coverage = tmp_path / "data"

    probed = measure_python(tmp_path, _probe_config(), {}, coverage, memo)

    assert memo.json_args == (tmp_path, ("src",), coverage)
    assert probed.exit_code == CONFIG_OR_TOOL
    assert probed.versions == {"lizard": "1.24.1", "coverage.py": "7.16.2"}
    assert probed.gate is not None
    assert render(probed.gate.reason, "en") == "coverage.py: coverage.py did not write coverage.xml"


def test_measure_python_reports_a_bad_lizard_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = PythonStarted(0, tmp_path / "coverage.rc")
    raw = json.dumps({"files": {}})
    memo = _Memo(PythonHold(started), raw)

    def bad_lizard(cwd: Path, include: tuple[str, ...], exclude: tuple[str, ...]) -> str:
        assert (cwd, include, exclude) == (tmp_path, ("src",), ("tests",))
        return "short"

    monkeypatch.setattr("bob_quality.python_probe.run_lizard_csv", bad_lizard)
    probed = measure_python(tmp_path, _probe_config(), {}, None, memo)

    assert probed.exit_code == CONFIG_OR_TOOL
    assert probed.versions == {"lizard": "1.24.1", "coverage.py": "7.16.2"}
    assert probed.gate is not None
    assert render(probed.gate.reason, "en").startswith("unexpected CSV row:")
    with pytest.raises(LizardParseError):
        parse_lizard_csv("short")


def test_measure_python_builds_metrics_from_the_hold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    started = PythonStarted(5, tmp_path / "coverage.rc")
    raw = json.dumps(
        {"files": {"src/app/safe.py": {"executed_lines": [1], "missing_lines": []}}}
    )
    memo = _Memo(PythonHold(started), raw)
    csv = "1,2,1,0,1,0,src/app/safe.py,add,add,1,2\n"
    seen: list[tuple[str, str]] = []
    real_version = python_probe.tool_version

    def spy(module: str, pattern: str) -> str:
        seen.append((module, pattern))
        return real_version(module, pattern)

    def lizard(cwd: Path, include: tuple[str, ...], exclude: tuple[str, ...]) -> str:
        assert (cwd, include, exclude) == (tmp_path, ("src",), ("tests",))
        return csv

    monkeypatch.setattr(python_probe, "tool_version", spy)
    monkeypatch.setattr(python_probe, "run_lizard_csv", lizard)
    coverage = tmp_path / "data"
    probed = measure_python(tmp_path, _probe_config(), {"src/app/safe.py": {1}}, coverage, memo)

    assert seen == [
        ("lizard", r"(\d+\.\d+\.\d+)"),
        ("coverage", r"version (\d+\.\d+\.\d+)"),
    ]
    assert memo.hold_args == (tmp_path, ("src",), coverage)
    assert memo.json_args == (tmp_path, ("src",), coverage)
    assert probed.exit_code is None
    assert probed.gate is None
    assert probed.baseline == 5
    assert probed.versions == {"lizard": "1.24.1", "coverage.py": "7.16.2"}
    assert len(probed.metrics) == 1
    metric = probed.metrics[0]
    assert metric.name == "add"
    assert metric.lang == "python"
    assert metric.file == "src/app/safe.py"
    assert metric.cc == 2
    assert metric.changed is True


def test_export_names_are_coverage_json_and_xml() -> None:
    assert _export_name(False) == "coverage.json"
    assert _export_name(True) == "coverage.xml"


def test_write_python_export_forwards_the_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        "bob_quality.suite_memo.export_coverage_xml",
        lambda cwd, started, dest: seen.append(("xml", cwd, started, dest)),
    )
    monkeypatch.setattr(
        "bob_quality.suite_memo.export_coverage_json",
        lambda cwd, started, dest: seen.append(("json", cwd, started, dest)),
    )
    started = PythonStarted(0, tmp_path / "coverage.rc")
    hold = PythonHold(started)
    dest = tmp_path / "out"

    _write_python_export(tmp_path, hold, dest, True)
    _write_python_export(tmp_path, hold, dest, False)

    assert seen == [
        ("xml", tmp_path, started, dest),
        ("json", tmp_path, started, dest),
    ]


def test_a_duplicate_waiver_stops_before_the_suite(tmp_path: Path) -> None:
    bob = tmp_path / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text(
        "waivers:\n"
        "- id: coverage:a.py\n"
        "  reason: one line\n"
        "  author: ada\n"
        "  date: '2026-10-12'\n"
        "- id: coverage:a.py\n"
        "  reason: another line\n"
        "  author: ada\n"
        "  date: '2026-10-12'\n"
    )

    outcome = run_coverage_gate(tmp_path, Config(), "main", None, SuiteMemo(False))

    assert outcome.exit_code == CONFIG_OR_TOOL
    assert outcome.versions == {}
    assert outcome.diff_coverage is None
    assert outcome.result.name == "coverage"
    assert outcome.result.status == "not_run"
    assert "repeats" in render(outcome.result.reason, "en")


def test_a_patch_failure_keeps_the_diff_cover_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(cwd: Path, base: str, dest: Path) -> None:
        raise ToolError(msg("coverage.unreadable"))

    monkeypatch.setattr("bob_quality.coverage_gate._write_patch", boom)
    coverage = tmp_path / "cov.json"

    outcome = run_coverage_gate(tmp_path, Config(), "main", coverage, SuiteMemo(False))

    assert outcome.exit_code == CONFIG_OR_TOOL
    assert outcome.versions == {"diff-cover": "10.6.0"}
    assert outcome.diff_coverage is None
    assert outcome.result.name == "coverage"
    assert outcome.result.status == "not_run"
    assert render(outcome.result.reason, "en") == "diff-cover returned an unreadable report"


def test_coverage_gate_forwards_the_patch_and_the_floor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tempfile

    from bob_quality.coverage_gate import CoverageOutcome

    distributions: list[str] = []
    real_version = importlib.metadata.version

    def spy_version(name: str) -> str:
        distributions.append(name)
        return real_version(name)

    monkeypatch.setattr("bob_quality.coverage_gate.importlib.metadata.version", spy_version)
    from bob_quality.models import DiffCoverage, DiffLine, GateResult, LanguageDiff

    prefixes: list[object] = []
    real_temp = tempfile.TemporaryDirectory

    class _Recording:
        def __init__(self, *args: object, **kwargs: object) -> None:
            prefixes.append(kwargs.get("prefix"))
            self._inner = real_temp()

        def __enter__(self) -> str:
            return self._inner.__enter__()

        def __exit__(self, *exc: object) -> object:
            return self._inner.__exit__(*exc)

    monkeypatch.setattr("bob_quality.coverage_gate.tempfile.TemporaryDirectory", _Recording)
    written: list[tuple[object, ...]] = []

    def write_patch(cwd: Path, base: str, dest: Path) -> None:
        written.append((cwd, base, dest.name))
        dest.write_text("diff\n")

    monkeypatch.setattr("bob_quality.coverage_gate._write_patch", write_patch)
    monkeypatch.setattr("bob_quality.coverage_gate._coverage_drops", lambda waivers: ())
    slots = (LanguageDiff("python", 80.0, (DiffLine("src/app/safe.py", 1),)),)
    collected: list[tuple[object, ...]] = []

    def collect(*args: object) -> tuple[LanguageDiff, ...]:
        collected.append(args)
        return slots

    monkeypatch.setattr("bob_quality.coverage_gate._collect", collect)
    judged = CoverageOutcome(
        GateResult("coverage", "passed"),
        0,
        {},
        DiffCoverage(slots),
    )
    seen_floor: list[tuple[object, float]] = []

    def judge(got: object, floor: float) -> CoverageOutcome:
        seen_floor.append((got, floor))
        return judged

    monkeypatch.setattr("bob_quality.coverage_gate._judge", judge)
    coverage = tmp_path / "cov.json"
    memo = SuiteMemo(False)
    config = Config(coverage_min_percent=80.5)

    outcome = run_coverage_gate(tmp_path, config, "main", coverage, memo)

    assert distributions == ["diff-cover"]
    assert prefixes == ["bob-diff-cover-"]
    assert written == [(tmp_path, "main", "patch.diff")]
    assert collected[0][0] == tmp_path
    assert collected[0][1] is config
    assert collected[0][2] == coverage
    assert collected[0][3] is memo
    assert collected[0][4].name == "patch.diff"
    assert collected[0][5] == ()
    assert seen_floor == [(slots, 80.5)]
    assert outcome.exit_code == 0
    assert outcome.versions == {"diff-cover": diff_cover_version()}
    assert outcome.result is judged.result
    assert outcome.diff_coverage is judged.diff_coverage


def _waiver(identifier: str) -> Waiver:
    return Waiver(identifier, "kept", "ada", "2026-10-12")


def test_floor_tie_passes_and_a_fraction_below_fails() -> None:
    assert below_floor(80.0, 80.0) is False
    assert below_floor(79.99, 80.0) is True
    assert below_floor(80.01, 80.0) is False


def test_coverage_drops_keep_only_the_coverage_prefix() -> None:
    drops = _coverage_drops(
        (
            _waiver("mutate:src/a.py"),
            _waiver("coverage:src/app/safe.py:4"),
            _waiver("coverage:src/missed.py"),
            _waiver("cover:src/nope.py"),
        )
    )

    assert drops == (
        DroppedLine("src/app/safe.py", 4),
        DroppedFile("src/missed.py"),
    )


def test_a_drop_uses_the_last_colon_and_keeps_a_bare_file() -> None:
    assert _drop("src/app/safe.py:12") == DroppedLine("src/app/safe.py", 12)
    assert _drop("src/app/safe.py:4:9") == DroppedLine("src/app/safe.py:4", 9)
    assert _drop("src/app/safe.py") == DroppedFile("src/app/safe.py")
    assert _drop(":5") == DroppedFile(":5")
    assert _drop("src/app/safe.py:line") == DroppedFile("src/app/safe.py:line")
    assert _drop("") == DroppedFile("")
