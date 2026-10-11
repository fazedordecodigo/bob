"""Adaptador c8/istanbul: `coverage-final.json` da versão pinada → modelo do núcleo."""

from __future__ import annotations

import json

from bob_quality.models import FileCoverage


class IstanbulParseError(Exception):
    """coverage-final.json fora do contrato da versão pinada do c8."""


def parse_coverage_final(raw: str) -> dict[str, FileCoverage]:
    """Recebe o JSON do reporter `json` do c8 e devolve cobertura por arquivo.

    A cobertura da função sai das linhas dos statements (`statementMap` + `s`)
    no intervalo que o lizard marca.
    """
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise IstanbulParseError("coverage-final.json inválido") from exc
    if not isinstance(payload, dict):
        raise IstanbulParseError("coverage-final.json deve ser um objeto de arquivos")
    parsed: dict[str, FileCoverage] = {}
    for path, data in payload.items():
        if not isinstance(data, dict) or not isinstance(data.get("statementMap"), dict):
            raise IstanbulParseError(f"entrada istanbul inválida para {path}")
        parsed[path] = _file_coverage(data)
    return parsed


def _file_coverage(data: dict) -> FileCoverage:
    counts = data.get("s") or {}
    if not isinstance(counts, dict):
        raise IstanbulParseError("mapa de statements `s` inválido")
    executed: set[int] = set()
    missing: set[int] = set()
    for key, loc in data["statementMap"].items():
        try:
            start = int(loc["start"]["line"])
            end = int(loc["end"]["line"])
            hits = int(counts.get(key, 0))
        except (KeyError, TypeError, ValueError) as exc:
            raise IstanbulParseError(f"statement inválido: {key}") from exc
        target = executed if hits > 0 else missing
        target.update(range(start, end + 1))
    missing -= executed
    return FileCoverage(
        executed_lines=frozenset(executed),
        missing_lines=frozenset(missing),
    )
