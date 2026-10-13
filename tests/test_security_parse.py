from __future__ import annotations

import json
from pathlib import Path

import pytest
from helpers import in_both

from bob_quality.adapters.bandit import BanditParseError, parse_bandit
from bob_quality.adapters.semgrep import SemgrepParseError, parse_semgrep
from bob_quality.security_scanners import _BANDIT_EXCLUDE

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "tests" / "fixtures" / "raw"


def test_parse_bandit_reads_the_captured_results() -> None:
    findings = parse_bandit((RAW / "bandit-1.9.4.json").read_text(), Path("/tmp/bob-sec-probe"))

    assert [
        (item.file, item.rule, item.severity, item.line, item.end_line, item.tool)
        for item in findings
    ] == [
        ("src/confidence.py", "B609", "HIGH", 4, 4, "bandit"),
        ("src/confidence.py", "B605", "LOW", 4, 4, "bandit"),
        ("src/confidence.py", "B607", "LOW", 4, 4, "bandit"),
        ("src/high.py", "B404", "LOW", 1, 1, "bandit"),
        ("src/high.py", "B602", "HIGH", 4, 4, "bandit"),
        ("src/medium.py", "B403", "LOW", 1, 1, "bandit"),
        ("src/medium.py", "B301", "MEDIUM", 4, 4, "bandit"),
        ("src/off.py", "B404", "LOW", 1, 1, "bandit"),
        ("src/off.py", "B607", "LOW", 4, 4, "bandit"),
        ("src/off.py", "B602", "LOW", 4, 4, "bandit"),
    ]


def test_parse_bandit_rejects_a_document_without_results() -> None:
    with pytest.raises(BanditParseError) as caught:
        parse_bandit("{", Path("."))

    assert in_both(caught.value) == ("bandit: invalid JSON", "bandit: JSON inválido")


def test_parse_semgrep_reads_the_captured_result_and_ignores_errors() -> None:
    payload = json.loads((RAW / "semgrep-1.180.0.json").read_text())
    payload["errors"] = [{"severity": "error", "message": "not a finding"}]

    findings = parse_semgrep(json.dumps(payload), Path("/tmp/bob-sec-probe"))

    assert len(findings) == 1
    assert findings[0].tool == "semgrep"
    assert findings[0].rule == "semgrep.dangerous-eval"
    assert findings[0].file == "src/fresh.ts"
    assert findings[0].line == 2
    assert findings[0].end_line == 2
    assert findings[0].severity == "ERROR"


def test_parse_semgrep_drops_experiment_and_rejects_an_unknown_severity() -> None:
    payload = json.loads((RAW / "semgrep-1.180.0.json").read_text())
    payload["results"][0]["extra"]["severity"] = "EXPERIMENT"
    assert parse_semgrep(json.dumps(payload), Path(".")) == ()

    payload["results"][0]["extra"]["severity"] = "INVENTORY"
    assert parse_semgrep(json.dumps(payload), Path(".")) == ()

    payload["results"][0]["extra"]["severity"] = "NOPE"
    with pytest.raises(SemgrepParseError) as caught:
        parse_semgrep(json.dumps(payload), Path("."))

    assert in_both(caught.value) == ("semgrep: malformed result", "semgrep: resultado fora do formato")


def test_parse_semgrep_drops_a_path_outside_the_scan_root() -> None:
    payload = json.loads((RAW / "semgrep-1.180.0.json").read_text())
    payload["results"][0]["path"] = "/etc/passwd"

    assert parse_semgrep(json.dumps(payload), Path("/tmp/bob-sec-probe")) == ()


def test_bandit_exclude_matches_the_pinned_constant() -> None:
    from bandit.core.constants import EXCLUDE

    assert tuple(EXCLUDE) == _BANDIT_EXCLUDE
