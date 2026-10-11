"""Adaptador coverage.py: JSON da ferramenta pinada → modelo do núcleo."""

from __future__ import annotations

import json

from bob_quality.models import FileCoverage


class CoverageParseError(Exception):
    """JSON do coverage.py fora do contrato da versão pinada."""


def parse_coverage_json(raw: str) -> dict[str, FileCoverage]:
    """Recebe o conteúdo de `coverage json` e devolve cobertura por arquivo."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CoverageParseError("coverage.json inválido") from exc
    files = payload.get("files")
    if not isinstance(files, dict):
        raise CoverageParseError("coverage.json sem chave files")
    parsed: dict[str, FileCoverage] = {}
    for path, data in files.items():
        if not isinstance(data, dict):
            raise CoverageParseError(f"entrada inválida para {path}")
        parsed[path] = FileCoverage(
            executed_lines=frozenset(data.get("executed_lines") or []),
            missing_lines=frozenset(data.get("missing_lines") or []),
        )
    return parsed
