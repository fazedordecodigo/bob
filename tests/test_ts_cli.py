"""Comportamento da CLI `bob` sobre o repo-fixture TypeScript (seam principal)."""

import json
import os
import shutil
from pathlib import Path

from helpers import TS_RISKY_SOURCE, TS_SAFE_CHANGE, commit_on_branch, init_ts_repo, run_bob


def test_check_fails_when_changed_typescript_function_exceeds_crap_10(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "risky",
        "src/messy.ts",
        TS_RISKY_SOURCE,
        "add untested messy function",
    )

    result = run_bob(repo, "check", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert result.returncode == 1, result.stderr
    messy = next(item for item in payload["top_crap"] if item["name"] == "messy")
    assert messy["lang"] == "typescript"
    assert messy["cc"] == 4
    assert messy["coverage"] == 0.0
    assert messy["crap"] == 20.0
    assert messy["file"].endswith("src/messy.ts")


def test_check_passes_when_changed_typescript_function_stays_under_crap_10(
    tmp_path: Path,
) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "safe-change",
        "src/safe.ts",
        TS_SAFE_CHANGE,
        "touch tested add",
    )

    result = run_bob(repo, "check", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 0, result.stderr
    add = next(item for item in payload["top_crap"] if item["name"] == "add")
    assert add["lang"] == "typescript"
    assert add["cc"] == 1
    assert add["coverage"] == 1.0
    assert add["crap"] == 1.0
    assert payload["tool_versions"]["c8"] == "12.0.0"
    assert payload["tool_versions"]["vitest"] == "5.0.4"
    assert "src/safe.ts" in markdown


def test_check_measures_a_covered_function_outside_bob_yaml_exclude(tmp_path: Path) -> None:
    """O c8 segue `paths.exclude` do bob.yaml.

    `dist/` está na lista fixa antiga e fora desta config. A função coberta
    entra com a cobertura dos testes.
    """
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "kept",
        "dist/kept.ts",
        TS_RISKY_SOURCE,
        "add covered function under dist",
    )
    (repo / "bob.yaml").write_text(
        "\n".join(
            [
                "base: main",
                "languages: [typescript]",
                "paths:",
                "  include: [dist]",
                "  exclude: [tests]",
                "crap:",
                "  max_per_function: 10",
                "  scope: changed",
                "",
            ]
        )
    )
    (repo / "tests" / "kept.test.ts").write_text(
        "\n".join(
            [
                'import { expect, test } from "vitest";',
                'import { messy } from "../dist/kept";',
                "",
                'test("messy", () => {',
                "  expect(messy(true, true, false)).toBe(1);",
                "  expect(messy(true, false, false)).toBe(2);",
                "  expect(messy(false, false, true)).toBe(3);",
                "  expect(messy(false, false, false)).toBe(0);",
                "});",
                "",
            ]
        )
    )

    result = run_bob(repo, "check", "--base", "main", "--gates", "crap")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    messy = next(item for item in payload["top_crap"] if item["name"] == "messy")

    assert result.returncode == 0, result.stderr
    assert messy["cc"] == 4
    assert messy["coverage"] == 1.0
    assert messy["crap"] == 4.0
    assert messy["file"].endswith("dist/kept.ts")


def test_omitted_paths_exclude_defaults_to_tests_node_modules_and_dist(
    tmp_path: Path,
) -> None:
    """Sem `paths.exclude`, o padrão da spec tira tests, node_modules e dist.

    Uma função alterada em `src/` continua medida.
    """
    repo = init_ts_repo(tmp_path / "repo")
    (repo / "bob.yaml").write_text(
        "\n".join(
            [
                "base: main",
                "languages: [typescript]",
                "paths:",
                "  include: [src, dist, node_modules, tests]",
                "crap:",
                "  max_per_function: 10",
                "  scope: changed",
                "",
            ]
        )
    )
    commit_on_branch(repo, "default-exclude", "src/safe.ts", TS_SAFE_CHANGE, "touch tested add")
    commit_on_branch(
        repo, "default-exclude", "dist/kept.ts", TS_RISKY_SOURCE, "add untested function under dist"
    )
    commit_on_branch(
        repo,
        "default-exclude",
        "node_modules/pkg/old.ts",
        TS_RISKY_SOURCE,
        "add untested function under node_modules",
    )
    commit_on_branch(
        repo,
        "default-exclude",
        "tests/extra.ts",
        TS_RISKY_SOURCE,
        "add untested function under tests",
    )

    result = run_bob(repo, "check", "--base", "main", "--gates", "crap")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    names = {item["name"] for item in payload["top_crap"]}
    files = {item["file"] for item in payload["top_crap"]}

    assert result.returncode == 0, result.stderr
    assert names == {"add"}
    assert any(path.endswith("src/safe.ts") for path in files)
    assert not any(path.startswith(("dist/", "node_modules/", "tests/")) for path in files)


def test_check_exits_4_with_a_clear_message_when_node_is_missing(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "safe-change",
        "src/safe.ts",
        TS_SAFE_CHANGE,
        "touch tested add",
    )
    bindir = tmp_path / "bin"
    bindir.mkdir()
    os.symlink(shutil.which("git"), bindir / "git")
    env = {**os.environ, "PATH": str(bindir)}

    result = run_bob(repo, "check", "--base", "main", "--gates", "crap", env=env)
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    crap = next(gate for gate in payload["gates"] if gate["name"] == "crap")

    assert result.returncode == 4, result.stderr
    assert crap["status"] == "not_run"
    assert crap["reason"]
    assert "Node missing" in crap["reason"]
    assert "Node missing" in markdown
    assert "✅ `crap`" not in markdown


def test_check_exits_2_when_typescript_baseline_tests_fail(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "broken",
        "tests/safe.test.ts",
        "\n".join(
            [
                'import { expect, test } from "vitest";',
                'import { add } from "../src/safe";',
                "",
                'test("add", () => {',
                "  expect(add(1, 2)).toBe(0);",
                "});",
                "",
            ]
        ),
        "break baseline tests",
    )

    result = run_bob(repo, "check", "--base", "main", "--gates", "crap")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    crap = next(gate for gate in payload["gates"] if gate["name"] == "crap")

    assert result.returncode == 2, result.stderr
    assert crap["status"] == "not_run"
    assert crap["reason"]
