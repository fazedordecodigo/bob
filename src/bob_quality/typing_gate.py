"""Gate de tipos: checkers do repositório e escapes no diff."""

from __future__ import annotations

import configparser
import io
import re
import shutil
import subprocess
import sys
import tempfile
import tokenize
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import ClassVar, Literal, NewType, TypedDict

def _unreachable(value: object) -> None:
    # O 3.10 não tem typing.assert_never. A mensagem é a do 3.11.
    text = repr(value)
    raise AssertionError(f"Expected code to be unreachable, but got: {text}")


try:
    from typing import assert_never
except ImportError:
    assert_never = _unreachable

from bob_quality.config import Config, SourceLanguage
from bob_quality.messages import Message, msg
from bob_quality.models import GateResult
from bob_quality.waivers import load_waivers

# No 3.10 o tomli vem com o pytest. Sem os dois parsers, um heading [tool.*] ainda conta.
_toml: ModuleType | None
if sys.version_info >= (3, 11):
    import tomllib

    _toml = tomllib
else:
    try:
        import tomli as tomllib

        _toml = tomllib
    except ImportError:
        _toml = None

CheckerName = Literal["mypy", "pyright", "tsc"]
EscapeCode = Literal["Any", "type: ignore", "as any", "@ts-ignore", "@ts-expect-error"]
MissReason = Literal[
    "missing_executable",
    "unparseable_output",
    "exit_outside_measurement",
    "crashed",
]
DiagnosticCode = NewType("DiagnosticCode", str)
WaiverId = NewType("WaiverId", str)
_Presence = Literal["absent", "spawn", "unreadable"]
_Section = Literal["missing", "absent", "present", "broken"]

MYPY_CLEAN_EXITS: frozenset[int] = frozenset({0})
MYPY_ERROR_EXITS: frozenset[int] = frozenset({1})
PYRIGHT_CLEAN_EXITS: frozenset[int] = frozenset({0})
PYRIGHT_ERROR_EXITS: frozenset[int] = frozenset({1})
TSC_CLEAN_EXITS: frozenset[int] = frozenset({0})
TSC_ERROR_EXITS: frozenset[int] = frozenset({1, 2})

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_TYPE_IGNORE = re.compile(r"#\s*type:\s*ignore")
_AS_ANY = re.compile(r"\bas[ \t]+any\b")
_TS_IGNORE = re.compile(r"(?<![A-Za-z0-9_])@ts-ignore(?![A-Za-z0-9_-])")
_TS_EXPECT = re.compile(r"(?<![A-Za-z0-9_])@ts-expect-error(?![A-Za-z0-9_-])")
_PYTHON_SUFFIXES = frozenset({".py", ".pyi"})
_TYPESCRIPT_SUFFIXES = frozenset({".ts", ".tsx"})


def _tool_language(tool: CheckerName) -> SourceLanguage:
    if tool == "mypy" or tool == "pyright":
        return "python"
    if tool == "tsc":
        return "typescript"
    assert_never(tool)


def waiver_id(file: str, line: int, code: str) -> WaiverId:
    """`typing:<file>:<line>:<code>`. A comparação é o texto inteiro."""
    return WaiverId(f"typing:{file}:{line}:{code}")


def on_diff_line(file: str, line: int, diff_lines: Mapping[str, set[int]]) -> bool:
    return line in diff_lines.get(file, ())


@dataclass(frozen=True)
class Diagnostic:
    file: str
    line: int
    code: DiagnosticCode
    tool: CheckerName


@dataclass(frozen=True)
class Escape:
    file: str
    line: int
    code: EscapeCode


@dataclass(frozen=True)
class Measured:
    tool: CheckerName
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True)
class Unmeasured:
    tool: CheckerName
    reason: MissReason
    code: int | None = None

    def __post_init__(self) -> None:
        if self.reason == "exit_outside_measurement":
            if self.code is None:
                raise ValueError(self.reason)
            return
        if self.code is not None:
            raise ValueError(self.reason)


CheckerRun = Measured | Unmeasured


@dataclass(frozen=True)
class Absent:
    language: SourceLanguage


@dataclass(frozen=True)
class Configured:
    language: SourceLanguage
    head: CheckerRun
    rest: tuple[CheckerRun, ...] = ()

    def runs(self) -> tuple[CheckerRun, ...]:
        return (self.head, *self.rest)


LanguageSlot = Absent | Configured
Subject = Diagnostic | Escape


@dataclass(frozen=True)
class Blocking:
    subject: Subject


@dataclass(frozen=True)
class Waived:
    subject: Subject


@dataclass(frozen=True)
class OffDiff:
    diagnostic: Diagnostic


Finding = Blocking | Waived | OffDiff


@dataclass(frozen=True)
class NoConfig:
    status: ClassVar[Literal["not_run"]] = "not_run"
    exit_code: ClassVar[Literal[0]] = 0


@dataclass(frozen=True)
class Clear:
    waived: tuple[Waived, ...]
    off_diff: tuple[OffDiff, ...]
    misses: tuple[Unmeasured, ...]
    status: ClassVar[Literal["passed"]] = "passed"
    exit_code: ClassVar[Literal[0]] = 0


@dataclass(frozen=True)
class Blocked:
    head: Blocking
    waived: tuple[Waived, ...]
    off_diff: tuple[OffDiff, ...]
    misses: tuple[Unmeasured, ...]
    rest: tuple[Blocking, ...] = ()
    status: ClassVar[Literal["failed"]] = "failed"
    exit_code: ClassVar[Literal[1]] = 1

    def blocking(self) -> tuple[Blocking, ...]:
        return (self.head, *self.rest)


@dataclass(frozen=True)
class NothingMeasured:
    head: Unmeasured
    rest: tuple[Unmeasured, ...] = ()
    status: ClassVar[Literal["not_run"]] = "not_run"
    exit_code: ClassVar[Literal[4]] = 4

    def misses(self) -> tuple[Unmeasured, ...]:
        return (self.head, *self.rest)


TypingVerdict = NoConfig | Clear | Blocked | NothingMeasured


class MeasuredCheckerJson(TypedDict):
    language: SourceLanguage
    tool: CheckerName
    outcome: Literal["measured"]


class UnmeasuredCheckerJson(TypedDict):
    language: SourceLanguage
    tool: CheckerName
    outcome: Literal["unmeasured"]
    reason: MissReason


class DiagnosticFindingJson(TypedDict):
    kind: Literal["diagnostic"]
    disposition: Literal["blocking", "waived", "off_diff"]
    file: str
    line: int
    code: str
    tool: CheckerName
    waiver_id: str


class EscapeFindingJson(TypedDict):
    kind: Literal["escape"]
    disposition: Literal["blocking", "waived"]
    file: str
    line: int
    code: EscapeCode
    waiver_id: str


class TypingJson(TypedDict):
    absent: list[SourceLanguage]
    checkers: list[MeasuredCheckerJson | UnmeasuredCheckerJson]
    findings: list[DiagnosticFindingJson | EscapeFindingJson]


@dataclass(frozen=True)
class _CheckerSpec:
    tool: CheckerName
    clean_exits: frozenset[int]
    error_exits: frozenset[int]
    diagnostic: re.Pattern[str]
    error_shaped: re.Pattern[str]
    sourceless: re.Pattern[str] | None
    presence: Callable[[Path], _Presence]
    argv: Callable[[str, tuple[str, ...], str | None], tuple[str, ...]]
    uses_cache: bool

    def __post_init__(self) -> None:
        overlap = self.clean_exits & self.error_exits
        if overlap:
            raise ValueError(overlap)


def _mypy_presence(cwd: Path) -> _Presence:
    if (cwd / "mypy.ini").is_file() or (cwd / ".mypy.ini").is_file():
        return "spawn"
    return _combine(
        _ini_section(cwd / "setup.cfg", "mypy"),
        _toml_section(cwd / "pyproject.toml", "mypy"),
    )


def _pyright_presence(cwd: Path) -> _Presence:
    if (cwd / "pyrightconfig.json").is_file():
        return "spawn"
    return _combine(_toml_section(cwd / "pyproject.toml", "pyright"))


def _tsc_presence(cwd: Path) -> _Presence:
    if (cwd / "tsconfig.json").is_file():
        return "spawn"
    return "absent"


def _combine(*states: _Section) -> _Presence:
    if any(state == "present" for state in states):
        return "spawn"
    if any(state == "broken" for state in states):
        return "unreadable"
    return "absent"


def _ini_section(path: Path, name: str) -> _Section:
    if not path.is_file():
        return "missing"
    parser = configparser.ConfigParser()
    try:
        parser.read_string(path.read_text(encoding="utf-8"))
    except (configparser.Error, OSError, UnicodeError):
        return "broken"
    if parser.has_section(name):
        return "present"
    return "absent"


def _toml_section(path: Path, name: str) -> _Section:
    if not path.is_file():
        return "missing"
    if _toml is None:
        return _heading(path, f"[tool.{name}]")
    try:
        with path.open("rb") as handle:
            data = _toml.load(handle)
    except _toml.TOMLDecodeError:
        return "broken"
    except OSError:
        return "broken"
    if _has_tool(data, name):
        return "present"
    return "absent"


def _heading(path: Path, heading: str) -> _Section:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return "broken"
    for line in text.splitlines():
        if line.strip() == heading:
            return "present"
    return "absent"


def _has_tool(data: object, name: str) -> bool:
    if not isinstance(data, dict):
        return False
    tool = data.get("tool")
    if not isinstance(tool, dict):
        return False
    return name in tool


def _mypy_argv(
    executable: str, include: tuple[str, ...], cache_dir: str | None
) -> tuple[str, ...]:
    return (
        executable,
        "--show-error-codes",
        "--no-error-summary",
        "--no-pretty",
        "--no-color-output",
        "--hide-error-context",
        "--no-incremental",
        "--cache-dir",
        cache_dir or "",
        *include,
    )


def _pyright_argv(
    executable: str, include: tuple[str, ...], cache_dir: str | None
) -> tuple[str, ...]:
    return (executable, *include)


def _tsc_argv(
    executable: str, include: tuple[str, ...], cache_dir: str | None
) -> tuple[str, ...]:
    return (
        executable,
        "--noEmit",
        "--pretty",
        "false",
        "--incremental",
        "false",
        "-p",
        "tsconfig.json",
    )


_CHECKERS: tuple[_CheckerSpec, ...] = (
    _CheckerSpec(
        tool="mypy",
        clean_exits=MYPY_CLEAN_EXITS,
        error_exits=MYPY_ERROR_EXITS,
        diagnostic=re.compile(
            r"^(?P<file>.+?):(?P<line>\d+):(?:\d+:)? error: .*\[(?P<code>[a-z0-9-]+)\]\s*$"
        ),
        error_shaped=re.compile(r": error:"),
        sourceless=None,
        presence=_mypy_presence,
        argv=_mypy_argv,
        uses_cache=True,
    ),
    _CheckerSpec(
        tool="pyright",
        clean_exits=PYRIGHT_CLEAN_EXITS,
        error_exits=PYRIGHT_ERROR_EXITS,
        diagnostic=re.compile(
            r"^(?P<file>.+):(?P<line>\d+):\d+ - error: .*\((?P<code>report[A-Za-z0-9]+)\)\s*$"
        ),
        error_shaped=re.compile(r" - error:"),
        sourceless=None,
        presence=_pyright_presence,
        argv=_pyright_argv,
        uses_cache=False,
    ),
    _CheckerSpec(
        tool="tsc",
        clean_exits=TSC_CLEAN_EXITS,
        error_exits=TSC_ERROR_EXITS,
        diagnostic=re.compile(
            r"^(?P<file>.+)\((?P<line>\d+),\d+\): error (?P<code>TS\d+): .*$"
        ),
        error_shaped=re.compile(r"error TS\d+:"),
        sourceless=re.compile(r"^error TS\d+:"),
        presence=_tsc_presence,
        argv=_tsc_argv,
        uses_cache=False,
    ),
)


def typing_verdict(
    slots: tuple[LanguageSlot, ...],
    escapes: tuple[Escape, ...],
    diff_lines: Mapping[str, set[int]],
    waiver_ids: frozenset[WaiverId],
) -> TypingVerdict:
    configured = tuple(slot for slot in slots if isinstance(slot, Configured))
    if not configured:
        return NoConfig()
    measured, misses = _runs(configured)
    if not measured:
        head, *rest = misses
        return NothingMeasured(head, tuple(rest))
    blocking, waived, off_diff = _place(measured, escapes, diff_lines, waiver_ids)
    if not blocking:
        return Clear(waived, off_diff, misses)
    head_blocking, *rest_blocking = blocking
    return Blocked(head_blocking, waived, off_diff, misses, tuple(rest_blocking))


def _runs(
    slots: tuple[Configured, ...],
) -> tuple[tuple[Measured, ...], tuple[Unmeasured, ...]]:
    measured: list[Measured] = []
    misses: list[Unmeasured] = []
    for slot in slots:
        for run in slot.runs():
            if isinstance(run, Measured):
                measured.append(run)
            elif isinstance(run, Unmeasured):
                misses.append(run)
            else:
                assert_never(run)
    return tuple(measured), tuple(misses)


def _place(
    measured: tuple[Measured, ...],
    escapes: tuple[Escape, ...],
    diff_lines: Mapping[str, set[int]],
    waiver_ids: frozenset[WaiverId],
) -> tuple[tuple[Blocking, ...], tuple[Waived, ...], tuple[OffDiff, ...]]:
    blocking: list[Blocking] = []
    waived: list[Waived] = []
    off_diff: list[OffDiff] = []
    for run in measured:
        for diagnostic in run.diagnostics:
            _place_diagnostic(diagnostic, diff_lines, waiver_ids, blocking, waived, off_diff)
    for escape in escapes:
        _place_escape(escape, waiver_ids, blocking, waived)
    return (
        tuple(sorted(blocking, key=_blocking_key)),
        tuple(sorted(waived, key=_waived_key)),
        tuple(sorted(off_diff, key=_off_key)),
    )


def _place_diagnostic(
    diagnostic: Diagnostic,
    diff_lines: Mapping[str, set[int]],
    waiver_ids: frozenset[WaiverId],
    blocking: list[Blocking],
    waived: list[Waived],
    off_diff: list[OffDiff],
) -> None:
    if not on_diff_line(diagnostic.file, diagnostic.line, diff_lines):
        off_diff.append(OffDiff(diagnostic))
        return
    if waiver_id(diagnostic.file, diagnostic.line, diagnostic.code) in waiver_ids:
        waived.append(Waived(diagnostic))
        return
    blocking.append(Blocking(diagnostic))


def _place_escape(
    escape: Escape,
    waiver_ids: frozenset[WaiverId],
    blocking: list[Blocking],
    waived: list[Waived],
) -> None:
    if waiver_id(escape.file, escape.line, escape.code) in waiver_ids:
        waived.append(Waived(escape))
        return
    blocking.append(Blocking(escape))


def _blocking_key(item: Blocking) -> tuple[str, int, str, str]:
    return _subject_key(item.subject)


def _waived_key(item: Waived) -> tuple[str, int, str, str]:
    return _subject_key(item.subject)


def _off_key(item: OffDiff) -> tuple[str, int, str, str]:
    return _subject_key(item.diagnostic)


def _subject_key(subject: Subject) -> tuple[str, int, str, str]:
    tool = subject.tool if isinstance(subject, Diagnostic) else ""
    return (subject.file, subject.line, subject.code, tool)


def run_typing_gate(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
) -> tuple[GateResult, Literal[0, 1, 4], dict[str, str], TypingJson]:
    slots, versions = _slots(cwd, config)
    configured = frozenset(slot.language for slot in slots if isinstance(slot, Configured))
    escapes = _scan_escapes(cwd, config, diff_lines, configured)
    verdict = typing_verdict(slots, escapes, diff_lines, _waiver_ids(cwd))
    result, code = _gate_result(verdict)
    return result, code, versions, _typing_json(slots, verdict)


def _slots(cwd: Path, config: Config) -> tuple[tuple[LanguageSlot, ...], dict[str, str]]:
    slots: list[LanguageSlot] = []
    versions: dict[str, str] = {}
    for language in config.languages:
        slot, found = _language_slot(cwd, config, language)
        slots.append(slot)
        versions.update(found)
    return tuple(slots), versions


def _language_slot(
    cwd: Path, config: Config, language: SourceLanguage
) -> tuple[LanguageSlot, dict[str, str]]:
    runs: list[CheckerRun] = []
    versions: dict[str, str] = {}
    for spec in _CHECKERS:
        if _tool_language(spec.tool) != language:
            continue
        run, version = _one_checker(cwd, config, spec)
        if run is None:
            continue
        runs.append(run)
        if version is not None:
            versions[spec.tool] = version
    if not runs:
        return Absent(language), versions
    return Configured(language, runs[0], tuple(runs[1:])), versions


def _one_checker(
    cwd: Path, config: Config, spec: _CheckerSpec
) -> tuple[CheckerRun | None, str | None]:
    state = spec.presence(cwd)
    if state == "absent":
        return None, None
    if state == "unreadable":
        return Unmeasured(spec.tool, "unparseable_output"), None
    if state == "spawn":
        return _spawn(cwd, config, spec)
    assert_never(state)


def _spawn(
    cwd: Path, config: Config, spec: _CheckerSpec
) -> tuple[CheckerRun, str | None]:
    executable = shutil.which(spec.tool)
    if executable is None:
        return Unmeasured(spec.tool, "missing_executable"), None
    try:
        completed = _invoke(cwd, executable, spec, config.include)
    except FileNotFoundError:
        return Unmeasured(spec.tool, "missing_executable"), None
    except OSError:
        return Unmeasured(spec.tool, "crashed"), None
    text = _output(completed.stdout, completed.stderr)
    run = _classify(
        spec, completed.returncode, text, cwd, config.include, config.exclude
    )
    return run, _version(executable, cwd)


def _invoke(
    cwd: Path, executable: str, spec: _CheckerSpec, include: tuple[str, ...]
) -> subprocess.CompletedProcess[str]:
    if spec.uses_cache:
        # O cache fica fora do repositório e some quando o processo volta.
        with tempfile.TemporaryDirectory(prefix="bob-mypy-") as cache:
            return _run(cwd, spec.argv(executable, include, cache))
    return _run(cwd, spec.argv(executable, include, None))


def _run(cwd: Path, argv: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        errors="replace",
        stdin=subprocess.DEVNULL,
    )


def _version(executable: str, cwd: Path) -> str:
    try:
        completed = _run(cwd, (executable, "--version"))
    except OSError:
        return "unknown"
    for line in _output(completed.stdout, completed.stderr).splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return "unknown"


def _output(stdout: str, stderr: str) -> str:
    if stdout and stderr and not stdout.endswith("\n"):
        text = stdout + "\n" + stderr
    else:
        text = stdout + stderr
    return _ANSI.sub("", text)


@dataclass(frozen=True)
class _Collected:
    diagnostics: tuple[Diagnostic, ...]
    malformed: bool
    saw_diagnostic: bool


def _classify(
    spec: _CheckerSpec,
    exit_code: int,
    text: str,
    cwd: Path,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
) -> CheckerRun:
    if exit_code not in spec.clean_exits | spec.error_exits:
        return Unmeasured(spec.tool, "exit_outside_measurement", code=exit_code)
    collected = _collect_lines(spec, text, cwd)
    if _rejected(spec, exit_code, collected):
        return Unmeasured(spec.tool, "unparseable_output")
    kept = tuple(
        item
        for item in collected.diagnostics
        if _in_scope(item.file, include, exclude)
    )
    return Measured(spec.tool, kept)


def _rejected(spec: _CheckerSpec, exit_code: int, collected: _Collected) -> bool:
    if collected.malformed:
        return True
    if exit_code in spec.clean_exits:
        return collected.saw_diagnostic
    return not collected.saw_diagnostic


def _collect_lines(spec: _CheckerSpec, text: str, cwd: Path) -> _Collected:
    diagnostics: list[Diagnostic] = []
    malformed = False
    saw_diagnostic = False
    for raw in text.splitlines():
        parsed = _parse_line(spec, raw.strip(), cwd)
        if parsed is None or parsed == "sourceless":
            continue
        if parsed == "malformed":
            malformed = True
            continue
        saw_diagnostic = True
        diagnostics.append(parsed)
    return _Collected(_dedupe_diagnostics(diagnostics), malformed, saw_diagnostic)


def _parse_line(
    spec: _CheckerSpec, line: str, cwd: Path
) -> Diagnostic | Literal["sourceless", "malformed"] | None:
    if line == "":
        return None
    match = spec.diagnostic.match(line)
    if match is not None:
        return _diagnostic(spec, match, cwd)
    if spec.sourceless is not None and spec.sourceless.match(line):
        return "sourceless"
    if spec.error_shaped.search(line):
        return "malformed"
    return None


def _diagnostic(spec: _CheckerSpec, match: re.Match[str], cwd: Path) -> Diagnostic:
    raw = match.group("file").strip()
    relative = _repo_relative(cwd, raw)
    return Diagnostic(
        file=relative if relative is not None else raw.replace("\\", "/"),
        line=int(match.group("line")),
        code=DiagnosticCode(match.group("code")),
        tool=spec.tool,
    )


def _dedupe_diagnostics(items: list[Diagnostic]) -> tuple[Diagnostic, ...]:
    seen: set[tuple[str, int, str, str]] = set()
    kept: list[Diagnostic] = []
    for item in items:
        key = (item.file, item.line, item.code, item.tool)
        if key in seen:
            continue
        seen.add(key)
        kept.append(item)
    return tuple(kept)


def _repo_relative(cwd: Path, raw: str) -> str | None:
    text = raw.strip().replace("\\", "/")
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = cwd / candidate
    try:
        relative = candidate.resolve().relative_to(cwd.resolve())
    except ValueError:
        return None
    posix = relative.as_posix()
    if posix == ".":
        return None
    return posix


def _in_scope(file: str, include: tuple[str, ...], exclude: tuple[str, ...]) -> bool:
    parts = _segments(file)
    if any(part in exclude for part in parts):
        return False
    return _under_include(parts, include)


def _under_include(parts: tuple[str, ...], include: tuple[str, ...]) -> bool:
    return any(parts[: len(prefix)] == prefix for prefix in map(_segments, include) if prefix)


def _segments(entry: str) -> tuple[str, ...]:
    return tuple(part for part in PurePosixPath(entry).parts if part not in {"", "."})


def _scan_escapes(
    cwd: Path,
    config: Config,
    diff_lines: Mapping[str, set[int]],
    configured: frozenset[SourceLanguage],
) -> tuple[Escape, ...]:
    found: list[Escape] = []
    for file, lines in diff_lines.items():
        found.extend(_file_escapes(cwd, config, file, lines, configured))
    return _dedupe_escapes(found)


def _file_escapes(
    cwd: Path,
    config: Config,
    file: str,
    lines: set[int],
    configured: frozenset[SourceLanguage],
) -> tuple[Escape, ...]:
    if not lines or not _in_scope(file, config.include, config.exclude):
        return ()
    suffix = PurePosixPath(file).suffix
    if suffix in _PYTHON_SUFFIXES and "python" in configured:
        return _python_file(cwd, file, lines)
    if suffix in _TYPESCRIPT_SUFFIXES and "typescript" in configured:
        return _typescript_file(cwd, file, lines)
    return ()


def _python_file(cwd: Path, file: str, lines: set[int]) -> tuple[Escape, ...]:
    text = _read_source(cwd, file)
    if text is None:
        return ()
    try:
        return _python_tokens(text, file, lines)
    except tokenize.TokenError:
        # O tokenize para no meio do arquivo. As linhas do diff ainda estão no texto.
        return _python_line_fallback(text, file, lines)


def _python_tokens(text: str, file: str, lines: set[int]) -> tuple[Escape, ...]:
    found: list[Escape] = []
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        line = token.start[0]
        if line not in lines:
            continue
        if token.type == tokenize.NAME and token.string == "Any":
            found.append(Escape(file, line, "Any"))
        elif token.type == tokenize.COMMENT and _TYPE_IGNORE.search(token.string):
            found.append(Escape(file, line, "type: ignore"))
    return tuple(found)


def _python_line_fallback(text: str, file: str, lines: set[int]) -> tuple[Escape, ...]:
    found: list[Escape] = []
    name = re.compile(r"(?<![A-Za-z0-9_])Any(?![A-Za-z0-9_])")
    for number, line in enumerate(text.splitlines(), start=1):
        if number not in lines:
            continue
        if name.search(line):
            found.append(Escape(file, number, "Any"))
        if _TYPE_IGNORE.search(line):
            found.append(Escape(file, number, "type: ignore"))
    return tuple(found)


def _typescript_file(cwd: Path, file: str, lines: set[int]) -> tuple[Escape, ...]:
    text = _read_source(cwd, file)
    if text is None:
        return ()
    code, comments = _partition_typescript(text)
    found: list[Escape] = []
    for match in _AS_ANY.finditer(code):
        number = _line_number(text, match.start())
        if number in lines:
            found.append(Escape(file, number, "as any"))
    for pattern, spelling in ((_TS_IGNORE, "@ts-ignore"), (_TS_EXPECT, "@ts-expect-error")):
        for match in pattern.finditer(comments):
            number = _line_number(text, match.start())
            if number in lines:
                found.append(Escape(file, number, spelling))
    return tuple(found)


def _read_source(cwd: Path, file: str) -> str | None:
    path = cwd / file
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _partition_typescript(text: str) -> tuple[str, str]:
    code = list(text)
    comments = [" "] * len(text)
    _scan_typescript(text, code, comments, 0, len(text))
    return "".join(code), "".join(comments)


def _scan_typescript(
    text: str, code: list[str], comments: list[str], start: int, end: int
) -> int:
    index = start
    while index < end:
        if text.startswith("//", index):
            index = _take_comment(text, code, comments, index, end, line=True)
            continue
        if text.startswith("/*", index):
            index = _take_comment(text, code, comments, index, end, line=False)
            continue
        char = text[index]
        if char in {"'", '"', "`"}:
            index = _take_string(text, code, comments, index, end, char)
            continue
        index += 1
    return index


def _take_comment(
    text: str,
    code: list[str],
    comments: list[str],
    start: int,
    end: int,
    *,
    line: bool,
) -> int:
    if line:
        newline = text.find("\n", start, end)
        stop = end if newline < 0 else newline
    else:
        closer = text.find("*/", start + 2, end)
        stop = end if closer < 0 else closer + 2
    for cursor in range(start, stop):
        comments[cursor] = text[cursor]
        if text[cursor] != "\n":
            code[cursor] = " "
    return max(stop, start + 1)


def _take_string(
    text: str,
    code: list[str],
    comments: list[str],
    start: int,
    end: int,
    quote: str,
) -> int:
    cursor = start + 1
    while cursor < end:
        step = _string_step(text, code, comments, cursor, end, quote)
        if step is None:
            return cursor + 1
        if step == cursor:
            return cursor
        cursor = step
    return max(cursor, start + 1)


def _string_step(
    text: str,
    code: list[str],
    comments: list[str],
    cursor: int,
    end: int,
    quote: str,
) -> int | None:
    special = _string_special(text, code, comments, cursor, end, quote)
    if special is not False:
        return special
    if text[cursor] == quote:
        return None
    if text[cursor] == "\n" and quote != "`":
        return cursor
    _blank(code, cursor)
    return cursor + 1


def _string_special(
    text: str,
    code: list[str],
    comments: list[str],
    cursor: int,
    end: int,
    quote: str,
) -> int | None | bool:
    if text[cursor] == "\\" and cursor + 1 < end:
        _blank(code, cursor)
        _blank(code, cursor + 1)
        return cursor + 2
    if quote == "`" and text.startswith("${", cursor):
        _blank(code, cursor)
        _blank(code, cursor + 1)
        return _take_interpolation(text, code, comments, cursor + 2, end)
    return False


def _take_interpolation(
    text: str, code: list[str], comments: list[str], start: int, end: int
) -> int:
    depth = 1
    cursor = start
    while cursor < end and depth > 0:
        cursor, depth, closed = _interpolation_step(text, code, comments, cursor, end, depth)
        if closed:
            return cursor
    return max(cursor, start)


def _interpolation_step(
    text: str,
    code: list[str],
    comments: list[str],
    cursor: int,
    end: int,
    depth: int,
) -> tuple[int, int, bool]:
    if text.startswith("//", cursor):
        return _take_comment(text, code, comments, cursor, end, line=True), depth, False
    if text.startswith("/*", cursor):
        return _take_comment(text, code, comments, cursor, end, line=False), depth, False
    char = text[cursor]
    if char in {"'", '"', "`"}:
        return _take_string(text, code, comments, cursor, end, char), depth, False
    if char == "{":
        return cursor + 1, depth + 1, False
    if char == "}":
        closed = depth == 1
        return cursor + 1, depth - 1, closed
    return cursor + 1, depth, False


def _blank(code: list[str], index: int) -> None:
    if code[index] != "\n":
        code[index] = " "


def _dedupe_escapes(items: list[Escape] | tuple[Escape, ...]) -> tuple[Escape, ...]:
    seen: set[tuple[str, int, str]] = set()
    kept: list[Escape] = []
    for item in items:
        key = (item.file, item.line, item.code)
        if key in seen:
            continue
        seen.add(key)
        kept.append(item)
    return tuple(kept)


def _waiver_ids(cwd: Path) -> frozenset[WaiverId]:
    return frozenset(
        WaiverId(item.id) for item in load_waivers(cwd) if item.id.startswith("typing:")
    )


def _gate_result(verdict: TypingVerdict) -> tuple[GateResult, Literal[0, 1, 4]]:
    if isinstance(verdict, NoConfig):
        return GateResult("typing", verdict.status, msg("typing.no_config")), verdict.exit_code
    if isinstance(verdict, Clear):
        return GateResult("typing", verdict.status, None), verdict.exit_code
    if isinstance(verdict, Blocked):
        return (
            GateResult("typing", verdict.status, _subject_id(verdict.head.subject)),
            verdict.exit_code,
        )
    if isinstance(verdict, NothingMeasured):
        return GateResult("typing", verdict.status, _miss_text(verdict.head)), verdict.exit_code
    assert_never(verdict)


def _subject_id(subject: Subject) -> str:
    return waiver_id(subject.file, subject.line, subject.code)


def _miss_text(miss: Unmeasured) -> Message:
    if miss.reason == "missing_executable":
        return msg("typing.missing_executable", tool=miss.tool)
    if miss.reason == "unparseable_output":
        return msg("typing.unparseable", tool=miss.tool)
    if miss.reason == "exit_outside_measurement":
        return msg("typing.exited", tool=miss.tool, code=miss.code)
    if miss.reason == "crashed":
        return msg("typing.crashed", tool=miss.tool)
    assert_never(miss.reason)


def _typing_json(slots: tuple[LanguageSlot, ...], verdict: TypingVerdict) -> TypingJson:
    return {
        "absent": [slot.language for slot in slots if isinstance(slot, Absent)],
        "checkers": [
            row
            for slot in slots
            if isinstance(slot, Configured)
            for row in _checker_rows(slot)
        ],
        "findings": _finding_rows(verdict),
    }


def _checker_rows(
    slot: Configured,
) -> list[MeasuredCheckerJson | UnmeasuredCheckerJson]:
    rows: list[MeasuredCheckerJson | UnmeasuredCheckerJson] = []
    for run in slot.runs():
        if isinstance(run, Measured):
            rows.append(
                {"language": slot.language, "tool": run.tool, "outcome": "measured"}
            )
            continue
        if isinstance(run, Unmeasured):
            rows.append(
                {
                    "language": slot.language,
                    "tool": run.tool,
                    "outcome": "unmeasured",
                    "reason": run.reason,
                }
            )
            continue
        assert_never(run)
    return rows


def _finding_rows(
    verdict: TypingVerdict,
) -> list[DiagnosticFindingJson | EscapeFindingJson]:
    if isinstance(verdict, (NoConfig, NothingMeasured)):
        return []
    if isinstance(verdict, Clear):
        found: tuple[Finding, ...] = (*verdict.waived, *verdict.off_diff)
    elif isinstance(verdict, Blocked):
        found = (*verdict.blocking(), *verdict.waived, *verdict.off_diff)
    else:
        assert_never(verdict)
    return [_finding_row(item) for item in sorted(found, key=_finding_key)]


def _finding_key(item: Finding) -> tuple[str, int, str, str]:
    if isinstance(item, OffDiff):
        return _subject_key(item.diagnostic)
    if isinstance(item, (Blocking, Waived)):
        return _subject_key(item.subject)
    assert_never(item)


def _finding_row(item: Finding) -> DiagnosticFindingJson | EscapeFindingJson:
    if isinstance(item, OffDiff):
        return _diagnostic_row(item.diagnostic, "off_diff")
    if isinstance(item, Blocking):
        return _subject_row(item.subject, "blocking")
    if isinstance(item, Waived):
        return _subject_row(item.subject, "waived")
    assert_never(item)


def _subject_row(
    subject: Subject, disposition: Literal["blocking", "waived"]
) -> DiagnosticFindingJson | EscapeFindingJson:
    if isinstance(subject, Diagnostic):
        return _diagnostic_row(subject, disposition)
    if isinstance(subject, Escape):
        return _escape_row(subject, disposition)
    assert_never(subject)


def _diagnostic_row(
    diagnostic: Diagnostic, disposition: Literal["blocking", "waived", "off_diff"]
) -> DiagnosticFindingJson:
    return {
        "kind": "diagnostic",
        "disposition": disposition,
        "file": diagnostic.file,
        "line": diagnostic.line,
        "code": diagnostic.code,
        "tool": diagnostic.tool,
        "waiver_id": waiver_id(diagnostic.file, diagnostic.line, diagnostic.code),
    }


def _escape_row(
    escape: Escape, disposition: Literal["blocking", "waived"]
) -> EscapeFindingJson:
    return {
        "kind": "escape",
        "disposition": disposition,
        "file": escape.file,
        "line": escape.line,
        "code": escape.code,
        "waiver_id": waiver_id(escape.file, escape.line, escape.code),
    }
