"""Custo fixo do gate: quais subprocessos rodam a suíte, e com qual ambiente."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

import bob_quality.mutate as mutate_module
from bob_quality import mutmut_tool, tools
from bob_quality.adapters.mutmut import baseline_failed
from bob_quality.models import CyclomaticFunction, GateResult
from bob_quality.mutate import _run_and_parse
from bob_quality.mutmut_tool import BaselineFailed
from bob_quality.tools import ToolError, run_coverage

# Trechos literais da saída de `mutmut run` 3.8, como o subprocess em modo texto devolve.
STATS_FAILED = (
    "    done in 25ms (2 files mutated, 0 ignored, 0 unmodified)\n\n"
    "⠧ Running stats     \n⠇ Running stats\n⠏ Running stats\n\n"
    "=========================== short test summary info ============================\n"
    "FAILED tests/test_safe.py::test_add - assert 3 == 0\n"
    "!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
    "1 failed in 0.01s\n"
    "failed to collect stats. runner returned 1\n\n"
)
CLEAN_FAILED = (
    "⠹ Running stats\n    done\n\n"
    "⠸ Running clean tests\n⠼ Running clean tests\n⠴ Running clean tests\n\n"
    "FAILED tests/test_safe.py::test_add - AssertionError: assert '' == 'stats'\n"
    "1 failed in 0.00s\n"
    "Failed to run clean test\n\n"
)
NO_TESTS = (
    "⠧ Running stats     \n⠇ Running stats\n\n"
    "no tests ran in 0.00s\n"
    "failed to collect stats. runner returned 5\n\n"
)


def _record_runs(
    monkeypatch: pytest.MonkeyPatch, module: ModuleType, returncode: int, stdout: str = ""
) -> list[tuple[list[str], dict[str, object]]]:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    return calls


def test_the_crap_coverage_run_skips_the_mutmut_dogfood(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "leak")
    monkeypatch.setenv("KEEP_ME", "yes")
    monkeypatch.setenv("BOB_SKIP_MUTMUT_DOGFOOD", "stale")
    calls = _record_runs(monkeypatch, tools, 1)
    rc = tmp_path / "coverage.rc"

    assert run_coverage(tmp_path, ["src"], tmp_path / "coverage.json", None) == 1

    [(args, kwargs)] = calls
    assert args == [sys.executable, "-m", "coverage", "run", "--rcfile", str(rc), "-m", "pytest"]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["stdin"] is subprocess.DEVNULL
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert env["BOB_SKIP_MUTMUT_DOGFOOD"] == "1"
    assert env["BOB_COVERAGE_RC"] == str(rc)
    assert env["KEEP_ME"] == "yes"
    assert not any(key.startswith("PYTEST_") for key in env)


@pytest.mark.parametrize("code", [0, 5])
def test_a_coverage_run_that_measured_exports_the_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    calls = _record_runs(monkeypatch, tools, code)
    json_path = tmp_path / "coverage.json"
    rc = str(tmp_path / "coverage.rc")

    assert run_coverage(tmp_path, ["src"], json_path, None) == code

    assert [(args, kwargs["cwd"]) for args, kwargs in calls[1:]] == [
        ([sys.executable, "-m", "coverage", "combine", "--rcfile", rc], tmp_path),
        (
            [sys.executable, "-m", "coverage", "json", "--rcfile", rc, "-o", str(json_path)],
            tmp_path,
        ),
    ]


def test_an_existing_coverage_file_is_only_exported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _record_runs(monkeypatch, tools, 0)
    data = tmp_path / ".coverage"
    json_path = tmp_path / "coverage.json"

    assert run_coverage(tmp_path, ["src"], json_path, data) == 0

    [(args, kwargs)] = calls
    assert args == [sys.executable, "-m", "coverage", "json", "-o", str(json_path)]
    assert kwargs["cwd"] == tmp_path
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert env["COVERAGE_FILE"] == str(data)


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (STATS_FAILED, True),
        (STATS_FAILED.replace("returned 1", "returned 2"), True),
        (CLEAN_FAILED, True),
        (NO_TESTS, False),
        ("failed to collect stats, no active tests found\n", False),
        ("FAILED: Unable to force test failures\n", False),
        ("AssertionError: Filtered for specific mutants, but nothing matches\n", False),
    ],
)
def test_baseline_failed_reads_the_suite_failures_of_mutmut_run(
    output: str, expected: bool
) -> None:
    assert baseline_failed(output) is expected


def test_mutmut_run_gets_the_patterns_and_a_clean_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # MUTANT_UNDER_TEST fica como o mutmut deixou. Sobrescrever aqui impede
    # o trampolim de associar este teste à função, e o mutante sobrevive.
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "leak")
    monkeypatch.setenv("KEEP_ME", "yes")
    monkeypatch.setenv("BOB_SKIP_MUTMUT_DOGFOOD", "stale")
    calls = _record_runs(monkeypatch, mutmut_tool, 0)

    mutmut_tool.run_mutmut(tmp_path, ["app.safe.x_add__mutmut*"], 2)

    [(args, kwargs)] = calls
    assert args == [
        sys.executable,
        "-m",
        "mutmut",
        "run",
        "app.safe.x_add__mutmut*",
        "--max-children",
        "2",
    ]
    env = kwargs.pop("env")
    assert kwargs == {
        "cwd": tmp_path,
        "capture_output": True,
        "text": True,
        "stdin": subprocess.DEVNULL,
        "timeout": 1800,
        "check": False,
    }
    assert isinstance(env, dict)
    assert env["KEEP_ME"] == "yes"
    assert env["BOB_SKIP_MUTMUT_DOGFOOD"] == "1"
    assert "MUTANT_UNDER_TEST" not in env
    assert not any(key.startswith("PYTEST_") for key in env)


def test_other_mutmut_commands_keep_the_short_timeout_and_return_the_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _record_runs(monkeypatch, mutmut_tool, 0, stdout="    app.safe.x_add__mutmut_1: killed\n")

    assert mutmut_tool.mutmut_results(tmp_path) == "    app.safe.x_add__mutmut_1: killed\n"
    [(_args, kwargs)] = calls
    assert kwargs["timeout"] == 180


@pytest.mark.parametrize(
    ("stdout", "message"),
    [
        (
            STATS_FAILED,
            "done in 25ms (2 files mutated, 0 ignored, 0 unmodified)"
            " =========================== short test summary info ============================"
            " FAILED tests/test_safe.py::test_add - assert 3 == 0"
            " !!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!"
            " 1 failed in 0.01s"
            " failed to collect stats. runner returned 1",
        ),
        (
            CLEAN_FAILED,
            "done FAILED tests/test_safe.py::test_add - AssertionError: assert '' == 'stats'"
            " 1 failed in 0.00s Failed to run clean test",
        ),
    ],
)
def test_a_suite_failure_inside_mutmut_run_is_a_broken_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stdout: str, message: str
) -> None:
    _record_runs(monkeypatch, mutmut_tool, 1, stdout=stdout)

    with pytest.raises(BaselineFailed) as caught:
        mutmut_tool.run_mutmut(tmp_path, ["app.safe.x_add__mutmut*"], None)

    assert str(caught.value) == message


def test_no_tests_collected_stays_a_tool_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _record_runs(monkeypatch, mutmut_tool, 1, stdout=NO_TESTS)

    with pytest.raises(ToolError) as caught:
        mutmut_tool.run_mutmut(tmp_path, ["app.safe.x_add__mutmut*"], None)

    assert type(caught.value) is ToolError
    assert str(caught.value) == (
        "no tests ran in 0.00s failed to collect stats. runner returned 5"
    )


def test_a_broken_baseline_stops_the_gate_with_exit_2_and_keeps_the_waivers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(_cwd: Path, _patterns: list[str], _max_workers: int | None) -> None:
        raise BaselineFailed("Failed to run clean test")

    monkeypatch.setattr(mutate_module, "run_mutmut", broken)
    versions = {"mutmut": "3.8.0"}
    waivers = [{"id": "keep-me", "reason": "porque"}]
    remutate = [
        CyclomaticFunction(file="src/app/safe.py", name="add", start_line=1, end_line=2, cc=1)
    ]

    parsed, failed = _run_and_parse(tmp_path, remutate, 2, versions, waivers)

    assert parsed == []
    assert failed is not None
    assert failed.result == GateResult(
        "mutate", "not_run", "testes da baseline falharam antes de medir"
    )
    assert failed.exit_code == 2
    assert failed.versions == versions
    assert failed.waivers == waivers
