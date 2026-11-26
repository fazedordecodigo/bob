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


class ChangedLines(set[int]):
    """Linhas do lado novo de um arquivo. `anchors` são as que só marcam uma remoção do commit."""

    anchors: frozenset[int] = frozenset()


def worktree_lines(cwd: Path, lines: dict[str, set[int]]) -> dict[str, set[int]]:
    """Leva as linhas do diff de HEAD para a árvore de trabalho, que é onde o gate mede.

    Uma linha fora dos hunks locais só se move. Uma linha que um hunk local substitui vale o
    bloco novo inteiro, porque o Git não diz qual linha nova corresponde a qual. Uma linha
    apagada localmente sai do escopo, a não ser que marque uma remoção do commit: aí a âncora
    vai para a linha anterior que sobrou.
    """
    return {file: _shift(touched, _local_hunks(cwd, file)) for file, touched in lines.items()}


def _local_hunks(cwd: Path, file: str) -> list[tuple[int, ...]]:
    """Os cabeçalhos `@@` do diff local de um arquivo: nenhuma linha de conteúdo começa com `@`."""
    patch = _git_raw(
        cwd,
        "diff",
        "--unified=0",
        "--inter-hunk-context=0",
        "--no-color",
        "--no-ext-diff",
        "--no-textconv",
        "HEAD",
        "--",
        file,
    ).decode(errors="surrogateescape")
    return [
        tuple(int(group or "1") for group in match.groups())
        for match in map(FULL_HUNK_RE.match, patch.split("\n"))
        if match
    ]


def _git_raw(cwd: Path, *args: str) -> bytes:
    try:
        return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GitError(str(exc)) from exc


def _shift(touched: set[int], hunks: list[tuple[int, ...]]) -> set[int]:
    anchors = getattr(touched, "anchors", frozenset())
    moved: set[int] = set()
    for line in touched:
        moved.update(_shift_line(line, hunks, line in anchors))
    return moved


def _shift_line(line: int, hunks: list[tuple[int, ...]], anchor: bool) -> set[int]:
    delta = 0
    for old, removed, new, added in hunks:
        if line < old + (removed == 0):
            break
        if line < old + removed:
            if added:
                return set(range(new, new + added))
            return {max(new, 1)} if anchor else set()
        delta += added - removed
    return {line + delta}


def parse_unified_diff(patch: str) -> dict[str, set[int]]:
    files: dict[str, ChangedLines] = {}
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
        touched = files.setdefault(current, ChangedLines())
        if count == 0:
            touched.add(start)
            touched.anchors = touched.anchors | {start}
            continue
        touched.update(range(start, start + count))
    return dict(files)


def function_is_changed(file: str, start: int, end: int, lines: dict[str, set[int]]) -> bool:
    touched = lines.get(file)
    if not touched:
        return False
    return any(start <= line <= end for line in touched)


def line_is_changed(file: str, line: int, changed: Mapping[str, Set[int]]) -> bool:
    return line in changed.get(file, ())


def normalize_include_root(path: Path) -> Path:
    anchor = Path(path.anchor)
    prefix = Path("/") if path.anchor == "//" else anchor
    for part in path.relative_to(anchor).parts:
        if part == "..":
            # Resolve only the symlink being popped, not aliases left in the path.
            prefix = (prefix.resolve() if prefix.is_symlink() else prefix).parent
        else:
            prefix /= part
    return prefix


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
