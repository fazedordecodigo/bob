"""Regra da #27 no gate deps, ainda sem OK do Emerson.

Sem Node num repo misto, o Python é medido e o TypeScript aparece pulado,
com aviso. O ponto único é `bob_quality.deps_typescript_skip`.
"""

import json
import os
import shutil
from pathlib import Path

from bob_quality.cli import main

from helpers import SAFE_CHANGE, commit_on_branch, init_mixed_repo, init_ts_repo


def test_mixed_repo_without_node_measures_python_deps_and_skips_typescript(
    tmp_path: Path,
) -> None:
    repo = init_mixed_repo(tmp_path / "repo")
    commit_on_branch(repo, "touch", "src/app/safe.py", SAFE_CHANGE, "touch python")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    os.symlink(shutil.which("git"), bindir / "git")
    previous_path = os.environ.get("PATH", "")
    previous_cwd = os.getcwd()
    os.environ["PATH"] = str(bindir)
    os.chdir(repo)
    try:
        code = main(["deps", "--base", "main"])
    finally:
        os.environ["PATH"] = previous_path
        os.chdir(previous_cwd)

    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")

    assert code == 0, markdown
    assert deps["status"] == "warn"
    assert deps["reason"].startswith("TypeScript pulado:")
    assert "Node ausente" in deps["reason"]
    assert "import-linter" in payload["tool_versions"]
    assert "⚠️ `deps`: aviso (TypeScript pulado:" in markdown


def test_mixed_repo_without_node_still_fails_a_new_python_dependency_violation(
    tmp_path: Path,
) -> None:
    repo = init_mixed_repo(tmp_path / "repo")
    left = "from app.right import RIGHT\n\nLEFT = RIGHT\n"
    right = "from app.left import LEFT\n\nRIGHT = LEFT\n"
    commit_on_branch(repo, "cycle", "src/app/left.py", left, "add left")
    commit_on_branch(repo, "cycle", "src/app/right.py", right, "add right")

    code, payload, markdown = _deps_without_node(repo)

    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")
    assert code == 1, markdown
    assert deps["status"] == "failed"
    assert "app.right → app.left" in deps["reason"]
    assert "TypeScript pulado:" in deps["reason"]
    assert "❌ `deps`" in markdown


def test_typescript_repo_without_node_keeps_deps_exit_4(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(repo, "touch", "src/safe.ts", "export const add = 1;\n", "touch")

    code, payload, markdown = _deps_without_node(repo)

    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")
    assert code == 4, markdown
    assert deps["status"] == "not_run"
    assert "Node ausente" in deps["reason"]
    assert "TypeScript pulado" not in deps["reason"]


def _deps_without_node(repo: Path) -> tuple[int, dict[str, object], str]:
    bindir = repo.parent / "bin"
    bindir.mkdir()
    os.symlink(shutil.which("git"), bindir / "git")
    previous_path = os.environ.get("PATH", "")
    previous_cwd = os.getcwd()
    os.environ["PATH"] = str(bindir)
    os.chdir(repo)
    try:
        code = main(["deps", "--base", "main"])
    finally:
        os.environ["PATH"] = previous_path
        os.chdir(previous_cwd)
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    return code, payload, markdown
