"""scripts/verify-install.sh (CT15): harness do espelho local."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from bob_quality import gitleaks
from bob_quality.init_config import render_config
from bob_quality.messages import t

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-install.sh"
_HELP = (
    "uso: sh scripts/verify-install.sh [--only <id>[,<id>...]]\n"
    "passos: 1 2 3 4 5 7 8 9a 9b\n"
    "VERIFY_REMOTE=1 usa o GitHub em vez do espelho local.\n"
)
_OUTSIDE = (
    "verify-install: uso: rode na raiz do checkout do bob "
    "(não achei scripts/install.sh).\n"
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


def test_step_ids_are_the_u1_u3_and_u4_steps() -> None:
    assert _assign("STEP_IDS") == "1 2 3 4 5 7 8 9a 9b"


def test_gitleaks_constants_match_the_gitleaks_table() -> None:
    assert _assign("GITLEAKS_VERSION") == gitleaks.VERSION
    pairs = (
        ("GITLEAKS_SHA_LINUX_X64", ("linux", "x64")),
        ("GITLEAKS_SHA_LINUX_ARM64", ("linux", "arm64")),
        ("GITLEAKS_SHA_DARWIN_X64", ("darwin", "x64")),
        ("GITLEAKS_SHA_DARWIN_ARM64", ("darwin", "arm64")),
    )
    for name, key in pairs:
        assert _assign(name) == gitleaks.ASSETS[key][1]


def test_harness_has_no_gitleaks_fixture() -> None:
    text = _text()
    assert "fixture-bin" not in text
    assert "gl-src" not in text
    match = re.search(r"^tool_path\(\) \{\n(.*?)^\}$", text, re.M | re.S)
    assert match is not None
    assert (
        match.group(1)
        == "  printf '%s' \"$T/fake-sudo:$NODE_DIR:$PY_DIR:/usr/bin:/bin\"\n"
    )


def test_harness_serves_gitleaks_from_the_mirror() -> None:
    text = _text()
    assert '"$T/mirror/gitleaks/$_asset"' in text
    assert '"$T/mirror/gitleaks-bad/$_asset"' in text
    assert "GL_URL=$BASE/gitleaks" in text
    assert "GL_URL=$BASE/gitleaks-bad" in text


def test_harness_passes_the_gitleaks_base_url() -> None:
    text = _text()
    assert "BOB_GITLEAKS_BASE_URL=$GL_URL" in text
    assert "command -v gitleaks" in text


def test_step_9a_is_wired() -> None:
    text = _text()
    lines = text.splitlines()
    assert "step_9a() {" in lines
    assert "      9a) step_9a ;;" in lines
    message = "verify-install: passo 9a: não se aplica (VERIFY_REMOTE=1)"
    assert text.count(message) == 1


def test_step_5_is_wired() -> None:
    text = _text()
    lines = text.splitlines()
    assert "step_5() {" in lines
    assert "      5) step_5 ;;" in lines
    assert "      3|4|5|7) ensure_2 ;;" in lines
    assert "expected_bob_yaml() {" in lines


@pytest.mark.parametrize(
    ("include", "item"),
    [
        (("src",), "[src]"),
        (("app",), "[app]"),
        ((".",), '["."]'),
    ],
)
def test_harness_expects_the_ct7_text(
    include: tuple[str, ...],
    item: str,
) -> None:
    text = _text()
    match = re.search(
        r"^expected_bob_yaml\(\) \{\n.*?^\}$",
        text,
        re.M | re.S,
    )
    assert match is not None
    function = match.group(0)
    checked = subprocess.run(
        ["sh", "-c", function + '\nexpected_bob_yaml "$1"\n', "_", item],
        capture_output=True,
        text=True,
        check=False,
    )
    assert checked.returncode == 0
    assert checked.stdout == render_config(include)


def test_step_5_checks_the_no_code_warning() -> None:
    warning = t(
        "en",
        "setup.warning_line",
        step="bob.yaml",
        text=t("en", "setup.warn_no_code"),
    )
    assert _text().count(warning) == 1


def test_steps_7_and_8_check_the_preserved_lines() -> None:
    text = _text()
    bob_yaml = t(
        "en",
        "setup.preserved",
        item=t("en", "setup.preserved_bob_yaml"),
    )
    waivers = t(
        "en",
        "setup.preserved",
        item=t("en", "setup.preserved_waivers"),
    )
    assert text.count(bob_yaml) == 2
    assert text.count(waivers) == 1


def test_step_5_runs_bob_check_with_the_u4_gates() -> None:
    text = _text()
    assert "check --base HEAD --gates crap,dry,deps" in text
    assert '"$S2_HOME/.local/share/bob-quality/bin/bob"' in text
    assert "bob check saiu 4" in text


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
            ("--only", "6"),
            (
                "verify-install: uso: passo desconhecido 6. "
                "Passos: 1 2 3 4 5 7 8 9a 9b."
            ),
        ),
        (
            ("--only", "9c"),
            (
                "verify-install: uso: passo desconhecido 9c. "
                "Passos: 1 2 3 4 5 7 8 9a 9b."
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
