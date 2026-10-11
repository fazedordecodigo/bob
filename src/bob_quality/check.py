"""Orquestra adaptador → núcleo → relatório → exit code."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bob_quality.adapters.coverage import (
    CoverageParseError,
    function_coverage,
    parse_coverage_json,
)
from bob_quality.adapters.lizard import LizardFunction, LizardParseError, parse_lizard_csv
from bob_quality.config import Config, ConfigError, load_config
from bob_quality.crap import calculate_crap
from bob_quality.diff import GitError, changed_lines, current_commit, function_is_changed
from bob_quality.exit_codes import BASELINE_BROKEN, CONFIG_OR_TOOL, GATE_FAILED, PASSED
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
    try:
        config = load_config(config_path, cwd)
    except ConfigError as exc:
        return _fail_early(cwd, out_dir, fmt, CONFIG_OR_TOOL, str(exc), base, reproduce)

    chosen_base = base or config.base
    chosen_gates = gates or list(DEFAULT_GATES)
    chosen_out = out_dir or (cwd / ".bob")
    max_crap = config.max_crap if threshold is None else threshold
    command = reproduce or "bob check"

    try:
        commit = current_commit(cwd)
        diff_lines = changed_lines(cwd, chosen_base)
    except GitError as exc:
        return _fail_early(
            cwd, chosen_out, fmt, CONFIG_OR_TOOL, str(exc), chosen_base, command
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
            out_dir=chosen_out,
        )
        gate_results.append(result)
        metrics = measured
        exit_code = _worse(exit_code, code)

    changed = [item for item in metrics if item.changed]
    old_debt = [
        item for item in metrics if not item.changed and item.crap > max_crap
    ]
    top = sorted(changed, key=lambda item: item.crap, reverse=True)[:5]
    focus = _focus(changed)
    report = Report(
        schema_version=1,
        commit=commit,
        base=chosen_base,
        generated_at=datetime.now(timezone.utc).isoformat(),
        tool_versions=versions,
        gates=gate_results,
        focus=focus,
        top_crap=[metric_row(item) for item in top],
        old_debt=[metric_row(item) for item in old_debt],
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
    out_dir: Path,
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

    out_dir.mkdir(parents=True, exist_ok=True)
    coverage_json = out_dir / "coverage.json"
    try:
        pytest_code = run_coverage(cwd, config.include, coverage_json, coverage_file)
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
        coverage_files = parse_coverage_json(coverage_json.read_text())
    except (ToolError, OSError, LizardParseError, CoverageParseError) as exc:
        return (
            GateResult("crap", "not_run", str(exc)),
            [],
            CONFIG_OR_TOOL,
            versions,
        )

    metrics = [
        _to_metric(cwd, item, coverage_files, diff_lines) for item in lizard_fns
    ]
    blockers = [item for item in metrics if item.changed and item.crap > max_crap]
    if blockers:
        names = ", ".join(f"{item.name}@{item.file}:{item.start_line}" for item in blockers)
        return (
            GateResult("crap", "failed", f"CRAP > {max_crap}: {names}"),
            metrics,
            GATE_FAILED,
            versions,
        )
    return GateResult("crap", "passed", None), metrics, PASSED, versions


def _to_metric(
    cwd: Path,
    item: LizardFunction,
    coverage_files: dict[str, Any],
    diff_lines: dict[str, set[int]],
) -> FunctionMetric:
    rel = _relative(cwd, item.file)
    file_data = _coverage_for(coverage_files, rel)
    coverage = function_coverage(file_data, item.start_line, item.end_line)
    crap = calculate_crap(item.cc, coverage)
    return FunctionMetric(
        lang="python",
        module=_module(rel),
        name=item.name,
        file=rel,
        start_line=item.start_line,
        end_line=item.end_line,
        cc=item.cc,
        coverage=coverage,
        crap=crap,
        changed=function_is_changed(rel, item.start_line, item.end_line, diff_lines),
    )


def _coverage_for(coverage_files: dict[str, Any], rel: str) -> dict[str, Any]:
    if rel in coverage_files:
        return coverage_files[rel]
    for key, value in coverage_files.items():
        if key.replace("\\", "/") == rel or key.endswith("/" + rel):
            return value
    return {}


def _relative(cwd: Path, path: str) -> str:
    resolved = Path(path)
    try:
        return resolved.resolve().relative_to(cwd.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _module(rel: str) -> str:
    return rel.replace("/", ".").removesuffix(".py")


def _focus(changed: list[FunctionMetric]) -> list[dict[str, object]]:
    by_file: dict[str, float] = {}
    for item in changed:
        by_file[item.file] = max(by_file.get(item.file, 0.0), item.crap)
    ordered = sorted(by_file.items(), key=lambda pair: pair[1], reverse=True)
    return [{"file": file, "risk": risk} for file, risk in ordered]


def _worse(current: int, incoming: int) -> int:
    return incoming if incoming > current else current


def _fail_early(
    cwd: Path,
    out_dir: Path | None,
    fmt: str,
    exit_code: int,
    reason: str,
    base: str | None,
    reproduce: str | None,
) -> int:
    target = out_dir or (cwd / ".bob")
    report = Report(
        schema_version=1,
        commit="",
        base=base or "",
        generated_at=datetime.now(timezone.utc).isoformat(),
        tool_versions={},
        gates=[GateResult("crap", "not_run", reason)],
        focus=[],
        top_crap=[],
        reproduce=reproduce or "bob check",
        exit_code=exit_code,
    )
    write_report(report, target, fmt)
    return exit_code
