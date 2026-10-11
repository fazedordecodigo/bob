"""Hook pre-push: `bob check --gates crap` em menos de 60 s no fixture."""

import shutil
import subprocess
import time
from pathlib import Path

from helpers import commit_on_branch, init_python_repo

HOOK = Path(__file__).resolve().parents[1] / "src/bob_quality/hooks/pre-push"


def test_pre_push_hook_runs_crap_gate_under_60s(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "safe-change",
        "src/app/safe.py",
        'def add(left: int, right: int) -> int:\n    """Soma dois inteiros."""\n    return left + right\n',
        "touch tested add",
    )
    dest = repo / ".git" / "hooks" / "pre-push"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(HOOK, dest)
    dest.chmod(0o755)

    started = time.monotonic()
    result = subprocess.run([str(dest)], cwd=repo, capture_output=True, text=True)
    elapsed = time.monotonic() - started

    assert "bob check --gates crap" in HOOK.read_text()
    assert result.returncode == 0, result.stderr
    assert elapsed < 60
    assert (repo / ".bob" / "report.json").is_file()
