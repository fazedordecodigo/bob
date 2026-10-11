"""Adaptador coverage.py: JSON da ferramenta pinada → cobertura por linha."""

from __future__ import annotations

import json
from typing import Any


class CoverageParseError(Exception):
    """JSON do coverage.py fora do contrato da versão pinada."""


def parse_coverage_json(raw: str) -> dict[str, dict[str, Any]]:
    """Recebe o conteúdo de `coverage json` e devolve o mapa `files`."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CoverageParseError("coverage.json inválido") from exc
    files = payload.get("files")
    if not isinstance(files, dict):
        raise CoverageParseError("coverage.json sem chave files")
    return files


def function_coverage(file_data: dict[str, Any], start_line: int, end_line: int) -> float:
    """Cobertura de linhas executáveis no intervalo da função, fração [0, 1]."""
    executed = set(file_data.get("executed_lines") or [])
    missing = set(file_data.get("missing_lines") or [])
    statements = {
        line for line in executed | missing if start_line <= line <= end_line
    }
    if not statements:
        return 1.0
    covered = statements & executed
    return len(covered) / len(statements)
