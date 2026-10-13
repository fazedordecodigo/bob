from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from bob_quality.config import Config, ConfigError, load_config
from bob_quality.messages import msg, reason, render
from bob_quality.models import GateResult, Report, SecretLedger, SecretRow
from bob_quality.report import to_json, to_markdown
from bob_quality.secrets_gate import judge_secrets
from helpers import commit_on_branch, in_both, init_python_repo, run_bob

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "src/bob_quality/schemas/report_v1.json").read_text()
)
_SENTINEL = "super-secret-value"
_PATH_SENTINEL = "path-only-sentinel"
_FAKE_KEY = "AKIABOBFAKEKEY2W3X4Y"


def test_judge_secrets_blocks_only_the_changed_unwaived_line() -> None:
    judgment = judge_secrets(
        (
            SecretRow("src/old.py", 2, "generic-api-key"),
            SecretRow("src/app.py", 12, "aws-access-token"),
        ),
        {"src/app.py": {12}},
        frozenset(),
    )

    assert judgment.exit_code == 1
    assert judgment.result.name == "secrets"
    assert judgment.result.status == "failed"
    assert in_both(judgment.result.reason) == (
        "1 new secret in the diff; 1 secret outside the diff",
        "1 segredo novo no diff; 1 segredo fora do diff",
    )
    assert judgment.ledger.blocking == (SecretRow("src/app.py", 12, "aws-access-token"),)
    assert judgment.ledger.outside_diff == (SecretRow("src/old.py", 2, "generic-api-key"),)


def test_judge_secrets_keeps_an_outside_row_without_failing() -> None:
    judgment = judge_secrets(
        (SecretRow("src/old.py", 2, "generic-api-key"),),
        {"src/app.py": {12}},
        frozenset(),
    )

    assert judgment.exit_code == 0
    assert judgment.result.name == "secrets"
    assert judgment.result.status == "passed"
    assert in_both(judgment.result.reason) == (
        "1 secret outside the diff",
        "1 segredo fora do diff",
    )
    assert judgment.ledger.blocking == ()
    assert judgment.ledger.outside_diff == (SecretRow("src/old.py", 2, "generic-api-key"),)


def test_judge_secrets_drops_only_a_whole_secret_waiver_id() -> None:
    row = SecretRow("src/app.py", 12, "aws-access-token")
    diff = {"src/app.py": {12}}

    waived = judge_secrets(
        (row,),
        diff,
        frozenset({"secret:aws-access-token:src/app.py:12"}),
    )
    mutant = judge_secrets((row,), diff, frozenset({"app.billing.x_charge__mutmut_2"}))
    sast = judge_secrets(
        (row,),
        diff,
        frozenset({"sast:bandit:hardcoded-password:src/app.py:12"}),
    )

    assert waived.exit_code == 0
    assert waived.result.status == "passed"
    assert waived.result.reason is None
    assert waived.ledger.blocking == ()
    assert waived.ledger.outside_diff == ()
    assert mutant.exit_code == 1
    assert mutant.result.status == "failed"
    assert mutant.ledger.blocking == (row,)
    assert sast.exit_code == 1
    assert sast.result.status == "failed"
    assert sast.ledger.blocking == (row,)


def test_judge_secrets_keeps_a_later_row_when_the_first_is_waived() -> None:
    waived = SecretRow("src/app.py", 1, "aws-access-token")
    later = SecretRow("src/app.py", 2, "aws-access-token")

    judgment = judge_secrets(
        (waived, later),
        {"src/app.py": {1, 2}},
        frozenset({waived.waiver_id()}),
    )

    assert judgment.exit_code == 1
    assert judgment.ledger.blocking == (later,)
    assert judgment.ledger.outside_diff == ()


def test_judge_secrets_counts_every_new_and_outside_row() -> None:
    blocking = (
        SecretRow("src/a.py", 1, "aws-access-token"),
        SecretRow("src/a.py", 2, "aws-access-token"),
    )
    outside = (
        SecretRow("src/b.py", 1, "generic-api-key"),
        SecretRow("src/b.py", 2, "generic-api-key"),
    )

    judgment = judge_secrets((*blocking, *outside), {"src/a.py": {1, 2}}, frozenset())

    assert judgment.exit_code == 1
    assert judgment.ledger.blocking == blocking
    assert judgment.ledger.outside_diff == outside
    assert in_both(judgment.result.reason) == (
        "2 new secrets in the diff; 2 secrets outside the diff",
        "2 segredos novos no diff; 2 segredos fora do diff",
    )


def test_secret_ledger_rejects_unsorted_rows() -> None:
    with pytest.raises(ValueError, match="^secret rows are unsorted$"):
        SecretLedger(
            blocking=(
                SecretRow("src/b.py", 1, "aws-access-token"),
                SecretRow("src/a.py", 1, "aws-access-token"),
            )
        )


def test_load_config_accepts_an_empty_secrets_mapping(tmp_path: Path) -> None:
    assert load_config(None, tmp_path) == Config()
    for text in ("secrets: {}\n", "secrets:\n", "secrets: null\n"):
        (tmp_path / "bob.yaml").write_text(text)
        assert load_config(None, tmp_path) == Config()


@pytest.mark.parametrize(
    ("text", "stderr"),
    [
        ("secrets: true\n", "bob.yaml: secrets must be a mapping\n"),
        ("secrets:\n  threshold: 1\n", "bob.yaml: unknown key secrets.threshold\n"),
    ],
)
def test_load_config_rejects_a_secrets_scalar_or_child(
    tmp_path: Path, text: str, stderr: str
) -> None:
    (tmp_path / "bob.yaml").write_text(text)

    with pytest.raises(ConfigError) as caught:
        load_config(None, tmp_path)

    assert render(reason(caught.value), "en") == stderr.rstrip("\n")
    result = run_bob(tmp_path, "check", "--gates", "secrets")
    assert result.returncode == 4
    assert result.stderr == stderr
    assert result.stdout == ""
    assert not (tmp_path / ".bob").exists()


def test_report_omits_the_secret_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "leak", "src/app/added.py", "print('ok')\n", "add file")
    added = repo / "src/app/added.py"
    body = json.dumps(
        [
            {
                "File": str(added.resolve()),
                "StartLine": 1,
                "RuleID": "aws-access-token",
                "Secret": _SENTINEL,
            },
            {
                "File": str(added.resolve()),
                "StartLine": 0,
                "RuleID": "path-only",
                "Secret": _PATH_SENTINEL,
            },
        ]
    )
    _use_stub(tmp_path, monkeypatch, [(body, 1)])

    result = run_bob(repo, "check", "--gates", "secrets", "--base", "main")
    report_json = (repo / ".bob" / "report.json").read_text()
    report_md = (repo / ".bob" / "report.md").read_text()
    payload = json.loads(report_json)

    assert result.returncode == 1
    assert _SENTINEL not in report_json
    assert _SENTINEL not in report_md
    assert _PATH_SENTINEL not in report_json
    assert _PATH_SENTINEL not in report_md
    assert sorted(path.name for path in (repo / ".bob").iterdir()) == ["report.json", "report.md"]
    assert payload["secrets"] == [
        {"file": "src/app/added.py", "line": 1, "rule_id": "aws-access-token"}
    ]
    assert payload["gates"] == [
        {"name": "secrets", "status": "failed", "reason": "1 new secret in the diff"}
    ]


def test_json_secrets_array_is_the_blocking_rows_only() -> None:
    payload = to_json(_secrets_report())

    assert payload["secrets"] == [
        {"file": "src/app.py", "line": 12, "rule_id": "aws-access-token"}
    ]
    keys = list(payload)
    assert keys[keys.index("mutation") + 1] == "churn"
    assert keys[keys.index("churn") + 1] == "secrets"
    assert keys[keys.index("secrets") + 1] == "reproduce"
    Draft202012Validator(SCHEMA).validate(payload)
    leaked = {
        **payload,
        "secrets": [
            {
                "file": "src/app.py",
                "line": 12,
                "rule_id": "aws-access-token",
                "secret": _SENTINEL,
            }
        ],
    }
    zero = {
        **payload,
        "secrets": [{"file": "src/app.py", "line": 0, "rule_id": "aws-access-token"}],
    }
    with pytest.raises(ValidationError):
        Draft202012Validator(SCHEMA).validate(leaked)
    with pytest.raises(ValidationError):
        Draft202012Validator(SCHEMA).validate(zero)


def test_markdown_puts_segredos_between_uncovered_mutants_and_reproduce() -> None:
    markdown = to_markdown(_secrets_report(), "pt-BR")
    uncovered = markdown.index("## Mutantes sem teste")
    secrets = markdown.index("## Segredos")
    outside = markdown.index("Fora do diff; não bloqueia.")
    old = markdown.index("src/old.py")
    reproduce = markdown.index("## Como reproduzir")

    assert uncovered < secrets < outside < old < reproduce
    assert "\n\n## Segredos\n\n| Alvo | Arquivo | Linha | Regra |\n|---|---|---:|---|\n" in markdown
    assert "\n\nFora do diff; não bloqueia.\n\n| Alvo | Arquivo | Linha | Regra |\n|---|---|---:|---|\n" in markdown
    assert "| `secret:aws-access-token:src/app.py:12` | src/app.py | 12 | aws-access-token |" in markdown
    assert "| `secret:generic-api-key:src/old.py:2` | src/old.py | 2 | generic-api-key |" in markdown

    empty = to_markdown(_outside_only_report(), "en")
    assert "\n\n## Secrets\n\nNo new secret in the diff.\n" in empty
    assert "\n\nOutside the diff; does not block.\n\n| Target | File | Line | Rule |\n|---|---|---:|---|\n" in empty


def test_empty_gitleaks_array_is_a_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = init_python_repo(tmp_path / "repo")
    _use_stub(tmp_path, monkeypatch, [("[]", 1)])

    result = run_bob(repo, "check", "--gates", "secrets", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert result.returncode == 0
    assert payload["exit_code"] == 0
    assert payload["secrets"] == []
    assert payload["gates"] == [{"name": "secrets", "status": "passed", "reason": None}]
    assert "No new secret in the diff." in (repo / ".bob" / "report.md").read_text()


def test_gitleaks_null_is_exit_4_and_still_writes_the_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    _use_stub(tmp_path, monkeypatch, [("null", 0)])

    result = run_bob(repo, "check", "--gates", "secrets", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert result.returncode == 4
    assert payload["exit_code"] == 4
    assert "secrets" not in payload
    assert payload["gates"] == [
        {
            "name": "secrets",
            "status": "not_run",
            "reason": "gitleaks did not return a usable report",
        }
    ]
    assert (repo / ".bob" / "report.md").is_file()


def test_gitleaksignore_stops_before_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "src" / ".gitleaksignore").write_text("src/app/safe.py\n")
    marker = tmp_path / "spawned"
    _use_stub(tmp_path, monkeypatch, [("[]", 0)], marker)

    result = run_bob(repo, "check", "--gates", "secrets", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert result.returncode == 4
    assert not marker.exists()
    assert "secrets" not in payload
    assert payload["gates"] == [
        {
            "name": "secrets",
            "status": "not_run",
            "reason": "move .gitleaksignore entries to .bob/waivers.yaml",
        }
    ]


def test_a_directory_named_b_stays_in_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "leak", "b/added.py", "print('ok')\n", "add file")
    _use_stub(
        tmp_path,
        monkeypatch,
        [(json.dumps([{"File": "b/added.py", "StartLine": 1, "RuleID": "aws-access-token"}]), 1)],
    )

    result = run_bob(repo, "check", "--gates", "secrets", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert result.returncode == 1
    assert payload["secrets"] == [{"file": "b/added.py", "line": 1, "rule_id": "aws-access-token"}]


def test_one_bad_include_discards_partial_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "extra").mkdir()
    (repo / "bob.yaml").write_text("base: main\npaths:\n  include: [src, extra]\n")
    commit_on_branch(repo, "leak", "src/app/added.py", "print('ok')\n", "add file")
    added = (repo / "src/app/added.py").resolve()
    first = json.dumps(
        [{"File": str(added), "StartLine": 1, "RuleID": "aws-access-token", "Secret": _SENTINEL}]
    )
    _use_stub(tmp_path, monkeypatch, [(first, 1), ("null", 0)])

    result = run_bob(repo, "check", "--gates", "secrets", "--base", "main")
    report_json = (repo / ".bob" / "report.json").read_text()
    payload = json.loads(report_json)

    assert result.returncode == 4
    assert "secrets" not in payload
    assert _SENTINEL not in report_json
    assert _SENTINEL not in (repo / ".bob" / "report.md").read_text()


def test_real_gitleaks_fails_a_new_synthetic_key_and_hides_it(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(
        repo,
        "leak",
        "src/app/leak.py",
        f'token = "{_FAKE_KEY}"\n',
        "add synthetic key",
    )

    result = run_bob(repo, "check", "--gates", "secrets", "--base", "main")
    report_json = (repo / ".bob" / "report.json").read_text()
    report_md = (repo / ".bob" / "report.md").read_text()
    payload = json.loads(report_json)

    assert _FAKE_KEY not in report_json
    assert _FAKE_KEY not in report_md
    assert result.returncode == 1
    assert payload["tool_versions"]["gitleaks"] == "8.30.1"
    assert payload["secrets"] == [
        {"file": "src/app/leak.py", "line": 1, "rule_id": "aws-access-token"}
    ]
    assert payload["gates"][0]["name"] == "secrets"
    assert payload["gates"][0]["status"] == "failed"


def _outside_only_report() -> Report:
    report = _secrets_report()
    return Report(
        schema_version=report.schema_version,
        commit=report.commit,
        base=report.base,
        generated_at=report.generated_at,
        tool_versions=report.tool_versions,
        gates=[GateResult("secrets", "passed", msg("secrets.outside_one"))],
        focus=report.focus,
        top_crap=report.top_crap,
        reproduce=report.reproduce,
        exit_code=0,
        mutation=report.mutation,
        secrets=SecretLedger(outside_diff=(SecretRow("src/old.py", 2, "generic-api-key"),)),
    )


def _secrets_report() -> Report:
    return Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-11T00:00:00+00:00",
        tool_versions={"gitleaks": "8.30.1"},
        gates=[GateResult("secrets", "failed", msg("secrets.new_one"))],
        focus=[],
        top_crap=[],
        reproduce="bob check --gates secrets",
        exit_code=1,
        mutation={"no_coverage": {"total": 0, "functions": []}},
        secrets=SecretLedger(
            blocking=(SecretRow("src/app.py", 12, "aws-access-token"),),
            outside_diff=(SecretRow("src/old.py", 2, "generic-api-key"),),
        ),
    )


def _use_stub(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reports: list[tuple[str, int]],
    marker: Path | None = None,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_stub(bin_dir, reports, marker)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])


def _write_stub(bin_dir: Path, reports: list[tuple[str, int]], marker: Path | None) -> None:
    payload = json.dumps([{"body": body, "code": code} for body, code in reports])
    marker_literal = "None" if marker is None else repr(str(marker))
    script = f"""#!{sys.executable}
import json
import sys
from pathlib import Path
marker = {marker_literal}
if marker is not None:
    Path(marker).write_text("ran")
if sys.argv[1:2] == ["--version"]:
    print("8.30.1")
    raise SystemExit(0)
state = Path({str(bin_dir / "state")!r})
index = int(state.read_text()) if state.is_file() else 0
state.write_text(str(index + 1))
chosen = json.loads({payload!r})[min(index, {len(reports) - 1})]
report = ""
args = sys.argv[1:]
for offset, arg in enumerate(args):
    if arg == "--report-path" and offset + 1 < len(args):
        report = args[offset + 1]
Path(report).write_text(chosen["body"])
raise SystemExit(chosen["code"])
"""
    path = bin_dir / "gitleaks"
    path.write_text(script)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
