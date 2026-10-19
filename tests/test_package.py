"""Seam: sdist/wheel do `bob-quality` passam em `twine check` e o CI não publica."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _skip_under_mutmut() -> None:
    if os.environ.get("MUTANT_UNDER_TEST") or os.environ.get("BOB_SKIP_MUTMUT_DOGFOOD"):
        pytest.skip("o build do wheel não participa da execução do mutmut")
    if os.environ.get("BOB_COVERAGE_RC"):
        pytest.skip("o build do wheel leva minutos sob o coverage do gate CRAP")


def test_sdist_and_wheel_pass_twine_check(tmp_path: Path) -> None:
    _skip_under_mutmut()
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
    _skip_under_mutmut()
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


def test_wheel_ships_the_plugin_skills_manifest_and_license(tmp_path: Path) -> None:
    _skip_under_mutmut()
    dist = tmp_path / "dist"
    build = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    wheel = next(dist.glob("*.whl"))
    manifest_path = ROOT / ".claude-plugin" / "plugin.json"
    entries = json.loads(manifest_path.read_text())["skills"]
    listed = subprocess.run(
        ["git", "ls-files", "skills"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    folders = [entry.removeprefix("./") for entry in entries]
    expected: set[str] = set()
    for line in listed.stdout.splitlines():
        path = ROOT / line
        if path.is_symlink() or not path.is_file():
            continue
        matched = any(
            line == folder or line.startswith(folder + "/") for folder in folders
        )
        if matched:
            expected.add(line.removeprefix("skills/"))
    with zipfile.ZipFile(wheel) as archive:
        packaged_manifest = "bob_quality/plugin/.claude-plugin/plugin.json"
        assert archive.read(packaged_manifest) == manifest_path.read_bytes()
        license_path = "bob_quality/plugin/LICENSE"
        assert archive.read(license_path) == (ROOT / "LICENSE").read_bytes()
        prefix = "bob_quality/plugin/skills/"
        names = {
            name.removeprefix(prefix)
            for name in archive.namelist()
            if name.startswith(prefix) and not name.endswith("/")
        }
        assert names == expected
        for entry in entries:
            relative = entry.removeprefix("./")
            packaged = f"bob_quality/plugin/{relative}/SKILL.md"
            assert archive.read(packaged) == (ROOT / relative / "SKILL.md").read_bytes()


def test_installed_wheel_installs_agents_skills_without_a_clone(tmp_path: Path) -> None:
    _skip_under_mutmut()
    dist = tmp_path / "dist"
    build = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    wheel = next(dist.glob("*.whl"))
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
    project = tmp_path / "proj"
    project.mkdir()
    result = subprocess.run(
        [
            str(python),
            "-m",
            "bob_quality.install_skills",
            "--project",
            str(project),
            "agents",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "3 skills em .agents/skills\n"
    agents = project / ".agents"
    for name in ("bob-check", "harden", "review-report"):
        skill = agents / "skills" / name
        assert (skill / "SKILL.md").is_file()
        assert (skill / "LICENSE").is_file()
    assert not agents.is_symlink()
    assert not any(path.is_symlink() for path in agents.rglob("*"))


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
