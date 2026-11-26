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


class ChangedLines(set[int]):
    """Linhas do lado novo de um arquivo. `anchors` são as que só marcam uma remoção do commit."""

    anchors: frozenset[int] = frozenset()


def worktree_lines(cwd: Path, lines: dict[str, set[int]]) -> dict[str, set[int]]:
    """Leva as linhas do diff de HEAD para a árvore de trabalho, que é onde o gate mede.

    Uma linha fora dos hunks locais só se move. Dentro de um hunk, ela vai para a linha de
    mesmo texto. Sem linha igual, a correspondência é ambígua e vale o bloco novo inteiro.
    Uma linha apagada localmente sai do escopo, a não ser que marque uma remoção do commit:
    aí a âncora vai para a linha anterior que sobrou.
    """
    if not lines:
        return lines
    patch = _git_raw(
        cwd,
        "diff",
        "--unified=0",
        "--inter-hunk-context=0",
        "--no-color",
        "--no-ext-diff",
        "--no-textconv",
        "--dst-prefix=b/",
        "HEAD",
    ).decode("utf-8", "surrogateescape")
    hunks = _local_hunks(patch) if patch else {}
    return {
        file: _shift(touched, hunks[file]) if file in hunks else touched
        for file, touched in lines.items()
    }


@dataclass
class _Hunk:
    old: int
    new: int
    removed: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    targets: list[set[int]] = field(default_factory=list)


def _local_hunks(patch: str) -> dict[str, list[_Hunk]]:
    hunks: dict[str, list[_Hunk]] = {}
    current: list[_Hunk] = []
    pending = 0
    for line in patch.split("\n"):
        if pending and not line.startswith("\\"):
            pending -= 1
            (current[-1].added if line.startswith("+") else current[-1].removed).append(line[1:])
        elif line.startswith("+++ "):
            current = hunks.setdefault(line[4:].removeprefix("b/"), [])
        elif match := FULL_HUNK_RE.match(line):
            old, old_count, new, new_count = (int(group or "1") for group in match.groups())
            current.append(_Hunk(old, new))
            pending = old_count + new_count
    return hunks


def _targets(hunk: _Hunk) -> list[set[int]]:
    """Para cada linha removida: as linhas novas que a substituem, ou nenhuma se foi apagada."""
    targets: list[set[int]] = []
    matcher = SequenceMatcher(None, hunk.removed, hunk.added, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            targets.extend({hunk.new + j1 + k} for k in range(i2 - i1))
        elif tag != "insert":
            block = set(range(hunk.new + j1, hunk.new + j2))
            targets.extend(set(block) for _ in range(i1, i2))
    return targets


def _shift(touched: set[int], hunks: list[_Hunk]) -> set[int]:
    anchors = getattr(touched, "anchors", frozenset())
    for hunk in hunks:
        hunk.targets = _targets(hunk)
    moved: set[int] = set()
    for line in touched:
        moved.update(_shift_line(line, hunks, line in anchors))
    return moved


def _shift_line(line: int, hunks: list[_Hunk], anchor: bool) -> set[int]:
    delta = 0
    for hunk in hunks:
        removed = len(hunk.removed)
        if line < hunk.old + (removed == 0):
            break
        if line < hunk.old + removed:
            return hunk.targets[line - hunk.old] or _anchor(line, hunk, anchor)
        delta += len(hunk.added) - removed
    return {line + delta}


def _anchor(line: int, hunk: _Hunk, anchor: bool) -> set[int]:
    if not anchor:
        return set()
    survivors = [target for target in hunk.targets[: line - hunk.old] if target]
    return {max(survivors[-1])} if survivors else {max(hunk.new - bool(hunk.added), 1)}


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


def _git_raw(cwd: Path, *args: str) -> bytes:
    try:
        return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GitError(str(exc)) from exc
