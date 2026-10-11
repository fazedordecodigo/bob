"""Testes da fórmula CRAP no núcleo (seam 1 da SPEC)."""

from bob_quality.core import crap_verdict
from bob_quality.crap import calculate_crap
from bob_quality.models import FunctionMetric


def test_crap_cc1_zero_coverage_is_two() -> None:
    """SPEC: CC 1 e cobertura 0% → CRAP = 1² × 1³ + 1 = 2."""
    assert calculate_crap(cc=1, coverage=0.0) == 2.0


def test_crap_cc1_full_coverage_is_one() -> None:
    """SPEC: CC 1 e cobertura 100% → CRAP = 1."""
    assert calculate_crap(cc=1, coverage=1.0) == 1.0


def test_crap_cc3_zero_coverage_is_twelve() -> None:
    """CC 3 e cobertura 0% → 3² × 1 + 3 = 12, acima do limite 10 da spec."""
    assert calculate_crap(cc=3, coverage=0.0) == 12.0


def test_crap_verdict_fails_only_changed_functions_over_ten() -> None:
    changed = FunctionMetric(
        lang="python",
        module="app.risky",
        name="messy",
        file="src/app/risky.py",
        start_line=1,
        end_line=8,
        cc=4,
        coverage=0.0,
        crap=20.0,
        changed=True,
    )
    debt = FunctionMetric(
        lang="python",
        module="app.legacy",
        name="legacy",
        file="src/app/legacy.py",
        start_line=1,
        end_line=8,
        cc=4,
        coverage=0.0,
        crap=20.0,
        changed=False,
    )
    result, code = crap_verdict([changed, debt], max_crap=10, scope="changed")
    assert code == 1
    assert result.status == "failed"
    safe = FunctionMetric(
        lang="python",
        module="app.safe",
        name="add",
        file="src/app/safe.py",
        start_line=1,
        end_line=2,
        cc=1,
        coverage=1.0,
        crap=1.0,
        changed=True,
    )
    result, code = crap_verdict([safe, debt], max_crap=10, scope="changed")
    assert code == 0
    assert result.status == "passed"


def test_crap_verdict_fails_when_crap_equals_threshold() -> None:
    """SPEC: só CRAP < 10 passa; CRAP = 10 falha."""
    on_the_limit = FunctionMetric(
        lang="python",
        module="app.edge",
        name="edge",
        file="src/app/edge.py",
        start_line=1,
        end_line=4,
        cc=10,
        coverage=1.0,
        crap=10.0,
        changed=True,
    )
    result, code = crap_verdict([on_the_limit], max_crap=10, scope="changed")
    assert code == 1
    assert result.status == "failed"
