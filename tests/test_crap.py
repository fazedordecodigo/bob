"""Testes da fórmula CRAP no núcleo (seam 1 da SPEC)."""

from bob_quality.crap import calculate_crap


def test_crap_cc1_zero_coverage_is_two() -> None:
    """SPEC: CC 1 e cobertura 0% → CRAP = 1² × 1³ + 1 = 2."""
    assert calculate_crap(cc=1, coverage=0.0) == 2.0


def test_crap_cc1_full_coverage_is_one() -> None:
    """SPEC: CC 1 e cobertura 100% → CRAP = 1."""
    assert calculate_crap(cc=1, coverage=1.0) == 1.0


def test_crap_cc3_zero_coverage_is_twelve() -> None:
    """CC 3 e cobertura 0% → 3² × 1 + 3 = 12, acima do limite 10 da spec."""
    assert calculate_crap(cc=3, coverage=0.0) == 12.0
