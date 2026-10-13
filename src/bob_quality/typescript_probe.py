"""Mede funções TypeScript: c8 (coverage-final.json) + lizard."""

from __future__ import annotations

from pathlib import Path

from bob_quality.adapters.istanbul import IstanbulParseError, parse_coverage_final
from bob_quality.adapters.lizard import LizardParseError, parse_lizard_csv
from bob_quality.config import Config
from bob_quality.exit_codes import BASELINE_BROKEN, CONFIG_OR_TOOL
from bob_quality.messages import msg, reason
from bob_quality.npm_tools import installed_npm_version, node_missing_message, npm_prefix
from bob_quality.probe import ProbeResult, build_metrics
from bob_quality.suite_memo import HoldBroken, HoldUnavailable, SuiteMemo
from bob_quality.tools import ToolError, run_lizard_csv, tool_version


def measure_typescript(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    memo: SuiteMemo,
) -> ProbeResult:
    versions: dict[str, str] = {}
    missing = node_missing_message()
    if missing:
        return ProbeResult.not_run({}, missing, CONFIG_OR_TOOL)
    try:
        prefix = npm_prefix()
        versions["c8"] = installed_npm_version(prefix, "c8")
        versions["vitest"] = installed_npm_version(prefix, "vitest")
        versions["lizard"] = tool_version("lizard", r"(\d+\.\d+\.\d+)")
    except ToolError as exc:
        return ProbeResult.not_run(versions, reason(exc), CONFIG_OR_TOOL)

    hold = memo.typescript_hold(cwd, config.include, config.exclude)
    if isinstance(hold, HoldBroken):
        return ProbeResult.not_run(versions, msg("probe.baseline_failed"), BASELINE_BROKEN)
    if isinstance(hold, HoldUnavailable):
        detail = msg("tool.detail", tool="c8", detail=hold.reason)
        return ProbeResult.not_run(versions, detail, CONFIG_OR_TOOL)
    final = hold.reports / "coverage-final.json"
    raw_coverage = final.read_text() if final.is_file() else ""
    if not raw_coverage:
        return ProbeResult.not_run(versions, msg("probe.c8_no_report"), CONFIG_OR_TOOL)

    try:
        raw_lizard = run_lizard_csv(
            cwd, config.include, config.exclude, language="typescript"
        )
        functions = parse_lizard_csv(raw_lizard)
        coverage_files = parse_coverage_final(raw_coverage)
    except (ToolError, OSError, LizardParseError, IstanbulParseError) as exc:
        return ProbeResult.not_run(versions, reason(exc), CONFIG_OR_TOOL)
    return ProbeResult(
        metrics=build_metrics(cwd, functions, coverage_files, diff_lines, "typescript"),
        versions=versions,
    )
