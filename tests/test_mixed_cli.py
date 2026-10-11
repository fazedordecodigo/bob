"""Um `bob check` num monorepo Py+TS grava um único relatório."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from helpers import SAFE_CHANGE, TS_SAFE_CHANGE, commit_on_branch, init_mixed_repo, run_bob

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "src/bob_quality/schemas/report_v1.json").read_text()
)


def test_mixed_python_and_typescript_share_one_report(tmp_path: Path) -> None:
    repo = init_mixed_repo(tmp_path / "repo")
    commit_on_branch(repo, "both", "src/app/safe.py", SAFE_CHANGE, "touch python add")
    commit_on_branch(repo, "both", "src/safe.ts", TS_SAFE_CHANGE, "touch typescript add")

    result = run_bob(repo, "check", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    reports = sorted(path.name for path in (repo / ".bob").glob("report.*"))

    assert result.returncode == 0, result.stderr
    assert reports == ["report.json", "report.md"]
    Draft202012Validator(SCHEMA).validate(payload)
    langs = {item["lang"] for item in payload["top_crap"]}
    assert langs == {"python", "typescript"}
    assert "src/app/safe.py" in markdown
    assert "src/safe.ts" in markdown
