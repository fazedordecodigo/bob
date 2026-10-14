"""Gate CRAP: escolhe a medição da linguagem e aplica o veredito do núcleo."""

from __future__ import annotations

from pathlib import Path

from bob_quality.config import Config
from bob_quality.core import crap_verdict
from bob_quality.exit_codes import CONFIG_OR_TOOL
from bob_quality.messages import Text, msg
from bob_quality.models import FunctionMetric, GateResult
from bob_quality.npm_tools import NODE_MISSING
from bob_quality.probe import ProbeResult
from bob_quality.python_probe import measure_python
from bob_quality.suite_memo import SuiteMemo
from bob_quality.typescript_probe import measure_typescript


def run_crap_gate(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    max_crap: float,
    coverage_file: Path | None,
    memo: SuiteMemo,
) -> tuple[GateResult, list[FunctionMetric], int, dict[str, str], int | None]:
    """O último item é o exit do pytest da medição Python, ou None sem pytest."""
    metrics: list[FunctionMetric] = []
    versions: dict[str, str] = {}
    typescript_skip: Text | None = None
    baseline: int | None = None
    if "python" in config.languages:
        python = measure_python(cwd, config, diff_lines, coverage_file, memo)
        baseline = python.baseline
        failure = _absorb(python, metrics, versions)
        if failure is not None:
            return (*failure, baseline)
    if "typescript" in config.languages:
        probed = measure_typescript(cwd, config, diff_lines, memo)
        if "python" in config.languages and _node_is_missing(probed):
            versions.update(probed.versions)
            typescript_skip = probed.gate.reason
        else:
            failure = _absorb(probed, metrics, versions)
            if failure is not None:
                return (*failure, baseline)
    verdict, code = crap_verdict(metrics, max_crap, config.crap_scope)
    return _with_typescript_skip(verdict, typescript_skip), metrics, code, versions, baseline


def _with_typescript_skip(verdict: GateResult, typescript_skip: Text | None) -> GateResult:
    if typescript_skip is None:
        return verdict
    note = msg("probe.typescript_skipped", reason=typescript_skip)
    if verdict.status == "passed":
        return GateResult("crap", "warn", note)
    return GateResult("crap", verdict.status, msg("probe.joined", first=verdict.reason, second=note))


def _node_is_missing(probed: ProbeResult) -> bool:
    return (
        probed.exit_code == CONFIG_OR_TOOL
        and probed.gate is not None
        and probed.gate.reason == NODE_MISSING
    )


def _absorb(
    probed: ProbeResult,
    metrics: list[FunctionMetric],
    versions: dict[str, str],
) -> tuple[GateResult, list[FunctionMetric], int, dict[str, str]] | None:
    versions.update(probed.versions)
    if probed.gate is not None and probed.exit_code is not None:
        return probed.gate, [], probed.exit_code, versions
    metrics.extend(probed.metrics)
    return None
