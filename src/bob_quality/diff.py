"""Escopo de diff: `git diff <base>...HEAD` → arquivos e linhas alteradas."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Mapping, Set
from dataclasses import dataclass, field
from pathlib import Path

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
FULL_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_NO_NEWLINE = chr(92)
_PATHSPEC_MODES = ("GIT_GLOB_PATHSPECS", "GIT_NOGLOB_PATHSPECS", "GIT_ICASE_PATHSPECS")


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


@dataclass
class _Hunk:
    old: int
    removed: int
    new: int
    added: int
    old_text: list[str] = field(default_factory=list)
    new_text: list[str] = field(default_factory=list)
    old_lacks_newline: bool = False


def worktree_lines(cwd: Path, lines: dict[str, set[int]]) -> dict[str, set[int]]:
    """Leva as linhas do diff de HEAD para a árvore de trabalho, que é onde o gate mede.

    Uma linha fora dos hunks locais só se move. Uma linha que um hunk local substitui vale o
    bloco novo inteiro, a não ser que seja a última do arquivo e só tenha ganhado a quebra
    final. Uma linha apagada localmente sai do escopo, a não ser que marque uma remoção do
    commit: aí a âncora vai para a linha anterior que sobrou.
    """
    names = _git_raw(cwd, "diff", "--name-only", "-z", "--no-renames", "HEAD").split(b"\0")
    edited = {name.decode(errors="surrogateescape") for name in names}
    return {
        file: _shift(touched, _local_hunks(cwd, file)) if file in edited else touched
        for file, touched in lines.items()
    }


def _local_hunks(cwd: Path, file: str) -> list[_Hunk]:
    patch = _git_raw(
        cwd,
        "diff",
        "--unified=0",
        "--inter-hunk-context=0",
        "--no-color",
        "--no-ext-diff",
        "--no-textconv",
        "--no-renames",
        "HEAD",
        "--",
        file,
    ).decode(errors="surrogateescape")
    hunks: list[_Hunk] = []
    previous = ""
    for line in patch.split("\n"):
        if match := FULL_HUNK_RE.match(line):
            old, old_count, new, new_count = (int(group or "1") for group in match.groups())
            hunks.append(_Hunk(old, old_count, new, new_count))
        elif hunks and line[:1] in ("+", "-"):
            (hunks[-1].new_text if line[0] == "+" else hunks[-1].old_text).append(line[1:])
        elif hunks and line.startswith(_NO_NEWLINE) and previous[:1] == "-":
            hunks[-1].old_lacks_newline = True
        previous = line
    return hunks


def _gained_newline(index: int, hunk: _Hunk) -> bool:
    """A última linha de HEAD, sem quebra final, que segue com o mesmo texto na mesma posição."""
    return (
        hunk.old_lacks_newline
        and index == len(hunk.old_text) - 1
        and hunk.new_text[index : index + 1] == hunk.old_text[index:]
    )


def _git_raw(cwd: Path, *args: str) -> bytes:
    env = {key: value for key, value in os.environ.items() if key not in _PATHSPEC_MODES}
    try:
        return subprocess.run(
            ["git", "--literal-pathspecs", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            env=env,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GitError(str(exc)) from exc


def _shift(touched: set[int], hunks: list[_Hunk]) -> set[int]:
    anchors = getattr(touched, "anchors", frozenset())
    moved: set[int] = set()
    for line in touched:
        moved.update(_shift_line(line, hunks, line in anchors))
    return moved


def _shift_line(line: int, hunks: list[_Hunk], anchor: bool) -> set[int]:
    delta = 0
    for hunk in hunks:
        if line < hunk.old + (hunk.removed == 0):
            break
        if line < hunk.old + hunk.removed:
            return _replaced(line - hunk.old, hunk, anchor)
        delta += hunk.added - hunk.removed
    return {line + delta}


def _replaced(index: int, hunk: _Hunk, anchor: bool) -> set[int]:
    if _gained_newline(index, hunk):
        return {hunk.new + index}
    if hunk.added:
        return set(range(hunk.new, hunk.new + hunk.added))
    return {max(hunk.new, 1)} if anchor else set()


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
