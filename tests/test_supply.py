"""Política pura do gate supply: judge, finish e tool_measured."""

from bob_quality.messages import render
from bob_quality.models import (
    Advisory,
    GateResult,
    MissingPackage,
    RowBlock,
    RowWarn,
    RowWaived,
    UndeclaredImport,
    UnverifiedAdvisory,
    UnverifiedExistence,
)
from bob_quality.supply import Judgment, finish, judge, supply_waiver_ids, tool_measured, waiver_id
from bob_quality.waivers import Waiver

FAIL = frozenset({"HIGH", "CRITICAL"})
DIFF = {"pyproject.toml": {14}, "package.json": {20}, "src/app.py": {3, 9}}


def test_waiver_id_names_missing_undeclared_and_advisory() -> None:
    missing = MissingPackage("pypi", "no-such-pkg", "pyproject.toml", 14)
    undeclared = UndeclaredImport("src/app.py", "requests", 3)
    advisory = Advisory("GHSA-1111", "npm", "left-pad", "HIGH", "package.json", 20)

    assert waiver_id(missing) == "supply:missing:pypi:no-such-pkg"
    assert waiver_id(undeclared) == "supply:undeclared:src/app.py:requests"
    assert waiver_id(advisory) == "supply:osv:GHSA-1111"


def test_supply_waiver_ids_keeps_only_the_supply_prefix() -> None:
    waivers = (
        Waiver("supply:osv:GHSA-1111", "because", "ada", "2026-10-11"),
        Waiver("app.billing.x", "because", "ada", "2026-10-11"),
        Waiver("supply:missing:npm:left-pad", "because", "ada", "2026-10-11"),
    )

    assert supply_waiver_ids(waivers) == frozenset(
        {"supply:osv:GHSA-1111", "supply:missing:npm:left-pad"}
    )


def test_judge_blocks_a_missing_package_on_a_new_line() -> None:
    finding = MissingPackage("pypi", "no-such-pkg", "pyproject.toml", 14)

    judgment = judge((finding,), DIFF, FAIL, frozenset())

    assert judgment.status == "failed"
    assert judgment.exit_code == 1
    assert judgment.rows == (RowBlock(finding),)
    assert render(judgment.reason, "en") == (
        "missing pypi package no-such-pkg at pyproject.toml:14"
    )
    assert render(judgment.reason, "pt-BR") == (
        "pacote no-such-pkg ausente no pypi em pyproject.toml:14"
    )


def test_judge_drops_a_finding_whose_line_is_absent_from_the_diff() -> None:
    finding = MissingPackage("pypi", "no-such-pkg", "pyproject.toml", 15)

    judgment = judge((finding,), DIFF, FAIL, frozenset())

    assert judgment == Judgment("passed", 0, None, ())


def test_judge_drops_a_finding_for_a_file_outside_the_diff() -> None:
    finding = UndeclaredImport("src/other.py", "requests", 3)

    judgment = judge((finding,), DIFF, FAIL, frozenset())

    assert judgment == Judgment("passed", 0, None, ())


def test_judge_keeps_the_first_row_for_one_package() -> None:
    first = MissingPackage("pypi", "no-such-pkg", "pyproject.toml", 14)
    second = UnverifiedExistence("pypi", "no-such-pkg", "pyproject.toml", 14, "timeout")

    judgment = judge((first, second), DIFF, FAIL, frozenset())

    assert judgment.rows == (RowBlock(first),)
    assert judgment.status == "failed"
    assert judgment.exit_code == 1


def test_judge_keeps_undeclared_imports_on_different_lines() -> None:
    first = UndeclaredImport("src/app.py", "requests", 3)
    second = UndeclaredImport("src/app.py", "requests", 9)

    judgment = judge((first, second), DIFF, FAIL, frozenset())

    assert judgment.rows == (RowBlock(first), RowBlock(second))
    assert render(judgment.reason, "en") == "undeclared import requests at src/app.py:3"


def test_judge_collapses_one_advisory_id_to_the_first_package() -> None:
    first = Advisory("GHSA-1111", "pypi", "left", "HIGH", "pyproject.toml", 14)
    second = Advisory("GHSA-1111", "npm", "left", "CRITICAL", "package.json", 20)

    judgment = judge((first, second), DIFF, FAIL, frozenset())

    assert judgment.rows == (RowBlock(first),)
    assert render(judgment.reason, "en") == "HIGH advisory GHSA-1111 on left at pyproject.toml:14"


def test_judge_warns_when_a_waived_high_advisory_leaves_a_moderate_one() -> None:
    high = Advisory("GHSA-1111", "pypi", "left", "HIGH", "pyproject.toml", 14)
    moderate = Advisory("GHSA-2222", "pypi", "left", "MODERATE", "pyproject.toml", 14)

    judgment = judge(
        (high, moderate),
        DIFF,
        FAIL,
        frozenset({"supply:osv:GHSA-1111"}),
    )

    assert judgment.status == "warn"
    assert judgment.exit_code == 0
    assert judgment.rows == (
        RowWaived(high, "supply:osv:GHSA-1111"),
        RowWarn(moderate),
    )
    assert render(judgment.reason, "en") == "1 warning"
    assert render(judgment.reason, "pt-BR") == "1 aviso"


def test_judge_passes_when_every_blocker_is_waived() -> None:
    finding = UndeclaredImport("src/app.py", "requests", 3)

    judgment = judge(
        (finding,),
        DIFF,
        FAIL,
        frozenset({"supply:undeclared:src/app.py:requests"}),
    )

    assert judgment == Judgment(
        "passed",
        0,
        None,
        (RowWaived(finding, "supply:undeclared:src/app.py:requests"),),
    )


def test_judge_waives_a_moderate_advisory_when_its_id_matches() -> None:
    finding = Advisory("GHSA-2222", "npm", "left-pad", "MODERATE", "package.json", 20)

    judgment = judge((finding,), DIFF, FAIL, frozenset({"supply:osv:GHSA-2222"}))

    assert judgment == Judgment(
        "passed",
        0,
        None,
        (RowWaived(finding, "supply:osv:GHSA-2222"),),
    )


def test_judge_warns_on_unverified_existence_and_ignores_a_missing_waiver() -> None:
    finding = UnverifiedExistence("npm", "left-pad", "package.json", 20, "timeout")

    judgment = judge(
        (finding,),
        DIFF,
        FAIL,
        frozenset({"supply:missing:npm:left-pad"}),
    )

    assert judgment.status == "warn"
    assert judgment.exit_code == 0
    assert judgment.rows == (RowWarn(finding),)


def test_judge_warns_on_an_unverified_advisory_and_counts_two_warnings() -> None:
    existence = UnverifiedExistence("pypi", "left", "pyproject.toml", 14, "dns")
    advisory = UnverifiedAdvisory("pypi", "left", "pyproject.toml", 14, "undecided", "GHSA-9")

    judgment = judge((existence, advisory), DIFF, FAIL, frozenset({"supply:osv:GHSA-9"}))

    assert judgment.rows == (RowWarn(existence), RowWarn(advisory))
    assert judgment.status == "warn"
    assert judgment.exit_code == 0
    assert render(judgment.reason, "en") == "2 warnings"
    assert render(judgment.reason, "pt-BR") == "2 avisos"


def test_judge_keeps_unverified_advisories_that_differ_by_id() -> None:
    named = UnverifiedAdvisory("npm", "left-pad", "package.json", 20, "undecided", "GHSA-9")
    blank = UnverifiedAdvisory("npm", "left-pad", "package.json", 20, "timeout", None)

    judgment = judge((named, blank), DIFF, FAIL, frozenset())

    assert judgment.rows == (RowWarn(named), RowWarn(blank))


def test_judge_treats_high_as_a_warning_when_it_is_outside_fail_severities() -> None:
    finding = Advisory("GHSA-1111", "pypi", "left", "HIGH", "pyproject.toml", 14)

    judgment = judge((finding,), DIFF, frozenset({"CRITICAL"}), frozenset())

    assert judgment.status == "warn"
    assert judgment.exit_code == 0
    assert judgment.rows == (RowWarn(finding),)


def test_judge_blocks_low_when_the_fail_set_names_it() -> None:
    finding = Advisory("GHSA-3333", "pypi", "left", "LOW", "pyproject.toml", 14)

    judgment = judge((finding,), DIFF, frozenset({"LOW", "CRITICAL"}), frozenset())

    assert judgment.rows == (RowBlock(finding),)
    assert judgment.exit_code == 1
    assert render(judgment.reason, "en") == "LOW advisory GHSA-3333 on left at pyproject.toml:14"


def test_finish_copies_a_measured_block() -> None:
    finding = MissingPackage("pypi", "no-such-pkg", "pyproject.toml", 14)
    judgment = judge((finding,), DIFF, FAIL, frozenset())

    result, code = finish(judgment, ("python",))

    assert code == 1
    assert result == GateResult("supply", "failed", judgment.reason)


def test_finish_copies_a_measured_warning() -> None:
    finding = UnverifiedExistence("npm", "left-pad", "package.json", 20, "timeout")
    judgment = judge((finding,), DIFF, FAIL, frozenset())

    result, code = finish(judgment, ("python", "typescript"))

    assert code == 0
    assert result == GateResult("supply", "warn", judgment.reason)


def test_finish_exits_4_when_no_language_measured_even_if_judge_blocked() -> None:
    finding = MissingPackage("pypi", "no-such-pkg", "pyproject.toml", 14)
    judgment = judge((finding,), DIFF, FAIL, frozenset())

    result, code = finish(judgment, ())

    assert code == 4
    assert result == GateResult("supply", "not_run", result.reason)
    assert render(result.reason, "en") == "no configured language produced a measurement"
    assert render(result.reason, "pt-BR") == "nenhuma linguagem configurada produziu medição"
    assert judgment.rows == (RowBlock(finding),)


def test_tool_measured_accepts_only_a_parsed_clean_run_or_found_exit() -> None:
    found = frozenset({1})

    assert tool_measured(0, True, found) is True
    assert tool_measured(1, True, found) is True
    assert tool_measured(1, False, found) is False
    assert tool_measured(2, True, found) is False
    assert tool_measured(0, False, found) is False
    assert tool_measured(128, True, found) is False
