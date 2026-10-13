"""CLI `bob mutate` / `bob waive` no repo-fixture Python.

Seams combinados em docs/SPEC.md (aceite da issue #3):

1. CLI sobre o fixture: dado um diff, `bob mutate` / `bob check` / `bob waive`
   produzem exit code, linhas do `report.md` e o cache `.bob/mutation-cache.json`.
2. Adaptador mutmut: saída bruta da versão pinada vira o modelo `Mutant`.
   O teste de contrato desse seam fica em `test_mutmut_adapter.py`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from helpers import commit_on_branch, commit_on_main, init_python_repo, run_bob

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
METHOD = (FIXTURE / "cases" / "survive_method.py").read_text()
METHOD_WEAK_TEST = (FIXTURE / "cases" / "test_method_weak.py").read_text()
NESTED_METHOD = """\
class Shelf:
    class Slot:
        def label(self, n: int) -> str:
            return "full" if n > 0 else "empty"
"""


def _repo_with_surviving_mutant(tmp_path: Path) -> Path:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "weak", "src/app/weak.py", CLASSIFY, "add classify")
    commit_on_branch(repo, "weak", "tests/test_classify.py", WEAK_TEST, "weak classify test")
    return repo


def _repo_with_surviving_method(tmp_path: Path) -> Path:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "method", "src/app/gauge.py", METHOD, "add Gauge.classify")
    commit_on_branch(repo, "method", "tests/test_gauge.py", METHOD_WEAK_TEST, "weak Gauge test")
    return repo


def test_mutate_exits_3_when_changed_function_has_unwaived_survivor(tmp_path: Path) -> None:
    repo = _repo_with_surviving_mutant(tmp_path)

    result = run_bob(repo, "mutate", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    mutate = next(gate for gate in payload["gates"] if gate["name"] == "mutate")

    assert result.returncode == 3
    assert mutate["status"] == "failed"
    assert "classify" in markdown
    assert "src/app/weak.py" in markdown


def _skip_inside_mutmut() -> None:
    if os.environ.get("MUTANT_UNDER_TEST") or os.environ.get("BOB_SKIP_MUTMUT_DOGFOOD"):
        pytest.skip("não reentrar na coleta do mutmut")


def test_mutate_exits_3_when_a_changed_method_has_an_unwaived_survivor(tmp_path: Path) -> None:
    _skip_inside_mutmut()
    repo = _repo_with_surviving_method(tmp_path)

    result = run_bob(repo, "mutate", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    cache = json.loads((repo / ".bob" / "mutation-cache.json").read_text())
    mutate = next(gate for gate in payload["gates"] if gate["name"] == "mutate")
    entry = cache["functions"]["src/app/gauge.py::Gauge.classify"]

    assert result.returncode == 3
    assert mutate == {
        "name": "mutate",
        "status": "failed",
        "reason": (
            "survivor without waiver: Gauge.classify@src/app/gauge.py:3,"
            " Gauge.classify@src/app/gauge.py:5, Gauge.classify@src/app/gauge.py:5"
        ),
    }
    assert payload["mutation"]["remutated"] == ["src/app/gauge.py::Gauge.classify"]
    assert [
        (row["id"], row["function"], row["file"], row["line"], row["operator"])
        for row in payload["survivors"]
    ] == [
        (
            "app.gauge.xǁGaugeǁclassify__mutmut_1",
            "Gauge.classify",
            "src/app/gauge.py",
            3,
            "if n > 0: -> if n >= 0:",
        ),
        (
            "app.gauge.xǁGaugeǁclassify__mutmut_5",
            "Gauge.classify",
            "src/app/gauge.py",
            5,
            'return "nonpos" -> return "XXnonposXX"',
        ),
        (
            "app.gauge.xǁGaugeǁclassify__mutmut_6",
            "Gauge.classify",
            "src/app/gauge.py",
            5,
            'return "nonpos" -> return "NONPOS"',
        ),
    ]
    assert (entry["name"], entry["start_line"], entry["end_line"]) == ("Gauge.classify", 2, 5)
    Draft202012Validator(SCHEMA).validate(payload)


def test_a_waiver_on_the_method_label_clears_the_method(tmp_path: Path) -> None:
    _skip_inside_mutmut()
    repo = _repo_with_surviving_method(tmp_path)
    reason = "o contrato exige estritamente maior que zero"

    first = run_bob(repo, "mutate", "--base", "main")
    saved = run_bob(repo, "waive", "src/app/gauge.py::Gauge.classify", "--reason", reason)
    result = run_bob(repo, "mutate", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert first.returncode == 3
    assert saved.returncode == 0
    assert result.returncode == 0
    assert payload["mutation"]["remutated"] == []
    assert payload["mutation"]["reused"] == ["src/app/gauge.py::Gauge.classify"]
    assert [(row["id"], row["waiver"]) for row in payload["survivors"]] == [
        ("app.gauge.xǁGaugeǁclassify__mutmut_1", reason),
        ("app.gauge.xǁGaugeǁclassify__mutmut_5", reason),
        ("app.gauge.xǁGaugeǁclassify__mutmut_6", reason),
    ]


def test_a_lone_change_to_a_nested_class_method_still_exits_4(tmp_path: Path) -> None:
    """O mutmut 3.8 não gera mutante para o método de uma classe aninhada."""
    _skip_inside_mutmut()
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "nested", "src/app/shelf.py", NESTED_METHOD, "add Shelf.Slot.label")

    result = run_bob(repo, "mutate", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    mutate = next(gate for gate in payload["gates"] if gate["name"] == "mutate")

    assert result.returncode == 4
    assert mutate == {"name": "mutate", "status": "not_run", "reason": "nothing matches"}


def test_uncovered_mutants_warn_without_changing_the_exit_code(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "orphan", "src/app/orphan.py", ORPHAN, "add orphan")

    result = run_bob(repo, "mutate", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    mutate = next(gate for gate in payload["gates"] if gate["name"] == "mutate")

    assert result.returncode == 0
    assert mutate == {
        "name": "mutate",
        "status": "warn",
        "reason": "2 mutants without a test",
    }
    assert payload["mutation"]["no_coverage"] == {
        "total": 2,
        "functions": [{"file": "src/app/orphan.py", "function": "orphan", "count": 2}],
    }
    assert "## Mutants without tests" in markdown
    assert "⚠️ Total: 2. Does not block." in markdown
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

    result = run_bob(repo, "mutate", "--base", "main")
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

    forced = run_bob(repo, "check", "--base", "main", "--gates", "mutate")
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
    result = run_bob(repo, "mutate", "--base", "main")
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

    first = run_bob(repo, "mutate", "--base", "main")
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

    second = run_bob(repo, "mutate", "--base", "main")
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

    first = run_bob(repo, "mutate", "--base", "main")
    assert first.returncode == 3

    commit_on_branch(repo, "weak", "tests/test_classify.py", STRONG_TEST, "kill the survivors")
    second = run_bob(repo, "mutate", "--base", "main")
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

    result = run_bob(repo, "mutate", "--base", "main")

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

    assert run_bob(repo, "mutate", "--base", "main").returncode == 3
    assert run_bob(repo, "waive", "classify", "--reason", reason).returncode == 0
    assert run_bob(repo, "mutate", "--base", "main").returncode == 0

    (repo / ".bob" / "waivers.yaml").unlink()
    result = run_bob(repo, "mutate", "--base", "main")
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 3
    assert reason not in markdown.split("## Verdict")[0]


def test_harden_skill_kills_mutants_without_weakening_production_code() -> None:
    text = (Path(__file__).resolve().parents[1] / "skills/harden/SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "name: harden" in text
    assert "dentro do razoável" in text
    assert "nunca enfraquecer o código de produção" in text
    assert "bob waive" in text
