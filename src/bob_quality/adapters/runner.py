from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from bob_quality.messages import Text, msg


@dataclass(frozen=True)
class ProcessExit:
    code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class ProcessFault:
    detail: Text


ProcessResult = ProcessExit | ProcessFault
Runner = Callable[[list[str], Path, int], ProcessResult]


def banner_version(result: ProcessExit, pattern: re.Pattern[str]) -> str:
    match = pattern.search(result.stdout)
    if match is None:
        match = pattern.search(result.stderr)
    if match is None:
        return "unknown"
    return match.group(0)


def default_runner(args: list[str], cwd: Path, timeout: int) -> ProcessResult:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return ProcessFault(msg("tool.detail", tool=args[0], detail="timed out"))
    except FileNotFoundError:
        return ProcessFault(msg("tool.missing", tool=args[0]))
    return ProcessExit(completed.returncode, completed.stdout, completed.stderr)
