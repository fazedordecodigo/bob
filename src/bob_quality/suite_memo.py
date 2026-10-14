from __future__ import annotations

import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from bob_quality.exit_codes import pytest_passed
from bob_quality.messages import Text, msg, reason
from bob_quality.npm_tools import run_vitest_under_c8
from bob_quality.tools import (
    PythonStarted,
    ToolError,
    export_coverage_json,
    export_coverage_xml,
    start_python_coverage,
)


@dataclass(frozen=True)
class HoldBroken:
    tool_exit: int


@dataclass(frozen=True)
class HoldUnavailable:
    reason: Text


@dataclass(frozen=True)
class PythonHold:
    started: PythonStarted


@dataclass(frozen=True)
class TypescriptHold:
    reports: Path


PythonState = PythonHold | HoldBroken | HoldUnavailable
TypescriptState = TypescriptHold | HoldBroken | HoldUnavailable
SuiteHold = PythonState | TypescriptState


@dataclass
class SuiteMemo:
    want_lcov: bool
    want_json: bool = False
    _python: SuiteHold | None = field(default=None, init=False)
    _typescript: SuiteHold | None = field(default=None, init=False)
    _python_dir: tempfile.TemporaryDirectory | None = field(default=None, init=False)
    _typescript_dir: tempfile.TemporaryDirectory | None = field(default=None, init=False)
    _json: str | None = field(default=None, init=False)
    _xml: str | None = field(default=None, init=False)
    _json_error: ToolError | None = field(default=None, init=False)
    _xml_error: ToolError | None = field(default=None, init=False)
    _closed: bool = field(default=False, init=False)

    def python_hold(
        self,
        cwd: Path,
        include: Sequence[str],
        coverage_file: Path | None,
    ) -> PythonState:
        if self._python is not None:
            return self._python
        self._python_dir = tempfile.TemporaryDirectory(prefix="bob-coverage-")
        try:
            started = start_python_coverage(
                cwd, include, Path(self._python_dir.name), coverage_file
            )
        except ToolError as exc:
            self._python = HoldUnavailable(reason(exc))
            return self._python
        if started.pytest_code is not None and not pytest_passed(started.pytest_code):
            self._python = HoldBroken(started.pytest_code)
            return self._python
        self._python = PythonHold(started)
        return self._python

    def python_json(
        self, cwd: Path, include: Sequence[str], coverage_file: Path | None
    ) -> str:
        return self._python_text(cwd, include, coverage_file, xml=False)

    def python_xml(
        self, cwd: Path, include: Sequence[str], coverage_file: Path | None
    ) -> str:
        return self._python_text(cwd, include, coverage_file, xml=True)

    def typescript_hold(
        self, cwd: Path, include: Sequence[str], exclude: Sequence[str]
    ) -> TypescriptState:
        if self._typescript is not None:
            return self._typescript
        self._typescript_dir = tempfile.TemporaryDirectory(prefix="bob-c8-")
        reports = Path(self._typescript_dir.name) / "coverage"
        try:
            code = run_vitest_under_c8(
                cwd,
                list(include),
                reports,
                list(exclude),
                self._reporters(),
            )
        except ToolError as exc:
            self._typescript = HoldUnavailable(reason(exc))
            return self._typescript
        if code != 0:
            self._typescript = HoldBroken(code)
            return self._typescript
        self._typescript = TypescriptHold(reports)
        return self._typescript

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for directory in (self._python_dir, self._typescript_dir):
            if directory is not None:
                directory.cleanup()

    def _reporters(self) -> tuple[str, ...]:
        names: list[str] = []
        if self.want_json:
            names.append("json")
        if self.want_lcov:
            names.append("lcov")
        if not names:
            names.append("json")
        return tuple(names)

    def _python_text(
        self,
        cwd: Path,
        include: Sequence[str],
        coverage_file: Path | None,
        *,
        xml: bool,
    ) -> str:
        hold = self.python_hold(cwd, include, coverage_file)
        if not isinstance(hold, PythonHold):
            raise _hold_error(hold)
        cached = self._cached_python(xml)
        if cached is not None:
            return cached
        text = self._read_export(cwd, hold, xml)
        self._store_python(xml, text)
        return text

    def _cached_python(self, xml: bool) -> str | None:
        error = self._xml_error if xml else self._json_error
        if error is not None:
            raise error
        return self._xml if xml else self._json

    def _read_export(self, cwd: Path, hold: PythonHold, xml: bool) -> str:
        if self._python_dir is None:
            raise ToolError(_missing_export(xml))
        dest = Path(self._python_dir.name) / _export_name(xml)
        try:
            _write_python_export(cwd, hold, dest, xml)
        except ToolError as exc:
            self._store_python_error(xml, exc)
            raise
        if not dest.is_file():
            return ""
        return dest.read_text()

    def _store_python(self, xml: bool, text: str) -> None:
        if xml:
            self._xml = text
            return
        self._json = text

    def _store_python_error(self, xml: bool, exc: ToolError) -> None:
        if xml:
            self._xml_error = exc
            return
        self._json_error = exc


def _missing_export(xml: bool) -> Text:
    if xml:
        return msg("coverage.no_xml")
    return msg("coverage.unreadable")


def _export_name(xml: bool) -> str:
    if xml:
        return "coverage.xml"
    return "coverage.json"


def _write_python_export(cwd: Path, hold: PythonHold, dest: Path, xml: bool) -> None:
    if xml:
        export_coverage_xml(cwd, hold.started, dest)
        return
    export_coverage_json(cwd, hold.started, dest)


def _hold_error(hold: SuiteHold) -> ToolError:
    if isinstance(hold, HoldBroken):
        return ToolError(msg("probe.baseline_failed"))
    if isinstance(hold, HoldUnavailable):
        return ToolError(hold.reason)
    return ToolError(msg("coverage.unreadable"))
