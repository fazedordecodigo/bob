"""Infra de teste para repos-fixture. Não é o seam — os testes observam a CLI."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

FIXTURE_PYTHON = Path(__file__).parent / "fixtures" / "python_app"
FIXTURE_TYPESCRIPT = Path(__file__).parent / "fixtures" / "ts_app"
FIXTURE_MIXED = Path(__file__).parent / "fixtures" / "mixed_app"
RISKY_SOURCE = (FIXTURE_PYTHON / "cases" / "fail_crap.py").read_text()
RISKY_WITH_CONSTANT = (FIXTURE_PYTHON / "cases" / "risky_with_constant.py").read_text()
MESSY_WITHOUT_RETURN_2 = (FIXTURE_PYTHON / "cases" / "messy_without_return_2.py").read_text()
SAFE_CHANGE = (FIXTURE_PYTHON / "cases" / "pass_safe.py").read_text()
TS_RISKY_SOURCE = (FIXTURE_TYPESCRIPT / "cases" / "fail_crap.ts").read_text()
TS_SAFE_CHANGE = (FIXTURE_TYPESCRIPT / "cases" / "pass_safe.ts").read_text()


def run_bob(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bob_quality", *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def init_python_repo(dest: Path) -> Path:
    """Copia o fixture e cria um git em `main` com o estado que passa."""
    return _init_repo(FIXTURE_PYTHON, dest)


def init_ts_repo(dest: Path) -> Path:
    """Copia o fixture TypeScript e cria um git em `main` com o estado que passa."""
    return _init_repo(FIXTURE_TYPESCRIPT, dest)


def init_mixed_repo(dest: Path) -> Path:
    """Copia o fixture Py+TS e cria um git em `main`."""
    return _init_repo(FIXTURE_MIXED, dest)


def _init_repo(source: Path, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest)
    _git(dest, "init", "-b", "main")
    _git(dest, "config", "user.email", "bob-test@example.com")
    _git(dest, "config", "user.name", "bob-test")
    _git(dest, "add", ".")
    _git(dest, "commit", "-m", "fixture base")
    return dest


def commit_on_main(repo: Path, relative: str, content: str, message: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    _git(repo, "add", relative)
    _git(repo, "commit", "-m", message)


def commit_on_branch(repo: Path, branch: str, relative: str, content: str, message: str) -> None:
    _git(repo, "checkout", "-B", branch)
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    _git(repo, "add", relative)
    _git(repo, "commit", "-m", message)
