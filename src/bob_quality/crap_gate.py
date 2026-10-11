"""Gate CRAP: escolhe a medição da linguagem e aplica o veredito do núcleo."""

from __future__ import annotations

from pathlib import Path

from bob_quality.config import Config
from bob_quality.core import crap_verdict
from bob_quality.exit_codes import CONFIG_OR_TOOL
from bob_quality.models import FunctionMetric, GateResult
from bob_quality.npm_tools import NODE_MISSING
from bob_quality.probe import ProbeResult
from bob_quality.python_probe import measure_python
from bob_quality.typescript_probe import measure_typescript


def run_crap_gate(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    max_crap: float,
    coverage_file: Path | None,
) -> tuple[GateResult, list[FunctionMetric], int, dict[str, str]]:
    metrics: list[FunctionMetric] = []
    versions: dict[str, str] = {}
    typescript_skip: str | None = None
    if "python" in config.languages:
        failure = _absorb(
            measure_python(cwd, config, diff_lines, coverage_file), metrics, versions
        )
        if failure is not None:
            return failure
    if "typescript" in config.languages:
        probed = measure_typescript(cwd, config, diff_lines)
        if "python" in config.languages and _node_is_missing(probed):
            versions.update(probed.versions)
            typescript_skip = probed.gate.reason if probed.gate is not None else None
        else:
            failure = _absorb(probed, metrics, versions)
            if failure is not None:
                return failure
    verdict, code = crap_verdict(metrics, max_crap, config.crap_scope)
    if typescript_skip:
        note = f"TypeScript pulado: {typescript_skip}"
        if verdict.status == "passed":
            verdict = GateResult("crap", "warn", note)
        else:
            verdict = GateResult("crap", verdict.status, f"{verdict.reason}; {note}")
    return verdict, metrics, code, versions


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
