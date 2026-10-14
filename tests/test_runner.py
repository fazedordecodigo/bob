"""The real process runner. Supply and the other gates call it when no fake is installed."""

import os
import sys
from pathlib import Path

import pytest

from bob_quality.adapters.runner import ProcessExit, ProcessFault, default_runner
from bob_quality.messages import msg


def test_default_runner_returns_text_from_the_given_directory(tmp_path: Path) -> None:
    (tmp_path / "talk.py").write_text(
        "import sys\nsys.stdout.write('out-text')\nsys.stderr.write('err-text')\nraise SystemExit(3)\n"
    )

    result = default_runner([sys.executable, "talk.py"], tmp_path, 5)

    assert result == ProcessExit(3, "out-text", "err-text")


def test_default_runner_names_a_missing_executable(tmp_path: Path) -> None:
    result = default_runner(["bob-missing-tool"], tmp_path, 5)

    assert result == ProcessFault(msg("tool.missing", tool="bob-missing-tool"))


def test_default_runner_lets_a_permission_error_escape(tmp_path: Path) -> None:
    with pytest.raises(PermissionError):
        default_runner([str(tmp_path)], tmp_path, 5)


def test_default_runner_times_out_and_names_the_executable(tmp_path: Path) -> None:
    (tmp_path / "wait.py").write_text("import time\ntime.sleep(1.5)\n")

    result = default_runner([sys.executable, "wait.py"], tmp_path, 1)

    assert result == ProcessFault(msg("tool.detail", tool=sys.executable, detail="timed out"))


def test_default_runner_waits_long_enough_for_a_short_command(tmp_path: Path) -> None:
    (tmp_path / "pause.py").write_text("import time\ntime.sleep(1.2)\n")

    result = default_runner([sys.executable, "pause.py"], tmp_path, 2)

    assert result == ProcessExit(0, "", "")


def test_default_runner_does_not_read_the_caller_stdin(tmp_path: Path) -> None:
    (tmp_path / "read.py").write_text("import sys\nsys.stdout.write(sys.stdin.read())\n")
    read_fd, write_fd = os.pipe()
    os.write(write_fd, b"secret")
    os.close(write_fd)
    saved = os.dup(0)
    os.dup2(read_fd, 0)
    os.close(read_fd)
    try:
        result = default_runner([sys.executable, "read.py"], tmp_path, 2)
    finally:
        os.dup2(saved, 0)
        os.close(saved)

    assert result == ProcessExit(0, "", "")
