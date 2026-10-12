"""Seam da CLI: `bob check --gates cognitive` num repo Python pequeno."""

import json
import os
import subprocess
import sys
from pathlib import Path

from helpers import commit_on_branch, commit_on_main, init_python_repo, run_bob


def _fifteen(name: str) -> str:
    lines = [f"def {name}(n):"]
    for number in range(1, 16):
        lines.append(f"    if n == {number}:")
        lines.append(f"        return {number}")
    lines.append("    return 0")
    lines.append("")
    return "\n".join(lines)


def test_changed_function_at_15_warns_and_an_unchanged_one_does_not(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/legacy.py", _fifteen("legacy"), "add unchanged legacy")
    commit_on_branch(repo, "hot", "src/app/edge.py", _fifteen("edge"), "add changed edge")

    result = run_bob(repo, "check", "--base", "main", "--gates", "cognitive")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    gate = next(item for item in payload["gates"] if item["name"] == "cognitive")
    rows = [(item["name"], item["score"], item["file"]) for item in payload["cognitive"]]

    assert result.returncode == 0, result.stderr
    assert payload["exit_code"] == 0
    assert gate["status"] == "warn"
    assert gate["reason"] == "1 function at or above the cognitive limit"
    assert rows == [("edge", 15, "src/app/edge.py")]
    assert payload["tool_versions"]["complexipy"] == "8.0.1"


def test_missing_complexipy_is_not_run(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "hot", "src/app/edge.py", _fifteen("edge"), "add changed edge")
    shadow = tmp_path / "shadow"
    shadow.mkdir()
    (shadow / "complexipy.py").write_text("raise ImportError('missing')\n")
    env = {key: value for key, value in os.environ.items() if key != "BOB_LANG"}
    env["PYTHONPATH"] = str(shadow)
    env["BOB_LANG"] = "pt-BR"

    result = subprocess.run(
        [sys.executable, "-m", "bob_quality", "check", "--base", "main", "--gates", "cognitive"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    gate = next(item for item in payload["gates"] if item["name"] == "cognitive")

    assert result.returncode == 0, result.stderr
    assert payload["exit_code"] == 0
    assert gate["status"] == "not_run"
    assert gate["reason"] == "complexipy is not installed"
    assert payload["cognitive"] == []
    assert "complexipy" not in payload["tool_versions"]
    assert "complexipy não está instalado" in markdown
