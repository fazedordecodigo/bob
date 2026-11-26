"""Escopo de diff: `git diff <base>...HEAD` → arquivos e linhas alteradas."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping, Set
from dataclasses import dataclass, field
from difflib import SequenceMatcher
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
    """Leva as linhas do diff de HEAD para a árvore de trabalho, que é onde o gate mede.

    Uma linha que só se moveu vai para a posição nova. Dentro de um hunk local, a linha
    casada por conteúdo, ou de uma troca de N linhas por N, vai para a correspondente. Numa
    troca de N por M, a correspondência é ambígua e vale o bloco novo inteiro. Uma linha
    apagada localmente vira âncora na linha anterior que sobrou, como faz o diff da branch.
    """
    if not lines:
        return lines
    patch = _git(cwd, "diff", "--unified=0", "HEAD", "--", *sorted(lines), errors="surrogateescape")
    hunks = _local_hunks(patch)
    return {file: _shift(touched, hunks.get(file, [])) for file, touched in lines.items()}


@dataclass(frozen=True)
class _Hunk:
    old: int
    new: int
    removed: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)


def _local_hunks(patch: str) -> dict[str, list[_Hunk]]:
    hunks: dict[str, list[_Hunk]] = {}
    current: list[_Hunk] = []
    in_header = True
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            in_header = True
        elif in_header and line.startswith("+++ "):
            current = hunks.setdefault(line[4:].strip().removeprefix("b/"), [])
        elif match := FULL_HUNK_RE.match(line):
            in_header = False
            current.append(_Hunk(int(match.group(1)), int(match.group(3))))
        elif not in_header and current and line[:1] in "+-" and line:
            (current[-1].added if line[0] == "+" else current[-1].removed).append(line[1:])
    return hunks


def _shift(touched: set[int], hunks: list[_Hunk]) -> set[int]:
    moved: set[int] = set()
    for line in touched:
        moved.update(_shift_line(line, hunks))
    return moved


def _shift_line(line: int, hunks: list[_Hunk]) -> set[int]:
    delta = 0
    for hunk in hunks:
        if not hunk.removed:
            if line <= hunk.old:
                break
            delta += len(hunk.added)
            continue
        if line < hunk.old:
            break
        if line < hunk.old + len(hunk.removed):
            return _inside(line - hunk.old, hunk)
        delta += len(hunk.added) - len(hunk.removed)
    return {line + delta}


def _inside(offset: int, hunk: _Hunk) -> set[int]:
    if not hunk.added:
        return {max(hunk.new, 1)}
    matcher = SequenceMatcher(None, hunk.removed, hunk.added, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if not i1 <= offset < i2:
            continue
        if tag == "delete":
            return {max(hunk.new + j1 - 1, 1)}
        if tag == "equal" or i2 - i1 == j2 - j1:
            return {hunk.new + j1 + offset - i1}
        return set(range(hunk.new + j1, hunk.new + j2))
    return set()


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


def _git(cwd: Path, *args: str, errors: str = "strict") -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            errors=errors,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GitError(str(exc)) from exc
    return completed.stdout
