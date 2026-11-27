"""Keep Python mutation scope on runtime edits."""

from __future__ import annotations

import ast
from collections.abc import Iterator, Sequence
from copy import copy
from fnmatch import fnmatchcase
from pathlib import Path
from typing import TypeVar

from bob_quality.diff import DiffHunk, GitError, _git, parse_diff_hunks

_Function = ast.FunctionDef | ast.AsyncFunctionDef
_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
_Node = TypeVar("_Node", bound=ast.AST)
_SUITES = ("body", "orelse", "finalbody", "handlers", "cases")
_Position = tuple[tuple[str, str, int], ...]


def mutation_lines(
    cwd: Path, base: str, lines: dict[str, set[int]], runtime_globs: tuple[str, ...]
) -> dict[str, set[int]]:
    python = [
        file
        for file in lines
        if file.endswith(".py") and not any(fnmatchcase(file, glob) for glob in runtime_globs)
    ]
    if not python:
        return lines
    try:
        ancestor = _git(cwd, "merge-base", base, "HEAD").strip()
        hunks = parse_diff_hunks(_git(cwd, "diff", "--unified=0", f"{ancestor}..HEAD"))
    except GitError:
        return lines
    return {
        **lines,
        **{
            file: _file_lines(cwd, ancestor, file, lines[file], hunks[file])
            for file in set(python).intersection(hunks)
        },
    }


def _file_lines(
    cwd: Path, ancestor: str, file: str, touched: set[int], hunks: Sequence[DiffHunk]
) -> set[int]:
    try:
        head = _git(cwd, "show", f"HEAD:{file}")
        if head != (cwd / file).read_text():
            return touched
        before = ast.parse(_git(cwd, "show", f"{ancestor}:{file}"))
        after = ast.parse(head)
    except (GitError, OSError, SyntaxError, UnicodeError, ValueError):
        return touched
    return _runtime_lines(before, after, touched, hunks)


def _runtime_lines(
    before: ast.Module, after: ast.Module, touched: set[int], hunks: Sequence[DiffHunk]
) -> set[int]:
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
    return touched.difference(_typing_hunk_lines(hunks, list(_annotation_scopes(old, new))))


def _typing_hunk_lines(
    hunks: Sequence[DiffHunk], scopes: Sequence[tuple[range, range]]
) -> Iterator[int]:
    for hunk in hunks:
        if any(
            all(line in previous for line in hunk.old)
            and all(line in current for line in hunk.new_lines)
            for previous, current in scopes
        ):
            yield from hunk.new_lines


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
        return node.asname or node.name.partition(".")[0]
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.ExceptHandler)):
        return node.name
    if isinstance(node, ast.arg):
        return node.arg
    if isinstance(node, (ast.MatchAs, ast.MatchStar)):
        return node.name
    if isinstance(node, ast.MatchMapping):
        return node.rest
    if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load):
        return node.id
    return None


def _writes_typing_flag(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "TYPE_CHECKING"
        and not isinstance(node.ctx, ast.Load)
    )


def _guard_binding_is_stable(tree: ast.Module, name: str, alias: ast.alias) -> bool:
    return not any(
        _writes_typing_flag(part) or _binding_name(part) == name
        for part in ast.walk(tree)
        if part is not alias
    )


def _guard_uses(body: list[ast.stmt], qualified: bool, name: str) -> dict[ast.stmt, ast.Name]:
    return {
        stmt: guard
        for stmt in body
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
    if not _guard_binding_is_stable(tree, name, alias):
        return set()
    guards = _guard_uses(tree.body[tree.body.index(node) + 1 :], qualified, name)
    if guards and _only_guard_uses(tree, name, set(guards.values())):
        return {node, *guards}
    return set(guards)


def _header(node: ast.AST) -> str:
    shell = copy(node)
    for field in _SUITES:
        if hasattr(shell, field):
            delattr(shell, field)
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


def _annotation_scopes(
    before: dict[_Position, tuple[str, _Function]],
    after: dict[_Position, tuple[str, _Function]],
) -> Iterator[tuple[range, range]]:
    for path in before.keys() & after.keys():
        old, old_node = before[path]
        new, new_node = after[path]
        if old != new and ast.dump(old_node) == ast.dump(new_node):
            yield _function_lines(old_node), _function_lines(new_node)


def _function_lines(node: _Function) -> range:
    assert node.end_lineno is not None
    return range(node.lineno, node.end_lineno + 1)


class _WithoutAnnotations(ast.NodeTransformer):
    def __init__(self, deferred: bool) -> None:
        self.deferred = deferred
        self.scopes: list[ast.AST] = []

    def _annotation(self, node: ast.expr | None) -> ast.expr | None:
        if self.deferred or isinstance(node, ast.Constant) and isinstance(node.value, str):
            return None
        return node

    def _function(self, node: _Function) -> _Function:
        if not node.decorator_list:
            node.returns = self._annotation(node.returns)
            for part in ast.iter_child_nodes(node.args):
                if isinstance(part, ast.arg):
                    part.annotation = self._annotation(part.annotation)
        return self._with_scope(node)

    visit_FunctionDef = _function
    visit_AsyncFunctionDef = _function

    def _with_scope(self, node: _Node) -> _Node:
        self.scopes.append(node)
        self.generic_visit(node)
        self.scopes.pop()
        return node

    visit_ClassDef = _with_scope

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.stmt:
        if not self.scopes or not isinstance(self.scopes[-1], _FUNCTIONS):
            return node
        if node.simple and node.value is not None:
            return ast.Assign(targets=[node.target], value=node.value)
        del node.annotation
        return node
