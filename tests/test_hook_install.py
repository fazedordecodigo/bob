"""Instalador do hook pre-push (CT10)."""

import os
import stat
import subprocess
from pathlib import Path

import pytest

from bob_quality import hook_install
from bob_quality.hook_install import (
    HOOK_MARKER,
    HookPathError,
    HookResult,
    install_hook,
    render_hook,
)
from bob_quality.messages import reason, render, t
from bob_quality.tools import ToolError

BOB = Path("/opt/bob home/bin/bob")
STATIC = Path(__file__).resolve().parents[1] / "src/bob_quality/hooks/pre-push"
_TEMPLATE = (
    "#!/bin/sh\n"
    "# managed-by: bob-quality\n"
    "set -e\n"
    "unset PYTEST_ADDOPTS\n"
    "unset PYTEST_PLUGINS\n"
    'BOB="<p>"\n'
    '[ -x "$BOB" ] || BOB=bob\n'
    'exec "$BOB" check --gates crap,dry,deps </dev/null\n'
)
_FOREIGN = (
    b"#!/bin/sh\nexit 0\n",
    b"# managed-by: bob-quality\n#!/bin/sh\n",
    b"#!/bin/sh\nset -e\n# managed-by: bob-quality\n",
    b"#!/bin/sh\r\n# managed-by: bob-quality\r\n",
    b"#!/bin/sh\n# managed-by: bob-quality \n",
)


@pytest.fixture(autouse=True)
def _isolated_git_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "gitconfig"
    config.write_bytes(b"")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def _repo(path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "config", "user.email", "dev@bob.local"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Dev"], cwd=path, check=True)
    return path


def _forbid_read(self: Path) -> bytes:
    raise AssertionError(self)


@pytest.mark.parametrize(
    "raw",
    [
        "/home/u/.local/share/bob-quality/bin/bob",
        "/opt/bob home/bin/bob",
        "/home/joão/bin/bob",
    ],
)
def test_render_hook_is_the_ct10_text(raw: str) -> None:
    path = Path(raw)
    result = render_hook(path)

    assert result == _TEMPLATE.replace("<p>", str(path)).encode()
    assert b"\r" not in result


@pytest.mark.parametrize(
    "p",
    ['/a"b/bob', "/a$b/bob", "/a`b/bob", "/a\\b/bob", "/a\nb/bob", "bin/bob"],
)
def test_render_hook_rejects_paths_the_hook_cannot_quote(p: str) -> None:
    assert issubclass(HookPathError, ValueError)
    with pytest.raises(HookPathError) as caught:
        render_hook(Path(p))
    assert caught.value.args == (str(p),)


def test_hook_marker_is_line_2_of_the_template() -> None:
    assert render_hook(BOB).split(b"\n")[1] == HOOK_MARKER == b"# managed-by: bob-quality"


def test_static_hook_runs_the_same_command() -> None:
    static = STATIC.read_bytes().split(b"\n")
    template = render_hook(BOB).split(b"\n")
    head = [b"#!/bin/sh", b"set -e", b"unset PYTEST_ADDOPTS", b"unset PYTEST_PLUGINS"]
    positions = [template.index(line) for line in head]

    assert static[:4] == head
    assert positions == sorted(positions)
    static_last = [line for line in static if line][-1]
    template_last = [line for line in template if line][-1]
    assert static_last.replace(b"exec bob ", b'exec "$BOB" ') == template_last


def test_install_creates_the_hook(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    dest = repo / ".git" / "hooks" / "pre-push"

    result = install_hook(repo, BOB)

    assert result == HookResult("created", dest)
    assert result.hooks_path == ""
    assert dest.read_bytes() == render_hook(BOB)
    assert stat.S_IMODE(dest.stat().st_mode) == 0o755


def test_install_creates_the_hooks_folder_when_missing(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", "--template=", str(repo)], check=True)
    dest = repo / ".git" / "hooks" / "pre-push"

    result = install_hook(repo, BOB)

    assert result == HookResult("created", dest)
    assert dest.is_file()
    assert dest.read_bytes() == render_hook(BOB)


def test_install_is_unchanged_on_the_second_run(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    dest = repo / ".git" / "hooks" / "pre-push"
    install_hook(repo, BOB)
    data = dest.read_bytes()
    mtime = dest.stat().st_mtime_ns

    result = install_hook(repo, BOB)

    assert result == HookResult("unchanged", dest)
    assert dest.read_bytes() == data
    assert dest.stat().st_mtime_ns == mtime


@pytest.mark.parametrize("kind", ["content", "mode"])
def test_install_updates_a_bob_hook_that_differs(tmp_path: Path, kind: str) -> None:
    repo = _repo(tmp_path / "repo")
    dest = repo / ".git" / "hooks" / "pre-push"
    if kind == "content":
        dest.write_bytes(b"#!/bin/sh\n# managed-by: bob-quality\nexec bob check\n")
        dest.chmod(0o755)
    else:
        dest.write_bytes(render_hook(BOB))
        dest.chmod(0o644)

    result = install_hook(repo, BOB)

    assert result == HookResult("updated", dest)
    assert dest.read_bytes() == render_hook(BOB)
    assert stat.S_IMODE(dest.stat().st_mode) == 0o755


@pytest.mark.parametrize("content", _FOREIGN)
def test_install_preserves_a_foreign_hook(tmp_path: Path, content: bytes) -> None:
    repo = _repo(tmp_path / "repo")
    dest = repo / ".git" / "hooks" / "pre-push"
    dest.write_bytes(content)
    dest.chmod(0o700)

    result = install_hook(repo, BOB)

    assert result == HookResult("preserved", dest)
    assert dest.read_bytes() == content
    assert stat.S_IMODE(dest.stat().st_mode) == 0o700
    assert list(dest.parent.glob("pre-push.tmp-*")) == []


@pytest.mark.parametrize("kind", ["link", "folder"])
def test_install_never_follows_a_link_or_a_folder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    repo = _repo(tmp_path / "repo")
    dest = repo / ".git" / "hooks" / "pre-push"
    target = tmp_path / "alvo"
    payload = b"#!/bin/sh\n# managed-by: bob-quality\nold\n"
    if kind == "link":
        target.write_bytes(payload)
        dest.symlink_to(target)
    else:
        dest.mkdir()
    monkeypatch.setattr(Path, "read_bytes", _forbid_read)

    result = install_hook(repo, BOB)

    assert result == HookResult("preserved", dest)
    monkeypatch.undo()
    if kind == "link":
        assert dest.is_symlink()
        assert dest.resolve() == target.resolve()
        assert target.read_bytes() == payload
    else:
        assert dest.is_dir()
        assert list(dest.iterdir()) == []


@pytest.mark.parametrize("absolute", [False, True])
def test_install_respects_core_hooks_path(tmp_path: Path, absolute: bool) -> None:
    repo = _repo(tmp_path / "repo")
    value = str(tmp_path / "hooks-dev") if absolute else ".husky"
    subprocess.run(["git", "config", "core.hooksPath", value], cwd=repo, check=True)

    result = install_hook(repo, BOB)

    assert result == HookResult("preserved_hookspath", repo / value, value)
    assert not (repo / ".git" / "hooks" / "pre-push").exists()
    assert not (repo / value).exists()


def test_install_uses_the_common_hooks_of_a_worktree(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    subprocess.run(
        ["git", "commit", "-q", "--allow-empty", "-m", "init"],
        cwd=repo,
        check=True,
    )
    worktree = tmp_path / "wt"
    subprocess.run(
        ["git", "worktree", "add", "-q", str(worktree), "-b", "wt"],
        cwd=repo,
        check=True,
    )
    expected = repo / ".git" / "hooks" / "pre-push"

    result = install_hook(worktree, BOB)

    assert result.state == "created"
    assert result.path.resolve() == expected.resolve()
    assert expected.is_file()


@pytest.mark.parametrize("kind", ["missing", "config", "rev-parse"])
def test_git_errors_are_tool_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    repo = _repo(tmp_path / "repo")
    hooks = repo / ".git" / "hooks"
    calls = {"n": 0}

    def fake_run(
        args: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        if kind == "missing":
            raise FileNotFoundError
        if kind == "config":
            return subprocess.CompletedProcess(args, 3, "", "  fatal: x \n")
        calls["n"] += 1
        if calls["n"] == 1:
            return subprocess.CompletedProcess(args, 1, "", "")
        return subprocess.CompletedProcess(args, 128, "", "fatal: not a git repository\n")

    before = sorted(hooks.glob("pre-push*"))
    monkeypatch.setattr(hook_install.subprocess, "run", fake_run)
    with pytest.raises(ToolError) as exc:
        install_hook(repo, BOB)
    if kind == "missing":
        assert render(reason(exc.value), "en") == "missing tool: git"
    elif kind == "config":
        assert render(reason(exc.value), "en") == (
            "git config --get core.hooksPath failed: fatal: x"
        )
    else:
        assert render(reason(exc.value), "en") == (
            "git rev-parse --git-path hooks failed: fatal: not a git repository"
        )
    assert sorted(hooks.glob("pre-push*")) == before


def test_git_is_called_with_the_exact_arguments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _repo(tmp_path / "repo")
    seen: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(
        args: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        seen.append((list(args), kwargs))
        if len(seen) == 1:
            return subprocess.CompletedProcess(args, 1, "", "")
        return subprocess.CompletedProcess(args, 0, ".git/hooks\n", "")

    monkeypatch.setattr(hook_install.subprocess, "run", fake_run)
    install_hook(repo, BOB)
    kwargs = {"cwd": repo, "capture_output": True, "text": True, "check": False}

    assert seen == [
        (["git", "config", "--get", "core.hooksPath"], kwargs),
        (["git", "rev-parse", "--git-path", "hooks"], kwargs),
    ]


def test_bad_path_writes_nothing_and_calls_no_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _repo(tmp_path / "repo")

    def fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("git")

    monkeypatch.setattr(hook_install.subprocess, "run", fail)
    with pytest.raises(HookPathError):
        install_hook(repo, Path("/a$b/bob"))
    assert not (repo / ".git" / "hooks" / "pre-push").exists()


@pytest.mark.parametrize("target", ["write_bytes", "chmod", "replace"])
def test_write_error_leaves_no_temporary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    repo = _repo(tmp_path / "repo")
    hooks = repo / ".git" / "hooks"
    before = sorted(hooks.glob("pre-push*"))

    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError(28, "boom")

    if target == "write_bytes":
        monkeypatch.setattr(Path, "write_bytes", boom)
    elif target == "chmod":
        monkeypatch.setattr(hook_install.os, "chmod", boom)
    else:
        monkeypatch.setattr(hook_install.os, "replace", boom)
    with pytest.raises(OSError, match="boom"):
        install_hook(repo, BOB)
    assert sorted(hooks.glob("pre-push*")) == before


def test_temporary_is_next_to_the_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _repo(tmp_path / "repo")
    dest = repo / ".git" / "hooks" / "pre-push"
    seen: list[tuple[object, object]] = []
    real = hook_install.os.replace

    def wrapped(src: object, dst: object) -> None:
        seen.append((src, dst))
        real(src, dst)

    monkeypatch.setattr(hook_install.os, "replace", wrapped)
    install_hook(repo, BOB)

    assert seen == [(dest.with_name(f"pre-push.tmp-{os.getpid()}"), dest)]


@pytest.mark.parametrize(
    ("lang", "expected"),
    [
        ("en", "git rev-parse x failed: d"),
        ("pt-BR", "git rev-parse x falhou: d"),
    ],
)
def test_git_command_failed_message_in_both_languages(lang: str, expected: str) -> None:
    assert t(lang, "git.command_failed", command="rev-parse x", detail="d") == expected


def test_hooks_path_value_stops_at_the_first_newline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _repo(tmp_path / "repo")

    def fake_run(
        args: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, ".husky\nignored\n", "")

    monkeypatch.setattr(hook_install.subprocess, "run", fake_run)
    result = install_hook(repo, BOB)

    assert result == HookResult("preserved_hookspath", repo / ".husky", ".husky")
    assert not (repo / ".husky").exists()


def test_hooks_directory_stops_at_the_first_newline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _repo(tmp_path / "repo")
    calls = {"n": 0}

    def fake_run(
        args: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls["n"] += 1
        if calls["n"] == 1:
            return subprocess.CompletedProcess(args, 1, "", "")
        return subprocess.CompletedProcess(args, 0, ".git/hooks\nignored\n", "")

    monkeypatch.setattr(hook_install.subprocess, "run", fake_run)
    result = install_hook(repo, BOB)
    expected = repo / ".git" / "hooks" / "pre-push"

    assert result.state == "created"
    assert result.path.resolve() == expected.resolve()
    assert expected.is_file()
