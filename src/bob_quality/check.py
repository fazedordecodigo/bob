"""Orquestra gates → relatório → exit code. A medição mora nos probes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from bob_quality.config import Config, ConfigError, load_config
from bob_quality.core import files_by_risk, informational_debt, top_changed_crap
from bob_quality.coverage_gate import run_coverage_gate
from bob_quality.crap_gate import run_crap_gate
from bob_quality.dead_code import WarningOnly, run_dead_code_gate
from bob_quality.deps_gate import run_deps_gate
from bob_quality.diff import GitError, changed_lines, current_commit
from bob_quality.dry_gate import run_dry_gate
from bob_quality.typing_gate import run_typing_gate
from bob_quality.exit_codes import CONFIG_OR_TOOL, PASSED
from bob_quality.messages import DEFAULT_LANGUAGE, Language, Text, msg, reason
from bob_quality.models import (
    Clone,
    DeadSection,
    DepViolation,
    DiffCoverage,
    FunctionMetric,
    GateResult,
    Report,
    SecretLedger,
    SecurityReport,
    SupplyReport,
)
from bob_quality.mutate import MutationOutcome, focus_with_survivors
from bob_quality.mutate_gate import run_mutate_gate
from bob_quality.report import metric_row, violation_rows, write_report
from bob_quality.secrets_gate import run_secrets_gate
from bob_quality.security_gate import run_security_gate
from bob_quality.suite_memo import SuiteMemo
from bob_quality.supply import run_supply_gate
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
    lang: Language = DEFAULT_LANGUAGE,
    dry_fail: bool = False,
    max_new_clones: int | None = None,
) -> int:
    chosen_gates = gates or list(DEFAULT_GATES)
    chosen_out = out_dir or (cwd / ".bob")
    command = reproduce or "bob check"
    opened = _open(cwd, base, config_path, threshold, command, chosen_gates)
    if isinstance(opened, Report):
        return _written(opened, chosen_out, fmt, lang)
    config, chosen_base, max_crap, commit, diff_lines = opened
    measured = _measure(
        cwd,
        config,
        chosen_base,
        diff_lines,
        max_crap,
        coverage_file,
        chosen_gates,
        chosen_out,
        max_workers,
        dry_fail,
        max_new_clones,
    )
    if measured.mutation is None:
        loaded = _load_idle_waivers(cwd, chosen_base, command, chosen_gates)
        if isinstance(loaded, Report):
            return _written(loaded, chosen_out, fmt, lang)
        measured.loaded_waivers = loaded
    return _written(
        _assemble(measured, commit, chosen_base, diff_lines, max_crap, command),
        chosen_out,
        fmt,
        lang,
    )


def _written(report: Report, out_dir: Path, fmt: str, lang: Language) -> int:
    write_report(report, out_dir, fmt, lang)
    return report.exit_code


def _open(
    cwd: Path,
    base: str | None,
    config_path: Path | None,
    threshold: float | None,
    command: str,
    gates: list[str],
) -> tuple[Config, str, float, str, dict[str, set[int]]] | Report:
    try:
        config = load_config(config_path, cwd)
    except ConfigError as exc:
        return _fail_early(CONFIG_OR_TOOL, reason(exc), base, command, gates)
    chosen_base = base or config.base
    max_crap = config.max_crap if threshold is None else threshold
    try:
        commit = current_commit(cwd)
        diff_lines = changed_lines(cwd, chosen_base)
    except GitError as exc:
        return _fail_early(CONFIG_OR_TOOL, reason(exc), chosen_base, command, gates)
    return config, chosen_base, max_crap, commit, diff_lines


@dataclass
class _Measured:
    versions: dict[str, str] = field(default_factory=dict)
    gates: list[GateResult] = field(default_factory=list)
    metrics: list[FunctionMetric] = field(default_factory=list)
    clones: list[Clone] = field(default_factory=list)
    violations: list[DepViolation] = field(default_factory=list)
    exit_code: int = PASSED
    mutation: MutationOutcome | None = None
    secrets: SecretLedger | None = None
    loaded_waivers: list[dict[str, object]] = field(default_factory=list)
    baseline: int | None = None
    diff_coverage: DiffCoverage | None = None
    supply: SupplyReport | None = None
    security: SecurityReport | None = None
    typing: dict[str, object] | None = None
    dead_code: DeadSection | None = None


def _measure(
    cwd: Path,
    config: Config,
    base: str,
    diff_lines: dict[str, set[int]],
    max_crap: float,
    coverage_file: Path | None,
    gates: list[str],
    out_dir: Path,
    max_workers: int | None,
    dry_fail: bool,
    max_new_clones: int | None,
) -> _Measured:
    state = _Measured()
    memo = SuiteMemo(want_lcov="coverage" in gates, want_json="crap" in gates)
    try:
        for gate in gates:
            _absorb(
                state,
                gate,
                cwd,
                config,
                base,
                diff_lines,
                max_crap,
                coverage_file,
                out_dir,
                max_workers,
                dry_fail,
                max_new_clones,
                memo,
            )
    finally:
        memo.close()
    return state


def _absorb(
    state: _Measured,
    gate: str,
    cwd: Path,
    config: Config,
    base: str,
    diff_lines: dict[str, set[int]],
    max_crap: float,
    coverage_file: Path | None,
    out_dir: Path,
    max_workers: int | None,
    dry_fail: bool,
    max_new_clones: int | None,
    memo: SuiteMemo,
) -> None:
    if gate == "crap":
        result, metrics, code, versions, baseline = run_crap_gate(
            cwd=cwd,
            config=config,
            diff_lines=diff_lines,
            max_crap=max_crap,
            coverage_file=coverage_file,
            memo=memo,
        )
        state.metrics = metrics
        state.baseline = baseline
        _record(state, result, code, versions)
        return
    if gate == "dry":
        result, found, code, versions = run_dry_gate(
            cwd=cwd,
            config=config,
            diff_lines=diff_lines,
            dry_fail=dry_fail,
            max_new_clones=max_new_clones,
        )
        state.clones = found
        _record(state, result, code, versions)
        return
    if gate == "deps":
        _absorb_deps(state, cwd, config, diff_lines)
        return
    if gate == "mutate":
        mutation = run_mutate_gate(
            cwd=cwd,
            config=config,
            diff_lines=diff_lines,
            out_dir=out_dir,
            max_workers=max_workers,
            baseline=state.baseline,
        )
        state.mutation = mutation
        _record(state, mutation.result, mutation.exit_code, mutation.versions)
        return
    if gate == "coverage":
        outcome = run_coverage_gate(cwd, config, base, coverage_file, memo)
        state.diff_coverage = outcome.diff_coverage
        _record(state, outcome.result, outcome.exit_code, outcome.versions)
        return
    _absorb_rest(state, gate, cwd, config, base, diff_lines)


def _absorb_rest(
    state: _Measured,
    gate: str,
    cwd: Path,
    config: Config,
    base: str,
    diff_lines: dict[str, set[int]],
) -> None:
    if gate == "supply":
        result, code, versions, supply = run_supply_gate(cwd, config, diff_lines, base)
        state.supply = supply
        _record(state, result, code, versions)
        return
    if gate == "security":
        result, code, versions, security = run_security_gate(cwd, config, base, diff_lines)
        state.security = security
        _record(state, result, code, versions)
        return
    if gate == "typing":
        result, code, versions, found = run_typing_gate(cwd, config, diff_lines)
        state.typing = found
        _record(state, result, code, versions)
        return
    if gate == "secrets":
        outcome = run_secrets_gate(cwd=cwd, config=config, diff_lines=diff_lines)
        state.secrets = outcome.ledger
        _record(state, outcome.result, outcome.exit_code, outcome.versions)
        return
    if gate == "dead_code":
        _record_dead(state, run_dead_code_gate(cwd, config, diff_lines))
        return
    _record(
        state,
        GateResult(gate, "not_run", msg("check.gate_not_implemented")),
        PASSED,
        {},
    )


def _absorb_deps(
    state: _Measured,
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
) -> None:
    result, code, versions, found = run_deps_gate(cwd, config, set(diff_lines))
    state.violations = found
    _record(state, result, code, versions)


def _record_dead(state: _Measured, advisory: WarningOnly) -> None:
    state.gates.append(advisory.as_gate())
    state.versions.update(dict(advisory.versions))
    state.dead_code = advisory.section


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
    focus = files_by_risk(measured.metrics, measured.clones, set(diff_lines))
    survivors: list[dict[str, object]] = []
    summary = None
    waivers = measured.loaded_waivers
    if measured.mutation is not None:
        survivors = measured.mutation.survivors
        summary = measured.mutation.summary
        waivers = measured.mutation.waivers
        focus = focus_with_survivors(focus, survivors)
    return Report(
        schema_version=1,
        commit=commit,
        base=base,
        generated_at=datetime.now(timezone.utc).isoformat(),
        tool_versions=measured.versions,
        gates=measured.gates,
        focus=focus,
        top_crap=[metric_row(item) for item in top_changed_crap(measured.metrics)],
        old_debt=[metric_row(item) for item in informational_debt(measured.metrics, max_crap)],
        dependencies=violation_rows(measured.violations, in_diff=True),
        old_dependencies=violation_rows(measured.violations, in_diff=False),
        clones=measured.clones,
        reproduce=command,
        exit_code=measured.exit_code,
        waivers=waivers,
        survivors=survivors,
        mutation=summary,
        diff_coverage=measured.diff_coverage,
        supply=measured.supply,
        security=measured.security,
        typing=measured.typing,
        secrets=measured.secrets,
        dead_code=measured.dead_code,
    )


def _load_idle_waivers(
    cwd: Path,
    base: str,
    command: str,
    gates: list[str],
) -> list[dict[str, object]] | Report:
    try:
        return [item.as_dict() for item in load_waivers(cwd)]
    except WaiverError as exc:
        return _fail_early(CONFIG_OR_TOOL, reason(exc), base, command, gates)


def _worse(current: int, incoming: int) -> int:
    return incoming if incoming > current else current


def _fail_early(
    exit_code: int,
    why: Text,
    base: str | None,
    reproduce: str,
    gates: list[str],
) -> Report:
    return Report(
        schema_version=1,
        commit="",
        base=base or "",
        generated_at=datetime.now(timezone.utc).isoformat(),
        tool_versions={},
        gates=[GateResult(name, "not_run", why) for name in gates],
        focus=[],
        top_crap=[],
        reproduce=reproduce,
        exit_code=exit_code,
    )
