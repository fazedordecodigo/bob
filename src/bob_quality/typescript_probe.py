"""Mede funções TypeScript: c8 (coverage-final.json) + lizard."""

from __future__ import annotations

import tempfile
from pathlib import Path

from bob_quality.adapters.istanbul import IstanbulParseError, parse_coverage_final
from bob_quality.adapters.lizard import LizardParseError, parse_lizard_csv
from bob_quality.config import Config
from bob_quality.exit_codes import BASELINE_BROKEN, CONFIG_OR_TOOL
from bob_quality.npm_tools import (
    installed_npm_version,
    node_missing_message,
    npm_prefix,
    run_vitest_under_c8,
)
from bob_quality.probe import ProbeResult, build_metrics
from bob_quality.tools import ToolError, run_lizard_csv, tool_version


def measure_typescript(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
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
        return ProbeResult.not_run(versions, str(exc), CONFIG_OR_TOOL)

    try:
        with tempfile.TemporaryDirectory(prefix="bob-c8-") as tmp:
            reports = Path(tmp) / "coverage"
            vitest_code = run_vitest_under_c8(
                cwd, config.include, reports, config.exclude
            )
            final = reports / "coverage-final.json"
            raw_coverage = final.read_text() if final.is_file() else ""
    except ToolError as exc:
        return ProbeResult.not_run(versions, f"c8: {exc}", CONFIG_OR_TOOL)
    if vitest_code != 0:
        return ProbeResult.not_run(
            versions, "testes da baseline falharam antes de medir", BASELINE_BROKEN
        )
    if not raw_coverage:
        return ProbeResult.not_run(versions, "c8 não gravou coverage-final.json", CONFIG_OR_TOOL)

    try:
        raw_lizard = run_lizard_csv(
            cwd, config.include, config.exclude, language="typescript"
        )
        functions = parse_lizard_csv(raw_lizard)
        coverage_files = parse_coverage_final(raw_coverage)
    except (ToolError, OSError, LizardParseError, IstanbulParseError) as exc:
        return ProbeResult.not_run(versions, str(exc), CONFIG_OR_TOOL)
    return ProbeResult(
        metrics=build_metrics(cwd, functions, coverage_files, diff_lines, "typescript"),
        versions=versions,
    )
