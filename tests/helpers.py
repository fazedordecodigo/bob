"""Infra de teste para repos-fixture. Não é o seam — os testes observam a CLI."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

from bob_quality.messages import Language, Text, reason, render

FIXTURE_PYTHON = Path(__file__).parent / "fixtures" / "python_app"
FIXTURE_TYPESCRIPT = Path(__file__).parent / "fixtures" / "ts_app"
FIXTURE_MIXED = Path(__file__).parent / "fixtures" / "mixed_app"
RISKY_SOURCE = (FIXTURE_PYTHON / "cases" / "fail_crap.py").read_text()
RISKY_WITH_CONSTANT = (FIXTURE_PYTHON / "cases" / "risky_with_constant.py").read_text()
MESSY_WITHOUT_RETURN_2 = (FIXTURE_PYTHON / "cases" / "messy_without_return_2.py").read_text()
SAFE_CHANGE = (FIXTURE_PYTHON / "cases" / "pass_safe.py").read_text()
TS_RISKY_SOURCE = (FIXTURE_TYPESCRIPT / "cases" / "fail_crap.ts").read_text()
TS_SAFE_CHANGE = (FIXTURE_TYPESCRIPT / "cases" / "pass_safe.ts").read_text()


class LanguageCase(NamedTuple):
    flag: Language | None
    env: Language | None
    configured: Language | None
    expected: Language


LANGUAGE_CASES: tuple[LanguageCase, ...] = (
    LanguageCase(None, None, None, "en"),
    LanguageCase("pt-BR", None, None, "pt-BR"),
    LanguageCase(None, "pt-BR", None, "pt-BR"),
    LanguageCase(None, None, "pt-BR", "pt-BR"),
    LanguageCase(None, "en", "pt-BR", "en"),
    LanguageCase("en", "pt-BR", "pt-BR", "en"),
    LanguageCase("pt-BR", "en", "en", "pt-BR"),
)

BAD_LANGUAGE_YAML: tuple[tuple[str, str], ...] = (
    ("language: fr\n", "bob.yaml: language must be en or pt-BR\n"),
    ("language: pt-br\n", "bob.yaml: language must be en or pt-BR\n"),
    ("language: 5\n", "bob.yaml: language must be a string\n"),
    ("- base\n", "bob.yaml must be a mapping\n"),
    (":\n  - [\n", "invalid YAML in bob.yaml: while parsing a block mapping\n"),
)


def in_both(text: Text | BaseException) -> tuple[str, str]:
    """A mensagem renderizada em en e em pt-BR."""
    message = reason(text) if isinstance(text, BaseException) else text
    return render(message, "en"), render(message, "pt-BR")


def run_bob(
    repo: Path, *args: str, bob_lang: str | None = None
) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key != "BOB_LANG"}
    if bob_lang is not None:
        env["BOB_LANG"] = bob_lang
    return subprocess.run(
        [sys.executable, "-m", "bob_quality", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def _git(repo: Path, *args: str) -> None:
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_PREFIX", "GIT_COMMON_DIR"):
        env.pop(key, None)
    completed = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    if completed.returncode != 0:
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
    # The image signs every commit. The signer fails under load and the baseline exits 2.
    _git(dest, "config", "commit.gpgsign", "false")
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
