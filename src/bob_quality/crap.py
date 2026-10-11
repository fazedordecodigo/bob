"""Fórmula CRAP do núcleo: CC² × (1 − cov)³ + CC."""


def calculate_crap(cc: int, coverage: float) -> float:
    """Calcula o CRAP de uma função. `coverage` é fração em [0, 1]."""
    uncovered = 1.0 - coverage
    return (cc**2) * (uncovered**3) + cc
