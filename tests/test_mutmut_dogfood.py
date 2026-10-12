"""O mutmut tem de passar da coleta de stats neste repo, não só no fixture."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from bob_quality import mutmut_tool
from bob_quality.mutate import prepare_mutmut_workspace
from bob_quality.tools import ToolError
from helpers import in_both

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
    "README.md",
    "README.pt-BR.md",
    "LICENSE",
    ".claude-plugin",
    ".cursor-plugin",
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


def test_baseline_timeout_is_a_tool_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def expired(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd="pytest", timeout=900)

    monkeypatch.setattr(mutmut_tool.subprocess, "run", expired)
    with pytest.raises(ToolError) as caught:
        mutmut_tool.pytest_exit_code(tmp_path)
    assert in_both(caught.value) == (
        "baseline pytest timed out",
        "pytest da baseline excedeu o tempo limite",
    )


def test_baseline_pytest_receives_the_repo_command_and_a_clean_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # MUTANT_UNDER_TEST fica como o mutmut deixou. Sobrescrever aqui impede
    # o trampolim de associar este teste à função, e o mutante sobrevive.
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "leak")
    monkeypatch.setenv("KEEP_ME", "yes")
    monkeypatch.setenv("BOB_SKIP_MUTMUT_DOGFOOD", "stale")
    seen: dict[str, object] = {}

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["args"] = args
        seen["kwargs"] = kwargs
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(mutmut_tool.subprocess, "run", fake_run)

    assert mutmut_tool.pytest_exit_code(tmp_path) == 0

    kwargs = seen["kwargs"]
    assert isinstance(kwargs, dict)
    assert seen["args"] == [sys.executable, "-m", "pytest", "-q"]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["check"] is False
    assert kwargs["timeout"] >= 900
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert env["KEEP_ME"] == "yes"
    assert env["BOB_SKIP_MUTMUT_DOGFOOD"] == "1"
    assert "MUTANT_UNDER_TEST" not in env
    assert not any(key.startswith("PYTEST_") for key in env)


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
    if os.environ.get("BOB_COVERAGE_RC"):
        pytest.skip("leva minutos sob o coverage do gate CRAP e roda no job de pytest")
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
