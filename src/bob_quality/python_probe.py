"""Mede funções Python: coverage.py + lizard. Uma razão para mudar."""

from __future__ import annotations

from pathlib import Path

from bob_quality.adapters.coverage import CoverageParseError, parse_coverage_json
from bob_quality.adapters.lizard import LizardParseError, parse_lizard_csv
from bob_quality.config import Config
from bob_quality.exit_codes import BASELINE_BROKEN, CONFIG_OR_TOOL
from bob_quality.messages import msg, reason
from bob_quality.probe import ProbeResult, build_metrics
from bob_quality.suite_memo import HoldBroken, HoldUnavailable, SuiteMemo
from bob_quality.tools import ToolError, run_lizard_csv, tool_version


def measure_python(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    coverage_file: Path | None,
    memo: SuiteMemo,
) -> ProbeResult:
    versions: dict[str, str] = {}
    try:
        versions["lizard"] = tool_version("lizard", r"(\d+\.\d+\.\d+)")
        versions["coverage.py"] = tool_version("coverage", r"version (\d+\.\d+\.\d+)")
    except ToolError as exc:
        return ProbeResult.not_run(versions, msg("tool.missing", tool=reason(exc)), CONFIG_OR_TOOL)

    hold = memo.python_hold(cwd, config.include, coverage_file)
    if isinstance(hold, HoldBroken):
        return ProbeResult.not_run(
            versions, msg("probe.baseline_failed"), BASELINE_BROKEN, baseline=hold.tool_exit
        )
    if isinstance(hold, HoldUnavailable):
        detail = msg("tool.detail", tool="coverage.py", detail=hold.reason)
        return ProbeResult.not_run(versions, detail, CONFIG_OR_TOOL)
    try:
        raw_coverage = memo.python_json(cwd, config.include, coverage_file)
    except ToolError as exc:
        detail = msg("tool.detail", tool="coverage.py", detail=reason(exc))
        return ProbeResult.not_run(versions, detail, CONFIG_OR_TOOL)

    try:
        raw_lizard = run_lizard_csv(cwd, config.include, config.exclude)
        lizard_fns = parse_lizard_csv(raw_lizard)
        coverage_files = parse_coverage_json(raw_coverage)
    except (ToolError, OSError, LizardParseError, CoverageParseError) as exc:
        return ProbeResult.not_run(versions, reason(exc), CONFIG_OR_TOOL)

    return ProbeResult(
        metrics=build_metrics(cwd, lizard_fns, coverage_files, diff_lines, "python"),
        versions=versions,
        baseline=hold.started.pytest_code,
    )
