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
    """O id é `{arquivo}:{id do Stryker}` para não colidir quando o Stryker recomeça a contagem em cada arquivo."""
    files = _files(payload)
    mutants: list[Mutant] = []
    for report_file, file_entry in files.items():
        for raw in _mutant_rows(report_file, file_entry):
            status = _status(raw)
            if status is None:
                continue
            start, end = _location(report_file, raw)
            span = _innermost(str(report_file), start[0], spans)
            if span is None:
                continue
            mutants.append(
                Mutant(
                    id=f"{span.file}:{_raw_id(report_file, raw)}",
                    function=span.name,
                    file=span.file,
                    line=start[0],
                    operator=_operator(report_file, raw, start, end),
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


def _operator(
    report_file: str,
    raw: Mapping[str, object],
    start: tuple[int, int],
    end: tuple[int, int],
) -> str:
    """O relatório não traz diff.

    Sem o trecho, dois mutantes do mesmo mutador na mesma função teriam o mesmo alvo de waiver.
    """
    name = raw.get("mutatorName")
    if not isinstance(name, str) or not name:
        raise StrykerParseError(msg("stryker.bad_report", detail=report_file))
    described = f"{name}@{start[0]}:{start[1]}-{end[0]}:{end[1]}"
    replacement = raw.get("replacement")
    if isinstance(replacement, str):
        return f"{described} -> {replacement}"
    return described


def _location(
    report_file: str, raw: Mapping[str, object]
) -> tuple[tuple[int, int], tuple[int, int]]:
    location = raw.get("location")
    if not isinstance(location, Mapping):
        raise StrykerParseError(msg("stryker.bad_report", detail=report_file))
    return _position(report_file, location, "start"), _position(report_file, location, "end")


def _position(report_file: str, location: Mapping[str, object], key: str) -> tuple[int, int]:
    position = location.get(key)
    if not isinstance(position, Mapping):
        raise StrykerParseError(msg("stryker.bad_report", detail=report_file))
    return _counted(report_file, position.get("line")), _counted(report_file, position.get("column"))


def _counted(report_file: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise StrykerParseError(msg("stryker.bad_report", detail=report_file))
    return value


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
