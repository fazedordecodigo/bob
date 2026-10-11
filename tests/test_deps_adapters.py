"""Adaptadores: saída bruta pinada de import-linter e dependency-cruiser → arestas."""

import subprocess
from pathlib import Path

import pytest

from bob_quality.adapters.dependency_cruiser import parse_dependency_cruiser
from bob_quality.adapters.import_linter import broken_contract_name, parse_import_linter
from bob_quality.deps_gate import UnparsedBreak, _import_linter_violations
from bob_quality.models import GateResult, Report
from bob_quality.report import to_markdown

RAW = Path(__file__).parent / "fixtures" / "raw"


def test_import_linter_adapter_reads_cycle_breaker() -> None:
    violations = parse_import_linter((RAW / "import-linter-cycle.txt").read_text())

    assert [(item.origin, item.destination, item.rule) for item in violations] == [
        ("app.right", "app.left", "Proibido ciclo de dependência")
    ]


def test_import_linter_break_without_an_arrow_is_still_a_broken_contract() -> None:
    raw = "Layers BROKEN\n\nLayers\n------\n\n- some.module\n"

    assert parse_import_linter(raw) == []
    assert broken_contract_name(raw) == "Layers"


def test_linter_exit_without_edges_does_not_count_as_passed() -> None:
    completed = subprocess.CompletedProcess(
        args=["lint-imports"],
        returncode=1,
        stdout="Layers BROKEN\n",
        stderr="",
    )

    with pytest.raises(UnparsedBreak, match="contrato quebrado: Layers"):
        _import_linter_violations(completed)


def test_report_names_a_broken_contract_when_no_edge_was_parsed() -> None:
    report = Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-11T00:00:00+00:00",
        tool_versions={},
        gates=[GateResult("deps", "failed", "contrato quebrado: Layers")],
        focus=[],
        top_crap=[],
        reproduce="bob deps",
        exit_code=1,
    )
    markdown = to_markdown(report)

    assert "❌ `deps`: falhou (contrato quebrado: Layers)" in markdown
    assert "- contrato quebrado: Layers" in markdown


def test_import_linter_adapter_reads_forbidden_contract() -> None:
    violations = parse_import_linter((RAW / "import-linter-forbidden.txt").read_text())

    assert [(item.origin, item.destination, item.rule) for item in violations] == [
        ("app.api", "app.domain", "API não importa domínio")
    ]


def test_dependency_cruiser_adapter_reads_cycle_and_skips_info() -> None:
    violations = parse_dependency_cruiser((RAW / "dependency-cruiser-cycle.json").read_text())
    edges = {(item.origin, item.destination, item.rule) for item in violations}

    assert edges == {
        ("src/right.ts", "src/left.ts", "bob-no-circular"),
        ("src/left.ts", "src/right.ts", "bob-no-circular"),
    }


def test_dependency_cruiser_adapter_reads_forbidden_rule() -> None:
    violations = parse_dependency_cruiser((RAW / "dependency-cruiser-forbidden.json").read_text())

    assert [(item.origin, item.destination, item.rule) for item in violations] == [
        ("src/api.ts", "src/domain.ts", "api-not-domain")
    ]
