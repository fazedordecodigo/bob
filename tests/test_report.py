"""Relatório `.bob/` (schema v1 + seções exigidas pela issue #1)."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from bob_quality.models import DiffCoverage, DiffLine, GateResult, LanguageDiff, Report
from bob_quality.models import flatten_uncovered
from bob_quality.report import to_json, to_markdown
from helpers import RISKY_SOURCE, commit_on_branch, init_python_repo, run_bob
from bob_quality.messages import msg
from bob_quality.models import (
    Advisory,
    GateResult,
    MissingPackage,
    Report,
    RowBlock,
    RowWarn,
    RowWaived,
    SecurityReport,
    SupplyReport,
    UndeclaredImport,
    UnverifiedAdvisory,
    UnverifiedExistence,
)
from bob_quality.report import to_json, to_markdown

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
    assert "\n\n## Diff coverage\n\n" in english
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
    assert "| Language | Percent |\n|---|---:|\n| python | 75.00% |" in english
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


def _bare(**extra: object) -> Report:
    gates = extra.pop("gates", [GateResult("supply", "passed", None)])
    return Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-11T00:00:00+00:00",
        tool_versions={},
        gates=gates,
        focus=[],
        top_crap=[],
        reproduce="bob check --gates supply",
        mutation={"no_coverage": {"total": 0, "functions": []}},
        **extra,
    )


_MISSING = MissingPackage("pypi", "no-such-pkg", "pyproject.toml", 14)
_TIMEOUT = UnverifiedExistence("npm", "left-pad", "package.json", 20, "timeout")
_WAIVED = UndeclaredImport("src/app.py", "requests", 3)
_ADVISORY = Advisory("GHSA-1111", "pypi", "left", "HIGH", "pyproject.toml", 14)
_GAP = UnverifiedAdvisory("pypi", "left", "pyproject.toml", 14, "dns", None)
_ROWS = (
    RowBlock(_MISSING),
    RowWarn(_TIMEOUT),
    RowWaived(_WAIVED, "supply:undeclared:src/app.py:requests"),
    RowWaived(_ADVISORY, "supply:osv:GHSA-1111"),
    RowWarn(_GAP),
)


def test_json_omits_supply_when_the_gate_did_not_run() -> None:
    payload = to_json(_bare())
    keys = list(payload)

    assert "supply" not in payload
    assert keys[keys.index("mutation") + 1] == "churn"
    assert keys[keys.index("churn") + 1] == "reproduce"


def test_json_supply_sits_after_mutation_and_matches_the_rows() -> None:
    report = _bare(supply=SupplyReport(("python", "typescript"), (), _ROWS))

    payload = to_json(report)
    keys = list(payload)

    assert keys[keys.index("mutation") + 1] == "supply"
    assert keys[keys.index("supply") + 1] == "churn"
    assert keys[keys.index("churn") + 1] == "reproduce"
    assert payload["supply"] == {
        "measured": ["python", "typescript"],
        "skipped": [],
        "findings": [
            {
                "kind": "missing",
                "index": "pypi",
                "name": "no-such-pkg",
                "file": "pyproject.toml",
                "line": 14,
                "effect": "block",
                "waiver": None,
            },
            {
                "kind": "unverified",
                "question": "existence",
                "index": "npm",
                "name": "left-pad",
                "file": "package.json",
                "line": 20,
                "cause": "timeout",
                "effect": "warn",
                "waiver": None,
            },
            {
                "kind": "undeclared",
                "file": "src/app.py",
                "module": "requests",
                "line": 3,
                "effect": "waived",
                "waiver": "supply:undeclared:src/app.py:requests",
            },
            {
                "kind": "advisory",
                "advisory": "GHSA-1111",
                "index": "pypi",
                "name": "left",
                "severity": "HIGH",
                "file": "pyproject.toml",
                "line": 14,
                "effect": "waived",
                "waiver": "supply:osv:GHSA-1111",
            },
            {
                "kind": "unverified",
                "question": "advisory",
                "advisory": None,
                "index": "pypi",
                "name": "left",
                "file": "pyproject.toml",
                "line": 14,
                "cause": "dns",
                "effect": "warn",
                "waiver": None,
            },
        ],
    }
    Draft202012Validator(SCHEMA).validate(payload)


def test_json_records_no_severity_when_the_fetched_advisory_has_no_band() -> None:
    finding = UnverifiedAdvisory(
        "pypi", "left", "pyproject.toml", 5, "no_severity", "GHSA-0000-0000-0000"
    )
    report = _bare(
        supply=SupplyReport(("python",), (), (RowWarn(finding),)),
        diff_coverage=DiffCoverage((LanguageDiff("python", 80.0, ()),)),
        security=SecurityReport((), ()),
    )

    payload = to_json(report)

    assert payload["diff_coverage"] == {"python": 80.0, "uncovered": []}
    assert payload["security"] == {"findings": [], "unmeasured": []}
    assert payload["supply"]["findings"] == [
        {
            "kind": "unverified",
            "question": "advisory",
            "advisory": "GHSA-0000-0000-0000",
            "index": "pypi",
            "name": "left",
            "file": "pyproject.toml",
            "line": 5,
            "cause": "no_severity",
            "effect": "warn",
            "waiver": None,
        }
    ]
    Draft202012Validator(SCHEMA).validate(payload)
    assert "advisory GHSA-0000-0000-0000, no severity published" in to_markdown(report, "en")
    assert "advisory GHSA-0000-0000-0000, sem severidade publicada" in to_markdown(report, "pt-BR")


def test_markdown_supply_section_follows_mutants_and_translates() -> None:
    report = _bare(supply=SupplyReport(("python", "typescript"), (), _ROWS[:3]))

    english = to_markdown(report, "en")
    portuguese = to_markdown(report, "pt-BR")

    assert english.index("## Mutants without tests") < english.index("## New dependencies")
    assert english.index("## New dependencies") < english.index("## How to reproduce")
    assert portuguese.index("## Mutantes sem teste") < portuguese.index("## Dependências novas")
    assert portuguese.index("## Dependências novas") < portuguese.index("## Como reproduzir")
    assert (
        "## New dependencies\n\n"
        "| Name | Where | What | Effect |\n"
        "|---|---|---|---|\n"
        "| `no-such-pkg` | `pyproject.toml:14` | missing on PyPI | blocks |\n"
        "| `left-pad` | `package.json:20` | registry timeout, left unverified | warns |\n"
        "| `requests` | `src/app.py:3` | undeclared, waived as `supply:undeclared:src/app.py:requests` | waived |\n"
    ) in english
    assert (
        "## Dependências novas\n\n"
        "| Nome | Onde | O quê | Efeito |\n"
        "|---|---|---|---|\n"
        "| `no-such-pkg` | `pyproject.toml:14` | ausente no PyPI | bloqueia |\n"
        "| `left-pad` | `package.json:20` | timeout do registro, ficou não verificado | avisa |\n"
        "| `requests` | `src/app.py:3` | não declarado, dispensado como `supply:undeclared:src/app.py:requests` | dispensado |\n"
    ) in portuguese
    assert "## New dependencies" not in portuguese
    assert "## Dependências novas" not in to_markdown(_bare(), "pt-BR")


def test_markdown_stringifies_a_type_cell_and_escapes_a_pipe() -> None:
    report = _bare(
        gates=[GateResult("typing", "failed", None)],
        typing={
            "findings": [
                {
                    "file": None,
                    "line": 1,
                    "code": "a|b",
                    "disposition": "in_diff",
                    "waiver_id": None,
                }
            ]
        },
    )

    english = to_markdown(report, "en")

    assert "| `None` | 1 | `a\\|b` | in_diff | `None` |" in english


def test_markdown_escapes_a_pipe_in_a_supply_cell() -> None:
    finding = MissingPackage("pypi", "left|pad", "src/a|b.py", 2)
    report = _bare(supply=SupplyReport(("python",), (), (RowBlock(finding),)))

    english = to_markdown(report, "en")

    assert "| `left\\|pad` | `src/a\\|b.py:2` | missing on PyPI | blocks |" in english


def test_markdown_says_when_supply_measured_nothing_and_when_the_diff_is_clean() -> None:
    missed = _bare(
        gates=[GateResult("supply", "not_run", msg("supply.unmeasured"))],
        supply=SupplyReport((), ("python", "typescript"), ()),
    )
    clean = _bare(supply=SupplyReport(("python",), ("typescript",), ()))

    assert "no configured language produced a measurement" in to_markdown(missed, "en")
    assert "nenhuma linguagem configurada produziu medição" in to_markdown(missed, "pt-BR")
    assert "| Name |" not in to_markdown(missed, "en")
    assert to_json(missed)["supply"] == {
        "measured": [],
        "skipped": ["python", "typescript"],
        "findings": [],
    }
    assert "No new dependency in the diff." in to_markdown(clean, "en")
    assert "typescript did not measure." in to_markdown(clean, "en")
    assert "Nenhuma dependência nova no diff." in to_markdown(clean, "pt-BR")
    assert "typescript não mediu." in to_markdown(clean, "pt-BR")
