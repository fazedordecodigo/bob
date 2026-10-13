import ast
import json
from pathlib import Path

import pytest

import bob_quality.test_smells as smells
from bob_quality import check as check_mod
from bob_quality.check import _Measured, _assemble, run_check
from bob_quality.config import Config
from bob_quality.messages import msg
from bob_quality.waivers import Waiver
from bob_quality.models import (
    Clone,
    DepViolation,
    FunctionMetric,
    GateResult,
    Report,
    TestSmell as SmellRow,
)
from bob_quality.mutate import MutationOutcome
from bob_quality.report import to_json, to_markdown
from helpers import init_python_repo

_FILE = "tests/test_gap.py"


def test_two_module_tests_both_count() -> None:
    source = "def test_one():\n    pass\n\ndef test_two():\n    value = 1\n"

    assert smells.python_smells(source, _FILE, frozenset(range(1, 6))) == (
        SmellRow(_FILE, 1, "empty-test"),
        SmellRow(_FILE, 4, "missing-assert"),
    )


def test_a_test_class_keeps_every_method() -> None:
    source = (
        "class TestGap:\n"
        "    def test_a(self):\n"
        "        pass\n"
        "    def test_b(self):\n"
        "        value = 1\n"
        "class Other:\n"
        "    def test_c(self):\n"
        "        pass\n"
    )

    assert smells.python_smells(source, _FILE, frozenset(range(1, 10))) == (
        SmellRow(_FILE, 2, "empty-test"),
        SmellRow(_FILE, 4, "missing-assert"),
    )


def test_pytestmark_forms_disable_on_each_changed_line() -> None:
    source = (
        "import pytest\n"
        "pytestmark = [pytest.mark.skip, pytest.mark.xfail]\n"
        "pytestmark: object = (pytest.mark.skipif,)\n"
        "pytest.importorskip('missing')\n"
        "def test_one():\n"
        "    pass\n"
    )

    assert smells.python_smells(source, _FILE, frozenset(range(1, 7))) == (
        SmellRow(_FILE, 2, "disabled-test"),
        SmellRow(_FILE, 3, "disabled-test"),
        SmellRow(_FILE, 4, "disabled-test"),
    )


def test_a_set_of_markers_and_a_plain_assignment_add_only_the_marker() -> None:
    source = (
        "import pytest\n"
        "pytestmark = {pytest.mark.skip}\n"
        "pytestmark = 1\n"
        "def test_one():\n"
        "    pass\n"
    )

    assert smells.python_smells(source, _FILE, frozenset(range(1, 6))) == (
        SmellRow(_FILE, 2, "disabled-test"),
    )


def test_a_sleep_after_another_call_in_the_same_statement_counts() -> None:
    source = "import time\ndef test_one():\n    (helper(), time.sleep(1))\n    assert True\n"

    assert smells.python_smells(source, _FILE, frozenset(range(1, 5))) == (
        SmellRow(_FILE, 3, "sleep"),
    )


def test_a_skipped_name_that_is_not_pytestmark_stays_an_empty_test() -> None:
    source = "import pytest\nvalue = pytest.mark.skip\ndef test_one():\n    pass\n"

    assert smells.python_smells(source, _FILE, frozenset(range(1, 5))) == (
        SmellRow(_FILE, 3, "empty-test"),
    )


def test_two_skip_calls_and_two_sleeps_all_count() -> None:
    source = (
        "import time\n"
        "import pytest\n"
        "def test_one():\n"
        "    pytest.skip('a')\n"
        "    pytest.xfail('b')\n"
        "    time.sleep(1)\n"
        "    time.sleep(2)\n"
    )

    assert smells.python_smells(source, _FILE, frozenset(range(1, 9))) == (
        SmellRow(_FILE, 4, "disabled-test"),
        SmellRow(_FILE, 5, "disabled-test"),
        SmellRow(_FILE, 6, "sleep"),
        SmellRow(_FILE, 7, "sleep"),
    )


def test_assertion_name_shapes() -> None:
    underscore = "def test_one():\n    self.assert_equal(1, 1)\n"
    bare = "def test_one():\n    self.assert()\n"
    lower = "def test_one():\n    self.assertfoo(1)\n"
    helper = "def test_one():\n    helper()\n"
    changed = frozenset(range(1, 4))

    assert smells.python_smells(underscore, _FILE, changed) == ()
    assert smells.python_smells(bare, _FILE, changed) == ()
    assert smells.python_smells(lower, _FILE, changed) == (
        SmellRow(_FILE, 1, "missing-assert"),
    )
    assert smells.python_smells(helper, _FILE, changed) == (
        SmellRow(_FILE, 1, "missing-assert"),
    )


def test_ellipsis_and_docstring_are_empty_and_a_number_is_not() -> None:
    source = "def test_a():\n    ...\ndef test_b():\n    'doc'\ndef test_c():\n    1\n"

    assert smells.python_smells(source, _FILE, frozenset(range(1, 8))) == (
        SmellRow(_FILE, 1, "empty-test"),
        SmellRow(_FILE, 3, "empty-test"),
        SmellRow(_FILE, 5, "missing-assert"),
    )


def test_body_line_uses_the_def_when_end_lineno_is_missing() -> None:
    fn = ast.parse("def test_gap():\n    value = 1\n").body[0]
    assert isinstance(fn, ast.FunctionDef)
    fn.end_lineno = None

    assert smells._body_line(fn, frozenset({1, 2})) == 1


def test_unique_keeps_the_first_duplicate_and_the_later_smell() -> None:
    first = SmellRow(_FILE, 1, "sleep")
    duplicate = SmellRow(_FILE, 1, "sleep")
    later = SmellRow(_FILE, 2, "missing-assert")

    assert smells._unique([first, duplicate, later]) == [first, later]


def test_changed_paths_follow_the_language_and_reject_any_other() -> None:
    diff = {
        "tests/test_a.py": {1},
        "tests/conftest.py": {1},
        "src/app.py": {1},
        "src/a.test.ts": {1},
        "src/a.ts": {1},
        "src/__tests__/gap.ts": {1},
        "src/__tests__/types.d.ts": {1},
        "src/__TESTS__/gap.ts": {1},
    }

    assert smells.changed_test_paths(diff, "python") == ("tests/test_a.py",)
    assert smells.changed_test_paths(diff, "typescript") == (
        "src/__tests__/gap.ts",
        "src/a.test.ts",
    )
    with pytest.raises(AssertionError, match="nope"):
        smells.changed_test_paths(diff, "nope")  # type: ignore[arg-type]


def test_measure_python_reads_every_changed_utf8_file(tmp_path: Path) -> None:
    (tmp_path / "test_a.py").write_bytes(b"def test_a():\n    \xff\n")
    (tmp_path / "test_b.py").write_text("def test_b():\n    pass\n", encoding="utf-8")
    (tmp_path / "test_c.py").write_text("def test_c():\n    café = 1\n", encoding="utf-8")

    measured = smells.measure_python(
        tmp_path,
        {"test_a.py": {1, 2}, "test_b.py": {1, 2}, "test_c.py": {1, 2}},
    )

    assert measured == smells.LanguageMeasured(
        "python",
        (
            SmellRow("test_b.py", 1, "empty-test"),
            SmellRow("test_c.py", 1, "missing-assert"),
        ),
    )


def test_the_gate_returns_zero_and_the_warning(tmp_path: Path) -> None:
    (tmp_path / "test_gap.py").write_text("def test_gap():\n    value = 1\n", encoding="utf-8")

    result, findings, code, versions = smells.run_test_smells_gate(
        tmp_path,
        Config(),
        {"test_gap.py": {1, 2}},
    )

    assert code == 0
    assert versions == {}
    assert result == GateResult("test_smells", "warn", msg("test_smells.one", count=1))
    assert findings == (SmellRow("test_gap.py", 1, "missing-assert"),)


def test_collect_outcome_rejects_a_foreign_value() -> None:
    with pytest.raises(AssertionError, match="int"):
        smells._collect_outcome(1, [], [])  # type: ignore[arg-type]


def test_json_and_markdown_name_the_smell_and_escape_a_pipe() -> None:
    smell = SmellRow(_FILE, 1, "missing-assert", "a|b")
    report = _report(test_smells=(smell,), gates=[GateResult("test_smells", "warn", "1")])

    payload = to_json(report)
    markdown = to_markdown(report, "en")

    assert payload["test_smells"] == [
        {"file": _FILE, "line": 1, "rule": "missing-assert", "waiver": "a|b"}
    ]
    assert "## Diff tests" in markdown
    assert "XXXX" not in markdown
    assert "|---|---|" in markdown
    assert "| `tests:tests/test_gap.py:1:missing-assert` | a\\|b |" in markdown


def test_markdown_prints_the_not_run_reason() -> None:
    report = _report(
        test_smells=(),
        gates=[GateResult("test_smells", "not_run", "eslint is not installed")],
    )

    markdown = to_markdown(report, "en")

    assert "eslint is not installed" in markdown
    assert "No smells in the changed tests." not in markdown


def test_assemble_keeps_mutation_fields_and_both_dependency_sides() -> None:
    changed = _metric("changed_fn", True, 4.0)
    old = _metric("old_fn", False, 12.0)
    smell = SmellRow(_FILE, 1, "missing-assert")
    survivor = {
        "id": "s",
        "function": "f",
        "file": "src/extra.py",
        "line": 1,
        "operator": "==",
        "status": "survived",
        "waiver": None,
    }
    waivers = [{"id": "m", "reason": "because", "author": "ada", "date": "2026-10-12"}]
    summary = {"remutated": ["src/app.py::changed_fn"], "reused": [], "no_coverage": {"total": 0}}
    measured = _Measured(
        versions={"mutmut": "3.8.0"},
        gates=[GateResult("mutate", "passed")],
        metrics=[changed, old],
        clones=[
            Clone("src/app.py", 1, 2, "src/other.py", 1, 2, 2, 10, 0.9, "exact"),
        ],
        violations=[
            DepViolation("a", "b", "cycle", True),
            DepViolation("c", "d", "old", False),
        ],
        mutation=MutationOutcome(
            result=GateResult("mutate", "passed"),
            exit_code=0,
            versions={"mutmut": "3.8.0"},
            waivers=waivers,
            survivors=[survivor],
            summary=summary,
        ),
        test_smells=(smell,),
    )

    report = _assemble(measured, "a" * 40, "main", {"src/app.py": {1}}, 10.0, "bob check")

    assert report.schema_version == 1
    assert report.commit == "a" * 40
    assert report.base == "main"
    assert report.generated_at
    assert report.tool_versions == {"mutmut": "3.8.0"}
    assert report.gates == [GateResult("mutate", "passed")]
    assert report.top_crap[0]["name"] == "changed_fn"
    assert report.old_debt[0]["name"] == "old_fn"
    assert report.dependencies[0]["origin"] == "a"
    assert report.old_dependencies[0]["origin"] == "c"
    assert report.reproduce == "bob check"
    assert report.waivers == waivers
    assert report.survivors == [survivor]
    assert report.mutation == summary
    assert report.test_smells == (smell,)
    assert report.clones == measured.clones
    assert report.generated_at.endswith("+00:00")
    assert {"file": "src/extra.py", "risk": 100.0} in report.focus


def test_assemble_uses_idle_waivers_when_mutation_did_not_run() -> None:
    waivers = [{"id": "m", "reason": "because", "author": "ada", "date": "2026-10-12"}]
    measured = _Measured(
        gates=[GateResult("dry", "passed")],
        loaded_waivers=waivers,
    )

    report = _assemble(measured, "a" * 40, "main", {}, 10.0, "bob check")

    assert report.mutation is None
    assert report.waivers == waivers
    assert report.survivors == []
    assert report.test_smells is None
    assert report.top_crap == []
    assert report.old_debt == []


def test_check_without_gates_names_the_defaults(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")

    code = run_check(repo, base="main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert code == 0
    assert payload["exit_code"] == 0
    assert payload["schema_version"] == 1
    assert payload["base"] == "main"
    assert payload["reproduce"] == "bob check"
    assert len(payload["commit"]) == 40
    assert [gate["name"] for gate in payload["gates"]] == ["crap", "dry", "deps"]
    assert "test_smells" not in payload
    assert payload["waivers"] == []
    assert payload["survivors"] == []
    assert payload["mutation"] is None


def test_bad_waivers_after_dry_still_name_the_base(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    bob = repo / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text("waivers: x\n")

    code = run_check(repo, base="main", gates=["dry"])
    payload = json.loads((bob / "report.json").read_text())

    assert code == 4
    assert payload["base"] == "main"
    assert payload["reproduce"] == "bob check"
    assert payload["gates"] == [
        {
            "name": "dry",
            "status": "not_run",
            "reason": ".bob/waivers.yaml: waivers must be a list",
        }
    ]


def test_apply_test_waivers_keeps_every_row_and_only_the_matching_reason() -> None:
    rows = (
        SmellRow("a.py", 1, "sleep"),
        SmellRow("b.py", 2, "empty-test"),
        SmellRow("c.py", 3, "sleep"),
    )
    waivers = [
        Waiver(
            id="tests:a.py:1:sleep",
            reason="the sandbox clock is real",
            author="ada",
            date="2026-10-12",
        ),
        Waiver(
            id="tests:c.py:3:sleep",
            reason="the sandbox clock is real",
            author="ada",
            date="2026-10-12",
        ),
    ]

    applied = smells.apply_test_waivers(rows, waivers)

    assert applied == (
        SmellRow("a.py", 1, "sleep", "the sandbox clock is real"),
        SmellRow("b.py", 2, "empty-test"),
        SmellRow("c.py", 3, "sleep", "the sandbox clock is real"),
    )


def test_outcomes_measure_python_then_skip_typescript(tmp_path: Path) -> None:
    class _Order:
        languages = ("python", "typescript", "python")

    (tmp_path / "test_gap.py").write_text("def test_gap():\n    pass\n", encoding="utf-8")
    measured = smells.LanguageMeasured(
        "python", (SmellRow("test_gap.py", 1, "empty-test"),)
    )

    found = smells._outcomes(_Order(), tmp_path, {"test_gap.py": {1, 2}})  # type: ignore[arg-type]

    assert found == (measured, smells.LanguageSkipped("typescript"), measured)


def test_outcomes_reject_an_unknown_language(tmp_path: Path) -> None:
    class _Lang:
        languages = ("nope",)

    with pytest.raises(AssertionError, match="nope"):
        smells._outcomes(_Lang(), tmp_path, {})  # type: ignore[arg-type]


def test_versions_keep_the_eslint_version_from_either_outcome() -> None:
    detail = msg("dry.node_missing")
    measured = smells.LanguageMeasured("typescript", (), "9.14.0")
    broken = smells.LanguageBroken("typescript", detail, "9.14.0")

    assert smells._versions((measured,)) == {"eslint": "9.14.0"}
    assert smells._versions((broken,)) == {"eslint": "9.14.0"}
    assert smells._versions((smells.LanguageSkipped("typescript"),)) == {}


def test_waive_one_keeps_language_and_version() -> None:
    smell = SmellRow("a.py", 1, "sleep")
    outcome = smells.LanguageMeasured("typescript", (smell,), "9.14.0")
    waivers = [
        Waiver(
            id="tests:a.py:1:sleep",
            reason="the sandbox clock is real",
            author="ada",
            date="2026-10-12",
        )
    ]

    waived = smells._waive_one(outcome, waivers)

    assert waived == smells.LanguageMeasured(
        "typescript",
        (SmellRow("a.py", 1, "sleep", "the sandbox clock is real"),),
        "9.14.0",
    )
    with pytest.raises(AssertionError, match="int"):
        smells._waive_one(1, [])  # type: ignore[arg-type]
    with pytest.raises(AssertionError, match="int"):
        smells._eslint_version(1)  # type: ignore[arg-type]


def test_run_check_forwards_threshold_workers_and_the_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    seen: dict[str, object] = {}
    coverage = tmp_path / "cov.json"

    def fake_open(
        cwd: Path,
        base: str | None,
        config_path: Path | None,
        threshold: float | None,
        command: str,
        gates: list[str],
    ) -> tuple[Config, str, float, str, dict[str, set[int]]]:
        seen["open"] = (threshold, command, tuple(gates))
        return Config(), base or "", 12.5, "c" * 40, {}

    def fake_measure(
        cwd: Path,
        config: Config,
        diff_lines: dict[str, set[int]],
        max_crap: float,
        coverage_file: Path | None,
        gates: list[str],
        out_dir: Path,
        max_workers: int | None,
    ) -> check_mod._Measured:
        seen["measure"] = (max_crap, coverage_file, max_workers)
        return check_mod._Measured()

    monkeypatch.setattr(check_mod, "_open", fake_open)
    monkeypatch.setattr(check_mod, "_measure", fake_measure)

    code = run_check(
        repo,
        base="main",
        threshold=12.5,
        coverage_file=coverage,
        max_workers=3,
        reproduce="bob check --gates crap",
    )

    assert code == 0
    assert seen["open"] == (12.5, "bob check --gates crap", ("crap", "dry", "deps"))
    assert seen["measure"] == (12.5, coverage, 3)


def test_a_missing_base_keeps_the_reproduce_command(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")

    code = run_check(repo, base="no-such-ref", reproduce="bob check --gates crap")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert code == 4
    assert payload["reproduce"] == "bob check --gates crap"
    assert payload["base"] == "no-such-ref"


def _metric(name: str, changed: bool, crap: float) -> FunctionMetric:
    return FunctionMetric("python", "app", name, "src/app.py", 1, 4, 2, 1.0, crap, changed)


def _report(
    *,
    test_smells: tuple[SmellRow, ...] | None,
    gates: list[GateResult],
) -> Report:
    return Report(
        schema_version=1,
        commit="a" * 40,
        base="main",
        generated_at="2026-10-13T00:00:00+00:00",
        tool_versions={},
        gates=gates,
        focus=[],
        top_crap=[],
        reproduce="bob check",
        test_smells=test_smells,
    )
