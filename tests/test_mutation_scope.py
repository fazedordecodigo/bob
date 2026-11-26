from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

import bob_quality.mutate as mutate
from bob_quality.check import run_check
from bob_quality.diff import changed_lines
from bob_quality.mutation_scope import _WithoutAnnotations, _runtime_lines, mutation_lines
from helpers import commit_on_branch, commit_on_main, init_python_repo

_FILE = "src/app/scope.py"
_FUTURE = "from __future__ import annotations\n"


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
    ("prefix", "before", "after", "selected"),
    [
        ("", "def f() -> 'int': return 1", "def f() -> 'str': return 1", False),
        ("", "def f() -> int: return 1", "def f() -> int(): return 1", True),
        ("", "def f() -> int: return 1", _FUTURE + "def f() -> str: return 1", True),
        ("", "def f(): return 1", "def f(): return 1  # touched", True),
        (
            "",
            "from typing import TYPE_CHECKING\n"
            "def f(): return 1\n"
            "if TYPE_CHECKING:\n    from types import NoneType",
            "def f(): return 1",
            False,
        ),
        (
            "",
            "import typing as t\ndef f(): return 1\nif t.TYPE_CHECKING:\n    import types",
            "def f(): return 1",
            False,
        ),
        (
            "import typing\ntyping.TYPE_CHECKING = True\n",
            "def f(): return 1\nif typing.TYPE_CHECKING:\n    import types",
            "def f(): return 1",
            True,
        ),
        (
            "from typing import TYPE_CHECKING\n",
            "def f(): return 1\nif TYPE_CHECKING:\n    import types\nelse:\n    import os",
            "def f(): return 1",
            True,
        ),
        (
            _FUTURE,
            "async def f(x: int) -> int: return x",
            "async def f(x: str) -> str: return x",
            False,
        ),
        (
            _FUTURE,
            "class C:\n    def f(self, x: int): return x",
            "class C:\n    def f(self, x: str): return x",
            False,
        ),
        (
            _FUTURE,
            "class C:\n    def f(self, x: int): return x",
            "class D:\n    def f(self, x: str): return x",
            True,
        ),
        (
            _FUTURE,
            "if True:\n    def f(x: int): return x",
            "if False:\n    def f(x: str): return x",
            True,
        ),
        (
            "",
            "def f(x):\n    item: int\n    return x",
            "def f(x):\n    item: str\n    return x",
            False,
        ),
        (
            _FUTURE,
            "def f(x: int): return x",
            "def f(x: str): return (",
            True,
        ),
    ],
)
def test_filter_preserves_changes_it_cannot_prove_type_only(
    tmp_path: Path, prefix: str, before: str, after: str, selected: bool
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, _FILE, prefix + before + "\n", "base")
    commit_on_branch(repo, "edit", _FILE, prefix + after + "\n", "edit")
    raw = changed_lines(repo, "main")

    assert raw[_FILE]
    assert mutation_lines(repo, "main", raw)[_FILE] == (raw[_FILE] if selected else set())


def test_filter_keeps_original_scope_for_new_files_dirty_sources_and_typescript(
    tmp_path: Path,
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, _FILE, _FUTURE + "def f(x: int): return x\n", "base")
    commit_on_branch(repo, "edit", _FILE, _FUTURE + "def f(x: str): return x\n", "type")
    commit_on_branch(repo, "edit", "src/app/new.py", "def new(): return 1\n", "new")
    commit_on_branch(repo, "edit", "src/app/app.ts", "export const n = 1;\n", "ts")
    (repo / _FILE).write_text(_FUTURE + "def f(x: str): return x + 1\n")
    raw = changed_lines(repo, "main")

    assert mutation_lines(repo, "main", raw) == raw
    assert mutation_lines(repo, "unresolvable", raw) == raw
    assert mutation_lines(repo, "main", {"src/app/app.ts": {1}}) == {"src/app/app.ts": {1}}


@pytest.mark.parametrize(
    "imports",
    [
        "import other as t\n",
        "from other import TYPE_CHECKING as t\n",
        "from .typing import TYPE_CHECKING as t\n",
        "from typing import cast as t\n",
        "import typing as t\nimport other as t\n",
        "import typing as t\nimport t.sub.child\n",
    ],
)
def test_guard_must_refer_to_typing_without_shadowing(imports: str) -> None:
    prefix = imports + "def f(): return 1\n"
    condition = "t" if imports.startswith("from") else "t.TYPE_CHECKING"
    before = prefix + f"if {condition}:\n    import types\n"
    line = len(prefix.splitlines())

    assert _runtime_lines(ast.parse(before), ast.parse(prefix), {line}) == {line}


@pytest.mark.parametrize(
    ("context", "condition", "kept"),
    [
        ("", "t", {2}),
        ("", "t.Any", {2}),
        ("t.Any = object()\n", "t.TYPE_CHECKING", set()),
        ("factory().TYPE_CHECKING = True\n", "t.TYPE_CHECKING", {2}),
    ],
)
def test_qualified_guard_only_accepts_type_checking(
    context: str, condition: str, kept: set[int]
) -> None:
    prefix = "import typing as t\n" + context
    before = prefix + f"if {condition}:\n    import types\n"
    after = prefix if context.startswith("t.") else context

    assert _runtime_lines(ast.parse(before), ast.parse(after), {2}) == kept


def test_bare_guard_does_not_normalize_an_attribute() -> None:
    prefix = "from typing import TYPE_CHECKING\n"
    before = prefix + "if flag.TYPE_CHECKING:\n    import types\n"

    assert _runtime_lines(ast.parse(before), ast.parse(prefix), {2}) == {2}


def test_typing_import_stays_if_used_at_runtime() -> None:
    before = "import typing as t\nif t.TYPE_CHECKING:\n    import types\nresult = t\n"
    after = "result = t\n"

    assert _runtime_lines(ast.parse(before), ast.parse(after), {1}) == {1}


def test_typing_guard_immediately_after_its_import_is_ignored() -> None:
    before = "import typing\nif typing.TYPE_CHECKING:\n    import types\n"

    assert _runtime_lines(ast.parse(before), ast.parse(""), {1}) == set()


def test_evaluated_parameter_annotations_stay_in_scope() -> None:
    before = "def f(x: factory()):\n    return x\n"
    after = "def f(x: other()):\n    return x\n"

    assert _runtime_lines(ast.parse(before), ast.parse(after), {1}) == {1}


def test_module_annotations_are_not_erased() -> None:
    before = _FUTURE + "label: int = 1\n"
    after = _FUTURE + "label: str = 1\n"

    assert _runtime_lines(ast.parse(before), ast.parse(after), {2}) == {2}


def test_local_annotations_do_not_erase_target_evaluation() -> None:
    before = _FUTURE + "def f(obj):\n    obj.value: int\n    return obj\n"
    after = _FUTURE + "def f(obj):\n    obj.value: str = 0\n    return obj\n"

    assert _runtime_lines(ast.parse(before), ast.parse(after), {3}) == {3}


def test_bare_annotation_preserves_the_declaration_without_an_assignment() -> None:
    tree = ast.parse("def f():\n    value: str\n    return value\n")
    function = tree.body[0]
    assert isinstance(function, ast.FunctionDef)

    _WithoutAnnotations(deferred=True).visit(tree)

    assert isinstance(function.body[0], ast.AnnAssign)
    assert function.body[0].value is None


def test_filter_keeps_changed_lines_on_each_side_of_an_annotation_only_method() -> None:
    before = _FUTURE + (
        "class Parent:\n"
        "    before = 1\n"
        "    def f(self):\n"
        "        class Inner:\n"
        "            field: int\n"
        "        value: int = 0\n"
        "        return value\n"
        "    after = 2\n"
    )
    after = before.replace("before = 1", "before = 3").replace("after = 2", "after = 4").replace(
        "value: int", "value: str"
    )

    assert _runtime_lines(ast.parse(before), ast.parse(after), {3, 7, 9}) == {3, 9}
