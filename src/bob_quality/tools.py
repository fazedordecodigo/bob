"""Invoca as ferramentas pinadas (nunca copia o código delas)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


class ToolError(Exception):
    """Ferramenta pinada ausente ou falhou de forma inesperada."""


def tool_version(module: str, pattern: str) -> str:
    raw = _run([sys.executable, "-m", module, "--version"], cwd=None)
    match = re.search(pattern, raw)
    if not match:
        return raw.splitlines()[0].strip() if raw.strip() else "unknown"
    return match.group(1)


def run_lizard_csv(cwd: Path, include: list[str], exclude: list[str]) -> str:
    args = [sys.executable, "-m", "lizard", "--csv", "-l", "python"]
    for pattern in exclude:
        args.extend(["-x", f"{pattern}/*"])
    args.extend(include or ["."])
    return _run(args, cwd)


def run_coverage(
    cwd: Path,
    include: list[str],
    json_path: Path,
    coverage_file: Path | None,
) -> int:
    """Roda pytest sob coverage e grava JSON. Devolve o exit code do pytest.

    Se `coverage_file` já existe, só exporta JSON a partir dele (exit 0).
    """
    if coverage_file is not None:
        _run(
            [sys.executable, "-m", "coverage", "json", "-o", str(json_path)],
            cwd,
            extra_env={"COVERAGE_FILE": str(coverage_file)},
        )
        return 0
    source = ",".join(include) if include else "."
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PYTEST_")
    }
    pytest_run = subprocess.run(
        [sys.executable, "-m", "coverage", "run", f"--source={source}", "-m", "pytest"],
        cwd=cwd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=env,
    )
    if pytest_run.returncode in {0, 5}:
        _run([sys.executable, "-m", "coverage", "json", "-o", str(json_path)], cwd)
    return pytest_run.returncode


def _run(
    args: list[str],
    cwd: Path | None,
    extra_env: dict[str, str] | None = None,
) -> str:
    env = None
    if extra_env is not None:
        env = {**os.environ, **extra_env}
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
    except FileNotFoundError as exc:
        raise ToolError(f"ferramenta ausente: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise ToolError(exc.stderr or exc.stdout or str(exc)) from exc
    return completed.stdout + completed.stderr
