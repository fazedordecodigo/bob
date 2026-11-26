from __future__ import annotations

import json
from pathlib import Path

import pytest

import bob_quality.mutate as mutate
from bob_quality.check import run_check
from bob_quality.diff import changed_lines
from bob_quality.mutation_scope import mutation_lines
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
