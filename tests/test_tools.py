"""Fronteira com o subprocesso das ferramentas pinadas."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from bob_quality.tools import PythonStarted, ToolError, _coverage_rc, _ensure_combined, _run
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


def test_combine_marker_is_named_and_written_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rc = tmp_path / "coverage.rc"
    rc.write_text("x\n")
    started = PythonStarted(0, rc)
    calls: list[tuple[object, ...]] = []

    def record(args: list[str], cwd: Path | None, extra_env: dict[str, str] | None = None) -> str:
        calls.append((args, cwd, extra_env))
        return ""

    monkeypatch.setattr("bob_quality.tools._run", record)

    _ensure_combined(tmp_path, started)
    _ensure_combined(tmp_path, started)

    marker = tmp_path / ".coverage-combined"
    assert marker.read_text() == ""
    assert calls == [
        (
            [sys.executable, "-m", "coverage", "combine", "--rcfile", str(rc)],
            tmp_path,
            None,
        )
    ]


def test_empty_include_uses_the_working_directory(tmp_path: Path) -> None:
    rc = _coverage_rc(tmp_path, [], tmp_path)

    text = rc.read_text()

    assert rc.name == "coverage.rc"
    assert "data_file = " + str(tmp_path / "coverage.data") in text
    assert "    " + str(tmp_path.resolve()) in text
    assert "XX" not in text
