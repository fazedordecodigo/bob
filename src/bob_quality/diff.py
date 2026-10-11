"""Escopo de diff: `git diff <base>...HEAD` → arquivos e linhas alteradas."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


class GitError(Exception):
    """Falha ao ler o git do repositório alvo."""


def current_commit(cwd: Path) -> str:
    return _git(cwd, "rev-parse", "HEAD").strip()


def changed_lines(cwd: Path, base: str) -> dict[str, set[int]]:
    """Linhas do lado novo por arquivo relativo ao root."""
    try:
        patch = _git(cwd, "diff", "--unified=0", f"{base}...HEAD")
    except GitError:
        raise
    return parse_unified_diff(patch)


def parse_unified_diff(patch: str) -> dict[str, set[int]]:
    files: dict[str, set[int]] = {}
    current: str | None = None
    for line in patch.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            if target == "/dev/null":
                current = None
                continue
            if target.startswith("b/"):
                target = target[2:]
            current = target
            files.setdefault(current, set())
            continue
        if current is None:
            continue
        match = HUNK_RE.match(line)
        if not match:
            continue
        start = int(match.group(1))
        count = int(match.group(2) or "1")
        if count == 0:
            continue
        files[current].update(range(start, start + count))
    return files


def function_is_changed(file: str, start: int, end: int, lines: dict[str, set[int]]) -> bool:
    touched = lines.get(file)
    if touched is None:
        return False
    if not touched:
        return True
    return any(start <= line <= end for line in touched)


def _git(cwd: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GitError(str(exc)) from exc
    return completed.stdout
