"""CLI orquestra adaptador → núcleo → relatório → exit code."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from bob_quality.adapters.coverage import CoverageParseError, parse_coverage_json
from bob_quality.adapters.lizard import LizardParseError, parse_lizard_csv
from bob_quality.config import Config, ConfigError, load_config
from bob_quality.core import (
    coverage_for,
    crap_verdict,
    files_by_risk,
    informational_debt,
    to_metric,
    top_changed_crap,
)
from bob_quality.diff import GitError, changed_lines, current_commit, function_is_changed
from bob_quality.exit_codes import BASELINE_BROKEN, CONFIG_OR_TOOL, PASSED
from bob_quality.models import FunctionMetric, GateResult, Report
from bob_quality.report import metric_row, write_report
from bob_quality.tools import ToolError, run_coverage, run_lizard_csv, tool_version

DEFAULT_GATES = ("crap", "dry", "deps")


def run_check(
    cwd: Path,
    base: str | None = None,
    gates: list[str] | None = None,
    config_path: Path | None = None,
    out_dir: Path | None = None,
    fmt: str = "both",
    threshold: float | None = None,
    coverage_file: Path | None = None,
    reproduce: str | None = None,
) -> int:
    chosen_gates = gates or list(DEFAULT_GATES)
    chosen_out = out_dir or (cwd / ".bob")
    command = reproduce or "bob check"
    try:
        config = load_config(config_path, cwd)
    except ConfigError as exc:
        return _fail_early(
            chosen_out, fmt, CONFIG_OR_TOOL, str(exc), base, command, chosen_gates
        )

    chosen_base = base or config.base
    max_crap = config.max_crap if threshold is None else threshold

    try:
        commit = current_commit(cwd)
        diff_lines = changed_lines(cwd, chosen_base)
    except GitError as exc:
        return _fail_early(
            chosen_out, fmt, CONFIG_OR_TOOL, str(exc), chosen_base, command, chosen_gates
        )

    versions: dict[str, str] = {}
    gate_results: list[GateResult] = []
    metrics: list[FunctionMetric] = []
    exit_code = PASSED

    for gate in chosen_gates:
        if gate != "crap":
            gate_results.append(
                GateResult(
                    name=gate,
                    status="not_run",
                    reason="gate não implementado nesta fatia",
                )
            )
            continue
        result, measured, code, versions = _run_crap(
            cwd=cwd,
            config=config,
            diff_lines=diff_lines,
            max_crap=max_crap,
            coverage_file=coverage_file,
        )
        gate_results.append(result)
        metrics = measured
        exit_code = _worse(exit_code, code)

    report = Report(
        schema_version=1,
        commit=commit,
        base=chosen_base,
        generated_at=datetime.now(timezone.utc).isoformat(),
        tool_versions=versions,
        gates=gate_results,
        focus=files_by_risk(metrics),
        top_crap=[metric_row(item) for item in top_changed_crap(metrics)],
        old_debt=[metric_row(item) for item in informational_debt(metrics, max_crap)],
        reproduce=command,
        exit_code=exit_code,
    )
    write_report(report, chosen_out, fmt)
    return exit_code


def _run_crap(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    max_crap: float,
    coverage_file: Path | None,
) -> tuple[GateResult, list[FunctionMetric], int, dict[str, str]]:
    versions: dict[str, str] = {}
    try:
        versions["lizard"] = tool_version("lizard", r"(\d+\.\d+\.\d+)")
        versions["coverage.py"] = tool_version("coverage", r"version (\d+\.\d+\.\d+)")
    except ToolError as exc:
        return (
            GateResult("crap", "not_run", f"ferramenta ausente: {exc}"),
            [],
            CONFIG_OR_TOOL,
            versions,
        )

    try:
        with tempfile.TemporaryDirectory(prefix="bob-coverage-") as tmp:
            coverage_json = Path(tmp) / "coverage.json"
            pytest_code = run_coverage(cwd, config.include, coverage_json, coverage_file)
            raw_coverage = coverage_json.read_text() if coverage_json.is_file() else ""
    except ToolError as exc:
        return (
            GateResult("crap", "not_run", f"coverage.py: {exc}"),
            [],
            CONFIG_OR_TOOL,
            versions,
        )
    if pytest_code not in {0, 5}:
        return (
            GateResult("crap", "not_run", "testes da baseline falharam antes de medir"),
            [],
            BASELINE_BROKEN,
            versions,
        )

    try:
        raw_lizard = run_lizard_csv(cwd, config.include, config.exclude)
        lizard_fns = parse_lizard_csv(raw_lizard)
        coverage_files = parse_coverage_json(raw_coverage)
    except (ToolError, OSError, LizardParseError, CoverageParseError) as exc:
        return (
            GateResult("crap", "not_run", str(exc)),
            [],
            CONFIG_OR_TOOL,
            versions,
        )

    metrics = []
    for item in lizard_fns:
        rel = _relative(cwd, item.file)
        metrics.append(
            to_metric(
                item,
                rel,
                coverage_for(coverage_files, rel),
                function_is_changed(rel, item.start_line, item.end_line, diff_lines),
            )
        )
    verdict, code = crap_verdict(metrics, max_crap, config.crap_scope)
    return verdict, metrics, code, versions


def _relative(cwd: Path, path: str) -> str:
    resolved = Path(path)
    try:
        return resolved.resolve().relative_to(cwd.resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def _worse(current: int, incoming: int) -> int:
    return incoming if incoming > current else current


def _fail_early(
    out_dir: Path,
    fmt: str,
    exit_code: int,
    reason: str,
    base: str | None,
    reproduce: str,
    gates: list[str],
) -> int:
    results = [GateResult(name, "not_run", reason) for name in gates]
    report = Report(
        schema_version=1,
        commit="",
        base=base or "",
        generated_at=datetime.now(timezone.utc).isoformat(),
        tool_versions={},
        gates=results,
        focus=[],
        top_crap=[],
        reproduce=reproduce,
        exit_code=exit_code,
    )
    write_report(report, out_dir, fmt)
    return exit_code
