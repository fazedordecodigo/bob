"""Adaptador mutmut: saída bruta da versão pinada → Mutant.

Seam secundário da SPEC: o adaptador não importa mutmut; só lê o texto
gravado de `mutmut results --all true` e `mutmut show` (mutmut==3.8.0).
"""

from pathlib import Path

import pytest

from bob_quality.adapters.mutmut import MutmutParseError, mutants_from_raw
from helpers import in_both

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
    assert by_id["app.safe.x_add__mutmut_1"].file == ""
    assert by_id["app.safe.x_add__mutmut_1"].line == 0
    assert by_id["app.safe.x_add__mutmut_1"].operator == ""
    assert sum(1 for item in mutants if item.status == "survived") == 3


def test_results_keep_later_mutants_after_noise_and_non_mutant_rows() -> None:
    raw = "\n".join(
        [
            "header",
            "    plain: killed",
            "    app.weak.x_classify__mutmut_1: survived",
        ]
    )

    mutants = mutants_from_raw(raw, {})

    assert [item.id for item in mutants] == ["app.weak.x_classify__mutmut_1"]
    assert mutants[0].status == "survived"


def test_unknown_status_names_the_label() -> None:
    raw = "    app.weak.x_classify__mutmut_1: exploded\n"

    with pytest.raises(MutmutParseError) as caught:
        mutants_from_raw(raw, {})

    assert in_both(caught.value) == (
        "unknown mutmut status: 'exploded'",
        "status desconhecido do mutmut: 'exploded'",
    )


def test_mutant_id_without_the_pinned_shape_is_rejected() -> None:
    raw = "    not_a_mutant_id__mutmut_1: killed\n"

    with pytest.raises(MutmutParseError) as caught:
        mutants_from_raw(raw, {})

    assert in_both(caught.value) == (
        "mutant id outside the contract: not_a_mutant_id__mutmut_1",
        "id de mutante fora do contrato: not_a_mutant_id__mutmut_1",
    )


def test_method_mutant_id_uses_the_method_name() -> None:
    raw = "    pkg.xǁBoxǁopen__mutmut_1: killed\n"

    mutants = mutants_from_raw(raw, {})

    assert mutants[0].function == "open"


def test_show_reads_a_column_zero_edit_and_a_backslash_line() -> None:
    show = "\n".join(
        [
            "--- src/app/weak.py",
            "+++ src/app/weak.py",
            "@@ -1,3 +2,3 @@",
            " unchanged",
            "\\ No newline at end of file",
            "-return 1",
            "+return 2",
        ]
    )

    mutant = mutants_from_raw(
        "    app.weak.x_classify__mutmut_1: survived\n",
        {"app.weak.x_classify__mutmut_1": show},
    )[0]

    assert mutant.file == "src/app/weak.py"
    assert mutant.line == 3
    assert mutant.operator == "return 1 -> return 2"


def test_show_joins_every_changed_line_and_skips_the_next_file_header() -> None:
    show = "\n".join(
        [
            "--- src/app/a.py",
            "+++ src/app/a.py",
            "@@ -1,2 +1,2 @@",
            "-left",
            "-right",
            "+one",
            "+two",
            "--- src/app/b.py",
            "+++ src/app/b.py",
            "@@ -1 +1 @@",
            "-keep",
            "+keep2",
        ]
    )

    mutant = mutants_from_raw(
        "    app.a.x_touch__mutmut_1: survived\n",
        {"app.a.x_touch__mutmut_1": show},
    )[0]

    assert mutant.file == "src/app/b.py"
    assert mutant.operator == "left ; right ; keep -> one ; two ; keep2"


def test_show_without_an_edit_has_an_empty_operator() -> None:
    show = "\n".join(
        [
            "--- src/app/weak.py",
            "+++ src/app/weak.py",
            "@@ -1 +1 @@",
            " unchanged",
        ]
    )

    mutant = mutants_from_raw(
        "    app.weak.x_classify__mutmut_1: killed\n",
        {"app.weak.x_classify__mutmut_1": show},
    )[0]

    assert mutant.operator == ""


def test_deletion_only_show_keeps_the_removed_line() -> None:
    show = "\n".join(
        [
            "--- src/app/weak.py",
            "+++ src/app/weak.py",
            "@@ -2 +2 @@",
            "-only",
        ]
    )

    mutant = mutants_from_raw(
        "    app.weak.x_classify__mutmut_1: survived\n",
        {"app.weak.x_classify__mutmut_1": show},
    )[0]

    assert mutant.operator == "only -> "
