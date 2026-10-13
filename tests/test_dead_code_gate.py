from __future__ import annotations

import importlib.metadata
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from vulture.config import DEFAULTS

from bob_quality.check import DEFAULT_GATES, run_check
from bob_quality.npm_tools import npm_prefix
from helpers import run_bob

ROOT = Path(__file__).resolve().parents[1]
ORPHAN = "def orphan():\n    return 1\n"
KEEP = "def keep():\n    return 1\n\n\nkeep()\n"


def test_pinned_vulture_default_confidence_is_zero() -> None:
    assert DEFAULTS["min_confidence"] == 0


def test_dead_code_stays_out_of_the_default_lists() -> None:
    hook = (ROOT / "src" / "bob_quality" / "hooks" / "pre-push").read_text(encoding="utf-8")
    action = (ROOT / ".github" / "actions" / "bob" / "action.yml").read_text(encoding="utf-8")

    assert DEFAULT_GATES == ("crap", "dry", "deps")
    assert "exec bob check --gates crap,dry,deps </dev/null\n" in hook
    assert "default: crap,dry,deps,mutate\n" in action


def test_an_unknown_gate_is_still_not_run(tmp_path: Path) -> None:
    repo = _init(tmp_path / "repo")

    code = run_check(repo, gates=["nope"], base="main")
    payload = _payload(repo)

    assert code == 0
    assert payload["exit_code"] == 0
    assert payload["gates"] == [
        {
            "name": "nope",
            "status": "not_run",
            "reason": "gate not implemented in this slice",
        }
    ]
    assert "dead_code" not in payload


def test_a_new_unused_function_warns_and_vulture_exit_3_stays_off_bob(
    tmp_path: Path,
) -> None:
    repo = _init(tmp_path / "repo")
    _git(repo, "checkout", "-b", "work")
    _commit(repo, "src/app/orphan.py", ORPHAN, "add orphan")

    result = run_bob(repo, "check", "--gates", "dead_code", "--base", "main")
    payload = _payload(repo)
    markdown = (repo / ".bob" / "report.md").read_text(encoding="utf-8")

    assert result.returncode == 0
    assert result.stdout == ""
    assert payload["exit_code"] == 0
    assert payload["schema_version"] == 1
    assert payload["gates"] == [
        {
            "name": "dead_code",
            "status": "warn",
            "reason": "1 unused symbol in the diff",
        }
    ]
    assert payload["tool_versions"]["vulture"] == "2.16"
    assert "knip" not in payload["tool_versions"]
    assert payload["dead_code"] == {
        "symbols": [
            {
                "file": "src/app/orphan.py",
                "line": 1,
                "name": "orphan",
                "kind": "function",
                "language": "python",
                "confidence": 60,
                "waiver": None,
            }
        ]
    }
    assert "- `src/app/orphan.py:1` function `orphan` 60%" in markdown
    assert "## Dead code" in markdown
    assert "## How to reproduce" in markdown


def test_a_body_edit_of_an_unused_function_passes(tmp_path: Path) -> None:
    repo = _init(tmp_path / "repo")
    _commit(repo, "src/app/orphan.py", ORPHAN, "add orphan")
    _commit(repo, "src/app/orphan.py", "def orphan():\n    return 2\n", "edit body")

    result = run_bob(repo, "check", "--gates", "dead_code", "--base", "HEAD~1")
    payload = _payload(repo)

    assert result.returncode == 0
    assert payload["exit_code"] == 0
    assert payload["gates"] == [{"name": "dead_code", "status": "passed", "reason": None}]
    assert payload["dead_code"] == {"symbols": []}
    assert "No unused symbol in the diff." in (repo / ".bob" / "report.md").read_text(
        encoding="utf-8"
    )


def test_a_dead_waiver_clears_the_warning(tmp_path: Path) -> None:
    repo = _init(tmp_path / "repo")
    _git(repo, "checkout", "-b", "work")
    _commit(repo, "src/app/orphan.py", ORPHAN, "add orphan")
    waiver = repo / ".bob" / "waivers.yaml"
    waiver.parent.mkdir()
    waiver.write_text(
        "waivers:\n"
        "  - id: dead:src/app/orphan.py:1:orphan\n"
        "    reason: loaded by a plugin\n"
        "    author: Ada\n"
        "    date: '2026-10-12'\n"
    )

    result = run_bob(repo, "check", "--gates", "dead_code", "--base", "main")
    payload = _payload(repo)

    assert result.returncode == 0
    assert payload["exit_code"] == 0
    assert payload["gates"] == [{"name": "dead_code", "status": "passed", "reason": None}]
    assert payload["dead_code"]["symbols"] == [
        {
            "file": "src/app/orphan.py",
            "line": 1,
            "name": "orphan",
            "kind": "function",
            "language": "python",
            "confidence": 60,
            "waiver": "dead:src/app/orphan.py:1:orphan",
        }
    ]


def test_repo_min_confidence_hides_a_finding_until_bob_passes_zero(tmp_path: Path) -> None:
    repo = _init(tmp_path / "repo")
    (repo / "pyproject.toml").write_text("[tool.vulture]\nmin_confidence = 100\n")
    _git(repo, "add", "pyproject.toml")
    _git(repo, "commit", "-m", "pin vulture confidence")
    _git(repo, "checkout", "-b", "work")
    _commit(repo, "src/app/orphan.py", ORPHAN, "add orphan")

    hidden = run_bob(repo, "check", "--gates", "dead_code", "--base", "main")
    hidden_payload = _payload(repo)
    (repo / "bob.yaml").write_text("dead_code:\n  min_confidence: 0\n")
    shown = run_bob(repo, "check", "--gates", "dead_code", "--base", "main")
    shown_payload = _payload(repo)

    assert hidden.returncode == 0
    assert hidden_payload["exit_code"] == 0
    assert hidden_payload["gates"][0]["status"] == "passed"
    assert hidden_payload["dead_code"] == {"symbols": []}
    assert shown.returncode == 0
    assert shown_payload["exit_code"] == 0
    assert shown_payload["gates"][0]["status"] == "warn"
    assert shown_payload["dead_code"]["symbols"][0]["name"] == "orphan"
    assert shown_payload["dead_code"]["symbols"][0]["confidence"] == 60


def test_missing_vulture_is_not_run_and_still_writes_the_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init(tmp_path / "repo")

    def missing(name: str) -> str:
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr("bob_quality.dead_code.importlib.metadata.version", missing)
    code = run_check(repo, gates=["dead_code"], base="main")
    payload = _payload(repo)
    markdown = (repo / ".bob" / "report.md").read_text(encoding="utf-8")

    assert code == 0
    assert payload["exit_code"] == 0
    assert payload["gates"] == [
        {
            "name": "dead_code",
            "status": "not_run",
            "reason": "missing tool: vulture",
        }
    ]
    assert payload["dead_code"] == {"symbols": []}
    assert "Not run (missing tool: vulture)." in markdown
    assert (repo / ".bob" / "report.json").is_file()
    assert (repo / ".bob" / "report.md").is_file()


def test_a_missing_include_path_exits_4_before_the_gate(tmp_path: Path) -> None:
    repo = _init(tmp_path / "repo")
    (repo / "bob.yaml").write_text("paths:\n  include: [missing]\n")

    code = run_check(repo, gates=["dead_code"], base="main")
    payload = _payload(repo)

    assert code == 4
    assert payload["exit_code"] == 4
    assert payload["gates"] == [
        {
            "name": "dead_code",
            "status": "not_run",
            "reason": "bob.yaml: paths.include does not exist: missing",
        }
    ]


def test_python_clean_stays_passed_when_node_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init(tmp_path / "repo")
    (repo / "bob.yaml").write_text("languages: [python, typescript]\n")
    _hide_node(monkeypatch)

    code = run_check(repo, gates=["dead_code"], base="main")
    payload = _payload(repo)

    assert code == 0
    assert payload["exit_code"] == 0
    assert payload["gates"] == [
        {
            "name": "dead_code",
            "status": "passed",
            "reason": "Node missing: install Node.js to run knip",
        }
    ]
    assert payload["dead_code"] == {"symbols": []}
    assert payload["tool_versions"]["vulture"] == "2.16"
    assert "knip" not in payload["tool_versions"]


def test_a_python_finding_warns_when_node_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init(tmp_path / "repo")
    (repo / "bob.yaml").write_text("languages: [python, typescript]\n")
    _git(repo, "checkout", "-b", "work")
    _commit(repo, "src/app/orphan.py", ORPHAN, "add orphan")
    _hide_node(monkeypatch)

    code = run_check(repo, gates=["dead_code"], base="main")
    payload = _payload(repo)

    assert code == 0
    assert payload["exit_code"] == 0
    assert payload["gates"] == [
        {
            "name": "dead_code",
            "status": "warn",
            "reason": (
                "1 unused symbol in the diff; "
                "Node missing: install Node.js to run knip"
            ),
        }
    ]
    assert payload["dead_code"]["symbols"][0]["name"] == "orphan"


def test_vulture_exit_zero_with_stdout_is_not_a_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init(tmp_path / "repo")
    real_run = subprocess.run

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[:1] == ["git"]:
            return real_run(args, **kwargs)
        assert args[1:3] == ["-m", "vulture"]
        assert "--min-confidence" not in args
        return subprocess.CompletedProcess(args, 0, stdout="noise\n", stderr="")

    monkeypatch.setattr("bob_quality.tools.subprocess.run", fake_run)
    code = run_check(repo, gates=["dead_code"], base="main")
    payload = _payload(repo)

    assert code == 0
    assert payload["gates"] == [
        {
            "name": "dead_code",
            "status": "not_run",
            "reason": "vulture: output could not be parsed",
        }
    ]
    assert payload["exit_code"] == 0


def test_vulture_exit_3_with_a_parsed_line_does_not_become_bob_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init(tmp_path / "repo")
    _git(repo, "checkout", "-b", "work")
    _commit(repo, "src/app/orphan.py", ORPHAN, "add orphan")

    real_run = subprocess.run

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[:1] == ["git"]:
            return real_run(args, **kwargs)
        return subprocess.CompletedProcess(
            args,
            3,
            stdout="src/app/orphan.py:1: unused function 'orphan' (60% confidence)\n",
            stderr="",
        )

    monkeypatch.setattr("bob_quality.tools.subprocess.run", fake_run)
    code = run_check(repo, gates=["dead_code"], base="main")
    payload = _payload(repo)

    assert code == 0
    assert payload["exit_code"] == 0
    assert payload["gates"][0]["status"] == "warn"
    assert payload["dead_code"]["symbols"][0]["confidence"] == 60


def test_knip_exit_1_with_json_is_a_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init(tmp_path / "repo")
    (repo / "bob.yaml").write_text("languages: [typescript]\n")
    _git(repo, "checkout", "-b", "work")
    _commit(repo, "src/app/orphan.ts", "export const orphan = 1\n", "add orphan")
    raw = (
        '{"issues":[{"file":"src/app/orphan.ts","exports":'
        '[{"name":"orphan","line":1,"col":1,"pos":1}]}]}\n'
    )

    real_run = subprocess.run

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[:1] == ["git"]:
            return real_run(args, **kwargs)
        prefix = str(npm_prefix())
        assert args == [
            "npx",
            "--no-install",
            "--prefix",
            prefix,
            "knip",
            "--reporter",
            "json",
            "--no-progress",
        ]
        return subprocess.CompletedProcess(args, 1, stdout=raw, stderr="")

    monkeypatch.setattr("bob_quality.tools.subprocess.run", fake_run)
    code = run_check(repo, gates=["dead_code"], base="main")
    payload = _payload(repo)

    assert code == 0
    assert payload["exit_code"] == 0
    assert payload["gates"][0] == {
        "name": "dead_code",
        "status": "warn",
        "reason": "1 unused symbol in the diff",
    }
    assert payload["tool_versions"] == {"knip": "6.41.0"}
    assert payload["dead_code"]["symbols"] == [
        {
            "file": "src/app/orphan.ts",
            "line": 1,
            "name": "orphan",
            "kind": "export",
            "language": "typescript",
            "confidence": None,
            "waiver": None,
        }
    ]


def test_knip_exit_2_with_json_is_not_a_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init(tmp_path / "repo")
    (repo / "bob.yaml").write_text("languages: [typescript]\n")

    real_run = subprocess.run

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[:1] == ["git"]:
            return real_run(args, **kwargs)
        return subprocess.CompletedProcess(
            args, 2, stdout='{"issues":[]}\n', stderr="config"
        )

    monkeypatch.setattr("bob_quality.tools.subprocess.run", fake_run)
    code = run_check(repo, gates=["dead_code"], base="main")
    payload = _payload(repo)

    assert code == 0
    assert payload["exit_code"] == 0
    assert payload["gates"] == [
        {
            "name": "dead_code",
            "status": "not_run",
            "reason": "knip: output could not be parsed",
        }
    ]


def _hide_node(monkeypatch: pytest.MonkeyPatch) -> None:
    real = shutil.which

    def which(cmd: str, *args: object, **kwargs: object) -> str | None:
        if cmd in {"node", "npx"}:
            return None
        return real(cmd)

    monkeypatch.setattr(shutil, "which", which)


def _payload(repo: Path) -> dict[str, object]:
    return json.loads((repo / ".bob" / "report.json").read_text(encoding="utf-8"))


def _init(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "bob-test@example.com")
    _git(path, "config", "user.name", "bob-test")
    _commit(path, "src/app/keep.py", KEEP, "base")
    return path


def _commit(repo: Path, relative: str, content: str, message: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    _git(repo, "add", relative)
    _git(repo, "commit", "-m", message)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
