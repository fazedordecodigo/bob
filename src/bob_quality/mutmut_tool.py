"""Invoca o mutmut pinado. Não lê o código dele."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from bob_quality.tools import ToolError

_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+)")


def pytest_exit_code(cwd: Path) -> int:
    """Roda a suíte uma vez. Devolve o exit code do pytest, sem transformar falha em erro de ferramenta."""
    env = _clean_env()
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=cwd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=env,
        timeout=120,
        check=False,
    )
    return completed.returncode


def mutmut_version() -> str:
    raw = _invoke([sys.executable, "-m", "mutmut", "--version"], cwd=None)
    match = _VERSION_RE.search(raw)
    if not match:
        raise ToolError(f"versão do mutmut ilegível: {raw.strip()}")
    return match.group(1)


def run_mutmut(cwd: Path, patterns: list[str], max_workers: int | None) -> None:
    args = [sys.executable, "-m", "mutmut", "run", *patterns]
    if max_workers is not None:
        args.extend(["--max-children", str(max_workers)])
    _invoke(args, cwd)


def mutmut_results(cwd: Path) -> str:
    return _invoke([sys.executable, "-m", "mutmut", "results", "--all", "true"], cwd)


def mutmut_show(cwd: Path, mutant_id: str) -> str:
    return _invoke([sys.executable, "-m", "mutmut", "show", mutant_id], cwd)


def _clean_env() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PYTEST_") and key != "MUTANT_UNDER_TEST"
    }


def _invoke(args: list[str], cwd: Path | None) -> str:
    env = _clean_env()
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            env=env,
            timeout=180,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ToolError(f"ferramenta ausente: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError("mutmut excedeu o tempo limite") from exc
    if completed.returncode != 0:
        detail = (completed.stdout + "\n" + completed.stderr).strip()
        if "nothing matches" in detail:
            raise ToolError("nothing matches")
        raise ToolError(_one_line(detail or f"exit {completed.returncode}"))
    return completed.stdout + completed.stderr


def _one_line(text: str) -> str:
    compact = " ".join(text.split())
    if len(compact) > 400:
        return compact[:400] + "…"
    return compact
