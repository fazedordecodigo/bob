"""Markdown do gate supply. Cada linha distingue o mutante que a troca."""

from bob_quality.messages import msg
from bob_quality.models import (
    Advisory,
    GateResult,
    MissingPackage,
    Report,
    RowBlock,
    RowWarn,
    RowWaived,
    SupplyReport,
    UndeclaredImport,
    UnverifiedAdvisory,
)
from bob_quality.report import supply_lines, to_markdown


def _report(**extra: object) -> Report:
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
        **extra,
    )


def test_supply_heading_starts_on_a_blank_line() -> None:
    report = _report(supply=SupplyReport(("python",), (), ()))
    lines = supply_lines(report)

    assert lines[0] == ""
    assert lines[1] == msg("report.supply")


def test_markdown_renders_each_supply_row_literally() -> None:
    supply = SupplyReport(
        ("python",),
        (),
        (
            RowWaived(MissingPackage("pypi", "no|such", "pyproject.toml", 14), "supply:missing:pypi:no|such"),
            RowBlock(UndeclaredImport("src/app.py", "requests", 3)),
            RowBlock(Advisory("GHSA-1111", "npm", "left-pad", "HIGH", "package.json", 8)),
            RowWaived(
                Advisory("GHSA-2222", "pypi", "flask", "CRITICAL", "pyproject.toml", 4),
                "supply:osv:GHSA-2222",
            ),
            RowWarn(UnverifiedAdvisory("npm", "left-pad", "package.json", 9, "dns", "GHSA-9")),
        ),
    )

    english = to_markdown(_report(supply=supply), "en")

    assert (
        "| `no\\|such` | `pyproject.toml:14` | missing on PyPI, waived as "
        "`supply:missing:pypi:no|such` | waived |"
    ) in english
    assert "| `requests` | `src/app.py:3` | undeclared import | blocks |" in english
    assert "| `left-pad` | `package.json:8` | HIGH advisory GHSA-1111 | blocks |" in english
    assert (
        "| `flask` | `pyproject.toml:4` | CRITICAL advisory GHSA-2222, waived as "
        "`supply:osv:GHSA-2222` | waived |"
    ) in english
    assert (
        "| `left-pad` | `package.json:9` | advisory GHSA-9 left unverified (DNS failure) | warns |"
    ) in english


def test_markdown_names_a_fetched_advisory_with_no_published_severity() -> None:
    supply = SupplyReport(
        ("python",),
        (),
        (
            RowWarn(
                UnverifiedAdvisory(
                    "pypi", "left", "pyproject.toml", 5, "no_severity", "GHSA-0000-0000-0000"
                )
            ),
        ),
    )

    english = to_markdown(_report(supply=supply), "en")
    portuguese = to_markdown(_report(supply=supply), "pt-BR")

    assert (
        "| `left` | `pyproject.toml:5` | advisory GHSA-0000-0000-0000, no severity published | warns |"
        in english
    )
    assert (
        "| `left` | `pyproject.toml:5` | advisory GHSA-0000-0000-0000, sem severidade publicada | avisa |"
        in portuguese
    )


def test_markdown_keeps_fetch_failure_wording_for_a_named_advisory() -> None:
    supply = SupplyReport(
        ("python",),
        (),
        (
            RowWarn(
                UnverifiedAdvisory(
                    "pypi", "left", "pyproject.toml", 5, "undecided", "GHSA-fail-0000-0003"
                )
            ),
            RowWarn(
                UnverifiedAdvisory(
                    "pypi", "left", "pyproject.toml", 6, "timeout", "GHSA-fail-0000-0001"
                )
            ),
            RowWarn(UnverifiedAdvisory("pypi", "left", "pyproject.toml", 7, "dns", "GHSA-fail-0000-0002")),
        ),
    )

    english = to_markdown(_report(supply=supply), "en")
    portuguese = to_markdown(_report(supply=supply), "pt-BR")

    assert (
        "| `left` | `pyproject.toml:5` | advisory GHSA-fail-0000-0003 left unverified (undecided answer) | warns |"
        in english
    )
    assert (
        "| `left` | `pyproject.toml:6` | advisory GHSA-fail-0000-0001 left unverified (timeout) | warns |"
        in english
    )
    assert (
        "| `left` | `pyproject.toml:7` | advisory GHSA-fail-0000-0002 left unverified (DNS failure) | warns |"
        in english
    )
    assert (
        "| `left` | `pyproject.toml:5` | advisory GHSA-fail-0000-0003 ficou não verificado (resposta sem decisão) | avisa |"
        in portuguese
    )


def test_unverified_advisory_without_an_id_names_the_cause() -> None:
    supply = SupplyReport(
        ("python",),
        (),
        (
            RowWarn(UnverifiedAdvisory("pypi", "flask", "pyproject.toml", 2, "timeout")),
            RowWarn(UnverifiedAdvisory("pypi", "flask", "pyproject.toml", 3, "dns")),
            RowWarn(UnverifiedAdvisory("pypi", "flask", "pyproject.toml", 4, "undecided")),
        ),
    )

    english = to_markdown(_report(supply=supply), "en")

    assert "| `flask` | `pyproject.toml:2` | registry timeout, left unverified | warns |" in english
    assert "| `flask` | `pyproject.toml:3` | registry DNS failure, left unverified | warns |" in english
    assert (
        "| `flask` | `pyproject.toml:4` | registry did not decide, left unverified | warns |"
    ) in english


def test_unmeasured_supply_uses_the_gate_reason_when_it_has_one() -> None:
    report = _report(
        gates=[GateResult("supply", "not_run", "deptry was not on PATH")],
        supply=SupplyReport((), ("python",), ()),
    )

    text = to_markdown(report, "en")

    assert "deptry was not on PATH" in text
    assert "no configured language produced a measurement" not in text


def test_unmeasured_supply_uses_the_default_line_when_the_gate_has_no_reason() -> None:
    report = _report(
        gates=[GateResult("supply", "not_run", None)],
        supply=SupplyReport((), ("python",), ()),
    )

    assert "no configured language produced a measurement" in to_markdown(report, "en")
