"""Gate CRAP: escolhe a medição da linguagem e aplica o veredito do núcleo."""

from __future__ import annotations

from pathlib import Path

from bob_quality.config import Config
from bob_quality.core import crap_verdict
from bob_quality.models import FunctionMetric, GateResult
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
    if "python" in config.languages:
        failure = _absorb(
            measure_python(cwd, config, diff_lines, coverage_file), metrics, versions
        )
        if failure is not None:
            return failure
    if "typescript" in config.languages:
        failure = _absorb(measure_typescript(cwd, config, diff_lines), metrics, versions)
        if failure is not None:
            return failure
    verdict, code = crap_verdict(metrics, max_crap, config.crap_scope)
    return verdict, metrics, code, versions


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
