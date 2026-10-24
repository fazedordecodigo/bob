"""scripts/verify-install.sh (CT15): harness do espelho local."""

from __future__ import annotations

import base64
import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from bob_quality import gitleaks
from bob_quality.hook_install import render_hook
from bob_quality.init_config import render_config
from bob_quality.messages import t

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-install.sh"
_HELP = (
    "uso: sh scripts/verify-install.sh [--only <id>[,<id>...]]\n"
    "passos: 1 2 3 4 5 6 7 8 9a 9b 10 11 12 13\n"
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


def test_step_ids_are_the_known_steps() -> None:
    assert _assign("STEP_IDS") == "1 2 3 4 5 6 7 8 9a 9b 10 11 12 13"


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
    assert "      3|4|5|6|7|12) ensure_2 ;;" in lines
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


def test_step_6_is_wired() -> None:
    lines = _text().splitlines()
    assert "step_6() {" in lines
    assert "      6) step_6 ;;" in lines
    assert "      3|4|5|6|7|12) ensure_2 ;;" in lines
    assert "expected_hook() {" in lines


@pytest.mark.parametrize(
    "bob_bin",
    (
        "/h/.local/share/bob-quality/bin/bob",
        "/opt/bob home/bin/bob",
    ),
)
def test_harness_expects_the_ct10_text(bob_bin: str) -> None:
    text = _text()
    match = re.search(
        r"^expected_hook\(\) \{\n.*?^\}$",
        text,
        re.M | re.S,
    )
    assert match is not None
    function = match.group(0)
    checked = subprocess.run(
        ["sh", "-c", function + '\nexpected_hook "$1"\n', "_", bob_bin],
        capture_output=True,
        check=False,
    )
    assert checked.returncode == 0
    assert checked.stdout == render_hook(Path(bob_bin))


def test_step_6_pushes_with_a_clean_env() -> None:
    text = _text()
    assert (
        'env -i "HOME=$S2_HOME" PATH=/usr/bin:/bin git push origin HEAD:main'
        in text
    )
    assert 'git init -q --bare "$T/s6/remote.git"' in text
    assert (
        'expected_hook "$S2_HOME/.local/share/bob-quality/bin/bob"' in text
    )
    assert "# bob report" in text
    assert "o push saiu $_rc" in text


def test_step_7_checks_the_hook_mtime() -> None:
    text = _text()
    assert text.count("o hook foi regravado") == 1
    assert text.count('file_mtime "$_hook"') == 2


def test_step_8_checks_the_foreign_hook() -> None:
    text = _text()
    preserved = t(
        "en",
        "setup.preserved",
        item=t("en", "setup.preserved_hook", path=".git/hooks/pre-push"),
    )
    assert text.count(preserved) == 1
    warn_lines = (
        "  _warn=\"bob setup: hook: warning: existing pre-push hook "
        "preserved (.git/hooks/pre-push).\"",
        "  _warn=\"$_warn To use bob's, add: "
        "$T/s8/home/.local/share/bob-quality/bin/bob\"",
        '  _warn="$_warn check --gates crap,dry,deps."',
    )
    lines = text.splitlines()
    for line in warn_lines:
        assert line in lines
    assert '  _files="$_files .git/hooks/pre-push"' in lines
    checked = subprocess.run(
        [
            "sh",
            "-c",
            "T=/t\n" + "\n".join(warn_lines) + '\nprintf %s "$_warn"\n',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert checked.returncode == 0
    assert checked.stdout == t(
        "en",
        "setup.warning_line",
        step="hook",
        text=t(
            "en",
            "setup.warn_hook_foreign",
            path=".git/hooks/pre-push",
            bob="/t/s8/home/.local/share/bob-quality/bin/bob",
        ),
    )


def _body(name: str) -> str:
    match = re.search(rf"^{name}\(\) \{{\n.*?^\}}$", _text(), re.M | re.S)
    assert match is not None, name
    return match.group(0)


def _sh(
    script: str,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sh", "-c", script, "sh", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env if env is not None else {"PATH": "/usr/bin:/bin"},
    )


def test_steps_10_and_11_are_wired() -> None:
    lines = _text().splitlines()
    names = (
        "ensure_8",
        "ensure_10",
        "next_patch",
        "rebrand_wheel",
        "sums_two",
        "build_update_mirror",
        "run_bob",
        "check_version",
        "step_10",
        "step_11",
    )
    for line in (
        "STEP8_DONE=0",
        "STEP10_DONE=0",
        "NEW_X=",
        "NEW_TAG=",
        "NEW_WHL=",
        *(f"{name}() {{" for name in names),
        "      8) ensure_8 ;;",
        "      10) ensure_10 ;;",
        "      11) step_11 ;;",
        '    check_version 2 "$S2_HOME" "$S2_PROJ" "$T/s2/tmp" "$X"',
    ):
        assert line in lines
    assert "      8) step_8 ;;" not in lines
    assert lines.index("      10) ensure_10 ;;") == (
        lines.index("      9b) step_9b ;;") + 1
    )
    assert lines.index("      11) step_11 ;;") == (
        lines.index("      10) ensure_10 ;;") + 1
    )
    remote = '  if [ "$remote" -eq 1 ]; then'
    skip = "    return 0"
    close = "  fi"
    step_10_head = [
        remote,
        "    printf '%s\\n' 'verify-install: passo 10: não se aplica "
        "(VERIFY_REMOTE=1)'",
        skip,
        close,
        "  ensure_8",
    ]
    step_11_head = [
        remote,
        "    printf '%s\\n' 'verify-install: passo 11: não se aplica "
        "(VERIFY_REMOTE=1)'",
        skip,
        close,
        "  ensure_10",
    ]
    assert _body("step_10").splitlines()[1:6] == step_10_head
    assert _body("step_11").splitlines()[1:6] == step_11_head
    assert lines.index("pytest_pin() {") > lines.index("step_11() {")
    assert lines.index("step_11() {") > lines.index("step_9b() {")


@pytest.mark.parametrize("n", ["8", "10"])
def test_ensure_runs_the_step_once(n: str) -> None:
    script = (
        f"STEP{n}_DONE=0\nstep_{n}() {{ echo ran; }}\n"
        + _body(f"ensure_{n}")
        + f"\nensure_{n}\nensure_{n}\n"
    )
    checked = _sh(script)
    assert checked.returncode == 0
    assert checked.stdout == "ran\n"


def test_next_patch() -> None:
    checked = _sh(_body("next_patch") + "\nnext_patch 1.2.3\nnext_patch 0.9.19\n")
    assert checked.returncode == 0
    assert checked.stdout == "1.2.4\n0.9.20\n"


@pytest.mark.parametrize("case", ["ok", "no_version"])
def test_rebrand_wheel_changes_only_the_version(
    tmp_path: Path, case: str
) -> None:
    meta = (
        b"Metadata-Version: 2.1\nName: bob-quality\n"
        b"Version: 1.2.3\n\nVersion: 1.2.3\n"
    )
    if case == "no_version":
        meta = b"Metadata-Version: 2.1\nName: bob-quality\n"
    wheel = tmp_path / "a.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("bob_quality/__init__.py", b"x = 1\n")
        archive.writestr("bob_quality-1.2.3.dist-info/METADATA", meta)
        archive.writestr("bob_quality-1.2.3.dist-info/RECORD", b"velho\n")
    dest = tmp_path / "b.whl"
    env = {
        "PATH": "/usr/bin:/bin",
        "PY_DIR": str(Path(sys.executable).parent),
    }
    checked = _sh(
        _body("rebrand_wheel") + '\nrebrand_wheel "$1" "$2" 1.2.3 1.2.4\n',
        str(wheel),
        str(dest),
        env=env,
    )
    if case == "no_version":
        assert checked.returncode == 1
        return
    assert checked.returncode == 0
    with zipfile.ZipFile(dest) as archive:
        assert archive.namelist() == [
            "bob_quality/__init__.py",
            "bob_quality-1.2.4.dist-info/METADATA",
            "bob_quality-1.2.4.dist-info/RECORD",
        ]
        init = archive.read("bob_quality/__init__.py")
        metadata = archive.read("bob_quality-1.2.4.dist-info/METADATA")
        record = archive.read("bob_quality-1.2.4.dist-info/RECORD")
    assert init == b"x = 1\n"
    assert metadata == (
        b"Metadata-Version: 2.1\nName: bob-quality\n"
        b"Version: 1.2.4\n\nVersion: 1.2.3\n"
    )
    blobs = (
        ("bob_quality/__init__.py", init),
        ("bob_quality-1.2.4.dist-info/METADATA", metadata),
    )
    expected = "".join(
        f"{name},sha256="
        f"{base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()},"
        f"{len(data)}\n"
        for name, data in blobs
    )
    expected += "bob_quality-1.2.4.dist-info/RECORD,,\n"
    assert record.decode() == expected


def test_sums_two_lists_the_wheel_then_install_sh(tmp_path: Path) -> None:
    folder = tmp_path / "d"
    folder.mkdir()
    (folder / "install.sh").write_bytes(b"a\n")
    (folder / "w.whl").write_bytes(b"b\n")
    checked = _sh(
        _body("file_sha") + "\n" + _body("sums_two") + '\nsums_two "$1" w.whl\n',
        str(folder),
    )
    assert checked.returncode == 0
    ha = hashlib.sha256(b"a\n").hexdigest()
    hb = hashlib.sha256(b"b\n").hexdigest()
    assert (folder / "SHA256SUMS").read_text() == (
        hb + "  w.whl\n" + ha + "  install.sh\n"
    )


def test_run_bob_builds_the_environment(tmp_path: Path) -> None:
    home = tmp_path / "h"
    bob = home / ".local" / "bin" / "bob"
    bob.parent.mkdir(parents=True)
    bob.write_text("#!/bin/sh\n")
    bob.chmod(0o755)
    stub = tmp_path / "stub"
    stub.mkdir()
    env_bin = stub / "env"
    env_bin.write_text(
        "#!/bin/sh\nfor a in \"$@\"; do printf '%s\\n' \"$a\"; done\n"
    )
    env_bin.chmod(0o755)
    out = tmp_path / "out"
    err = tmp_path / "err"
    script = (
        "T=/t\nNODE_DIR=/n\nPY_DIR=/p\nGL_URL=http://g\n"
        + _body("die_passo")
        + "\n"
        + _body("tool_path")
        + "\n"
        + _body("run_bob")
        + '\nrun_bob 10 "$@"\necho "RC:$?"\n'
    )
    checked = _sh(
        script,
        str(home),
        str(tmp_path),
        "/tt",
        "http://r",
        str(out),
        str(err),
        "update",
        env={"PATH": f"{stub}:/usr/bin:/bin", "PIP_INDEX_URL": "http://pip"},
    )
    assert checked.stdout == "RC:0\n"
    assert out.read_text().splitlines() == [
        "-i",
        f"HOME={home}",
        "TMPDIR=/tt",
        "LANG=C.UTF-8",
        "PATH=/t/fake-sudo:/n:/p:/usr/bin:/bin",
        "BOB_RELEASES_URL=http://r",
        "BOB_GITLEAKS_BASE_URL=http://g",
        "PIP_INDEX_URL=http://pip",
        f"{home}/.local/bin/bob",
        "update",
    ]


def test_update_texts_are_the_catalog_texts() -> None:
    lines = _text().splitlines()
    wanted = (
        '  _v1="bob $5"',
        '  _v2="project skills: $5 (.agents/skills)"',
        '  _upg="bob update: updating from v$X to $NEW_TAG."',
        '  _same="bob update: already on the newest release ($NEW_TAG)."',
    )
    for line in wanted:
        assert line in lines
    checked = _sh(
        "set -- a b c d 1.2.3\nX=1.2.3\nNEW_TAG=v1.2.4\n"
        + "\n".join(wanted)
        + '\nprintf "%s\\n" "$_v1" "$_v2" "$_upg" "$_same"\n'
    )
    assert checked.returncode == 0
    assert checked.stdout.splitlines() == [
        t("en", "version.bob", version="1.2.3"),
        t(
            "en",
            "version.skills",
            state=t("en", "version.at", version="1.2.3"),
        ),
        t("en", "update.upgrading", old="1.2.3", tag="v1.2.4"),
        t("en", "update.up_to_date", tag="v1.2.4"),
    ]


def test_step_12_runs_the_hook_tests() -> None:
    text = _text()
    lines = text.splitlines()
    assert "step_12() {" in lines
    assert "      12) step_12 ;;" in lines
    assert "pytest_pin() {" in lines
    assert "-m pytest -q -p no:cacheprovider tests/test_hook.py" in text
    assert "7 passed" in text


def test_pytest_pin_matches_pyproject() -> None:
    text = _text()
    match = re.search(
        r"^pytest_pin\(\) \{\n.*?^\}$",
        text,
        re.M | re.S,
    )
    assert match is not None
    function = match.group(0)
    checked = subprocess.run(
        ["sh", "-c", function + "\npytest_pin\n"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert checked.returncode == 0
    pin = checked.stdout.strip()
    dev = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["optional-dependencies"]["dev"]
    assert pin in dev
    assert pin.startswith("pytest==")


def _function(text: str, name: str) -> str:
    match = re.search(rf"^{name}\(\) \{{\n.*?^\}}$", text, re.M | re.S)
    assert match is not None
    return match.group(0)


_INSTALL = ROOT / "scripts" / "install.sh"

_SUMMARY_LINES = (
    (
        '  _added="  shell profile: added ~/.local/bin to PATH in '
        '$_pf. Open a new terminal or run: . $_pf"'
    ),
    (
        '  _marked="  shell profile: $_pf already has the bob line; '
        'nothing changed"'
    ),
    (
        '  _onpath="  shell profile: ~/.local/bin is already on PATH; '
        'nothing changed"'
    ),
    '  _failed="  shell profile: could not write $_pf; see the warning above"',
)
_WARN_LINES = (
    "  _full=$(profile_line)",
    '  _mark="#${_full#* #}"',
    "  _paste=${_full%% #*}",
    (
        '  _warn="install: perfil: warning: could not write $_pf '
        "(Permission denied). To use the bob command, add to your "
        'profile: $_paste."'
    ),
)


def test_step_13_is_wired() -> None:
    lines = _text().splitlines()
    expected = (
        "profile_line() {",
        "profile_case() {",
        "step_13() {",
        "      13) step_13 ;;",
        "      3|4|5|6|7|12) ensure_2 ;;",
        "  profile_case a /bin/zsh",
        "  profile_case b /bin/bash",
        "  profile_case c /bin/sh",
        "  profile_case d /bin/bash",
        "  profile_case e /bin/bash",
    )
    for line in expected:
        assert line in lines
    assert _function(_text(), "step_13").splitlines()[1:5] == [
        '  if [ "$(id -u)" -eq 0 ]; then',
        (
            '    die_passo 13 "rode sem root: o caso (e) precisa de um '
            'perfil só leitura"'
        ),
        "  fi",
        "  ensure_2",
    ]
    assert '"$2" "$S2_HOME/.local/share/bob-quality"' in _text()
    step_13 = lines.index("      13) step_13 ;;")
    step_12 = lines.index("      12) step_12 ;;")
    assert step_13 == step_12 + 1


def _env_rows(home: Path, path: Path, *, shell: str | None) -> list[str]:
    rows = [
        "-i",
        f"HOME={home}",
        "TMPDIR=/t",
        "LANG=C.UTF-8",
        f"PATH={path}",
        "BOB_RELEASES_URL=http://r",
    ]
    if shell is not None:
        rows.append(f"SHELL={shell}")
        rows.append("BOB_HOME=/bh")
    rows.extend(
        [
            "sh",
            "-c",
            'curl -fsSL "$1/latest/download/install.sh" | sh',
            "_",
            "http://u",
        ]
    )
    return rows


@pytest.mark.parametrize(
    "case",
    ["with", "without", "own_bob", "foreign_bob"],
)
def test_run_oneliner_passes_shell_and_bob_home(
    case: str,
    tmp_path: Path,
) -> None:
    home = tmp_path / "h"
    home.mkdir()
    stub = tmp_path / "stub"
    stub.mkdir()
    env_bin = stub / "env"
    env_bin.write_text(
        "#!/bin/sh\n"
        "for a in \"$@\"; do printf '%s\\n' \"$a\"; done\n",
        encoding="utf-8",
    )
    env_bin.chmod(0o755)
    if case in ("with", "without"):
        path = tmp_path / "none"
        path.mkdir()
    elif case == "own_bob":
        path = home / ".local" / "bin"
        path.mkdir(parents=True)
        bob = path / "bob"
        bob.write_text("#!/bin/sh\n", encoding="utf-8")
        bob.chmod(0o755)
    else:
        path = tmp_path / "other"
        path.mkdir()
        bob = path / "bob"
        bob.write_text("#!/bin/sh\n", encoding="utf-8")
        bob.chmod(0o755)
    if case == "with":
        extra = ["/bin/zsh", "/bh"]
    elif case == "without":
        extra = []
    else:
        extra = ["/bin/bash", "/bh"]
    out = tmp_path / "out"
    err = tmp_path / "err"
    script = (
        "GL_URL=\n"
        + _function(_text(), "die_passo")
        + "\n"
        + _function(_text(), "run_oneliner")
        + '\nrun_oneliner 13 "$@"\necho "RC:$?"\n'
    )
    checked = subprocess.run(
        [
            "sh",
            "-c",
            script,
            "sh",
            str(home),
            "/t",
            str(tmp_path),
            "http://r",
            "http://u",
            str(path),
            str(out),
            str(err),
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": f"{stub}:/usr/bin:/bin"},
    )
    if case == "with":
        assert checked.stdout == "RC:0\n"
        assert out.read_text(encoding="utf-8").splitlines() == _env_rows(
            home,
            path,
            shell="/bin/zsh",
        )
    elif case == "without":
        assert checked.stdout == "RC:0\n"
        assert out.read_text(encoding="utf-8").splitlines() == _env_rows(
            home,
            path,
            shell=None,
        )
    elif case == "own_bob":
        assert checked.stdout == "RC:0\n"
        assert "SHELL=/bin/bash" in out.read_text(encoding="utf-8").splitlines()
    else:
        assert checked.returncode == 1
        assert checked.stderr == (
            "verify-install: passo 13: bob já está no PATH "
            f"({path / 'bob'}); a máquina não está limpa.\n"
        )
        assert not out.exists()


def test_step_13_summary_lines_are_the_ct3_texts() -> None:
    text_lines = _text().splitlines()
    for line in _SUMMARY_LINES:
        assert line in text_lines
    checked = subprocess.run(
        [
            "sh",
            "-c",
            "_pf=/h/.bashrc\n"
            + "\n".join(_SUMMARY_LINES)
            + '\nprintf "%s\\n" "$_added" "$_marked" "$_onpath" "$_failed"\n',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert checked.returncode == 0
    keys = (
        "setup.profile_added",
        "setup.profile_marked",
        "setup.profile_on_path",
        "setup.profile_failed",
    )
    assert checked.stdout.splitlines() == [
        t("en", "setup.profile", text=t("en", key, path="/h/.bashrc"))
        for key in keys
    ]


def test_step_13_warning_is_the_install_sh_text() -> None:
    install = _INSTALL.read_text(encoding="utf-8")
    text_lines = _text().splitlines()
    for line in _WARN_LINES:
        assert line in text_lines
    harness = subprocess.run(
        [
            "sh",
            "-c",
            _function(_text(), "profile_line")
            + "\n_pf=/h/.bashrc\n"
            + "\n".join(_WARN_LINES)
            + '\nprintf "%s\\n" "$_warn" "$_mark"\n',
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    profile = re.search(r"^PROFILE_LINE='.*'$", install, re.M)
    assert profile is not None
    install_run = subprocess.run(
        [
            "sh",
            "-c",
            profile.group(0)
            + "\nNODE_FLOOR='22.18.0'\nbob_lang=en\n"
            + _function(install, "say")
            + "\nsay profile_warning /h/.bashrc 'Permission denied'\n",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert harness.returncode == 0
    assert install_run.returncode == 0
    assert harness.stdout.splitlines()[0] == install_run.stdout[:-1]
    assert harness.stdout.splitlines()[1] == "# managed-by: bob-quality"


def test_profile_line_comes_from_install_sh() -> None:
    checked = subprocess.run(
        [
            "sh",
            "-c",
            _function(_text(), "profile_line") + "\nprofile_line\n",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert checked.returncode == 0
    found = re.search(
        r"^PROFILE_LINE='(.*)'$",
        _INSTALL.read_text(encoding="utf-8"),
        re.M,
    )
    assert found is not None
    assert checked.stdout == found.group(1) + "\n"
    assert found.group(1) not in _text()


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
            ("--only", "15"),
            (
                "verify-install: uso: passo desconhecido 15. "
                "Passos: 1 2 3 4 5 6 7 8 9a 9b 10 11 12 13."
            ),
        ),
        (
            ("--only", "9c"),
            (
                "verify-install: uso: passo desconhecido 9c. "
                "Passos: 1 2 3 4 5 6 7 8 9a 9b 10 11 12 13."
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
