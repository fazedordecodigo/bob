"""`worktree_lines`: as linhas do diff de HEAD na árvore de trabalho."""

from __future__ import annotations

from pathlib import Path

from bob_quality.diff import _local_hunks, _shift_line, worktree_lines
from helpers import commit_on_branch, init_python_repo

INSERT = (5, 0, 6, 3)
REPLACE = (10, 2, 13, 4)
DELETE = (20, 1, 24, 0)


def test_lines_before_an_insertion_stay_and_lines_after_it_move() -> None:
    assert _shift_line(5, [INSERT]) == {5}
    assert _shift_line(6, [INSERT]) == {9}


def test_a_replaced_line_maps_to_every_new_line_of_its_hunk() -> None:
    assert _shift_line(9, [INSERT, REPLACE]) == {12}
    assert _shift_line(10, [INSERT, REPLACE]) == {13, 14, 15, 16}
    assert _shift_line(11, [INSERT, REPLACE]) == {13, 14, 15, 16}
    assert _shift_line(12, [INSERT, REPLACE]) == {17}


def test_a_deleted_line_leaves_the_scope_and_later_lines_move_back() -> None:
    assert _shift_line(20, [INSERT, REPLACE, DELETE]) == set()
    assert _shift_line(21, [INSERT, REPLACE, DELETE]) == {25}


def test_hunk_counts_default_to_one() -> None:
    patch = "+++ b/src/a.py\n@@ -3 +4 @@\n@@ -7,0 +9,2 @@\n+++ b/src/b.py\n@@ -1,2 +1 @@\n"

    assert _local_hunks(patch) == {
        "src/a.py": [(3, 1, 4, 1), (7, 0, 9, 2)],
        "src/b.py": [(1, 2, 1, 1)],
    }


def test_worktree_lines_follow_an_uncommitted_edit(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "work", "src/app/x.py", "a = 1\nb = 2\n", "add x")
    (repo / "src" / "app" / "x.py").write_text("# note\na = 1\nb = 2\n")

    assert worktree_lines(repo, {}) == {}
    assert worktree_lines(repo, {"src/app/x.py": {1, 2}}) == {"src/app/x.py": {2, 3}}
    assert worktree_lines(repo, {"src/app/y.py": {4}}) == {"src/app/y.py": {4}}
