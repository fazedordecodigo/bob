"""`languages` omitido segue os arquivos do repositório, não a tupla padrão."""

import json
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from bob_quality.config import ConfigError, load_config
from bob_quality.messages import reason, render
from helpers import commit_on_branch, run_bob

_NODE = "Node missing: install Node.js to measure TypeScript (c8 and vitest via npx)"
_SKIP = f"TypeScript skipped: {_NODE}"
_PY = "def add(left: int, right: int) -> int:\n    return left + right\n"
_TS = "export function add(left: number): number {\n  return left;\n}\n"
_JS = "export function add(left) {\n  return left;\n}\n"
_PLACEHOLDER = "def test_keeps_the_suite_green() -> None:\n    assert True\n"


def test_python_file_selects_python(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.py", _PY)

    assert load_config(None, tmp_path).languages == ("python",)


@pytest.mark.parametrize("name", ["app.ts", "app.tsx", "app.js", "app.jsx", "app.mjs", "app.cjs"])
def test_script_suffix_selects_typescript(tmp_path: Path, name: str) -> None:
    _write(tmp_path, f"src/{name}", "export const value = 1;\n")

    assert load_config(None, tmp_path).languages == ("typescript",)


def test_detected_order_is_python_then_typescript(tmp_path: Path) -> None:
    _write(tmp_path, "pkg_ts/app.ts", _TS)
    _write(tmp_path, "pkg_py/app.py", _PY)
    _yaml(tmp_path, "paths:\n  include: [pkg_ts, pkg_py]\n")

    assert load_config(None, tmp_path).languages == ("python", "typescript")


def test_default_exclude_skips_vendored_and_test_trees(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.py", _PY)
    _write(tmp_path, "src/node_modules/index.js", _JS)
    _write(tmp_path, "src/tests/app.ts", _TS)
    _write(tmp_path, "tests/app.tsx", _TS)
    _write(tmp_path, "src/dist/app.mjs", _JS)

    assert load_config(None, tmp_path).languages == ("python",)


def test_source_outside_include_is_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.py", _PY)
    _write(tmp_path, "lib/app.ts", _TS)

    assert load_config(None, tmp_path).languages == ("python",)


def test_custom_include_sees_that_tree(tmp_path: Path) -> None:
    _write(tmp_path, "pkg/app.ts", _TS)
    _write(tmp_path, "src/app.py", _PY)
    _yaml(tmp_path, "paths:\n  include: [pkg]\n")

    assert load_config(None, tmp_path).languages == ("typescript",)


def test_null_languages_is_detected(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.ts", _TS)
    _yaml(tmp_path, "languages: null\n")

    assert load_config(None, tmp_path).languages == ("typescript",)


def test_missing_bob_yaml_is_detected(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.ts", _TS)

    assert load_config(None, tmp_path).languages == ("typescript",)


def test_explicit_list_wins_over_the_tree(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.ts", _TS)
    _yaml(tmp_path, "languages: [python]\n")

    assert load_config(None, tmp_path).languages == ("python",)


def test_explicit_list_keeps_file_order(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.py", _PY)
    _yaml(tmp_path, "languages: [typescript, python]\n")

    assert load_config(None, tmp_path).languages == ("typescript", "python")


def test_readme_only_stays_python(tmp_path: Path) -> None:
    _write(tmp_path, "src/README.md", "notes\n")

    assert load_config(None, tmp_path).languages == ("python",)


def test_empty_languages_list_still_exits_4(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.ts", _TS)
    _yaml(tmp_path, "languages: []\n")

    with pytest.raises(ConfigError) as raised:
        load_config(None, tmp_path)

    assert render(reason(raised.value), "en") == "bob.yaml: languages must not be empty"


def test_exclude_prefix_drops_a_nested_file(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.py", _PY)
    _write(tmp_path, "src/vendor/app.ts", _TS)
    _yaml(
        tmp_path,
        "paths:\n  include: [src/app.py, src/vendor/app.ts]\n  exclude: [src/vendor]\n",
    )

    assert load_config(None, tmp_path).languages == ("python",)


def test_exclude_entry_ignores_wrapping_slashes(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.py", _PY)
    _write(tmp_path, "src/vendor/app.ts", _TS)
    _yaml(tmp_path, 'paths:\n  exclude: ["/src/vendor/"]\n')

    assert load_config(None, tmp_path).languages == ("python",)


def test_exclude_entry_strips_slashes_only(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.py", _PY)
    _write(tmp_path, "src/vendor/app.ts", _TS)
    _yaml(tmp_path, "paths:\n  exclude: [Xsrc/vendor]\n")

    assert load_config(None, tmp_path).languages == ("python", "typescript")


def test_exclude_matches_an_exact_file(tmp_path: Path) -> None:
    _write(tmp_path, "src/keep.py", _PY)
    _write(tmp_path, "src/skip.ts", _TS)
    _yaml(tmp_path, "paths:\n  exclude: [src/skip.ts]\n")

    assert load_config(None, tmp_path).languages == ("python",)


def test_missing_include_root_is_skipped(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.py", _PY)
    _yaml(tmp_path, "paths:\n  include: [missing, src]\n")

    assert load_config(None, tmp_path).languages == ("python",)


def test_include_can_be_a_file(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.ts", _TS)
    _write(tmp_path, "src/app.py", _PY)
    _yaml(tmp_path, "paths:\n  include: [src/app.ts]\n")

    assert load_config(None, tmp_path).languages == ("typescript",)


def test_absolute_include_outside_the_checkout_is_detected(tmp_path: Path) -> None:
    outside = tmp_path / "pkg"
    _write(outside, "app.ts", _TS)
    repo = tmp_path / "repo"
    repo.mkdir()
    _yaml(repo, f"paths:\n  include: [{outside.as_posix()}]\n")

    assert load_config(None, repo).languages == ("typescript",)


def test_absolute_include_under_node_modules_stays_python(tmp_path: Path) -> None:
    outside = tmp_path / "node_modules"
    _write(outside, "app.ts", _TS)
    repo = tmp_path / "repo"
    repo.mkdir()
    _yaml(repo, f"paths:\n  include: [{outside.as_posix()}]\n")

    assert load_config(None, repo).languages == ("python",)


def test_typescript_only_without_node_exits_4(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    commit_on_branch(repo, "change", "src/app.ts", _TS, "add typescript")

    result, payload = _check_without_node(repo, tmp_path)
    crap = _gate(payload, "crap")

    assert result.returncode == 4, result.stderr
    assert crap["status"] == "not_run"
    assert crap["reason"] == _NODE
    assert "TypeScript skipped" not in crap["reason"]


def test_javascript_only_without_node_exits_4(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    commit_on_branch(repo, "change", "src/index.js", _JS, "add javascript")

    result, payload = _check_without_node(repo, tmp_path)
    crap = _gate(payload, "crap")

    assert result.returncode == 4, result.stderr
    assert crap["status"] == "not_run"
    assert crap["reason"] == _NODE


def test_mixed_tree_without_node_measures_python_and_skips_typescript(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    commit_on_branch(repo, "change", "src/app.py", _PY, "add python")
    commit_on_branch(repo, "change", "src/app.ts", _TS, "add typescript")
    commit_on_branch(repo, "change", "tests/test_placeholder.py", _PLACEHOLDER, "add test")

    result, payload = _check_without_node(repo, tmp_path)
    crap = _gate(payload, "crap")
    langs = {item["lang"] for item in payload["top_crap"]}

    assert result.returncode == 0, result.stderr
    assert crap["status"] == "warn"
    assert crap["reason"] == _SKIP
    assert langs == {"python"}


def test_explicit_python_ignores_typescript_when_node_is_missing(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    _yaml(repo, "languages: [python]\n")
    commit_on_branch(repo, "change", "src/app.py", _PY, "add python")
    commit_on_branch(repo, "change", "src/app.ts", _TS, "add typescript")
    commit_on_branch(repo, "change", "tests/test_placeholder.py", _PLACEHOLDER, "add test")

    result, payload = _check_without_node(repo, tmp_path)
    crap = _gate(payload, "crap")

    assert result.returncode == 0, result.stderr
    assert "TypeScript" not in (crap["reason"] or "")
    assert "Node missing" not in (crap["reason"] or "")


def test_directory_symlink_does_not_select_typescript(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    _write(outside, "app.ts", _TS)
    repo = tmp_path / "repo"
    _write(repo, "src/app.py", _PY)
    (repo / "src" / "vendor").symlink_to(outside, target_is_directory=True)

    assert load_config(None, repo).languages == ("python",)


def test_file_symlink_does_not_select_typescript(tmp_path: Path) -> None:
    target = tmp_path / "app.ts"
    target.write_text(_TS)
    repo = tmp_path / "repo"
    _write(repo, "src/app.py", _PY)
    (repo / "src" / "app.ts").symlink_to(target)

    assert load_config(None, repo).languages == ("python",)


def test_symlink_cycle_stays_python(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.py", _PY)
    (tmp_path / "src" / "loop").symlink_to(tmp_path / "src", target_is_directory=True)

    def _expire(_signum: int, _frame: object) -> None:
        raise AssertionError("symlink cycle did not finish")

    previous = signal.signal(signal.SIGALRM, _expire)
    signal.setitimer(signal.ITIMER_REAL, 2)
    try:
        assert load_config(None, tmp_path).languages == ("python",)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def test_exclude_glob_does_not_drop_python(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.py", _PY)
    _write(tmp_path, "src/app.ts", _TS)
    _yaml(tmp_path, 'paths:\n  exclude: ["*.py"]\n')

    assert load_config(None, tmp_path).languages == ("python", "typescript")


def test_missing_config_still_exits_4_when_the_tree_has_typescript(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/app.ts", _TS)

    result = run_bob(repo, "check", "--config", "missing.yaml", "--lang", "pt-BR")

    assert result.returncode == 4
    assert result.stdout == ""
    assert result.stderr == f"config file not found: {repo / 'missing.yaml'}\n"
    assert not (repo / ".bob").exists()


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _yaml(root: Path, text: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "bob.yaml").write_text(text)


def _repo(dest: Path) -> Path:
    dest.mkdir()
    _git(dest, "init", "-b", "main")
    _git(dest, "config", "user.email", "bob-test@example.com")
    _git(dest, "config", "user.name", "bob-test")
    _git(dest, "commit", "--allow-empty", "-m", "base")
    return dest


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )


def _check_without_node(
    repo: Path, tmp_path: Path
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    git = shutil.which("git")
    assert git is not None
    os.symlink(git, bindir / "git")
    env = {key: value for key, value in os.environ.items() if key != "BOB_LANG"}
    env["PATH"] = str(bindir)
    result = subprocess.run(
        [sys.executable, "-m", "bob_quality", "check", "--base", "main", "--gates", "crap"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    return result, payload


def _gate(payload: dict[str, object], name: str) -> dict[str, object]:
    gates = payload["gates"]
    assert isinstance(gates, list)
    found = next(gate for gate in gates if gate["name"] == name)
    assert isinstance(found, dict)
    return found
