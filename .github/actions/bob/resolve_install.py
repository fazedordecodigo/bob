"""Decide o requisito pip: checkout do bob, spec explícito ou git da action."""

from __future__ import annotations

import os
import sys
from pathlib import Path

DEFAULT_REPO = "fazedordecodigo/bob"
DEFAULT_REF = "main"


def project_name(text: str) -> str | None:
    in_project = False
    for line in text.splitlines():
        stripped = line.split("#", 1)[0].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_project = stripped == "[project]"
            continue
        if not in_project:
            continue
        key, sep, raw = stripped.partition("=")
        if sep and key.strip() == "name":
            return raw.strip().strip('"').strip("'")
    return None


def pip_requirement(
    explicit: str,
    project: str | None,
    action_repo: str,
    action_ref: str,
) -> str:
    if explicit.strip():
        return explicit.strip()
    if project == "bob-quality":
        return ".[dev]"
    repo = action_repo.strip() or DEFAULT_REPO
    ref = action_ref.strip() or DEFAULT_REF
    return f"bob-quality[dev] @ git+https://github.com/{repo}.git@{ref}"


def main() -> int:
    pyproject = Path("pyproject.toml")
    project = project_name(pyproject.read_text(encoding="utf-8")) if pyproject.is_file() else None
    spec = pip_requirement(
        os.environ.get("BOB_PIP_SPEC", ""),
        project,
        os.environ.get("GITHUB_ACTION_REPOSITORY", ""),
        os.environ.get("GITHUB_ACTION_REF", ""),
    )
    print(spec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
