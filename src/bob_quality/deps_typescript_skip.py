"""Ponto único da regra da #27 no gate deps.

A #27 ainda espera o OK do Emerson. Para reverter este comportamento:

1. Apagar este arquivo.
2. Apagar `tests/test_deps_typescript_skip.py`.
3. Em `run_deps_gate`, voltar a chamar `_typescript_violations` direto
   (sem `collect_typescript_deps` nem `note_typescript_skipped`).
   Um ToolError do TypeScript derruba o gate inteiro com exit 4.
"""

from __future__ import annotations

from collections.abc import Callable

from bob_quality.exit_codes import PASSED
from bob_quality.models import DepViolation, GateResult
from bob_quality.tools import ToolError


def collect_typescript_deps(
    *,
    enabled: bool,
    python_measured: bool,
    measure: Callable[[], list[DepViolation]],
    sink: list[DepViolation],
) -> str | None:
    """Mede o TypeScript. Sem Node, e com Python no repo, devolve o motivo do pulo."""
    if not enabled:
        return None
    try:
        sink.extend(measure())
    except ToolError as exc:
        if not python_measured or not str(exc).startswith("Node ausente"):
            raise
        return str(exc)
    return None


def note_typescript_skipped(
    result: GateResult,
    code: int,
    reason: str | None,
) -> tuple[GateResult, int]:
    """Aviso no veredito. Exit 1 continua 1; o passe vira aviso e não sai 4."""
    if not reason:
        return result, code
    note = f"TypeScript pulado: {reason}"
    if result.status == "failed":
        detail = f"{result.reason}; {note}" if result.reason else note
        return GateResult("deps", "failed", detail), code
    if code != PASSED:
        return result, code
    return GateResult("deps", "warn", note), code
