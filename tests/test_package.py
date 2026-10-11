"""Seam: sdist/wheel do `bob-quality` passam em `twine check` e o CI não publica."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sdist_and_wheel_pass_twine_check(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    build = subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(dist)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    artifacts = sorted(dist.iterdir())
    names = [path.name for path in artifacts]
    assert any(name.endswith(".tar.gz") for name in names)
    assert any(name.endswith(".whl") for name in names)

    check = subprocess.run(
        [sys.executable, "-m", "twine", "check", "--strict", *(str(path) for path in artifacts)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0, check.stdout + check.stderr


def test_package_workflow_checks_the_dist_and_does_not_publish() -> None:
    text = (ROOT / ".github" / "workflows" / "package.yml").read_text()
    assert "python -m build" in text
    assert "twine check --strict" in text
    for forbidden in (
        "twine upload",
        "pypa/gh-action-pypi-publish",
        "npm publish",
        "softprops/action-gh-release",
        "actions/create-release",
    ):
        assert forbidden not in text
