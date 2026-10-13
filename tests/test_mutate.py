"""CLI `bob mutate` / `bob waive` no repo-fixture Python.

Seams combinados em docs/SPEC.md (aceite da issue #3):

1. CLI sobre o fixture: dado um diff, `bob mutate` / `bob check` / `bob waive`
   produzem exit code, linhas do `report.md` e o cache `.bob/mutation-cache.json`.
2. Adaptador mutmut: saída bruta da versão pinada vira o modelo `Mutant`.
   O teste de contrato desse seam fica em `test_mutmut_adapter.py`.
"""

from __future__ import annotations

import json
import signal
import subprocess
import sys
from pathlib import Path

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
TALLY = (FIXTURE / "cases" / "tally.py").read_text()
TALLY_WEAK_TEST = (FIXTURE / "cases" / "test_tally_weak.py").read_text()
TALLY_LINE_5 = TALLY.replace("return n + extra", "return n + extra  # total")
TALLY_LINE_3 = TALLY.replace("n = n + 1", "n = n + 1  # bump")
TALLY_KEY = "src/app/tally.py::tally"
LINE_2_OUTSIDE = "| src/app/tally.py:2 (outside the diff; does not block) |"


def _repo_with_surviving_mutant(tmp_path: Path) -> Path:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "weak", "src/app/weak.py", CLASSIFY, "add classify")
    commit_on_branch(repo, "weak", "tests/test_classify.py", WEAK_TEST, "weak classify test")
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


def test_uncovered_mutants_in_the_diff_fail_with_exit_3(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "orphan", "src/app/orphan.py", ORPHAN, "add orphan")

    result = run_bob(repo, "mutate", "--base", "main")
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


def _survivors(repo: Path) -> list[dict[str, object]]:
    return json.loads((repo / ".bob" / "report.json").read_text())["survivors"]


def test_waive_puts_the_reason_at_the_top_of_the_report(tmp_path: Path) -> None:
    repo = _repo_with_surviving_mutant(tmp_path)
    reason = "o contrato exige estritamente maior que zero"

    assert run_bob(repo, "mutate", "--base", "main").returncode == 3
    target = f"{_survivors(repo)[0]['file']}::classify"
    saved = run_bob(repo, "waive", target, "--reason", reason)
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
        "  - id: src/app/weak.py::classify\n"
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
    waived = run_bob(repo, "waive", "src/app/weak.py::classify", "--reason", reason)
    assert waived.returncode == 0
    assert run_bob(repo, "mutate", "--base", "main").returncode == 0

    (repo / ".bob" / "waivers.yaml").unlink()
    result = run_bob(repo, "mutate", "--base", "main")
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 3
    assert reason not in markdown.split("## Verdict")[0]


def test_waiving_each_target_from_the_report_passes_the_next_run(tmp_path: Path) -> None:
    repo = _repo_with_surviving_mutant(tmp_path)

    assert run_bob(repo, "mutate", "--base", "main").returncode == 3
    targets = [str(item["target"]) for item in _survivors(repo)]
    saved = [
        run_bob(repo, "waive", target, "--reason", "equivalente no contrato").returncode
        for target in targets
    ]
    result = run_bob(repo, "mutate", "--base", "main")

    assert targets
    assert all(target.startswith("src/app/weak.py::classify::") for target in targets)
    assert saved == [0] * len(targets)
    assert result.returncode == 0
    assert all(item["waiver"] == "equivalente no contrato" for item in _survivors(repo))


def test_waive_rejects_a_bare_function_name_and_keeps_the_yaml_absent(tmp_path: Path) -> None:
    repo = _repo_with_surviving_mutant(tmp_path)

    assert run_bob(repo, "mutate", "--base", "main").returncode == 3
    survivor = str(_survivors(repo)[0]["id"])
    bare = run_bob(repo, "waive", "classify", "--reason", "x")
    tool_id = run_bob(repo, "waive", survivor, "--reason", "x")

    assert bare.returncode == 4
    assert bare.stdout == ""
    assert bare.stderr == (
        "no survivor matches classify:"
        " copy file::function or a Target from the last mutation report\n"
    )
    assert tool_id.returncode == 4
    assert not (repo / ".bob" / "waivers.yaml").exists()


def test_waive_before_any_mutation_run_exits_4(tmp_path: Path) -> None:
    repo = _repo_with_surviving_mutant(tmp_path)

    result = run_bob(repo, "waive", "src/app/weak.py::classify", "--reason", "x")

    assert result.returncode == 4
    assert result.stderr.startswith("no survivor matches src/app/weak.py::classify:")
    assert not (repo / ".bob" / "waivers.yaml").exists()


def test_exact_waivers_survive_an_edit_above_the_waived_site(tmp_path: Path) -> None:
    repo = _repo_with_surviving_mutant(tmp_path)

    assert run_bob(repo, "mutate", "--base", "main").returncode == 3
    before = _survivors(repo)
    for item in before:
        assert run_bob(repo, "waive", str(item["target"]), "--reason", "equivalente").returncode == 0
    shifted = CLASSIFY.replace("str:\n", "str:\n    n = int(n)\n", 1)
    commit_on_branch(repo, "weak", "src/app/weak.py", shifted, "coerce before classifying")
    result = run_bob(repo, "mutate", "--base", "main")
    after = {item["target"]: item for item in _survivors(repo)}

    assert result.returncode == 0, result.stderr
    for item in before:
        moved = after[item["target"]]
        assert moved["id"] != item["id"]
        assert moved["line"] == item["line"] + 1
        assert moved["waiver"] == "equivalente"


def test_a_killed_mutation_run_leaves_setup_cfg_and_mutants_untouched(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "setup.cfg", "[metadata]\nname = app\n", "add setup.cfg")
    commit_on_branch(repo, "weak", "src/app/weak.py", CLASSIFY, "add classify")
    commit_on_branch(repo, "weak", "tests/test_classify.py", WEAK_TEST, "weak classify test")
    before = (repo / "setup.cfg").read_bytes()
    script = (
        "import os, runpy, signal, sys\n"
        "from pathlib import Path\n"
        "import bob_quality.mutate as mutate\n"
        "def die(cwd, patterns, max_workers):\n"
        "    assert '[mutmut]' in (Path(cwd) / 'setup.cfg').read_text()\n"
        "    os.kill(os.getpid(), signal.SIGKILL)\n"
        "mutate.run_mutmut = die\n"
        "sys.argv = ['bob', 'mutate', '--base', 'main']\n"
        "runpy.run_module('bob_quality', run_name='__main__')\n"
    )

    killed = subprocess.run(
        [sys.executable, "-c", script], cwd=repo, capture_output=True, text=True
    )

    assert killed.returncode == -signal.SIGKILL, killed.stderr
    assert (repo / "setup.cfg").read_bytes() == before
    assert not (repo / "mutants").exists()

    rerun = run_bob(repo, "mutate", "--base", "main")

    assert rerun.returncode == 3, rerun.stderr
    assert (repo / "setup.cfg").read_bytes() == before
    assert not (repo / "mutants").exists()
    assert (repo / ".bob" / "mutmut" / "mutants").is_dir()


def _repo_with_tally(tmp_path: Path, touched: str) -> Path:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/tally.py", TALLY, "add tally")
    commit_on_main(repo, "tests/test_tally.py", TALLY_WEAK_TEST, "weak tally test")
    commit_on_branch(repo, "touch", "src/app/tally.py", touched, "touch one line")
    return repo


def _mutate_gate(payload: dict) -> dict:
    return next(gate for gate in payload["gates"] if gate["name"] == "mutate")


def test_survivors_on_unchanged_lines_of_a_changed_function_do_not_block(
    tmp_path: Path,
) -> None:
    repo = _repo_with_tally(tmp_path, TALLY_LINE_5)

    result = run_bob(repo, "mutate", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    cache = json.loads((repo / ".bob" / "mutation-cache.json").read_text())
    cached = cache["functions"][TALLY_KEY]["mutants"]

    assert result.returncode == 0
    assert _mutate_gate(payload) == {"name": "mutate", "status": "passed", "reason": None}
    assert payload["exit_code"] == 0
    assert payload["mutation"]["remutated"] == [TALLY_KEY]
    assert sorted({row["line"] for row in payload["survivors"]}) == [2, 3]
    assert {row["blocking"] for row in payload["survivors"]} == {False}
    assert LINE_2_OUTSIDE in markdown
    assert payload["focus"] == []
    assert [row["status"] for row in cached].count("survived") == len(payload["survivors"])
    assert "killed" in [row["status"] for row in cached]
    assert all("blocking" not in row for row in cached)
    Draft202012Validator(SCHEMA).validate(payload)

    forced = run_bob(repo, "check", "--base", "main", "--gates", "mutate")

    assert forced.returncode == 0


def test_a_survivor_on_a_changed_line_exits_3(tmp_path: Path) -> None:
    repo = _repo_with_tally(tmp_path, TALLY_LINE_3)

    result = run_bob(repo, "mutate", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    blocking = {row["line"] for row in payload["survivors"] if row["blocking"]}
    outside = {row["line"] for row in payload["survivors"] if not row["blocking"]}

    assert result.returncode == 3
    assert _mutate_gate(payload) == {
        "name": "mutate",
        "status": "failed",
        "reason": (
            "survivor without waiver: "
            "tally@src/app/tally.py:3, tally@src/app/tally.py:3, tally@src/app/tally.py:3"
        ),
    }
    assert blocking == {3}
    assert outside == {2}
    assert LINE_2_OUTSIDE in markdown
    assert "src/app/tally.py:3 (outside" not in markdown
    assert payload["focus"] == [{"file": "src/app/tally.py", "risk": 300.0}]

    forced = run_bob(repo, "check", "--base", "main", "--gates", "mutate")

    assert forced.returncode == 3


def test_a_waiver_clears_a_survivor_on_a_changed_line(tmp_path: Path) -> None:
    repo = _repo_with_tally(tmp_path, TALLY_LINE_3)
    reason = "o incremento só muda o total quando n é positivo"

    blocked = run_bob(repo, "mutate", "--base", "main")
    saved = run_bob(repo, "waive", "src/app/tally.py::tally", "--reason", reason)
    result = run_bob(repo, "mutate", "--base", "main")
    markdown = (repo / ".bob" / "report.md").read_text()
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    head = markdown.split("## Verdict")[0]

    assert blocked.returncode == 3
    assert saved.returncode == 0
    assert result.returncode == 0
    assert markdown.startswith("# bob report\n\n## Waivers\n")
    assert reason in head
    assert payload["waivers"][0]["reason"] == reason
    assert payload["waivers"][0]["author"] == "bob-test"
    assert payload["exit_code"] == 0
    assert _mutate_gate(payload) == {"name": "mutate", "status": "passed", "reason": None}
    assert {row["waiver"] for row in payload["survivors"]} == {reason}
    assert {row["blocking"] for row in payload["survivors"]} == {False}
    assert "(outside the diff; does not block)" not in markdown


def test_a_cached_survivor_in_a_function_the_diff_never_touched_does_not_block(
    tmp_path: Path,
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/safe.py", ADD_AND_SCALE, "add and scale")
    commit_on_main(repo, "tests/test_safe.py", ADD_AND_SCALE_TEST, "test add and scale")
    commit_on_main(repo, "src/app/tally.py", TALLY, "add tally")
    commit_on_main(repo, "tests/test_tally.py", TALLY_WEAK_TEST, "weak tally test")
    commit_on_branch(repo, "touch-add", "src/app/safe.py", ADD_TOUCHED, "comment inside add")
    cache_path = repo / ".bob" / "mutation-cache.json"

    first = run_bob(repo, "mutate", "--base", "main")
    cache = json.loads(cache_path.read_text())
    first_functions = sorted(cache["functions"])
    cache["functions"][TALLY_KEY] = {
        "file": "src/app/tally.py",
        "name": "tally",
        "mutants": [
            {
                "id": "tally-planted",
                "function": "tally",
                "file": "src/app/tally.py",
                "line": 2,
                "operator": "SENTINEL",
                "status": "survived",
            }
        ],
    }
    cache_path.write_text(json.dumps(cache, indent=2) + "\n")

    second = run_bob(repo, "mutate", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    stored = json.loads(cache_path.read_text())["functions"][TALLY_KEY]["mutants"]

    assert first.returncode == 0
    assert TALLY_KEY not in first_functions
    assert second.returncode == 0
    assert _mutate_gate(payload) == {"name": "mutate", "status": "passed", "reason": None}
    assert TALLY_KEY in payload["mutation"]["remutated"]
    assert {row["file"] for row in payload["survivors"]} == {"src/app/tally.py"}
    assert {row["blocking"] for row in payload["survivors"]} == {False}
    assert "SENTINEL" not in [row["operator"] for row in stored]
    assert [row["status"] for row in stored].count("survived") == len(payload["survivors"])


def test_harden_skill_kills_mutants_without_weakening_production_code() -> None:
    text = (Path(__file__).resolve().parents[1] / "skills/harden/SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "name: harden" in text
    assert "dentro do razoável" in text
    assert "nunca enfraquecer o código de produção" in text
    assert "bob waive" in text
