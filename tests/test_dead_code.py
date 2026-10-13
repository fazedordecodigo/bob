from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from bob_quality.check import _Measured, _record_dead
from bob_quality.config import Config
from bob_quality.dead_code import (
    Dark,
    MeasuredPython,
    MeasuredTypeScript,
    Quiet,
    _knip_half,
    _knip_prefix,
    _parsed_knip,
    _parsed_vulture,
    _spawn,
    _vulture_half,
    definition_is_new,
    knip_command,
    settle,
    vulture_command,
)
from bob_quality.tools import ToolError
from bob_quality.diff import function_is_changed, line_is_changed
from bob_quality.messages import msg, render
from bob_quality.models import (
    DeadSection,
    GateResult,
    LedgerRow,
    Mutant,
    PythonDead,
    Report,
    TypeScriptDead,
)
from bob_quality.report import to_json, to_markdown
from bob_quality.waivers import Waiver, apply_waivers

ORPHAN = PythonDead("src/app/orphan.py", 3, "orphan", "function", 60)
CHANGED = {"src/app/orphan.py": {3}}


def _waiver(identifier: str, reason: str = "loaded by a plugin") -> Waiver:
    return Waiver(id=identifier, reason=reason, author="Ada", date="2026-10-12")


def test_definition_line_warns_and_a_body_edit_passes() -> None:
    body = {"src/app/orphan.py": {4}}
    half = MeasuredPython((ORPHAN,), "2.16")

    missed = settle(half, Quiet(), body, Config(), [])
    hit = settle(half, Quiet(), CHANGED, Config(), [])

    assert function_is_changed("src/app/orphan.py", 3, 8, body) is True
    assert definition_is_new(ORPHAN, body) is False
    assert missed.status == "passed"
    assert missed.reason is None
    assert missed.section.rows == ()
    assert hit.status == "warn"
    assert hit.as_gate() == GateResult("dead_code", "warn", msg("dead.one", count=1))
    assert render(hit.reason, "en") == "1 unused symbol in the diff"
    assert hit.section.rows == (LedgerRow(ORPHAN, None),)


def test_definition_is_new_is_membership_of_that_line() -> None:
    assert line_is_changed("src/app/orphan.py", 3, CHANGED) is True
    assert line_is_changed("src/app/orphan.py", 4, CHANGED) is False
    assert line_is_changed("src/app/other.py", 3, CHANGED) is False
    assert definition_is_new(ORPHAN, CHANGED) is True
    assert definition_is_new(ORPHAN, {"src/app/orphan.py": {4}}) is False


def test_out_of_diff_symbols_are_dropped() -> None:
    other = PythonDead("src/app/keep.py", 1, "keep", "function", 80)
    advisory = settle(
        MeasuredPython((other, ORPHAN), "2.16"),
        Quiet(),
        CHANGED,
        Config(),
        [],
    )

    assert advisory.status == "warn"
    assert [row.symbol for row in advisory.section.rows] == [ORPHAN]


def test_symbols_outside_include_or_under_exclude_are_dropped() -> None:
    excluded = PythonDead("src/tests/orphan.py", 3, "orphan", "function", 80)
    outside = PythonDead("lib/orphan.py", 3, "orphan", "function", 90)
    absolute = PythonDead("/tmp/orphan.py", 1, "orphan", "function", 60)
    changed = {
        "src/app/orphan.py": {3},
        "src/tests/orphan.py": {3},
        "lib/orphan.py": {3},
        "/tmp/orphan.py": {1},
    }

    advisory = settle(
        MeasuredPython((excluded, outside, absolute, ORPHAN), "2.16"),
        Quiet(),
        changed,
        Config(),
        [],
    )

    assert advisory.section.rows == (LedgerRow(ORPHAN, None),)
    assert render(advisory.reason, "en") == "1 unused symbol in the diff"


def test_a_dead_waiver_removes_that_symbol_from_the_warn_set() -> None:
    exact = _waiver("dead:src/app/orphan.py:3:orphan")
    other = _waiver("dead:src/app/orphan.py:4:orphan")
    half = MeasuredPython((ORPHAN,), "2.16")

    waived = settle(half, Quiet(), CHANGED, Config(), [exact])
    still = settle(half, Quiet(), CHANGED, Config(), [other])

    assert waived.status == "passed"
    assert waived.reason is None
    assert waived.section.rows == (LedgerRow(ORPHAN, "dead:src/app/orphan.py:3:orphan"),)
    assert still.status == "warn"
    assert still.section.rows == (LedgerRow(ORPHAN, None),)


def test_a_dead_waiver_does_not_waive_a_mutant() -> None:
    mutant = Mutant(
        id="app.keep_x__mutmut_1",
        function="keep",
        file="src/app/orphan.py",
        line=3,
        operator="AOR",
        status="survived",
    )
    dead = _waiver("dead:src/app/orphan.py:3:orphan")
    matched = _waiver("app.keep_x__mutmut_1", "equivalent")

    ignored = apply_waivers([mutant], [dead])
    applied = apply_waivers([mutant], [matched])

    assert ignored == [mutant]
    assert applied[0].waiver == "equivalent"
    assert applied[0].id == "app.keep_x__mutmut_1"
    assert applied[0].status == "survived"


def test_record_dead_leaves_a_prior_exit_code_alone() -> None:
    advisory = settle(MeasuredPython((ORPHAN,), "2.16"), Quiet(), CHANGED, Config(), [])
    clean = _Measured()
    _record_dead(clean, advisory)
    prior = _Measured()
    prior.exit_code = 3
    _record_dead(prior, advisory)

    assert advisory.status == "warn"
    assert clean.exit_code == 0
    assert clean.gates == [GateResult("dead_code", "warn", msg("dead.one", count=1))]
    assert clean.dead_code == DeadSection((LedgerRow(ORPHAN, None),))
    assert clean.versions == {"vulture": "2.16"}
    assert prior.exit_code == 3
    assert prior.gates[-1].name == "dead_code"
    assert prior.gates[-1].status == "warn"
    assert prior.dead_code is not None
    assert prior.dead_code.rows[0].symbol == ORPHAN


def test_a_clean_ledger_stays_passed_when_the_other_language_is_dark() -> None:
    advisory = settle(
        MeasuredPython((), "2.16"),
        Dark(msg("dead.node_missing")),
        {},
        Config(),
        [],
    )

    assert advisory.status == "passed"
    assert advisory.section.rows == ()
    assert advisory.versions == (("vulture", "2.16"),)
    assert render(advisory.reason, "en") == "Node missing: install Node.js to run knip"
    assert render(advisory.reason, "pt-BR") == "Node ausente: instale o Node.js para rodar o knip"


def test_an_unwaived_symbol_warns_and_keeps_the_dark_reason() -> None:
    advisory = settle(
        MeasuredPython((ORPHAN,), "2.16"),
        Dark(msg("tool.missing", tool="knip")),
        CHANGED,
        Config(),
        [],
    )

    assert advisory.status == "warn"
    assert render(advisory.reason, "en") == (
        "1 unused symbol in the diff; missing tool: knip"
    )


def test_no_measurement_is_not_run() -> None:
    both_quiet = settle(Quiet(), Quiet(), {}, Config(), [])
    both_dark = settle(
        Dark(msg("tool.missing", tool="vulture")),
        Dark(msg("dead.node_missing")),
        {},
        Config(),
        [],
    )
    only_python_dark = settle(
        Dark(msg("tool.missing", tool="vulture")),
        Quiet(),
        {},
        Config(),
        [],
    )

    assert both_quiet.status == "not_run"
    assert both_quiet.section.rows == ()
    assert both_quiet.versions == ()
    assert both_quiet.as_gate() == GateResult("dead_code", "not_run", msg("dead.no_language"))
    assert render(both_quiet.reason, "en") == "dead_code: no language selected"
    assert both_dark.status == "not_run"
    assert both_dark.section == DeadSection()
    assert render(both_dark.reason, "en") == (
        "missing tool: vulture; Node missing: install Node.js to run knip"
    )
    assert only_python_dark.status == "not_run"
    assert render(only_python_dark.reason, "en") == "missing tool: vulture"
    assert only_python_dark.versions == ()


def test_two_clean_measurements_pass_without_a_reason() -> None:
    advisory = settle(
        MeasuredPython((), "2.16"),
        MeasuredTypeScript((), "6.41.0"),
        {},
        Config(),
        [],
    )

    assert advisory.status == "passed"
    assert advisory.reason is None
    assert advisory.section.rows == ()
    assert advisory.versions == (("vulture", "2.16"), ("knip", "6.41.0"))


def test_two_unwaived_symbols_use_the_plural_and_sort() -> None:
    first = TypeScriptDead("src/a.ts", 4, "a", "export")
    same = PythonDead("src/a.ts", 4, "a", "function", 60)
    later = PythonDead("src/b.py", 2, "b", "variable", 90)

    advisory = settle(
        MeasuredPython((later, same), "2.16"),
        MeasuredTypeScript((first,), "6.41.0"),
        {"src/a.ts": {4}, "src/b.py": {2}},
        Config(),
        [],
    )

    assert advisory.status == "warn"
    assert render(advisory.reason, "en") == "3 unused symbols in the diff"
    assert render(advisory.reason, "pt-BR") == "3 símbolos mortos no diff"
    assert advisory.versions == (("vulture", "2.16"), ("knip", "6.41.0"))
    assert [row.symbol for row in advisory.section.rows] == [first, same, later]


def test_an_empty_section_stays_truthy() -> None:
    assert DeadSection().rows == ()
    assert bool(DeadSection()) is True


def test_vulture_argv_omits_min_confidence_until_the_value_is_present() -> None:
    absent = vulture_command(Config(), ["src"])
    zero = vulture_command(Config(dead_code_min_confidence=0), ["src", "lib"])

    assert absent == [sys.executable, "-m", "vulture", "src"]
    assert "--min-confidence" not in absent
    assert zero == [
        sys.executable,
        "-m",
        "vulture",
        "src",
        "lib",
        "--min-confidence",
        "0",
    ]


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "src" / "bob_quality" / "schemas" / "report_v1.json").read_text())


def _plain() -> Report:
    return Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-12T00:00:00+00:00",
        tool_versions={},
        gates=[GateResult("crap", "passed", None)],
        focus=[],
        top_crap=[],
        reproduce="bob check",
        exit_code=0,
    )


def test_json_omits_dead_code_until_the_gate_runs() -> None:
    report = _plain()

    assert report.dead_code is None
    assert "dead_code" not in to_json(report)
    assert "## Dead code" not in to_markdown(report, "en")
    assert "## Código morto" not in to_markdown(report, "pt-BR")
    Draft202012Validator(SCHEMA).validate(to_json(report))


def test_the_dead_section_sits_between_untested_mutants_and_reproduce() -> None:
    symbol = TypeScriptDead("src/app/orphan.ts", 3, "orphan", "export")
    report = Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-12T00:00:00+00:00",
        tool_versions={"vulture": "2.16", "knip": "6.41.0"},
        gates=[GateResult("dead_code", "warn", msg("dead.many", count=2))],
        focus=[],
        top_crap=[],
        reproduce="bob check --gates dead_code",
        exit_code=0,
        mutation={"no_coverage": {"total": 0, "functions": []}},
        dead_code=DeadSection(
            (
                LedgerRow(ORPHAN, "dead:src/app/orphan.py:3:orphan"),
                LedgerRow(symbol, None),
            )
        ),
    )

    english = to_markdown(report, "en")
    portuguese = to_markdown(report, "pt-BR")
    block = (
        "## Mutants without tests\n\n"
        "No mutants without tests.\n\n"
        "## Dead code\n\n"
        "- `src/app/orphan.py:3` function `orphan` 60% "
        "waiver `dead:src/app/orphan.py:3:orphan`\n"
        "- `src/app/orphan.ts:3` export `orphan`\n\n"
        "## How to reproduce"
    )
    assert block in english
    assert (
        "## Mutantes sem teste\n\n"
        "Nenhum mutante sem teste.\n\n"
        "## Código morto\n\n"
        "- `src/app/orphan.py:3` function `orphan` 60% "
        "waiver `dead:src/app/orphan.py:3:orphan`\n"
        "- `src/app/orphan.ts:3` export `orphan`\n\n"
        "## Como reproduzir"
    ) in portuguese
    payload = to_json(report)
    Draft202012Validator(SCHEMA).validate(payload)
    assert payload["exit_code"] == 0
    assert payload["gates"] == [
        {"name": "dead_code", "status": "warn", "reason": "2 unused symbols in the diff"}
    ]
    assert payload["dead_code"] == {
        "symbols": [
            {
                "file": "src/app/orphan.py",
                "line": 3,
                "name": "orphan",
                "kind": "function",
                "language": "python",
                "confidence": 60,
                "waiver": "dead:src/app/orphan.py:3:orphan",
            },
            {
                "file": "src/app/orphan.ts",
                "line": 3,
                "name": "orphan",
                "kind": "export",
                "language": "typescript",
                "confidence": None,
                "waiver": None,
            },
        ]
    }


def test_not_run_and_a_clean_skip_render_the_reason() -> None:
    skipped = Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-12T00:00:00+00:00",
        tool_versions={},
        gates=[GateResult("dead_code", "not_run", msg("tool.missing", tool="vulture"))],
        focus=[],
        top_crap=[],
        reproduce="bob check --gates dead_code",
        dead_code=DeadSection(),
    )
    clean = Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-12T00:00:00+00:00",
        tool_versions={"vulture": "2.16"},
        gates=[GateResult("dead_code", "passed", msg("dead.node_missing"))],
        focus=[],
        top_crap=[],
        reproduce="bob check --gates dead_code",
        dead_code=DeadSection(),
    )

    assert "Not run (missing tool: vulture)." in to_markdown(skipped, "en")
    assert "Não executado (ferramenta ausente: vulture)." in to_markdown(skipped, "pt-BR")
    assert "No unused symbol" not in to_markdown(skipped, "en")
    assert (
        "No unused symbol in the diff.\n"
        "Node missing: install Node.js to run knip"
    ) in to_markdown(clean, "en")
    assert to_json(skipped)["dead_code"] == {"symbols": []}
    assert to_json(skipped)["gates"][0]["reason"] == "missing tool: vulture"


def test_knip_argv_never_receives_min_confidence(tmp_path: Path) -> None:
    command = knip_command(tmp_path)

    assert command == [
        "npx",
        "--no-install",
        "--prefix",
        str(tmp_path),
        "knip",
        "--reporter",
        "json",
        "--no-progress",
    ]


def _completed(code: int, stdout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], code, stdout, "")


def test_vulture_half_names_vulture_when_the_version_is_gone(monkeypatch) -> None:
    monkeypatch.setattr("bob_quality.dead_code._vulture_version", lambda: None)

    found = _vulture_half(_completed(3, "src/a.py:1: unused function 'a' (60% confidence)"), Path("."))

    assert isinstance(found, Dark)
    assert render(found.reason, "en") == "missing tool: vulture"


def test_a_bad_vulture_line_keeps_the_parser_reason(tmp_path: Path) -> None:
    found = _parsed_vulture("not a vulture line", tmp_path, "2.16")

    assert isinstance(found, Dark)
    assert render(found.reason, "en") == "vulture: output could not be parsed"


def test_knip_exit_zero_with_json_is_measured(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("bob_quality.dead_code.installed_npm_version", lambda _prefix, _name: "6.41.0")

    found = _knip_half(_completed(0, '{"issues":[]}'), tmp_path, tmp_path)

    assert isinstance(found, MeasuredTypeScript)
    assert found.symbols == ()
    assert found.version == "6.41.0"


def test_blank_knip_stdout_does_not_reach_the_parser(tmp_path: Path, monkeypatch) -> None:
    def explode(*_args: object) -> object:
        raise AssertionError("parser")

    monkeypatch.setattr("bob_quality.dead_code._parsed_knip", explode)
    found = _knip_half(_completed(0, " \n"), tmp_path, tmp_path)

    assert isinstance(found, Dark)
    assert render(found.reason, "en") == "knip: output could not be parsed"


def test_a_bad_knip_document_keeps_the_parser_reason(tmp_path: Path) -> None:
    found = _parsed_knip("{", tmp_path)

    assert isinstance(found, Dark)
    assert render(found.reason, "en") == "knip: output could not be parsed"


def test_a_knip_version_failure_keeps_the_tool_reason(tmp_path: Path, monkeypatch) -> None:
    def broken(_prefix: Path, _name: str) -> str:
        raise ToolError(msg("tool.missing", tool="knip"))

    monkeypatch.setattr("bob_quality.dead_code.installed_npm_version", broken)
    found = _knip_half(_completed(0, '{"issues":[]}'), tmp_path, tmp_path)

    assert isinstance(found, Dark)
    assert render(found.reason, "en") == "missing tool: knip"


def test_an_npm_prefix_failure_keeps_its_reason(monkeypatch) -> None:
    def broken() -> Path:
        raise ToolError(msg("dead.node_missing"))

    monkeypatch.setattr("bob_quality.dead_code.node_missing_message", lambda: None)
    monkeypatch.setattr("bob_quality.dead_code.npm_prefix", broken)
    found = _knip_prefix()

    assert isinstance(found, Dark)
    assert render(found.reason, "en") == "Node missing: install Node.js to run knip"


def test_a_missing_knip_package_names_knip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("bob_quality.dead_code.node_missing_message", lambda: None)
    monkeypatch.setattr("bob_quality.dead_code.npm_prefix", lambda: tmp_path)
    found = _knip_prefix()

    assert isinstance(found, Dark)
    assert render(found.reason, "en") == "missing tool: knip"


def test_spawn_exports_the_prefix_bin_and_hides_pytest(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, dict[str, str]] = {}

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        env = kwargs["env"]
        assert isinstance(env, dict)
        captured["env"] = env
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr("bob_quality.dead_code.subprocess.run", fake_run)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "dead")
    monkeypatch.setenv("KEEP_ME", "1")
    _spawn(tmp_path, ["knip"], tmp_path)

    env = captured["env"]
    bindir = str(tmp_path / "node_modules" / ".bin")
    assert env["PATH"].startswith(bindir + os.pathsep)
    assert "PYTEST_CURRENT_TEST" not in env
    assert env["KEEP_ME"] == "1"


def test_an_empty_dead_section_with_no_reason_is_one_sentence() -> None:
    report = _plain()
    report.gates = [GateResult("dead_code", "passed", None)]
    report.dead_code = DeadSection()

    assert to_markdown(report, "en").count("No unused symbol in the diff.") == 1
