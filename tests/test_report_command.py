from __future__ import annotations

import json
from pathlib import Path

import pytest
from helpers import run_bob

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

    result = run_bob(tmp_path, "report")

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == ""
    assert (tmp_path / ".bob" / "report.md").read_text() == _EN
    assert saved.read_bytes() == before
    assert not (tmp_path / ".bob" / "report.md.tmp").exists()


def test_report_follows_the_language_flag(tmp_path: Path) -> None:
    _save(tmp_path, _MINIMAL)

    result = run_bob(tmp_path, "report", "--lang", "pt-BR")

    assert result.returncode == 0
    assert (tmp_path / ".bob" / "report.md").read_text() == _PT


def test_report_language_before_the_command(tmp_path: Path) -> None:
    _save(tmp_path, _MINIMAL)

    result = run_bob(tmp_path, "--lang", "pt-BR", "report")

    assert result.returncode == 0
    assert (tmp_path / ".bob" / "report.md").read_text() == _PT


def test_report_help_follows_the_language(tmp_path: Path) -> None:
    english = run_bob(tmp_path, "report", "--help")
    portuguese = run_bob(tmp_path, "report", "--lang", "pt-BR", "--help")

    assert english.returncode == 0
    assert "Render report.json from a directory as Markdown" in english.stdout
    assert portuguese.returncode == 0
    assert "Renderiza o report.json de uma pasta como Markdown" in portuguese.stdout
    assert not (tmp_path / ".bob").exists()


def test_report_reads_another_directory_and_writes_another_file(tmp_path: Path) -> None:
    _save(tmp_path, _MINIMAL, folder="saved")

    result = run_bob(tmp_path, "report", "--in", "saved", "--out", "out/summary.md")

    assert result.returncode == 0
    assert (tmp_path / "out" / "summary.md").read_text() == _EN
    assert not (tmp_path / ".bob").exists()
    assert not (tmp_path / "saved" / "report.md").exists()


def test_report_is_idempotent(tmp_path: Path) -> None:
    _save(tmp_path, _MINIMAL)
    first = run_bob(tmp_path, "report")
    written = (tmp_path / ".bob" / "report.md").read_bytes()

    second = run_bob(tmp_path, "report")

    assert first.returncode == 0
    assert second.returncode == 0
    assert (tmp_path / ".bob" / "report.md").read_bytes() == written


@pytest.mark.parametrize("code", [0, 1, 2, 3, 4])
def test_report_returns_the_stored_exit_code(tmp_path: Path, code: int) -> None:
    payload = dict(_MINIMAL)
    payload["exit_code"] = code
    _save(tmp_path, payload)

    result = run_bob(tmp_path, "report")

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
            "delta": None,
        }
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

    result = run_bob(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 1
    assert "- ❌ `crap`: failed (over the limit)" in markdown
    assert "- ⚠️ `dry`: warning" in markdown
    assert "- ❌ `deps`: failed (tool missing)" in markdown
    assert "- ⏭️ `mutate`: not run" in markdown
    assert "- `app.py` (risk 12, clone)" in markdown
    assert "| add | app.py:4 | 2 | 50% | 2.25 | — |" in markdown
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
        }
    ]
    payload["mutation"] = {
        "no_coverage": {"total": 1, "functions": [{"file": "app.py", "function": "add", "count": 1}]}
    }
    payload["survivors"] = [
        {"id": "app.add__mutmut_1", "function": "add", "file": "app.py", "line": 4}
    ]
    payload["waivers"] = [
        {"id": "fn", "reason": "because", "author": "ada", "date": "2026-10-11"}
    ]
    _save(tmp_path, payload)

    result = run_bob(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert "legacy" in markdown
    assert "old.py:9" in markdown
    assert "similarity exact" in markdown
    assert "`app.add__mutmut_1`" in markdown
    assert "| `fn` | because | ada | 2026-10-11 |" in markdown
    assert "| add | app.py | 1 |" in markdown


def test_missing_report_exits_4_and_writes_nothing(tmp_path: Path) -> None:
    result = run_bob(tmp_path, "report", "--lang", "pt-BR")
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

    result = run_bob(tmp_path, "report")

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

    result = run_bob(tmp_path, "report")

    assert result.returncode == 4
    assert result.stderr == f"invalid report: {saved}\n"
    assert not (tmp_path / ".bob" / "report.md").exists()


def test_report_accepts_a_null_mutation_and_empty_tools(tmp_path: Path) -> None:
    payload = dict(_MINIMAL)
    payload["mutation"] = None
    payload["tool_versions"] = {}
    _save(tmp_path, payload)

    result = run_bob(tmp_path, "report")
    markdown = (tmp_path / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert "- Tools: —" in markdown
    assert "## Surviving mutants" not in markdown


def test_report_rejects_bytes_that_are_not_utf8(tmp_path: Path) -> None:
    directory = tmp_path / ".bob"
    directory.mkdir()
    saved = directory / "report.json"
    saved.write_bytes(b"\xff")

    result = run_bob(tmp_path, "report")

    assert result.returncode == 4
    assert result.stderr == f"invalid report: {saved}\n"
    assert not (directory / "report.md").exists()


def test_report_rejects_an_output_parent_that_is_a_file(tmp_path: Path) -> None:
    _save(tmp_path, _MINIMAL, folder="saved")
    blocked = tmp_path / "out"
    blocked.write_text("keep\n")
    destination = blocked / "report.md"

    result = run_bob(tmp_path, "report", "--in", "saved", "--out", "out/report.md")

    assert result.returncode == 4
    assert result.stderr == f"could not write report: {destination}\n"
    assert blocked.read_text() == "keep\n"


def test_report_does_not_replace_a_directory_at_the_output_path(tmp_path: Path) -> None:
    _save(tmp_path, _MINIMAL, folder="saved")
    blocked = tmp_path / "out"
    blocked.mkdir()

    result = run_bob(tmp_path, "report", "--in", "saved", "--out", "out")

    assert result.returncode == 4
    assert result.stderr == f"could not write report: {blocked}\n"
    assert blocked.is_dir()
    assert list(blocked.iterdir()) == []
    assert not (tmp_path / "out.tmp").exists()
