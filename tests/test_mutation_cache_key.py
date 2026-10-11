"""Chave do cache de mutação: função, testes que a cobrem e versão do mutmut.

Seams:

1. CLI `bob mutate` sobre o fixture Python e o cache `.bob/mutation-cache.json`.
2. Adaptador mutmut: o texto de `mutants/mutmut-stats.json` (mutmut==3.8.0)
   vira os arquivos de teste de cada função.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bob_quality.adapters.mutmut import MutmutParseError, covering_test_files, mutmut_stats_key
from bob_quality.mutmut_tool import mutmut_stats
from bob_quality.tools import ToolError

STATS = """\
{
    "tests_by_mangled_function_name": {
        "app.safe.x_add": [
            "tests/test_safe.py::test_add",
            "tests/test_param.py::test_add_param[1]",
            "tests/test_param.py::test_add_param[a::b]",
            "tests/test_box.py::TestBox::test_add"
        ],
        "app.safe.x_scale": []
    },
    "duration_by_test": {},
    "stats_time": 0.1
}
"""


def test_stats_key_is_the_mutant_prefix_without_the_mutmut_suffix() -> None:
    assert mutmut_stats_key("src/app/safe.py", "add") == "app.safe.x_add"
    assert mutmut_stats_key("pkg/mod.py", "fn") == "pkg.mod.x_fn"


def test_covering_test_files_keep_the_file_of_each_node_id() -> None:
    assert covering_test_files(STATS) == {
        "app.safe.x_add": {"tests/test_safe.py", "tests/test_param.py", "tests/test_box.py"},
        "app.safe.x_scale": set(),
    }


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("{", r"^stats do mutmut ilegível: Expecting property name"),
        ("[]", r"^stats do mutmut sem tests_by_mangled_function_name$"),
        ('{"duration_by_test": {}}', r"^stats do mutmut sem tests_by_mangled_function_name$"),
        (
            '{"tests_by_mangled_function_name": []}',
            r"^stats do mutmut sem tests_by_mangled_function_name$",
        ),
        (
            '{"tests_by_mangled_function_name": {"app.safe.x_add": "tests/test_safe.py"}}',
            r"^testes fora do contrato no stats do mutmut: 'tests/test_safe.py'$",
        ),
        (
            '{"tests_by_mangled_function_name": {"app.safe.x_add": ["tests/a.py::t", 1]}}',
            r"^testes fora do contrato no stats do mutmut: \['tests/a.py::t', 1\]$",
        ),
    ],
)
def test_stats_outside_the_pinned_shape_are_rejected(raw: str, message: str) -> None:
    with pytest.raises(MutmutParseError, match=message):
        covering_test_files(raw)


def test_mutmut_stats_reads_the_file_that_mutmut_run_writes(tmp_path: Path) -> None:
    (tmp_path / "mutants").mkdir()
    (tmp_path / "mutants" / "mutmut-stats.json").write_text(STATS)

    assert mutmut_stats(tmp_path) == STATS


def test_missing_mutmut_stats_is_a_tool_error(tmp_path: Path) -> None:
    with pytest.raises(ToolError) as caught:
        mutmut_stats(tmp_path)

    assert str(caught.value) == "stats do mutmut ausente: mutants/mutmut-stats.json"
