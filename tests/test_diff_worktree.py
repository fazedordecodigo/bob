"""`worktree_lines`: as linhas do diff da branch na árvore de trabalho, num repositório Git."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from bob_quality.diff import GitError, changed_lines, worktree_lines
from helpers import commit_on_branch, commit_on_main, init_python_repo

FILE = "src/app/flow.py"
FLOW = "def flow(n: int) -> bool:\n    x = n\n    print(x)\n    # positive\n    return x > 0\n"


def _branch(tmp_path: Path, main: str | None, branch: str, local: str | bytes) -> Path:
    repo = init_python_repo(tmp_path / "repo")
    if main is not None:
        commit_on_main(repo, FILE, main, "main")
    commit_on_branch(repo, "work", FILE, branch, "branch")
    target = repo / FILE
    target.write_bytes(local) if isinstance(local, bytes) else target.write_text(local)
    return repo


def _projected(repo: Path) -> set[int]:
    return worktree_lines(repo, changed_lines(repo, "main")).get(FILE, set())


def test_an_insertion_above_moves_the_branch_lines_down(tmp_path: Path) -> None:
    repo = _branch(tmp_path, None, "a = 1\nb = 2\n", "# note\na = 1\nb = 2\n")
    subprocess.run(["git", "add", FILE], cwd=repo, check=True)

    assert _projected(repo) == {2, 3}
    assert worktree_lines(repo, {}) == {}
    assert worktree_lines(repo, {"src/app/y.py": {4}}) == {"src/app/y.py": {4}}


def test_a_clean_tree_keeps_the_branch_lines(tmp_path: Path) -> None:
    repo = _branch(tmp_path, FLOW, FLOW.replace("x > 0", "x > 1"), FLOW.replace("x > 0", "x > 1"))

    assert _projected(repo) == {5}


def test_a_local_edit_next_to_a_committed_one_widens_the_scope_to_the_new_block(
    tmp_path: Path,
) -> None:
    branch = FLOW.replace("# positive", "# above zero")
    local = FLOW.replace("# positive", "# strictly above zero").replace("x > 0", "x > 1")
    repo = _branch(tmp_path, FLOW, branch, local)

    assert _projected(repo) == {4, 5}


def test_a_changed_function_swapped_with_a_comment_follows_the_function(tmp_path: Path) -> None:
    repo = _branch(
        tmp_path,
        "def f(): return 1\n# old note\n",
        "def f(): return 2\n# old note\n",
        "# a brand new note\ndef f(): return 3\n",
    )

    assert _projected(repo) == {1, 2}


def test_an_ambiguous_replacement_keeps_the_whole_new_block(tmp_path: Path) -> None:
    repo = _branch(tmp_path, "a = 1\nb = 2\n", "a = 10\nb = 2\n", "zzz()\nqqq()\nrrr()\nb = 2\n")

    assert _projected(repo) == {1, 2, 3}


def test_a_committed_removal_stays_in_scope_when_its_anchor_is_deleted_locally(
    tmp_path: Path,
) -> None:
    branch = FLOW.replace("    print(x)\n", "")
    repo = _branch(tmp_path, FLOW, branch, branch.replace("    x = n\n", ""))

    assert changed_lines(repo, "main") == {FILE: {2}}
    assert _projected(repo) == {1}


def test_a_branch_function_deleted_locally_leaves_its_neighbour_out(tmp_path: Path) -> None:
    old = "def old():\n    return 1\n"
    repo = _branch(tmp_path, old, old + "\n\ndef new():\n    return 2\n", old)

    assert _projected(repo) == set()


def test_inter_hunk_context_does_not_merge_local_edits(tmp_path: Path) -> None:
    main = "# one\n# two\ndef f(): return 1\n"
    repo = _branch(tmp_path, main, main.replace("1", "2"), "# uno\n# two\ndef f(): return 2\n# tail\n")
    subprocess.run(["git", "config", "diff.interHunkContext", "10"], cwd=repo, check=True)

    assert _projected(repo) == {3}


def test_a_line_separator_inside_a_line_is_not_a_new_line(tmp_path: Path) -> None:
    text = "s = 'a\u2028+b'\nt = 1\n"
    repo = _branch(tmp_path, None, text, "# top\n" + text)

    assert _projected(repo) == {2, 3}


def test_a_latin1_edit_outside_python_does_not_break_the_projection(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "work", "docs/notes.txt", "cafe\n", "notes")
    commit_on_branch(repo, "work", FILE, "a = 1\n", "add flow")
    (repo / "docs" / "notes.txt").write_bytes("café\n".encode("latin-1"))

    assert worktree_lines(repo, changed_lines(repo, "main")) == {"docs/notes.txt": {1}, FILE: {1}}


def test_a_moved_line_inside_a_hunk_keeps_its_own_position(tmp_path: Path) -> None:
    main = "a = 1\nb = 2\nc = 3\nd = 4\n"
    repo = _branch(tmp_path, main, main.replace("c = 3", "c = 30"), "x = 0\nb = 2\nc = 30\n")

    assert _projected(repo) == {3}


def test_deleted_lines_after_a_kept_one_anchor_on_it(tmp_path: Path) -> None:
    main = "a = 1\nb = 2\nc = 3\nd = 4\ne = 5\n"
    repo = _branch(tmp_path, main, main.replace("d = 4\n", ""), "a = 1\nz = 9\nc = 3\n")

    assert changed_lines(repo, "main") == {FILE: {3}}
    assert _projected(repo) == {3}
    repo_two = _branch(tmp_path / "two", main, main.replace("e = 5\n", ""), "a = 1\nb = 2\nz = 9\n")
    assert _projected(repo_two) == {3}


def test_hostile_git_config_does_not_change_the_projection(tmp_path: Path) -> None:
    repo = _branch(tmp_path, None, "a = 1\nb = 2\n", "# note\na = 1\nb = 2\n")
    branch = changed_lines(repo, "main")
    for key, value in {
        "color.diff": "always",
        "diff.noprefix": "true",
        "diff.external": "false",
        "diff.top.textconv": "sh -c 'echo top; cat \"$1\"' -",
    }.items():
        subprocess.run(["git", "config", key, value], cwd=repo, check=True)
    (repo / ".gitattributes").write_text("*.py diff=top\n")

    assert worktree_lines(repo, branch) == {FILE: {2, 3}}


def test_several_local_hunks_above_add_up(tmp_path: Path) -> None:
    main = "".join(f"v{n} = {n}\n" for n in range(1, 13))
    branch = main.replace("v9 = 9", "v9 = 90")
    local = branch.replace("v1 = 1\n", "top = 0\nv1 = 1\n").replace("v3 = 3\n", "v3 = 30\nv3b = 31\n")
    local = local.replace("v5 = 5\n", "").replace("v8 = 8\n", "v8 = 8\nmid = 0\n")
    local = local.replace("v9 = 90\n", "v9 = 90\nafter = 0\n")
    repo = _branch(tmp_path, main, branch, local)

    assert _projected(repo) == {11}


def test_a_deleted_first_line_anchor_falls_back_to_line_one(tmp_path: Path) -> None:
    repo = _branch(tmp_path, "a = 1\nb = 2\nc = 3\n", "a = 1\nc = 3\n", "c = 3\n")

    assert changed_lines(repo, "main") == {FILE: {1}}
    assert _projected(repo) == {1}


def test_a_plain_set_is_projected_like_changed_lines(tmp_path: Path) -> None:
    repo = _branch(tmp_path, None, "a = 1\nb = 2\n", "# note\na = 1\nb = 2\n")

    assert worktree_lines(repo, {FILE: {2}}) == {FILE: {3}}


def test_a_branch_file_deleted_locally_leaves_the_scope(tmp_path: Path) -> None:
    repo = _branch(tmp_path, None, "a = 1\nb = 2\n", "")
    (repo / FILE).unlink()

    assert _projected(repo) == set()


def test_outside_a_repository_the_projection_fails_with_the_git_command(tmp_path: Path) -> None:
    with pytest.raises(GitError, match="'diff'"):
        worktree_lines(tmp_path, {FILE: {1}})


def test_a_last_line_that_only_gains_its_newline_keeps_its_own_line(tmp_path: Path) -> None:
    repo = _branch(
        tmp_path,
        "def f(n):\n    return n > 0",
        "def f(n):\n    return n > 1",
        "def f(n):\n    return n > 1\n\n\ndef g(n):\n    return n < 0\n",
    )

    assert _projected(repo) == {2}


def test_a_path_with_brackets_takes_only_its_own_local_edits(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    pattern, plain = "src/[ab]/app/flow.py", "src/a/app/flow.py"
    commit_on_main(repo, pattern, "def f(n):\n    return n > 0\n", "pattern")
    commit_on_main(repo, plain, "def f(n):\n    return n > 0\n", "plain")
    commit_on_branch(repo, "work", pattern, "def f(n):\n    return n > 1\n", "branch")
    (repo / plain).write_text("# note\ndef f(n):\n    return n > 0\n")

    assert worktree_lines(repo, changed_lines(repo, "main")) == {pattern: {2}}


def test_an_edited_last_line_whose_old_text_reappears_below_takes_the_whole_block(
    tmp_path: Path,
) -> None:
    repo = _branch(
        tmp_path,
        "def f(n):\n    return n > 0",
        "def f(n):\n    return n > 1",
        "def f(n):\n    return n > 2\n\n\ndef g(n):\n    return n > 1\n",
    )

    assert _projected(repo) == {2, 3, 4, 5, 6}


@pytest.mark.parametrize(
    "mode",
    ["GIT_LITERAL_PATHSPECS", "GIT_GLOB_PATHSPECS", "GIT_NOGLOB_PATHSPECS", "GIT_ICASE_PATHSPECS"],
)
def test_a_pathspec_mode_in_the_environment_does_not_change_the_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    pattern, plain = "src/[ab]/app/flow.py", "src/a/app/flow.py"
    commit_on_main(repo, pattern, "def f(n):\n    return n > 0\n", "pattern")
    commit_on_main(repo, plain, "def f(n):\n    return n > 0\n", "plain")
    commit_on_branch(repo, "work", pattern, "def f(n):\n    return n > 1\n", "branch")
    commit_on_branch(repo, "work", FILE, "def f(n):\n    return n > 1\n", "flow")
    (repo / plain).write_text("# note\ndef f(n):\n    return n > 0\n")
    (repo / FILE).write_text("# one\n# two\ndef f(n):\n    return n > 1\n")
    lines = changed_lines(repo, "main")
    monkeypatch.setenv(mode, "1")

    assert worktree_lines(repo, lines) == {pattern: {2}, FILE: {3, 4}}


def test_a_diff_with_more_paths_than_fit_in_a_command_line_is_still_projected(
    tmp_path: Path,
) -> None:
    repo = _branch(tmp_path, None, "a = 1\nb = 2\n", "# note\na = 1\nb = 2\n")
    lines = {f"docs/{'x' * 200}/{index}.md": {1} for index in range(20_000)}

    projected = worktree_lines(repo, {**lines, FILE: {2}})

    assert projected[FILE] == {3}
