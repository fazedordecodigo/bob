"""Escopo de diff: `git diff <base>...HEAD` → arquivos e linhas alteradas."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping, Set
from pathlib import Path

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
FULL_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class GitError(Exception):
    """Falha ao ler o git do repositório alvo."""


def current_commit(cwd: Path) -> str:
    return _git(cwd, "rev-parse", "HEAD").strip()


def changed_lines(cwd: Path, base: str) -> dict[str, set[int]]:
    """Linhas do lado novo por arquivo relativo ao root."""
    patch = _git(cwd, "diff", "--unified=0", f"{base}...HEAD")
    return parse_unified_diff(patch)


def worktree_lines(cwd: Path, lines: dict[str, set[int]]) -> dict[str, set[int]]:
    """Leva as linhas do diff de HEAD para a árvore de trabalho, que é onde o gate mede."""
    if not lines:
        return lines
    patch = _git(cwd, "diff", "--unified=0", "HEAD", "--", *sorted(lines))
    hunks = _local_hunks(patch)
    return {file: _shift(touched, hunks.get(file, [])) for file, touched in lines.items()}


def _local_hunks(patch: str) -> dict[str, list[tuple[int, int, int, int]]]:
    hunks: dict[str, list[tuple[int, int, int, int]]] = {}
    current: list[tuple[int, int, int, int]] = []
    for line in patch.splitlines():
        if line.startswith("+++ "):
            current = hunks.setdefault(line[4:].strip().removeprefix("b/"), [])
            continue
        match = FULL_HUNK_RE.match(line)
        if match:
            old, old_count, new, new_count = match.groups()
            current.append((int(old), int(old_count or "1"), int(new), int(new_count or "1")))
    return hunks


def _shift(touched: set[int], hunks: list[tuple[int, int, int, int]]) -> set[int]:
    moved: set[int] = set()
    for line in touched:
        moved.update(_shift_line(line, hunks))
    return moved


def _shift_line(line: int, hunks: list[tuple[int, int, int, int]]) -> set[int]:
    delta = 0
    for old, old_count, new, new_count in hunks:
        if old_count == 0:
            if line <= old:
                break
            delta += new_count
            continue
        if line < old:
            break
        if line < old + old_count:
            return set(range(new, new + new_count))
        delta += new_count - old_count
    return {line + delta}


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
            continue
        if current is None:
            continue
        match = HUNK_RE.match(line)
        if not match:
            continue
        start = int(match.group(1))
        count = int(match.group(2) or "1")
        touched = files.setdefault(current, set())
        if count == 0:
            touched.add(start)
            continue
        touched.update(range(start, start + count))
    return files


def function_is_changed(file: str, start: int, end: int, lines: dict[str, set[int]]) -> bool:
    touched = lines.get(file)
    if not touched:
        return False
    return any(start <= line <= end for line in touched)


def line_is_changed(file: str, line: int, changed: Mapping[str, Set[int]]) -> bool:
    return line in changed.get(file, ())


def as_diff_path(cwd: Path, raw: str) -> str | None:
    if raw == "":
        return None
    path = Path(raw)
    if ".." in path.parts:
        return None
    root = cwd.resolve()
    if path.is_absolute():
        candidate = path
    else:
        candidate = root / path
    try:
        relative = candidate.resolve().relative_to(root)
    except ValueError:
        return None
    return relative.as_posix()


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
