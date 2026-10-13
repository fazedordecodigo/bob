from __future__ import annotations

from pathlib import Path

import pytest

from bob_quality.messages import msg
from bob_quality.suite_memo import (
    HoldBroken,
    HoldUnavailable,
    PythonHold,
    SuiteMemo,
    _hold_error,
    _missing_export,
)
from bob_quality.tools import PythonStarted, ToolError
from helpers import in_both


def _started(tmp_path: Path, code: int | None) -> PythonStarted:
    return PythonStarted(code, tmp_path / "coverage.rc")


def _patch_start(monkeypatch: pytest.MonkeyPatch, started: PythonStarted, seen: list[tuple[object, ...]]) -> None:
    def start(cwd: Path, include: tuple[str, ...], work: Path, coverage_file: Path | None) -> PythonStarted:
        seen.append((cwd, tuple(include), work, coverage_file))
        return started

    monkeypatch.setattr("bob_quality.suite_memo.start_python_coverage", start)


def test_python_hold_starts_once_under_the_coverage_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[object, ...]] = []
    started = _started(tmp_path, 0)
    _patch_start(monkeypatch, started, seen)
    memo = SuiteMemo(want_lcov=False)
    coverage = tmp_path / "data"

    first = memo.python_hold(tmp_path, ("src",), coverage)
    second = memo.python_hold(tmp_path, ("other",), None)

    assert first is second
    assert isinstance(first, PythonHold)
    assert first.started is started
    assert len(seen) == 1
    cwd, include, work, coverage_file = seen[0]
    assert (cwd, include, coverage_file) == (tmp_path, ("src",), coverage)
    assert work.name.startswith("bob-coverage-")
    assert memo._python_dir is not None
    assert Path(memo._python_dir.name) == work


def test_python_hold_keeps_a_reused_coverage_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[object, ...]] = []
    _patch_start(monkeypatch, _started(tmp_path, None), seen)
    memo = SuiteMemo(want_lcov=True, want_json=True)

    hold = memo.python_hold(tmp_path, ("src",), tmp_path / "data")

    assert isinstance(hold, PythonHold)
    assert hold.started.pytest_code is None
    assert len(seen) == 1


def test_python_hold_records_a_broken_baseline_and_reuses_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[object, ...]] = []
    _patch_start(monkeypatch, _started(tmp_path, 1), seen)
    memo = SuiteMemo(want_lcov=False)

    first = memo.python_hold(tmp_path, ("src",), None)
    second = memo.python_hold(tmp_path, ("src",), None)

    assert first is second
    assert isinstance(first, HoldBroken)
    assert first.tool_exit == 1
    assert len(seen) == 1


def test_pytest_without_tests_is_a_usable_hold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_start(monkeypatch, _started(tmp_path, 5), [])
    memo = SuiteMemo(want_lcov=False)

    hold = memo.python_hold(tmp_path, ("src",), None)

    assert isinstance(hold, PythonHold)
    assert hold.started.pytest_code == 5


def test_python_hold_records_the_tool_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(cwd: Path, include: tuple[str, ...], work: Path, coverage_file: Path | None) -> PythonStarted:
        raise ToolError(msg("tool.missing", tool="coverage"))

    monkeypatch.setattr("bob_quality.suite_memo.start_python_coverage", boom)
    memo = SuiteMemo(want_lcov=False)

    first = memo.python_hold(tmp_path, ("src",), None)
    second = memo.python_hold(tmp_path, ("src",), None)

    assert first is second
    assert isinstance(first, HoldUnavailable)
    assert in_both(first.reason) == ("missing tool: coverage", "ferramenta ausente: coverage")


def test_json_export_is_read_once_and_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    started = _started(tmp_path, 0)
    seen: list[tuple[object, ...]] = []
    _patch_start(monkeypatch, started, seen)
    calls: list[tuple[object, ...]] = []
    flags: list[tuple[object, ...]] = []
    real_text = SuiteMemo._python_text

    def export(cwd: Path, got: PythonStarted, dest: Path) -> None:
        calls.append((cwd, got, dest.name))
        dest.write_text('{"files": {}}')

    def spy_text(
        self: SuiteMemo,
        cwd: Path,
        include: tuple[str, ...],
        coverage_file: Path | None,
        *,
        xml: bool,
    ) -> str:
        flags.append((cwd, tuple(include), coverage_file, xml))
        return real_text(self, cwd, include, coverage_file, xml=xml)

    monkeypatch.setattr("bob_quality.suite_memo.export_coverage_json", export)
    monkeypatch.setattr(SuiteMemo, "_python_text", spy_text)
    memo = SuiteMemo(want_lcov=False)
    coverage = tmp_path / "data"

    text = memo.python_json(tmp_path, ("src",), coverage)
    again = memo.python_json(tmp_path, ("other",), None)

    assert text == again == '{"files": {}}'
    assert calls == [(tmp_path, started, "coverage.json")]
    assert flags[0] == (tmp_path, ("src",), coverage, False)
    assert seen[0] == (tmp_path, ("src",), seen[0][2], coverage)


def test_xml_export_is_read_once_and_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    started = _started(tmp_path, 0)
    seen: list[tuple[object, ...]] = []
    _patch_start(monkeypatch, started, seen)
    calls: list[str] = []
    flags: list[tuple[object, ...]] = []
    real_text = SuiteMemo._python_text

    def export(cwd: Path, got: PythonStarted, dest: Path) -> None:
        calls.append(dest.name)
        dest.write_text("<coverage/>")

    def spy_text(
        self: SuiteMemo,
        cwd: Path,
        include: tuple[str, ...],
        coverage_file: Path | None,
        *,
        xml: bool,
    ) -> str:
        flags.append((cwd, tuple(include), coverage_file, xml))
        return real_text(self, cwd, include, coverage_file, xml=xml)

    monkeypatch.setattr("bob_quality.suite_memo.export_coverage_xml", export)
    monkeypatch.setattr(SuiteMemo, "_python_text", spy_text)
    memo = SuiteMemo(want_lcov=True)
    coverage = tmp_path / "data"

    text = memo.python_xml(tmp_path, ("src",), coverage)
    again = memo.python_xml(tmp_path, ("src",), None)

    assert text == again == "<coverage/>"
    assert calls == ["coverage.xml"]
    assert flags[0] == (tmp_path, ("src",), coverage, True)
    assert seen[0] == (tmp_path, ("src",), seen[0][2], coverage)


def test_a_missing_export_file_is_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_start(monkeypatch, _started(tmp_path, 0), [])

    def export(cwd: Path, got: PythonStarted, dest: Path) -> None:
        return None

    monkeypatch.setattr("bob_quality.suite_memo.export_coverage_json", export)
    memo = SuiteMemo(want_lcov=False)

    assert memo.python_json(tmp_path, ("src",), None) == ""


def test_an_export_error_is_cached(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_start(monkeypatch, _started(tmp_path, 0), [])
    calls: list[str] = []

    def export(cwd: Path, got: PythonStarted, dest: Path) -> None:
        calls.append(dest.name)
        raise ToolError(msg("coverage.no_xml"))

    monkeypatch.setattr("bob_quality.suite_memo.export_coverage_json", export)
    monkeypatch.setattr("bob_quality.suite_memo.export_coverage_xml", export)
    memo = SuiteMemo(want_lcov=False)

    with pytest.raises(ToolError) as first:
        memo.python_json(tmp_path, ("src",), None)
    with pytest.raises(ToolError) as second:
        memo.python_json(tmp_path, ("src",), None)
    with pytest.raises(ToolError) as xml:
        memo.python_xml(tmp_path, ("src",), None)
    with pytest.raises(ToolError) as xml_again:
        memo.python_xml(tmp_path, ("src",), None)

    assert first.value is second.value
    assert xml.value is xml_again.value
    assert calls == ["coverage.json", "coverage.xml"]
    assert in_both(first.value) == (
        "coverage.py did not write coverage.xml",
        "coverage.py não gravou coverage.xml",
    )
    assert xml.value is not first.value


def test_a_hold_without_a_directory_names_the_missing_export(tmp_path: Path) -> None:
    memo = SuiteMemo(want_lcov=False)
    hold = PythonHold(_started(tmp_path, 0))

    with pytest.raises(ToolError) as json_error:
        memo._read_export(tmp_path, hold, False)
    with pytest.raises(ToolError) as xml_error:
        memo._read_export(tmp_path, hold, True)

    assert in_both(json_error.value) == in_both(_missing_export(False))
    assert in_both(xml_error.value) == in_both(_missing_export(True))
    assert in_both(json_error.value) == (
        "diff-cover returned an unreadable report",
        "diff-cover devolveu um relatório ilegível",
    )
    assert in_both(xml_error.value) == (
        "coverage.py did not write coverage.xml",
        "coverage.py não gravou coverage.xml",
    )


def test_hold_errors_keep_the_baseline_and_the_tool_reason() -> None:
    broken = _hold_error(HoldBroken(4))
    unavailable = _hold_error(HoldUnavailable(msg("tool.missing", tool="coverage")))
    other = _hold_error(PythonHold(PythonStarted(0, Path("coverage.rc"))))

    assert in_both(broken) == (
        "baseline tests failed before measuring",
        "testes da baseline falharam antes de medir",
    )
    assert in_both(unavailable) == ("missing tool: coverage", "ferramenta ausente: coverage")
    assert in_both(other) == (
        "diff-cover returned an unreadable report",
        "diff-cover devolveu um relatório ilegível",
    )


def test_a_broken_hold_blocks_the_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_start(monkeypatch, _started(tmp_path, 3), [])
    memo = SuiteMemo(want_lcov=False)

    with pytest.raises(ToolError) as caught:
        memo.python_json(tmp_path, ("src",), None)

    assert in_both(caught.value) == (
        "baseline tests failed before measuring",
        "testes da baseline falharam antes de medir",
    )


def test_close_removes_the_hold_directory_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_start(monkeypatch, _started(tmp_path, 0), [])
    memo = SuiteMemo(want_lcov=False)
    memo.python_hold(tmp_path, ("src",), None)
    assert memo._python_dir is not None
    directory = Path(memo._python_dir.name)
    calls: list[str] = []
    real_cleanup = memo._python_dir.cleanup

    def spy_cleanup() -> None:
        calls.append("cleanup")
        real_cleanup()

    memo._python_dir.cleanup = spy_cleanup

    memo.close()
    memo.close()

    assert calls == ["cleanup"]
    assert directory.exists() is False
    assert memo._closed is True
