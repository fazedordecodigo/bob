from __future__ import annotations

import re
from pathlib import Path

_LOAD = re.compile(r"\byaml\.(safe_|full_|unsafe_)?load(_all)?\(")


def test_only_yaml_text_parses_yaml_in_src() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "bob_quality"
    offenders = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if path.relative_to(root).as_posix() != "yaml_text.py"
        and _LOAD.search(path.read_text())
    )

    assert offenders == []
    assert _LOAD.search((root / "yaml_text.py").read_text())
