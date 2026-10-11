"""Relatório `.bob/` (schema v1 + seções exigidas pela issue #1)."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from helpers import RISKY_SOURCE, commit_on_branch, init_python_repo, run_bob

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "src/bob_quality/schemas/report_v1.json").read_text()
)


def test_check_report_matches_schema_v1_and_required_sections(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "risky",
        "src/app/risky.py",
        RISKY_SOURCE,
        "add untested messy function",
    )

    result = run_bob(repo, "check", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 1
    Draft202012Validator(SCHEMA).validate(payload)
    assert payload["schema_version"] == 1
    assert payload["top_crap"][0]["name"] == "messy"
    assert payload["top_crap"][0]["crap"] > 10
    assert payload["focus"][0]["file"] == "src/app/risky.py"
    assert "bob check --base main" in payload["reproduce"]
    assert "## Verdict" in markdown
    assert "## Where to focus the review" in markdown
    assert "## Top 5 functions by CRAP" in markdown
    assert "## How to reproduce" in markdown
    assert "src/app/risky.py" in markdown


def test_crap_command_writes_the_same_report_files(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "risky",
        "src/app/risky.py",
        RISKY_SOURCE,
        "add untested messy function",
    )

    result = run_bob(repo, "crap", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert result.returncode == 1
    Draft202012Validator(SCHEMA).validate(payload)
    assert any(gate["name"] == "crap" for gate in payload["gates"])
    assert "bob crap --base main" in payload["reproduce"]
