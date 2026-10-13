from __future__ import annotations

import json
from pathlib import Path

import pytest

from bob_quality.adapters.stryker import StrykerParseError, mutants_from_report
from bob_quality.models import CyclomaticFunction
from helpers import in_both

RAW = Path(__file__).parent / "fixtures" / "raw"

_SPANS = [
    CyclomaticFunction("src/safe.ts", "add", 1, 8, 1),
    CyclomaticFunction("src/safe.ts", "inner", 4, 4, 1),
    CyclomaticFunction("src/other.ts", "scale", 10, 20, 1),
]


def _mapped():
    payload = json.loads((RAW / "stryker-report.json").read_text())
    return mutants_from_report(payload, _SPANS)


def test_recorded_report_maps_every_status_and_drops_ignored_and_out_of_span() -> None:
    mutants = _mapped()

    assert [(item.id, item.status, item.function, item.file, item.line, item.operator) for item in mutants] == [
        ("src/safe.ts:0", "killed", "add", "src/safe.ts", 2, "ArithmeticOperator"),
        ("src/safe.ts:1", "survived", "add", "src/safe.ts", 3, "ConditionalExpression"),
        ("src/safe.ts:2", "no_coverage", "inner", "src/safe.ts", 4, "BlockStatement"),
        ("src/safe.ts:3", "timeout", "add", "src/safe.ts", 5, "StringLiteral"),
        ("src/safe.ts:4", "killed", "add", "src/safe.ts", 6, "BooleanLiteral"),
        ("src/safe.ts:5", "killed", "add", "src/safe.ts", 7, "EqualityOperator"),
        ("src/other.ts:0", "killed", "scale", "src/other.ts", 12, "ArithmeticOperator"),
    ]


def test_two_files_with_stryker_id_zero_keep_distinct_mutant_ids() -> None:
    mutants = _mapped()

    assert [item.id for item in mutants if item.id.endswith(":0")] == [
        "src/safe.ts:0",
        "src/other.ts:0",
    ]


def test_no_coverage_keeps_file_and_innermost_function() -> None:
    mutants = _mapped()
    uncovered = next(item for item in mutants if item.status == "no_coverage")

    assert uncovered.id == "src/safe.ts:2"
    assert uncovered.file == "src/safe.ts"
    assert uncovered.function == "inner"
    assert uncovered.line == 4
    assert uncovered.operator == "BlockStatement"


def test_pending_outside_every_span_raises() -> None:
    payload = {
        "files": {
            "src/untouched.ts": {
                "mutants": [
                    {
                        "id": "0",
                        "mutatorName": "ArithmeticOperator",
                        "status": "Pending",
                        "location": {
                            "start": {"line": 1, "column": 1},
                            "end": {"line": 1, "column": 2},
                        },
                    }
                ]
            }
        }
    }

    with pytest.raises(StrykerParseError) as caught:
        mutants_from_report(payload, [])

    assert in_both(caught.value) == (
        "unknown Stryker status: 'Pending'",
        "status desconhecido do Stryker: 'Pending'",
    )


def test_unknown_status_raises() -> None:
    payload = json.loads((RAW / "stryker-report.json").read_text())
    payload["files"]["src/safe.ts"]["mutants"][0]["status"] = "Exploded"

    with pytest.raises(StrykerParseError) as caught:
        mutants_from_report(payload, _SPANS)

    assert in_both(caught.value) == (
        "unknown Stryker status: 'Exploded'",
        "status desconhecido do Stryker: 'Exploded'",
    )


def _bad(detail: object) -> tuple[str, str]:
    return (
        f"invalid Stryker report: {detail}",
        f"relatório do Stryker inválido: {detail}",
    )


def _mutant(
    *,
    status: object = "Killed",
    mutant_id: object = "0",
    name: object = "ArithmeticOperator",
    line: object = 2,
    location: object | None = None,
) -> dict[str, object]:
    if location is None:
        location = {
            "start": {"line": line, "column": 1},
            "end": {"line": line, "column": 2},
        }
    return {
        "id": mutant_id,
        "mutatorName": name,
        "status": status,
        "location": location,
    }


def _one(report_file: str, row: dict[str, object], spans: list[CyclomaticFunction]):
    return mutants_from_report({"files": {report_file: {"mutants": [row]}}}, spans)


def test_files_must_be_a_mapping() -> None:
    with pytest.raises(StrykerParseError) as caught:
        mutants_from_report({"files": []}, _SPANS)

    assert in_both(caught.value) == _bad("files")


def test_each_malformed_row_names_the_report_file() -> None:
    spans = [CyclomaticFunction("src/safe.ts", "add", 1, 8, 1)]
    rows = [
        {"mutants": {}},
        {"mutants": [[]]},
        {"mutants": [_mutant(mutant_id=True)]},
        {"mutants": [_mutant(mutant_id=["x"])]},
        {"mutants": [_mutant(name="")]},
        {"mutants": [_mutant(name=1)]},
        {"mutants": [_mutant(location=[])]},
        {"mutants": [_mutant(location={"start": []})]},
        {"mutants": [_mutant(line=0)]},
        {"mutants": [_mutant(line=True)]},
        {"mutants": [_mutant(line="2")]},
    ]

    with pytest.raises(StrykerParseError) as caught:
        mutants_from_report({"files": {"src/safe.ts": []}}, spans)
    assert in_both(caught.value) == _bad("src/safe.ts")

    for entry in rows:
        with pytest.raises(StrykerParseError) as caught:
            mutants_from_report({"files": {"src/safe.ts": entry}}, spans)
        assert in_both(caught.value) == _bad("src/safe.ts")


def test_a_non_string_status_is_shown_with_repr() -> None:
    with pytest.raises(StrykerParseError) as caught:
        _one("src/safe.ts", _mutant(status=1), _SPANS)

    assert in_both(caught.value) == (
        "unknown Stryker status: '1'",
        "status desconhecido do Stryker: '1'",
    )


def test_ignored_and_out_of_span_do_not_drop_the_next_mutant() -> None:
    payload = {
        "files": {
            "src/kept.ts": {
                "mutants": [
                    _mutant(status="Ignored", mutant_id="0"),
                    _mutant(mutant_id="9", line=50),
                    _mutant(mutant_id="1", line=2),
                ]
            },
            "src/other.ts": {"mutants": [_mutant(line=2)]},
            "src/later.ts": {
                "mutants": [_mutant(mutant_id="2", line=3)],
            },
        }
    }
    spans = [
        CyclomaticFunction("src/kept.ts", "kept", 1, 4, 1),
        CyclomaticFunction("src/later.ts", "later", 1, 4, 1),
    ]

    mutants = mutants_from_report(payload, spans)

    assert [(item.id, item.function) for item in mutants] == [
        ("src/kept.ts:1", "kept"),
        ("src/later.ts:2", "later"),
    ]


def test_innermost_span_wins_on_size_then_path_then_start() -> None:
    row = _mutant(line=95)
    wide = CyclomaticFunction("src/safe.ts", "wide", 1, 100, 1)
    tight = CyclomaticFunction("src/safe.ts", "tight", 90, 100, 1)
    by_size = _one("src/safe.ts", row, [wide, tight])
    assert by_size[0].function == "tight"

    prefixed = CyclomaticFunction("./src/safe.ts", "prefixed", 1, 8, 1)
    plain = CyclomaticFunction("src/safe.ts", "plain", 1, 8, 1)
    by_path = _one("src/safe.ts", _mutant(line=2), [prefixed, plain])
    assert by_path[0].function == "prefixed"

    early = CyclomaticFunction("src/safe.ts", "early", 1, 10, 1)
    late = CyclomaticFunction("src/safe.ts", "late", 2, 11, 1)
    by_start = _one("src/safe.ts", _mutant(line=10), [early, late])
    assert by_start[0].function == "late"


def test_file_identity_accepts_a_dot_slash_and_a_backslash() -> None:
    spans = [
        CyclomaticFunction("./src/safe.ts", "dotted", 1, 8, 1),
        CyclomaticFunction("src\\safe.ts", "slashed", 1, 8, 1),
        CyclomaticFunction("Xsrc/safe.ts", "marked", 1, 8, 1),
    ]

    dotted = _one("src/safe.ts", _mutant(line=2), [spans[0]])
    slashed = _one("src\\safe.ts", _mutant(line=2), [CyclomaticFunction("src/safe.ts", "plain", 1, 8, 1)])
    span_slashed = _one("src/safe.ts", _mutant(line=2), [spans[1]])
    marked = _one("Xsrc/safe.ts", _mutant(line=2), [spans[2]])

    assert dotted[0].function == "dotted"
    assert slashed[0].function == "plain"
    assert span_slashed[0].function == "slashed"
    assert marked[0].function == "marked"
