"""Orquestra gates → relatório → exit code. A medição mora nos probes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from bob_quality.config import ConfigError, load_config
from bob_quality.core import files_by_risk, informational_debt, top_changed_crap
from bob_quality.crap_gate import run_crap_gate
from bob_quality.diff import GitError, changed_lines, current_commit
from bob_quality.exit_codes import CONFIG_OR_TOOL, PASSED
from bob_quality.models import FunctionMetric, GateResult, Report
from bob_quality.mutate import focus_with_survivors, run_mutation_gate
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
    max_workers: int | None = None,
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
    mutation = None

    for gate in chosen_gates:
        if gate == "mutate":
            mutation = run_mutation_gate(
                cwd=cwd,
                config=config,
                diff_lines=diff_lines,
                out_dir=chosen_out,
                max_workers=max_workers,
            )
            gate_results.append(mutation.result)
            versions.update(mutation.versions)
            exit_code = _worse(exit_code, mutation.exit_code)
            continue
        if gate != "crap":
            gate_results.append(
                GateResult(
                    name=gate,
                    status="not_run",
                    reason="gate não implementado nesta fatia",
                )
            )
            continue
        result, measured, code, crap_versions = run_crap_gate(
            cwd=cwd,
            config=config,
            diff_lines=diff_lines,
            max_crap=max_crap,
            coverage_file=coverage_file,
        )
        gate_results.append(result)
        metrics = measured
        versions.update(crap_versions)
        exit_code = _worse(exit_code, code)

    focus = files_by_risk(metrics)
    survivors: list[dict[str, object]] = []
    waivers: list[dict[str, object]] = []
    mutation_summary = None
    if mutation is not None:
        survivors = mutation.survivors
        waivers = mutation.waivers
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
