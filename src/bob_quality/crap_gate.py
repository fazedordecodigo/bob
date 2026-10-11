"""Gate CRAP: escolhe a medição da linguagem e aplica o veredito do núcleo."""

from __future__ import annotations

from pathlib import Path

from bob_quality.config import Config
from bob_quality.core import crap_verdict
from bob_quality.models import FunctionMetric, GateResult
from bob_quality.python_probe import measure_python


def run_crap_gate(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    max_crap: float,
    coverage_file: Path | None,
) -> tuple[GateResult, list[FunctionMetric], int, dict[str, str]]:
    probed = measure_python(cwd, config, diff_lines, coverage_file)
    if probed.gate is not None and probed.exit_code is not None:
        return probed.gate, probed.metrics, probed.exit_code, probed.versions
    verdict, code = crap_verdict(probed.metrics, max_crap, config.crap_scope)
    return verdict, probed.metrics, code, probed.versions
