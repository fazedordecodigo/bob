from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

from helpers import in_both, run_bob
from jsonschema import Draft202012Validator

from bob_quality.adapters.bandit import parse_bandit
from bob_quality.config import load_config
from bob_quality.models import Fail, OffDiff, Severity, Waived
from bob_quality.security_gate import FailSeverities, judge, run_security_gate
from bob_quality.waivers import Waiver

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "src" / "bob_quality" / "schemas" / "report_v1.json").read_text())
FIXTURE = ROOT / "tests" / "fixtures" / "raw" / "bandit-1.9.4.json"
EMPTY = "—"
ALLOWED = "CRITICAL, ERROR, HIGH, INFO, LOW, MEDIUM, UNDEFINED, WARNING"

HIGH_PY = """\
import subprocess

def run(command):
    return subprocess.Popen(command, shell=True)
"""
MEDIUM_PY = """\
import pickle

def load(blob):
    return pickle.loads(blob)
"""
CONFIDENCE_PY = """\
import os

def loose():
    os.system("chmod 777 *")
"""
OFF_PY = """\
import subprocess

def legacy(command):
    return subprocess.Popen(command, shell=True)

def current():
    return 1
"""
TS_CLEAN = """\
export function ready(): number {
  return 1;
}
"""
TS_EVAL = """\
export function current(code: string): unknown {
  return eval(code);
}
"""
TS_OLD = """\
export function old(code: string): unknown {
  return eval(code);
}

export function current(): number {
  return 1;
}
"""
RULE = """\
rules:
  - id: dangerous-eval
    languages: [typescript]
    severity: ERROR
    message: eval is forbidden
    pattern: eval(...)
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _init(tmp_path: Path, languages: str) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "bob-test@example.com")
    _git(repo, "config", "user.name", "bob-test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "bob.yaml").write_text(
        f"languages: [{languages}]\npaths:\n  include: [src]\n  exclude: [tests]\n"
    )
    (repo / "src").mkdir()
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    return repo


def _commit(repo: Path, relative: str, content: str, message: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    _git(repo, "add", relative)
    _git(repo, "commit", "-m", message)


def _on_branch(repo: Path, relative: str, content: str) -> None:
    _git(repo, "checkout", "-B", "feature")
    _commit(repo, relative, content, "change")


def _waiver(repo: Path, rows: str) -> None:
    path = repo / ".bob" / "waivers.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("waivers:\n" + rows)


def _check(repo: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return run_bob(repo, "check", "--gates", "security", "--base", "main", *extra)


def _report(repo: Path) -> tuple[dict[str, object], str]:
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    Draft202012Validator(SCHEMA).validate(payload)
    return payload, (repo / ".bob" / "report.md").read_text()


def _gate(payload: dict[str, object]) -> dict[str, object]:
    gates = payload["gates"]
    assert isinstance(gates, list)
    return gates[0]


def _findings(payload: dict[str, object]) -> list[dict[str, object]]:
    security = payload["security"]
    assert isinstance(security, dict)
    findings = security["findings"]
    assert isinstance(findings, list)
    return findings


@contextmanager
def _without_semgrep() -> Iterator[None]:
    original = os.environ.get("PATH", "")
    kept = [
        entry
        for entry in original.split(os.pathsep)
        if not entry or not (Path(entry) / "uvx").exists()
    ]
    os.environ["PATH"] = os.pathsep.join(kept)
    try:
        yield
    finally:
        os.environ["PATH"] = original


def test_bandit_high_on_a_changed_line_fails(tmp_path: Path) -> None:
    repo = _init(tmp_path, "python")
    _on_branch(repo, "src/app.py", HIGH_PY)

    result = _check(repo)

    assert result.returncode == 1
    assert result.stderr == ""
    payload, markdown = _report(repo)
    assert payload["exit_code"] == 1
    assert _gate(payload) == {
        "name": "security",
        "status": "failed",
        "reason": "1 findings in security.fail_severities",
    }
    assert _findings(payload) == [
        {
            "tool": "bandit",
            "rule": "B602",
            "file": "src/app.py",
            "line": 4,
            "end_line": 4,
            "severity": "HIGH",
            "disposition": "fail",
            "waiver": None,
        },
        {
            "tool": "bandit",
            "rule": "B404",
            "file": "src/app.py",
            "line": 1,
            "end_line": 1,
            "severity": "LOW",
            "disposition": "warn",
            "waiver": None,
        },
    ]
    assert payload["tool_versions"]["bandit"] == "1.9.4"
    assert "semgrep" not in payload["tool_versions"]
    assert "## Security" in markdown
    assert f"| bandit | B602 | src/app.py:4 | HIGH | fail | {EMPTY} |" in markdown


def test_bandit_medium_on_a_changed_line_warns(tmp_path: Path) -> None:
    repo = _init(tmp_path, "python")
    _on_branch(repo, "src/app.py", MEDIUM_PY)

    result = _check(repo, "--lang", "pt-BR")

    assert result.returncode == 0
    payload, markdown = _report(repo)
    assert payload["exit_code"] == 0
    assert _gate(payload) == {
        "name": "security",
        "status": "warn",
        "reason": "2 findings outside security.fail_severities",
    }
    assert _findings(payload) == [
        {
            "tool": "bandit",
            "rule": "B403",
            "file": "src/app.py",
            "line": 1,
            "end_line": 1,
            "severity": "LOW",
            "disposition": "warn",
            "waiver": None,
        },
        {
            "tool": "bandit",
            "rule": "B301",
            "file": "src/app.py",
            "line": 4,
            "end_line": 4,
            "severity": "MEDIUM",
            "disposition": "warn",
            "waiver": None,
        },
    ]
    assert "## Segurança" in markdown
    assert f"| bandit | B301 | src/app.py:4 | MEDIUM | aviso | {EMPTY} |" in markdown


def test_a_finding_outside_changed_lines_does_not_fail(tmp_path: Path) -> None:
    repo = _init(tmp_path, "python")
    _commit(repo, "src/app.py", OFF_PY, "legacy shell")
    _on_branch(repo, "src/app.py", OFF_PY.replace("return 1", "return 2"))

    result = _check(repo)

    assert result.returncode == 0
    payload, _markdown = _report(repo)
    assert _gate(payload) == {"name": "security", "status": "passed", "reason": None}
    assert _findings(payload) == [
        {
            "tool": "bandit",
            "rule": "B404",
            "file": "src/app.py",
            "line": 1,
            "end_line": 1,
            "severity": "LOW",
            "disposition": "off_diff",
            "waiver": None,
        },
        {
            "tool": "bandit",
            "rule": "B602",
            "file": "src/app.py",
            "line": 4,
            "end_line": 4,
            "severity": "HIGH",
            "disposition": "off_diff",
            "waiver": None,
        },
    ]


def test_a_rule_waiver_clears_an_on_diff_hit(tmp_path: Path) -> None:
    repo = _init(tmp_path, "python")
    _on_branch(repo, "src/app.py", HIGH_PY)
    _waiver(
        repo,
        "  - id: sast:bandit:B602\n"
        "    reason: accepted shell\n"
        "    author: ada\n"
        "    date: '2026-10-12'\n",
    )

    result = _check(repo)

    assert result.returncode == 0
    payload, _markdown = _report(repo)
    assert _gate(payload)["status"] == "warn"
    assert _gate(payload)["reason"] == "1 findings outside security.fail_severities"
    by_rule = {item["rule"]: item for item in _findings(payload)}
    assert by_rule["B602"]["disposition"] == "waived"
    assert by_rule["B602"]["waiver"] == "accepted shell"
    assert by_rule["B404"]["disposition"] == "warn"


def test_a_file_and_line_waiver_wins_over_the_rule_waiver(tmp_path: Path) -> None:
    repo = _init(tmp_path, "python")
    _on_branch(repo, "src/app.py", HIGH_PY)
    _waiver(
        repo,
        "  - id: sast:bandit:B602\n"
        "    reason: broad shell\n"
        "    author: ada\n"
        "    date: '2026-10-12'\n"
        "  - id: sast:bandit:B602:src/app.py:4\n"
        "    reason: this line\n"
        "    author: ada\n"
        "    date: '2026-10-12'\n",
    )

    result = _check(repo)

    assert result.returncode == 0
    payload, _markdown = _report(repo)
    by_rule = {item["rule"]: item for item in _findings(payload)}
    assert by_rule["B602"]["disposition"] == "waived"
    assert by_rule["B602"]["waiver"] == "this line"


def test_bandit_confidence_does_not_drop_a_high_hit(tmp_path: Path) -> None:
    repo = _init(tmp_path, "python")
    _on_branch(repo, "src/app.py", CONFIDENCE_PY)

    result = _check(repo)

    assert result.returncode == 1
    payload, _markdown = _report(repo)
    assert _gate(payload)["status"] == "failed"
    by_rule = {item["rule"]: item for item in _findings(payload)}
    assert by_rule["B609"] == {
        "tool": "bandit",
        "rule": "B609",
        "file": "src/app.py",
        "line": 4,
        "end_line": 4,
        "severity": "HIGH",
        "disposition": "fail",
        "waiver": None,
    }
    assert by_rule["B605"]["disposition"] == "warn"
    assert by_rule["B607"]["disposition"] == "warn"


def test_a_project_bandit_file_does_not_hide_a_high_hit(tmp_path: Path) -> None:
    repo = _init(tmp_path, "python")
    _on_branch(repo, "src/app.py", HIGH_PY)
    _commit(repo, "src/.bandit", "[bandit]\nskips = B602\n", "skip shell")

    result = _check(repo)

    assert result.returncode == 1
    payload, _markdown = _report(repo)
    rules = {item["rule"] for item in _findings(payload) if item["disposition"] == "fail"}
    assert rules == {"B602"}


def test_semgrep_error_on_a_changed_line_fails(tmp_path: Path) -> None:
    repo = _init(tmp_path, "typescript")
    _commit(repo, ".semgrep/rules.yml", RULE, "rules")
    _commit(repo, "src/app.ts", TS_CLEAN, "clean")
    _on_branch(repo, "src/app.ts", TS_EVAL)

    result = _check(repo)

    assert result.returncode == 1
    payload, markdown = _report(repo)
    assert _gate(payload) == {
        "name": "security",
        "status": "failed",
        "reason": "1 findings in security.fail_severities",
    }
    assert _findings(payload) == [
        {
            "tool": "semgrep",
            "rule": "semgrep.dangerous-eval",
            "file": "src/app.ts",
            "line": 2,
            "end_line": 2,
            "severity": "ERROR",
            "disposition": "fail",
            "waiver": None,
        }
    ]
    assert payload["tool_versions"]["semgrep"] == "1.180.0"
    assert "bandit" not in payload["tool_versions"]
    assert f"| semgrep | semgrep.dangerous-eval | src/app.ts:2 | ERROR | fail | {EMPTY} |" in markdown


def test_semgrep_baseline_ignores_a_finding_that_exists_at_the_merge_base(tmp_path: Path) -> None:
    repo = _init(tmp_path, "typescript")
    _commit(repo, ".semgrep/rules.yml", RULE, "rules")
    _commit(repo, "src/app.ts", TS_OLD, "old eval")
    _on_branch(repo, "src/app.ts", TS_OLD.replace("return 1;", "return 2;"))

    result = _check(repo)

    assert result.returncode == 0
    payload, markdown = _report(repo)
    assert _gate(payload) == {"name": "security", "status": "passed", "reason": None}
    assert _findings(payload) == []
    assert "No findings." in markdown
    assert "dangerous-eval" not in markdown


def test_error_is_not_an_alias_of_high(tmp_path: Path) -> None:
    repo = _init(tmp_path, "typescript")
    (repo / "bob.yaml").write_text(
        "languages: [typescript]\n"
        "paths:\n  include: [src]\n  exclude: [tests]\n"
        "security:\n  fail_severities: [HIGH, CRITICAL]\n"
    )
    _git(repo, "add", "bob.yaml")
    _git(repo, "commit", "-m", "policy")
    _commit(repo, ".semgrep/rules.yml", RULE, "rules")
    _on_branch(repo, "src/app.ts", TS_EVAL)

    result = _check(repo)

    assert result.returncode == 0
    payload, _markdown = _report(repo)
    assert _gate(payload) == {
        "name": "security",
        "status": "warn",
        "reason": "1 findings outside security.fail_severities",
    }
    assert _findings(payload)[0]["severity"] == "ERROR"
    assert _findings(payload)[0]["disposition"] == "warn"


def test_semgrep_runs_when_the_worktree_is_dirty(tmp_path: Path) -> None:
    repo = _init(tmp_path, "typescript")
    _commit(repo, ".semgrep/rules.yml", RULE, "rules")
    _commit(repo, "src/app.ts", TS_CLEAN, "clean")
    (repo / "src" / "app.ts").write_text(TS_EVAL)

    result = _check(repo)

    assert result.returncode == 0
    payload, _markdown = _report(repo)
    assert _gate(payload)["status"] == "passed"
    assert _findings(payload) == []
    assert "dangerous-eval" not in json.dumps(payload["security"])


def test_missing_semgrep_on_a_typescript_repo_is_not_run(tmp_path: Path) -> None:
    repo = _init(tmp_path, "typescript")
    _commit(repo, ".semgrep/rules.yml", RULE, "rules")
    _commit(repo, "src/app.ts", TS_CLEAN, "clean")

    with _without_semgrep():
        result = _check(repo)

    assert result.returncode == 4
    payload, _markdown = _report(repo)
    assert payload["exit_code"] == 4
    assert _gate(payload) == {
        "name": "security",
        "status": "not_run",
        "reason": "semgrep runner missing: uvx",
    }
    assert payload["security"] == {"findings": [], "unmeasured": ["semgrep"]}
    assert "semgrep" not in payload["tool_versions"]
    assert (repo / ".bob" / "report.md").is_file()


def test_a_python_repo_does_not_require_semgrep(tmp_path: Path) -> None:
    clean = _init(tmp_path, "python")
    _commit(clean, "src/app.py", "def ready():\n    return 1\n", "ready")

    with _without_semgrep():
        clean_result = _check(clean)

    assert clean_result.returncode == 0
    clean_payload, _markdown = _report(clean)
    assert _gate(clean_payload)["status"] == "passed"
    assert clean_payload["security"]["findings"] == []
    assert clean_payload["security"]["unmeasured"] == []
    assert clean_payload["tool_versions"]["bandit"] == "1.9.4"
    assert "semgrep" not in clean_payload["tool_versions"]


def test_python_bandit_still_fails_when_semgrep_is_absent(tmp_path: Path) -> None:
    repo = _init(tmp_path, "python")
    _on_branch(repo, "src/app.py", HIGH_PY)

    with _without_semgrep():
        result = _check(repo)

    assert result.returncode == 1
    payload, _markdown = _report(repo)
    assert _gate(payload)["status"] == "failed"
    assert _findings(payload)[0]["rule"] == "B602"
    assert _findings(payload)[0]["disposition"] == "fail"


def test_unknown_fail_severity_exits_4_without_a_report(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("security:\n  fail_severities: [NOPE]\n")

    result = run_bob(tmp_path, "check", "--gates", "security")

    assert result.returncode == 4
    assert result.stdout == ""
    assert result.stderr == (
        "bob.yaml: security.fail_severities[0] must be one of "
        f"{ALLOWED}\n"
    )
    assert not (tmp_path / ".bob" / "report.json").exists()
    assert not (tmp_path / ".bob" / "report.md").exists()


def test_check_without_security_omits_the_report_key(tmp_path: Path) -> None:
    repo = _init(tmp_path, "python")

    result = run_bob(repo, "check", "--gates", "nope", "--base", "main")

    assert result.returncode == 0
    payload, markdown = _report(repo)
    assert "security" not in payload
    assert "## Security" not in markdown
    assert "## Segurança" not in markdown


def test_missing_semgrep_rules_are_unmeasured(tmp_path: Path) -> None:
    repo = _init(tmp_path, "typescript")
    _commit(repo, "src/app.ts", TS_CLEAN, "clean")

    result = _check(repo)

    assert result.returncode == 4
    payload, markdown = _report(repo)
    assert _gate(payload) == {
        "name": "security",
        "status": "not_run",
        "reason": "missing rules directory: .semgrep",
    }
    assert payload["security"] == {"findings": [], "unmeasured": ["semgrep"]}
    assert "No findings." not in markdown
    assert "missing rules directory: .semgrep" in markdown


def test_a_missing_language_warns_when_another_measured(tmp_path: Path) -> None:
    repo = _init(tmp_path, "python, typescript")
    _commit(repo, "src/app.py", "def ready():\n    return 1\n", "ready")

    with _without_semgrep():
        result = _check(repo)

    assert result.returncode == 0
    payload, _markdown = _report(repo)
    assert _gate(payload) == {
        "name": "security",
        "status": "warn",
        "reason": "semgrep runner missing: uvx",
    }
    assert payload["security"]["unmeasured"] == ["semgrep"]
    assert payload["security"]["findings"] == []


def test_a_missing_language_keeps_a_failure(tmp_path: Path) -> None:
    repo = _init(tmp_path, "python, typescript")
    _on_branch(repo, "src/app.py", HIGH_PY)

    with _without_semgrep():
        result = _check(repo)

    assert result.returncode == 1
    payload, _markdown = _report(repo)
    assert _gate(payload) == {
        "name": "security",
        "status": "failed",
        "reason": "1 findings in security.fail_severities; semgrep runner missing: uvx",
    }
    assert _findings(payload)[0]["disposition"] == "fail"
    assert payload["security"]["unmeasured"] == ["semgrep"]


def test_a_rule_id_with_a_colon_matches_by_equality() -> None:
    parsed = parse_bandit(FIXTURE.read_text(), Path("/tmp/bob-sec-probe"))
    high = next(item for item in parsed if item.rule == "B602" and item.severity == "HIGH")
    finding = replace(high, rule="B602:extra", file="src/app.py", line=4, end_line=4)
    policy = FailSeverities(frozenset(Severity(label) for label in ("HIGH", "CRITICAL", "ERROR")))
    on_diff = {"src/app.py": {4}}
    off_diff = {"src/app.py": {9}}
    broad = Waiver("sast:bandit:B602:extra", "broad", "ada", "2026-10-12")
    specific = Waiver("sast:bandit:B602:extra:src/app.py:4", "specific", "ada", "2026-10-12")
    split = Waiver("sast:bandit:B602", "split", "ada", "2026-10-12")

    assert judge(finding, on_diff, policy, (broad,)) == Waived(finding, "broad")
    assert judge(finding, on_diff, policy, (broad, specific)) == Waived(finding, "specific")
    assert judge(finding, on_diff, policy, (split,)) == Fail(finding)
    assert judge(finding, off_diff, policy, (specific,)) == Waived(finding, "specific")
    assert judge(finding, off_diff, policy, (broad,)) == OffDiff(finding)


def test_a_missing_include_root_exits_4_before_the_scan(tmp_path: Path) -> None:
    repo = _init(tmp_path, "python")
    shutil.rmtree(repo / "src")

    result = _check(repo)

    assert result.returncode == 4
    assert result.stdout == ""
    assert result.stderr == "bob.yaml: paths.include does not exist: src\n"
    assert not (repo / ".bob" / "report.json").exists()
    assert not (repo / ".bob" / "report.md").exists()


def test_invalid_semgrep_rules_are_unmeasured(tmp_path: Path) -> None:
    repo = _init(tmp_path, "typescript")
    _commit(repo, ".semgrep/rules.yml", "rules:\n  - id: [broken\n", "rules")
    _commit(repo, "src/app.ts", TS_CLEAN, "clean")

    result = _check(repo)

    assert result.returncode == 4
    payload, _markdown = _report(repo)
    assert _gate(payload)["status"] == "not_run"
    assert _gate(payload)["reason"] == "semgrep: exit 7"
    assert payload["security"] == {"findings": [], "unmeasured": ["semgrep"]}


def test_bandit_stdout_outside_the_contract_is_unmeasured(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _ready_python(tmp_path)
    _stub_bandit(monkeypatch, subprocess.CompletedProcess([], 0, stdout="{", stderr=""))

    result, code, versions, report = run_security_gate(repo, load_config(None, repo), "main", {})

    assert code == 4
    assert versions == {}
    assert result.status == "not_run"
    assert in_both(result.reason) == ("bandit: invalid JSON", "bandit: JSON inválido")
    assert report.unmeasured == ("bandit",)
    assert report.findings == ()


def test_bandit_exit_outside_measurement_is_unmeasured(tmp_path: Path, monkeypatch) -> None:
    repo = _ready_python(tmp_path)
    _stub_bandit(monkeypatch, subprocess.CompletedProcess([], 2, stdout="", stderr="usage"))

    result, code, _versions, report = run_security_gate(
        repo, load_config(None, repo), "main", {}
    )

    assert code == 4
    assert result.status == "not_run"
    assert in_both(result.reason) == ("bandit: exit 2", "bandit: exit 2")
    assert report.unmeasured == ("bandit",)


def test_a_bandit_timeout_is_unmeasured(tmp_path: Path, monkeypatch) -> None:
    repo = _ready_python(tmp_path)

    def explode(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(argv, 1)

    _stub_bandit(monkeypatch, explode)

    result, code, _versions, report = run_security_gate(
        repo, load_config(None, repo), "main", {}
    )

    assert code == 4
    assert result.status == "not_run"
    assert "timed out" in in_both(result.reason)[0]
    assert report.unmeasured == ("bandit",)


def _ready_python(tmp_path: Path) -> Path:
    repo = _init(tmp_path, "python")
    _commit(repo, "src/app.py", "def ready():\n    return 1\n", "ready")
    return repo


def _stub_bandit(monkeypatch, outcome: object) -> None:
    real = subprocess.run

    def fake(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["-m", "bandit"]:
            if isinstance(outcome, subprocess.CompletedProcess):
                return outcome
            return outcome(argv, **kwargs)
        return real(argv, **kwargs)

    monkeypatch.setattr("bob_quality.security_gate.subprocess.run", fake)


def test_gate_publications_stay_on_the_default_lists() -> None:
    from bob_quality.check import DEFAULT_GATES

    assert DEFAULT_GATES == ("crap", "dry", "deps")


def test_detached_resolves_symlinked_tempdir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bob_quality.security_gate import _detached

    repo = _ready_python(tmp_path)
    real_tmp = tmp_path / "real_tmp"
    real_tmp.mkdir()
    link_tmp = tmp_path / "var_tmp"
    link_tmp.symlink_to(real_tmp)
    seen_prefix: list[str | None] = []

    def _fake_mkdtemp(
        suffix: str | None = None,
        prefix: str | None = None,
        dir: str | None = None,
    ) -> str:
        seen_prefix.append(prefix)
        created = real_tmp / "bob-semgrep-123"
        created.mkdir()
        return str(link_tmp / "bob-semgrep-123")

    monkeypatch.setattr("bob_quality.security_gate.tempfile.mkdtemp", _fake_mkdtemp)
    generated = _detached(repo)
    try:
        root = next(generated)
        assert root == (real_tmp / "bob-semgrep-123" / "head").resolve()
        assert (root / "src" / "app.py").is_file()
    finally:
        generated.close()
    assert seen_prefix == ["bob-semgrep-"]
    assert not (real_tmp / "bob-semgrep-123").exists()
