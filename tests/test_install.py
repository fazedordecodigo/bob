"""Scaffold: `pip install -e .` expõe o comando `bob` com deps pinadas."""

import shutil
import subprocess
import sysconfig
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_bob_console_script_is_on_path() -> None:
    scripts = Path(sysconfig.get_path("scripts")) / "bob"
    executable = str(scripts) if scripts.is_file() else shutil.which("bob")
    assert executable is not None
    result = subprocess.run([executable, "check", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--base" in result.stdout
    assert "--gates" in result.stdout


def test_lizard_and_coverage_are_pinned_dependencies() -> None:
    text = (ROOT / "pyproject.toml").read_text()
    assert "lizard==1.24.1" in text
    assert "coverage==7.16.2" in text
