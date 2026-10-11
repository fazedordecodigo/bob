"""De onde a Action instala o bob: checkout local ou git da própria action."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOLVE = ROOT / ".github" / "actions" / "bob" / "resolve_install.py"


def _resolve(cwd: Path, **env: str) -> subprocess.CompletedProcess[str]:
    clean = os.environ.copy()
    for key in ("BOB_PIP_SPEC", "GITHUB_ACTION_REPOSITORY", "GITHUB_ACTION_REF"):
        clean.pop(key, None)
    clean.update(env)
    return subprocess.run(
        [sys.executable, str(RESOLVE)],
        cwd=cwd,
        env=clean,
        capture_output=True,
        text=True,
        check=False,
    )


def test_bob_checkout_installs_the_local_project_with_dev_extras(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "bob-quality"\n')

    result = _resolve(tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ".[dev]"


def test_explicit_pip_spec_wins_over_the_checkout(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "bob-quality"\n')

    result = _resolve(tmp_path, BOB_PIP_SPEC="bob-quality==0.1.0")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "bob-quality==0.1.0"


def test_other_repository_installs_bob_from_the_action_git_ref(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "loja"\n')

    result = _resolve(
        tmp_path,
        GITHUB_ACTION_REPOSITORY="fazedordecodigo/bob",
        GITHUB_ACTION_REF="abc123",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == (
        "bob-quality[dev] @ git+https://github.com/fazedordecodigo/bob.git@abc123"
    )


def test_dependency_mention_does_not_count_as_the_bob_checkout(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "loja"\ndependencies = ["bob-quality"]\n'
    )

    result = _resolve(
        tmp_path,
        GITHUB_ACTION_REPOSITORY="fazedordecodigo/bob",
        GITHUB_ACTION_REF="abc123",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().startswith("bob-quality[dev] @ git+")


def test_without_action_coordinates_defaults_to_this_repo_main(tmp_path: Path) -> None:
    result = _resolve(tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == (
        "bob-quality[dev] @ git+https://github.com/fazedordecodigo/bob.git@main"
    )
