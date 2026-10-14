"""Seam da CLI: `bob dry` / `bob check` sobre repos-fixture.

Pega clones novos no diff (par, linhas, tamanho), esconde clones fora do diff,
avisa por padrão e falha no modo fail. Não inspeciona o parser do jscpd. A
similaridade fracionária tem um teste direto, porque o jscpd não gera 0.29.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from helpers import (
    RISKY_SOURCE,
    SAFE_CHANGE,
    TS_SAFE_CHANGE,
    commit_on_branch,
    commit_on_main,
    init_python_repo,
    init_ts_repo,
    run_bob,
)

from bob_quality.config import Config
from bob_quality.dry_gate import _budget, _run_jscpd, _verdict
from bob_quality.models import Clone
from bob_quality.tools import ToolError

CLONE_PY = """\
def format_receipt(name, street, city, amount, tax, note):
    line_name = "name=" + name
    line_street = "street=" + street
    line_city = "city=" + city
    line_amount = "amount=" + str(amount)
    line_tax = "tax=" + str(tax)
    line_note = "note=" + note
    line_total = "total=" + str(amount + tax)
    line_paid = "paid=" + "yes"
    line_footer = "thanks"
    return line_name + line_street + line_city + line_amount + line_tax + line_note + line_total + line_paid + line_footer
"""


def test_jscpd_spawns_inside_a_bob_temp_dir(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    prefix = tmp_path / "tools"
    seen: dict[str, object] = {}

    def fake_spawn(cwd: Path, args: list[str], prefix: Path | None = None) -> subprocess.CompletedProcess[str]:
        out = Path(args[args.index("--output") + 1])
        assert len(out.name) == len("bob-jscpd-") + 8
        assert out.name.startswith("bob-jscpd-")
        (out / "jscpd-report.json").write_text('{"duplicates":[]}')
        seen["cwd"] = cwd
        seen["args"] = args
        seen["prefix"] = prefix
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr("bob_quality.dry_gate.spawn_clean", fake_spawn)
    found = _run_jscpd(repo, Config(), prefix)

    assert found == '{"duplicates":[]}'
    assert seen["cwd"] == repo
    assert seen["prefix"] == prefix
    args = seen["args"]
    assert isinstance(args, list)
    assert args[:8] == [
        "npx",
        "--no-install",
        "--prefix",
        str(prefix),
        "jscpd",
        "--min-tokens",
        "50",
        "--reporters",
    ]

    def fake_spawn_without_report(
        cwd: Path, args: list[str], prefix: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, "from-stdout", "from-stderr")

    monkeypatch.setattr("bob_quality.dry_gate.spawn_clean", fake_spawn_without_report)
    with pytest.raises(ToolError, match="^from-stderr$"):
        _run_jscpd(repo, Config(), prefix)


def test_new_python_clones_in_the_diff_warn_without_failing(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "clones", "src/app/receipt_a.py", CLONE_PY, "add receipt copy")
    commit_on_branch(repo, "clones", "src/app/receipt_b.py", CLONE_PY, "add receipt twin")

    result = run_bob(repo, "dry", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    section = markdown.split("## New clones", 1)[1]
    dry = next(gate for gate in payload["gates"] if gate["name"] == "dry")
    pair = {payload["clones"][0]["first_file"], payload["clones"][0]["second_file"]}

    assert result.returncode == 0, result.stderr
    assert dry["status"] == "warn"
    assert "⚠️" in markdown
    assert pair == {"src/app/receipt_a.py", "src/app/receipt_b.py"}
    assert payload["clones"][0]["lines"] == 11
    assert payload["clones"][0]["tokens"] == 88
    assert "src/app/receipt_a.py:1-11" in section
    assert "src/app/receipt_b.py:1-11" in section
    assert "11" in section
    assert "88" in section
    assert "similarity exact" in section
    assert any(
        item["file"] == "src/app/receipt_a.py" and item.get("clone") is True
        for item in payload["focus"]
    )


def test_old_python_clones_outside_the_diff_are_not_new(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/receipt_a.py", CLONE_PY, "old receipt copy")
    commit_on_main(repo, "src/app/receipt_b.py", CLONE_PY, "old receipt twin")
    commit_on_branch(repo, "touch", "src/app/safe.py", SAFE_CHANGE, "touch tested add")

    result = run_bob(repo, "dry", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    dry = next(gate for gate in payload["gates"] if gate["name"] == "dry")

    assert result.returncode == 0, result.stderr
    assert dry["status"] == "passed"
    assert payload["clones"] == []
    assert "receipt_a.py" not in markdown
    assert "No new clones in the diff." in markdown


def test_python_clone_kept_when_only_the_new_copy_is_in_the_diff(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/receipt_a.py", CLONE_PY, "existing receipt")
    commit_on_branch(repo, "copy", "src/app/receipt_b.py", CLONE_PY, "duplicate receipt")

    result = run_bob(repo, "check", "--base", "main", "--gates", "crap,dry")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    dry = next(gate for gate in payload["gates"] if gate["name"] == "dry")
    pair = {payload["clones"][0]["first_file"], payload["clones"][0]["second_file"]}

    assert result.returncode == 0, result.stderr
    assert dry["status"] == "warn"
    assert pair == {"src/app/receipt_a.py", "src/app/receipt_b.py"}


def test_python_clone_outside_the_hunk_is_not_new(tmp_path: Path) -> None:
    original = CLONE_PY + "\n# note\n"
    edited = CLONE_PY + "\n# edited\n"
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/receipt_a.py", original, "receipt with note")
    commit_on_main(repo, "src/app/receipt_b.py", original, "receipt twin with note")
    commit_on_branch(repo, "note", "src/app/receipt_a.py", edited, "edit only the note")

    result = run_bob(repo, "dry", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 0, result.stderr
    assert payload["clones"] == []
    assert "receipt_b.py" not in markdown


def test_clone_warning_does_not_change_exit_when_crap_fails(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "both", "src/app/risky.py", RISKY_SOURCE, "add untested messy")
    commit_on_branch(repo, "both", "src/app/receipt_a.py", CLONE_PY, "add receipt copy")
    commit_on_branch(repo, "both", "src/app/receipt_b.py", CLONE_PY, "add receipt twin")

    result = run_bob(repo, "check", "--base", "main", "--gates", "crap,dry")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    crap = next(gate for gate in payload["gates"] if gate["name"] == "crap")
    dry = next(gate for gate in payload["gates"] if gate["name"] == "dry")

    assert result.returncode == 1, result.stderr
    assert crap["status"] == "failed"
    assert dry["status"] == "warn"
    assert payload["exit_code"] == 1


def _clone_repo(tmp_path: Path, extra_yaml: str = "", copies: int = 2) -> Path:
    repo = init_python_repo(tmp_path / "repo")
    config = repo / "bob.yaml"
    config.write_text(config.read_text() + extra_yaml)
    for name in "abc"[:copies]:
        commit_on_branch(
            repo, "clones", f"src/app/receipt_{name}.py", CLONE_PY, f"add receipt {name}"
        )
    return repo


def _dry_report(repo: Path) -> tuple[dict, dict, str]:
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    dry = next(gate for gate in payload["gates"] if gate["name"] == "dry")
    return payload, dry, (repo / ".bob" / "report.md").read_text()


def test_fail_mode_fails_on_one_new_clone_and_still_lists_it(tmp_path: Path) -> None:
    repo = _clone_repo(tmp_path, "duplication:\n  new_clones: fail\n")

    result = run_bob(repo, "dry", "--base", "main")
    payload, dry, markdown = _dry_report(repo)
    section = markdown.split("## New clones", 1)[1]

    assert result.returncode == 1, result.stderr
    assert dry == {
        "name": "dry",
        "status": "failed",
        "reason": "1 new clone exceeds duplication.max_new_clones 0",
    }
    assert payload["exit_code"] == 1
    assert "❌ `dry`: failed (1 new clone exceeds duplication.max_new_clones 0)" in markdown
    assert "src/app/receipt_a.py:1-11" in section
    assert "src/app/receipt_b.py:1-11" in section
    assert "Not run" not in section


def test_fail_reason_follows_the_language_only_in_markdown(tmp_path: Path) -> None:
    repo = _clone_repo(tmp_path, "language: pt-BR\nduplication:\n  new_clones: fail\n")

    result = run_bob(repo, "dry", "--base", "main")
    _payload, dry, markdown = _dry_report(repo)

    assert result.returncode == 1, result.stderr
    assert dry["reason"] == "1 new clone exceeds duplication.max_new_clones 0"
    assert "❌ `dry`: falhou (1 clone novo excede duplication.max_new_clones 0)" in markdown


def test_dry_fail_flag_fails_bob_dry_without_config(tmp_path: Path) -> None:
    repo = _clone_repo(tmp_path)

    result = run_bob(repo, "dry", "--base", "main", "--dry-fail")
    payload, dry, _markdown = _dry_report(repo)

    assert result.returncode == 1, result.stderr
    assert dry["status"] == "failed"
    assert dry["reason"] == "1 new clone exceeds duplication.max_new_clones 0"
    assert payload["reproduce"] == "bob dry --base main --dry-fail"


def test_dry_fail_flag_fails_bob_check_with_the_dry_gate(tmp_path: Path) -> None:
    repo = _clone_repo(tmp_path)

    result = run_bob(
        repo,
        "check",
        "--base",
        "main",
        "--gates",
        "crap,dry",
        "--dry-fail",
        "--max-new-clones",
        "0",
    )
    payload, dry, _markdown = _dry_report(repo)
    crap = next(gate for gate in payload["gates"] if gate["name"] == "crap")

    assert result.returncode == 1, result.stderr
    assert crap["status"] == "passed"
    assert dry["status"] == "failed"
    assert payload["reproduce"] == (
        "bob check --base main --gates crap,dry --dry-fail --max-new-clones 0"
    )


def test_max_new_clones_flag_zero_overrides_the_file_ceiling(tmp_path: Path) -> None:
    repo = _clone_repo(tmp_path, "duplication:\n  new_clones: fail\n  max_new_clones: 3\n")

    result = run_bob(repo, "dry", "--base", "main", "--max-new-clones", "0")
    payload, dry, _markdown = _dry_report(repo)

    assert result.returncode == 1, result.stderr
    assert dry["reason"] == "1 new clone exceeds duplication.max_new_clones 0"
    assert payload["reproduce"] == "bob dry --base main --max-new-clones 0"


@pytest.mark.parametrize(
    "extra_yaml",
    [
        "duplication:\n  new_clones: fail\n  max_new_clones: 1\n",
        "duplication:\n  new_clones: warn\n  max_new_clones: 0\n",
    ],
)
def test_clone_within_the_ceiling_or_in_warn_mode_warns(tmp_path: Path, extra_yaml: str) -> None:
    repo = _clone_repo(tmp_path, extra_yaml)

    result = run_bob(repo, "dry", "--base", "main")
    payload, dry, _markdown = _dry_report(repo)

    assert result.returncode == 0, result.stderr
    assert dry == {"name": "dry", "status": "warn", "reason": "1 new clone in the diff"}
    assert len(payload["clones"]) == 1


def test_fail_mode_counts_every_clone_over_the_ceiling(tmp_path: Path) -> None:
    repo = _clone_repo(
        tmp_path, "duplication:\n  new_clones: fail\n  max_new_clones: 1\n", copies=3
    )

    result = run_bob(repo, "dry", "--base", "main")
    payload, dry, _markdown = _dry_report(repo)

    assert result.returncode == 1, result.stderr
    assert dry["reason"] == "2 new clones exceed duplication.max_new_clones 1"
    assert len(payload["clones"]) == 2


@pytest.mark.parametrize("mode", ["warn", "fail"])
def test_clone_shorter_than_min_lines_is_dropped(tmp_path: Path, mode: str) -> None:
    repo = _clone_repo(tmp_path, f"duplication:\n  new_clones: {mode}\n  min_lines: 12\n")

    result = run_bob(repo, "dry", "--base", "main")
    payload, dry, markdown = _dry_report(repo)

    assert result.returncode == 0, result.stderr
    assert dry["status"] == "passed"
    assert payload["clones"] == []
    clones = markdown.split("## New clones\n", 1)[1].split("\n## ", 1)[0]
    assert "receipt_a.py" not in clones
    assert "No new clones in the diff." in clones


def test_exact_clone_at_both_floors_still_fails(tmp_path: Path) -> None:
    repo = _clone_repo(
        tmp_path,
        "duplication:\n  new_clones: fail\n  min_similarity: 100\n  min_lines: 11\n",
    )

    result = run_bob(repo, "dry", "--base", "main")
    payload, dry, _markdown = _dry_report(repo)

    assert result.returncode == 1, result.stderr
    assert dry["status"] == "failed"
    assert payload["clones"][0]["similarity"] is None
    assert payload["clones"][0]["lines"] == 11


@pytest.mark.parametrize("command", ["dry", "check"])
def test_negative_max_new_clones_exits_4_before_a_report(tmp_path: Path, command: str) -> None:
    repo = _clone_repo(tmp_path)

    result = run_bob(repo, command, "--base", "main", "--max-new-clones", "-1")

    assert result.returncode == 4
    assert result.stderr == "--max-new-clones must be at least 0\n"
    assert result.stdout == ""
    assert not (repo / ".bob").exists()


def _counted(min_similarity: float, similarity: float | None) -> tuple[str, list[Clone], Clone]:
    clone = Clone("a.py", 1, 11, "b.py", 1, 11, lines=11, tokens=88, similarity=similarity)
    budget = _budget(Config(min_similarity=min_similarity), dry_fail=False, max_new_clones=None)
    gate, clones, _code, _versions = _verdict(budget, [clone], {})
    return gate.status, clones, clone


@pytest.mark.parametrize(
    ("min_similarity", "similarity"),
    [(29, 0.29), (57, 0.57), (58, 0.58), (100, None)],
)
def test_similarity_at_the_floor_counts(min_similarity: float, similarity: float | None) -> None:
    status, clones, clone = _counted(min_similarity, similarity)

    assert (status, clones) == ("warn", [clone])


@pytest.mark.parametrize(("min_similarity", "similarity"), [(30, 0.29), (100, 0.99)])
def test_similarity_below_the_floor_is_dropped(
    min_similarity: float, similarity: float | None
) -> None:
    assert _counted(min_similarity, similarity)[:2] == ("passed", [])


CLONE_TS = """\
export function formatReceipt(name: string, street: string, city: string, amount: number, tax: number, note: string): string {
  const lineName = "name=" + name;
  const lineStreet = "street=" + street;
  const lineCity = "city=" + city;
  const lineAmount = "amount=" + String(amount);
  const lineTax = "tax=" + String(tax);
  const lineNote = "note=" + note;
  const lineTotal = "total=" + String(amount + tax);
  const linePaid = "paid=" + "yes";
  const lineFooter = "thanks";
  return lineName + lineStreet + lineCity + lineAmount + lineTax + lineNote + lineTotal + linePaid + lineFooter;
}
"""


def test_new_typescript_clones_in_the_diff_warn_without_failing(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(repo, "clones", "src/receipt_a.ts", CLONE_TS, "add receipt copy")
    commit_on_branch(repo, "clones", "src/receipt_b.ts", CLONE_TS, "add receipt twin")

    result = run_bob(repo, "dry", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    section = markdown.split("## New clones", 1)[1]
    dry = next(gate for gate in payload["gates"] if gate["name"] == "dry")
    pair = {payload["clones"][0]["first_file"], payload["clones"][0]["second_file"]}

    assert result.returncode == 0, result.stderr
    assert dry["status"] == "warn"
    assert pair == {"src/receipt_a.ts", "src/receipt_b.ts"}
    assert payload["clones"][0]["lines"] == 12
    assert payload["clones"][0]["tokens"] == 123
    assert "src/receipt_a.ts:1-12" in section
    assert "src/receipt_b.ts:1-12" in section
    assert "123" in section


def test_old_typescript_clones_outside_the_diff_are_not_new(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_main(repo, "src/receipt_a.ts", CLONE_TS, "old receipt copy")
    commit_on_main(repo, "src/receipt_b.ts", CLONE_TS, "old receipt twin")
    commit_on_branch(repo, "touch", "src/safe.ts", TS_SAFE_CHANGE, "touch tested add")

    result = run_bob(repo, "dry", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    dry = next(gate for gate in payload["gates"] if gate["name"] == "dry")

    assert result.returncode == 0, result.stderr
    assert dry["status"] == "passed"
    assert payload["clones"] == []
    assert "receipt_a.ts" not in markdown


def test_dry_is_not_run_when_node_is_missing(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "clones", "src/app/receipt_a.py", CLONE_PY, "add receipt copy")
    commit_on_branch(repo, "clones", "src/app/receipt_b.py", CLONE_PY, "add receipt twin")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    os.symlink(shutil.which("git"), bindir / "git")
    env = {**os.environ, "PATH": str(bindir)}

    result = run_bob(repo, "dry", "--base", "main", env=env)
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    dry = next(gate for gate in payload["gates"] if gate["name"] == "dry")

    assert result.returncode == 0, result.stderr
    assert dry["status"] == "not_run"
    assert "Node missing" in dry["reason"]
    assert "⏭️" in markdown
    assert "⚠️" not in markdown
    assert "✅ `dry`" not in markdown
