"""Adaptador Stryker: relatório JSON da versão pinada → Mutant.

Não importa o Stryker. O contrato é o mutation-testing-report-schema
que `@stryker-mutator/core` 10.0.0 grava no reporter json.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from bob_quality.messages import msg
from bob_quality.models import CyclomaticFunction, Mutant, MutantStatus

_STATUS: dict[str, MutantStatus] = {
    "Killed": "killed",
    "Survived": "survived",
    "NoCoverage": "no_coverage",
    "Timeout": "timeout",
    "RuntimeError": "killed",
    "CompileError": "killed",
}
_IGNORED = "Ignored"


class StrykerParseError(Exception):
    """Relatório JSON fora do contrato da versão pinada."""


def mutants_from_report(
    payload: Mapping[str, object],
    spans: Sequence[CyclomaticFunction],
) -> list[Mutant]:
    """Mapeia o status antes do filtro de span.

    Um status desconhecido num arquivo fora do diff ainda é exit 4.
    `Ignored` some. O id é `{arquivo}:{id do Stryker}` para não colidir
    quando o Stryker recomeça a contagem em cada arquivo.
    """
    files = _files(payload)
    mutants: list[Mutant] = []
    for report_file, file_entry in files.items():
        for raw in _mutant_rows(report_file, file_entry):
            status = _status(raw)
            if status is None:
                continue
            line = _line(report_file, raw)
            span = _innermost(str(report_file), line, spans)
            if span is None:
                continue
            mutants.append(
                Mutant(
                    id=f"{span.file}:{_raw_id(report_file, raw)}",
                    function=span.name,
                    file=span.file,
                    line=line,
                    operator=_operator(report_file, raw),
                    status=status,
                )
            )
    return mutants


def _files(payload: Mapping[str, object]) -> Mapping[str, object]:
    files = payload.get("files")
    if not isinstance(files, Mapping):
        raise StrykerParseError(msg("stryker.bad_report", detail="files"))
    return files


def _mutant_rows(report_file: str, file_entry: object) -> list[Mapping[str, object]]:
    if not isinstance(file_entry, Mapping):
        raise StrykerParseError(msg("stryker.bad_report", detail=report_file))
    rows = file_entry.get("mutants")
    if not isinstance(rows, list):
        raise StrykerParseError(msg("stryker.bad_report", detail=report_file))
    parsed: list[Mapping[str, object]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise StrykerParseError(msg("stryker.bad_report", detail=report_file))
        parsed.append(row)
    return parsed


def _status(raw: Mapping[str, object]) -> MutantStatus | None:
    label = raw.get("status")
    if label == _IGNORED:
        return None
    if not isinstance(label, str) or label not in _STATUS:
        shown = label if isinstance(label, str) else repr(label)
        raise StrykerParseError(msg("stryker.unknown_status", label=shown))
    return _STATUS[label]


def _raw_id(report_file: str, raw: Mapping[str, object]) -> str:
    mutant_id = raw.get("id")
    if isinstance(mutant_id, bool) or not isinstance(mutant_id, (str, int)):
        raise StrykerParseError(msg("stryker.bad_report", detail=report_file))
    return str(mutant_id)


def _operator(report_file: str, raw: Mapping[str, object]) -> str:
    name = raw.get("mutatorName")
    if not isinstance(name, str) or not name:
        raise StrykerParseError(msg("stryker.bad_report", detail=report_file))
    return name


def _line(report_file: str, raw: Mapping[str, object]) -> int:
    location = raw.get("location")
    if not isinstance(location, Mapping):
        raise StrykerParseError(msg("stryker.bad_report", detail=report_file))
    start = location.get("start")
    if not isinstance(start, Mapping):
        raise StrykerParseError(msg("stryker.bad_report", detail=report_file))
    line = start.get("line")
    if isinstance(line, bool) or not isinstance(line, int) or line < 1:
        raise StrykerParseError(msg("stryker.bad_report", detail=report_file))
    return line


def _innermost(
    report_file: str,
    line: int,
    spans: Sequence[CyclomaticFunction],
) -> CyclomaticFunction | None:
    containing = [
        span
        for span in spans
        if _same_file(span.file, report_file) and span.start_line <= line <= span.end_line
    ]
    if not containing:
        return None
    return min(
        containing,
        key=lambda span: (span.end_line - span.start_line, -len(span.file), -span.start_line, span.name),
    )


def _same_file(span_file: str, report_file: str) -> bool:
    span = span_file.replace("\\", "/").lstrip("./")
    report = report_file.replace("\\", "/")
    return report == span or report.endswith("/" + span)
