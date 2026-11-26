"""`worktree_lines`: as linhas do diff de HEAD na árvore de trabalho."""

from __future__ import annotations

from pathlib import Path

from bob_quality.diff import _Hunk, _local_hunks, _shift_line, changed_lines, worktree_lines
from helpers import commit_on_branch, commit_on_main, init_python_repo

INSERT = _Hunk(5, 6, [], ["a", "b", "c"])
REPLACE = _Hunk(10, 13, ["x", "y"], ["x2", "y", "z", "w"])
DELETE = _Hunk(20, 24, ["gone"], [])
FLOW = "def flow(n: int) -> bool:\n    x = n\n    print(x)\n    # positive\n    return x > 0\n"


def test_lines_before_an_insertion_stay_and_lines_after_it_move() -> None:
    assert _shift_line(5, [INSERT]) == {5}
    assert _shift_line(6, [INSERT]) == {9}


def test_a_replaced_line_maps_by_content_and_an_uneven_swap_takes_the_whole_block() -> None:
    assert _shift_line(9, [INSERT, REPLACE]) == {12}
    assert _shift_line(10, [INSERT, REPLACE]) == {13}
    assert _shift_line(11, [INSERT, REPLACE]) == {14}
    assert _shift_line(12, [INSERT, REPLACE]) == {17}
    assert _shift_line(1, [_Hunk(1, 1, ["a", "b"], ["c", "d", "e"])]) == {1, 2, 3}


def test_a_one_for_one_swap_keeps_each_line_on_its_counterpart() -> None:
    swap = _Hunk(3, 3, ["# old", "return x > 0"], ["# new", "return x > 1"])

    assert _shift_line(3, [swap]) == {3}
    assert _shift_line(4, [swap]) == {4}


def test_a_deleted_line_anchors_on_the_line_before_it() -> None:
    assert _shift_line(20, [INSERT, REPLACE, DELETE]) == {24}
    assert _shift_line(21, [INSERT, REPLACE, DELETE]) == {25}
    assert _shift_line(1, [_Hunk(1, 0, ["gone"], [])]) == {1}
    assert _shift_line(3, [_Hunk(2, 2, ["keep", "gone"], ["keep"])]) == {2}
    assert _shift_line(2, [_Hunk(2, 2, ["gone", "keep"], ["keep"])]) == {1}


def test_hunks_keep_their_removed_and_added_lines() -> None:
    patch = (
        "diff --git a/src/a.py b/src/a.py\n--- a/src/a.py\n+++ b/src/a.py\n"
        "@@ -3 +4 @@\n-old\n+new\n@@ -7,0 +9,2 @@\n++++ plus\n+--- minus\n"
        "diff --git a/src/b.py b/src/b.py\n--- a/src/b.py\n+++ b/src/b.py\n"
        "@@ -1,2 +1 @@\n-x\n-y\n+z\n\\ No newline at end of file\n"
    )

    assert _local_hunks(patch) == {
        "src/a.py": [_Hunk(3, 4, ["old"], ["new"]), _Hunk(7, 9, [], ["+++ plus", "--- minus"])],
        "src/b.py": [_Hunk(1, 1, ["x", "y"], ["z"])],
    }


def test_worktree_lines_follow_an_uncommitted_edit(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "work", "src/app/x.py", "a = 1\nb = 2\n", "add x")
    (repo / "src" / "app" / "x.py").write_text("# note\na = 1\nb = 2\n")

    assert worktree_lines(repo, {}) == {}
    assert worktree_lines(repo, {"src/app/x.py": {1, 2}}) == {"src/app/x.py": {2, 3}}
    assert worktree_lines(repo, {"src/app/y.py": {4}}) == {"src/app/y.py": {4}}


def test_a_local_edit_next_to_a_committed_one_stays_out_of_scope(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/flow.py", FLOW, "add flow")
    commit_on_branch(repo, "work", "src/app/flow.py", FLOW.replace("# positive", "# above zero"), "comment")
    (repo / "src" / "app" / "flow.py").write_text(
        FLOW.replace("# positive", "# strictly above zero").replace("x > 0", "x > 1")
    )

    assert worktree_lines(repo, changed_lines(repo, "main")) == {"src/app/flow.py": {4}}


def test_a_committed_removal_stays_in_scope_when_its_anchor_is_deleted_locally(
    tmp_path: Path,
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/flow.py", FLOW, "add flow")
    commit_on_branch(repo, "work", "src/app/flow.py", FLOW.replace("    print(x)\n", ""), "drop print")
    (repo / "src" / "app" / "flow.py").write_text(FLOW.replace("    print(x)\n", "").replace("    x = n\n", ""))

    assert changed_lines(repo, "main") == {"src/app/flow.py": {2}}
    assert worktree_lines(repo, changed_lines(repo, "main")) == {"src/app/flow.py": {1}}


def test_a_latin1_edit_outside_python_does_not_break_the_projection(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "work", "docs/notes.txt", "cafe\n", "notes")
    commit_on_branch(repo, "work", "src/app/x.py", "a = 1\n", "add x")
    (repo / "docs" / "notes.txt").write_bytes("café\n".encode("latin-1"))

    assert worktree_lines(repo, changed_lines(repo, "main")) == {"docs/notes.txt": {1}, "src/app/x.py": {1}}
