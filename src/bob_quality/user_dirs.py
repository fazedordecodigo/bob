"""Pastas do usuário do bob (CT5, CT6)."""

from __future__ import annotations

import os
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
        data_home = env.get("XDG_DATA_HOME") or ""
        if data_home.startswith("/"):
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
