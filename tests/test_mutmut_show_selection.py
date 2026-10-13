"""O show só preenche o diff. O status, e portanto o veredito, sai do results."""

from __future__ import annotations

from pathlib import Path

import bob_quality.mutate as mutate_module
from bob_quality.adapters.mutmut import MutmutParseError, mutants_from_raw
from bob_quality.models import CyclomaticFunction, GateResult
from bob_quality.mutate import _cached_start, _mutants_from_cache, _run_and_parse
from bob_quality.tools import ToolError

VERSIONS = {"mutmut": "3.8.0"}
WAIVERS = [{"id": "keep-me", "reason": "porque"}]

RESULTS = """\
    app.weak.x_classify__mutmut_1: survived
    app.weak.x_classify__mutmut_2: killed
    app.weak.x_classify__mutmut_3: timeout
    app.weak.x_classify__mutmut_4: no tests
"""

SHOW = """\
--- src/app/weak.py
+++ src/app/weak.py
@@ -2 +2 @@
-old
+new
"""


def _changed() -> list[CyclomaticFunction]:
    return [
        CyclomaticFunction(
            file="src/app/weak.py", name="classify", start_line=1, end_line=4, cc=1
        ),
        CyclomaticFunction(file="src/app/safe.py", name="add", start_line=1, end_line=3, cc=1),
    ]


def test_show_runs_only_for_survivors_and_timeouts(monkeypatch, tmp_path: Path) -> None:
    shown: list[tuple[Path, str]] = []
    calls: dict[str, object] = {}

    def fake_run(cwd: Path, patterns: list[str], max_workers: int | None) -> None:
        calls["run"] = (cwd, list(patterns), max_workers)

    def fake_results(cwd: Path) -> str:
        calls["results"] = cwd
        return RESULTS

    def fake_show(cwd: Path, mutant_id: str) -> str:
        shown.append((cwd, mutant_id))
        return SHOW

    monkeypatch.setattr(mutate_module, "run_mutmut", fake_run)
    monkeypatch.setattr(mutate_module, "mutmut_results", fake_results)
    monkeypatch.setattr(mutate_module, "mutmut_show", fake_show)

    parsed, failed = _run_and_parse(tmp_path, _changed(), 2, VERSIONS, WAIVERS)

    assert failed is None
    assert calls["run"] == (
        tmp_path,
        [
            "app.weak.x_classify__mutmut*",
            "*app.weak.x_classify",
            "app.safe.x_add__mutmut*",
            "*app.safe.x_add",
        ],
        2,
    )
    assert calls["results"] == tmp_path
    assert shown == [
        (tmp_path, "app.weak.x_classify__mutmut_1"),
        (tmp_path, "app.weak.x_classify__mutmut_3"),
    ]
    by_id = {item.id: item for item in parsed}
    assert by_id["app.weak.x_classify__mutmut_1"].status == "survived"
    assert by_id["app.weak.x_classify__mutmut_1"].operator == "old -> new"
    assert by_id["app.weak.x_classify__mutmut_2"].status == "killed"
    assert by_id["app.weak.x_classify__mutmut_2"].operator == ""
    assert by_id["app.weak.x_classify__mutmut_3"].status == "timeout"
    assert by_id["app.weak.x_classify__mutmut_3"].operator == "old -> new"
    assert by_id["app.weak.x_classify__mutmut_4"].status == "no_coverage"
    assert by_id["app.weak.x_classify__mutmut_4"].operator == ""


SHOW_FAR_FROM_TOP = """\
--- src/bob_quality/mutate.py
+++ src/bob_quality/mutate.py
@@ -4,7 +4,7 @@
     if not source.is_dir():
         return
     dest_root = cwd / "mutants"
-    dest_root.mkdir(parents=True, exist_ok=True)
+    dest_root.mkdir(parents=None, exist_ok=True)
     dest = dest_root / "node_modules"
     if dest.is_symlink() or dest.exists():
         return
"""


def test_show_line_is_the_file_line_when_the_function_is_not_at_the_top(
    monkeypatch, tmp_path: Path
) -> None:
    """O mutmut 3.8 numera o diff a partir da função. O mkdir está na linha 7 do trecho e na 480 do arquivo."""

    def fake_show(_cwd: Path, _mutant_id: str) -> str:
        return SHOW_FAR_FROM_TOP

    monkeypatch.setattr(mutate_module, "run_mutmut", lambda *_args: None)
    monkeypatch.setattr(
        mutate_module,
        "mutmut_results",
        lambda _cwd: "    bob_quality.mutate.x_prepare_mutmut_workspace__mutmut_10: survived\n",
    )
    monkeypatch.setattr(mutate_module, "mutmut_show", fake_show)
    remutate = [
        CyclomaticFunction(
            file="src/bob_quality/mutate.py",
            name="prepare_mutmut_workspace",
            start_line=474,
            end_line=484,
            cc=2,
        )
    ]

    parsed, failed = _run_and_parse(tmp_path, remutate, 1, VERSIONS, WAIVERS)

    assert failed is None
    assert parsed[0].line == 480


SHOW_DECORATED = """\
# app.box.xǁBoxǁmake__mutmut_1: survived
--- src/app/box.py
+++ src/app/box.py
@@ -1,3 +1,3 @@
 @staticmethod
 def make(n: int) -> int:
-    return n * 2
+    return n / 2
"""


def test_a_decorated_method_counts_its_lines_from_the_decorator(
    monkeypatch, tmp_path: Path
) -> None:
    """O `mutmut show` 3.8 de um método decorado começa no decorador da linha 9."""
    monkeypatch.setattr(mutate_module, "run_mutmut", lambda *_args: None)
    monkeypatch.setattr(
        mutate_module,
        "mutmut_results",
        lambda _cwd: "    app.box.xǁBoxǁmake__mutmut_1: survived\n",
    )
    monkeypatch.setattr(mutate_module, "mutmut_show", lambda _cwd, _id: SHOW_DECORATED)
    make = CyclomaticFunction(
        file="src/app/box.py", name="Box.make", start_line=9, end_line=11, cc=1
    )

    parsed, failed = _run_and_parse(tmp_path, [make], 1, VERSIONS, WAIVERS)

    assert failed is None
    assert [(item.function, item.file, item.line, item.operator) for item in parsed] == [
        ("Box.make", "src/app/box.py", 11, "return n * 2 -> return n / 2")
    ]


def test_a_function_relative_line_of_one_lands_on_the_function_start(
    monkeypatch, tmp_path: Path
) -> None:
    show = "\n".join(
        [
            "--- src/app/far.py",
            "+++ src/app/far.py",
            "@@ -1 +1 @@",
            "-old",
            "+new",
        ]
    )
    monkeypatch.setattr(mutate_module, "run_mutmut", lambda *_args: None)
    monkeypatch.setattr(
        mutate_module,
        "mutmut_results",
        lambda _cwd: "    app.far.x_place__mutmut_1: survived\n",
    )
    monkeypatch.setattr(mutate_module, "mutmut_show", lambda _cwd, _mutant_id: show)
    remutate = [
        CyclomaticFunction(file="src/app/far.py", name="place", start_line=474, end_line=480, cc=1)
    ]

    parsed, failed = _run_and_parse(tmp_path, remutate, 1, VERSIONS, WAIVERS)

    assert failed is None
    assert parsed[0].line == 474


def test_a_show_without_an_added_line_keeps_line_zero(monkeypatch, tmp_path: Path) -> None:
    show = "\n".join(
        [
            "--- src/app/far.py",
            "+++ src/app/far.py",
            "@@ -5 +4,0 @@",
            "-only",
        ]
    )
    monkeypatch.setattr(mutate_module, "run_mutmut", lambda *_args: None)
    monkeypatch.setattr(
        mutate_module,
        "mutmut_results",
        lambda _cwd: "    app.far.x_place__mutmut_1: survived\n",
    )
    monkeypatch.setattr(mutate_module, "mutmut_show", lambda _cwd, _mutant_id: show)
    remutate = [
        CyclomaticFunction(file="src/app/far.py", name="place", start_line=474, end_line=480, cc=1)
    ]

    parsed, failed = _run_and_parse(tmp_path, remutate, 1, VERSIONS, WAIVERS)

    assert failed is None
    assert parsed[0].line == 0


def test_a_cached_function_relative_line_becomes_the_file_line() -> None:
    kept = {
        "id": "bob_quality.mutate.x_prepare_mutmut_workspace__mutmut_10",
        "function": "prepare_mutmut_workspace",
        "file": "src/bob_quality/mutate.py",
        "line": 7,
        "operator": "a -> b",
        "status": "survived",
        "waiver": "porque",
    }
    skipped_noise = {"line": 1}
    blank_line = {
        "id": "bob_quality.mutate.x_prepare_mutmut_workspace__mutmut_11",
        "function": "prepare_mutmut_workspace",
        "file": "src/bob_quality/mutate.py",
        "line": 0,
        "operator": "",
        "status": "killed",
        "waiver": "",
    }
    first_line = {
        "id": "bob_quality.mutate.x_prepare_mutmut_workspace__mutmut_12",
        "function": "prepare_mutmut_workspace",
        "file": "src/bob_quality/mutate.py",
        "line": 1,
        "operator": "old -> new",
        "status": "timeout",
    }
    missing_fields = {
        "id": "bob_quality.mutate.x_prepare_mutmut_workspace__mutmut_15",
        "line": 3,
        "status": "killed",
    }
    zero_start = {
        "id": "bob_quality.mutate.x_prepare_mutmut_workspace__mutmut_13",
        "function": "prepare_mutmut_workspace",
        "file": "src/bob_quality/mutate.py",
        "line": 7,
        "operator": "a -> b",
        "status": "killed",
    }
    text_start = {
        "id": "bob_quality.mutate.x_prepare_mutmut_workspace__mutmut_14",
        "function": "prepare_mutmut_workspace",
        "file": "src/bob_quality/mutate.py",
        "line": 7,
        "operator": "a -> b",
        "status": "killed",
    }
    place = CyclomaticFunction(
        file="src/bob_quality/mutate.py",
        name="prepare_mutmut_workspace",
        start_line=474,
        end_line=484,
        cc=2,
    )
    mutants = _mutants_from_cache(
        [
            ("noise", {"start_line": 10, "mutants": "não é lista"}),
            (
                "src/bob_quality/mutate.py::prepare_mutmut_workspace",
                {
                    "start_line": 10,
                    "mutants": [kept, skipped_noise, blank_line, first_line, missing_fields],
                },
            ),
            ("zero", {"start_line": 0, "mutants": [zero_start]}),
            ("text", {"start_line": "474", "mutants": [text_start]}),
        ],
        {"src/bob_quality/mutate.py::prepare_mutmut_workspace": place},
    )

    assert [(item.id, item.line) for item in mutants] == [
        (kept["id"], 480),
        (blank_line["id"], 0),
        (first_line["id"], 474),
        (missing_fields["id"], 476),
        (zero_start["id"], 7),
        (text_start["id"], 7),
    ]
    assert mutants[3].function == ""
    assert mutants[3].file == ""
    assert mutants[3].operator == ""
    assert mutants[3].status == "killed"
    assert mutants[1].status == "killed"
    assert mutants[2].status == "timeout"
    shifted = mutants[0]
    assert shifted.function == "prepare_mutmut_workspace"
    assert shifted.file == "src/bob_quality/mutate.py"
    assert shifted.operator == "a -> b"
    assert shifted.status == "survived"
    assert shifted.waiver == "porque"
    assert mutants[1].waiver is None


def test_a_cached_file_line_is_not_shifted_again() -> None:
    entry = {
        "start_line": 474,
        "line_base": "file",
        "mutants": [
            {
                "id": "bob_quality.mutate.x_prepare_mutmut_workspace__mutmut_10",
                "function": "prepare_mutmut_workspace",
                "file": "src/bob_quality/mutate.py",
                "line": 480,
                "operator": "a -> b",
                "status": "survived",
                "waiver": "porque",
            }
        ],
    }

    mutants = _mutants_from_cache([("src/bob_quality/mutate.py::prepare_mutmut_workspace", entry)])

    assert _cached_start({"start_line": 1}) == 1
    assert _cached_start({"start_line": 0}) is None
    assert _cached_start({"line_base": "file", "start_line": 474}) is None
    already_file = {
        "id": "bob_quality.mutate.x_prepare_mutmut_workspace__mutmut_16",
        "function": "prepare_mutmut_workspace",
        "file": "src/bob_quality/mutate.py",
        "line": 40,
        "operator": "a -> b",
        "status": "killed",
    }
    at_top = {
        "id": "bob_quality.mutate.x_prepare_mutmut_workspace__mutmut_17",
        "function": "prepare_mutmut_workspace",
        "file": "src/bob_quality/mutate.py",
        "line": 4,
        "operator": "a -> b",
        "status": "killed",
    }
    no_live_start = {
        "id": "bob_quality.mutate.x_prepare_mutmut_workspace__mutmut_18",
        "function": "prepare_mutmut_workspace",
        "file": "src/bob_quality/mutate.py",
        "line": 7,
        "operator": "a -> b",
        "status": "killed",
    }
    file_rows = _mutants_from_cache(
        [("kept", {"line_base": "file", "start_line": 100, "mutants": [already_file]})],
        {
            "kept": CyclomaticFunction(
                file="src/bob_quality/mutate.py",
                name="prepare_mutmut_workspace",
                start_line=474,
                end_line=484,
                cc=1,
            )
        },
    )
    top_rows = _mutants_from_cache(
        [("top", {"start_line": 100, "mutants": [at_top]})],
        {
            "top": CyclomaticFunction(
                file="src/app/far.py",
                name="place",
                start_line=1,
                end_line=8,
                cc=1,
            )
        },
    )
    zero_rows = _mutants_from_cache(
        [("zero-live", {"mutants": [no_live_start]})],
        {
            "zero-live": CyclomaticFunction(
                file="src/app/far.py",
                name="place",
                start_line=0,
                end_line=8,
                cc=1,
            )
        },
    )
    assert file_rows[0].line == 40
    assert top_rows[0].line == 4
    assert zero_rows[0].line == 7
    assert mutants[0].line == 480
    assert mutants[0].waiver == "porque"
    assert mutants[0].operator == "a -> b"
    assert mutants[0].status == "survived"


def test_a_tool_failure_keeps_the_message_and_the_waivers(monkeypatch, tmp_path: Path) -> None:
    def boom(_cwd: Path, _patterns: list[str], _max_workers: int | None) -> None:
        raise ToolError("tool broke")

    monkeypatch.setattr(mutate_module, "run_mutmut", boom)

    parsed, failed = _run_and_parse(tmp_path, _changed(), 2, VERSIONS, WAIVERS)

    assert parsed == []
    assert failed is not None
    assert failed.result == GateResult("mutate", "not_run", "tool broke")
    assert failed.exit_code == 4
    assert failed.versions == VERSIONS
    assert failed.waivers == WAIVERS


def test_a_bad_diff_keeps_the_message_and_the_waivers(monkeypatch, tmp_path: Path) -> None:
    seen = {"n": 0}

    def fake_parse(raw: str, shows: dict[str, str]):
        seen["n"] += 1
        if seen["n"] == 2:
            raise MutmutParseError("diff ilegível")
        return mutants_from_raw(raw, shows)

    monkeypatch.setattr(mutate_module, "run_mutmut", lambda *_args: None)
    monkeypatch.setattr(mutate_module, "mutmut_results", lambda _cwd: RESULTS)
    monkeypatch.setattr(mutate_module, "mutmut_show", lambda _cwd, _mutant_id: SHOW)
    monkeypatch.setattr(mutate_module, "mutants_from_raw", fake_parse)

    parsed, failed = _run_and_parse(tmp_path, _changed(), 2, VERSIONS, WAIVERS)

    assert parsed == []
    assert failed is not None
    assert failed.result == GateResult("mutate", "not_run", "diff ilegível")
    assert failed.exit_code == 4
    assert failed.versions == VERSIONS
    assert failed.waivers == WAIVERS
