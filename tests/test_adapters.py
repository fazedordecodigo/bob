"""Adaptadores: saída bruta pinada → modelo. Contrato quebra se o formato mudar."""

import json
from pathlib import Path

from bob_quality.adapters.coverage import parse_coverage_json
from bob_quality.adapters.jscpd import parse_jscpd_json
from bob_quality.adapters.lizard import parse_lizard_csv
from bob_quality.core import coverage_for, line_coverage, to_metric
from bob_quality.crap import calculate_crap
from bob_quality.models import Clone, CyclomaticFunction, FileCoverage
from bob_quality.tools import run_lizard_csv

RAW = Path(__file__).parent / "fixtures" / "raw"
FIXTURE_SRC = Path(__file__).parent / "fixtures" / "python_app"


def test_lizard_adapter_reads_pinned_csv_fixture() -> None:
    functions = parse_lizard_csv((RAW / "lizard.csv").read_text())
    by_name = {item.name: item for item in functions}
    assert by_name["add"].cc == 1
    assert by_name["add"].start_line == 1
    assert by_name["messy"].cc == 4
    assert by_name["messy"].end_line == 8


def test_lizard_adapter_skips_header_and_blank_rows() -> None:
    header = "NLOC,CCN,token,PARAM,length,location,file,function,long_name,start,end\n\n"

    functions = parse_lizard_csv(header + (RAW / "lizard.csv").read_text())

    assert functions == [
        CyclomaticFunction(file="src/app/safe.py", name="add", start_line=1, end_line=2, cc=1),
        CyclomaticFunction(file="src/app/risky.py", name="messy", start_line=1, end_line=8, cc=4),
    ]


def test_coverage_adapter_reads_line_sets_and_defaults_absent_ones_to_empty() -> None:
    raw = '{"files": {"a.py": {"executed_lines": [1, 2], "missing_lines": [3]}, "b.py": {}}}'

    assert parse_coverage_json(raw) == {
        "a.py": FileCoverage(executed_lines=frozenset({1, 2}), missing_lines=frozenset({3})),
        "b.py": FileCoverage(executed_lines=frozenset(), missing_lines=frozenset()),
    }


def test_coverage_adapter_reads_pinned_json_fixture() -> None:
    files = parse_coverage_json((RAW / "coverage.json").read_text())
    assert line_coverage(files["src/app/safe.py"], 1, 2) == 1.0
    assert line_coverage(files["src/app/risky.py"], 1, 8) == 0.0


def test_adapters_feed_crap_formula_with_known_literals() -> None:
    functions = parse_lizard_csv((RAW / "lizard.csv").read_text())
    files = parse_coverage_json((RAW / "coverage.json").read_text())
    messy = next(item for item in functions if item.name == "messy")
    coverage = line_coverage(files["src/app/risky.py"], messy.start_line, messy.end_line)
    assert calculate_crap(messy.cc, coverage) == 20.0
    metric = to_metric(messy, "src/app/risky.py", coverage_for(files, "src/app/risky.py"), True)
    assert metric.crap == 20.0
    assert metric.changed is True


def test_jscpd_adapter_reads_pinned_json_fixture() -> None:
    clones = parse_jscpd_json((RAW / "jscpd-report.json").read_text())
    assert len(clones) == 1
    clone = clones[0]
    assert clone.first_file == "src/receipt_a.py"
    assert clone.second_file == "src/receipt_b.py"
    assert clone.first_start == 1
    assert clone.first_end == 11
    assert clone.second_start == 1
    assert clone.second_end == 11
    assert clone.lines == 11
    assert clone.tokens == 88
    assert clone.kind == "exact"
    assert clone.similarity is None


def test_pinned_lizard_csv_contract_on_python_fixture() -> None:
    raw = run_lizard_csv(FIXTURE_SRC, include=["src"], exclude=["tests"])
    functions = parse_lizard_csv(raw)
    add = next(item for item in functions if item.name == "add")
    assert add.cc == 1
    assert add.start_line == 1
    assert add.end_line == 2


def test_jscpd_adapter_reads_similarity_and_drops_a_kind_that_is_not_text() -> None:
    duplicate = {
        "firstFile": {"name": "a.py", "start": 1, "end": 4},
        "secondFile": {"name": "b.py", "start": 5, "end": 8},
        "lines": 4,
        "tokens": 30,
        "similarity": "0.75",
        "kind": 3,
    }

    clones = parse_jscpd_json(json.dumps({"duplicates": [duplicate]}))

    assert clones == [Clone("a.py", 1, 4, "b.py", 5, 8, 4, 30, similarity=0.75, kind="")]
