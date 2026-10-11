"""Adaptadores: saída bruta pinada → modelo. Contrato quebra se o formato mudar."""

from pathlib import Path

from bob_quality.adapters.coverage import parse_coverage_json
from bob_quality.adapters.lizard import parse_lizard_csv
from bob_quality.core import coverage_for, line_coverage, to_metric
from bob_quality.crap import calculate_crap
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


def test_pinned_lizard_csv_contract_on_python_fixture() -> None:
    raw = run_lizard_csv(FIXTURE_SRC, include=["src"], exclude=["tests"])
    functions = parse_lizard_csv(raw)
    add = next(item for item in functions if item.name == "add")
    assert add.cc == 1
    assert add.start_line == 1
    assert add.end_line == 2
