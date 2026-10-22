"""Hook pre-push gerenciado pelo bob (CT10, ADR 0016)."""

from __future__ import annotations

import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from bob_quality.messages import msg
from bob_quality.tools import ToolError

HOOK_MARKER = b"# managed-by: bob-quality"
HookState = Literal["created", "updated", "unchanged", "preserved", "preserved_hookspath"]
_MODE = 0o755
_UNSAFE = (b'"', b"$", b"`", b"\\", b"\n")


class HookPathError(ValueError):
    pass


@dataclass(frozen=True)
class HookResult:
    state: HookState
    path: Path
    hooks_path: str = ""


def render_hook(bob_bin: Path) -> bytes:
    if not bob_bin.is_absolute():
        raise HookPathError(str(bob_bin))
    raw = os.fsencode(str(bob_bin))
    _reject_unsafe(raw, bob_bin)
    return _template(raw)


def install_hook(project: Path, bob_bin: Path) -> HookResult:
    text = render_hook(bob_bin)
    hooks_path = _configured_hooks_path(project)
    if hooks_path is not None:
        return HookResult("preserved_hookspath", project / hooks_path, hooks_path)
    return _install_at(_hook_destination(project), text)


def _reject_unsafe(raw: bytes, bob_bin: Path) -> None:
    for item in _UNSAFE:
        if item in raw:
            raise HookPathError(str(bob_bin))


def _template(raw: bytes) -> bytes:
    return b"".join(
        (
            b"#!/bin/sh\n",
            HOOK_MARKER + b"\n",
            b"set -e\n",
            b"unset PYTEST_ADDOPTS\n",
            b"unset PYTEST_PLUGINS\n",
            b'BOB="' + raw + b'"\n',
            b'[ -x "$BOB" ] || BOB=bob\n',
            b'exec "$BOB" check --gates crap,dry,deps </dev/null\n',
        )
    )


def _configured_hooks_path(project: Path) -> str | None:
    completed = _git(project, "config", "--get", "core.hooksPath")
    if completed.returncode == 0:
        return completed.stdout.partition("\n")[0]
    if completed.returncode != 1:
        raise ToolError(
            msg(
                "git.command_failed",
                command="config --get core.hooksPath",
                detail=completed.stderr.strip(),
            )
        )
    return None


def _hook_destination(project: Path) -> Path:
    completed = _git(project, "rev-parse", "--git-path", "hooks")
    if completed.returncode != 0:
        raise ToolError(
            msg(
                "git.command_failed",
                command="rev-parse --git-path hooks",
                detail=completed.stderr.strip(),
            )
        )
    relative = completed.stdout.partition("\n")[0]
    return project / relative / "pre-push"


def _install_at(dest: Path, text: bytes) -> HookResult:
    if _preserved(dest):
        return HookResult("preserved", dest)
    if not dest.exists():
        dest.parent.mkdir(exist_ok=True)
        _write(dest, text)
        return HookResult("created", dest)
    if _current(dest, text):
        return HookResult("unchanged", dest)
    _write(dest, text)
    return HookResult("updated", dest)


def _preserved(dest: Path) -> bool:
    if dest.is_symlink():
        return True
    if dest.exists() and not dest.is_file():
        return True
    if not dest.is_file():
        return False
    return dest.read_bytes().split(b"\n")[1:2] != [HOOK_MARKER]


def _current(dest: Path, text: bytes) -> bool:
    if dest.read_bytes() != text:
        return False
    return stat.S_IMODE(dest.stat().st_mode) == _MODE


def _write(dest: Path, text: bytes) -> None:
    tmp = dest.with_name(f"pre-push.tmp-{os.getpid()}")
    try:
        tmp.write_bytes(text)
        os.chmod(tmp, _MODE)
        os.replace(tmp, dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _git(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise ToolError(msg("tool.missing", tool="git")) from exc
