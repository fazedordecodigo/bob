"""Baseline: a suíte do repositório passa antes de o CRAP ou a mutação medirem.

Seam: CLI `bob check` sobre o fixture Python. Exit code, gate no `report.json`
e o diretório `.bob/mutmut/mutants/`.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from helpers import (
    FIXTURE_PYTHON,
    commit_on_branch,
    commit_on_main,
    init_python_repo,
    run_bob_subprocess,
)

ADD_TOUCHED = (FIXTURE_PYTHON / "cases" / "add_touched.py").read_text()
ADD_COMMENT = "def add(left: int, right: int) -> int:\n    return left + right  # soma\n"
BROKEN_TEST = "from app.safe import add\n\n\ndef test_add() -> None:\n    assert add(1, 2) == 0\n"
UNKNOWN_FLAG_INI = "[pytest]\ntestpaths = tests\npythonpath = src\naddopts = --no-such-flag\n"
TEST_READING_THE_ROOT = """\
from pathlib import Path

from app.safe import add

EXPECTED = Path(__file__).resolve().parents[1] / "expected.txt"


def test_add() -> None:
    assert add(1, 2) == int(EXPECTED.read_text())
"""
RUN_LOGGER = """\
from pathlib import Path


def test_logs_the_run() -> None:
    where = "mutants" if "mutants" in Path(__file__).parts else "repo"
    with Path({log!r}).open("a") as runs:
        runs.write(where + "\\n")
"""
BROKEN = "baseline tests failed before measuring"


def _touched(repo_dir: Path) -> Path:
    repo = init_python_repo(repo_dir)
    commit_on_branch(repo, "touch", "src/app/safe.py", ADD_TOUCHED, "touch add")
    return repo


def _check(repo: Path, gates: str) -> tuple[subprocess.CompletedProcess[str], dict[str, dict]]:
    result = run_bob_subprocess(repo, "check", "--base", "main", "--gates", gates)
    report = json.loads((repo / ".bob" / "report.json").read_text())
    return result, {gate["name"]: gate for gate in report["gates"]}


@pytest.mark.parametrize("gates", ["mutate", "crap,mutate"])
def test_a_broken_baseline_stops_the_mutation_before_mutants_exists(
    tmp_path: Path, gates: str
) -> None:
    repo = _touched(tmp_path / "repo")
    commit_on_branch(repo, "touch", "tests/test_safe.py", BROKEN_TEST, "break the suite")

    result, gate = _check(repo, gates)

    assert result.returncode == 2
    assert gate["mutate"] == {"name": "mutate", "status": "not_run", "reason": BROKEN}
    assert not (repo / ".bob" / "mutmut").exists()


@pytest.mark.parametrize("gates", ["crap", "mutate"])
def test_a_pytest_usage_error_is_a_broken_baseline_in_both_gates(
    tmp_path: Path, gates: str
) -> None:
    repo = _touched(tmp_path / "repo")
    commit_on_branch(repo, "touch", "pytest.ini", UNKNOWN_FLAG_INI, "unknown pytest flag")

    result, gate = _check(repo, gates)
    reports = [(repo / ".bob" / name).read_text() for name in ("report.md", "report.json")]

    assert result.returncode == 2
    assert gate[gates] == {"name": gates, "status": "not_run", "reason": BROKEN}
    assert [text for text in [result.stdout, result.stderr, *reports] if "Traceback" in text] == []


def test_a_suite_that_fails_only_inside_mutants_points_at_also_copy(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "expected.txt", "3\n", "expected sum at the root")
    commit_on_main(repo, "tests/test_safe.py", TEST_READING_THE_ROOT, "read the root")
    commit_on_branch(repo, "touch", "src/app/safe.py", ADD_TOUCHED, "touch add")

    result, gate = _check(repo, "mutate")

    missing = repo.resolve() / ".bob" / "mutmut" / "mutants" / "expected.txt"
    assert result.returncode == 4
    assert gate["mutate"] == {
        "name": "mutate",
        "status": "not_run",
        "reason": "the suite passes in the repository and fails inside mutants/; check also_copy"
        " and the [mutmut] configuration: FileNotFoundError: [Errno 2] No such file or directory:"
        f" '{missing}'",
    }


def test_check_takes_the_mutation_baseline_from_the_crap_pytest(tmp_path: Path) -> None:
    repo_runs: dict[str, int] = {}
    codes: dict[str, int] = {}
    for gates in ("mutate", "crap,mutate"):
        log = tmp_path / f"{gates}.log"
        repo = init_python_repo(tmp_path / gates.replace(",", "-"))
        commit_on_main(repo, "tests/test_runs.py", RUN_LOGGER.format(log=str(log)), "log runs")
        commit_on_branch(repo, "touch", "src/app/safe.py", ADD_COMMENT, "touch add")

        codes[gates] = _check(repo, gates)[0].returncode
        repo_runs[gates] = log.read_text().splitlines().count("repo")

    assert codes == {"mutate": 0, "crap,mutate": 0}
    assert repo_runs == {"mutate": 1, "crap,mutate": 1}

