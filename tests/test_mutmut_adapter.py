"""Adaptador mutmut: saída bruta da versão pinada → Mutant.

Seam secundário da SPEC: o adaptador não importa mutmut; só lê o texto
gravado de `mutmut results --all true` e `mutmut show` (mutmut==3.8.0).
"""

from pathlib import Path

from bob_quality.adapters.mutmut import mutants_from_raw

RAW = Path(__file__).parent / "fixtures" / "raw"


def test_mutmut_adapter_reads_pinned_results_and_show() -> None:
    results = (RAW / "mutmut-results.txt").read_text()
    show = (RAW / "mutmut-show.txt").read_text()
    mutants = mutants_from_raw(
        results,
        {"app.weak.x_classify__mutmut_1": show},
    )
    by_id = {item.id: item for item in mutants}

    survivor = by_id["app.weak.x_classify__mutmut_1"]
    assert survivor.status == "survived"
    assert survivor.function == "classify"
    assert survivor.file == "src/app/weak.py"
    assert survivor.line == 2
    assert survivor.operator == "if n > 0: -> if n >= 0:"
    assert by_id["app.safe.x_add__mutmut_1"].status == "killed"
    assert by_id["app.safe.x_add__mutmut_1"].function == "add"
    assert sum(1 for item in mutants if item.status == "survived") == 3
