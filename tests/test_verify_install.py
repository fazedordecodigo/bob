"""scripts/verify-install.sh (CT15): harness do espelho local."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from bob_quality.doctor import BinaryPin, PINS

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-install.sh"
_HELP = (
    "uso: sh scripts/verify-install.sh [--only <id>[,<id>...]]\n"
    "passos: 1 2 3 4 7 8 9b\n"
    "VERIFY_REMOTE=1 usa o GitHub em vez do espelho local.\n"
)
_OUTSIDE = (
    "verify-install: uso: rode na raiz do checkout do bob "
    "(não achei scripts/install.sh).\n"
)
_SHA_NAMES = (
    "GITLEAKS_SHA_LINUX_X64",
    "GITLEAKS_SHA_LINUX_ARM64",
    "GITLEAKS_SHA_DARWIN_X64",
    "GITLEAKS_SHA_DARWIN_ARM64",
)


def _text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _assign(name: str) -> str:
    match = re.search(rf"^{name}='(.*)'$", _text(), re.M)
    assert match is not None
    return match.group(1)


def _tmpdir() -> Path:
    return Path(os.environ.get("TMPDIR", "/tmp"))


def _verify_names(directory: Path) -> set[str]:
    if not directory.is_dir():
        return set()
    return {
        child.name
        for child in directory.iterdir()
        if child.name.startswith("bob-verify.")
    }


def _gitleaks() -> BinaryPin:
    for pin in PINS:
        if isinstance(pin, BinaryPin) and pin.name == "gitleaks":
            return pin
    raise AssertionError("pin gitleaks ausente")


def test_verify_install_is_posix() -> None:
    checked = subprocess.run(["sh", "-n", str(SCRIPT)], check=False)
    assert checked.returncode == 0
    dash = shutil.which("dash")
    if dash:
        checked = subprocess.run([dash, "-n", str(SCRIPT)], check=False)
        assert checked.returncode == 0


def test_verify_install_shape() -> None:
    text = _text()
    assert text.startswith("#!/bin/sh\n")
    assert "\r" not in text
    lines = [line for line in text.splitlines() if line]
    assert lines[-1] == 'main "$@"'
    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    repo = Path(top.stdout.strip() or str(ROOT))
    listed = subprocess.run(
        ["git", "ls-files", "-s", "scripts/verify-install.sh"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert listed.stdout.startswith("100755")
    assert re.search(r"^\s*sudo\b", text, re.M) is None


def test_step_ids_are_the_u1_steps() -> None:
    assert _assign("STEP_IDS") == "1 2 3 4 7 8 9b"


def test_gitleaks_constants_match_the_doctor_pin() -> None:
    pin = _gitleaks()
    assert _assign("GITLEAKS_VERSION") == pin.expected
    assert _assign("GITLEAKS_SHA_LINUX_X64") == pin.sha256
    for name in _SHA_NAMES:
        assert re.fullmatch(r"[0-9a-f]{64}", _assign(name))


def test_help_exits_0() -> None:
    before = _verify_names(_tmpdir())
    checked = subprocess.run(
        ["sh", "scripts/verify-install.sh", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert checked.returncode == 0
    assert checked.stdout == _HELP
    assert _verify_names(_tmpdir()) == before


@pytest.mark.parametrize(
    ("args", "line"),
    [
        (
            ("--only", "5"),
            (
                "verify-install: uso: passo desconhecido 5. "
                "Passos: 1 2 3 4 7 8 9b."
            ),
        ),
        (
            ("--only",),
            "verify-install: uso: --only. Rode com --help.",
        ),
        (
            ("--nope",),
            "verify-install: uso: --nope. Rode com --help.",
        ),
    ],
)
def test_usage_errors_exit_1_before_preparing(
    args: tuple[str, ...],
    line: str,
) -> None:
    before = _verify_names(_tmpdir())
    checked = subprocess.run(
        ["sh", str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert checked.returncode == 1
    assert checked.stderr == line + "\n"
    assert _verify_names(_tmpdir()) == before


def test_outside_the_checkout_exits_1(tmp_path: Path) -> None:
    checked = subprocess.run(
        ["sh", str(SCRIPT)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert checked.returncode == 1
    assert checked.stderr == _OUTSIDE
