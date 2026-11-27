from __future__ import annotations

import json
from pathlib import Path

import pytest

import bob_quality.mutate as mutate
from bob_quality.check import run_check
from helpers import commit_on_branch, commit_on_main, init_python_repo, run_bob

_FILE = "src/app/scope.py"
_FUTURE = "from __future__ import annotations\n"


@pytest.fixture
def scope_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = init_python_repo(tmp_path / "repo")
    monkeypatch.setattr(mutate, "mutmut_version", lambda: "3.8.0")
    monkeypatch.setattr(mutate, "pytest_exit_code", lambda _cwd: 0)
    monkeypatch.setattr(mutate, "run_mutmut", lambda _cwd, _patterns, _workers: None)
    monkeypatch.setattr(mutate, "mutmut_results", lambda _cwd: "")
    return repo


def _commit_edit(repo: Path, before: str, after: str) -> None:
    commit_on_main(repo, _FILE, before, "base")
    commit_on_branch(repo, "edit", _FILE, after, "edit")


def _report(repo: Path) -> dict:
    return json.loads((repo / ".bob" / "report.json").read_text())


def _report_after_check(repo: Path) -> dict:
    assert run_check(repo, base="main", gates=["mutate"]) == 0
    return _report(repo)


def _selected(repo: Path) -> list[str]:
    return [key.removeprefix(f"{_FILE}::") for key in _report_after_check(repo)["mutation"]["remutated"]]


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        ("def scale(x: int):\n    return x\n", "def scale(x: str) -> str:\n    return x\n", []),
        ("def scale(x: int):\n    return x\n", "def scale(x: str):\n    return x + 1\n", ["scale"]),
        (
            "def unchanged(x: int):\n    return x\n\ndef scale(x: int):\n    return x\n",
            "def unchanged(x: str):\n    return x\n\ndef scale(x: str):\n    return x + 1\n",
            ["scale"],
        ),
        (
            "def scale(x: int):\n    value = x\n    return value\n",
            "def scale(\n    x: str,\n) -> str:\n    value: str = x\n    return value\n",
            [],
        ),
        (
            "def scale(x: int):\n    value: int = x\n    return value\n",
            "def scale(x: str):\n    value: str = x + 1\n    return value\n",
            ["scale"],
        ),
        (
            "def scale(x):\n    return x\n",
            "def scale(x):\n    x: str\n    return x\n",
            ["scale"],
        ),
        (
            "def scale(x=1):\n    return x\n",
            "def scale(x: int = 2):\n    return x\n",
            ["scale"],
        ),
        (
            "def outer():\n    class Data:\n        value: int\n    return Data\n",
            "def outer():\n    class Data:\n        value: str\n    return Data\n",
            ["outer"],
        ),
    ],
)
def test_python_gate_scopes_mutation_to_runtime_edits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    before: str,
    after: str,
    expected: list[str],
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, _FILE, _FUTURE + before, "base")
    commit_on_branch(repo, "edit", _FILE, _FUTURE + after, "edit")
    monkeypatch.setattr(mutate, "mutmut_version", lambda: "3.8.0")
    monkeypatch.setattr(mutate, "pytest_exit_code", lambda _cwd: 0)
    seen: list[list[str]] = []

    def fake_run(_cwd: Path, patterns: list[str], _workers: int | None) -> None:
        seen.append(patterns)

    monkeypatch.setattr(mutate, "run_mutmut", fake_run)
    monkeypatch.setattr(mutate, "mutmut_results", lambda _cwd: "")

    assert run_check(repo, base="main", gates=["mutate"]) == 0

    report = json.loads((repo / ".bob" / "report.json").read_text())
    assert report["mutation"]["remutated"] == [f"{_FILE}::{name}" for name in expected]
    patterns = [
        pattern
        for name in expected
        for pattern in (f"app.scope.x_{name}__mutmut*", f"*app.scope.x_{name}")
    ]
    assert seen == ([patterns] if patterns else [])


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        ("def f() -> 'int':\n    return 1\n", "def f() -> 'str':\n    return 1\n", []),
        ("def f() -> int:\n    return 1\n", "def f() -> int():\n    return 1\n", ["f"]),
        ("def f(x: marker(1)):\n    return x\n", "def f(x: marker(2)):\n    return x\n", ["f"]),
        ("def f() -> int:\n    return 1\n", _FUTURE + "def f() -> str:\n    return 1\n", ["f"]),
        ("def f():\n    return 1\n", "def f():\n    return 1  # touched\n", ["f"]),
        (_FUTURE + "async def f(x: int):\n    return x\n",
         _FUTURE + "async def f(x: str):\n    return x\n", []),
        (_FUTURE + "class C:\n    def f(self, x: int):\n        return x\n",
         _FUTURE + "class D:\n    def f(self, x: str):\n        return x\n", ["D.f"]),
        (_FUTURE + "if True:\n    def f(x: int):\n        return x\n",
         _FUTURE + "if False:\n    def f(x: str):\n        return x\n", ["f"]),
        ("def f(x):\n    item: int\n    return x\n", "def f(x):\n    item: str\n    return x\n", []),
        (_FUTURE + "def f(obj):\n    obj.value: int\n    return obj\n",
         _FUTURE + "def f(obj):\n    obj.value: str = 0\n    return obj\n", ["f"]),
        (_FUTURE + "def f(x: int):\n    return x\n", _FUTURE + "def f(x):\n    return x\n", []),
    ],
)
def test_gate_keeps_changes_that_are_not_proven_type_only(
    scope_repo: Path, before: str, after: str, expected: list[str]
) -> None:
    _commit_edit(scope_repo, before, after)

    assert _selected(scope_repo) == expected


@pytest.mark.parametrize(
    ("imports", "guard", "remaining_imports", "expected"),
    [
        ("from typing import TYPE_CHECKING\n", "TYPE_CHECKING", "", []),
        ("import typing as t\n", "t.TYPE_CHECKING", "", []),
        ("import other as t\n", "t.TYPE_CHECKING", "", ["f"]),
        ("from other import TYPE_CHECKING as t\n", "t", "", ["f"]),
        ("from .typing import TYPE_CHECKING as t\n", "t", "", ["f"]),
        ("from typing import cast as t\n", "t", "", ["f"]),
        ("import typing as t\nimport other as t\n", "t.TYPE_CHECKING", "import other as t\n", ["f"]),
        ("import typing as t\nimport t.sub.child\n", "t.TYPE_CHECKING", "import t.sub.child\n", ["f"]),
        ("import typing as t\nt = runtime\n", "t.TYPE_CHECKING", "t = runtime\n", ["f"]),
        ("import typing as t\nfactory().TYPE_CHECKING = True\n", "t.TYPE_CHECKING",
         "factory().TYPE_CHECKING = True\n", ["f"]),
        ("import typing as t\nt.Any = object()\n", "t.TYPE_CHECKING", "import typing as t\nt.Any = object()\n", []),
        ("import typing as t\n", "t", "", ["f"]),
        ("import typing as t\n", "t.Any", "", ["f"]),
    ],
)
def test_gate_skips_deleted_typing_guards_only_when_binding_is_proven(
    scope_repo: Path, imports: str, guard: str, remaining_imports: str, expected: list[str]
) -> None:
    stable = "def f():\n    return 1\n"
    _commit_edit(
        scope_repo, imports + stable + f"if {guard}:\n    import types\n", remaining_imports + stable
    )

    assert _selected(scope_repo) == expected


def test_gate_reports_an_unparseable_edited_file(scope_repo: Path) -> None:
    before = _FUTURE + "def f(x: int):\n    return x\n"
    _commit_edit(scope_repo, before, _FUTURE + "def f(x: str):\n    return (\n")

    assert run_check(scope_repo, base="main", gates=["mutate"]) == 4
    assert "cannot parse src/app/scope.py:3" in _report(scope_repo)["gates"][0]["reason"]


def test_gate_keeps_a_deleted_guard_before_its_import(scope_repo: Path) -> None:
    stable = "def f():\n    return 1\n"
    _commit_edit(
        scope_repo,
        stable + "if typing.TYPE_CHECKING:\n    import types\nimport typing\n",
        stable + "import typing\n",
    )

    assert _selected(scope_repo) == ["f"]


def test_gate_keeps_runtime_use_of_the_typing_import(scope_repo: Path) -> None:
    stable = "import typing\ndef f():\n    return typing.Any\n"
    after = stable.removeprefix("import typing\n")
    _commit_edit(scope_repo, stable + "if typing.TYPE_CHECKING:\n    import types\n", after)

    assert _selected(scope_repo) == ["f"]


def test_gate_skips_an_import_immediately_followed_by_its_typing_guard(scope_repo: Path) -> None:
    after = "def f():\n    return 1\n"
    _commit_edit(scope_repo, after + "import typing\nif typing.TYPE_CHECKING:\n    import types\n", after)

    assert _selected(scope_repo) == []


def test_gate_keeps_deleted_outer_body_anchored_inside_annotation_only_inner(
    scope_repo: Path,
) -> None:
    before = _FUTURE + (
        "def outer():\n"
        "    def inner(x: int):\n"
        "        return x\n"
        "    record()\n"
        "    return inner\n"
    )
    _commit_edit(scope_repo, before, before.replace("x: int", "x: str").replace("    record()\n", ""))

    assert "outer" in _selected(scope_repo)


def test_gate_keeps_a_hunk_that_starts_before_an_annotation_only_function(scope_repo: Path) -> None:
    before = _FUTURE + "setting = 1\ndef f(x: int):\n    return x\n"
    _commit_edit(scope_repo, before, before.replace("= 1", "= 2").replace("x: int", "x: str"))

    assert _selected(scope_repo) == ["f"]


def test_gate_skips_deletion_of_an_annotation_in_a_mixed_diff(scope_repo: Path) -> None:
    before = _FUTURE + (
        "def type_only(\n"
        "    x\n"
        "    : int\n"
        "):\n"
        "    return x\n\n"
        "def changed():\n"
        "    return 1\n"
    )
    _commit_edit(scope_repo, before, before.replace("    : int\n", "").replace("return 1", "return 2"))

    assert _selected(scope_repo) == ["changed"]


def test_gate_preserves_annotation_read_by_a_decorator(scope_repo: Path) -> None:
    before = _FUTURE + (
        "from typing import get_type_hints\n\n"
        "def convert(fn):\n"
        "    decode = get_type_hints(fn)['item_id']\n"
        "    return lambda value: fn(decode(value))\n\n"
        "@convert\n"
        "def item(item_id: int) -> int:\n"
        "    return item_id\n"
    )
    after = before.replace("item_id: int", "item_id: str").replace("-> int", "-> str")
    _commit_edit(scope_repo, before, after)

    for source, value in ((before, 42), (after, "42")):
        namespace = {}
        exec(source, namespace)
        assert namespace["item"]("42") == value
    assert _selected(scope_repo) == ["item"]


@pytest.mark.parametrize(("glob", "expected"), [("src/app/*.py", ["f"]), ("other/*.py", [])])
def test_gate_can_keep_runtime_read_annotations_in_matching_modules(
    scope_repo: Path, glob: str, expected: list[str]
) -> None:
    before = _FUTURE + "def f(x: int):\n    return x\n"
    _commit_edit(scope_repo, before, before.replace("x: int", "x: str"))
    (scope_repo / "bob.yaml").write_text(f"mutation:\n  runtime_annotation_globs: ['{glob}']\n")

    assert _selected(scope_repo) == expected


@pytest.mark.parametrize("wrong", ["true", "null", "src/app/*.py", "[1]"])
def test_bad_runtime_annotation_globs_exit_four(scope_repo: Path, wrong: str) -> None:
    (scope_repo / "bob.yaml").write_text(f"mutation:\n  runtime_annotation_globs: {wrong}\n")

    result = run_bob(scope_repo, "mutate", "--base", "main")

    assert result.returncode == 4
    assert "bob.yaml: mutation.runtime_annotation_globs must be a list of strings" in result.stderr
    assert not (scope_repo / ".bob" / "report.json").exists()


@pytest.mark.parametrize("flags", [(), ("--since-last-run",)])
def test_annotation_edit_remutates_a_cached_unwaived_survivor(
    scope_repo: Path, monkeypatch: pytest.MonkeyPatch, flags: tuple[str, ...]
) -> None:
    before = _FUTURE + "def f(x: int):\n    return x + 1\n"
    _commit_edit(scope_repo, before.replace("+ 1", "+ 0"), before)
    monkeypatch.setattr(
        mutate, "mutmut_results", lambda _cwd: "    app.scope.x_f__mutmut_1: survived\n"
    )
    monkeypatch.setattr(
        mutate, "mutmut_show",
        lambda _cwd, _id: f"--- {_FILE}\n+++ {_FILE}\n@@ -2 +2 @@\n"
        "-    return x + 1\n+    return x - 1\n",
    )
    assert run_check(scope_repo, base="main", gates=["mutate"]) == 3
    assert _report(scope_repo)["survivors"][0]["status"] == "survived"

    commit_on_branch(scope_repo, "annotation", _FILE, before.replace("x: int", "x: str"), "type")
    assert run_bob(scope_repo, "mutate", "--base", "edit", *flags).returncode == 0

    report = _report(scope_repo)
    assert report["mutation"]["remutated"] == [f"{_FILE}::f"]
    assert report["mutation"]["reused"] == []
    assert report["survivors"][0]["blocking"] is False


def test_gate_keeps_original_scope_for_new_and_dirty_sources(scope_repo: Path) -> None:
    before = _FUTURE + "def f(x: int):\n    return x\n"
    _commit_edit(scope_repo, before, before.replace("x: int", "x: str"))
    commit_on_branch(scope_repo, "edit", "src/app/new.py", "def new():\n    return 1\n", "new")
    (scope_repo / _FILE).write_text(before.replace("return x", "return x + 1"))

    assert _report_after_check(scope_repo)["mutation"]["remutated"] == [
        "src/app/new.py::new", f"{_FILE}::f",
    ]
