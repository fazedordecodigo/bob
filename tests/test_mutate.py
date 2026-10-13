"""CLI `bob mutate` / `bob waive` no repo-fixture Python.

Seams combinados em docs/SPEC.md (aceite da issue #3):

1. CLI sobre o fixture: dado um diff, `bob mutate` / `bob check` / `bob waive`
   produzem exit code, linhas do `report.md` e o cache `.bob/mutation-cache.json`.
2. Adaptador mutmut: saída bruta da versão pinada vira o modelo `Mutant`.
   O teste de contrato desse seam fica em `test_mutmut_adapter.py`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator
from pytest import MonkeyPatch

from bob_quality.models import Mutant
from bob_quality.waivers import Waiver, _matching_reason, _row_mutant, _status, add_waiver

from helpers import (
    commit_on_branch,
    commit_on_main,
    init_python_repo,
    run_bob,
    run_bob_subprocess,
)

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "src/bob_quality/schemas/report_v1.json").read_text()
)

FIXTURE = Path(__file__).parent / "fixtures" / "python_app"
CLASSIFY = (FIXTURE / "cases" / "survive_classify.py").read_text()
WEAK_TEST = (FIXTURE / "cases" / "test_classify_weak.py").read_text()
ADD_AND_SCALE = (FIXTURE / "cases" / "add_and_scale.py").read_text()
ADD_TOUCHED = (FIXTURE / "cases" / "add_touched.py").read_text()
ADD_AND_SCALE_TEST = (FIXTURE / "cases" / "test_add_and_scale.py").read_text()
STRONG_TEST = (FIXTURE / "cases" / "test_classify_strong.py").read_text()
ORPHAN = (FIXTURE / "cases" / "orphan.py").read_text()


def _repo_with_surviving_mutant(tmp_path: Path) -> Path:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "weak", "src/app/weak.py", CLASSIFY, "add classify")
    commit_on_branch(repo, "weak", "tests/test_classify.py", WEAK_TEST, "weak classify test")
    return repo


def test_mutate_exits_3_when_changed_function_has_unwaived_survivor(tmp_path: Path) -> None:
    repo = _repo_with_surviving_mutant(tmp_path)

    result = run_bob_subprocess(repo, "mutate", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    mutate = next(gate for gate in payload["gates"] if gate["name"] == "mutate")

    assert result.returncode == 3
    assert mutate["status"] == "failed"
    assert "classify" in markdown
    assert "src/app/weak.py" in markdown


def test_uncovered_mutants_in_the_diff_fail_with_exit_3(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "orphan", "src/app/orphan.py", ORPHAN, "add orphan")

    result = run_bob_subprocess(repo, "mutate", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    mutate = next(gate for gate in payload["gates"] if gate["name"] == "mutate")

    assert result.returncode == 3
    assert mutate == {
        "name": "mutate",
        "status": "failed",
        "reason": "2 mutants without a test",
    }
    assert payload["mutation"]["no_coverage"] == {
        "total": 2,
        "functions": [{"file": "src/app/orphan.py", "function": "orphan", "count": 2}],
    }
    assert "## Mutants without tests" in markdown
    assert "❌ Total: 2. Blocks." in markdown
    assert "| orphan | src/app/orphan.py | 2 |" in markdown
    Draft202012Validator(SCHEMA).validate(payload)


def test_mutate_exits_2_when_baseline_tests_fail(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "broken",
        "src/app/safe.py",
        "def add(left: int, right: int) -> int:\n    return left + right  # soma\n",
        "touch add",
    )
    commit_on_branch(
        repo,
        "broken",
        "tests/test_safe.py",
        "from app.safe import add\n\ndef test_add() -> None:\n    assert add(1, 2) == 0\n",
        "break baseline tests",
    )

    result = run_bob_subprocess(repo, "mutate", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    mutate = next(gate for gate in payload["gates"] if gate["name"] == "mutate")

    assert result.returncode == 2
    assert mutate["status"] == "not_run"
    assert mutate["reason"]
    assert "baseline" in mutate["reason"]


def test_local_check_skips_mutation_unless_gates_mutate(tmp_path: Path) -> None:
    repo = _repo_with_surviving_mutant(tmp_path)

    plain = run_bob(repo, "check", "--base", "main")
    plain_payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert plain.returncode != 3
    assert not (repo / ".bob" / "mutation-cache.json").exists()
    assert all(gate["name"] != "mutate" for gate in plain_payload["gates"])
    assert "mutmut" not in plain_payload["tool_versions"]

    forced = run_bob_subprocess(repo, "check", "--base", "main", "--gates", "mutate")
    forced_payload = json.loads((repo / ".bob" / "report.json").read_text())
    mutate = next(gate for gate in forced_payload["gates"] if gate["name"] == "mutate")

    assert forced.returncode == 3
    assert mutate["status"] == "failed"
    assert (repo / ".bob" / "mutation-cache.json").is_file()


def test_waive_rejects_a_reason_that_is_missing_blank_or_multiline(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")

    missing = run_bob(repo, "waive", "classify")
    blank = run_bob(repo, "waive", "classify", "--reason", "   ")
    multiline = run_bob(repo, "waive", "classify", "--reason", "uma linha\noutra")

    assert missing.returncode != 0
    assert missing.stderr == "waiver without a reason: pass --reason with one line\n"
    assert blank.returncode != 0
    assert multiline.returncode != 0
    assert not (repo / ".bob" / "waivers.yaml").exists()


def test_waive_puts_the_reason_at_the_top_of_the_report(tmp_path: Path) -> None:
    repo = _repo_with_surviving_mutant(tmp_path)
    reason = "o contrato exige estritamente maior que zero"

    saved = run_bob(repo, "waive", "classify", "--reason", reason)
    result = run_bob_subprocess(repo, "mutate", "--base", "main")
    markdown = (repo / ".bob" / "report.md").read_text()
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    stored = (repo / ".bob" / "waivers.yaml").read_text()
    head = markdown.split("## Verdict")[0]

    assert saved.returncode == 0
    assert result.returncode == 0
    assert markdown.startswith("# bob report\n\n## Waivers\n")
    assert reason in head
    assert "bob-test" in head
    assert reason in stored
    assert payload["waivers"][0]["reason"] == reason
    assert payload["waivers"][0]["author"] == "bob-test"
    assert payload["exit_code"] == 0


def test_only_changed_functions_are_mutated_and_clean_ones_are_not_remutated(
    tmp_path: Path,
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/safe.py", ADD_AND_SCALE, "add and scale")
    commit_on_main(repo, "tests/test_safe.py", ADD_AND_SCALE_TEST, "test add and scale")
    commit_on_branch(repo, "touch-add", "src/app/safe.py", ADD_TOUCHED, "comment inside add")

    first = run_bob_subprocess(repo, "mutate", "--base", "main")
    cache_path = repo / ".bob" / "mutation-cache.json"
    cache = json.loads(cache_path.read_text())
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    functions = cache["functions"]

    markdown = (repo / ".bob" / "report.md").read_text()
    mutate = next(gate for gate in payload["gates"] if gate["name"] == "mutate")

    assert first.returncode == 0
    assert mutate["status"] == "passed"
    assert mutate["reason"] is None
    assert payload["mutation"]["no_coverage"] == {"total": 0, "functions": []}
    assert "## Mutants without tests\n\nNo mutants without tests." in markdown
    assert "src/app/safe.py::add" in payload["mutation"]["remutated"]
    assert "src/app/safe.py::scale" not in payload["mutation"]["remutated"]
    assert "src/app/safe.py::scale" not in functions
    assert functions["src/app/safe.py::add"]["mutants"]
    assert functions["src/app/safe.py::add"]["mutants"][0]["operator"] != "SENTINEL"

    functions["src/app/safe.py::add"]["mutants"][0]["operator"] = "SENTINEL"
    cache_path.write_text(json.dumps(cache, indent=2) + "\n")

    second = run_bob_subprocess(repo, "mutate", "--base", "main")
    again = json.loads(cache_path.read_text())
    second_payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert second.returncode == 0
    assert again["functions"]["src/app/safe.py::add"]["mutants"][0]["operator"] == "SENTINEL"
    assert "src/app/safe.py::add" in second_payload["mutation"]["reused"]
    assert "src/app/safe.py::add" not in second_payload["mutation"]["remutated"]


def test_functions_with_survivors_are_remutated_even_when_the_hash_matches(
    tmp_path: Path,
) -> None:
    repo = _repo_with_surviving_mutant(tmp_path)

    first = run_bob_subprocess(repo, "mutate", "--base", "main")
    assert first.returncode == 3

    commit_on_branch(repo, "weak", "tests/test_classify.py", STRONG_TEST, "kill the survivors")
    second = run_bob_subprocess(repo, "mutate", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert second.returncode == 0
    assert "src/app/weak.py::classify" in payload["mutation"]["remutated"]
    assert payload["survivors"] == []


def test_hand_written_waiver_without_author_is_rejected(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    bob = repo / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text(
        "waivers:\n  - id: classify\n    reason: falta o autor\n    date: '2026-10-11'\n",
        encoding="utf-8",
    )

    result = run_bob_subprocess(repo, "mutate", "--base", "main")

    assert result.returncode == 4
    assert result.stderr == ".bob/waivers.yaml: waivers[0].author must be a string\n"
    assert result.stdout == ""
    assert not (bob / "report.md").exists()
    assert not (bob / "report.json").exists()


def test_check_lists_an_existing_waiver_at_the_top(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    bob = repo / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text(
        "waivers:\n"
        "  - id: classify\n"
        "    reason: o contrato exige estritamente maior que zero\n"
        "    author: bob-test\n"
        "    date: '2026-10-11'\n",
        encoding="utf-8",
    )

    result = run_bob(repo, "check", "--base", "main", "--gates", "crap")
    markdown = (repo / ".bob" / "report.md").read_text()
    head = markdown.split("## Verdict")[0]

    assert result.returncode == 0
    assert markdown.startswith("# bob report\n\n## Waivers\n")
    assert "o contrato exige estritamente maior que zero" in head


def test_removed_waiver_fails_the_survivor_again(tmp_path: Path) -> None:
    repo = _repo_with_surviving_mutant(tmp_path)
    reason = "o contrato exige estritamente maior que zero"

    assert run_bob_subprocess(repo, "mutate", "--base", "main").returncode == 3
    assert run_bob(repo, "waive", "classify", "--reason", reason).returncode == 0
    assert run_bob_subprocess(repo, "mutate", "--base", "main").returncode == 0

    (repo / ".bob" / "waivers.yaml").unlink()
    result = run_bob_subprocess(repo, "mutate", "--base", "main")
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 3
    assert reason not in markdown.split("## Verdict")[0]


def test_waive_rejects_an_id_that_is_not_a_survivor(tmp_path: Path) -> None:
    bob = tmp_path / ".bob"
    bob.mkdir()
    (bob / "mutation-cache.json").write_text(
        json.dumps(
            {
                "functions": {
                    "src/app/a.py::add": {
                        "mutants": [
                            {
                                "id": "app.a.x_add__mutmut_1",
                                "function": "add",
                                "file": "src/app/a.py",
                                "status": "killed",
                            },
                            {
                                "id": "app.a.x_orphan__mutmut_1",
                                "function": "orphan",
                                "file": "src/app/a.py",
                                "status": "no_coverage",
                            },
                            {
                                "id": "app.a.x_wait__mutmut_1",
                                "function": "wait",
                                "file": "src/app/a.py",
                                "status": "timeout",
                            },
                            {
                                "id": "app.a.x_keep__mutmut_1",
                                "function": "keep",
                                "file": "src/app/a.py",
                                "status": "survived",
                            },
                        ]
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    missing = run_bob(tmp_path, "waive", "missing", "--reason", "because")
    uncovered = run_bob(tmp_path, "waive", "orphan", "--reason", "because", bob_lang="pt-BR")
    killed = run_bob(tmp_path, "waive", "add", "--reason", "because")
    timed = run_bob(tmp_path, "waive", "wait", "--reason", "because")

    assert missing.returncode == 4
    assert missing.stderr == "waiver does not match a survivor: missing\n"
    assert uncovered.returncode == 4
    assert uncovered.stderr == "waiver não cobre mutante sem teste: orphan\n"
    assert killed.returncode == 4
    assert killed.stderr == "waiver does not match a survivor: add\n"
    assert timed.returncode == 4
    assert timed.stderr == "waiver does not match a survivor: wait\n"
    assert not (bob / "waivers.yaml").exists()

    saved = run_bob(tmp_path, "waive", "keep", "--reason", "because")
    assert saved.returncode == 0
    assert "keep" in (bob / "waivers.yaml").read_text(encoding="utf-8")


def test_waive_rejects_a_cache_without_a_survivor_list(tmp_path: Path) -> None:
    bob = tmp_path / ".bob"
    bob.mkdir()
    cache = bob / "mutation-cache.json"
    cache.write_text("[]\n", encoding="utf-8")
    mapping = run_bob(tmp_path, "waive", "add", "--reason", "because")
    cache.write_text('{"functions": []}\n', encoding="utf-8")
    empty = run_bob(tmp_path, "waive", "add", "--reason", "because")
    cache.write_text(
        '{"functions": {"src/app/a.py::add": {"mutants": [null, {"status": "survived"}]}}}\n',
        encoding="utf-8",
    )
    junk = run_bob(tmp_path, "waive", "add", "--reason", "because")

    assert mapping.returncode == 4
    assert mapping.stderr == "invalid mutation cache: not a mapping\n"
    assert empty.returncode == 4
    assert empty.stderr == "waiver does not match a survivor: add\n"
    assert junk.returncode == 4
    assert junk.stderr == "waiver does not match a survivor: add\n"
    assert not (bob / "waivers.yaml").exists()


def test_waive_rejects_a_cache_that_is_not_json(tmp_path: Path) -> None:
    bob = tmp_path / ".bob"
    bob.mkdir()
    (bob / "mutation-cache.json").write_text("{", encoding="utf-8")

    result = run_bob(tmp_path, "waive", "add", "--reason", "because")

    assert result.returncode == 4
    assert result.stderr == (
        "invalid mutation cache: Expecting property name enclosed in double quotes:"
        " line 1 column 2 (char 1)\n"
    )
    assert not (bob / "waivers.yaml").exists()


def test_waive_creates_a_missing_directory(tmp_path: Path) -> None:
    repo = tmp_path / "missing"

    waiver = add_waiver(repo, "keep", "because")

    assert waiver.id == "keep"
    assert (repo / ".bob" / "waivers.yaml").is_file()


def test_an_empty_target_names_the_missing_target(tmp_path: Path) -> None:
    result = run_bob(tmp_path, "waive", "   ", "--reason", "because")

    assert result.returncode == 4
    assert result.stderr == "waiver without a target\n"
    assert result.stdout == ""


def test_a_new_waiver_records_the_repo_author_the_utc_date_and_the_yaml_order(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    real = datetime

    class DateTime:
        @staticmethod
        def now(tz: timezone | None = None) -> datetime:
            assert tz is timezone.utc
            return real(2026, 1, 2, 15, tzinfo=timezone.utc)

    monkeypatch.setattr("bob_quality.waivers.datetime", DateTime)

    waiver = add_waiver(repo, "keep", "não")

    assert waiver.author == "bob-test"
    assert waiver.date == "2026-01-02"
    assert (repo / ".bob" / "waivers.yaml").read_text(encoding="utf-8") == (
        "waivers:\n"
        "- author: bob-test\n"
        "  date: '2026-01-02'\n"
        "  id: keep\n"
        "  reason: não\n"
    )


def test_a_cache_row_keeps_string_fields_and_drops_an_unknown_status() -> None:
    kept = _row_mutant(
        {"id": "app.a.x_add__mutmut_1", "status": "killed", "function": "add", "file": "src/a.py"}
    )
    blank = _row_mutant({"id": "app.a.x_add__mutmut_1", "status": "timeout", "function": 1, "file": 2})

    assert kept == Mutant("app.a.x_add__mutmut_1", "add", "src/a.py", 0, "", "killed")
    assert blank == Mutant("app.a.x_add__mutmut_1", "", "", 0, "", "timeout")
    assert _row_mutant({"id": "app.a.x_add__mutmut_1", "status": "nope"}) is None
    assert _row_mutant({"id": 1, "status": "killed"}) is None
    assert _row_mutant({"id": "app.a.x_add__mutmut_1", "status": 1}) is None
    assert _row_mutant(["id"]) is None
    assert _status("killed") == "killed"
    assert _status("timeout") == "timeout"
    assert _status("no_coverage") == "no_coverage"
    assert _status("survived") == "survived"


def test_a_waiver_matches_the_mutant_it_names() -> None:
    mutant = Mutant("app.a.x_add__mutmut_1", "add", "src/a.py", 1, "AOR", "survived")
    named = Waiver("add", "because", "bob-test", "2026-01-02")
    other = Waiver("scale", "nope", "bob-test", "2026-01-02")

    assert _matching_reason(mutant, [other, named]) == "because"
    assert _matching_reason(mutant, [other]) is None
    assert _matching_reason(mutant, []) is None


def test_harden_skill_kills_mutants_without_weakening_production_code() -> None:
    text = (Path(__file__).resolve().parents[1] / "skills/harden/SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "name: harden" in text
    assert "dentro do razoável" in text
    assert "nunca enfraquecer o código de produção" in text
    assert "bob waive" in text
