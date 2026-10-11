"""Orquestra gates → relatório → exit code. A medição mora nos probes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from bob_quality.config import Config, ConfigError, load_config
from bob_quality.core import files_by_risk, informational_debt, top_changed_crap
from bob_quality.crap_gate import run_crap_gate
from bob_quality.diff import GitError, changed_lines, current_commit
from bob_quality.dry_gate import run_dry_gate
from bob_quality.exit_codes import CONFIG_OR_TOOL, PASSED
from bob_quality.models import Clone, FunctionMetric, GateResult, Report
from bob_quality.report import metric_row, write_report

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
    opened = _open(cwd, base, config_path, threshold, chosen_out, fmt, command, chosen_gates)
    if isinstance(opened, int):
        return opened
    config, chosen_base, max_crap, commit, diff_lines = opened
    measured = _measure(cwd, config, diff_lines, max_crap, coverage_file, chosen_gates)
    write_report(
        _assemble(measured, commit, chosen_base, diff_lines, max_crap, command),
        chosen_out,
        fmt,
    )
    return measured.exit_code


def _open(
    cwd: Path,
    base: str | None,
    config_path: Path | None,
    threshold: float | None,
    out_dir: Path,
    fmt: str,
    command: str,
    gates: list[str],
) -> tuple[Config, str, float, str, dict[str, set[int]]] | int:
    try:
        config = load_config(config_path, cwd)
    except ConfigError as exc:
        return _fail_early(out_dir, fmt, CONFIG_OR_TOOL, str(exc), base, command, gates)
    chosen_base = base or config.base
    max_crap = config.max_crap if threshold is None else threshold
    try:
        commit = current_commit(cwd)
        diff_lines = changed_lines(cwd, chosen_base)
    except GitError as exc:
        return _fail_early(
            out_dir, fmt, CONFIG_OR_TOOL, str(exc), chosen_base, command, gates
        )
    return config, chosen_base, max_crap, commit, diff_lines


@dataclass
class _Measured:
    versions: dict[str, str] = field(default_factory=dict)
    gates: list[GateResult] = field(default_factory=list)
    metrics: list[FunctionMetric] = field(default_factory=list)
    clones: list[Clone] = field(default_factory=list)
    exit_code: int = PASSED


def _measure(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    max_crap: float,
    coverage_file: Path | None,
    gates: list[str],
) -> _Measured:
    state = _Measured()
    for gate in gates:
        _absorb(state, gate, cwd, config, diff_lines, max_crap, coverage_file)
    return state


def _absorb(
    state: _Measured,
    gate: str,
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    max_crap: float,
    coverage_file: Path | None,
) -> None:
    if gate == "crap":
        result, metrics, code, versions = run_crap_gate(
            cwd=cwd,
            config=config,
            diff_lines=diff_lines,
            max_crap=max_crap,
            coverage_file=coverage_file,
        )
        state.metrics = metrics
        _record(state, result, code, versions)
        return
    if gate == "dry":
        result, found, code, versions = run_dry_gate(
            cwd=cwd, config=config, diff_lines=diff_lines
        )
        state.clones = found
        _record(state, result, code, versions)
        return
    _record(
        state,
        GateResult(gate, "not_run", "gate não implementado nesta fatia"),
        PASSED,
        {},
    )


def _record(
    state: _Measured,
    result: GateResult,
    code: int,
    versions: dict[str, str],
) -> None:
    state.gates.append(result)
    state.versions.update(versions)
    state.exit_code = _worse(state.exit_code, code)


def _assemble(
    measured: _Measured,
    commit: str,
    base: str,
    diff_lines: dict[str, set[int]],
    max_crap: float,
    command: str,
) -> Report:
    return Report(
        schema_version=1,
        commit=commit,
        base=base,
        generated_at=datetime.now(timezone.utc).isoformat(),
        tool_versions=measured.versions,
        gates=measured.gates,
        focus=files_by_risk(measured.metrics, measured.clones, set(diff_lines)),
        top_crap=[metric_row(item) for item in top_changed_crap(measured.metrics)],
        old_debt=[metric_row(item) for item in informational_debt(measured.metrics, max_crap)],
        clones=measured.clones,
        reproduce=command,
        exit_code=measured.exit_code,
    )


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
