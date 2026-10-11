"""Comportamento da CLI `bob` sobre o repo-fixture Python (seam principal)."""

import json
from pathlib import Path

from helpers import (
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
    assert "dívida antiga" in markdown
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


def test_unimplemented_gates_are_skipped_never_passed(tmp_path: Path) -> None:
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

    assert result.returncode == 0
    assert dry["status"] == "not_run"
    assert dry["reason"]
    assert deps["status"] == "not_run"
    assert "⏭️" in markdown
    assert "✅ `dry`" not in markdown
    assert "✅ `deps`" not in markdown


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

