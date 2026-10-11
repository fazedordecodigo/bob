"""Hook pre-push: `bob check --gates crap` em menos de 60 s no fixture."""

import shutil
import subprocess
import time
from pathlib import Path

from helpers import RISKY_SOURCE, SAFE_CHANGE, commit_on_branch, init_python_repo

HOOK = Path(__file__).resolve().parents[1] / "src/bob_quality/hooks/pre-push"


def _install_hook(repo: Path) -> Path:
    dest = repo / ".git" / "hooks" / "pre-push"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(HOOK, dest)
    dest.chmod(0o755)
    return dest


def test_pre_push_hook_runs_crap_gate_under_60s(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "safe-change",
        "src/app/safe.py",
        SAFE_CHANGE,
        "touch tested add",
    )
    dest = _install_hook(repo)

    started = time.monotonic()
    result = subprocess.run(
        [str(dest)],
        cwd=repo,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    elapsed = time.monotonic() - started

    assert "bob check --gates crap" in HOOK.read_text()
    assert result.returncode == 0, result.stderr
    assert elapsed < 60
    assert (repo / ".bob" / "report.json").is_file()


def test_pre_push_hook_blocks_when_changed_function_exceeds_crap_10(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "risky",
        "src/app/risky.py",
        RISKY_SOURCE,
        "add untested messy function",
    )
    dest = _install_hook(repo)

    started = time.monotonic()
    result = subprocess.run(
        [str(dest)],
        cwd=repo,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    elapsed = time.monotonic() - started

    assert result.returncode == 1
    assert elapsed < 60
    assert (repo / ".bob" / "report.json").is_file()
