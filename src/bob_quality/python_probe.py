"""Mede funções Python: coverage.py + lizard. Uma razão para mudar."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bob_quality.adapters.coverage import CoverageParseError, parse_coverage_json
from bob_quality.adapters.lizard import LizardParseError, parse_lizard_csv
from bob_quality.config import Config
from bob_quality.exit_codes import BASELINE_BROKEN, CONFIG_OR_TOOL
from bob_quality.messages import msg, reason
from bob_quality.probe import ProbeResult, build_metrics
from bob_quality.tools import ToolError, run_coverage, run_lizard_csv, tool_version


def measure_python(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    coverage_file: Path | None,
) -> ProbeResult:
    versions: dict[str, str] = {}
    try:
        versions["lizard"] = tool_version("lizard", r"(\d+\.\d+\.\d+)")
        versions["coverage.py"] = tool_version("coverage", r"version (\d+\.\d+\.\d+)")
    except ToolError as exc:
        return ProbeResult.not_run(versions, msg("tool.missing", tool=reason(exc)), CONFIG_OR_TOOL)

    try:
        with tempfile.TemporaryDirectory(prefix="bob-coverage-") as tmp:
            coverage_json = Path(tmp) / "coverage.json"
            pytest_code = run_coverage(cwd, config.include, coverage_json, coverage_file)
            raw_coverage = coverage_json.read_text() if coverage_json.is_file() else ""
    except ToolError as exc:
        detail = msg("tool.detail", tool="coverage.py", detail=reason(exc))
        return ProbeResult.not_run(versions, detail, CONFIG_OR_TOOL)
    if pytest_code not in {0, 5}:
        return ProbeResult.not_run(versions, msg("probe.baseline_failed"), BASELINE_BROKEN)

    try:
        raw_lizard = run_lizard_csv(cwd, config.include, config.exclude)
        lizard_fns = parse_lizard_csv(raw_lizard)
        coverage_files = parse_coverage_json(raw_coverage)
    except (ToolError, OSError, LizardParseError, CoverageParseError) as exc:
        return ProbeResult.not_run(versions, reason(exc), CONFIG_OR_TOOL)

    return ProbeResult(
        metrics=build_metrics(cwd, lizard_fns, coverage_files, diff_lines, "python"),
        versions=versions,
    )
