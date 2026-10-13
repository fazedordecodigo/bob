"""Mutantes sem teste: contagem por função e falha no relatório."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from bob_quality.adapters.mutmut import id_matches_function
from bob_quality.messages import Language, render
from bob_quality.models import CyclomaticFunction, GateResult, Mutant, Report
from bob_quality.mutate import (
    _belongs,
    _cache_body,
    _finish,
    _start_line,
    _with_file_lines,
    focus_with_survivors,
    no_coverage_summary,
)
from bob_quality.report import to_markdown


def _verdict(result: GateResult, lang: Language) -> tuple[str, str, str | None]:
    shown = render(result.reason, lang) if result.reason is not None else None
    return result.name, result.status, shown

_LABELS = [
    "src/app/b.py::a",
    "src/app/a.py::z",
    "src/app/a.py::m",
    "src/gone.py::zero",
    "src/app/a.py::add",
    "src/c.py::top",
]

_MUTANTS = [
    Mutant("app.b.x_a__mutmut_1", "a", "", 0, "", "no_coverage"),
    Mutant("app.b.x_a__mutmut_2", "a", "", 0, "", "no_coverage"),
    Mutant("app.a.x_z__mutmut_1", "z", "", 0, "", "no_coverage"),
    Mutant("app.a.x_z__mutmut_2", "z", "", 0, "", "no_coverage"),
    Mutant("app.a.x_m__mutmut_1", "m", "", 0, "", "no_coverage"),
    Mutant("app.a.x_m__mutmut_2", "m", "", 0, "", "no_coverage"),
    Mutant("app.a.x_add__mutmut_1", "add", "", 0, "", "no_coverage"),
    Mutant("app.a.x_add__mutmut_2", "add", "", 0, "", "killed"),
    Mutant("app.a.x_add__mutmut_3", "add", "", 0, "", "survived"),
    Mutant("app.a.x_add_two__mutmut_1", "add_two", "", 0, "", "no_coverage"),
    Mutant("app.a.x_other__mutmut_1", "other", "", 0, "", "no_coverage"),
    Mutant("gone.x_zero__mutmut_1", "zero", "", 0, "", "killed"),
    Mutant("c.x_top__mutmut_1", "top", "", 0, "", "no_coverage"),
    Mutant("c.x_top__mutmut_2", "top", "", 0, "", "no_coverage"),
    Mutant("c.x_top__mutmut_3", "top", "", 0, "", "no_coverage"),
    Mutant("c.x_top__mutmut_4", "top", "", 0, "", "timeout"),
]

_SUMMARY = {
    "total": 10,
    "functions": [
        {"file": "src/c.py", "function": "top", "count": 3},
        {"file": "src/app/a.py", "function": "m", "count": 2},
        {"file": "src/app/a.py", "function": "z", "count": 2},
        {"file": "src/app/b.py", "function": "a", "count": 2},
        {"file": "src/app/a.py", "function": "add", "count": 1},
    ],
}


def test_no_coverage_summary_groups_uncovered_mutants_by_listed_function() -> None:
    assert no_coverage_summary(_MUTANTS, _LABELS) == _SUMMARY


def test_no_coverage_summary_counts_a_typescript_id_by_file_and_function() -> None:
    mutants = [
        Mutant("src/safe.ts:2", "add", "src/safe.ts", 2, "BlockStatement", "no_coverage"),
        Mutant("app.a.x_add__mutmut_1", "add", "", 0, "", "no_coverage"),
    ]

    assert no_coverage_summary(mutants, ["src/safe.ts::add", "src/app/a.py::add"]) == {
        "total": 2,
        "functions": [
            {"file": "src/app/a.py", "function": "add", "count": 1},
            {"file": "src/safe.ts", "function": "add", "count": 1},
        ],
    }


def test_id_matches_function_stops_after_the_function_name() -> None:
    assert id_matches_function("app.a.x_foo__mutmut_1", "src/app/a.py", "foo") is True
    assert id_matches_function("app.a.x_foo__mutmut", "src/app/a.py", "foo") is True
    assert id_matches_function("app.a.x_foo_bar__mutmut_1", "src/app/a.py", "foo") is False
    assert id_matches_function("app.a.x_foo__mutmut_1", "src/app/a.py", "foo_bar") is False


def test_summary_does_not_count_foo_bar_as_foo() -> None:
    mutants = [
        Mutant("app.a.x_foo__mutmut_1", "foo", "", 0, "", "no_coverage"),
        Mutant("app.a.x_foo_bar__mutmut_1", "foo_bar", "", 0, "", "no_coverage"),
    ]

    assert no_coverage_summary(mutants, ["src/app/a.py::foo"]) == {
        "total": 1,
        "functions": [{"file": "src/app/a.py", "function": "foo", "count": 1}],
    }


def test_summary_keeps_a_function_name_after_the_first_separator() -> None:
    mutant = Mutant("app.a.x_add::more__mutmut_1", "add::more", "", 0, "", "no_coverage")

    assert no_coverage_summary([mutant], ["src/app/a.py::add::more"]) == {
        "total": 1,
        "functions": [{"file": "src/app/a.py", "function": "add::more", "count": 1}],
    }


def test_finish_fails_for_one_uncovered_mutant_and_passes_when_there_are_none() -> None:
    uncovered = Mutant("app.orphan.x_orphan__mutmut_1", "orphan", "", 0, "", "no_coverage")
    blocked = _finish([uncovered], {}, ["src/app/orphan.py::orphan"], [], {}, [])
    passed = _finish(
        [Mutant("app.a.x_add__mutmut_1", "add", "src/app/a.py", 1, "AOR", "killed")],
        {},
        ["src/app/a.py::add"],
        ["src/app/a.py::scale"],
        {},
        [],
    )

    assert blocked.exit_code == 3
    assert _verdict(blocked.result, "pt-BR") == ("mutate", "failed", "1 mutante sem teste")
    assert _verdict(blocked.result, "en") == ("mutate", "failed", "1 mutant without a test")
    assert blocked.summary["no_coverage"] == {
        "total": 1,
        "functions": [{"file": "src/app/orphan.py", "function": "orphan", "count": 1}],
    }
    assert passed.exit_code == 0
    assert passed.result == GateResult("mutate", "passed", None)
    assert passed.summary["remutated"] == ["src/app/a.py::add"]
    assert passed.summary["reused"] == ["src/app/a.py::scale"]
    assert passed.summary["no_coverage"] == {"total": 0, "functions": []}


def test_finish_stays_failed_when_an_unwaived_survivor_remains() -> None:
    first = Mutant("app.a.x_a__mutmut_1", "a", "src/app/a.py", 2, "AOR", "survived")
    second = Mutant("app.b.x_b__mutmut_1", "b", "src/app/b.py", 4, "AOR", "survived")
    uncovered = Mutant("app.a.x_a__mutmut_2", "a", "", 0, "", "no_coverage")
    waivers = [{"id": "other", "reason": "outro", "author": "ada", "date": "2026-10-11"}]
    outcome = _finish(
        [first, second, uncovered],
        {"src/app/a.py": {2}, "src/app/b.py": {4}},
        ["src/app/a.py::a", "src/app/b.py::b"],
        [],
        {"mutmut": "3.8.0"},
        waivers,
    )

    assert outcome.exit_code == 3
    assert _verdict(outcome.result, "pt-BR") == (
        "mutate",
        "failed",
        "sobrevivente sem waiver: a@src/app/a.py:2, b@src/app/b.py:4",
    )
    assert _verdict(outcome.result, "en") == (
        "mutate",
        "failed",
        "survivor without waiver: a@src/app/a.py:2, b@src/app/b.py:4",
    )
    assert outcome.versions == {"mutmut": "3.8.0"}
    assert outcome.waivers == waivers
    assert outcome.survivors == [
        {
            "id": "app.a.x_a__mutmut_1",
            "function": "a",
            "file": "src/app/a.py",
            "line": 2,
            "operator": "AOR",
            "status": "survived",
            "waiver": None,
            "blocking": True,
        },
        {
            "id": "app.b.x_b__mutmut_1",
            "function": "b",
            "file": "src/app/b.py",
            "line": 4,
            "operator": "AOR",
            "status": "survived",
            "waiver": None,
            "blocking": True,
        },
    ]
    assert outcome.summary["no_coverage"] == {
        "total": 1,
        "functions": [{"file": "src/app/a.py", "function": "a", "count": 1}],
    }


def test_finish_keeps_a_waived_survivor_while_warning_about_uncovered_mutants() -> None:
    survivor = Mutant(
        "app.orphan.x_orphan__mutmut_1",
        "orphan",
        "src/app/orphan.py",
        2,
        "AOR",
        "survived",
        "w1",
    )
    uncovered = Mutant("app.orphan.x_orphan__mutmut_2", "orphan", "", 0, "", "no_coverage")
    waivers = [{"id": "w1", "reason": "equivalente", "author": "ada", "date": "2026-10-11"}]
    outcome = _finish(
        [survivor, uncovered],
        {"src/app/orphan.py": {2}},
        ["src/app/orphan.py::orphan"],
        [],
        {"mutmut": "3.8.0"},
        waivers,
    )

    assert outcome.exit_code == 3
    assert _verdict(outcome.result, "pt-BR") == ("mutate", "failed", "1 mutante sem teste")
    assert _verdict(outcome.result, "en") == ("mutate", "failed", "1 mutant without a test")
    assert outcome.versions == {"mutmut": "3.8.0"}
    assert outcome.waivers == waivers
    assert outcome.survivors == [
        {
            "id": "app.orphan.x_orphan__mutmut_1",
            "function": "orphan",
            "file": "src/app/orphan.py",
            "line": 2,
            "operator": "AOR",
            "status": "survived",
            "waiver": "w1",
            "blocking": False,
        }
    ]


def test_a_waiver_does_not_excuse_a_mutant_without_a_test() -> None:
    uncovered = Mutant(
        "app.orphan.x_orphan__mutmut_1",
        "orphan",
        "src/app/orphan.py",
        1,
        "AOR",
        "no_coverage",
        "because",
    )
    waivers = [{"id": "orphan", "reason": "because", "author": "ada", "date": "2026-10-11"}]

    outcome = _finish([uncovered], {}, ["src/app/orphan.py::orphan"], [], {}, waivers)

    assert outcome.exit_code == 3
    assert _verdict(outcome.result, "en") == ("mutate", "failed", "1 mutant without a test")
    assert outcome.summary["no_coverage"] == {
        "total": 1,
        "functions": [{"file": "src/app/orphan.py", "function": "orphan", "count": 1}],
    }


def test_finish_fails_with_the_uncovered_total() -> None:
    mutants = [
        Mutant("app.orphan.x_orphan__mutmut_1", "orphan", "", 0, "", "no_coverage"),
        Mutant("app.orphan.x_orphan__mutmut_2", "orphan", "", 0, "", "no_coverage"),
    ]
    outcome = _finish(mutants, {}, ["src/app/orphan.py::orphan"], [], {}, [])

    assert outcome.exit_code == 3
    assert _verdict(outcome.result, "pt-BR") == ("mutate", "failed", "2 mutantes sem teste")
    assert _verdict(outcome.result, "en") == ("mutate", "failed", "2 mutants without a test")


def test_finish_blocks_only_the_survivor_on_a_changed_line() -> None:
    changed = Mutant("app.a.x_a__mutmut_1", "a", "src/app/a.py", 2, "AOR", "survived")
    unchanged = Mutant("app.a.x_a__mutmut_2", "a", "src/app/a.py", 3, "AOR", "survived")
    reused = Mutant("app.b.x_b__mutmut_1", "b", "src/app/b.py", 2, "AOR", "survived")

    outcome = _finish(
        [changed, unchanged, reused],
        {"src/app/a.py": {2}},
        ["src/app/a.py::a"],
        ["src/app/b.py::b"],
        {},
        [],
    )

    assert outcome.exit_code == 3
    assert _verdict(outcome.result, "en") == (
        "mutate",
        "failed",
        "survivor without waiver: a@src/app/a.py:2",
    )
    assert [row["blocking"] for row in outcome.survivors] == [True, False, False]


def test_finish_passes_when_every_survivor_is_off_the_diff() -> None:
    off = Mutant("app.a.x_a__mutmut_1", "a", "src/app/a.py", 3, "AOR", "survived")
    uncovered = Mutant("app.a.x_a__mutmut_2", "a", "", 0, "", "no_coverage")

    passed = _finish([off], {"src/app/a.py": {2}}, ["src/app/a.py::a"], [], {}, [])
    failed = _finish([off, uncovered], {"src/app/a.py": {2}}, ["src/app/a.py::a"], [], {}, [])

    assert passed.exit_code == 0
    assert passed.result == GateResult("mutate", "passed", None)
    assert passed.survivors[0]["blocking"] is False
    assert failed.exit_code == 3
    assert failed.survivors[0]["blocking"] is False
    assert _verdict(failed.result, "en") == ("mutate", "failed", "1 mutant without a test")


@pytest.mark.parametrize(
    ("file", "line"),
    [("", 0), ("src/app/a.py", 0), ("src/app/a.py", -1), ("", 2)],
    ids=["show-failed", "no-added-line", "negative-line", "no-file"],
)
def test_finish_blocks_a_survivor_without_a_file_line(file: str, line: int) -> None:
    lost = Mutant("app.a.x_a__mutmut_1", "a", file, line, "", "survived")

    outcome = _finish([lost], {"src/app/a.py": {2}}, ["src/app/a.py::a"], [], {}, [])

    assert outcome.exit_code == 3
    assert outcome.survivors[0]["blocking"] is True


def test_finish_never_blocks_a_timeout_or_an_uncovered_mutant() -> None:
    timeout = Mutant("app.a.x_a__mutmut_1", "a", "src/app/a.py", 2, "AOR", "timeout")
    uncovered = Mutant("app.a.x_a__mutmut_2", "a", "", 0, "", "no_coverage")

    outcome = _finish([timeout, uncovered], {"src/app/a.py": {2}}, ["src/app/a.py::a"], [], {}, [])

    assert outcome.exit_code == 3
    assert outcome.survivors == []
    assert _verdict(outcome.result, "en") == ("mutate", "failed", "1 mutant without a test")


def test_finish_does_not_block_line_1_outside_the_diff() -> None:
    edge = Mutant("app.a.x_a__mutmut_1", "a", "src/app/a.py", 1, "AOR", "survived")

    outcome = _finish([edge], {"src/app/a.py": {2}}, ["src/app/a.py::a"], [], {}, [])

    assert outcome.exit_code == 0
    assert outcome.survivors[0]["blocking"] is False


def test_focus_counts_only_blocking_survivors() -> None:
    survivors = [
        {"file": "src/app/b.py", "waiver": None, "blocking": False},
        {"file": "src/app/c.py", "waiver": None, "blocking": True},
        {"file": "src/app/a.py", "waiver": None, "blocking": True},
        {"file": "src/app/a.py", "waiver": "w1", "blocking": False},
    ]

    assert focus_with_survivors([{"file": "src/app/a.py", "risk": 12.0}], survivors) == [
        {"file": "src/app/a.py", "risk": 112.0},
        {"file": "src/app/c.py", "risk": 100.0},
    ]


def test_markdown_lists_uncovered_mutants_after_the_survivors() -> None:
    report = _report(
        gates=[GateResult("mutate", "failed", "3 mutantes sem teste")],
        mutation={
            "remutated": ["src/app/b.py::z"],
            "reused": ["src/app/a.py::add"],
            "no_coverage": {
                "total": 3,
                "functions": [
                    {"file": "src/app/b.py", "function": "z", "count": 2},
                    {"file": "src/app/a.py", "function": "add", "count": 1},
                ],
            },
        },
    )

    assert to_markdown(report, "pt-BR") == _MARKDOWN_WITH_ROWS


def test_markdown_says_when_no_listed_mutant_lacks_a_test() -> None:
    report = _report(
        mutation={"remutated": [], "reused": [], "no_coverage": {"total": 0, "functions": []}},
    )

    assert to_markdown(report, "pt-BR") == _MARKDOWN_EMPTY


def _report(gates: list[GateResult] | None = None, **extra: object) -> Report:
    return Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-11T00:00:00+00:00",
        tool_versions={"mutmut": "3.8.0"},
        gates=gates if gates is not None else [GateResult("mutate", "passed", None)],
        focus=[],
        top_crap=[],
        reproduce="bob mutate --base main",
        **extra,
    )


_HEAD = (
    "# Relatório bob\n\n"
    "## Waivers\n\nNenhum waiver.\n\n"
    "- Commit: `abc`\n- Base: `main`\n- Data: 2026-10-11T00:00:00+00:00\n"
    "- Ferramentas: mutmut 3.8.0\n\n"
    "## Veredito\n\n"
)

_BODY = (
    "\n## Onde focar o review\n\n- Nenhum arquivo alterado com risco de CRAP.\n\n"
    "## Top 5 funções por CRAP (diff)\n\nNenhuma função alterada medida.\n\n"
    "## Violações e ciclos de dependência\n\n- Gate não executado.\n\n"
    "## Clones novos\n\nNão executado.\n\n"
    "## Mutantes sobreviventes\n\nNenhum mutante sobrevivente.\n\n"
)

_MARKDOWN_WITH_ROWS = (
    _HEAD
    + "- ❌ `mutate`: falhou (3 mutantes sem teste)\n"
    + _BODY
    + "## Mutantes sem teste\n\n"
    + "❌ Total: 3. Bloqueia.\n\n"
    + "| Função | Arquivo | Mutantes |\n"
    + "|---|---|---:|\n"
    + "| z | src/app/b.py | 2 |\n"
    + "| add | src/app/a.py | 1 |\n\n"
    + "## Como reproduzir\n\n```\nbob mutate --base main --lang pt-BR\n```\n"
)

_MARKDOWN_EMPTY = (
    _HEAD
    + "- ✅ `mutate`: passou\n"
    + _BODY
    + "## Mutantes sem teste\n\nNenhum mutante sem teste.\n\n"
    + "## Como reproduzir\n\n```\nbob mutate --base main --lang pt-BR\n```\n"
)


def test_a_mutant_belongs_only_to_the_function_with_that_name() -> None:
    foo = CyclomaticFunction("src/app/a.py", "foo", 10, 12, 1)
    longer = CyclomaticFunction("src/app/a.py", "foo_bar", 40, 42, 1)
    own = Mutant("app.a.x_foo__mutmut_1", "foo", "src/app/a.py", 2, "AOR", "killed")
    sibling = Mutant("app.a.x_foo_bar__mutmut_1", "foo_bar", "src/app/a.py", 3, "AOR", "killed")

    assert _belongs(own, []) is False
    assert _belongs(own, [longer, foo]) is True
    assert _belongs(sibling, [foo]) is False
    assert _start_line(own, [longer, foo]) == 10
    assert _start_line(sibling, [foo]) is None
    assert _with_file_lines([own, sibling], [foo, longer]) == [
        Mutant("app.a.x_foo__mutmut_1", "foo", "src/app/a.py", 11, "AOR", "killed"),
        Mutant("app.a.x_foo_bar__mutmut_1", "foo_bar", "src/app/a.py", 42, "AOR", "killed"),
    ]


def test_an_unlocated_mutant_keeps_its_line() -> None:
    foo = CyclomaticFunction("src/app/a.py", "foo", 10, 12, 1)
    unknown = Mutant("app.a.x_missing__mutmut_1", "missing", "", 2, "", "killed")
    uncovered = Mutant("app.a.x_foo__mutmut_2", "foo", "", 0, "", "no_coverage")

    assert _start_line(unknown, [foo]) is None
    assert _with_file_lines([unknown, uncovered], [foo]) == [unknown, uncovered]


def test_cache_body_stores_each_function_and_skips_a_longer_name(tmp_path: Path) -> None:
    source = "def foo():\n    return 1\n\ndef foo_bar():\n    return 2\n"
    path = tmp_path / "src" / "app" / "a.py"
    path.parent.mkdir(parents=True)
    path.write_text(source)
    foo = CyclomaticFunction("src/app/a.py", "foo", 1, 2, 1)
    longer = CyclomaticFunction("src/app/a.py", "foo_bar", 4, 5, 1)
    own = Mutant("app.a.x_foo__mutmut_1", "foo", "src/app/a.py", 2, "AOR", "killed")
    sibling = Mutant("app.a.x_foo_bar__mutmut_1", "foo_bar", "src/app/a.py", 5, "AOR", "survived")

    body = _cache_body(tmp_path, [foo, longer], [own, sibling])

    assert body["src/app/a.py::foo"] == {
        "hash": hashlib.sha256(b"def foo():\n    return 1").hexdigest(),
        "file": "src/app/a.py",
        "name": "foo",
        "start_line": 1,
        "end_line": 2,
        "line_base": "file",
        "mutants": [
            {
                "id": own.id,
                "function": "foo",
                "file": "src/app/a.py",
                "line": 2,
                "operator": "AOR",
                "status": "killed",
                "waiver": None,
            }
        ],
    }
    assert body["src/app/a.py::foo_bar"]["mutants"] == [
        {
            "id": sibling.id,
            "function": "foo_bar",
            "file": "src/app/a.py",
            "line": 5,
            "operator": "AOR",
            "status": "survived",
            "waiver": None,
        }
    ]
