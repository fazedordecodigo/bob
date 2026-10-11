"""O mutmut tem de passar da coleta de stats neste repo, não só no fixture."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from bob_quality import mutmut_tool
from bob_quality.mutate import prepare_mutmut_workspace

ROOT = Path(__file__).resolve().parents[1]

_ALSO_COPY = (
    "docs",
    "skills",
    "js",
    "tests/fixtures",
    ".github",
    "package.json",
    "package-lock.json",
    "AGENTS.md",
)


def test_pyproject_also_copy_lists_what_the_suite_reads_outside_the_package() -> None:
    text = (ROOT / "pyproject.toml").read_text()
    section = text.split("[tool.mutmut]", 1)[1]
    for path in _ALSO_COPY:
        assert f'"{path}"' in section
    assert "node_modules" not in section


def test_prepare_mutmut_workspace_symlinks_node_modules(tmp_path: Path) -> None:
    source = tmp_path / "node_modules" / "pkg"
    source.mkdir(parents=True)
    prepare_mutmut_workspace(tmp_path)
    dest = tmp_path / "mutants" / "node_modules"
    assert dest.is_symlink()
    assert dest.resolve() == source.parent.resolve()
    assert not (dest / "pkg").is_symlink()


def test_gate_subprocesses_skip_the_dogfood_reentry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOB_SKIP_MUTMUT_DOGFOOD", "stale")
    env = mutmut_tool._clean_env()
    assert env["BOB_SKIP_MUTMUT_DOGFOOD"] == "1"
    assert "bob_skip_mutmut_dogfood" not in env


def test_prepare_replaces_nothing_when_mutants_already_exists(tmp_path: Path) -> None:
    (tmp_path / "node_modules").mkdir()
    dest = tmp_path / "mutants" / "node_modules"
    dest.mkdir(parents=True)
    (dest / "marker").write_text("keep")

    prepare_mutmut_workspace(tmp_path)

    assert not dest.is_symlink()
    assert (dest / "marker").read_text() == "keep"


def test_prepare_is_idempotent_when_the_mutants_directory_exists(tmp_path: Path) -> None:
    source = tmp_path / "node_modules"
    source.mkdir()
    (tmp_path / "mutants").mkdir()

    prepare_mutmut_workspace(tmp_path)
    prepare_mutmut_workspace(tmp_path)

    dest = tmp_path / "mutants" / "node_modules"
    assert dest.is_symlink()
    assert dest.resolve() == source.resolve()


def test_mutmut_stats_collection_does_not_die_on_this_repo() -> None:
    if os.environ.get("MUTANT_UNDER_TEST") or os.environ.get("BOB_SKIP_MUTMUT_DOGFOOD"):
        pytest.skip("não reentrar na coleta do mutmut")
    prepare_mutmut_workspace(ROOT)
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PYTEST_") and key != "MUTANT_UNDER_TEST"
    }
    env["BOB_SKIP_MUTMUT_DOGFOOD"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "mutmut",
            "run",
            "bob_quality.crap.x_calculate_crap__mutmut*",
            "--max-children",
            "2",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=env,
        timeout=900,
        check=False,
    )
    blob = f"{completed.stdout}\n{completed.stderr}"
    assert "failed to collect stats" not in blob
    assert "docs/SPEC.md" not in blob
    assert completed.returncode == 0 or "nothing matches" in blob or "mutations/second" in blob
