"""Adaptador c8/istanbul e lizard em TypeScript: saída gravada → modelo."""

from pathlib import Path

from bob_quality.adapters.istanbul import parse_coverage_final
from bob_quality.adapters.lizard import parse_lizard_csv
from bob_quality.core import line_coverage
from bob_quality.npm_tools import run_vitest_under_c8
from bob_quality.tools import run_lizard_csv

RAW = Path(__file__).parent / "fixtures" / "raw"
FIXTURE_TS = Path(__file__).parent / "fixtures" / "ts_app"


def _by_suffix(files: dict, suffix: str):
    matches = [value for key, value in files.items() if key.replace("\\", "/").endswith(suffix)]
    assert len(matches) == 1
    return matches[0]


def test_istanbul_adapter_reads_recorded_c8_coverage_final() -> None:
    """Saída real do c8 12 (coverage-final.json): add coberto, messy sem cobertura."""
    files = parse_coverage_final((RAW / "coverage-final.json").read_text())
    assert line_coverage(_by_suffix(files, "src/safe.ts"), 1, 3) == 1.0
    assert line_coverage(_by_suffix(files, "src/messy.ts"), 1, 12) == 0.0


def test_lizard_adapter_reads_recorded_typescript_csv() -> None:
    functions = parse_lizard_csv((RAW / "lizard-ts.csv").read_text())
    by_name = {item.name: item for item in functions}
    assert by_name["add"].cc == 1
    assert by_name["add"].start_line == 1
    assert by_name["add"].end_line == 3
    assert by_name["messy"].cc == 4
    assert by_name["messy"].start_line == 1
    assert by_name["messy"].end_line == 12


def test_pinned_lizard_csv_contract_on_typescript_fixture() -> None:
    raw = run_lizard_csv(FIXTURE_TS, include=["src"], exclude=["tests"], language="typescript")
    functions = parse_lizard_csv(raw)
    add = next(item for item in functions if item.name == "add")
    assert add.cc == 1
    assert add.start_line == 1
    assert add.end_line == 3


def test_pinned_c8_coverage_final_contract_on_typescript_fixture(tmp_path: Path) -> None:
    reports = tmp_path / "coverage"
    code = run_vitest_under_c8(FIXTURE_TS, ["src"], reports)
    files = parse_coverage_final((reports / "coverage-final.json").read_text())
    assert code == 0
    assert line_coverage(_by_suffix(files, "src/safe.ts"), 1, 3) == 1.0
