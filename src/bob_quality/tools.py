"""Invoca as ferramentas pinadas (nunca copia o código delas)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from bob_quality.exit_codes import pytest_passed
from bob_quality.messages import msg


class ToolError(Exception):
    """Ferramenta pinada ausente ou falhou de forma inesperada."""


def spawn_clean(
    cwd: Path,
    args: Sequence[str],
    prefix: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}
    if prefix is not None:
        bindir = prefix / "node_modules" / ".bin"
        env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=env,
    )


def tool_version(module: str, pattern: str) -> str:
    raw = _run([sys.executable, "-m", module, "--version"], cwd=None)
    match = re.search(pattern, raw)
    if not match:
        return raw.splitlines()[0].strip() if raw.strip() else "unknown"
    return match.group(1)


def run_lizard_csv(
    cwd: Path,
    include: list[str],
    exclude: list[str],
    language: str = "python",
) -> str:
    args = [sys.executable, "-m", "lizard", "--csv", "-l", language]
    for pattern in exclude:
        args.extend(["-x", f"{pattern}/*"])
    args.extend(include or ["."])
    return _run(args, cwd)


@dataclass(frozen=True)
class PythonStarted:
    pytest_code: int | None
    rc: Path


def run_coverage(
    cwd: Path,
    include: list[str],
    json_path: Path,
    coverage_file: Path | None,
) -> int | None:
    """Roda pytest sob coverage e grava JSON. Devolve o exit code do pytest.

    Se `coverage_file` já existe, só exporta JSON a partir dele e devolve None,
    porque nenhum pytest rodou.
    """
    started = start_python_coverage(cwd, include, json_path.parent, coverage_file)
    if started.pytest_code is not None and not pytest_passed(started.pytest_code):
        return started.pytest_code
    export_coverage_json(cwd, started, json_path)
    return started.pytest_code


def start_python_coverage(
    cwd: Path,
    include: Sequence[str],
    work: Path,
    coverage_file: Path | None,
) -> PythonStarted:
    if coverage_file is not None:
        return PythonStarted(pytest_code=None, rc=coverage_file)
    rc = _coverage_rc(work, include, cwd)
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PYTEST_")
    }
    # coverage apaga COVERAGE_PROCESS_START no processo medido. O conftest
    # do repo copia BOB_COVERAGE_RC para os subprocessos (a CLI sob teste).
    env["BOB_COVERAGE_RC"] = str(rc)
    pytest_run = subprocess.run(
        [sys.executable, "-m", "coverage", "run", "--rcfile", str(rc), "-m", "pytest"],
        cwd=cwd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=env,
    )
    return PythonStarted(pytest_code=pytest_run.returncode, rc=rc)


def export_coverage_json(cwd: Path, started: PythonStarted, dest: Path) -> None:
    _export_coverage(cwd, started, dest, "json")


def export_coverage_xml(cwd: Path, started: PythonStarted, dest: Path) -> None:
    _export_coverage(cwd, started, dest, "xml")


def _export_coverage(cwd: Path, started: PythonStarted, dest: Path, kind: str) -> None:
    if started.pytest_code is None:
        _run(
            [sys.executable, "-m", "coverage", kind, "-o", str(dest)],
            cwd,
            extra_env={"COVERAGE_FILE": str(started.rc)},
        )
        return
    _ensure_combined(cwd, started)
    _run(
        [sys.executable, "-m", "coverage", kind, "--rcfile", str(started.rc), "-o", str(dest)],
        cwd,
    )


def _ensure_combined(cwd: Path, started: PythonStarted) -> None:
    marker = started.rc.parent / ".coverage-combined"
    if marker.is_file():
        return
    _run([sys.executable, "-m", "coverage", "combine", "--rcfile", str(started.rc)], cwd)
    marker.write_text("")


def _coverage_rc(work: Path, include: Sequence[str], cwd: Path) -> Path:
    data_file = work / "coverage.data"
    rc = work / "coverage.rc"
    lines = ["[run]", "parallel = true", f"data_file = {data_file}", "source ="]
    for item in include or ["."]:
        path = Path(item)
        if not path.is_absolute():
            path = cwd / path
        lines.append(f"    {path.resolve()}")
    rc.write_text("\n".join(lines) + "\n")
    return rc


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
        raise ToolError(msg("tool.missing", tool=args[0])) from exc
    except subprocess.CalledProcessError as exc:
        raise ToolError(exc.stderr or exc.stdout or str(exc)) from exc
    return completed.stdout + completed.stderr
