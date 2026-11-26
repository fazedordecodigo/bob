"""Keep Python mutation scope on runtime edits."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from copy import copy
from pathlib import Path
from typing import TypeVar

from bob_quality.diff import GitError, _git

_Function = ast.FunctionDef | ast.AsyncFunctionDef
_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
_Node = TypeVar("_Node", bound=ast.AST)
_SUITES = ("body", "orelse", "finalbody", "handlers", "cases")
_Position = tuple[tuple[str, str, int], ...]


def mutation_lines(cwd: Path, base: str, lines: dict[str, set[int]]) -> dict[str, set[int]]:
    python = [file for file in lines if file.endswith(".py")]
    if not python:
        return lines
    try:
        ancestor = _git(cwd, "merge-base", base, "HEAD").strip()
    except GitError:
        return lines
    return {**lines, **{file: _file_lines(cwd, ancestor, file, lines[file]) for file in python}}


def _file_lines(cwd: Path, ancestor: str, file: str, touched: set[int]) -> set[int]:
    try:
        head = _git(cwd, "show", f"HEAD:{file}")
        if head != (cwd / file).read_text():
            return touched
        before = ast.parse(_git(cwd, "show", f"{ancestor}:{file}"))
        after = ast.parse(head)
    except (GitError, OSError, SyntaxError, UnicodeError, ValueError):
        return touched
    return _runtime_lines(before, after, touched)


def _runtime_lines(before: ast.Module, after: ast.Module, touched: set[int]) -> set[int]:
    deferred = _deferred(before)
    if deferred != _deferred(after):
        return touched
    original = ast.dump(before)
    edited = ast.dump(after)
    if original == edited:
        return touched

    old = _normalize(before, deferred)
    new = _normalize(after, deferred)
    if ast.dump(before) == ast.dump(after):
        return set()
    return touched.difference(_annotation_lines(old, new))


def _deferred(tree: ast.Module) -> bool:
    return any(
        alias.name == "annotations"
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "__future__" and not node.level
        for alias in node.names
    )


def _typing_import(node: ast.stmt) -> tuple[str, bool, ast.alias] | None:
    if not isinstance(node, (ast.Import, ast.ImportFrom)) or len(node.names) != 1:
        return None
    alias = node.names[0]
    name = alias.asname or alias.name
    if isinstance(node, ast.Import):
        return (name, True, alias) if alias.name == "typing" else None
    if _imports_type_checking(node, alias):
        return name, False, alias
    return None


def _imports_type_checking(node: ast.ImportFrom, alias: ast.alias) -> bool:
    return node.module == "typing" and not node.level and alias.name == "TYPE_CHECKING"


def _guard_name(node: ast.stmt, qualified: bool) -> ast.Name | None:
    if not isinstance(node, ast.If) or node.orelse:
        return None
    if not all(isinstance(stmt, (ast.Import, ast.ImportFrom)) for stmt in node.body):
        return None
    test = node.test
    if qualified:
        if not isinstance(test, ast.Attribute) or test.attr != "TYPE_CHECKING":
            return None
        test = test.value
    return test if isinstance(test, ast.Name) else None


def _binding_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.alias):
        return node.asname or node.name.split(".", 1)[0]
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.ExceptHandler)):
        return node.name
    if isinstance(node, ast.arg):
        return node.arg
    if isinstance(node, (ast.MatchAs, ast.MatchStar)):
        return node.name
    if isinstance(node, ast.MatchMapping):
        return node.rest
    return _writes_name(node)


def _writes_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load):
        return node.id
    if isinstance(node, ast.Attribute) and not isinstance(node.ctx, ast.Load):
        if node.attr == "TYPE_CHECKING" and isinstance(node.value, ast.Name):
            return node.value.id
    return None


def _guard_uses(tree: ast.Module, start: int, qualified: bool, name: str) -> dict[ast.stmt, ast.Name]:
    return {
        stmt: guard
        for stmt in tree.body
        if stmt.lineno > start
        if (guard := _guard_name(stmt, qualified)) is not None and guard.id == name
    }


def _only_guard_uses(tree: ast.Module, name: str, guards: set[ast.Name]) -> bool:
    names = {part for part in ast.walk(tree) if isinstance(part, ast.Name) and part.id == name}
    return names == guards


def _typing_statements(tree: ast.Module, node: ast.stmt) -> set[ast.stmt]:
    imported = _typing_import(node)
    if imported is None:
        return set()
    name, qualified, alias = imported
    if any(part is not alias and _binding_name(part) == name for part in ast.walk(tree)):
        return set()
    guards = _guard_uses(tree, node.lineno, qualified, name)
    if guards and _only_guard_uses(tree, name, set(guards.values())):
        return {node, *guards}
    return set(guards)


def _header(node: ast.AST) -> str:
    shell = copy(node)
    for field in _SUITES:
        if hasattr(shell, field):
            setattr(shell, field, [])
    return ast.dump(shell)


def _definitions(node: ast.AST, path: _Position = ()) -> Iterator[tuple[_Position, _Function]]:
    for field in _SUITES:
        for index, child in enumerate(getattr(node, field, ())):
            position = (*path, (_header(node), field, index))
            if isinstance(child, _FUNCTIONS):
                yield position, child
            yield from _definitions(child, position)


def _normalize(tree: ast.Module, deferred: bool) -> dict[_Position, tuple[str, _Function]]:
    typing = set().union(*(_typing_statements(tree, node) for node in tree.body))
    tree.body = [node for node in tree.body if node not in typing]
    original = {id(node): ast.dump(node) for node in ast.walk(tree) if isinstance(node, _FUNCTIONS)}
    _WithoutAnnotations(deferred).visit(tree)
    return {path: (original[id(node)], node) for path, node in _definitions(tree)}


def _annotation_lines(
    before: dict[_Position, tuple[str, _Function]],
    after: dict[_Position, tuple[str, _Function]],
) -> Iterator[int]:
    for path in before.keys() & after.keys():
        old, old_node = before[path]
        new, new_node = after[path]
        if old != new and ast.dump(old_node) == ast.dump(new_node):
            start = min((d.lineno for d in new_node.decorator_list), default=new_node.lineno)
            yield from range(start, (new_node.end_lineno or new_node.lineno) + 1)


class _WithoutAnnotations(ast.NodeTransformer):
    def __init__(self, deferred: bool) -> None:
        self.deferred = deferred
        self.local = False

    def _annotation(self, node: ast.expr | None) -> ast.expr | None:
        if self.deferred or isinstance(node, ast.Constant) and isinstance(node.value, str):
            return None
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        node.annotation = self._annotation(node.annotation)
        return node

    def _function(self, node: _Function) -> _Function:
        node.returns = self._annotation(node.returns)
        return self._with_scope(node, local=True)

    visit_FunctionDef = _function
    visit_AsyncFunctionDef = _function

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        return self._with_scope(node, local=False)

    def _with_scope(self, node: _Node, *, local: bool) -> _Node:
        outer, self.local = self.local, local
        self.generic_visit(node)
        self.local = outer
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.stmt:
        if not self.local:
            return node
        if node.simple and node.value is not None:
            return ast.Assign(targets=[node.target], value=node.value, type_comment=None)
        node.annotation = ast.Constant(None)
        return node
