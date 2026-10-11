"""Adaptadores: entrada fora do contrato vira mensagem nos dois idiomas."""

from __future__ import annotations

import pytest

from bob_quality.adapters.coverage import CoverageParseError, parse_coverage_json
from bob_quality.adapters.istanbul import IstanbulParseError, parse_coverage_final
from bob_quality.adapters.jscpd import JscpdParseError, parse_jscpd_json
from bob_quality.adapters.lizard import LizardParseError, parse_lizard_csv
from helpers import in_both

_SIDE = '{"name": "a.py", "start": 1, "end": 2}'

CASES = [
    (
        parse_coverage_json,
        CoverageParseError,
        "{",
        "invalid coverage.json",
        "coverage.json inválido",
    ),
    (
        parse_coverage_json,
        CoverageParseError,
        "{}",
        "coverage.json without a files key",
        "coverage.json sem chave files",
    ),
    (
        parse_coverage_json,
        CoverageParseError,
        '{"files": {"a.py": []}}',
        "invalid entry for a.py",
        "entrada inválida para a.py",
    ),
    (
        parse_coverage_final,
        IstanbulParseError,
        "{",
        "invalid coverage-final.json",
        "coverage-final.json inválido",
    ),
    (
        parse_coverage_final,
        IstanbulParseError,
        "[]",
        "coverage-final.json must be an object of files",
        "coverage-final.json deve ser um objeto de arquivos",
    ),
    (
        parse_coverage_final,
        IstanbulParseError,
        '{"a.ts": {"s": {}}}',
        "invalid istanbul entry for a.ts",
        "entrada istanbul inválida para a.ts",
    ),
    (
        parse_coverage_final,
        IstanbulParseError,
        '{"a.ts": {"statementMap": {}, "s": [1]}}',
        "invalid statement map `s`",
        "mapa de statements `s` inválido",
    ),
    (
        parse_coverage_final,
        IstanbulParseError,
        '{"a.ts": {"statementMap": {"7": {"start": {}}}, "s": {}}}',
        "invalid statement: 7",
        "statement inválido: 7",
    ),
    (parse_jscpd_json, JscpdParseError, "{", "jscpd: invalid JSON", "jscpd: JSON inválido"),
    (
        parse_jscpd_json,
        JscpdParseError,
        '{"duplicates": {}}',
        "jscpd: JSON without the duplicates list",
        "jscpd: JSON sem a lista duplicates",
    ),
    (
        parse_jscpd_json,
        JscpdParseError,
        '{"duplicates": [1]}',
        "jscpd: malformed duplicate",
        "jscpd: duplicata fora do formato",
    ),
    (
        parse_jscpd_json,
        JscpdParseError,
        '{"duplicates": [{}]}',
        "jscpd: duplicate without firstFile",
        "jscpd: duplicata sem firstFile",
    ),
    (
        parse_jscpd_json,
        JscpdParseError,
        '{"duplicates": [{"firstFile": {"name": "", "start": 1, "end": 2}}]}',
        "jscpd: firstFile without name",
        "jscpd: firstFile sem name",
    ),
    (
        parse_jscpd_json,
        JscpdParseError,
        '{"duplicates": [{"firstFile": {"name": "a.py"}}]}',
        "jscpd: firstFile without lines",
        "jscpd: firstFile sem linhas",
    ),
    (
        parse_jscpd_json,
        JscpdParseError,
        f'{{"duplicates": [{{"firstFile": {_SIDE}, "secondFile": {_SIDE}}}]}}',
        "jscpd: duplicate without lines or tokens",
        "jscpd: duplicata sem lines ou tokens",
    ),
    (
        parse_jscpd_json,
        JscpdParseError,
        f'{{"duplicates": [{{"firstFile": {_SIDE}, "secondFile": {_SIDE},'
        ' "lines": 2, "tokens": 9, "similarity": "high"}]}',
        "jscpd: invalid similarity",
        "jscpd: similarity inválida",
    ),
    (
        parse_lizard_csv,
        LizardParseError,
        "a,b\n",
        "unexpected CSV row: ['a', 'b']",
        "linha CSV inesperada: ['a', 'b']",
    ),
    (
        parse_lizard_csv,
        LizardParseError,
        "1,x,3,4,5,6,f.py,g,g(),1,2\n",
        "invalid CSV row: ['1', 'x', '3', '4', '5', '6', 'f.py', 'g', 'g()', '1', '2']",
        "linha CSV inválida: ['1', 'x', '3', '4', '5', '6', 'f.py', 'g', 'g()', '1', '2']",
    ),
]


@pytest.mark.parametrize(("parse", "error", "raw", "english", "portuguese"), CASES)
def test_out_of_contract_input_explains_itself_in_both_languages(
    parse, error: type[Exception], raw: str, english: str, portuguese: str
) -> None:
    with pytest.raises(error) as caught:
        parse(raw)

    assert in_both(caught.value) == (english, portuguese)
