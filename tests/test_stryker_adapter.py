"""Adaptador Stryker: relatório JSON gravado → Mutant.

O arquivo é a forma do mutation-testing-report-schema que o reporter json
do @stryker-mutator/core 10.0.0 grava. O adaptador não importa o Stryker.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bob_quality.models import CyclomaticFunction
from helpers import in_both

RAW = Path(__file__).parent / "fixtures" / "raw"

_SPANS = [
    CyclomaticFunction("src/safe.ts", "add", 1, 8, 1),
    CyclomaticFunction("src/safe.ts", "inner", 4, 4, 1),
    CyclomaticFunction("src/other.ts", "scale", 10, 20, 1),
]


def _mapped():
    from bob_quality.adapters.stryker import mutants_from_report

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
    from bob_quality.adapters.stryker import StrykerParseError, mutants_from_report

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
    from bob_quality.adapters.stryker import StrykerParseError, mutants_from_report

    payload = json.loads((RAW / "stryker-report.json").read_text())
    payload["files"]["src/safe.ts"]["mutants"][0]["status"] = "Exploded"

    with pytest.raises(StrykerParseError) as caught:
        mutants_from_report(payload, _SPANS)

    assert in_both(caught.value) == (
        "unknown Stryker status: 'Exploded'",
        "status desconhecido do Stryker: 'Exploded'",
    )
