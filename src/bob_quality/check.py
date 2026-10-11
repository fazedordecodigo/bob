"""Orquestra gates → relatório → exit code. A medição mora nos probes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from bob_quality.config import Config, ConfigError, load_config
from bob_quality.core import files_by_risk, informational_debt, top_changed_crap
from bob_quality.crap_gate import run_crap_gate
from bob_quality.diff import GitError, changed_lines, current_commit
from bob_quality.exit_codes import CONFIG_OR_TOOL, PASSED
from bob_quality.models import FunctionMetric, GateResult, Report
from bob_quality.mutate import MutationOutcome, focus_with_survivors, run_mutation_gate
from bob_quality.report import metric_row, write_report
from bob_quality.waivers import WaiverError, load_waivers

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
    max_workers: int | None = None,
) -> int:
    opened = _open_check(cwd, base, gates, config_path, out_dir, fmt, reproduce, threshold)
    if isinstance(opened, int):
        return opened
    config, chosen_base, commit, diff_lines, chosen_out, command, max_crap, chosen_gates = opened
    versions, gate_results, metrics, exit_code, mutation = _execute_gates(
        cwd, config, diff_lines, chosen_out, max_crap, chosen_gates, coverage_file, max_workers
    )
    return _write_check_report(
        cwd, chosen_out, fmt, commit, chosen_base, command, versions,
        gate_results, metrics, exit_code, mutation, max_crap, chosen_gates,
    )


def _open_check(
    cwd: Path,
    base: str | None,
    gates: list[str] | None,
    config_path: Path | None,
    out_dir: Path | None,
    fmt: str,
    reproduce: str | None,
    threshold: float | None,
) -> int | tuple[Config, str, str, dict[str, set[int]], Path, str, float, list[str]]:
    chosen_gates = gates or list(DEFAULT_GATES)
    chosen_out = out_dir or (cwd / ".bob")
    command = reproduce or "bob check"
    try:
        config = load_config(config_path, cwd)
    except ConfigError as exc:
        return _fail_early(chosen_out, fmt, CONFIG_OR_TOOL, str(exc), base, command, chosen_gates)
    chosen_base = base or config.base
    max_crap = config.max_crap if threshold is None else threshold
    try:
        commit = current_commit(cwd)
        diff_lines = changed_lines(cwd, chosen_base)
    except GitError as exc:
        return _fail_early(
            chosen_out, fmt, CONFIG_OR_TOOL, str(exc), chosen_base, command, chosen_gates
        )
    return config, chosen_base, commit, diff_lines, chosen_out, command, max_crap, chosen_gates


def _execute_gates(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    chosen_out: Path,
    max_crap: float,
    chosen_gates: list[str],
    coverage_file: Path | None,
    max_workers: int | None,
) -> tuple[dict[str, str], list[GateResult], list[FunctionMetric], int, MutationOutcome | None]:
    versions: dict[str, str] = {}
    gate_results: list[GateResult] = []
    metrics: list[FunctionMetric] = []
    exit_code = PASSED
    mutation: MutationOutcome | None = None
    for gate in chosen_gates:
        exit_code, mutation = _apply_gate(
            gate, cwd, config, diff_lines, chosen_out, max_crap, coverage_file,
            max_workers, versions, gate_results, metrics, exit_code, mutation,
        )
    return versions, gate_results, metrics, exit_code, mutation


def _apply_gate(
    gate: str,
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    chosen_out: Path,
    max_crap: float,
    coverage_file: Path | None,
    max_workers: int | None,
    versions: dict[str, str],
    gate_results: list[GateResult],
    metrics: list[FunctionMetric],
    exit_code: int,
    mutation: MutationOutcome | None,
) -> tuple[int, MutationOutcome | None]:
    if gate == "mutate":
        return _apply_mutate(
            cwd, config, diff_lines, chosen_out, max_workers, versions, gate_results, exit_code
        )
    if gate != "crap":
        gate_results.append(
            GateResult(name=gate, status="not_run", reason="gate não implementado nesta fatia")
        )
        return exit_code, mutation
    result, measured, code, crap_versions = run_crap_gate(
        cwd=cwd,
        config=config,
        diff_lines=diff_lines,
        max_crap=max_crap,
        coverage_file=coverage_file,
    )
    gate_results.append(result)
    metrics.clear()
    metrics.extend(measured)
    versions.update(crap_versions)
    return _worse(exit_code, code), mutation


def _apply_mutate(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    chosen_out: Path,
    max_workers: int | None,
    versions: dict[str, str],
    gate_results: list[GateResult],
    exit_code: int,
) -> tuple[int, MutationOutcome]:
    mutation = run_mutation_gate(
        cwd=cwd,
        config=config,
        diff_lines=diff_lines,
        out_dir=chosen_out,
        max_workers=max_workers,
    )
    gate_results.append(mutation.result)
    versions.update(mutation.versions)
    return _worse(exit_code, mutation.exit_code), mutation


def _write_check_report(
    cwd: Path,
    chosen_out: Path,
    fmt: str,
    commit: str,
    chosen_base: str,
    command: str,
    versions: dict[str, str],
    gate_results: list[GateResult],
    metrics: list[FunctionMetric],
    exit_code: int,
    mutation: MutationOutcome | None,
    max_crap: float,
    chosen_gates: list[str],
) -> int:
    focus = files_by_risk(metrics)
    survivors: list[dict[str, object]] = []
    mutation_summary = None
    waivers, failed = _waivers_for_report(
        cwd, chosen_out, fmt, chosen_base, command, chosen_gates, mutation
    )
    if failed is not None:
        return failed
    if mutation is not None:
        survivors = mutation.survivors
        mutation_summary = mutation.summary
        focus = focus_with_survivors(focus, survivors)
    report = Report(
        schema_version=1,
        commit=commit,
        base=chosen_base,
        generated_at=datetime.now(timezone.utc).isoformat(),
        tool_versions=versions,
        gates=gate_results,
        focus=focus,
        top_crap=[metric_row(item) for item in top_changed_crap(metrics)],
        old_debt=[metric_row(item) for item in informational_debt(metrics, max_crap)],
        reproduce=command,
        exit_code=exit_code,
        waivers=waivers,
        survivors=survivors,
        mutation=mutation_summary,
    )
    write_report(report, chosen_out, fmt)
    return exit_code


def _waivers_for_report(
    cwd: Path,
    chosen_out: Path,
    fmt: str,
    chosen_base: str,
    command: str,
    chosen_gates: list[str],
    mutation: MutationOutcome | None,
) -> tuple[list[dict[str, object]], int | None]:
    if mutation is not None:
        return mutation.waivers, None
    try:
        return [item.as_dict() for item in load_waivers(cwd)], None
    except WaiverError as exc:
        code = _fail_early(
            chosen_out, fmt, CONFIG_OR_TOOL, str(exc), chosen_base, command, chosen_gates
        )
        return [], code


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
