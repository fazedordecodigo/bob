"""Guarda de rede da U5: os testes novos não abrem socket."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_GUARD = _ROOT / "tests" / "net_guard"
_UNIT_ARGS: tuple[tuple[str, ...], ...] = (
    ("tests/test_init_config.py",),
    ("tests/test_project_version.py",),
    ("tests/test_update.py",),
    ("tests/test_docs_pins.py",),
    ("tests/test_hook_install.py",),
    ("tests/test_setup_cmd.py", "-k", "bob_yaml or hook or profile"),
    ("tests/test_verify_install.py",),
    ("tests/test_release_workflow.py",),
    ("tests/test_release_checks.py",),
)


def _guarded_env(log: Path) -> dict[str, str]:
    env = dict(os.environ)
    previous = env.get("PYTHONPATH")
    guard = str(_GUARD)
    if previous:
        env["PYTHONPATH"] = guard + os.pathsep + previous
    else:
        env["PYTHONPATH"] = guard
    env["BOB_NET_GUARD_LOG"] = str(log)
    return env


def test_net_guard_catches_a_connection(tmp_path: Path) -> None:
    log = tmp_path / "net.log"
    code = "import socket; socket.create_connection(('192.0.2.1', 9), timeout=1)"
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=_guarded_env(log),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode != 0
    assert "bob net guard" in result.stderr
    assert len(log.read_text().splitlines()) >= 1


@pytest.mark.parametrize("args", _UNIT_ARGS, ids=[item[0] for item in _UNIT_ARGS])
def test_u5_tests_open_no_network(tmp_path: Path, args: tuple[str, ...]) -> None:
    log = tmp_path / "net.log"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *args],
        cwd=_ROOT,
        env=_guarded_env(log),
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert result.returncode == 0, result.stdout
    assert not log.exists() or log.read_text() == ""
