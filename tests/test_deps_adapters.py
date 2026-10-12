"""Adaptadores: saída bruta pinada de import-linter e dependency-cruiser → arestas."""

import json
import locale
import subprocess
from pathlib import Path

import pytest

from bob_quality.adapters.dependency_cruiser import parse_dependency_cruiser
from bob_quality.adapters.import_linter import broken_contract_name, parse_import_linter
from bob_quality.config import Config
from bob_quality.deps_gate import (
    UnparsedBreak,
    _cruise_violations,
    _import_linter_violations,
    _ini_roots,
    _short,
    run_deps_gate,
)
from bob_quality.messages import render
from bob_quality.models import DepViolation, GateResult, Report
from bob_quality.report import to_markdown
from bob_quality.tools import ToolError
from helpers import in_both

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


def _broken_layers() -> UnparsedBreak:
    completed = subprocess.CompletedProcess(
        args=["lint-imports"],
        returncode=1,
        stdout="Layers BROKEN\n",
        stderr="",
    )
    with pytest.raises(UnparsedBreak) as caught:
        _import_linter_violations(completed)
    return caught.value


def test_linter_exit_without_edges_does_not_count_as_passed() -> None:
    broken = _broken_layers()

    assert render(broken.reason, "en") == "broken contract: Layers"
    assert render(broken.reason, "pt-BR") == "contrato quebrado: Layers"


def test_report_names_a_broken_contract_when_no_edge_was_parsed() -> None:
    report = Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-11T00:00:00+00:00",
        tool_versions={},
        gates=[GateResult("deps", "failed", _broken_layers().reason)],
        focus=[],
        top_crap=[],
        reproduce="bob deps",
        exit_code=1,
    )
    portuguese = to_markdown(report, "pt-BR")
    english = to_markdown(report, "en")

    assert "❌ `deps`: falhou (contrato quebrado: Layers)" in portuguese
    assert "- contrato quebrado: Layers" in portuguese
    assert "❌ `deps`: failed (broken contract: Layers)" in english
    assert "- broken contract: Layers" in english


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

    assert [(item.origin, item.destination, item.in_diff) for item in violations] == [
        ("src/a.ts", "src/b.ts", False)
    ]
    assert in_both(violations[0].rule) == ("dependency", "dependência")


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


def test_importlinter_roots_are_empty_when_the_section_declares_none(tmp_path: Path) -> None:
    path = tmp_path / ".importlinter"
    path.write_text("[importlinter]\nroot_packages =\n", encoding="utf-8")

    assert _ini_roots(path) == []


def test_import_linter_edges_are_never_marked_in_diff() -> None:
    violations = parse_import_linter((RAW / "import-linter-forbidden.txt").read_text())

    assert [item.in_diff for item in violations] == [False]


def test_import_linter_reads_edges_painted_with_ansi_color() -> None:
    raw = "Layers\n------\n\n\x1b[31m- app.api -> app.domain\x1b[0m\n"

    assert [(item.origin, item.destination, item.rule) for item in parse_import_linter(raw)] == [
        ("app.api", "app.domain", "Layers")
    ]


def test_import_linter_edge_before_any_heading_keeps_the_default_rule() -> None:
    raw = "------\n- a.x -> a.y\n"

    assert [item.rule for item in parse_import_linter(raw)] == ["import-linter"]


def test_import_linter_heading_names_every_edge_below_it() -> None:
    raw = "Layers\n------\n\n------\n- a.x -> a.y\n- a.z -> a.y\n"

    assert [item.rule for item in parse_import_linter(raw)] == ["Layers", "Layers"]


def test_import_linter_sentence_ending_in_a_period_is_not_a_cycle_package() -> None:
    raw = (
        "Cycles\n------\n\n"
        "No cycles are allowed in app.\n"
        "Remove one dependency.\n"
        "- .right -> .left\n"
    )

    assert [(item.origin, item.destination) for item in parse_import_linter(raw)] == [
        ("app.right", "app.left")
    ]


def test_import_linter_cycle_line_without_final_period_keeps_the_previous_package() -> None:
    raw = (
        "Cycles\n------\n\n"
        "No cycles are allowed in app.\n"
        "No cycles are allowed in other\n"
        "- .right -> .left\n"
    )

    assert [(item.origin, item.destination) for item in parse_import_linter(raw)] == [
        ("app.right", "app.left")
    ]


def test_import_linter_repeated_edge_is_reported_once_and_later_edges_survive() -> None:
    raw = "Layers\n------\n\n- a.x -> a.y\n- a.x -> a.y\n- a.z -> a.y\n"

    assert [(item.origin, item.destination) for item in parse_import_linter(raw)] == [
        ("a.x", "a.y"),
        ("a.z", "a.y"),
    ]


def test_cruiser_cycle_skips_steps_without_a_name() -> None:
    raw = json.dumps(
        {
            "summary": {
                "violations": [
                    {
                        "rule": {"name": "no-circular", "severity": "error"},
                        "cycle": [{"name": "src/a.ts"}, {}, 5, "src/b.ts"],
                    }
                ]
            }
        }
    )

    assert [(item.origin, item.destination) for item in parse_dependency_cruiser(raw)] == [
        ("src/a.ts", "src/b.ts"),
        ("src/b.ts", "src/a.ts"),
    ]


def test_cruiser_rule_without_name_or_severity_uses_the_defaults() -> None:
    raw = json.dumps(
        {
            "summary": {
                "violations": [
                    {"from": "src/a.ts", "to": "src/b.ts", "rule": {"severity": "warn"}},
                    {"from": "src/c.ts", "to": "src/d.ts", "rule": {"name": "layers"}},
                ]
            }
        }
    )

    violations = parse_dependency_cruiser(raw)

    assert [(item.origin, item.destination) for item in violations] == [
        ("src/a.ts", "src/b.ts"),
        ("src/c.ts", "src/d.ts"),
    ]
    assert in_both(violations[0].rule) == ("dependency", "dependência")
    assert violations[1].rule == "layers"


def test_cruiser_reads_top_level_violations_when_summary_has_none() -> None:
    raw = json.dumps(
        {"summary": {}, "violations": [{"from": "src/a.ts", "to": "src/b.ts"}]}
    )

    assert [(item.origin, item.destination) for item in parse_dependency_cruiser(raw)] == [
        ("src/a.ts", "src/b.ts")
    ]


def test_cruiser_violation_without_a_destination_is_dropped() -> None:
    raw = json.dumps({"violations": [{"from": "src/a.ts"}]})

    assert parse_dependency_cruiser(raw) == []


def _linted(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["lint-imports"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_linter_clean_exit_returns_no_violation() -> None:
    assert _import_linter_violations(_linted(0, "Contracts: 1 kept, 0 broken.\n")) == []


def test_linter_broken_exit_with_edges_returns_them() -> None:
    raw = (RAW / "import-linter-forbidden.txt").read_text()

    violations = _import_linter_violations(_linted(1, raw))

    assert [(item.origin, item.destination) for item in violations] == [("app.api", "app.domain")]


def test_linter_broken_exit_without_contract_name_blames_import_linter() -> None:
    with pytest.raises(UnparsedBreak) as caught:
        _import_linter_violations(_linted(1, "nada útil\n"))

    assert render(caught.value.reason, "pt-BR") == "contrato quebrado: import-linter"


def test_linter_traceback_is_a_tool_failure_with_stderr_first() -> None:
    completed = _linted(1, "saída comum", "Traceback (most recent call last):\n  boom")

    with pytest.raises(ToolError, match="^Traceback \\(most recent call last\\): boom$"):
        _import_linter_violations(completed)


def test_linter_failure_falls_back_to_stdout_when_stderr_is_empty() -> None:
    with pytest.raises(ToolError, match="^Contract not configured correctly$"):
        _import_linter_violations(_linted(1, "Contract not configured correctly"))


def test_linter_could_not_import_without_an_edge_is_a_tool_failure() -> None:
    with pytest.raises(ToolError, match="^Could not import app$"):
        _import_linter_violations(_linted(1, "", "Could not import app"))


def test_linter_could_not_import_beside_an_edge_is_still_a_violation() -> None:
    raw = "Layers\n------\n\nCould not import app.extra\n- app.api -> app.domain\n"

    violations = _import_linter_violations(_linted(1, raw))

    assert [(item.origin, item.destination) for item in violations] == [("app.api", "app.domain")]


def test_linter_unexpected_exit_code_is_a_tool_failure() -> None:
    with pytest.raises(ToolError, match="^exit estranho$"):
        _import_linter_violations(_linted(2, "", "exit estranho"))


def test_tool_failure_text_is_one_line_capped_at_300_characters() -> None:
    assert _short("a\n\nb") == "a b"
    assert render(_short(" \n\t"), "pt-BR") == "ferramenta de dependência falhou"
    assert render(_short(" \n\t"), "en") == "dependency tool failed"
    assert _short("x" * 400) == "x" * 300


_LISTS = json.loads((RAW / "dependency-cruiser-violations-list.json").read_text())
_CRUISER_MISSING = (
    "dependency-cruiser: JSON without a violations list",
    "dependency-cruiser: JSON sem a lista violations",
)
_LINTER_UNRECOGNIZED = (
    "import-linter: output is not an empty report",
    "import-linter: saída não é um relatório vazio",
)
_KEPT_REPORT = (
    "---------\n"
    "Contracts\n"
    "---------\n"
    "\n"
    "Analyzed 3 files, 1 dependencies.\n"
    "---------------------------------\n"
    "\n"
    "Layers KEPT\n"
    "\n"
    "Contracts: 1 kept, 0 broken.\n"
)


def _cruiser_gate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, raw: str
) -> tuple[GateResult, int, dict[str, str], list[DepViolation]]:
    def measure(cwd: Path, config: Config, versions: dict[str, str]) -> list[DepViolation]:
        versions["dependency-cruiser"] = "18.5.0"
        return _cruise_violations(_linted(0, raw))

    monkeypatch.setattr("bob_quality.deps_gate._typescript_violations", measure)
    return run_deps_gate(tmp_path, Config(languages=("typescript",)))


def _linter_gate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stdout: str
) -> tuple[GateResult, int, dict[str, str], list[DepViolation]]:
    def measure(
        cwd: Path, config: Config, versions: dict[str, str], cycle_rule: str
    ) -> list[DepViolation]:
        versions["import-linter"] = "2.15"
        return _import_linter_violations(_linted(0, stdout))

    monkeypatch.setattr("bob_quality.deps_gate._python_violations", measure)
    return run_deps_gate(tmp_path, Config(languages=("python",)))


def test_cruiser_json_without_a_violations_list_exits_4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, code, _, rows = _cruiser_gate(
        monkeypatch, tmp_path, json.dumps(_LISTS["missing_list"])
    )

    assert (code, result.name, result.status, rows) == (4, "deps", "not_run", [])
    assert in_both(result.reason) == _CRUISER_MISSING


def test_cruiser_empty_violations_list_still_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, code, _, rows = _cruiser_gate(
        monkeypatch, tmp_path, json.dumps(_LISTS["empty_list"])
    )

    assert (code, result.name, result.status, result.reason, rows) == (
        0,
        "deps",
        "passed",
        None,
        [],
    )


def test_import_linter_exit_0_without_an_empty_report_exits_4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, code, _, rows = _linter_gate(
        monkeypatch, tmp_path, "Analyzed 3 files, 1 dependencies.\n"
    )

    assert (code, result.name, result.status, rows) == (4, "deps", "not_run", [])
    assert in_both(result.reason) == _LINTER_UNRECOGNIZED


def test_import_linter_recognized_empty_report_still_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, code, _, rows = _linter_gate(monkeypatch, tmp_path, _KEPT_REPORT)

    assert (code, result.name, result.status, result.reason, rows) == (
        0,
        "deps",
        "passed",
        None,
        [],
    )


def test_import_linter_colored_empty_report_still_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    colored = "\x1b[32mContracts: 1 kept, 0 broken.\x1b[0m\n"
    result, code, _, rows = _linter_gate(monkeypatch, tmp_path, colored)

    assert (code, result.name, result.status, result.reason, rows) == (
        0,
        "deps",
        "passed",
        None,
        [],
    )


def test_cruiser_invalid_json_reports_stderr_before_stdout() -> None:
    with pytest.raises(ToolError, match=r"^\{$"):
        _cruise_violations(_linted(1, "{", ""))
    with pytest.raises(ToolError, match="^broken stderr$"):
        _cruise_violations(_linted(1, "{", "broken stderr"))
