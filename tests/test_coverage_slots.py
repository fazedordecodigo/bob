"""Trava o resultado que o gate de cobertura e os probes devolvem."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import bob_quality.crap_gate as crap_gate
import bob_quality.suite_memo as suite_memo
import bob_quality.tools as tools
import bob_quality.typescript_probe as typescript_probe
from bob_quality.config import Config
from bob_quality.coverage_gate import (
    DIFF_COVER_MODULE,
    FileLines,
    LanguageMiss,
    _adjusted_percent,
    _collect,
    _fail_reason,
    _from_percents,
    _hold_miss,
    _judge,
    _measured,
    _miss_reason,
    _python_slot,
    _run_diff_cover,
    _slot,
    _typescript_slot,
    _write_patch,
)
from bob_quality.exit_codes import BASELINE_BROKEN, CONFIG_OR_TOOL, GATE_FAILED, PASSED
from bob_quality.messages import msg
from bob_quality.models import DiffLine, FunctionMetric, LanguageDiff
from bob_quality.npm_tools import NODE_MISSING
from bob_quality.probe import ProbeResult
from bob_quality.suite_memo import (
    HoldBroken,
    HoldUnavailable,
    PythonHold,
    SuiteMemo,
    TypescriptHold,
)
from bob_quality.tools import PythonStarted, ToolError, export_coverage_xml
from bob_quality.typescript_probe import measure_typescript
from helpers import in_both

_XML = "<coverage></coverage>"
_NO_XML = (
    "coverage.py did not write coverage.xml",
    "coverage.py não gravou coverage.xml",
)
_NO_LCOV = (
    "c8 did not write lcov.info",
    "c8 não gravou lcov.info",
)
_UNREADABLE = (
    "diff-cover returned an unreadable report",
    "diff-cover devolveu um relatório ilegível",
)
_BASELINE = (
    "baseline tests failed before measuring",
    "testes da baseline falharam antes de medir",
)
_MISSING_DIFF_COVER = (
    "missing tool: diff-cover",
    "ferramenta ausente: diff-cover",
)


class _Memo:
    def __init__(self) -> None:
        self.holds: list[tuple[object, ...]] = []
        self.xml_calls: list[tuple[object, ...]] = []
        self.ts_calls: list[tuple[object, ...]] = []
        self.hold: object = PythonHold(PythonStarted(0, Path("coverage.data")))
        self.xml = _XML
        self.xml_error: ToolError | None = None
        self.typescript: object = TypescriptHold(Path("reports"))

    def python_hold(self, cwd: Path, include: object, coverage_file: Path | None) -> object:
        self.holds.append((cwd, include, coverage_file))
        return self.hold

    def python_xml(self, cwd: Path, include: object, coverage_file: Path | None) -> str:
        self.xml_calls.append((cwd, include, coverage_file))
        if self.xml_error is not None:
            raise self.xml_error
        return self.xml

    def typescript_hold(self, cwd: Path, include: object, exclude: object) -> object:
        self.ts_calls.append((cwd, include, exclude))
        return self.typescript


def _config(*languages: str) -> Config:
    return Config(languages=languages, include=("pkg",), exclude=("dist",))


def _patch(tmp_path: Path) -> Path:
    return tmp_path / "patch.diff"


def test_hold_miss_names_baseline_tool_and_unreadable() -> None:
    baseline = _hold_miss("python", HoldBroken(2))
    unavailable = _hold_miss("typescript", HoldUnavailable(msg("coverage.no_lcov")))
    other = _hold_miss("python", object())

    assert baseline == LanguageMiss("python", "baseline", msg("probe.baseline_failed"))
    assert unavailable == LanguageMiss("typescript", "tool", msg("coverage.no_lcov"))
    assert other == LanguageMiss("python", "tool", msg("coverage.unreadable"))
    assert in_both(baseline.reason) == _BASELINE
    assert in_both(unavailable.reason) == _NO_LCOV
    assert in_both(other.reason) == _UNREADABLE


def test_python_slot_forwards_the_hold_and_names_a_broken_baseline(tmp_path: Path) -> None:
    memo = _Memo()
    memo.hold = HoldBroken(1)
    coverage = tmp_path / "given.xml"

    slot = _python_slot(tmp_path, _config("python"), coverage, memo, _patch(tmp_path), ())

    assert memo.holds == [(tmp_path, ("pkg",), coverage)]
    assert memo.xml_calls == []
    assert slot == LanguageMiss("python", "baseline", msg("probe.baseline_failed"))


def test_python_slot_names_an_export_failure_and_a_blank_xml(tmp_path: Path) -> None:
    memo = _Memo()
    memo.xml_error = ToolError("export broke")
    coverage = tmp_path / "given.xml"
    failed = _python_slot(tmp_path, _config("python"), coverage, memo, _patch(tmp_path), ())

    memo.xml_error = None
    memo.xml = "  \n"
    blank = _python_slot(tmp_path, _config("python"), coverage, memo, _patch(tmp_path), ())

    assert memo.xml_calls == [
        (tmp_path, ("pkg",), coverage),
        (tmp_path, ("pkg",), coverage),
    ]
    assert failed == LanguageMiss("python", "tool", "export broke")
    assert blank == LanguageMiss("python", "tool", msg("coverage.no_xml"))
    assert in_both(blank.reason) == _NO_XML


def test_python_slot_measures_with_the_given_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    memo = _Memo()
    coverage = tmp_path / "given.xml"
    calls: list[tuple[list[str], dict[str, object]]] = []

    def spy(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        _write_diff_cover_json(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", spy)
    slot = _python_slot(tmp_path, _config("python"), coverage, memo, _patch(tmp_path), ())

    assert calls[0][1]["cwd"] is tmp_path
    assert isinstance(slot, LanguageDiff)
    assert slot.language == "python"
    assert slot.percent == 100.0
    assert slot.uncovered == ()


def test_typescript_slot_forwards_include_and_exclude_and_names_a_miss(tmp_path: Path) -> None:
    memo = _Memo()
    memo.typescript = HoldBroken(3)
    missed = _typescript_slot(tmp_path, _config("typescript"), memo, _patch(tmp_path), ())

    reports = tmp_path / "reports"
    reports.mkdir()
    memo.typescript = TypescriptHold(reports)
    empty = _typescript_slot(tmp_path, _config("typescript"), memo, _patch(tmp_path), ())
    (reports / "lcov.info").write_text("")
    blank = _typescript_slot(tmp_path, _config("typescript"), memo, _patch(tmp_path), ())

    assert memo.ts_calls[0] == (tmp_path, ("pkg",), ("dist",))
    assert missed == LanguageMiss("typescript", "baseline", msg("probe.baseline_failed"))
    assert empty == LanguageMiss("typescript", "tool", msg("coverage.no_lcov"))
    assert blank == LanguageMiss("typescript", "tool", msg("coverage.no_lcov"))
    assert in_both(empty.reason) == _NO_LCOV


def test_typescript_slot_measures_a_real_lcov(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "lcov.info").write_text("TN:\n")
    memo = _Memo()
    memo.typescript = TypescriptHold(reports)
    calls: list[dict[str, object]] = []

    def spy(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(kwargs)
        _write_diff_cover_json(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", spy)
    slot = _typescript_slot(tmp_path, _config("typescript"), memo, _patch(tmp_path), ())

    assert calls[0]["cwd"] is tmp_path
    assert isinstance(slot, LanguageDiff)
    assert slot == LanguageDiff("typescript", 100.0, ())


def test_collect_stops_after_a_baseline_miss_and_keeps_the_coverage_file(tmp_path: Path) -> None:
    memo = _Memo()
    memo.hold = HoldBroken(1)
    coverage = tmp_path / "given.xml"

    slots = _collect(tmp_path, _config("python", "typescript"), coverage, memo, _patch(tmp_path), ())

    assert slots == (LanguageMiss("python", "baseline", msg("probe.baseline_failed")),)
    assert memo.ts_calls == []
    assert memo.holds == [(tmp_path, ("pkg",), coverage)]


def test_slot_forwards_the_coverage_file_to_python(tmp_path: Path) -> None:
    memo = _Memo()
    memo.hold = HoldUnavailable(msg("coverage.no_xml"))
    coverage = tmp_path / "given.xml"

    slot = _slot("python", tmp_path, _config("python"), coverage, memo, _patch(tmp_path), ())

    assert memo.holds == [(tmp_path, ("pkg",), coverage)]
    assert slot == LanguageMiss("python", "tool", msg("coverage.no_xml"))


def test_measured_reports_the_diff_cover_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = tmp_path / "coverage.xml"
    artifact.write_text(_XML)

    def spy(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        _write_diff_cover_json(args)
        return subprocess.CompletedProcess(args, 3, "stdout noise", "diff-cover failed")

    monkeypatch.setattr(subprocess, "run", spy)
    slot = _measured("python", tmp_path, artifact, _patch(tmp_path), ())

    assert slot == LanguageMiss("python", "tool", "diff-cover failed")


def test_run_diff_cover_invokes_the_module_and_reads_the_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "coverage.xml"
    artifact.write_text(_XML)
    patch = _patch(tmp_path)
    calls: list[tuple[list[str], dict[str, object]]] = []

    def spy(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((list(args), kwargs))
        _write_diff_cover_json(args, covered=[1], uncovered=[4])
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", spy)
    files = _run_diff_cover(tmp_path, artifact, patch)

    args, kwargs = calls[0]
    assert args[:3] == [sys.executable, "-m", DIFF_COVER_MODULE]
    assert kwargs == {
        "cwd": tmp_path,
        "capture_output": True,
        "text": True,
        "stdin": subprocess.DEVNULL,
    }
    assert files["a.py"].covered == frozenset({1})
    assert files["a.py"].uncovered == frozenset({4})


def test_run_diff_cover_prefers_stderr_and_rejects_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "coverage.xml"
    artifact.write_text(_XML)

    def spy(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        _write_diff_cover_json(args)
        return subprocess.CompletedProcess(args, 2, "stdout noise", "diff-cover failed")

    monkeypatch.setattr(subprocess, "run", spy)
    with pytest.raises(ToolError) as caught:
        _run_diff_cover(tmp_path, artifact, _patch(tmp_path))

    assert in_both(caught.value) == ("diff-cover failed", "diff-cover failed")


def test_run_diff_cover_names_a_missing_report_and_an_unreadable_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "coverage.xml"
    artifact.write_text(_XML)

    def missing(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", missing)
    with pytest.raises(ToolError) as absent:
        _run_diff_cover(tmp_path, artifact, _patch(tmp_path))
    assert in_both(absent.value) == _UNREADABLE

    def present(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        _write_diff_cover_json(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    def boom(self: Path, *args: object, **kwargs: object) -> str:
        raise OSError("disk")

    monkeypatch.setattr(subprocess, "run", present)
    monkeypatch.setattr(Path, "read_text", boom)
    with pytest.raises(ToolError) as unreadable:
        _run_diff_cover(tmp_path, artifact, _patch(tmp_path))
    assert in_both(unreadable.value) == _UNREADABLE


def test_write_patch_asks_git_for_the_unified_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "patch.diff"
    calls: list[tuple[list[str], dict[str, object]]] = []

    def spy(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((list(args), kwargs))
        return subprocess.CompletedProcess(args, 0, "diff --git a/a b/a\n", "")

    monkeypatch.setattr(subprocess, "run", spy)
    _write_patch(tmp_path, "origin/main", dest)

    args, kwargs = calls[0]
    assert args == [
        "git",
        "-c",
        "diff.noprefix=no",
        "-c",
        "diff.mnemonicprefix=no",
        "diff",
        "--no-color",
        "--no-ext-diff",
        "--unified=0",
        "origin/main...HEAD",
    ]
    assert kwargs == {
        "cwd": tmp_path,
        "capture_output": True,
        "text": True,
        "stdin": subprocess.DEVNULL,
    }
    assert dest.read_text() == "diff --git a/a b/a\n"


def test_write_patch_prefers_stderr_when_git_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def spy(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, "stdout noise", "bad diff")

    monkeypatch.setattr(subprocess, "run", spy)
    with pytest.raises(ToolError) as caught:
        _write_patch(tmp_path, "origin/main", tmp_path / "patch.diff")

    assert in_both(caught.value) == ("bad diff", "bad diff")


def test_write_patch_names_an_empty_git_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def spy(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, "", "")

    monkeypatch.setattr(subprocess, "run", spy)
    with pytest.raises(ToolError) as caught:
        _write_patch(tmp_path, "origin/main", tmp_path / "patch.diff")

    assert in_both(caught.value) == _UNREADABLE


def test_adjusted_percent_adds_every_file_and_rounds_to_two_places() -> None:
    two = {
        "a.py": FileLines(frozenset({1, 2}), frozenset({3})),
        "b.py": FileLines(frozenset({4}), frozenset({5, 6})),
    }
    third = {"a.py": FileLines(frozenset({1}), frozenset({2, 3}))}

    assert _adjusted_percent(two, ()).value == 50.0
    assert _adjusted_percent(third, ()).value == 33.33


def test_judge_with_no_measurement_names_every_miss() -> None:
    outcome = _judge((), 80.0)
    joined = _judge(
        (
            LanguageMiss("python", "tool", msg("coverage.no_xml")),
            LanguageMiss("typescript", "tool", msg("coverage.no_lcov")),
        ),
        80.0,
    )

    assert outcome.exit_code == CONFIG_OR_TOOL
    assert outcome.versions == {}
    assert outcome.diff_coverage is None
    assert outcome.result.name == "coverage"
    assert outcome.result.status == "not_run"
    assert in_both(outcome.result.reason) == _MISSING_DIFF_COVER
    assert joined.result.name == "coverage"
    assert joined.result.status == "not_run"
    assert joined.exit_code == CONFIG_OR_TOOL
    assert joined.versions == {}
    assert in_both(joined.result.reason) == (
        "coverage.py did not write coverage.xml; c8 did not write lcov.info",
        "coverage.py não gravou coverage.xml; c8 não gravou lcov.info",
    )
    assert in_both(_miss_reason(())) == _MISSING_DIFF_COVER


def test_a_baseline_miss_exits_2_with_empty_versions() -> None:
    outcome = _judge((LanguageMiss("python", "baseline", msg("probe.baseline_failed")),), 80.0)

    assert outcome.exit_code == BASELINE_BROKEN
    assert outcome.versions == {}
    assert outcome.diff_coverage is None
    assert outcome.result.status == "not_run"
    assert in_both(outcome.result.reason) == _BASELINE


def test_a_measured_miss_stays_on_the_passed_result() -> None:
    outcome = _from_percents(
        (LanguageDiff("python", 100.0, ()),),
        (LanguageMiss("typescript", "tool", msg("coverage.no_lcov")),),
        80.0,
    )

    assert outcome.exit_code == PASSED
    assert outcome.versions == {}
    assert outcome.result.status == "passed"
    assert outcome.diff_coverage is not None
    assert in_both(outcome.result.reason) == (
        "typescript skipped: c8 did not write lcov.info",
        "typescript pulado: c8 não gravou lcov.info",
    )


def test_a_low_percent_joins_the_skip_and_keeps_both_languages() -> None:
    failing = (
        LanguageDiff("python", 10.0, (DiffLine("src/a.py", 2),)),
        LanguageDiff("typescript", 20.0, ()),
    )
    outcome = _from_percents(
        failing,
        (
            LanguageMiss("python", "tool", msg("coverage.no_xml")),
            LanguageMiss("typescript", "tool", msg("coverage.no_lcov")),
        ),
        80.0,
    )

    assert outcome.exit_code == GATE_FAILED
    assert outcome.versions == {}
    assert outcome.result.status == "failed"
    assert outcome.diff_coverage is not None
    assert in_both(outcome.result.reason) == (
        "python 10.00% < 80; typescript 20.00% < 80; "
        "python skipped: coverage.py did not write coverage.xml; "
        "typescript skipped: c8 did not write lcov.info",
        "python 10.00% < 80; typescript 20.00% < 80; "
        "python pulado: coverage.py não gravou coverage.xml; "
        "typescript pulado: c8 não gravou lcov.info",
    )
    assert _fail_reason(failing, 80.0) == "python 10.00% < 80; typescript 20.00% < 80"


def test_reporters_default_to_json_and_keep_an_explicit_lcov() -> None:
    assert SuiteMemo(False)._reporters() == ("json",)
    assert SuiteMemo(False, want_json=True)._reporters() == ("json",)
    assert SuiteMemo(True)._reporters() == ("lcov",)
    assert SuiteMemo(True, want_json=True)._reporters() == ("json", "lcov")


def test_typescript_hold_uses_the_bob_c8_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[object, ...]] = []

    def fake(
        cwd: Path,
        include: list[str],
        reports: Path,
        exclude: list[str],
        reporters: tuple[str, ...],
    ) -> int:
        seen.append((cwd, include, reports, exclude, reporters))
        reports.mkdir(parents=True)
        return 0

    monkeypatch.setattr(suite_memo, "run_vitest_under_c8", fake)
    memo = SuiteMemo(True)
    try:
        hold = memo.typescript_hold(tmp_path, ("pkg",), ("dist",))
    finally:
        memo.close()

    assert len(seen) == 1
    cwd, include, reports, exclude, reporters = seen[0]
    assert cwd is tmp_path
    assert include == ["pkg"]
    assert exclude == ["dist"]
    assert reporters == ("lcov",)
    assert reports.name == "coverage"
    assert reports.parent.name.startswith("bob-c8-")
    assert isinstance(hold, TypescriptHold)
    assert hold.reports == reports


def test_typescript_hold_keeps_a_vitest_failure_and_a_tool_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*args: object) -> int:
        return 4

    monkeypatch.setattr(suite_memo, "run_vitest_under_c8", broken)
    failed = SuiteMemo(False)
    try:
        hold = failed.typescript_hold(tmp_path, ("pkg",), ("dist",))
    finally:
        failed.close()
    assert hold == HoldBroken(4)

    def unavailable(*args: object) -> int:
        raise ToolError(msg("probe.baseline_failed"))

    monkeypatch.setattr(suite_memo, "run_vitest_under_c8", unavailable)
    missing = SuiteMemo(False)
    try:
        down = missing.typescript_hold(tmp_path, ("pkg",), ("dist",))
    finally:
        missing.close()
    assert isinstance(down, HoldUnavailable)
    assert in_both(down.reason) == _BASELINE


def test_export_coverage_xml_forwards_the_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    started = PythonStarted(0, tmp_path / "coverage.data")
    dest = tmp_path / "coverage.xml"
    seen: list[tuple[object, ...]] = []

    def spy(cwd: Path, got: PythonStarted, target: Path, kind: str) -> None:
        seen.append((cwd, got, target, kind))

    monkeypatch.setattr(tools, "_export_coverage", spy)
    export_coverage_xml(tmp_path, started, dest)

    assert seen == [(tmp_path, started, dest, "xml")]


def test_measure_typescript_records_the_pinned_tool_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    versions = _patch_typescript_versions(monkeypatch)
    reports = tmp_path / "coverage"
    reports.mkdir()
    (reports / "coverage-final.json").write_text('{"ok": true}')
    memo = SuiteMemo(False)
    memo._typescript = TypescriptHold(reports)
    lizard: list[tuple[object, ...]] = []

    def fake_lizard(cwd: Path, include: list[str], exclude: list[str], language: str = "python") -> str:
        lizard.append((cwd, include, exclude, language))
        return "csv"

    monkeypatch.setattr(typescript_probe, "run_lizard_csv", fake_lizard)
    monkeypatch.setattr(typescript_probe, "parse_lizard_csv", lambda raw: [])
    monkeypatch.setattr(typescript_probe, "parse_coverage_final", lambda raw: {})
    monkeypatch.setattr(typescript_probe, "build_metrics", lambda *args: [])

    result = measure_typescript(tmp_path, _config("typescript"), {}, memo)

    assert versions["calls"] == [
        ("c8",),
        ("vitest",),
        ("lizard", r"(\d+\.\d+\.\d+)"),
    ]
    assert result.versions == {"c8": "12.0.0", "vitest": "5.0.4", "lizard": "1.24.1"}
    assert result.gate is None
    assert result.metrics == []
    assert lizard == [(tmp_path, ("pkg",), ("dist",), "typescript")]


def test_measure_typescript_names_a_version_failure_and_a_missing_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_typescript_versions(monkeypatch, lizard_error=ToolError("no lizard"))
    failed = measure_typescript(tmp_path, _config("typescript"), {}, SuiteMemo(False))

    reports = tmp_path / "coverage"
    reports.mkdir()
    memo = SuiteMemo(False)
    memo._typescript = TypescriptHold(reports)
    _patch_typescript_versions(monkeypatch)
    missing = measure_typescript(tmp_path, _config("typescript"), {}, memo)

    assert failed.exit_code == CONFIG_OR_TOOL
    assert failed.versions == {"c8": "12.0.0", "vitest": "5.0.4"}
    assert failed.gate is not None
    assert in_both(failed.gate.reason) == ("no lizard", "no lizard")
    assert missing.exit_code == CONFIG_OR_TOOL
    assert missing.versions["lizard"] == "1.24.1"
    assert missing.gate is not None
    assert in_both(missing.gate.reason) == (
        "c8 did not write coverage-final.json",
        "c8 não gravou coverage-final.json",
    )


def test_measure_typescript_names_an_unavailable_c8_hold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_typescript_versions(monkeypatch)
    memo = SuiteMemo(False)
    memo._typescript = HoldUnavailable(msg("probe.baseline_failed"))

    result = measure_typescript(tmp_path, _config("typescript"), {}, memo)

    assert result.exit_code == CONFIG_OR_TOOL
    assert result.versions == {"c8": "12.0.0", "vitest": "5.0.4", "lizard": "1.24.1"}
    assert result.gate is not None
    assert in_both(result.gate.reason) == (
        "c8: baseline tests failed before measuring",
        "c8: testes da baseline falharam antes de medir",
    )


def test_measure_typescript_names_a_lizard_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_typescript_versions(monkeypatch)
    reports = tmp_path / "coverage"
    reports.mkdir()
    (reports / "coverage-final.json").write_text('{"ok": true}')
    memo = SuiteMemo(False)
    memo._typescript = TypescriptHold(reports)

    def fake_lizard(*args: object, **kwargs: object) -> str:
        raise ToolError(msg("probe.c8_no_report"))

    monkeypatch.setattr(typescript_probe, "run_lizard_csv", fake_lizard)
    result = measure_typescript(tmp_path, _config("typescript"), {}, memo)

    assert result.exit_code == CONFIG_OR_TOOL
    assert result.versions["lizard"] == "1.24.1"
    assert result.gate is not None
    assert in_both(result.gate.reason) == (
        "c8 did not write coverage-final.json",
        "c8 não gravou coverage-final.json",
    )


def test_crap_keeps_the_python_baseline_and_the_all_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    metric = FunctionMetric(
        "python",
        "app",
        "gap",
        "src/app.py",
        1,
        4,
        5,
        0.0,
        30.0,
        False,
    )

    def python_only(*args: object) -> ProbeResult:
        return ProbeResult(metrics=[metric], baseline=7)

    monkeypatch.setattr(crap_gate, "measure_python", python_only)
    gate, _metrics, _code, _versions, baseline = crap_gate.run_crap_gate(
        tmp_path,
        Config(languages=("python",), crap_scope="all"),
        {},
        10.0,
        None,
        SuiteMemo(False),
    )

    assert baseline == 7
    assert gate.status == "failed"


def test_crap_without_python_has_no_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def typescript_only(*args: object) -> ProbeResult:
        return ProbeResult()

    monkeypatch.setattr(crap_gate, "measure_typescript", typescript_only)
    gate, _metrics, _code, _versions, baseline = crap_gate.run_crap_gate(
        tmp_path,
        Config(languages=("typescript",)),
        {},
        10.0,
        None,
        SuiteMemo(False),
    )

    assert baseline is None
    assert gate.status == "passed"
    assert gate.reason is None


def test_crap_warns_when_node_is_missing_beside_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def python_ok(*args: object) -> ProbeResult:
        return ProbeResult(baseline=0)

    def node_missing(*args: object) -> ProbeResult:
        return ProbeResult.not_run({}, NODE_MISSING, CONFIG_OR_TOOL)

    monkeypatch.setattr(crap_gate, "measure_python", python_ok)
    monkeypatch.setattr(crap_gate, "measure_typescript", node_missing)
    gate, _metrics, _code, _versions, baseline = crap_gate.run_crap_gate(
        tmp_path,
        Config(languages=("python", "typescript")),
        {},
        10.0,
        None,
        SuiteMemo(False),
    )

    assert baseline == 0
    assert gate.status == "warn"
    assert in_both(gate.reason) == (
        "TypeScript skipped: Node missing: install Node.js to measure TypeScript (c8 and vitest via npx)",
        "TypeScript pulado: Node ausente: instale Node.js para medir TypeScript (c8 e vitest via npx)",
    )


def test_python_only_crap_does_not_mention_typescript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def python_ok(*args: object) -> ProbeResult:
        return ProbeResult(baseline=0)

    monkeypatch.setattr(crap_gate, "measure_python", python_ok)
    gate, _metrics, _code, _versions, baseline = crap_gate.run_crap_gate(
        tmp_path,
        Config(languages=("python",)),
        {},
        10.0,
        None,
        SuiteMemo(False),
    )

    assert baseline == 0
    assert gate.status == "passed"
    assert gate.reason is None


def _patch_typescript_versions(
    monkeypatch: pytest.MonkeyPatch, lizard_error: ToolError | None = None
) -> dict[str, list[tuple[str, ...]]]:
    seen: dict[str, list[tuple[str, ...]]] = {"calls": []}

    def versions(prefix: Path, package: str) -> str:
        seen["calls"].append((package,))
        return {"c8": "12.0.0", "vitest": "5.0.4"}[package]

    def lizard_version(module: str, pattern: str) -> str:
        seen["calls"].append((module, pattern))
        if lizard_error is not None:
            raise lizard_error
        return "1.24.1"

    monkeypatch.setattr(typescript_probe, "node_missing_message", lambda: None)
    monkeypatch.setattr(typescript_probe, "npm_prefix", lambda: Path("/prefix"))
    monkeypatch.setattr(typescript_probe, "installed_npm_version", versions)
    monkeypatch.setattr(typescript_probe, "tool_version", lizard_version)
    return seen


def _write_diff_cover_json(
    args: list[str], covered: list[int] | None = None, uncovered: list[int] | None = None
) -> None:
    raw = next(item for item in args if str(item).startswith("json:"))
    path = Path(str(raw).split(":", 1)[1])
    path.write_text(
        json.dumps(
            {
                "src_stats": {
                    "a.py": {
                        "covered_lines": [1] if covered is None else covered,
                        "violation_lines": [] if uncovered is None else uncovered,
                    }
                }
            }
        )
    )
