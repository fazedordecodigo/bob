"""Adaptadores: saída bruta pinada de import-linter e dependency-cruiser → arestas."""

import json
import locale
import subprocess
from pathlib import Path

import pytest

from bob_quality.adapters.dependency_cruiser import parse_dependency_cruiser
from bob_quality.adapters.import_linter import broken_contract_name, parse_import_linter
from bob_quality.deps_gate import UnparsedBreak, _import_linter_violations, _ini_roots, _short
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


def test_broken_contract_keeps_a_long_name_and_strips_color() -> None:
    raw = "\x1b[31mIndependence contract\x1b[0m BROKEN\n"

    assert broken_contract_name(raw) == "Independence contract"


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
    edges = {(item.origin, item.destination, item.rule, item.in_diff) for item in violations}

    assert edges == {
        ("src/right.ts", "src/left.ts", "bob-no-circular", False),
        ("src/left.ts", "src/right.ts", "bob-no-circular", False),
    }


def test_dependency_cruiser_adapter_reads_forbidden_rule() -> None:
    violations = parse_dependency_cruiser((RAW / "dependency-cruiser-forbidden.json").read_text())

    assert [(item.origin, item.destination, item.rule) for item in violations] == [
        ("src/api.ts", "src/domain.ts", "api-not-domain")
    ]


def test_cruiser_violation_without_rule_metadata_still_blocks() -> None:
    raw = json.dumps(
        {"summary": {"violations": [{"from": "src/a.ts", "to": "src/b.ts"}]}}
    )

    violations = parse_dependency_cruiser(raw)

    assert [(item.origin, item.destination, item.rule, item.in_diff) for item in violations] == [
        ("src/a.ts", "src/b.ts", "dependência", False)
    ]


def test_cruiser_violation_without_an_origin_is_dropped() -> None:
    raw = json.dumps(
        {
            "summary": {
                "violations": [
                    {"to": "src/b.ts", "rule": {"name": "api-not-domain", "severity": "error"}}
                ]
            }
        }
    )

    assert parse_dependency_cruiser(raw) == []


def test_importlinter_roots_come_from_the_declared_section(tmp_path: Path) -> None:
    path = tmp_path / ".importlinter"
    path.write_text(
        "[importlinter]\nroot_packages =\n    alpha,\n    beta\n",
        encoding="utf-8",
    )

    assert _ini_roots(path) == ["alpha", "beta"]


def test_importlinter_roots_fall_back_to_the_singular_key(tmp_path: Path) -> None:
    path = tmp_path / ".importlinter"
    path.write_text("[importlinter]\nroot_package = only\n", encoding="utf-8")

    assert _ini_roots(path) == ["only"]


def test_importlinter_roots_ignore_a_file_without_the_section(tmp_path: Path) -> None:
    path = tmp_path / ".importlinter"
    path.write_text("[other]\nroot_packages = nope\n", encoding="utf-8")

    assert _ini_roots(path) == []


def test_importlinter_roots_read_utf8_names(tmp_path: Path) -> None:
    path = tmp_path / ".importlinter"
    path.write_bytes("[importlinter]\nroot_packages = nãoapp\n".encode("utf-8"))
    previous = locale.setlocale(locale.LC_ALL)
    locale.setlocale(locale.LC_ALL, "C")
    try:
        assert _ini_roots(path) == ["nãoapp"]
    finally:
        locale.setlocale(locale.LC_ALL, previous)


def test_tool_failure_text_is_one_line_capped_at_300_characters() -> None:
    assert _short("a\n\nb") == "a b"
    assert _short(" \n\t") == "ferramenta de dependência falhou"
    assert _short("x" * 400) == "x" * 300
