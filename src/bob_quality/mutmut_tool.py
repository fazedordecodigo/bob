"""Invoca o mutmut pinado. Não lê o código dele."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from bob_quality.tools import ToolError

_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+)")
_SPINNER_CHAR = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_SPINNER_LINE = re.compile(rf"^[{_SPINNER_CHAR}]\s")


def pytest_exit_code(cwd: Path) -> int:
    """Roda a suíte uma vez. Devolve o exit code do pytest, sem transformar falha em erro de ferramenta."""
    env = _clean_env()
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=cwd,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            env=env,
            timeout=900,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError("pytest da baseline excedeu o tempo limite") from exc
    return completed.returncode


def mutmut_version() -> str:
    raw = _invoke([sys.executable, "-m", "mutmut", "--version"], cwd=None)
    match = _VERSION_RE.search(raw)
    if not match:
        raise ToolError(f"versão do mutmut ilegível: {raw.strip()}")
    return match.group(1)


# A coleta de stats passa de 180s. O diff desta fatia não terminou em 1800s.
_RUN_TIMEOUT_SECONDS = 10800


def run_mutmut(cwd: Path, patterns: list[str], max_workers: int | None) -> None:
    args = [sys.executable, "-m", "mutmut", "run", *patterns]
    if max_workers is not None:
        args.extend(["--max-children", str(max_workers)])
    _invoke(args, cwd, timeout=_RUN_TIMEOUT_SECONDS)


def mutmut_results(cwd: Path) -> str:
    return _invoke([sys.executable, "-m", "mutmut", "results", "--all", "true"], cwd)


def mutmut_show(cwd: Path, mutant_id: str) -> str:
    return _invoke([sys.executable, "-m", "mutmut", "show", mutant_id], cwd)


def _clean_env() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PYTEST_") and key != "MUTANT_UNDER_TEST"
    }
    # A suíte deste repo inclui um teste que dispara o mutmut. Sem esta marca,
    # a baseline e a coleta reentram nele.
    env["BOB_SKIP_MUTMUT_DOGFOOD"] = "1"
    return env


def _invoke(args: list[str], cwd: Path | None, timeout: int = 180) -> str:
    env = _clean_env()
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            env=env,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ToolError(f"ferramenta ausente: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError("mutmut excedeu o tempo limite") from exc
    if completed.returncode != 0:
        detail = failure_text(completed.stdout, completed.stderr)
        if "nothing matches" in f"{completed.stdout}\n{completed.stderr}":
            raise ToolError("nothing matches")
        raise ToolError(detail or f"exit {completed.returncode}")
    return completed.stdout + completed.stderr


def failure_text(stdout: str, stderr: str) -> str:
    """Tira o spinner do mutmut e devolve o erro, que vem no fim da saída."""
    kept: list[str] = []
    blob = f"{stdout}\n{stderr}".replace("\r", "\n")
    for raw in blob.splitlines():
        text = raw.strip()
        if not text or _SPINNER_LINE.match(text) or "Generating mutants" in text:
            continue
        if all(char in _SPINNER_CHAR or char.isspace() for char in text):
            continue
        kept.append(text)
    compact = " ".join(kept)
    if len(compact) > 400:
        return "…" + compact[-400:]
    return compact
