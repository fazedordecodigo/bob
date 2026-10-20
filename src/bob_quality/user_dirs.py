"""Pastas do usuário do bob (CT5, CT6)."""

from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BobHome:
    root: Path
    versions: Path
    current: Path
    bin: Path
    bin_bob: Path
    tools: Path


def bob_home(env: Mapping[str, str] = os.environ) -> BobHome:
    """BOB_HOME, senão XDG_DATA_HOME/bob-quality, senão HOME/.local/share/bob-quality."""
    chosen = env.get("BOB_HOME") or ""
    if chosen:
        if not chosen.startswith("/"):
            raise ValueError(chosen)
        root = Path(chosen)
    else:
        data_home = env.get("XDG_DATA_HOME")
        if isinstance(data_home, str) and data_home.startswith("/"):
            root = Path(data_home) / "bob-quality"
        else:
            home = env.get("HOME") or Path.home()
            root = Path(home) / ".local" / "share" / "bob-quality"
    return BobHome(
        root=root,
        versions=root / "versions",
        current=root / "current",
        bin=root / "bin",
        bin_bob=root / "bin" / "bob",
        tools=root / "tools",
    )


def locate_binary(name: str, env: Mapping[str, str] = os.environ) -> str | None:
    """BOB_HOME/bin/<name> se for arquivo executável, senão o PATH (CT8, ADR 0019)."""
    try:
        home = bob_home(env)
    except ValueError:
        return shutil.which(name)
    candidate = home.bin / name
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    return shutil.which(name)
