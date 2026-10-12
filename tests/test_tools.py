"""Fronteira com o subprocesso das ferramentas pinadas."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from bob_quality.tools import ToolError, _run
from helpers import in_both


def test_missing_executable_names_the_tool(tmp_path: Path) -> None:
    missing = str(tmp_path / "nope")

    with pytest.raises(ToolError) as caught:
        _run([missing], cwd=None)

    assert in_both(caught.value) == (f"missing tool: {missing}", f"ferramenta ausente: {missing}")


def test_failure_prefers_stderr_over_stdout() -> None:
    with pytest.raises(ToolError) as caught:
        _run([sys.executable, "-c", "print('out'); raise SystemExit('err')"], cwd=None)

    assert str(caught.value) == "err\n"


def test_failure_without_stderr_keeps_stdout() -> None:
    with pytest.raises(ToolError) as caught:
        _run([sys.executable, "-c", "print('out'); raise SystemExit(3)"], cwd=None)

    assert str(caught.value) == "out\n"


def test_silent_failure_names_the_command_and_exit_status() -> None:
    args = [sys.executable, "-c", "raise SystemExit(3)"]

    with pytest.raises(ToolError) as caught:
        _run(args, cwd=None)

    assert str(caught.value) == f"Command '{args}' returned non-zero exit status 3."


def test_success_runs_in_cwd_with_the_extra_env_and_joins_both_streams(tmp_path: Path) -> None:
    script = "import os, sys; print(os.getcwd()); print(os.environ['BOB_PROBE'], file=sys.stderr)"

    out = _run([sys.executable, "-c", script], tmp_path, extra_env={"BOB_PROBE": "seen"})

    assert out == f"{tmp_path.resolve()}\nseen\n"
