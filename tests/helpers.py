"""Infra de teste para repos-fixture. Não é o seam — os testes observam a CLI."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from bob_quality.cli import main
from bob_quality.messages import Text, reason, render

FIXTURE_PYTHON = Path(__file__).parent / "fixtures" / "python_app"
FIXTURE_TYPESCRIPT = Path(__file__).parent / "fixtures" / "ts_app"
FIXTURE_MIXED = Path(__file__).parent / "fixtures" / "mixed_app"
RISKY_SOURCE = (FIXTURE_PYTHON / "cases" / "fail_crap.py").read_text()
RISKY_WITH_CONSTANT = (FIXTURE_PYTHON / "cases" / "risky_with_constant.py").read_text()
MESSY_WITHOUT_RETURN_2 = (FIXTURE_PYTHON / "cases" / "messy_without_return_2.py").read_text()
SAFE_CHANGE = (FIXTURE_PYTHON / "cases" / "pass_safe.py").read_text()
TS_RISKY_SOURCE = (FIXTURE_TYPESCRIPT / "cases" / "fail_crap.ts").read_text()
TS_SAFE_CHANGE = (FIXTURE_TYPESCRIPT / "cases" / "pass_safe.ts").read_text()


def in_both(text: Text | BaseException) -> tuple[str, str]:
    """A mensagem renderizada em en e em pt-BR."""
    message = reason(text) if isinstance(text, BaseException) else text
    return render(message, "en"), render(message, "pt-BR")


def run_bob(
    repo: Path,
    *args: str,
    bob_lang: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Roda a CLI no processo do teste, para o mutmut enxergar a função.

    `MUTANT_UNDER_TEST` fica como o mutmut deixou. Apagá-lo solta o trampolim.
    """
    previous_cwd = Path.cwd()
    previous_env = os.environ.copy()
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        os.environ.clear()
        os.environ.update(previous_env if env is None else env)
        os.environ.pop("BOB_LANG", None)
        if bob_lang is not None:
            os.environ["BOB_LANG"] = bob_lang
        os.chdir(repo)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(list(args))
    finally:
        os.chdir(previous_cwd)
        os.environ.clear()
        os.environ.update(previous_env)
    return subprocess.CompletedProcess(
        ["bob", *args], code, stdout.getvalue(), stderr.getvalue()
    )


def run_bob_subprocess(
    repo: Path,
    *args: str,
    bob_lang: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Roda a CLI num interpretador filho.

    O filho não carrega o trampolim do mutmut. Teste que dispara mutmut ou
    Stryker fica neste caminho. No processo, cada mutante do gate repetiria
    o teste.
    """
    base = os.environ if env is None else env
    child = {key: value for key, value in base.items() if key != "BOB_LANG"}
    if bob_lang is not None:
        child["BOB_LANG"] = bob_lang
    return subprocess.run(
        [sys.executable, "-m", "bob_quality", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        env=child,
    )


def _git(repo: Path, *args: str) -> None:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return
    detail = completed.stderr.strip() or completed.stdout.strip()
    raise RuntimeError(f"git {' '.join(args)} exited {completed.returncode}: {detail}")


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
