"""Stryker de verdade no fixture TypeScript.

O teste que mata fica dentro de describe. Um test("add") no topo não
trava o stryker-js#6210: o Vitest 5 casa o nome com ' > '.
"""

from __future__ import annotations

import json
from pathlib import Path

from helpers import commit_on_branch, init_ts_repo, run_bob_subprocess

_SAFE = """\
export function add(left: number, right: number): number {
  return left + right;
}

export function label(value: number): string {
  if (value > 0) {
    return "pos";
  }
  return "neg";
}
"""

_NESTED = """\
import { describe, expect, test } from "vitest";
import { add, label } from "../src/safe";

describe("safe", () => {
  test("add", () => {
    expect(add(1, 2)).toBe(3);
  });

  test("label", () => {
    expect(label(1)).toBe("pos");
  });
});
"""

_ORPHAN_FILE = """\
export function add(left: number, right: number): number {
  return left + right;
}

export function orphan(value: number): number {
  return value + 1;
}
"""


def _mutants(repo: Path, suffix: str) -> list[dict[str, object]]:
    report = json.loads((repo / ".bob" / "stryker-report.json").read_text())
    matches = [
        value["mutants"]
        for key, value in report["files"].items()
        if str(key).replace("\\", "/").endswith(suffix)
    ]
    assert len(matches) == 1
    return matches[0]


def test_nested_describe_kills_add_and_an_unwaived_survivor_exits_3(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(repo, "change", "src/safe.ts", _SAFE, "add label")
    commit_on_branch(repo, "change", "tests/safe.test.ts", _NESTED, "nest the killer")

    result = run_bob_subprocess(repo, "mutate", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    mutate = next(gate for gate in payload["gates"] if gate["name"] == "mutate")
    mutants = _mutants(repo, "src/safe.ts")
    killed = [
        item
        for item in mutants
        if item["status"] == "Killed" and item["location"]["start"]["line"] == 2
    ]

    assert result.returncode == 3, result.stdout + result.stderr + (repo / ".bob" / "report.md").read_text()
    assert mutate["status"] == "failed"
    assert killed
    assert killed[0]["testsCompleted"] > 0
    assert any(item["status"] == "Survived" for item in mutants)
    assert any(item["function"] == "label" for item in payload["survivors"])
    assert not any(item["function"] == "add" for item in payload["survivors"])


def test_an_uncovered_changed_function_exits_3(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(repo, "orphan", "src/safe.ts", _ORPHAN_FILE, "add orphan")

    result = run_bob_subprocess(repo, "mutate", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    mutate = next(gate for gate in payload["gates"] if gate["name"] == "mutate")

    assert result.returncode == 3, result.stdout + result.stderr + (repo / ".bob" / "report.md").read_text()
    assert mutate == {
        "name": "mutate",
        "status": "failed",
        "reason": "2 mutants without a test",
    }
    assert payload["mutation"]["no_coverage"] == {
        "total": 2,
        "functions": [{"file": "src/safe.ts", "function": "orphan", "count": 2}],
    }
