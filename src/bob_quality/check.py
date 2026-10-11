"""Orquestra gates → relatório → exit code. A medição mora nos probes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bob_quality.config import Config, ConfigError, load_config
from bob_quality.core import files_by_risk, informational_debt, top_changed_crap
from bob_quality.crap_gate import run_crap_gate
from bob_quality.deps_gate import run_deps_gate
from bob_quality.diff import GitError, changed_lines, current_commit
from bob_quality.exit_codes import CONFIG_OR_TOOL, PASSED
from bob_quality.models import DepViolation, FunctionMetric, GateResult, Report
from bob_quality.report import metric_row, violation_rows, write_report

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
    context = _context(
        cwd, base, gates, config_path, out_dir, fmt, threshold, coverage_file, reproduce
    )
    if isinstance(context, int):
        return context
    applied = _apply_gates(
        cwd=context.cwd,
        config=context.config,
        gates=context.gates,
        diff_lines=context.diff_lines,
        max_crap=context.max_crap,
        coverage_file=context.coverage_file,
    )
    write_report(_report(context, applied), context.out_dir, context.fmt)
    return applied.exit_code


@dataclass
class _Context:
    cwd: Path
    config: Config
    gates: list[str]
    out_dir: Path
    fmt: str
    command: str
    base: str
    commit: str
    diff_lines: dict[str, set[int]]
    max_crap: float
    coverage_file: Path | None


def _context(
    cwd: Path,
    base: str | None,
    gates: list[str] | None,
    config_path: Path | None,
    out_dir: Path | None,
    fmt: str,
    threshold: float | None,
    coverage_file: Path | None,
    reproduce: str | None,
) -> _Context | int:
    chosen_gates = gates or list(DEFAULT_GATES)
    chosen_out = out_dir or (cwd / ".bob")
    command = reproduce or "bob check"
    config = _load_config(config_path, cwd, chosen_out, fmt, base, command, chosen_gates)
    if isinstance(config, int):
        return config
    chosen_base = base or config.base
    diff = _load_diff(cwd, chosen_base, chosen_out, fmt, command, chosen_gates)
    if isinstance(diff, int):
        return diff
    commit, diff_lines = diff
    max_crap = config.max_crap if threshold is None else threshold
    return _Context(
        cwd,
        config,
        chosen_gates,
        chosen_out,
        fmt,
        command,
        chosen_base,
        commit,
        diff_lines,
        max_crap,
        coverage_file,
    )


def _load_config(
    config_path: Path | None,
    cwd: Path,
    out_dir: Path,
    fmt: str,
    base: str | None,
    command: str,
    gates: list[str],
) -> Config | int:
    try:
        return load_config(config_path, cwd)
    except ConfigError as exc:
        return _fail_early(out_dir, fmt, CONFIG_OR_TOOL, str(exc), base, command, gates)


def _load_diff(
    cwd: Path,
    base: str,
    out_dir: Path,
    fmt: str,
    command: str,
    gates: list[str],
) -> tuple[str, dict[str, set[int]]] | int:
    try:
        return current_commit(cwd), changed_lines(cwd, base)
    except GitError as exc:
        return _fail_early(out_dir, fmt, CONFIG_OR_TOOL, str(exc), base, command, gates)


def _report(context: _Context, applied: _Applied) -> Report:
    metrics = applied.metrics
    return Report(
        schema_version=1,
        commit=context.commit,
        base=context.base,
        generated_at=datetime.now(timezone.utc).isoformat(),
        tool_versions=applied.versions,
        gates=applied.gates,
        focus=files_by_risk(metrics),
        top_crap=[metric_row(item) for item in top_changed_crap(metrics)],
        old_debt=[metric_row(item) for item in informational_debt(metrics, applied.max_crap)],
        dependencies=violation_rows(applied.violations, in_diff=True),
        old_dependencies=violation_rows(applied.violations, in_diff=False),
        reproduce=context.command,
        exit_code=applied.exit_code,
    )


@dataclass
class _Applied:
    gates: list[GateResult]
    metrics: list[FunctionMetric]
    violations: list[DepViolation]
    versions: dict[str, str]
    exit_code: int
    max_crap: float


def _apply_gates(
    cwd: Path,
    config: Config,
    gates: list[str],
    diff_lines: dict[str, set[int]],
    max_crap: float,
    coverage_file: Path | None,
) -> _Applied:
    versions: dict[str, str] = {}
    gate_results: list[GateResult] = []
    metrics: list[FunctionMetric] = []
    violations: list[DepViolation] = []
    exit_code = PASSED
    for gate in gates:
        exit_code = _one_gate(
            gate,
            _GateCall(cwd, config, diff_lines, max_crap, coverage_file),
            gate_results,
            metrics,
            violations,
            versions,
            exit_code,
        )
    return _Applied(gate_results, metrics, violations, versions, exit_code, max_crap)


@dataclass
class _GateCall:
    cwd: Path
    config: Config
    diff_lines: dict[str, set[int]]
    max_crap: float
    coverage_file: Path | None


def _one_gate(
    gate: str,
    call: _GateCall,
    gate_results: list[GateResult],
    metrics: list[FunctionMetric],
    violations: list[DepViolation],
    versions: dict[str, str],
    exit_code: int,
) -> int:
    if gate == "crap":
        return _apply_crap(call, gate_results, metrics, versions, exit_code)
    if gate == "deps":
        return _apply_deps(call, gate_results, violations, versions, exit_code)
    gate_results.append(
        GateResult(name=gate, status="not_run", reason="gate não implementado nesta fatia")
    )
    return exit_code


def _apply_crap(
    call: _GateCall,
    gate_results: list[GateResult],
    metrics: list[FunctionMetric],
    versions: dict[str, str],
    exit_code: int,
) -> int:
    result, measured, code, gate_versions = run_crap_gate(
        cwd=call.cwd,
        config=call.config,
        diff_lines=call.diff_lines,
        max_crap=call.max_crap,
        coverage_file=call.coverage_file,
    )
    gate_results.append(result)
    metrics[:] = measured
    versions.update(gate_versions)
    return _worse(exit_code, code)


def _apply_deps(
    call: _GateCall,
    gate_results: list[GateResult],
    violations: list[DepViolation],
    versions: dict[str, str],
    exit_code: int,
) -> int:
    result, code, gate_versions, found = run_deps_gate(
        call.cwd, call.config, set(call.diff_lines)
    )
    gate_results.append(result)
    violations.extend(found)
    versions.update(gate_versions)
    return _worse(exit_code, code)


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
