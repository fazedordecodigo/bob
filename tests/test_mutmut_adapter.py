"""Adaptador mutmut: saída bruta da versão pinada → Mutant.

Seam secundário da SPEC: o adaptador não importa mutmut; só lê o texto
gravado de `mutmut results --all true` e `mutmut show` (mutmut==3.8.0).
"""

from pathlib import Path

import pytest

from bob_quality.adapters.lizard import parse_lizard_csv
from bob_quality.adapters.mutmut import MutmutParseError, mutants_from_raw, mutation_targets
from bob_quality.models import CyclomaticFunction, MutationTarget
from helpers import in_both

RAW = Path(__file__).parent / "fixtures" / "raw"
# box.py e o CSV que o lizard 1.24.1 gravou para ele. O mutmut 3.8 só gera
# mutantes para `open`, `make` e `helped` de `Box`, e para `outer` e `build`.
BOX = (RAW / "box.py").read_text()
BOX_ROWS = parse_lizard_csv((RAW / "lizard-box.csv").read_text())


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

    assert mutants[0].function == "Box.open"


def test_mutation_targets_name_each_def_in_a_class_body_by_its_class() -> None:
    targets = mutation_targets(BOX_ROWS, {"src/app/box.py": BOX})

    assert targets == [
        MutationTarget("src/app/box.py", "open", 1, 2),
        MutationTarget("src/app/box.py", "open", 6, 7, owner="Box"),
        MutationTarget("src/app/box.py", "make", 9, 11, owner="Box"),
        MutationTarget("src/app/box.py", "open", 14, 15, owner="Box.Inner"),
        MutationTarget("src/app/box.py", "helped.helper", 18, 19),
        MutationTarget("src/app/box.py", "helped", 17, 21, owner="Box"),
        MutationTarget("src/app/box.py", "maybe", 24, 25, owner="Box.nested"),
        MutationTarget("src/app/box.py", "size", 27, 29, owner="Box"),
        MutationTarget("src/app/box.py", "outer.inner", 33, 34),
        MutationTarget("src/app/box.py", "outer", 32, 36),
        MutationTarget("src/app/box.py", "open", 42, 43, owner="nested.Late"),
        MutationTarget("src/app/box.py", "build.open", 48, 49),
        MutationTarget("src/app/box.py", "build", 46, 51),
    ]
    assert [item.key() for item in targets[:4]] == [
        "src/app/box.py::open",
        "src/app/box.py::Box.open",
        "src/app/box.py::Box.make",
        "src/app/box.py::Box.Inner.open",
    ]


def test_a_bare_name_inside_a_class_that_matches_no_def_is_rejected() -> None:
    row = CyclomaticFunction("src/app/box.py", "open", 7, 7, 1)

    with pytest.raises(MutmutParseError) as caught:
        mutation_targets([row], {"src/app/box.py": BOX})

    assert in_both(caught.value) == (
        "lizard function open at src/app/box.py:7 is inside a class and matches no def",
        "a função open do lizard em src/app/box.py:7 está dentro de uma classe"
        " e não casa com nenhum def",
    )
    assert mutation_targets([row], {"src/app/box.py": "class Box:\n    pass\n"}) == [
        MutationTarget("src/app/box.py", "open", 7, 7)
    ]


def test_a_source_that_ast_cannot_read_names_the_file_and_line() -> None:
    row = CyclomaticFunction("src/app/bad.py", "f", 1, 2, 1)

    with pytest.raises(MutmutParseError) as caught:
        mutation_targets([row], {"src/app/bad.py": "def f(\n"})

    assert in_both(caught.value) == (
        "cannot parse src/app/bad.py:1: '(' was never closed",
        "não foi possível analisar src/app/bad.py:1: '(' was never closed",
    )


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
