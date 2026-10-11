"""Exit code do `bob` é o status do check, e o relatório sobrevive à falha."""

import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / ".github" / "actions" / "bob"
RUN_CHECK = ACTION / "run_check.sh"
PROPAGATE = ACTION / "propagate_exit.sh"


def _fake_bob(bin_dir: Path, code: int) -> None:
    bin_dir.mkdir()
    script = bin_dir / "bob"
    script.write_text(
        "#!/bin/sh\n"
        "mkdir -p .bob\n"
        "printf '%s\\n' \"$*\" > .bob/args\n"
        "printf '%s\\n' '# Relatório bob' > .bob/report.md\n"
        f"exit {code}\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)


def _env(bin_dir: Path, work: Path, **extra: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["BOB_EXIT_FILE"] = str(work / "exit-code")
    env.pop("GITHUB_OUTPUT", None)
    env.pop("GITHUB_BASE_REF", None)
    env.pop("BOB_BASE", None)
    env.pop("BOB_GATES", None)
    env.update(extra)
    return env


def test_failed_check_keeps_the_report_and_propagates_exit_3(tmp_path: Path) -> None:
    _fake_bob(tmp_path / "bin", 3)
    env = _env(tmp_path / "bin", tmp_path, BOB_BASE="origin/main")

    ran = subprocess.run(
        ["bash", str(RUN_CHECK)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    propagated = subprocess.run(
        ["bash", str(PROPAGATE)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert ran.returncode == 0, ran.stderr
    assert (tmp_path / ".bob" / "report.md").read_text().startswith("# Relatório bob")
    assert "check" in (tmp_path / ".bob" / "args").read_text()
    assert "--gates" in (tmp_path / ".bob" / "args").read_text()
    assert "mutate" in (tmp_path / ".bob" / "args").read_text()
    assert "--base origin/main" in (tmp_path / ".bob" / "args").read_text()
    assert propagated.returncode == 3


def test_pull_request_base_ref_is_passed_when_input_is_empty(tmp_path: Path) -> None:
    _fake_bob(tmp_path / "bin", 0)
    env = _env(tmp_path / "bin", tmp_path, GITHUB_BASE_REF="main")

    ran = subprocess.run(
        ["bash", str(RUN_CHECK)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert ran.returncode == 0, ran.stderr
    assert "--base origin/main" in (tmp_path / ".bob" / "args").read_text()


def test_missing_exit_file_is_a_config_error(tmp_path: Path) -> None:
    env = _env(tmp_path / "bin", tmp_path)
    propagated = subprocess.run(
        ["bash", str(PROPAGATE)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert propagated.returncode == 4
