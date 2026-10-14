from __future__ import annotations

import io
import json
import os
import subprocess
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from bob_quality.cli import main
from bob_quality.report import load_saved_report


def _invoke(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    previous_cwd = Path.cwd()
    previous_env = os.environ.copy()
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        os.environ.pop("BOB_LANG", None)
        os.chdir(repo)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(list(args))
    finally:
        os.chdir(previous_cwd)
        os.environ.clear()
        os.environ.update(previous_env)
    return subprocess.CompletedProcess(
        ["bob", *args], code, stdout.getvalue(), stderr.getvalue()
    )


_MINIMAL = {
    "schema_version": 1,
    "commit": "abc",
    "base": "main",
    "generated_at": "2026-10-12T00:00:00Z",
    "tool_versions": {"lizard": "1.24.1"},
    "gates": [{"name": "crap", "status": "passed", "reason": None}],
    "focus": [],
    "top_crap": [],
    "reproduce": "bob check",
    "exit_code": 0,
}

_EN = """# bob report

- Commit: `abc`
- Base: `main`
- Date: 2026-10-12T00:00:00Z
- Tools: lizard 1.24.1

## Verdict

- ✅ `crap`: passed

## Where to focus the review

- No changed file with CRAP risk.

## Top 5 functions by CRAP (diff)

No changed function measured.

## Dependency violations and cycles

- Gate not run.

## New clones

Not run.

## How to reproduce

```
bob check --lang en
```
"""

_PT = """# Relatório bob

- Commit: `abc`
- Base: `main`
- Data: 2026-10-12T00:00:00Z
- Ferramentas: lizard 1.24.1

## Veredito

- ✅ `crap`: passou

## Onde focar o review

- Nenhum arquivo alterado com risco de CRAP.

## Top 5 funções por CRAP (diff)

Nenhuma função alterada medida.

## Violações e ciclos de dependência

- Gate não executado.

## Clones novos

Não executado.

## Como reproduzir

```
bob check --lang pt-BR
```
"""


def _save(repo: Path, payload: object, folder: str = ".bob") -> Path:
    directory = repo / folder
    directory.mkdir(parents=True)
    path = directory / "report.json"
    path.write_text(json.dumps(payload) + "\n")
    return path


def test_report_renders_the_saved_json_and_keeps_the_exit_code(tmp_path: Path) -> None:
    saved = _save(tmp_path, _MINIMAL)
    before = saved.read_bytes()

    result = _invoke(tmp_path, "report")

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == ""
    assert (tmp_path / ".bob" / "report.md").read_text() == _EN
    assert load_saved_report(tmp_path / ".bob").schema_version == 1
    assert saved.read_bytes() == before
    assert not (tmp_path / ".bob" / "report.md.tmp").exists()


def test_report_follows_the_language_flag(tmp_path: Path) -> None:
    _save(tmp_path, _MINIMAL)

    result = _invoke(tmp_path, "report", "--lang", "pt-BR")

    assert result.returncode == 0
    assert (tmp_path / ".bob" / "report.md").read_text() == _PT


def test_report_language_before_the_command(tmp_path: Path) -> None:
    _save(tmp_path, _MINIMAL)

    result = _invoke(tmp_path, "--lang", "pt-BR", "report")

    assert result.returncode == 0
    assert (tmp_path / ".bob" / "report.md").read_text() == _PT


def test_report_help_follows_the_language(tmp_path: Path) -> None:
    english = _invoke(tmp_path, "report", "--help")
    portuguese = _invoke(tmp_path, "report", "--lang", "pt-BR", "--help")

    assert english.returncode == 0
    assert "Render report.json from a directory as Markdown" in english.stdout
    assert portuguese.returncode == 0
    assert "Renderiza o report.json de uma pasta como Markdown" in portuguese.stdout
    assert not (tmp_path / ".bob").exists()


def test_report_reads_another_directory_and_writes_another_file(tmp_path: Path) -> None:
    _save(tmp_path, _MINIMAL, folder="saved")

    result = _invoke(tmp_path, "report", "--in", "saved", "--out", "out/nested/summary.md")

    assert result.returncode == 0
    assert (tmp_path / "out" / "nested" / "summary.md").read_text() == _EN
    assert not (tmp_path / ".bob").exists()
    assert not (tmp_path / "saved" / "report.md").exists()


def test_report_is_idempotent(tmp_path: Path) -> None:
    _save(tmp_path, _MINIMAL)
    first = _invoke(tmp_path, "report")
    written = (tmp_path / ".bob" / "report.md").read_bytes()

    second = _invoke(tmp_path, "report")

    assert first.returncode == 0
    assert second.returncode == 0
    assert (tmp_path / ".bob" / "report.md").read_bytes() == written


@pytest.mark.parametrize("code", [0, 1, 2, 3, 4])
def test_report_returns_the_stored_exit_code(tmp_path: Path, code: int) -> None:
    payload = dict(_MINIMAL)
    payload["exit_code"] = code
    _save(tmp_path, payload)

    result = _invoke(tmp_path, "report")

    assert result.returncode == code
    assert (tmp_path / ".bob" / "report.md").read_text().startswith("# bob report\n")


def test_report_renders_a_failed_gate_a_clone_and_a_metric(tmp_path: Path) -> None:
    payload = dict(_MINIMAL)
    payload["exit_code"] = 1
    payload["gates"] = [
        {"name": "crap", "status": "failed", "reason": "over the limit"},
        {"name": "dry", "status": "warn"},
        {"name": "deps", "status": "failed", "reason": "tool missing"},
        {"name": "mutate", "status": "not_run"},
    ]
    payload["focus"] = [{"file": "app.py", "risk": 12, "clone": True}]
    payload["top_crap"] = [
        {
            "name": "add",
            "file": "app.py",
            "start_line": 4,
            "coverage": 0.5,
            "cc": 2,
            "crap": 2.25,
            "delta": 1.5,
        },
        {
            "name": "old",
            "file": "old.py",
            "start_line": 9,
            "coverage": 1,
            "cc": 1,
            "crap": 1,
            "delta": None,
        },
    ]
    payload["clones"] = [
        {
            "first_file": "a.py",
            "first_start": 1,
            "first_end": 2,
            "second_file": "b.py",
            "second_start": 3,
            "second_end": 4,
            "lines": 2,
            "tokens": 10,
            "similarity": 1,
        }
    ]
    payload["dependencies"] = [
        {"origin": "app", "destination": "core", "rule": "Forbidden dependency cycle"}
    ]
    payload["old_dependencies"] = [
        {"origin": "legacy", "destination": "util", "rule": "old rule"}
    ]
    _save(tmp_path, payload)

    result = _invoke(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 1
    assert "- ❌ `crap`: failed (over the limit)" in markdown
    assert "- ⚠️ `dry`: warning" in markdown
    assert "- ❌ `deps`: failed (tool missing)" in markdown
    assert "- ⏭️ `mutate`: not run" in markdown
    assert "- `app.py` (risk 12, clone)" in markdown
    assert "| add | app.py:4 | 2 | 50% | 2.25 | 1.5 |" in markdown
    assert "| old | old.py:9 | 1 | 100% | 1 | — |" in markdown
    assert (
        "- `a.py:1-2` ↔ `b.py:3-4` — 2 lines, 10 tokens, similarity 100%" in markdown
    )
    assert "- `app → core` (Forbidden dependency cycle)" in markdown
    assert "- `legacy → util` (old rule) (outside the diff; does not block)" in markdown


def test_report_renders_an_exact_clone_and_old_debt(tmp_path: Path) -> None:
    payload = dict(_MINIMAL)
    payload["old_debt"] = [
        {"name": "legacy", "file": "old.py", "start_line": 9, "crap": 30}
    ]
    payload["clones"] = [
        {
            "first_file": "a.py",
            "first_start": 1,
            "first_end": 2,
            "second_file": "b.py",
            "second_start": 3,
            "second_end": 4,
            "lines": 2,
            "tokens": 10,
            "kind": "exact",
        },
        {
            "first_file": "c.py",
            "first_start": 1,
            "first_end": 2,
            "second_file": "d.py",
            "second_start": 3,
            "second_end": 4,
            "lines": 2,
            "tokens": 10,
        },
    ]
    payload["mutation"] = {
        "no_coverage": {"total": 1, "functions": [{"file": "app.py", "function": "add", "count": 1}]}
    }
    payload["survivors"] = [
        {
            "id": "app.add__mutmut_1",
            "function": "add",
            "file": "app.py",
            "line": 4,
            "operator": "ROR",
            "target": "app.py::add::ROR",
        }
    ]
    payload["waivers"] = [
        {"id": "fn", "reason": "because", "author": "ada", "date": "2026-10-11"}
    ]
    _save(tmp_path, payload)

    result = _invoke(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert "legacy" in markdown
    assert "old.py:9" in markdown
    assert "similarity exact" in markdown
    assert "similarity —" in markdown
    assert "`app.py::add::ROR`" in markdown
    assert "| `fn` | because | ada | 2026-10-11 |" in markdown
    assert "| add | app.py | 1 |" in markdown


def test_missing_report_exits_4_and_writes_nothing(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "report", "--lang", "pt-BR")
    missing = tmp_path / ".bob" / "report.json"

    assert result.returncode == 4
    assert result.stderr == f"report file not found: {missing}\n"
    assert result.stdout == ""
    assert "baseline" not in result.stderr.lower()
    assert not (tmp_path / ".bob").exists()
    assert not (tmp_path / "out").exists()


def test_invalid_report_does_not_truncate_an_existing_file(tmp_path: Path) -> None:
    saved = _save(tmp_path, [])
    destination = tmp_path / ".bob" / "report.md"
    destination.write_text("keep\n")

    result = _invoke(tmp_path, "report")

    assert result.returncode == 4
    assert result.stderr == f"invalid report: {saved}\n"
    assert destination.read_text() == "keep\n"
    assert not (tmp_path / ".bob" / "report.md.tmp").exists()


_CLONE = {
    "first_file": "a.py",
    "first_start": 1,
    "first_end": 2,
    "second_file": "b.py",
    "second_start": 3,
    "second_end": 4,
    "lines": 2,
    "tokens": 10,
}


def _metric(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "name": "add",
        "file": "app.py",
        "start_line": 4,
        "coverage": 0.5,
        "cc": 2,
        "crap": 2.25,
    }
    row.update(overrides)
    return row


def _finding(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "tool": "bandit",
        "rule": "B602",
        "file": "src/app.py",
        "line": 4,
        "end_line": 4,
        "severity": "HIGH",
        "disposition": "fail",
        "waiver": None,
    }
    row.update(overrides)
    return row


def _secret(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "file": "src/app.py",
        "line": 12,
        "rule_id": "aws-access-token",
    }
    row.update(overrides)
    return row


def _dead(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "file": "app.py",
        "line": 4,
        "name": "add",
        "kind": "function",
        "language": "python",
        "confidence": 60,
        "waiver": None,
    }
    row.update(overrides)
    return row


_DEAD_KINDS = (
    ("python", "attribute", 0),
    ("python", "class", 100),
    ("python", "function", 60),
    ("python", "import", 1),
    ("python", "method", 50),
    ("python", "property", 40),
    ("python", "variable", 30),
    ("python", "unreachable_code", 90),
    ("typescript", "export", None),
    ("typescript", "type", None),
    ("typescript", "enum_member", None),
    ("typescript", "namespace_member", None),
    ("typescript", "ns_export", None),
    ("typescript", "ns_type", None),
)


@pytest.mark.parametrize(("language", "kind", "confidence"), _DEAD_KINDS)
def test_report_renders_a_saved_dead_symbol(
    tmp_path: Path, language: str, kind: str, confidence: int | None
) -> None:
    payload = dict(_MINIMAL)
    payload["dead_code"] = {"symbols": [_dead(language=language, kind=kind, confidence=confidence)]}
    _save(tmp_path, payload)

    result = _invoke(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert f"- `app.py:4` {kind} `add`" in markdown
    if confidence is None:
        assert "- `app.py:4` " + kind + " `add`" in markdown
        assert "%" not in markdown.split("## Dead code", 1)[1]
    else:
        assert f"- `app.py:4` {kind} `add` {confidence}%" in markdown


def test_report_renders_a_waived_dead_symbol(tmp_path: Path) -> None:
    payload = dict(_MINIMAL)
    payload["gates"] = [{"name": "dead_code", "status": "passed", "reason": "vulture quiet"}]
    payload["dead_code"] = {
        "symbols": [_dead(waiver="dead:app.py:4:add", confidence=60)]
    }
    _save(tmp_path, payload)

    result = _invoke(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert "- `app.py:4` function `add` 60% waiver `dead:app.py:4:add`" in markdown


def test_report_renders_an_empty_dead_section_with_its_reason(tmp_path: Path) -> None:
    payload = dict(_MINIMAL)
    payload["gates"] = [{"name": "dead_code", "status": "passed", "reason": "vulture quiet"}]
    payload["dead_code"] = {"symbols": []}
    _save(tmp_path, payload)

    result = _invoke(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert "No unused symbol in the diff." in markdown
    assert "vulture quiet" in markdown


def test_report_renders_dead_code_that_did_not_run(tmp_path: Path) -> None:
    payload = dict(_MINIMAL)
    payload["gates"] = [{"name": "dead_code", "status": "not_run", "reason": "no files"}]
    payload["dead_code"] = {"symbols": []}
    _save(tmp_path, payload)

    result = _invoke(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert "## Dead code" in markdown
    assert "Not run (no files)." in markdown


def test_report_renders_a_dead_symbol_on_the_first_line(tmp_path: Path) -> None:
    payload = dict(_MINIMAL)
    payload["dead_code"] = {"symbols": [_dead(line=1)]}
    _save(tmp_path, payload)

    result = _invoke(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert "- `app.py:1` function `add` 60%" in markdown


def test_report_renders_a_dead_symbol_without_a_waiver_key(tmp_path: Path) -> None:
    payload = dict(_MINIMAL)
    symbol = _dead()
    del symbol["waiver"]
    payload["dead_code"] = {"symbols": [symbol]}
    _save(tmp_path, payload)

    result = _invoke(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert "- `app.py:4` function `add` 60%" in markdown
    assert "waiver" not in markdown


def test_report_renders_saved_secrets(tmp_path: Path) -> None:
    payload = dict(_MINIMAL)
    payload["secrets"] = [
        _secret(),
        _secret(file="src/old.py", line=2, rule_id="generic-api-key"),
    ]
    _save(tmp_path, payload)

    result = _invoke(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert "\n\n## Secrets\n\n| Target | File | Line | Rule |\n|---|---|---:|---|\n" in markdown
    assert "| `secret:aws-access-token:src/app.py:12` | src/app.py | 12 | aws-access-token |" in markdown
    assert "| `secret:generic-api-key:src/old.py:2` | src/old.py | 2 | generic-api-key |" in markdown


def test_report_renders_saved_security_and_types(tmp_path: Path) -> None:
    payload = dict(_MINIMAL)
    payload["security"] = {
        "findings": [
            {
                "tool": "bandit",
                "rule": "B602",
                "file": "src/app.py",
                "line": 4,
                "end_line": 6,
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
            {
                "tool": "semgrep",
                "rule": "rule",
                "file": "src/app.py",
                "line": 2,
                "end_line": 2,
                "severity": "MEDIUM",
                "disposition": "waived",
                "waiver": "because",
            },
            {
                "tool": "semgrep",
                "rule": "other",
                "file": "src/old.py",
                "line": 9,
                "end_line": 9,
                "severity": "INFO",
                "disposition": "off_diff",
                "waiver": None,
            },
        ],
        "unmeasured": ["semgrep"],
    }
    payload["typing"] = {
        "absent": [],
        "checkers": [],
        "findings": [
            {
                "kind": "diagnostic",
                "disposition": "blocking",
                "file": "src/app.py",
                "line": 4,
                "code": "assignment",
                "tool": "mypy",
                "waiver_id": "typing:src/app.py:4:assignment",
            }
        ],
    }
    _save(tmp_path, payload)

    result = _invoke(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert "| bandit | B602 | src/app.py:4-6 | HIGH | fail | — |" in markdown
    assert "| bandit | B404 | src/app.py:1 | LOW | warn | — |" in markdown
    assert "| semgrep | rule | src/app.py:2 | MEDIUM | waived | because |" in markdown
    assert "| semgrep | other | src/old.py:9 | INFO | off diff | — |" in markdown
    assert "| `src/app.py` | 4 | `assignment` | blocking | `typing:src/app.py:4:assignment` |" in markdown


def test_report_renders_an_empty_security_report(tmp_path: Path) -> None:
    payload = dict(_MINIMAL)
    payload["security"] = {"findings": [], "unmeasured": []}
    _save(tmp_path, payload)

    result = _invoke(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert "\n\n## Security\n\nNo findings.\n" in markdown


def test_report_renders_an_empty_secrets_list(tmp_path: Path) -> None:
    payload = dict(_MINIMAL)
    payload["secrets"] = []
    _save(tmp_path, payload)

    result = _invoke(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert "\n\n## Secrets\n\nNo new secret in the diff.\n" in markdown


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        {"schema_version": 2},
        {**_MINIMAL, "schema_version": True},
        {**_MINIMAL, "exit_code": 9},
        {**_MINIMAL, "exit_code": True},
        {**_MINIMAL, "exit_code": 1.5},
        {key: value for key, value in _MINIMAL.items() if key != "commit"},
        {**_MINIMAL, "gates": [{"name": "crap", "status": "nope"}]},
        {**_MINIMAL, "gates": [{"name": 1, "status": "passed"}]},
        {**_MINIMAL, "gates": [{"status": "passed"}]},
        {**_MINIMAL, "gates": "crap"},
        {**_MINIMAL, "focus": [{"risk": 1}]},
        {**_MINIMAL, "top_crap": [{"name": "add"}]},
        {**_MINIMAL, "clones": [{"first_file": "a.py"}]},
        {**_MINIMAL, "tool_versions": {"lizard": 1}},
        {**_MINIMAL, "mutation": []},
        {**_MINIMAL, "mutation": {"no_coverage": {"total": "1", "functions": []}}},
        {**_MINIMAL, "dependencies": [{"origin": "app"}]},
        {**_MINIMAL, "old_debt": [{"name": "legacy"}]},
        {**_MINIMAL, "survivors": [{"id": "x"}]},
        {**_MINIMAL, "focus": [{"file": "app.py"}]},
        {**_MINIMAL, "gates": [{"name": "crap", "status": "passed", "reason": 1}]},
        {**_MINIMAL, "gates": [1]},
        {**_MINIMAL, "top_crap": [_metric(coverage=True)]},
        {**_MINIMAL, "top_crap": [_metric(cc="2")]},
        {**_MINIMAL, "top_crap": [_metric(crap=None)]},
        {**_MINIMAL, "top_crap": [_metric(delta="up")]},
        {**_MINIMAL, "top_crap": [_metric(start_line=True)]},
        {**_MINIMAL, "old_debt": [{"name": "legacy", "file": "old.py", "start_line": 9}]},
        {**_MINIMAL, "dependencies": [{"origin": "app", "destination": "core"}]},
        {**_MINIMAL, "clones": [{**_CLONE, "tokens": "10"}]},
        {**_MINIMAL, "clones": [{**_CLONE, "similarity": "high"}]},
        {**_MINIMAL, "clones": [{**_CLONE, "kind": None}]},
        {**_MINIMAL, "mutation": {"no_coverage": 1}},
        {**_MINIMAL, "mutation": {"no_coverage": {"total": 1, "functions": [{"file": "a.py"}]}}},
        {**_MINIMAL, "survivors": [{"id": "x", "function": "add", "file": "app.py"}]},
        {**_MINIMAL, "tool_versions": []},
        {**_MINIMAL, "dead_code": "nope"},
        {**_MINIMAL, "secrets": "nope"},
        {**_MINIMAL, "security": "nope"},
        {**_MINIMAL, "security": {}},
        {**_MINIMAL, "security": {"findings": []}},
        {**_MINIMAL, "security": {"unmeasured": []}},
        {**_MINIMAL, "security": {"findings": [], "unmeasured": [1]}},
        {**_MINIMAL, "security": {"findings": [], "unmeasured": "nope"}},
        {**_MINIMAL, "security": {"findings": {}, "unmeasured": []}},
        {**_MINIMAL, "security": {"findings": [_finding(disposition="nope")], "unmeasured": []}},
        {**_MINIMAL, "security": {"findings": [_finding(waiver="because")], "unmeasured": []}},
        {**_MINIMAL, "security": {"findings": [_finding(disposition="waived", waiver="")], "unmeasured": []}},
        {**_MINIMAL, "security": {"findings": [_finding(disposition="waived", waiver=None)], "unmeasured": []}},
        {**_MINIMAL, "security": {"findings": [_finding(line="4")], "unmeasured": []}},
        {**_MINIMAL, "security": {"findings": [_finding(tool=1)], "unmeasured": []}},
        {**_MINIMAL, "security": {"findings": [_finding(rule=1)], "unmeasured": []}},
        {**_MINIMAL, "security": {"findings": [_finding(file=1)], "unmeasured": []}},
        {**_MINIMAL, "security": {"findings": [_finding(end_line="4")], "unmeasured": []}},
        {**_MINIMAL, "security": {"findings": [_finding(severity=1)], "unmeasured": []}},
        {**_MINIMAL, "security": {"findings": [_finding(disposition=["fail"])], "unmeasured": []}},
        {**_MINIMAL, "typing": "nope"},
        {**_MINIMAL, "typing": {}},
        {**_MINIMAL, "typing": {"findings": [{"file": 1, "line": 4, "code": "assignment", "disposition": "blocking", "waiver_id": "typing:x"}]}},
        {**_MINIMAL, "typing": {"findings": [{"file": "src/app.py", "line": "4", "code": "assignment", "disposition": "blocking", "waiver_id": "typing:x"}]}},
        {**_MINIMAL, "typing": {"findings": [{"file": "src/app.py", "line": 4, "code": 1, "disposition": "blocking", "waiver_id": "typing:x"}]}},
        {**_MINIMAL, "typing": {"findings": [{"file": "src/app.py", "line": 4, "code": "assignment", "disposition": 1, "waiver_id": "typing:x"}]}},
        {**_MINIMAL, "typing": {"findings": [{"file": "src/app.py", "line": 4, "code": "assignment", "disposition": "blocking", "waiver_id": 1}]}},
        {**_MINIMAL, "typing": {"findings": "nope"}},
        {**_MINIMAL, "secrets": [1]},
        {**_MINIMAL, "secrets": [_secret(line=0)]},
        {**_MINIMAL, "secrets": [_secret(line="12")]},
        {**_MINIMAL, "secrets": [_secret(file=1)]},
        {**_MINIMAL, "secrets": [_secret(rule_id=1)]},
        {
            **_MINIMAL,
            "secrets": [
                _secret(file="src/old.py", line=2, rule_id="generic-api-key"),
                _secret(),
            ],
        },
        {**_MINIMAL, "secrets": [_secret(), _secret()]},
        {**_MINIMAL, "dead_code": {}},
        {**_MINIMAL, "dead_code": {"symbols": "nope"}},
        {**_MINIMAL, "dead_code": {"symbols": [1]}},
        {**_MINIMAL, "dead_code": {"symbols": [_dead(file=1)]}},
        {**_MINIMAL, "dead_code": {"symbols": [_dead(kind=1)]}},
        {**_MINIMAL, "dead_code": {"symbols": [_dead(line=0)]}},
        {**_MINIMAL, "dead_code": {"symbols": [_dead(line="4")]}},
        {**_MINIMAL, "dead_code": {"symbols": [_dead(name=1)]}},
        {**_MINIMAL, "dead_code": {"symbols": [_dead(kind="export")]}},
        {**_MINIMAL, "dead_code": {"symbols": [_dead(language="ruby")]}},
        {**_MINIMAL, "dead_code": {"symbols": [_dead(confidence=None)]}},
        {**_MINIMAL, "dead_code": {"symbols": [_dead(confidence=101)]}},
        {**_MINIMAL, "dead_code": {"symbols": [_dead(confidence=-1)]}},
        {**_MINIMAL, "dead_code": {"symbols": [_dead(confidence=True)]}},
        {**_MINIMAL, "dead_code": {"symbols": [_dead(language="typescript", kind="function")]}},
        {**_MINIMAL, "dead_code": {"symbols": [_dead(language="typescript", kind="export", confidence=60)]}},
        {**_MINIMAL, "dead_code": {"symbols": [_dead(waiver=1)]}},
        {**_MINIMAL, "commit": 1},
        {**_MINIMAL, "base": 1},
        {**_MINIMAL, "generated_at": 1},
        {**_MINIMAL, "reproduce": 1},
        {**_MINIMAL, "waivers": "nope"},
        {**_MINIMAL, "focus": "nope"},
        {**_MINIMAL, "top_crap": "nope"},
        {**_MINIMAL, "top_crap": [_metric(name=1)]},
        {**_MINIMAL, "old_debt": "nope"},
        {**_MINIMAL, "old_debt": [{"name": 1, "file": "old.py", "start_line": 9, "crap": 30}]},
        {
            **_MINIMAL,
            "old_debt": [{"name": "legacy", "file": "old.py", "start_line": "9", "crap": 30}],
        },
        {**_MINIMAL, "dependencies": "nope"},
        {**_MINIMAL, "dependencies": [{"origin": 1, "destination": "core", "rule": "cycle"}]},
        {**_MINIMAL, "old_dependencies": "nope"},
        {**_MINIMAL, "clones": "nope"},
        {**_MINIMAL, "survivors": "nope"},
        {**_MINIMAL, "survivors": [{"id": 1, "function": "add", "file": "app.py", "line": 4}]},
        {
            **_MINIMAL,
            "survivors": [{"id": "x", "function": "add", "file": 1, "line": 4}],
        },
        {**_MINIMAL, "mutation": {"no_coverage": {"total": 1, "functions": "nope"}}},
        {
            **_MINIMAL,
            "mutation": {
                "no_coverage": {"total": 1, "functions": [{"file": 1, "function": "add", "count": 1}]}
            },
        },
        {
            **_MINIMAL,
            "mutation": {
                "no_coverage": {
                    "total": 1,
                    "functions": [{"file": "a.py", "function": "add", "count": "1"}],
                }
            },
        },
    ],
)
def test_invalid_saved_report_exits_4(tmp_path: Path, payload: object) -> None:
    if isinstance(payload, str):
        directory = tmp_path / ".bob"
        directory.mkdir()
        saved = directory / "report.json"
        saved.write_text(payload)
    else:
        saved = _save(tmp_path, payload)

    result = _invoke(tmp_path, "report")

    assert result.returncode == 4
    assert result.stderr == f"invalid report: {saved}\n"
    assert not (tmp_path / ".bob" / "report.md").exists()


def test_report_accepts_a_null_mutation_and_empty_tools(tmp_path: Path) -> None:
    payload = dict(_MINIMAL)
    payload["mutation"] = None
    payload["tool_versions"] = {}
    _save(tmp_path, payload)

    result = _invoke(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert "- Tools: —" in markdown
    assert "## Surviving mutants" not in markdown


def test_report_rejects_bytes_that_are_not_utf8(tmp_path: Path) -> None:
    directory = tmp_path / ".bob"
    directory.mkdir()
    saved = directory / "report.json"
    saved.write_bytes(b"\xff")

    result = _invoke(tmp_path, "report")

    assert result.returncode == 4
    assert result.stderr == f"invalid report: {saved}\n"
    assert not (directory / "report.md").exists()


def test_report_rejects_an_output_parent_that_is_a_file(tmp_path: Path) -> None:
    _save(tmp_path, _MINIMAL, folder="saved")
    blocked = tmp_path / "out"
    blocked.write_text("keep\n")
    destination = blocked / "report.md"

    result = _invoke(tmp_path, "report", "--in", "saved", "--out", "out/report.md")

    assert result.returncode == 4
    assert result.stderr == f"could not write report: {destination}\n"
    assert blocked.read_text() == "keep\n"


def test_report_does_not_replace_a_directory_at_the_output_path(tmp_path: Path) -> None:
    _save(tmp_path, _MINIMAL, folder="saved")
    blocked = tmp_path / "out"
    blocked.mkdir()
    sentinel = tmp_path / "out.tmp"
    sentinel.write_text("sentinel\n")

    result = _invoke(tmp_path, "report", "--in", "saved", "--out", "out")

    assert result.returncode == 4
    assert result.stderr == f"could not write report: {blocked}\n"
    assert blocked.is_dir()
    assert list(blocked.iterdir()) == []
    assert not sentinel.exists()
