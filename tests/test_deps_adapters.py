"""Adaptadores: saída bruta pinada de import-linter e dependency-cruiser → arestas."""

from pathlib import Path

from bob_quality.adapters.dependency_cruiser import parse_dependency_cruiser
from bob_quality.adapters.import_linter import parse_import_linter

RAW = Path(__file__).parent / "fixtures" / "raw"


def test_import_linter_adapter_reads_cycle_breaker() -> None:
    violations = parse_import_linter((RAW / "import-linter-cycle.txt").read_text())

    assert [(item.origin, item.destination, item.rule) for item in violations] == [
        ("app.right", "app.left", "Proibido ciclo de dependência")
    ]


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
