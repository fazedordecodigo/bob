"""Seam: sdist/wheel do `bob-quality` passam em `twine check` e o CI não publica."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
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


def test_wheel_ships_npm_manifest_and_install_can_find_it(tmp_path: Path) -> None:
    """Uma instalação pip comum carrega o package.json das ferramentas npm."""
    dist = tmp_path / "dist"
    build = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    wheel = next(dist.glob("*.whl"))
    root_manifest = json.loads((ROOT / "package.json").read_text())
    with zipfile.ZipFile(wheel) as archive:
        packaged = json.loads(archive.read("bob_quality/package.json"))
    assert packaged["dependencies"] == root_manifest["dependencies"]

    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    pip = venv / "bin" / "pip"
    python = venv / "bin" / "python"
    install = subprocess.run(
        [str(pip), "install", "--no-deps", str(wheel)],
        capture_output=True,
        text=True,
    )
    assert install.returncode == 0, install.stdout + install.stderr
    probe = tmp_path / "probe.py"
    probe.write_text(
        "from bob_quality.npm_tools import npm_prefix\n"
        "print(npm_prefix() / 'package.json')\n"
    )
    found = subprocess.run(
        [str(python), str(probe)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert found.returncode == 0, found.stdout + found.stderr
    installed = Path(found.stdout.strip())
    assert installed.is_file()
    assert "site-packages" in str(installed)
    assert json.loads(installed.read_text())["dependencies"] == root_manifest["dependencies"]


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
