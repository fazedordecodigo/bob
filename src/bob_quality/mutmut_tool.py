"""Invoca o mutmut pinado. Não lê o código dele."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from bob_quality.adapters.mutmut import suite_failed
from bob_quality.tools import ToolError

_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+)")
_SPINNER_CHAR = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_SPINNER_LINE = re.compile(rf"^[{_SPINNER_CHAR}]\s")
_STATS_PATH = "mutants/mutmut-stats.json"
_TRACEBACK = "Traceback (most recent call last):\n"
_EXCEPTION_LINE = re.compile(r"^\S.*", re.MULTILINE)
# O gate só chama o mutmut depois que a baseline passou no repositório.
_SUITE_FAILS_IN_MUTANTS = (
    "a suíte passa no repositório e falha dentro de mutants/;"
    " confira also_copy e a configuração [mutmut]"
)


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


# A coleta de stats neste repo sozinha passa de 180s. O limite continua existindo.
_RUN_TIMEOUT_SECONDS = 1800


def run_mutmut(cwd: Path, patterns: list[str], max_workers: int | None) -> None:
    args = [sys.executable, "-m", "mutmut", "run", *patterns]
    if max_workers is not None:
        args.extend(["--max-children", str(max_workers)])
    _invoke(args, cwd, timeout=_RUN_TIMEOUT_SECONDS)


def mutmut_results(cwd: Path) -> str:
    return _invoke([sys.executable, "-m", "mutmut", "results", "--all", "true"], cwd)


def mutmut_show(cwd: Path, mutant_id: str) -> str:
    return _invoke([sys.executable, "-m", "mutmut", "show", mutant_id], cwd)


def mutmut_stats(cwd: Path) -> str:
    try:
        return (cwd / _STATS_PATH).read_text()
    except OSError as exc:
        raise ToolError(f"stats do mutmut ausente: {_STATS_PATH}") from exc


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
        output = f"{completed.stdout}\n{completed.stderr}"
        detail = failure_text(completed.stdout, completed.stderr)
        if suite_failed(output):
            raise ToolError(f"{_SUITE_FAILS_IN_MUTANTS}: {detail}")
        if "nothing matches" in output:
            raise ToolError("nothing matches")
        raise ToolError(detail or f"exit {completed.returncode}")
    return completed.stdout + completed.stderr


def failure_text(stdout: str, stderr: str) -> str:
    """Tira o spinner do mutmut e devolve o erro, que vem no fim da saída.

    Com traceback do Python, o erro é só a linha final da exceção.
    """
    kept: list[str] = []
    blob = f"{stdout}\n{stderr}".replace("\r", "\n")
    exception = _final_exception(blob)
    if exception is not None:
        return exception
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


def _final_exception(blob: str) -> str | None:
    """Primeira linha sem recuo depois do último cabeçalho de traceback."""
    _before, header, after = blob.rpartition(_TRACEBACK)
    line = _EXCEPTION_LINE.search(after)
    if not header or line is None:
        return None
    return line.group(0)
