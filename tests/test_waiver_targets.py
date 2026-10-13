"""A chave do waiver: `arquivo::função` cobre a função, `arquivo::função::<descrição>` cobre um sobrevivente."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from bob_quality.models import Mutant, MutantStatus
from bob_quality.mutate import (
    CACHE_NAME,
    STRYKER_MUTANTS_NAME,
    _finish,
    waivable_targets,
    write_stryker_mutants,
)
from bob_quality.waivers import (
    SurvivorTargets,
    Waiver,
    WaiverError,
    add_waiver,
    apply_waivers,
    load_waivers,
    survivor_targets,
    waivers_path,
    write_waivers,
)
from helpers import in_both

FILE = "src/app/m.py"
UNKNOWN = (
    "no survivor matches classify: copy file::function or a Target from the last mutation report",
    "nenhum sobrevivente casa com classify:"
    " copie arquivo::função ou um Alvo do último relatório de mutação",
)


def _mutant(
    mutant_id: str,
    operator: str,
    status: MutantStatus = "survived",
    file: str = FILE,
    function: str = "f",
) -> Mutant:
    return Mutant(mutant_id, function, file, 2, operator, status)


def _waiver(target: str, reason: str = "porque") -> Waiver:
    return Waiver(target, reason, "ada", "2026-10-12")


def _reasons(mutants: list[Mutant], waivers: list[Waiver]) -> dict[str, str | None]:
    return {item.id: item.waiver for item in apply_waivers(mutants, waivers)}


def test_exact_target_waives_one_survivor_and_not_its_sibling() -> None:
    one = _mutant("app.m.x_f__mutmut_1", "return 1 -> return 2")
    two = _mutant("app.m.x_f__mutmut_2", "return 1 -> return None")

    assert survivor_targets([one, two]) == {
        one.id: SurvivorTargets("src/app/m.py::f", "src/app/m.py::f::return 1 -> return 2"),
        two.id: SurvivorTargets("src/app/m.py::f", "src/app/m.py::f::return 1 -> return None"),
    }
    assert _reasons([one, two], [_waiver("src/app/m.py::f::return 1 -> return 2")]) == {
        one.id: "porque",
        two.id: None,
    }


def test_function_target_waives_every_survivor_of_that_function_only() -> None:
    mutants = [
        _mutant("app.m.x_f__mutmut_1", "a -> b"),
        _mutant("app.m.x_f__mutmut_2", "a -> c"),
        _mutant("app.m.x_g__mutmut_1", "a -> b", function="g"),
        _mutant("app.n.x_f__mutmut_1", "a -> b", file="src/app/n.py"),
    ]

    assert _reasons(mutants, [_waiver("src/app/m.py::f")]) == {
        "app.m.x_f__mutmut_1": "porque",
        "app.m.x_f__mutmut_2": "porque",
        "app.m.x_g__mutmut_1": None,
        "app.n.x_f__mutmut_1": None,
    }


def test_the_first_matching_row_gives_the_reason() -> None:
    mutant = _mutant("app.m.x_f__mutmut_1", "a -> b")
    waivers = [
        _waiver("src/app/m.py::g", "outra função"),
        _waiver("src/app/m.py::f::a -> b", "exato"),
        _waiver("src/app/m.py::f", "função"),
    ]

    assert _reasons([mutant], waivers) == {mutant.id: "exato"}


@pytest.mark.parametrize(
    "old_form", ["app.m.x_f__mutmut_1", "f", "src/app/m.py:f", "src/app/m.py:7"]
)
def test_removed_forms_waive_nothing(old_form: str) -> None:
    mutant = _mutant("app.m.x_f__mutmut_1", "a -> b")

    assert _reasons([mutant], [_waiver(old_form)]) == {mutant.id: None}


def test_twin_survivors_get_no_exact_target_and_the_text_waives_neither() -> None:
    one = _mutant("app.m.x_f__mutmut_1", "a -> b")
    two = _mutant("app.m.x_f__mutmut_2", " a -> b ")

    assert survivor_targets([one, two]) == {
        one.id: SurvivorTargets("src/app/m.py::f", None),
        two.id: SurvivorTargets("src/app/m.py::f", None),
    }
    assert _reasons([one, two], [_waiver("src/app/m.py::f::a -> b")]) == {
        one.id: None,
        two.id: None,
    }


def test_the_same_text_in_another_function_or_file_is_not_a_twin() -> None:
    mutants = [
        _mutant("app.m.x_f__mutmut_1", "a -> b"),
        _mutant("app.m.x_g__mutmut_1", "a -> b", function="g"),
        _mutant("app.n.x_f__mutmut_1", "a -> b", file="src/app/n.py"),
    ]

    assert [targets.exact for targets in survivor_targets(mutants).values()] == [
        "src/app/m.py::f::a -> b",
        "src/app/m.py::g::a -> b",
        "src/app/n.py::f::a -> b",
    ]


def test_a_killed_twin_does_not_block_the_exact_target_and_is_never_waived() -> None:
    survivor = _mutant("app.m.x_f__mutmut_1", "a -> b")
    killed = _mutant("app.m.x_f__mutmut_2", "a -> b", status="killed")
    timeout = _mutant("app.m.x_f__mutmut_3", "a -> b", status="timeout")
    uncovered = _mutant("app.m.x_f__mutmut_4", "a -> b", status="no_coverage")
    mutants = [survivor, killed, timeout, uncovered]

    assert survivor_targets(mutants) == {
        survivor.id: SurvivorTargets("src/app/m.py::f", "src/app/m.py::f::a -> b"),
    }
    assert _reasons(mutants, [_waiver("src/app/m.py::f")]) == {
        survivor.id: "porque",
        killed.id: None,
        timeout.id: None,
        uncovered.id: None,
    }


def test_a_deleted_line_operator_is_stripped_in_the_target(tmp_path: Path) -> None:
    deleted = _mutant("app.m.x_f__mutmut_1", "x = 1 -> ")
    target = survivor_targets([deleted])[deleted.id].exact

    write_waivers(tmp_path, [_waiver(str(target))])

    assert target == "src/app/m.py::f::x = 1 ->"
    assert _reasons([deleted], load_waivers(tmp_path)) == {deleted.id: "porque"}


def test_an_empty_operator_has_only_the_function_target() -> None:
    bare = _mutant("app.m.x_f__mutmut_1", "  ")

    assert survivor_targets([bare]) == {bare.id: SurvivorTargets("src/app/m.py::f", None)}
    assert _reasons([bare], [_waiver("src/app/m.py::f::")]) == {bare.id: None}
    assert _reasons([bare], [_waiver("src/app/m.py::f")]) == {bare.id: "porque"}


def test_a_survivor_without_show_data_has_no_target() -> None:
    blind = _mutant("app.m.x_f__mutmut_1", "", file="")
    waivers = [_waiver("::f"), _waiver("f"), _waiver(blind.id)]

    assert survivor_targets([blind]) == {}
    assert _reasons([blind], waivers) == {blind.id: None}


def test_a_report_row_without_an_exact_target_shows_none() -> None:
    twins = [
        Mutant("app.m.x_f__mutmut_1", "f", FILE, 2, "AOR", "survived", "porque"),
        Mutant("app.m.x_f__mutmut_2", "f", FILE, 3, "AOR", "survived", "porque"),
    ]
    blind = Mutant("app.m.x_f__mutmut_3", "f", "", 0, "", "survived")

    outcome = _finish([*twins, blind], ["src/app/m.py::f"], [], {}, [])

    assert [(row["id"], row["target"]) for row in outcome.survivors] == [
        ("app.m.x_f__mutmut_1", None),
        ("app.m.x_f__mutmut_2", None),
        ("app.m.x_f__mutmut_3", None),
    ]


@pytest.mark.parametrize("prefixed", ["cognitive:src/app/m.py:f", "coverage:src/app/m.py"])
def test_prefixed_ids_of_other_gates_never_match_a_mutant(prefixed: str) -> None:
    mutant = _mutant("app.m.x_f__mutmut_1", "a -> b")

    assert _reasons([mutant], [_waiver(prefixed)]) == {mutant.id: None}


def _git_repo(root: Path) -> Path:
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "ada"], cwd=root, check=True)
    return root


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


@pytest.mark.parametrize(
    ("target", "reason", "english"),
    [
        ("classify", None, "waiver without a reason: pass --reason with one line"),
        ("   ", "porque", "waiver without a target"),
        (" classify ", "porque", UNKNOWN[0]),
    ],
)
def test_add_waiver_refuses_before_touching_the_file(
    tmp_path: Path, target: str, reason: str | None, english: str
) -> None:
    write_waivers(tmp_path, [_waiver("src/app/m.py::f")])
    before = waivers_path(tmp_path).read_bytes()

    with pytest.raises(WaiverError) as caught:
        add_waiver(tmp_path, target, reason, frozenset({"src/app/m.py::f"}))

    assert in_both(caught.value)[0] == english
    assert waivers_path(tmp_path).read_bytes() == before


def test_an_unknown_target_is_explained_in_both_languages(tmp_path: Path) -> None:
    with pytest.raises(WaiverError) as caught:
        add_waiver(tmp_path, "classify", "porque", frozenset())

    assert in_both(caught.value) == UNKNOWN
    assert not waivers_path(tmp_path).exists()


def test_add_waiver_replaces_one_existing_id(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "repo")
    write_waivers(repo, [_waiver("src/app/m.py::f", "velho"), _waiver("src/app/m.py::g", "fica")])
    before = _today()

    saved = add_waiver(repo, " src/app/m.py::f ", " novo ", frozenset({"src/app/m.py::f"}))

    assert saved.id == "src/app/m.py::f"
    assert saved.reason == "novo"
    assert saved.author == "ada"
    assert saved.date in {before, _today()}
    assert load_waivers(repo) == [_waiver("src/app/m.py::g", "fica"), saved]


def test_add_waiver_creates_the_folder_on_the_first_waiver(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "repo")

    saved = add_waiver(repo, "src/app/m.py::f", "porque", frozenset({"src/app/m.py::f"}))

    assert load_waivers(repo) == [saved]


def test_write_waivers_keeps_a_long_id_on_one_line(tmp_path: Path) -> None:
    long_id = "src/bob_quality/adapters/mutmut.py::_consume_hunk_line::" + " ; ".join(
        ["x = 1 -> x = 2"] * 8
    )
    waiver = _waiver(long_id, " ".join(["um motivo longo"] * 8))

    write_waivers(tmp_path, [waiver])

    assert len(waivers_path(tmp_path).read_text().splitlines()) == 5
    assert load_waivers(tmp_path) == [waiver]


def test_write_waivers_creates_a_missing_ancestor(tmp_path: Path) -> None:
    repo = tmp_path / "missing" / "repo"
    waiver = _waiver("src/app/m.py::f")

    write_waivers(repo, [waiver])

    assert load_waivers(repo) == [waiver]


def test_write_waivers_keeps_unicode_and_the_dataclass_field_order(tmp_path: Path) -> None:
    write_waivers(tmp_path, [_waiver("src/app/m.py::f", "não")])

    text = waivers_path(tmp_path).read_text()
    assert "não" in text
    assert "\\x" not in text
    assert "\\u" not in text
    keys = [line.split(":", 1)[0].strip("- ").strip() for line in text.splitlines() if ":" in line]
    assert keys == ["waivers", "id", "reason", "author", "date"]


def test_add_waiver_records_the_utc_date_when_the_local_date_differs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _git_repo(tmp_path / "repo")

    class Clock:
        @staticmethod
        def now(tz: object = None) -> datetime:
            if tz is timezone.utc:
                return datetime(2026, 1, 2, 0, 30, tzinfo=timezone.utc)
            return datetime(2026, 1, 1, 21, 30)

    monkeypatch.setattr("bob_quality.waivers.datetime", Clock)

    saved = add_waiver(repo, "src/app/m.py::f", "porque", frozenset({"src/app/m.py::f"}))

    assert saved.date == "2026-01-02"


def _cache(out: Path, functions: object, **key: object) -> None:
    out.mkdir(exist_ok=True)
    (out / CACHE_NAME).write_text(json.dumps({**key, "functions": functions}))


def _row(mutant_id: str, operator: str, status: str = "survived", file: str = FILE) -> dict[str, object]:
    return {
        "id": mutant_id,
        "function": "f",
        "file": file,
        "line": 2,
        "operator": operator,
        "status": status,
        "waiver": None,
    }


def test_waivable_targets_come_from_the_survivors_of_both_reports(tmp_path: Path) -> None:
    out = tmp_path / ".bob"
    _cache(
        out,
        {
            "src/app/m.py::f": {
                "mutants": [
                    _row("app.m.x_f__mutmut_1", "a -> b"),
                    _row("app.m.x_f__mutmut_2", "a -> c"),
                    _row("app.m.x_f__mutmut_3", "a -> d", status="killed"),
                ]
            },
            "src/app/n.py::f": {
                "mutants": [
                    _row("app.n.x_f__mutmut_1", "a -> b", file="src/app/n.py"),
                    _row("app.n.x_f__mutmut_2", "a -> b", file="src/app/n.py"),
                ]
            },
            "broken": "não é entrada",
        },
        mutmut="0.0.0",
        suite="outra suíte",
    )
    write_stryker_mutants(
        out,
        [
            Mutant("src/safe.ts:1", "add", "src/safe.ts", 3, "ConditionalExpression@3:3-3:12", "survived"),
            Mutant("src/safe.ts:2", "add", "src/safe.ts", 4, "BlockStatement@4:1-4:2", "killed"),
        ],
    )

    assert waivable_targets(out) == {
        "src/app/m.py::f",
        "src/app/m.py::f::a -> b",
        "src/app/m.py::f::a -> c",
        "src/app/n.py::f",
        "src/safe.ts::add",
        "src/safe.ts::add::ConditionalExpression@3:3-3:12",
    }


def test_the_stryker_file_keeps_the_rows_of_a_cache_mutant(tmp_path: Path) -> None:
    out = tmp_path / "fresh" / "out"
    mutant = Mutant("src/safe.ts:1", "add", "src/safe.ts", 3, "ConditionalExpression@3:3-3:12", "survived", "porque")

    write_stryker_mutants(out, [mutant])

    assert (out / STRYKER_MUTANTS_NAME).read_text() == json.dumps(
        {
            "mutants": [
                {
                    "id": "src/safe.ts:1",
                    "function": "add",
                    "file": "src/safe.ts",
                    "line": 3,
                    "operator": "ConditionalExpression@3:3-3:12",
                    "status": "survived",
                    "waiver": "porque",
                }
            ]
        },
        indent=2,
    ) + "\n"


def test_no_report_means_nothing_to_waive(tmp_path: Path) -> None:
    assert waivable_targets(tmp_path / ".bob") == frozenset()


_BAD_LINE = _row("app.m.x_f__mutmut_2", "a -> c") | {"line": "dois"}
_UNREADABLE = [b"{not json", b"\xff\xfe", b"[]"]


@pytest.mark.parametrize(
    "raw",
    [
        *_UNREADABLE,
        json.dumps({"functions": []}).encode(),
        json.dumps(
            {
                "functions": {
                    "src/app/m.py::f": {"mutants": [_row("app.m.x_f__mutmut_1", "a -> b")]},
                    "src/app/m.py::g": {"mutants": [_BAD_LINE]},
                }
            }
        ).encode(),
    ],
)
def test_a_broken_cache_contributes_nothing_and_spares_the_stryker_file(
    tmp_path: Path, raw: bytes
) -> None:
    out = tmp_path / ".bob"
    write_stryker_mutants(out, [Mutant("src/safe.ts:1", "add", "src/safe.ts", 3, "X@3:3-3:4", "survived")])
    (out / CACHE_NAME).write_bytes(raw)

    assert waivable_targets(out) == {"src/safe.ts::add", "src/safe.ts::add::X@3:3-3:4"}


@pytest.mark.parametrize(
    "raw",
    [
        *_UNREADABLE,
        json.dumps({"mutants": {}}).encode(),
        json.dumps({"mutants": [_row("src/safe.ts:1", "X@3:3-3:4", file="src/safe.ts"), _BAD_LINE]}).encode(),
    ],
)
def test_a_broken_stryker_file_contributes_nothing_and_spares_the_cache(
    tmp_path: Path, raw: bytes
) -> None:
    out = tmp_path / ".bob"
    _cache(out, {"src/app/m.py::f": {"mutants": [_row("app.m.x_f__mutmut_1", "a -> b")]}})
    (out / STRYKER_MUTANTS_NAME).write_bytes(raw)

    assert waivable_targets(out) == {"src/app/m.py::f", "src/app/m.py::f::a -> b"}
