"""Gate test_smells: aviso no diff, exit 0."""

import json
from pathlib import Path

import bob_quality.models as models
import bob_quality.test_smells as smells
from bob_quality.check import run_check
from bob_quality.messages import msg
from bob_quality.waivers import Waiver, apply_waivers
from helpers import (
    SAFE_CHANGE,
    commit_on_branch,
    commit_on_main,
    init_python_repo,
    init_ts_repo,
    run_bob,
)

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


def test_an_empty_body_is_only_empty_test() -> None:
    source = "def test_gap():\n    pass\n"

    assert smells.python_smells(source, "tests/test_gap.py", frozenset({1, 2})) == (
        models.TestSmell("tests/test_gap.py", 1, "empty-test", None),
    )


def test_a_body_without_an_assertion_is_only_missing_assert() -> None:
    source = "def test_gap():\n    value = 1\n"

    assert smells.python_smells(source, "tests/test_gap.py", frozenset({1, 2})) == (
        models.TestSmell("tests/test_gap.py", 1, "missing-assert", None),
    )


def test_assertion_names_count_and_a_helper_does_not() -> None:
    helper = "def test_gap():\n    assertion_helper()\n"
    equal = "def test_gap():\n    self.assertEqual(1, 1)\n"
    raises = (
        "import pytest\n\n"
        "def test_gap():\n"
        "    with pytest.raises(ValueError):\n"
        "        raise ValueError('no')\n"
    )
    nested = "def test_gap():\n    def inner():\n        assert 1\n"
    changed = frozenset(range(1, 8))

    assert smells.python_smells(helper, "tests/test_gap.py", changed) == (
        models.TestSmell("tests/test_gap.py", 1, "missing-assert", None),
    )
    assert smells.python_smells(equal, "tests/test_gap.py", changed) == ()
    assert smells.python_smells(raises, "tests/test_gap.py", changed) == ()
    assert smells.python_smells(nested, "tests/test_gap.py", changed) == (
        models.TestSmell("tests/test_gap.py", 1, "missing-assert", None),
    )


def test_a_changed_skip_disables_the_test_without_a_body_smell() -> None:
    source = "import pytest\n\n@pytest.mark.skip\ndef test_gap():\n    pass\n"

    assert smells.python_smells(source, "tests/test_gap.py", frozenset({1, 2, 3, 4, 5})) == (
        models.TestSmell("tests/test_gap.py", 3, "disabled-test", None),
    )


def test_an_unchanged_skip_emits_nothing() -> None:
    source = "import pytest\n\n@pytest.mark.skip\ndef test_gap():\n    pass\n"

    assert smells.python_smells(source, "tests/test_gap.py", frozenset({5})) == ()


def test_sleep_inside_the_test_is_kept_and_a_helper_outside_is_not() -> None:
    source = (
        "import time\n\n"
        "def helper():\n"
        "    time.sleep(1)\n\n"
        "def test_gap():\n"
        "    time.sleep(1)\n"
        "    sleeping()\n"
        "    assert True\n"
    )

    assert smells.python_smells(source, "tests/test_gap.py", frozenset(range(1, 12))) == (
        models.TestSmell("tests/test_gap.py", 7, "sleep", None),
    )


def test_body_line_prefers_the_def_when_that_line_changed() -> None:
    source = "@pytest.mark.parametrize('n', [1])\ndef test_gap(n):\n    value = n\n"

    assert smells.python_smells(source, "tests/test_gap.py", frozenset({1, 2, 3})) == (
        models.TestSmell("tests/test_gap.py", 2, "missing-assert", None),
    )
    assert smells.python_smells(source, "tests/test_gap.py", frozenset({3})) == (
        models.TestSmell("tests/test_gap.py", 3, "missing-assert", None),
    )


def test_a_syntax_error_adds_no_row() -> None:
    assert smells.python_smells("def test_gap(:\n", "tests/test_gap.py", frozenset({1})) == ()


def test_a_non_utf8_test_file_adds_no_row(tmp_path: Path) -> None:
    (tmp_path / "test_gap.py").write_bytes(b"def test_gap():\n    \xff\n")

    assert smells.measure_python(tmp_path, {"test_gap.py": {1, 2}}) == smells.LanguageMeasured(
        "python", ()
    )


def test_a_tests_waiver_does_not_waive_a_mutant_with_another_id() -> None:
    mutant = models.Mutant(
        id="app.mod.fn__mutmut_1",
        function="fn",
        file="src/app/mod.py",
        line=3,
        operator="==",
        status="survived",
    )
    waiver = Waiver(
        id="tests:tests/test_gap.py:1:missing-assert",
        reason="the sandbox clock is real",
        author="ada",
        date="2026-10-12",
    )

    applied = apply_waivers([mutant], [waiver])

    assert applied == [
        models.Mutant(
            id="app.mod.fn__mutmut_1",
            function="fn",
            file="src/app/mod.py",
            line=3,
            operator="==",
            status="survived",
            waiver=None,
        )
    ]


def test_a_tests_waiver_waives_a_mutant_only_when_the_id_is_that_string() -> None:
    mutant = models.Mutant(
        id="tests:tests/test_gap.py:1:missing-assert",
        function="fn",
        file="src/app/mod.py",
        line=3,
        operator="==",
        status="survived",
    )
    waiver = Waiver(
        id="tests:tests/test_gap.py:1:missing-assert",
        reason="the sandbox clock is real",
        author="ada",
        date="2026-10-12",
    )

    applied = apply_waivers([mutant], [waiver])

    assert applied[0].waiver == "the sandbox clock is real"


def test_a_python_test_without_an_assert_warns_and_exits_0(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "gap",
        "tests/test_gap.py",
        "def test_gap():\n    value = 1\n",
        "add a test with no assert",
    )

    result = run_bob(repo, "check", "--base", "main", "--gates", "test_smells")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert result.returncode == 0, result.stderr
    assert payload["exit_code"] == 0
    assert payload["schema_version"] == 1
    assert payload["gates"] == [
        {
            "name": "test_smells",
            "status": "warn",
            "reason": "1 test smell in the diff",
        }
    ]


def test_a_python_test_with_an_assert_passes(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "ok",
        "tests/test_gap.py",
        "def test_gap():\n    assert 1 == 1\n",
        "add a test with an assert",
    )

    result = run_bob(repo, "check", "--base", "main", "--gates", "test_smells")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert result.returncode == 0, result.stderr
    assert payload["exit_code"] == 0
    assert payload["gates"] == [
        {"name": "test_smells", "status": "passed", "reason": None}
    ]


def test_a_waiver_keeps_the_smell_from_warning(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "gap",
        "tests/test_gap.py",
        "def test_gap():\n    value = 1\n",
        "add a test with no assert",
    )
    bob = repo / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text(
        "waivers:\n"
        "  - id: tests:tests/test_gap.py:1:missing-assert\n"
        "    reason: the sandbox clock is real\n"
        "    author: ada\n"
        "    date: '2026-10-12'\n"
    )

    result = run_bob(repo, "check", "--base", "main", "--gates", "test_smells")
    payload = json.loads((bob / "report.json").read_text())

    assert result.returncode == 0, result.stderr
    assert payload["exit_code"] == 0
    assert payload["gates"] == [
        {"name": "test_smells", "status": "passed", "reason": None}
    ]


def test_an_old_skip_on_an_unchanged_line_does_not_warn(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    original = "import pytest\n\n@pytest.mark.skip\ndef test_gap():\n    pass\n"
    edited = "import pytest\n\n@pytest.mark.skip\ndef test_gap():\n    pass  # edited\n"
    commit_on_main(repo, "tests/test_gap.py", original, "add a skipped test")
    commit_on_branch(repo, "edit", "tests/test_gap.py", edited, "edit the skipped body")

    result = run_bob(repo, "check", "--base", "main", "--gates", "test_smells")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert result.returncode == 0, result.stderr
    assert payload["gates"] == [
        {"name": "test_smells", "status": "passed", "reason": None}
    ]


def test_conftest_is_not_a_test_file(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "conf",
        "tests/conftest.py",
        "def test_gap():\n    pass\n",
        "add an empty conftest test",
    )

    result = run_bob(repo, "check", "--base", "main", "--gates", "test_smells")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert result.returncode == 0, result.stderr
    assert payload["gates"] == [
        {"name": "test_smells", "status": "passed", "reason": None}
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
