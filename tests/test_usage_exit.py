from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from bob_quality.cli import main
from helpers import run_bob

_COMMAND_GROUP = re.compile(r"\{([^{}]+)\}")


def _usage_4(result: subprocess.CompletedProcess[str], repo: Path) -> None:
    assert result.returncode == 4, result.stderr
    assert "usage:" in result.stderr, result.stderr
    assert "baseline" not in result.stderr.lower(), result.stderr
    assert not (repo / ".bob").exists(), repo


def _help_0(result: subprocess.CompletedProcess[str], repo: Path) -> None:
    assert result.returncode == 0, result.stderr
    assert not (repo / ".bob").exists(), repo


def _commands(repo: Path) -> tuple[str, ...]:
    result = run_bob(repo, "--help")
    assert result.returncode == 0, result.stderr
    match = _COMMAND_GROUP.search(result.stdout)
    assert match is not None, result.stdout
    names = tuple(part.strip() for part in match.group(1).split(",") if part.strip())
    assert names, result.stdout
    return names


def test_missing_command_exits_4(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path), tmp_path)


def test_unknown_command_exits_4(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path, "report"), tmp_path)


def test_every_command_rejects_an_unknown_flag(tmp_path: Path) -> None:
    for command in _commands(tmp_path):
        _usage_4(run_bob(tmp_path, command, "--not-a-real-flag"), tmp_path)


def test_check_format_outside_choices(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path, "check", "--format", "xml"), tmp_path)


def test_numeric_flags_reject_text(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path, "mutate", "--max-workers", "nope"), tmp_path)
    _usage_4(run_bob(tmp_path, "crap", "--threshold", "nope"), tmp_path)


def test_waive_without_a_target(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path, "waive"), tmp_path)


def test_waive_reason_without_a_value(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path, "waive", "classify", "--reason"), tmp_path)


def test_doctor_rejects_config_and_base(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path, "doctor", "--config"), tmp_path)
    _usage_4(run_bob(tmp_path, "doctor", "--config", "bob.yaml"), tmp_path)
    _usage_4(run_bob(tmp_path, "doctor", "--base"), tmp_path)
    _usage_4(run_bob(tmp_path, "doctor", "--base", "main"), tmp_path)


def test_missing_lang_and_config_values(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path, "--lang"), tmp_path)
    _usage_4(run_bob(tmp_path, "--config"), tmp_path)
    _usage_4(run_bob(tmp_path, "check", "--lang"), tmp_path)
    _usage_4(run_bob(tmp_path, "check", "--config"), tmp_path)


def test_shared_flag_before_the_command(tmp_path: Path) -> None:
    for command in _commands(tmp_path):
        _usage_4(run_bob(tmp_path, "--base", "main", command), tmp_path)


def test_help_exits_0(tmp_path: Path) -> None:
    _help_0(run_bob(tmp_path, "--help"), tmp_path)
    _help_0(run_bob(tmp_path, "-h"), tmp_path)
    _help_0(run_bob(tmp_path, "--lang", "en", "--help"), tmp_path)
    for command in _commands(tmp_path):
        _help_0(run_bob(tmp_path, command, "--help"), tmp_path)


def test_main_returns_the_process_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["--help"]) == 0
    assert main(["check", "--help"]) == 0
    assert main(["check", "--format", "xml"]) == 4
    assert not (tmp_path / ".bob").exists()


def test_invalid_lang_masks_a_later_usage_error(tmp_path: Path) -> None:
    result = run_bob(tmp_path, "--lang", "nope", "check", "--format", "xml")
    assert result.returncode == 4, result.stderr
    assert "invalid language" in result.stderr, result.stderr
    assert "xml" not in result.stderr, result.stderr
    assert "baseline" not in result.stderr.lower(), result.stderr
    assert not (tmp_path / ".bob").exists(), tmp_path
