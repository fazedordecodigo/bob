from __future__ import annotations

from pathlib import Path

import pytest

from bob_quality.adapters.vulture import VultureParseError, python_symbols
from bob_quality.messages import reason, render
from bob_quality.models import PythonDead

_REPORT = """\
src/app/orphan.py:3: unused function 'orphan' (60% confidence, 3 lines)
src/app/flow.py:4: unreachable code after 'return' (100% confidence, 1 line)
src/app/flow.py:9: unreachable 'else' block (100% confidence)
src/app/flow.py:11: redundant if-condition (100% confidence, 1 line)
src/app/flow.py:13: unsatisfiable 'if' condition (100% confidence)

./src/app/widget.py:2: unused class 'Widget' (90% confidence)
"""


def test_vulture_lines_become_symbols(tmp_path: Path) -> None:
    found = python_symbols(_REPORT, tmp_path)

    assert found == (
        PythonDead("src/app/orphan.py", 3, "orphan", "function", 60),
        PythonDead("src/app/flow.py", 4, "return", "unreachable_code", 100),
        PythonDead("src/app/flow.py", 9, "else", "unreachable_code", 100),
        PythonDead("src/app/flow.py", 11, "if", "unreachable_code", 100),
        PythonDead("src/app/flow.py", 13, "if", "unreachable_code", 100),
        PythonDead("src/app/widget.py", 2, "Widget", "class", 90),
    )


def test_each_unused_kind_keeps_its_name_and_confidence(tmp_path: Path) -> None:
    raw = "\n".join(
        [
            "src/kinds.py:1: unused attribute 'field' (60% confidence)",
            "src/kinds.py:2: unused class 'Box' (61% confidence)",
            "src/kinds.py:3: unused function 'run' (62% confidence)",
            "src/kinds.py:4: unused import 'os' (0% confidence)",
            "src/kinds.py:5: unused method 'save' (64% confidence)",
            "src/kinds.py:6: unused property 'ready' (65% confidence)",
            "src/kinds.py:7: unused variable 'cached' (66% confidence)",
            "src/kinds.py:8: unreachable 'else' expression (100% confidence)",
            "src/kinds.py:9: unsatisfiable 'while' condition (100% confidence)",
            "",
        ]
    )

    assert python_symbols(raw, tmp_path) == (
        PythonDead("src/kinds.py", 1, "field", "attribute", 60),
        PythonDead("src/kinds.py", 2, "Box", "class", 61),
        PythonDead("src/kinds.py", 3, "run", "function", 62),
        PythonDead("src/kinds.py", 4, "os", "import", 0),
        PythonDead("src/kinds.py", 5, "save", "method", 64),
        PythonDead("src/kinds.py", 6, "ready", "property", 65),
        PythonDead("src/kinds.py", 7, "cached", "variable", 66),
        PythonDead("src/kinds.py", 8, "else", "unreachable_code", 100),
        PythonDead("src/kinds.py", 9, "while", "unreachable_code", 100),
    )


def test_an_absolute_path_inside_the_repo_is_relative_and_outside_is_omitted(
    tmp_path: Path,
) -> None:
    inside = tmp_path / "src" / "in.py"
    raw = (
        f"{inside}:1: unused variable 'n' (70% confidence)\n"
        "/etc/passwd:1: unused function 'x' (60% confidence)\n"
        "../outside.py:2: unused function 'y' (60% confidence)\n"
    )

    assert python_symbols(raw, tmp_path) == (
        PythonDead("src/in.py", 1, "n", "variable", 70),
    )


def test_a_bad_line_or_confidence_rejects_the_whole_report(tmp_path: Path) -> None:
    samples = (
        "src/app/orphan.py:3: unused function 'orphan' (60% confidence)\nnope\n",
        "src/app/orphan.py:3: unused function 'orphan' (101% confidence)\n",
        "src/app/orphan.py:3: unused function 'orphan' (60% confidence) extra\n",
    )

    for raw in samples:
        with pytest.raises(VultureParseError) as caught:
            python_symbols(raw, tmp_path)
        assert render(reason(caught.value), "en") == "vulture: output could not be parsed"
        assert render(reason(caught.value), "pt-BR") == "vulture: saída ilegível"


def test_whitespace_only_stdout_has_no_symbols(tmp_path: Path) -> None:
    assert python_symbols("", tmp_path) == ()
    assert python_symbols("\n\n  \n", tmp_path) == ()
