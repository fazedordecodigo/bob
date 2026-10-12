"""Gate test_smells: aviso no diff, exit 0."""

import json
from pathlib import Path

import bob_quality.models as models
import bob_quality.test_smells as smells
from bob_quality.check import run_check
from bob_quality.messages import msg
from helpers import SAFE_CHANGE, commit_on_branch, init_python_repo, init_ts_repo, run_bob

MISSING = models.TestSmell("tests/test_gap.py", 1, "missing-assert", None)
SLEEP = models.TestSmell("tests/test_gap.py", 4, "sleep", None)


def test_fold_warns_for_one_unwaived_smell() -> None:
    result, rows = smells.fold_outcomes((smells.LanguageMeasured("python", (MISSING,)),))

    assert result == models.GateResult("test_smells", "warn", msg("test_smells.one", count=1))
    assert rows == (models.TestSmell("tests/test_gap.py", 1, "missing-assert", None),)


def test_fold_keeps_a_waived_smell_and_passes() -> None:
    waived = models.TestSmell("tests/test_gap.py", 4, "sleep", "the sandbox clock is real")

    result, rows = smells.fold_outcomes((smells.LanguageMeasured("python", (waived,)),))

    assert result == models.GateResult("test_smells", "passed", None)
    assert rows == (models.TestSmell("tests/test_gap.py", 4, "sleep", "the sandbox clock is real"),)


def test_fold_sorts_rows_and_counts_every_unwaived_smell() -> None:
    result, rows = smells.fold_outcomes(
        (
            smells.LanguageMeasured("python", (SLEEP, MISSING)),
            smells.LanguageSkipped("typescript"),
        )
    )

    assert result == models.GateResult("test_smells", "warn", msg("test_smells.many", count=2))
    assert rows == (
        models.TestSmell("tests/test_gap.py", 1, "missing-assert", None),
        models.TestSmell("tests/test_gap.py", 4, "sleep", None),
    )


def test_fold_ignores_a_skip_when_python_measured_nothing() -> None:
    result, rows = smells.fold_outcomes(
        (smells.LanguageMeasured("python", ()), smells.LanguageSkipped("typescript"))
    )

    assert result == models.GateResult("test_smells", "passed", None)
    assert rows == ()


def test_fold_reports_nothing_measured_when_every_language_is_skipped() -> None:
    result, rows = smells.fold_outcomes((smells.LanguageSkipped("typescript"),))

    assert result == models.GateResult(
        "test_smells", "not_run", msg("test_smells.nothing_measured")
    )
    assert rows == ()


def test_fold_uses_a_broken_detail_when_nothing_was_measured() -> None:
    detail = msg("dry.node_missing")

    result, rows = smells.fold_outcomes((smells.LanguageBroken("typescript", detail),))

    assert result == models.GateResult("test_smells", "not_run", detail)
    assert rows == ()


def test_fold_joins_every_broken_detail() -> None:
    left = msg("dry.node_missing")
    right = msg("dry.deps_missing")

    result, rows = smells.fold_outcomes(
        (smells.LanguageBroken("typescript", left), smells.LanguageBroken("typescript", right))
    )

    assert result == models.GateResult(
        "test_smells", "not_run", msg("probe.joined", first=left, second=right)
    )
    assert rows == ()


def test_fold_keeps_the_measured_status_when_a_sibling_breaks() -> None:
    detail = msg("dry.node_missing")

    warned, warned_rows = smells.fold_outcomes(
        (smells.LanguageMeasured("python", (MISSING,)), smells.LanguageBroken("typescript", detail))
    )
    passed, passed_rows = smells.fold_outcomes(
        (smells.LanguageMeasured("python", ()), smells.LanguageBroken("typescript", detail))
    )

    assert warned == models.GateResult(
        "test_smells",
        "warn",
        msg("test_smells.with_detail", head=msg("test_smells.one", count=1), detail=detail),
    )
    assert warned_rows == (models.TestSmell("tests/test_gap.py", 1, "missing-assert", None),)
    assert passed == models.GateResult("test_smells", "passed", detail)
    assert passed_rows == ()


def test_smell_row_exists_only_on_a_changed_line() -> None:
    assert smells.test_smell("tests/test_gap.py", 9, "sleep", frozenset({4})) is None
    assert smells.test_smell("tests/test_gap.py", 4, "sleep", frozenset({4})) == models.TestSmell(
        "tests/test_gap.py", 4, "sleep", None
    )


def test_python_without_a_changed_test_passes(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "touch", "src/app/safe.py", SAFE_CHANGE, "touch tested add")

    result = run_bob(repo, "check", "--base", "main", "--gates", "test_smells")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    gate = payload["gates"][0]

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert payload["schema_version"] == 1
    assert payload["exit_code"] == 0
    assert gate == {"name": "test_smells", "status": "passed", "reason": None}


def test_typescript_without_python_is_not_run(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")

    result = run_bob(repo, "check", "--base", "main", "--gates", "test_smells")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert result.returncode == 0, result.stderr
    assert payload["exit_code"] == 0
    assert payload["schema_version"] == 1
    assert payload["gates"] == [
        {
            "name": "test_smells",
            "status": "not_run",
            "reason": "no language measured test smells",
        }
    ]


def test_a_bad_waiver_file_is_not_a_smell_verdict(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    bob = repo / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text("waivers: x\n")

    code = run_check(repo, base="main", gates=["test_smells"])
    payload = json.loads((bob / "report.json").read_text())

    assert code == 4
    assert payload["exit_code"] == 4
    assert payload["gates"] == [
        {
            "name": "test_smells",
            "status": "not_run",
            "reason": ".bob/waivers.yaml: waivers must be a list",
        }
    ]


def test_cli_rejects_a_bad_waiver_before_writing_a_report(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    bob = repo / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text("waivers: x\n")

    result = run_bob(repo, "check", "--base", "main", "--gates", "test_smells")

    assert result.returncode == 4
    assert result.stderr == ".bob/waivers.yaml: waivers must be a list\n"
    assert result.stdout == ""
    assert not (bob / "report.json").exists()
    assert not (bob / "report.md").exists()
