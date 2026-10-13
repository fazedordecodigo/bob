import json
import subprocess
from pathlib import Path

from helpers import run_bob


def test_check_gates_supply_blocks_an_undeclared_import(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "block")

    english = run_bob(repo, "check", "--base", "main", "--gates", "supply", "--lang", "en")
    en_payload = json.loads((repo / ".bob" / "report.json").read_text())
    en_md = (repo / ".bob" / "report.md").read_text()
    portuguese = run_bob(repo, "check", "--base", "main", "--gates", "supply", "--lang", "pt-BR")
    pt_payload = json.loads((repo / ".bob" / "report.json").read_text())
    pt_md = (repo / ".bob" / "report.md").read_text()

    assert english.returncode == 1
    assert portuguese.returncode == 1
    assert english.stdout == ""
    assert portuguese.stdout == ""
    assert en_payload["schema_version"] == 1
    assert en_payload["supply"] == pt_payload["supply"]
    assert en_payload["gates"] == pt_payload["gates"]
    assert en_payload["supply"]["findings"] == [
        {
            "kind": "undeclared",
            "file": "src/app.py",
            "module": "requests",
            "line": 1,
            "effect": "block",
            "waiver": None,
        }
    ]
    assert en_payload["gates"] == [
        {
            "name": "supply",
            "status": "failed",
            "reason": "undeclared import requests at src/app.py:1",
        }
    ]
    assert "## New dependencies" in en_md
    assert "undeclared import" in en_md
    assert "blocks" in en_md
    assert "## Dependências novas" in pt_md
    assert "import não declarado" in pt_md
    assert "bloqueia" in pt_md


def test_check_gates_supply_passes_when_the_import_is_waived(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "waived")
    bob = repo / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text(
        "waivers:\n"
        "  - id: supply:undeclared:src/app.py:requests\n"
        "    reason: local stub\n"
        "    author: ada\n"
        "    date: '2026-10-11'\n"
    )

    result = run_bob(repo, "check", "--base", "main", "--gates", "supply")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert result.stdout == ""
    assert payload["exit_code"] == 0
    assert payload["gates"] == [{"name": "supply", "status": "passed", "reason": None}]
    assert payload["supply"]["findings"] == [
        {
            "kind": "undeclared",
            "file": "src/app.py",
            "module": "requests",
            "line": 1,
            "effect": "waived",
            "waiver": "supply:undeclared:src/app.py:requests",
        }
    ]
    assert (
        "| `requests` | `src/app.py:1` | undeclared, waived as "
        "`supply:undeclared:src/app.py:requests` | waived |"
    ) in markdown


def test_check_gates_supply_passes_when_the_diff_adds_no_dependency(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "clean", source="x = 1\n", replacement="x = 2\n")

    result = run_bob(repo, "check", "--base", "main", "--gates", "supply")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 0
    assert payload["supply"] == {
        "measured": ["python"],
        "skipped": [],
        "findings": [],
    }
    assert payload["gates"] == [{"name": "supply", "status": "passed", "reason": None}]
    assert "No new dependency in the diff." in markdown
    assert "## New dependencies" in markdown


def test_check_omits_supply_when_the_gate_was_not_requested(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "idle")

    result = run_bob(repo, "check", "--base", "main", "--gates", "supply,nope")
    mixed = json.loads((repo / ".bob" / "report.json").read_text())
    skipped = run_bob(repo, "check", "--base", "main", "--gates", "nope")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert result.returncode == 1
    assert mixed["exit_code"] == 1
    assert [gate["name"] for gate in mixed["gates"]] == ["supply", "nope"]
    assert mixed["gates"][1] == {
        "name": "nope",
        "status": "not_run",
        "reason": "gate not implemented in this slice",
    }
    assert skipped.returncode == 0
    assert "supply" not in payload
    assert "## New dependencies" not in (repo / ".bob" / "report.md").read_text()


def _repo(tmp_path: Path, source: str = "x = 1\n", replacement: str = "import requests\n") -> Path:
    repo = tmp_path
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = []\n'
    )
    (repo / "src" / "app.py").write_text(source)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "bob-test@example.com")
    _git(repo, "config", "user.name", "bob-test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    _git(repo, "checkout", "-b", "head")
    (repo / "src" / "app.py").write_text(replacement)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "change")
    return repo


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
