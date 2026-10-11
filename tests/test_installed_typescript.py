"""Seam: wheel instalado sem editable mede o fixture TypeScript."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

from helpers import TS_RISKY_SOURCE, TS_SAFE_CHANGE, commit_on_branch, init_ts_repo

ROOT = Path(__file__).resolve().parents[1]
_NPM_CI = re.compile(r"npm ci --prefix ([^)\s]+)")


def test_installed_wheel_checks_typescript_after_doctor_install(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    build = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    wheel = next(dist.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
    assert "bob_quality/js/flush-coverage.mjs" in names

    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    pip = venv / "bin" / "pip"
    bob = venv / "bin" / "bob"
    install = subprocess.run(
        [str(pip), "install", str(wheel)],
        capture_output=True,
        text=True,
    )
    assert install.returncode == 0, install.stdout + install.stderr
    env = os.environ.copy()
    env["HOME"] = str(tmp_path / "home")
    env["XDG_CACHE_HOME"] = str(tmp_path / "cache")
    env.pop("PYTHONPATH", None)

    failing = init_ts_repo(tmp_path / "failing")
    commit_on_branch(failing, "risky", "src/messy.ts", TS_RISKY_SOURCE, "add untested messy")
    before = _bob(bob, env, failing, "check", "--base", "main", "--gates", "crap")
    report = (failing / ".bob" / "report.md").read_text() if (failing / ".bob" / "report.md").is_file() else ""
    shown = before.stdout + before.stderr + report
    assert before.returncode == 4, shown
    prefix = _npm_ci_prefix(shown)
    assert (prefix / "package.json").is_file()
    assert "site-packages" in str(prefix)

    installed = _bob(bob, env, failing, "doctor", "--install")
    assert installed.returncode == 0, installed.stdout + installed.stderr

    failed = _bob(bob, env, failing, "check", "--base", "main", "--gates", "crap")
    assert failed.returncode == 1, failed.stdout + failed.stderr

    passing = init_ts_repo(tmp_path / "passing")
    commit_on_branch(passing, "safe", "src/safe.ts", TS_SAFE_CHANGE, "touch tested add")
    passed = _bob(bob, env, passing, "check", "--base", "main", "--gates", "crap")
    assert passed.returncode == 0, passed.stdout + passed.stderr


def test_doctor_install_uses_user_cache_when_package_dir_is_not_writable(tmp_path: Path) -> None:
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
    bob = venv / "bin" / "bob"
    install = subprocess.run([str(pip), "install", str(wheel)], capture_output=True, text=True)
    assert install.returncode == 0, install.stdout + install.stderr
    package_dir = Path(
        subprocess.run(
            [str(python), "-c", "import bob_quality, pathlib; print(pathlib.Path(bob_quality.__file__).parent)"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    package_dir.chmod(0o555)
    env = os.environ.copy()
    env["HOME"] = str(tmp_path / "home")
    env["XDG_CACHE_HOME"] = str(tmp_path / "cache")
    env.pop("PYTHONPATH", None)
    try:
        result = _bob(bob, env, tmp_path, "doctor", "--install")
        assert result.returncode == 0, result.stdout + result.stderr
        cache = Path(env["XDG_CACHE_HOME"]) / "bob-quality"
        assert (cache / "node_modules" / "vitest" / "package.json").is_file()
        assert (cache / "js" / "flush-coverage.mjs").is_file()
        located = subprocess.run(
            [str(python), "-c", "from bob_quality.npm_tools import npm_prefix; print(npm_prefix())"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert Path(located.stdout.strip()) == cache
    finally:
        package_dir.chmod(0o755)


def _bob(bob: Path, env: dict[str, str], repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(bob), *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


def _npm_ci_prefix(text: str) -> Path:
    match = _NPM_CI.search(text)
    assert match, text
    return Path(match.group(1))
