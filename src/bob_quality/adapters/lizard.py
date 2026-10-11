"""Adaptador lizard: CSV da ferramenta pinada → modelo do núcleo."""

from __future__ import annotations

import csv
import io

from bob_quality.models import CyclomaticFunction


class LizardParseError(Exception):
    """CSV do lizard fora do contrato da versão pinada."""


def parse_lizard_csv(raw: str) -> list[CyclomaticFunction]:
    """Recebe o stdout de `lizard --csv` (versão pinada) e devolve o modelo."""
    functions: list[CyclomaticFunction] = []
    reader = csv.reader(io.StringIO(raw))
    for row in reader:
        if not row or row[0].strip().lower() == "nloc":
            continue
        if len(row) < 11:
            raise LizardParseError(f"linha CSV inesperada: {row!r}")
        try:
            functions.append(
                CyclomaticFunction(
                    file=row[6],
                    name=row[7],
                    start_line=int(row[9]),
                    end_line=int(row[10]),
                    cc=int(row[1]),
                )
            )
        except (TypeError, ValueError) as exc:
            raise LizardParseError(f"linha CSV inválida: {row!r}") from exc
    return functions
