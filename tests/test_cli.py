"""Comportamento da CLI `bob` sobre o repo-fixture Python (seam principal)."""

import json
import os
import subprocess
import sys
from pathlib import Path

from helpers import (
    MESSY_WITHOUT_RETURN_2,
    RISKY_SOURCE,
    RISKY_WITH_CONSTANT,
    SAFE_CHANGE,
    commit_on_branch,
    commit_on_main,
    init_python_repo,
    run_bob,
)


def test_check_fails_when_changed_function_exceeds_crap_10(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "risky",
        "src/app/risky.py",
        RISKY_SOURCE,
        "add untested messy function",
    )

    result = run_bob(repo, "check", "--base", "main")

    assert result.returncode == 1
    assert (repo / ".bob" / "report.md").is_file()
    assert (repo / ".bob" / "report.json").is_file()


def test_check_passes_when_changed_function_stays_under_crap_10(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "safe-change",
        "src/app/safe.py",
        SAFE_CHANGE,
        "touch tested add",
    )

    result = run_bob(repo, "check", "--base", "main")

    assert result.returncode == 0
    assert (repo / ".bob" / "report.md").is_file()


def test_check_does_not_fail_on_old_debt_outside_the_diff(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/legacy.py", RISKY_SOURCE, "old untested messy")
    commit_on_branch(
        repo,
        "safe-change",
        "src/app/safe.py",
        SAFE_CHANGE,
        "touch tested add",
    )

    result = run_bob(repo, "check", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert payload["old_debt"]
    assert any(item["name"] == "messy" for item in payload["old_debt"])
    assert "## Information (old debt)" in markdown
    assert not any(item["name"] == "messy" for item in payload["top_crap"])


def test_check_does_not_block_old_debt_when_only_unrelated_line_is_removed(
    tmp_path: Path,
) -> None:
    """AC5: remover só `X = 1` de um arquivo com `messy` (CRAP 20) não bloqueia."""
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/risky.py", RISKY_WITH_CONSTANT, "messy plus unused constant")
    commit_on_branch(
        repo,
        "drop-const",
        "src/app/risky.py",
        RISKY_SOURCE,
        "remove only X = 1",
    )

    result = run_bob(repo, "check", "--base", "main", "--gates", "crap")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert result.returncode == 0
    assert any(item["name"] == "messy" for item in payload["old_debt"])
    assert not any(item["name"] == "messy" and item["changed"] for item in payload["top_crap"])


def test_check_blocks_when_line_is_removed_inside_high_crap_function(
    tmp_path: Path,
) -> None:
    """Remover só `return 2` dentro de `messy` (hunk `@@ -5 +4,0 @@`) bloqueia."""
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/risky.py", RISKY_SOURCE, "untested messy")
    commit_on_branch(
        repo,
        "drop-return",
        "src/app/risky.py",
        MESSY_WITHOUT_RETURN_2,
        "remove only return 2",
    )

    result = run_bob(repo, "check", "--base", "main", "--gates", "crap")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 1
    assert any(item["name"] == "messy" and item["changed"] for item in payload["top_crap"])
    assert "fora do diff" not in markdown


def test_default_check_runs_dry_and_deps(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "safe-change",
        "src/app/safe.py",
        SAFE_CHANGE,
        "touch tested add",
    )

    result = run_bob(repo, "check", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    dry = next(gate for gate in payload["gates"] if gate["name"] == "dry")
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")

    assert result.returncode == 0, result.stderr
    assert dry["status"] == "passed"
    assert deps["status"] == "passed"
    assert "✅ `dry`" in markdown
    assert "✅ `deps`" in markdown


def test_check_exits_2_when_baseline_tests_fail(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "broken",
        "tests/test_safe.py",
        "from app.safe import add\n\ndef test_add() -> None:\n    assert add(1, 2) == 0\n",
        "break baseline tests",
    )

    result = run_bob(repo, "check", "--base", "main", "--gates", "crap")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    crap = next(gate for gate in payload["gates"] if gate["name"] == "crap")

    assert result.returncode == 2
    assert crap["status"] == "not_run"
    assert crap["reason"]


def test_check_exits_4_when_config_is_missing(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "safe-change",
        "src/app/safe.py",
        SAFE_CHANGE,
        "touch tested add",
    )

    result = run_bob(repo, "check", "--base", "main", "--config", "missing.yaml")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    names = {gate["name"]: gate for gate in payload["gates"]}

    assert result.returncode == 4
    assert (repo / ".bob" / "report.md").is_file()
    assert names["crap"]["status"] == "not_run"
    assert names["dry"]["status"] == "not_run"
    assert names["deps"]["status"] == "not_run"
    assert names["dry"]["reason"]


def test_check_does_not_reenter_parent_pytest_via_addopts(tmp_path: Path) -> None:
    """`bob check` no fixture não pode herdar PYTEST_ADDOPTS do pytest pai."""
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "safe-change",
        "src/app/safe.py",
        SAFE_CHANGE,
        "touch tested add",
    )
    foreign = tmp_path / "parent" / "test_foreign_reentry.py"
    foreign.parent.mkdir()
    foreign.write_text(
        "from pathlib import Path\n"
        "Path(__file__).with_name('collected').write_text('')\n"
        "def test_foreign():\n"
        "    assert False\n"
    )
    env = {**os.environ, "PYTEST_ADDOPTS": str(foreign)}
    result = subprocess.run(
        [sys.executable, "-m", "bob_quality", "check", "--base", "main", "--gates", "crap"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert not (foreign.parent / "collected").exists()
    assert result.returncode == 0, result.stderr
    assert [item["coverage"] for item in payload["top_crap"] if item["name"] == "add"] == [1.0]


