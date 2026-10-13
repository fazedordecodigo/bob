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


def test_parse_bandit_keeps_paths_inside_the_root_and_drops_the_rest(tmp_path: Path) -> None:
    inside = _bandit_item()
    inside["filename"] = str(tmp_path / "src" / "high.py")
    kept = parse_bandit(_document(inside), tmp_path)
    assert kept[0].file == "src/high.py"

    prefixed = _bandit_item()
    prefixed["filename"] = "./src/high.py"
    assert parse_bandit(_document(prefixed), tmp_path)[0].file == "src/high.py"

    empty = _bandit_item()
    empty["filename"] = ""
    assert parse_bandit(_document(empty), tmp_path) == ()

    outside = _bandit_item()
    outside["filename"] = "/etc/passwd"
    assert parse_bandit(_document(outside), tmp_path) == ()

    escaped = _bandit_item()
    escaped["filename"] = "../secret.py"
    assert parse_bandit(_document(escaped), tmp_path) == ()

    root = _bandit_item()
    root["filename"] = str(tmp_path)
    assert parse_bandit(_document(root), tmp_path) == ()


def test_parse_bandit_rejects_a_broken_span_and_uses_an_empty_range() -> None:
    missing = _bandit_item()
    del missing["line_number"]
    with pytest.raises(BanditParseError) as caught:
        parse_bandit(_document(missing), Path("."))
    assert in_both(caught.value) == ("bandit: malformed result", "bandit: resultado fora do formato")

    broken = _bandit_item()
    broken["line_range"] = ["nope"]
    with pytest.raises(BanditParseError):
        parse_bandit(_document(broken), Path("."))

    blank = _bandit_item()
    blank["line_range"] = None
    with pytest.raises(BanditParseError):
        parse_bandit(_document(blank), Path("."))

    empty = _bandit_item()
    empty["line_range"] = []
    found = parse_bandit(_document(empty), Path("."))
    assert (found[0].line, found[0].end_line) == (4, 4)

    odd = _bandit_item()
    del odd["test_id"]
    with pytest.raises(BanditParseError):
        parse_bandit(_document(odd), Path("."))

    labeled = _bandit_item()
    labeled["issue_severity"] = "NOPE"
    with pytest.raises(BanditParseError):
        parse_bandit(_document(labeled), Path("."))

    with pytest.raises(BanditParseError):
        parse_bandit(json.dumps({"results": [1]}), Path("."))


def test_parse_semgrep_rejects_a_malformed_result_and_a_broken_span() -> None:
    payload = json.loads((RAW / "semgrep-1.180.0.json").read_text())
    payload["results"] = ["nope"]
    with pytest.raises(SemgrepParseError) as caught:
        parse_semgrep(json.dumps(payload), Path("."))
    assert in_both(caught.value) == (
        "semgrep: malformed result",
        "semgrep: resultado fora do formato",
    )

    payload = json.loads((RAW / "semgrep-1.180.0.json").read_text())
    del payload["results"][0]["check_id"]
    with pytest.raises(SemgrepParseError):
        parse_semgrep(json.dumps(payload), Path("."))

    payload = json.loads((RAW / "semgrep-1.180.0.json").read_text())
    payload["results"][0]["extra"]["severity"] = 1
    with pytest.raises(SemgrepParseError):
        parse_semgrep(json.dumps(payload), Path("."))

    payload = json.loads((RAW / "semgrep-1.180.0.json").read_text())
    del payload["results"][0]["start"]
    with pytest.raises(SemgrepParseError):
        parse_semgrep(json.dumps(payload), Path("."))


def _bandit_item() -> dict[str, object]:
    payload = json.loads((RAW / "bandit-1.9.4.json").read_text())
    item = payload["results"][0]
    assert isinstance(item, dict)
    return item


def _document(item: dict[str, object]) -> str:
    return json.dumps({"results": [item]})


def test_bandit_exclude_matches_the_pinned_constant() -> None:
    from bandit.core.constants import EXCLUDE

    assert tuple(EXCLUDE) == _BANDIT_EXCLUDE
