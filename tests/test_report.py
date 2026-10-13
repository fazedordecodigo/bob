"""Relatório `.bob/` (schema v1 + seções exigidas pela issue #1)."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from bob_quality.models import DiffCoverage, DiffLine, GateResult, LanguageDiff, Report
from bob_quality.models import flatten_uncovered
from bob_quality.report import to_json, to_markdown
from helpers import RISKY_SOURCE, commit_on_branch, init_python_repo, run_bob

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "src/bob_quality/schemas/report_v1.json").read_text()
)


def test_check_report_matches_schema_v1_and_required_sections(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "risky",
        "src/app/risky.py",
        RISKY_SOURCE,
        "add untested messy function",
    )

    result = run_bob(repo, "check", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 1
    Draft202012Validator(SCHEMA).validate(payload)
    assert payload["schema_version"] == 1
    assert payload["top_crap"][0]["name"] == "messy"
    assert payload["top_crap"][0]["crap"] > 10
    assert payload["focus"][0]["file"] == "src/app/risky.py"
    assert "bob check --base main" in payload["reproduce"]
    assert "## Verdict" in markdown
    assert "## Where to focus the review" in markdown
    assert "## Top 5 functions by CRAP" in markdown
    assert "## How to reproduce" in markdown
    assert "src/app/risky.py" in markdown
    assert "diff_coverage" not in payload
    assert "## Diff coverage" not in markdown


def test_crap_command_writes_the_same_report_files(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "risky",
        "src/app/risky.py",
        RISKY_SOURCE,
        "add untested messy function",
    )

    result = run_bob(repo, "crap", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert result.returncode == 1
    Draft202012Validator(SCHEMA).validate(payload)
    assert any(gate["name"] == "crap" for gate in payload["gates"])
    assert "bob crap --base main" in payload["reproduce"]


def _coverage_report(status: str, reason: str | None, coverage: DiffCoverage | None) -> Report:
    return Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-12T00:00:00+00:00",
        tool_versions={"diff-cover": "10.6.0"},
        gates=[GateResult("coverage", status, reason)],
        focus=[],
        top_crap=[],
        reproduce="bob check --gates coverage",
        exit_code=0 if status == "passed" else 1,
        mutation={"no_coverage": {"total": 0, "functions": []}},
        diff_coverage=coverage,
    )


def test_diff_coverage_is_omitted_until_a_language_is_measured() -> None:
    report = _coverage_report("not_run", "baseline tests failed before measuring", None)

    payload = to_json(report)
    english = to_markdown(report, "en")
    portuguese = to_markdown(report, "pt-BR")

    assert "diff_coverage" not in payload
    Draft202012Validator(SCHEMA).validate(payload)
    assert english.index("## Mutants without tests") < english.index("## Diff coverage")
    assert english.index("## Diff coverage") < english.index("## How to reproduce")
    assert "baseline tests failed before measuring" in english
    assert "| Language | Percent |" not in english
    assert portuguese.index("## Mutantes sem teste") < portuguese.index("## Cobertura do diff")
    assert "## Cobertura do diff" in portuguese
    assert "| Linguagem | Percentual |" not in portuguese


def test_diff_coverage_json_lists_measured_percents_and_uncovered_lines() -> None:
    report = _coverage_report(
        "failed",
        "python 75.00% < 80",
        DiffCoverage(
            (
                LanguageDiff("python", 75.0, (DiffLine("src/app/gap.py", 12),)),
                LanguageDiff("typescript", 100.0, ()),
            )
        ),
    )

    payload = to_json(report)
    english = to_markdown(report, "en")

    Draft202012Validator(SCHEMA).validate(payload)
    assert payload["diff_coverage"] == {
        "python": 75.0,
        "typescript": 100.0,
        "uncovered": [{"file": "src/app/gap.py", "line": 12}],
    }
    assert "| python | 75.00% |" in english
    assert "| typescript | 100.00% |" in english
    assert "`src/app/gap.py:12`" in english


def test_uncovered_lines_are_sorted_by_file_then_line() -> None:
    coverage = DiffCoverage(
        (
            LanguageDiff("typescript", 0.0, (DiffLine("b.ts", 2), DiffLine("b.ts", 1))),
            LanguageDiff("python", 50.0, (DiffLine("a.py", 3),)),
        )
    )

    assert flatten_uncovered(coverage) == (
        DiffLine("a.py", 3),
        DiffLine("b.ts", 1),
        DiffLine("b.ts", 2),
    )
