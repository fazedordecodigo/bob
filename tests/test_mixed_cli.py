"""Um `bob check` num monorepo Py+TS grava um único relatório."""

import json
import os
import shutil
import subprocess
import sys
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


def test_mixed_repo_without_node_measures_python_and_skips_typescript(
    tmp_path: Path,
) -> None:
    """Sem Node, o Python segue no relatório e o TypeScript aparece pulado, com aviso.

    O exit code é 0: o aviso não derruba o check. Exit 4 fica para quando a
    ferramenta ausente impede a medição (repositório só TypeScript).
    """
    repo = init_mixed_repo(tmp_path / "repo")
    commit_on_branch(repo, "both", "src/app/safe.py", SAFE_CHANGE, "touch python add")
    commit_on_branch(repo, "both", "src/safe.ts", TS_SAFE_CHANGE, "touch typescript add")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    os.symlink(shutil.which("git"), bindir / "git")
    env = {**os.environ, "PATH": str(bindir)}

    result = subprocess.run(
        [sys.executable, "-m", "bob_quality", "check", "--base", "main", "--gates", "crap"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    crap = next(gate for gate in payload["gates"] if gate["name"] == "crap")
    add = next(item for item in payload["top_crap"] if item["name"] == "add")

    assert result.returncode == 0, result.stderr
    assert payload["exit_code"] == 0
    Draft202012Validator(SCHEMA).validate(payload)
    assert crap["status"] == "warn"
    assert (
        crap["reason"]
        == "TypeScript pulado: Node ausente: instale Node.js para medir TypeScript (c8 e vitest via npx)"
    )
    assert add["lang"] == "python"
    assert add["cc"] == 1
    assert add["coverage"] == 1.0
    assert add["crap"] == 1.0
    assert {item["lang"] for item in payload["top_crap"]} == {"python"}
    assert "⚠️ `crap`: aviso (TypeScript pulado:" in markdown
    assert "src/app/safe.py" in markdown
    assert "src/safe.ts" not in markdown
