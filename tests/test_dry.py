"""Seam da CLI: `bob dry` / `bob check` sobre repos-fixture.

Pega clones novos no diff (par, linhas, tamanho) como aviso, esconde clones
fora do diff e mantém o exit code. Não inspeciona o parser do jscpd.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from bob_quality.config import Config
from bob_quality.dry_gate import _run_jscpd

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

    result = subprocess.run(
        [sys.executable, "-m", "bob_quality", "dry", "--base", "main"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    dry = next(gate for gate in payload["gates"] if gate["name"] == "dry")

    assert result.returncode == 0, result.stderr
    assert dry["status"] == "not_run"
    assert "Node missing" in dry["reason"]
    assert "⏭️" in markdown
    assert "⚠️" not in markdown
    assert "✅ `dry`" not in markdown
