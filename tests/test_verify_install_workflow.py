"""Workflow verify-install: harness no Linux x64, sem segredo e sem escrita."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "verify-install.yml"
CI = ROOT / ".github" / "workflows" / "ci.yml"
INSTALL = ROOT / "scripts" / "install.sh"
USES = re.compile(r"^\s*(- )?uses: [\w./-]+@[0-9a-f]{40} # v\S+$")
UPLOAD = "cf430e030ddbb5b0abf93d22962f4752f3646cd9"
HARNESS = "run: sh scripts/verify-install.sh"


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _sha(text: str, action: str) -> str:
    found = re.findall(rf"{re.escape(action)}@([0-9a-f]{{40}})", text)
    assert found
    assert len(set(found)) == 1
    return found[0]


def test_workflow_runs_the_harness_on_prs_and_main() -> None:
    text = _text()
    assert "pull_request:" in text
    assert "branches: [main]" in text
    assert "runs-on: ubuntu-latest" in text
    assert "timeout-minutes: 20" in text
    assert any(line.strip() == HARNESS for line in text.splitlines())


def test_workflow_pins_the_same_actions_as_ci() -> None:
    text = _text()
    ci = CI.read_text(encoding="utf-8")
    uses_lines = [line for line in text.splitlines() if "uses:" in line]
    assert uses_lines
    for line in uses_lines:
        assert USES.fullmatch(line)
    for action in (
        "actions/checkout",
        "actions/setup-python",
        "actions/setup-node",
    ):
        assert _sha(text, action) == _sha(ci, action)
    assert _sha(text, "actions/upload-artifact") == UPLOAD


def test_workflow_node_matches_install_sh() -> None:
    script = INSTALL.read_text(encoding="utf-8")
    match = re.search(r"^NODE_FLOOR='([^']*)'$", script, re.M)
    assert match is not None
    floor = match.group(1)
    versions = re.findall(r'node-version:\s*"([^"]*)"', _text())
    assert versions == [floor]


def test_workflow_has_no_secrets_and_reads_only() -> None:
    text = _text()
    for forbidden in ("secrets.", "sudo", "pull_request_target", ": write"):
        assert forbidden not in text
    assert "contents: read" in text
