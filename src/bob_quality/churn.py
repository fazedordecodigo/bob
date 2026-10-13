from __future__ import annotations

import posixpath
import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Mapping, Protocol, Sequence

__all__ = (
    "ChurnSection",
    "ChurnMeasured",
    "ChurnUnavailable",
    "ChurnWindow",
    "FileChurn",
    "Hotspot",
    "MetricView",
    "measure_churn",
)

# --literal-pathspecs impede que um caractere de glob no caminho do diff
# amplie a listagem.
_GIT = ("git", "--literal-pathspecs")
_CI_LINE = re.compile(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) ([+-]\d{4})")
_COMMIT_LINE = re.compile(r"[0-9a-f]{40}")


class MetricView(Protocol):
    changed: bool
    file: str
    name: str
    start_line: int
    cc: int


@dataclass(frozen=True)
class ChurnWindow:
    days: int
    ends_on: date


@dataclass(frozen=True)
class FileChurn:
    path: str
    commits: int


@dataclass(frozen=True)
class Hotspot:
    file: str
    function: str
    start_line: int
    cc: int
    commits: int

    @property
    def hotspot(self) -> int:
        return self.commits * self.cc


@dataclass(frozen=True)
class ChurnMeasured:
    window: ChurnWindow
    files: tuple[FileChurn, ...]
    hotspots: tuple[Hotspot, ...]

    def __post_init__(self) -> None:
        paths = [item.path for item in self.files]
        if paths != sorted(paths) or len(set(paths)) != len(paths):
            raise ValueError("files")
        counts = {item.path: item.commits for item in self.files}
        ordered = tuple(
            sorted(
                self.hotspots,
                key=lambda row: (-row.hotspot, row.file, row.function, row.start_line),
            )
        )
        if self.hotspots != ordered:
            raise ValueError("hotspots")
        for row in self.hotspots:
            if counts.get(row.file) != row.commits:
                raise ValueError("hotspots")

    def file_count(self) -> int:
        return len(self.files)

    def module_names(self) -> tuple[str, ...]:
        return tuple(sorted({posixpath.dirname(item.path) or "." for item in self.files}))

    def module_count(self) -> int:
        return len(self.module_names())


@dataclass(frozen=True)
class ChurnUnavailable:
    pass


ChurnSection = ChurnMeasured | ChurnUnavailable


def measure_churn(
    cwd: Path,
    commit: str,
    window_days: int,
    changed_lines: Mapping[str, set[int]],
    include: tuple[str, ...],
    metrics: Sequence[MetricView],
) -> ChurnSection:
    paths = _included_paths(changed_lines, include)
    dated = _git_stdout(cwd, _date_argv(commit))
    if dated is None:
        return ChurnUnavailable()
    parsed = _commit_date(dated)
    if parsed is None:
        return ChurnUnavailable()
    ends_on, offset = parsed
    start = ends_on - timedelta(days=window_days - 1)
    since = f"{start.isoformat()} 00:00:00 {offset}"
    # O walker inclui o segundo exato de --until, então o fim do dia é
    # 23:59:59 e não a meia-noite seguinte.
    until = f"{ends_on.isoformat()} 23:59:59 {offset}"
    counted: list[FileChurn] = []
    for path in paths:
        logged = _git_stdout(cwd, _file_log_argv(commit, since, until, path))
        if logged is None:
            return ChurnUnavailable()
        counted.append(FileChurn(path, _commit_count(logged)))
    return ChurnMeasured(
        ChurnWindow(window_days, ends_on),
        tuple(counted),
        _hotspots(tuple(counted), metrics),
    )


def _date_argv(commit: str) -> tuple[str, ...]:
    return _GIT + ("log", "-1", "--no-notes", "--format=%ci", commit)


def _file_log_argv(commit: str, since: str, until: str, path: str) -> tuple[str, ...]:
    return _GIT + (
        "log",
        "--no-notes",
        "--format=%H",
        f"--since={since}",
        f"--until={until}",
        commit,
        "--",
        path,
    )


def _included_paths(
    changed_lines: Mapping[str, set[int]], include: tuple[str, ...]
) -> tuple[str, ...]:
    roots = tuple(PurePosixPath(entry) for entry in include)
    chosen = [path for path in changed_lines if _matches(path, roots)]
    return tuple(sorted(chosen))


def _matches(path: str, roots: tuple[PurePosixPath, ...]) -> bool:
    key = PurePosixPath(path)
    if key.is_absolute():
        return False
    for root in roots:
        if root.as_posix() == ".":
            return True
        if key == root or root in key.parents:
            return True
    return False


def _commit_date(stdout: str) -> tuple[date, str] | None:
    found = [
        match
        for line in stdout.splitlines()
        if (match := _CI_LINE.fullmatch(line)) is not None
    ]
    if len(found) != 1:
        return None
    match = found[0]
    day, clock, offset = match.group(1), match.group(2), match.group(3)
    try:
        datetime.strptime(f"{day} {clock}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return date.fromisoformat(day), offset


def _commit_count(stdout: str) -> int:
    return sum(1 for line in stdout.splitlines() if _COMMIT_LINE.fullmatch(line))


def _hotspots(
    files: tuple[FileChurn, ...], metrics: Sequence[MetricView]
) -> tuple[Hotspot, ...]:
    counts = {item.path: item.commits for item in files}
    seen: set[tuple[str, str, int]] = set()
    rows: list[Hotspot] = []
    for metric in metrics:
        if not metric.changed or metric.file not in counts:
            continue
        key = (metric.file, metric.name, metric.start_line)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            Hotspot(
                file=metric.file,
                function=metric.name,
                start_line=metric.start_line,
                cc=metric.cc,
                commits=counts[metric.file],
            )
        )
    rows.sort(key=lambda row: (-row.hotspot, row.file, row.function, row.start_line))
    return tuple(rows)


def _git_stdout(cwd: Path, argv: tuple[str, ...]) -> str | None:
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout
