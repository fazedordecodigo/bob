"""Escopo de diff: `git diff <base>...HEAD` → arquivos e linhas alteradas."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping, Set
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache
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


_SIMILAR = 0.6
_MAX_PAIRS = 10_000


def worktree_lines(cwd: Path, lines: dict[str, set[int]]) -> dict[str, set[int]]:
    """Leva as linhas do diff de HEAD para a árvore de trabalho, que é onde o gate mede.

    Uma linha fora dos hunks locais só se move. Dentro de um hunk, ela vai para a linha de
    mesmo texto ou, numa troca, para a nova linha parecida o bastante. Sem par confiável, vale
    o bloco novo inteiro. Uma linha apagada localmente sai do escopo, a não ser que marque
    uma remoção do commit: aí a âncora vai para a linha anterior que sobrou.
    """
    if not lines:
        return lines
    patch = _git(
        cwd,
        "diff",
        "--unified=0",
        "--inter-hunk-context=0",
        "--no-color",
        "--no-ext-diff",
        "--no-textconv",
        "--src-prefix=a/",
        "--dst-prefix=b/",
        "HEAD",
        "--",
        *sorted(lines),
        errors="surrogateescape",
    )
    hunks = _local_hunks(patch)
    return {file: _shift(touched, hunks.get(file, ())) for file, touched in lines.items()}


@dataclass(frozen=True)
class _Hunk:
    old: int
    new: int
    removed: tuple[str, ...] = ()
    added: tuple[str, ...] = ()


@dataclass
class _Parsed:
    old: int
    new: int
    removed: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)


def _local_hunks(patch: str) -> dict[str, tuple[_Hunk, ...]]:
    parsed: dict[str, list[_Parsed]] = {}
    current: list[_Parsed] = []
    in_header = True
    for line in patch.split("\n"):
        if line.startswith("diff --git "):
            in_header = True
        elif in_header and line.startswith("+++ "):
            current = parsed.setdefault(line[4:].removeprefix("b/"), [])
        elif match := FULL_HUNK_RE.match(line):
            in_header = False
            current.append(_Parsed(int(match.group(1)), int(match.group(3))))
        elif not in_header and current and line[:1] in ("+", "-"):
            (current[-1].added if line[0] == "+" else current[-1].removed).append(line[1:])
    return {
        file: tuple(_Hunk(h.old, h.new, tuple(h.removed), tuple(h.added)) for h in found)
        for file, found in parsed.items()
    }


def _shift(touched: set[int], hunks: tuple[_Hunk, ...]) -> set[int]:
    anchors = getattr(touched, "anchors", frozenset())
    moved: set[int] = set()
    for line in touched:
        moved.update(_shift_line(line, hunks, line in anchors))
    return moved


def _shift_line(line: int, hunks: tuple[_Hunk, ...], anchor: bool) -> set[int]:
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
            target, before = _targets(hunk)[line - hunk.old]
            return target or ({before} if anchor else set())
        delta += len(hunk.added) - len(hunk.removed)
    return {line + delta}


@lru_cache(maxsize=256)
def _targets(hunk: _Hunk) -> tuple[tuple[frozenset[int], int], ...]:
    """Para cada linha removida do hunk: as linhas novas que a substituem e a anterior que sobrou."""
    rows: list[tuple[frozenset[int], int]] = []
    matcher = SequenceMatcher(None, hunk.removed, hunk.added, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        before = max(hunk.new + j1 - 1, 1) if hunk.added else max(hunk.new, 1)
        if tag == "equal":
            rows.extend((frozenset({hunk.new + j1 + k}), before) for k in range(i2 - i1))
        elif tag == "delete":
            rows.extend((frozenset(), before) for _ in range(i1, i2))
        elif tag == "replace":
            rows.extend((target, before) for target in _pair(hunk, i1, i2, j1, j2))
    return tuple(rows)


def _pair(hunk: _Hunk, i1: int, i2: int, j1: int, j2: int) -> list[frozenset[int]]:
    block = frozenset(range(hunk.new + j1, hunk.new + j2))
    if (i2 - i1) * (j2 - j1) > _MAX_PAIRS:
        return [block] * (i2 - i1)
    paired: list[frozenset[int]] = []
    for old in hunk.removed[i1:i2]:
        best, score = -1, _SIMILAR
        for j in range(j1, j2):
            ratio = SequenceMatcher(None, old, hunk.added[j], autojunk=False)
            if ratio.real_quick_ratio() >= score and ratio.quick_ratio() >= score and ratio.ratio() >= score:
                best, score = j, ratio.ratio()
        paired.append(frozenset({hunk.new + best}) if best >= 0 else block)
    return paired


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
