"""Custo fixo do gate: quais subprocessos rodam a suíte, com qual ambiente, e como a falha deles vira exit."""

from __future__ import annotations

import fnmatch
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from bob_quality import mutmut_tool, tools
from bob_quality.adapters.mutmut import mutmut_run_patterns, suite_failed
from bob_quality.exit_codes import pytest_passed
from bob_quality.tools import ToolError, run_coverage

from helpers import (
    FIXTURE_PYTHON,
    commit_on_branch,
    commit_on_main,
    in_both,
    init_python_repo,
    run_bob_subprocess,
)

ADD_AND_SCALE = (FIXTURE_PYTHON / "cases" / "add_and_scale.py").read_text()
ADD_TOUCHED = (FIXTURE_PYTHON / "cases" / "add_touched.py").read_text()
SCALE_TEST_THAT_LOGS = """\
import os
from pathlib import Path

from app.safe import scale


def test_scale() -> None:
    with Path({log!r}).open("a") as runs:
        runs.write(os.environ.get("MUTANT_UNDER_TEST", "unset") + "\\n")
    assert scale(3) == 6
"""

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


NOTHING_MATCHES = (
    '  File "/tmp/venv/lib/python3.12/site-packages/mutmut/__main__.py", line 815,'
    " in collect_source_file_mutation_data\n"
    "AssertionError: Filtered for specific mutants, but nothing matches\n\n"
    "Filter: ('app.safe.x_add__mutmut*',)\n"
)


def _record_runs(
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
    returncode: int,
    stdout: str = "",
    stderr: str = "",
) -> list[tuple[list[str], dict[str, object]]]:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    return calls


def test_the_crap_coverage_run_gets_the_rc_and_keeps_the_dogfood(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "leak")
    monkeypatch.setenv("KEEP_ME", "yes")
    monkeypatch.delenv("BOB_SKIP_MUTMUT_DOGFOOD", raising=False)
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
    assert "BOB_SKIP_MUTMUT_DOGFOOD" not in env
    assert env["BOB_COVERAGE_RC"] == str(rc)
    assert env["KEEP_ME"] == "yes"
    assert not any(key.startswith("PYTEST_") for key in env)
    assert rc.read_text() == (
        "[run]\nparallel = true\n"
        f"data_file = {tmp_path / 'coverage.data'}\n"
        f"source =\n    {(tmp_path / 'src').resolve()}\n"
    )


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

    assert run_coverage(tmp_path, ["src"], json_path, data) is None

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
def test_suite_failed_reads_the_suite_failures_of_mutmut_run(output: str, expected: bool) -> None:
    assert suite_failed(output) is expected


@pytest.mark.parametrize(("code", "passed"), [(0, True), (5, True), (1, False), (4, False)])
def test_pytest_passes_with_tests_green_or_none_collected(code: int, passed: bool) -> None:
    assert pytest_passed(code) is passed


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
def test_a_suite_failure_inside_mutmut_run_points_at_also_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stdout: str, message: str
) -> None:
    _record_runs(monkeypatch, mutmut_tool, 1, stdout=stdout)

    with pytest.raises(ToolError) as caught:
        mutmut_tool.run_mutmut(tmp_path, ["app.safe.x_add__mutmut*"], None)

    assert in_both(caught.value) == (
        "the suite passes in the repository and fails inside mutants/;"
        f" check also_copy and the [mutmut] configuration: {message}",
        "a suíte passa no repositório e falha dentro de mutants/;"
        f" confira also_copy e a configuração [mutmut]: {message}",
    )


def test_no_tests_collected_stays_a_plain_tool_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _record_runs(monkeypatch, mutmut_tool, 1, stdout=NO_TESTS)

    with pytest.raises(ToolError) as caught:
        mutmut_tool.run_mutmut(tmp_path, ["app.safe.x_add__mutmut*"], None)

    assert str(caught.value) == (
        "no tests ran in 0.00s failed to collect stats. runner returned 5"
    )


def test_a_filter_that_matches_no_mutant_is_reported_as_nothing_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _record_runs(monkeypatch, mutmut_tool, 1, stdout="    done\n", stderr=NOTHING_MATCHES)

    with pytest.raises(ToolError) as caught:
        mutmut_tool.run_mutmut(tmp_path, ["app.safe.x_add__mutmut*"], None)

    assert str(caught.value) == "nothing matches"


def _mutants_run(patterns: list[str], mutant_ids: list[str]) -> list[str]:
    """Filtro de mutantes do `mutmut run` 3.8."""
    return [
        key
        for key in mutant_ids
        if key in patterns or any(fnmatch.fnmatch(key, pattern) for pattern in patterns)
    ]


def _clean_run_tests(patterns: list[str], stats: dict[str, set[str]]) -> set[str]:
    """Testes da execução limpa do `mutmut run` 3.8. Padrão sem `*` quebra o mutmut."""
    selected: set[str] = set()
    for pattern in patterns:
        assert "*" in pattern
        for key, tests in stats.items():
            if fnmatch.fnmatch(key, pattern):
                selected |= tests
    return selected


STATS = {
    "bob_quality.crap.x_calculate_crap": {"tests/test_crap.py::test_crap_formula"},
    "bob_quality.crap.x_calculate_crap_delta": {"tests/test_crap.py::test_delta"},
    "bob_quality.cli.x_main": {"tests/test_cli.py::test_main"},
}
def test_the_clean_run_picks_only_the_tests_of_the_function() -> None:
    patterns = mutmut_run_patterns("src/bob_quality/crap.py", "calculate_crap")

    assert patterns == [
        "bob_quality.crap.x_calculate_crap__mutmut*",
        "*bob_quality.crap.x_calculate_crap",
    ]
    assert _clean_run_tests(patterns, STATS) == {"tests/test_crap.py::test_crap_formula"}
    assert _clean_run_tests(patterns[:1], STATS) == set()


def test_the_run_patterns_select_only_the_mutants_of_the_function() -> None:
    own = [
        "bob_quality.crap.x_calculate_crap__mutmut_1",
        "bob_quality.crap.x_calculate_crap__mutmut_12",
    ]
    siblings = [
        "bob_quality.crap.x_calculate_crap_delta__mutmut_1",
        "bob_quality.cli.x_main__mutmut_3",
    ]

    patterns = mutmut_run_patterns("src/bob_quality/crap.py", "calculate_crap")

    assert _mutants_run(patterns, own + siblings) == own


def test_the_run_patterns_of_a_method_select_only_its_mutants_and_tests() -> None:
    own = ["app.box.xǁBoxǁopen__mutmut_1", "app.box.xǁBoxǁopen__mutmut_6"]
    siblings = [
        "app.box.x_open__mutmut_1",
        "app.box.xǁCrateǁopen__mutmut_1",
        "app.box.xǁBoxǁopen_all__mutmut_1",
    ]
    stats = {
        "app.box.xǁBoxǁopen": {"tests/test_box.py::test_box_open"},
        "app.box.x_open": {"tests/test_box.py::test_open"},
        "app.box.xǁCrateǁopen": {"tests/test_box.py::test_crate_open"},
    }

    patterns = mutmut_run_patterns("src/app/box.py", "Box.open")

    assert patterns == ["app.box.xǁBoxǁopen__mutmut*", "*app.box.xǁBoxǁopen"]
    assert _mutants_run(patterns, own + siblings) == own
    assert _clean_run_tests(patterns, stats) == {"tests/test_box.py::test_box_open"}


def test_the_gate_runs_tests_of_other_functions_only_for_the_baseline_and_the_stats(
    tmp_path: Path,
) -> None:
    log = tmp_path / "runs.log"
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/safe.py", ADD_AND_SCALE, "add and scale")
    commit_on_main(
        repo, "tests/test_unrelated.py", SCALE_TEST_THAT_LOGS.format(log=str(log)), "test scale"
    )
    commit_on_branch(repo, "touch-add", "src/app/safe.py", ADD_TOUCHED, "comment inside add")

    result = run_bob_subprocess(repo, "mutate", "--base", "main")

    assert result.returncode == 0
    runs = log.read_text().splitlines()
    assert [mode for mode in runs if mode != "fail"] == ["unset", "stats"]
