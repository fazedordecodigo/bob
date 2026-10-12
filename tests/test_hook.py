"""Hook pre-push: `bob check --gates crap` em menos de 60 s no fixture."""

import shutil
import subprocess
import time
from pathlib import Path

from helpers import (
    RISKY_SOURCE,
    SAFE_CHANGE,
    TS_SAFE_CHANGE,
    commit_on_branch,
    commit_on_main,
    init_python_repo,
    init_ts_repo,
)

HOOK = Path(__file__).resolve().parents[1] / "src/bob_quality/hooks/pre-push"
LEFT = (
    Path(__file__).resolve().parents[0] / "fixtures" / "python_app" / "cases" / "cycle_left.py"
).read_text()
RIGHT = (
    Path(__file__).resolve().parents[0] / "fixtures" / "python_app" / "cases" / "cycle_right.py"
).read_text()
LEFT_TS = 'import { right } from "./right";\nexport const left = right;\n'
RIGHT_TS = 'import { left } from "./left";\nexport const right = left;\n'


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


def test_pre_push_hook_blocks_a_new_python_dependency_violation(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "cycle", "src/app/left.py", LEFT, "add left")
    commit_on_branch(repo, "cycle", "src/app/right.py", RIGHT, "add right")
    dest = _install_hook(repo)

    result = subprocess.run(
        [str(dest)],
        cwd=repo,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 1, result.stderr
    assert "`app.right → app.left`" in markdown


def test_pre_push_hook_allows_an_old_python_dependency_violation(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/left.py", LEFT, "old left")
    commit_on_main(repo, "src/app/right.py", RIGHT, "old right")
    commit_on_branch(repo, "safe-change", "src/app/safe.py", SAFE_CHANGE, "touch add")
    dest = _install_hook(repo)

    result = subprocess.run(
        [str(dest)],
        cwd=repo,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 0, result.stderr
    assert "`app.right → app.left`" in markdown
    assert "outside the diff; does not block" in markdown


def test_pre_push_hook_blocks_a_new_typescript_dependency_violation(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(repo, "cycle", "src/left.ts", LEFT_TS, "add left")
    commit_on_branch(repo, "cycle", "src/right.ts", RIGHT_TS, "add right")
    dest = _install_hook(repo)

    result = subprocess.run(
        [str(dest)],
        cwd=repo,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 1, result.stderr
    assert "`src/left.ts → src/right.ts`" in markdown


def test_pre_push_hook_allows_an_old_typescript_dependency_violation(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_main(repo, "src/left.ts", LEFT_TS, "old left")
    commit_on_main(repo, "src/right.ts", RIGHT_TS, "old right")
    commit_on_branch(repo, "safe-change", "src/safe.ts", TS_SAFE_CHANGE, "touch add")
    dest = _install_hook(repo)

    result = subprocess.run(
        [str(dest)],
        cwd=repo,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 0, result.stderr
    assert "src/left.ts → src/right.ts" in markdown
    assert "outside the diff; does not block" in markdown
