"""Call run_secrets_gate in this process so mutmut associates the scan."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from bob_quality.config import Config
from bob_quality.models import SecretLedger, SecretRow
from bob_quality.secrets_gate import SecretsRun, run_secrets_gate
from helpers import in_both

_UNREADABLE = (
    "gitleaks did not return a usable report",
    "o gitleaks não devolveu um relatório utilizável",
)
_AWS = "aws-access-token"
_PASSED = {
    "exit_code": 0,
    "name": "secrets",
    "status": "passed",
    "reason": None,
    "ledger": SecretLedger(),
    "versions": {"gitleaks": "8.30.1"},
}

_FAKE = '''
import json
import os
import sys
from pathlib import Path

UNPLANNED = 97
STALE_REPORT = 98
KEYS = ("GITLEAKS_CONFIG", "GITLEAKS_CONFIG_TOML", "PYTEST_ADDOPTS", "BOB_KEEP")
here = Path(__file__).parent
plan = json.loads((here / "plan.json").read_text())
log = here / "calls.jsonl"
earlier = [json.loads(line) for line in log.read_text().splitlines()] if log.is_file() else []
args = sys.argv[1:]


def option(name):
    return args[args.index(name) + 1] if name in args else None


config = option("--config")
report = option("--report-path")
call = {
    "argv": sys.argv,
    "cwd": os.getcwd(),
    "config": None if config is None else Path(config).read_text(),
    "env": {key: key in os.environ for key in KEYS},
    "report_existed": None if report is None else Path(report).exists(),
}
with log.open("a") as handle:
    print(json.dumps(call), file=handle)
if args == ["--version"]:
    sys.stdout.write(plan["stdout"])
    sys.stderr.write(plan["stderr"])
    if plan["vanish"]:
        Path(__file__).unlink()
    raise SystemExit(plan["version_code"])
if call["report_existed"]:
    raise SystemExit(STALE_REPORT)
print("gitleaks detect stdout")
print("gitleaks detect stderr", file=sys.stderr)
done = sum(1 for item in earlier if item["argv"][1:2] == ["detect"])
if done >= len(plan["detects"]):
    raise SystemExit(UNPLANNED)
step = plan["detects"][done]
if step["body"] is not None:
    Path(report).write_bytes(bytes.fromhex(step["body"]))
raise SystemExit(step["code"])
'''


@dataclass(frozen=True)
class Detect:
    body: str | bytes | None
    code: int = 1


@dataclass(frozen=True)
class Gitleaks:
    detects: tuple[Detect, ...] = ()
    stdout: str = "8.30.1\n"
    stderr: str = ""
    version_code: int = 0
    vanish: bool = False

    def encoded(self) -> dict[str, object]:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "version_code": self.version_code,
            "vanish": self.vanish,
            "detects": [{"body": _hex(step.body), "code": step.code} for step in self.detects],
        }


_BOB_HOME_STUB = '''
import json
import sys
from pathlib import Path

log = Path(__file__).with_name("calls.jsonl")
with log.open("a") as handle:
    handle.write(json.dumps({"argv": sys.argv}) + "\\n")
args = sys.argv[1:]
if args in (["version"], ["--version"]):
    sys.stdout.write("8.30.1\\n")
    raise SystemExit(0)
name = "--report-path"
if name in args:
    Path(args[args.index(name) + 1]).write_text("[]")
raise SystemExit(0)
'''


@pytest.fixture(autouse=True)
def _empty_bob_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BOB_HOME", str(tmp_path / "bob-home"))


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    return root


def test_a_missing_include_stops_before_gitleaks(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = _install(tmp_path, monkeypatch, Gitleaks((Detect("[]"),)))

    run = run_secrets_gate(repo, Config(include=("missing",)), {})

    assert _seen(run) == {
        "exit_code": 4,
        "name": "secrets",
        "status": "not_run",
        "reason": (
            "gitleaks: include path missing: missing",
            "gitleaks: caminho include ausente: missing",
        ),
        "ledger": None,
        "versions": {},
    }
    assert _calls(bin_dir) == []


def test_every_missing_include_is_named_once(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install(tmp_path, monkeypatch, Gitleaks((Detect("[]"),)))

    run = run_secrets_gate(repo, Config(include=("a", "src", "b")), {})

    assert _seen(run) == {
        "exit_code": 4,
        "name": "secrets",
        "status": "not_run",
        "reason": (
            "gitleaks: include path missing: a, b",
            "gitleaks: caminho include ausente: a, b",
        ),
        "ledger": None,
        "versions": {},
    }


def test_a_gitleaksignore_under_an_include_root_stops_before_gitleaks(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / "lib").mkdir()
    (repo / "lib" / ".gitleaksignore").write_text("src/a.py\n")
    bin_dir = _install(tmp_path, monkeypatch, Gitleaks((Detect("[]"), Detect("[]"))))

    run = run_secrets_gate(repo, Config(include=("src", "lib")), {})

    assert _seen(run) == {
        "exit_code": 4,
        "name": "secrets",
        "status": "not_run",
        "reason": (
            "move .gitleaksignore entries to .bob/waivers.yaml",
            "mova as entradas de .gitleaksignore para .bob/waivers.yaml",
        ),
        "ledger": None,
        "versions": {},
    }
    assert _calls(bin_dir) == []


def test_gitleaks_absent_from_path_is_a_missing_tool(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))

    run = run_secrets_gate(repo, Config(), {})

    assert _seen(run) == {
        "exit_code": 4,
        "name": "secrets",
        "status": "not_run",
        "reason": ("missing tool: gitleaks", "ferramenta ausente: gitleaks"),
        "ledger": None,
        "versions": {},
    }


def test_gitleaks_in_bob_home_is_used_before_the_path(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home_bin = _install_bob_home(tmp_path, monkeypatch)
    path_dir = tmp_path / "path"
    path_dir.mkdir()
    called = path_dir / "called"
    path_stub = path_dir / "gitleaks"
    path_stub.write_text(f"#!/bin/sh\nprintf used >> {called}\nexit 99\n")
    path_stub.chmod(0o755)
    monkeypatch.setenv("PATH", str(path_dir))

    run = run_secrets_gate(repo, Config(), {})

    binary = str(home_bin / "gitleaks")
    calls = _calls(home_bin)
    assert run.versions == {"gitleaks": "8.30.1"}
    assert calls[0]["argv"] == [binary, "--version"]
    assert {call["argv"][0] for call in calls} == {binary}
    assert not called.is_file()


def test_gitleaks_only_in_bob_home_is_not_a_missing_tool(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    _install_bob_home(tmp_path, monkeypatch)

    run = run_secrets_gate(repo, Config(), {})

    assert _seen(run) != {
        "exit_code": 4,
        "name": "secrets",
        "status": "not_run",
        "reason": ("missing tool: gitleaks", "ferramenta ausente: gitleaks"),
        "ledger": None,
        "versions": {},
    }


def test_a_version_without_a_number_stops_before_detect(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = _install(tmp_path, monkeypatch, Gitleaks((Detect("[]"),), stdout="gitleaks dev\n"))

    run = run_secrets_gate(repo, Config(), {})

    assert _seen(run) == {
        "exit_code": 4,
        "name": "secrets",
        "status": "not_run",
        "reason": ("unreadable gitleaks version", "versão do gitleaks ilegível"),
        "ledger": None,
        "versions": {},
    }
    assert [call["argv"] for call in _calls(bin_dir)] == [[str(bin_dir / "gitleaks"), "--version"]]


def test_a_version_printed_only_on_stderr_is_recorded(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install(
        tmp_path,
        monkeypatch,
        Gitleaks((Detect("[]", 0),), stdout="", stderr="gitleaks 8.30.1\n"),
    )

    run = run_secrets_gate(repo, Config(), {})

    assert _seen(run) == {
        "exit_code": 0,
        "name": "secrets",
        "status": "passed",
        "reason": None,
        "ledger": SecretLedger(),
        "versions": {"gitleaks": "8.30.1"},
    }


@pytest.mark.parametrize(
    ("stdout", "stderr", "code", "version"),
    [
        ("v1.2.3-extra\n", "9.9.9\n", 0, "1.2.3"),
        ("10.20\n", "", 0, "10.20"),
        ("8.30.1\n", "", 1, "8.30.1"),
    ],
    ids=["first match", "two parts", "nonzero exit"],
)
def test_the_first_version_match_wins(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
    stderr: str,
    code: int,
    version: str,
) -> None:
    _install(
        tmp_path,
        monkeypatch,
        Gitleaks((Detect("[]", 0),), stdout=stdout, stderr=stderr, version_code=code),
    )

    run = run_secrets_gate(repo, Config(), {})

    assert run.exit_code == 0
    assert run.versions == {"gitleaks": version}


def test_a_detect_that_cannot_spawn_keeps_the_version(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = _install(tmp_path, monkeypatch, Gitleaks((Detect("[]", 0),), vanish=True))

    run = run_secrets_gate(repo, Config(), {})

    assert _seen(run) == {
        "exit_code": 4,
        "name": "secrets",
        "status": "not_run",
        "reason": _UNREADABLE,
        "ledger": None,
        "versions": {"gitleaks": "8.30.1"},
    }
    assert [call["argv"] for call in _calls(bin_dir)] == [[str(bin_dir / "gitleaks"), "--version"]]


def test_a_waiver_file_that_is_not_a_mapping_keeps_the_version(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / ".bob").mkdir()
    (repo / ".bob" / "waivers.yaml").write_text("- secret:aws-access-token:src/a.py:1\n")
    bin_dir = _install(tmp_path, monkeypatch, Gitleaks((Detect("[]", 0),)))

    run = run_secrets_gate(repo, Config(), {})

    assert _seen(run) == {
        "exit_code": 4,
        "name": "secrets",
        "status": "not_run",
        "reason": (
            ".bob/waivers.yaml must be a mapping",
            ".bob/waivers.yaml deve ser um mapeamento",
        ),
        "ledger": None,
        "versions": {"gitleaks": "8.30.1"},
    }
    assert [call["argv"] for call in _calls(bin_dir)] == [[str(bin_dir / "gitleaks"), "--version"]]


@pytest.mark.parametrize(
    "detect",
    [
        Detect(json.dumps([{"File": "src/a.py", "StartLine": 1, "RuleID": _AWS}]), 2),
        Detect(None, 0),
        Detect(b"\xff\xfe[]", 1),
    ],
    ids=["exit 2 with an array", "exit 0 without a report", "not utf-8"],
)
def test_a_detect_without_a_readable_report_is_exit_4(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, detect: Detect
) -> None:
    _install(tmp_path, monkeypatch, Gitleaks((detect,)))

    run = run_secrets_gate(repo, Config(), {"src/a.py": {1}})

    assert _seen(run) == {
        "exit_code": 4,
        "name": "secrets",
        "status": "not_run",
        "reason": _UNREADABLE,
        "ledger": None,
        "versions": {"gitleaks": "8.30.1"},
    }


@pytest.mark.parametrize(
    "body",
    [
        "{",
        "{}",
        "[1]",
        json.dumps([{"StartLine": 1, "RuleID": _AWS}]),
        json.dumps([{"File": "src/a.py", "StartLine": 1, "RuleID": ""}]),
        json.dumps([{"File": "src/a.py", "RuleID": _AWS}]),
        json.dumps([{"File": "src/a.py", "StartLine": True, "RuleID": _AWS}]),
        json.dumps([{"File": "src/a.py", "StartLine": "1", "RuleID": _AWS}]),
    ],
    ids=[
        "truncated",
        "object",
        "number item",
        "no File",
        "empty RuleID",
        "no StartLine",
        "bool StartLine",
        "text StartLine",
    ],
)
def test_a_malformed_report_is_exit_4(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str
) -> None:
    _install(tmp_path, monkeypatch, Gitleaks((Detect(body),)))

    run = run_secrets_gate(repo, Config(), {"src/a.py": {1}})

    assert _seen(run) == {
        "exit_code": 4,
        "name": "secrets",
        "status": "not_run",
        "reason": _UNREADABLE,
        "ledger": None,
        "versions": {"gitleaks": "8.30.1"},
    }


def test_a_zero_start_line_drops_the_row(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install(tmp_path, monkeypatch, Gitleaks((Detect(_report(("src/a.py", 0, _AWS))),)))

    run = run_secrets_gate(repo, Config(), {"src/a.py": {1}})

    assert _seen(run) == {
        "exit_code": 0,
        "name": "secrets",
        "status": "passed",
        "reason": None,
        "ledger": SecretLedger(blocking=(), outside_diff=()),
        "versions": {"gitleaks": "8.30.1"},
    }


@pytest.mark.parametrize("file_name", ["../outside.py", "src/.."], ids=["outside", "repo root"])
def test_a_file_that_is_not_inside_the_repo_is_exit_4(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file_name: str
) -> None:
    _install(tmp_path, monkeypatch, Gitleaks((Detect(_report((file_name, 1, _AWS))),)))

    run = run_secrets_gate(repo, Config(), {})

    assert _seen(run) == {
        "exit_code": 4,
        "name": "secrets",
        "status": "not_run",
        "reason": _UNREADABLE,
        "ledger": None,
        "versions": {"gitleaks": "8.30.1"},
    }


@pytest.mark.parametrize(
    "file_name",
    ["./src/a.py", "src\\a.py", "{repo}/src/a.py"],
    ids=["dot slash", "backslash", "absolute"],
)
def test_report_paths_become_the_repo_relative_posix_path(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file_name: str
) -> None:
    shown = file_name.format(repo=repo)
    _install(tmp_path, monkeypatch, Gitleaks((Detect(_report((shown, 3, _AWS))),)))

    run = run_secrets_gate(repo, Config(), {"src/a.py": {3}})

    assert run.exit_code == 1
    assert run.ledger == SecretLedger(blocking=(SecretRow("src/a.py", 3, _AWS),))


@pytest.mark.parametrize("code", [0, 1])
def test_an_empty_array_passes(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    _install(tmp_path, monkeypatch, Gitleaks((Detect("[]", code),)))

    run = run_secrets_gate(repo, Config(), {"src/a.py": {1}})

    assert _seen(run) == {
        "exit_code": 0,
        "name": "secrets",
        "status": "passed",
        "reason": None,
        "ledger": SecretLedger(),
        "versions": {"gitleaks": "8.30.1"},
    }


def test_a_finding_on_a_diff_line_blocks(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install(tmp_path, monkeypatch, Gitleaks((Detect(_report(("src/a.py", 3, _AWS))),)))

    run = run_secrets_gate(repo, Config(), {"src/a.py": {3}})

    assert _seen(run) == {
        "exit_code": 1,
        "name": "secrets",
        "status": "failed",
        "reason": ("1 new secret in the diff", "1 segredo novo no diff"),
        "ledger": SecretLedger(blocking=(SecretRow("src/a.py", 3, _AWS),)),
        "versions": {"gitleaks": "8.30.1"},
    }


def test_a_finding_off_the_diff_passes(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install(tmp_path, monkeypatch, Gitleaks((Detect(_report(("src/a.py", 3, _AWS))),)))

    run = run_secrets_gate(repo, Config(), {"src/a.py": {4}})

    assert _seen(run) == {
        "exit_code": 0,
        "name": "secrets",
        "status": "passed",
        "reason": ("1 secret outside the diff", "1 segredo fora do diff"),
        "ledger": SecretLedger(outside_diff=(SecretRow("src/a.py", 3, _AWS),)),
        "versions": {"gitleaks": "8.30.1"},
    }


def test_two_new_secrets_are_counted(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _report(("src/a.py", 3, _AWS), ("src/a.py", 4, _AWS))
    _install(tmp_path, monkeypatch, Gitleaks((Detect(body),)))

    run = run_secrets_gate(repo, Config(), {"src/a.py": {3, 4}})

    assert _seen(run) == {
        "exit_code": 1,
        "name": "secrets",
        "status": "failed",
        "reason": ("2 new secrets in the diff", "2 segredos novos no diff"),
        "ledger": SecretLedger(
            blocking=(SecretRow("src/a.py", 3, _AWS), SecretRow("src/a.py", 4, _AWS)),
        ),
        "versions": {"gitleaks": "8.30.1"},
    }


def test_one_new_and_one_outside_secret_join_both_counts(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _report(("src/a.py", 3, _AWS), ("src/a.py", 4, _AWS))
    _install(tmp_path, monkeypatch, Gitleaks((Detect(body),)))

    run = run_secrets_gate(repo, Config(), {"src/a.py": {3}})

    assert _seen(run) == {
        "exit_code": 1,
        "name": "secrets",
        "status": "failed",
        "reason": (
            "1 new secret in the diff; 1 secret outside the diff",
            "1 segredo novo no diff; 1 segredo fora do diff",
        ),
        "ledger": SecretLedger(
            blocking=(SecretRow("src/a.py", 3, _AWS),),
            outside_diff=(SecretRow("src/a.py", 4, _AWS),),
        ),
        "versions": {"gitleaks": "8.30.1"},
    }


def test_only_a_secret_waiver_id_drops_its_row(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / ".bob").mkdir()
    (repo / ".bob" / "waivers.yaml").write_text(
        "waivers:\n"
        "  - id: 'secret:aws-access-token:src/a.py:3'\n"
        "    reason: fixture key\n"
        "    author: bob-test\n"
        "    date: '2026-10-13'\n"
        "  - id: 'aws-access-token:src/b.py:4'\n"
        "    reason: missing prefix\n"
        "    author: bob-test\n"
        "    date: '2026-10-13'\n"
    )
    body = _report(("src/a.py", 3, _AWS), ("src/b.py", 4, _AWS))
    _install(tmp_path, monkeypatch, Gitleaks((Detect(body),)))

    run = run_secrets_gate(repo, Config(), {"src/a.py": {3}, "src/b.py": {4}})

    assert _seen(run) == {
        "exit_code": 1,
        "name": "secrets",
        "status": "failed",
        "reason": ("1 new secret in the diff", "1 segredo novo no diff"),
        "ledger": SecretLedger(blocking=(SecretRow("src/b.py", 4, _AWS),)),
        "versions": {"gitleaks": "8.30.1"},
    }


def test_duplicate_findings_collapse_and_rows_sort(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _report(
        ("src/b.py", 1, _AWS),
        ("src/a.py", 2, _AWS),
        ("src/a.py", 1, "generic-api-key"),
        ("src/a.py", 1, _AWS),
        ("src/a.py", 2, _AWS),
        ("src/a.py", 3, "a-rule"),
    )
    _install(tmp_path, monkeypatch, Gitleaks((Detect(body),)))

    run = run_secrets_gate(repo, Config(), {"src/a.py": {1}})

    assert _seen(run) == {
        "exit_code": 1,
        "name": "secrets",
        "status": "failed",
        "reason": (
            "2 new secrets in the diff; 3 secrets outside the diff",
            "2 segredos novos no diff; 3 segredos fora do diff",
        ),
        "ledger": SecretLedger(
            blocking=(
                SecretRow("src/a.py", 1, _AWS),
                SecretRow("src/a.py", 1, "generic-api-key"),
            ),
            outside_diff=(
                SecretRow("src/a.py", 2, _AWS),
                SecretRow("src/a.py", 3, "a-rule"),
                SecretRow("src/b.py", 1, _AWS),
            ),
        ),
        "versions": {"gitleaks": "8.30.1"},
    }


def test_a_null_report_from_the_second_root_discards_the_first_roots_rows(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / "lib").mkdir()
    first = Detect(_report(("src/a.py", 3, _AWS)))
    _install(tmp_path, monkeypatch, Gitleaks((first, Detect("null", 0))))

    run = run_secrets_gate(repo, Config(include=("src", "lib")), {"src/a.py": {3}})

    assert _seen(run) == {
        "exit_code": 4,
        "name": "secrets",
        "status": "not_run",
        "reason": _UNREADABLE,
        "ledger": None,
        "versions": {"gitleaks": "8.30.1"},
    }


def test_rows_from_two_roots_merge_sorted(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / "lib").mkdir()
    first = Detect(_report(("src/b.py", 1, _AWS)))
    second = Detect(_report(("lib/a.py", 5, _AWS)))
    _install(tmp_path, monkeypatch, Gitleaks((first, second)))

    run = run_secrets_gate(repo, Config(include=("src", "lib")), {})

    assert _seen(run) == {
        "exit_code": 0,
        "name": "secrets",
        "status": "passed",
        "reason": ("2 secrets outside the diff", "2 segredos fora do diff"),
        "ledger": SecretLedger(
            outside_diff=(SecretRow("lib/a.py", 5, _AWS), SecretRow("src/b.py", 1, _AWS)),
        ),
        "versions": {"gitleaks": "8.30.1"},
    }


def test_each_detect_starts_after_the_previous_report_is_gone(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repo / "lib").mkdir()
    first = Detect(_report(("src/a.py", 3, _AWS)))
    bin_dir = _install(tmp_path, monkeypatch, Gitleaks((first, Detect("[]", 0))))

    run = run_secrets_gate(repo, Config(include=("src", "lib")), {"src/a.py": {3}})

    detects = [call for call in _calls(bin_dir) if call["argv"][1] == "detect"]
    assert [(call["argv"][4], call["report_existed"]) for call in detects] == [
        (str((repo / "src").resolve()), False),
        (str((repo / "lib").resolve()), False),
    ]
    assert run.exit_code == 1
    assert run.ledger == SecretLedger(blocking=(SecretRow("src/a.py", 3, _AWS),))


def test_detect_receives_the_exact_argv_from_the_repo_root(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = _install(tmp_path, monkeypatch, Gitleaks((Detect("[]", 0),)))

    run = run_secrets_gate(repo, Config(), {})

    binary = str(bin_dir / "gitleaks")
    version, detect = _calls(bin_dir)
    scratch = Path(detect["argv"][6]).parent
    assert version["argv"] == [binary, "--version"]
    assert detect["argv"] == [
        binary,
        "detect",
        "--no-git",
        "--source",
        str((repo / "src").resolve()),
        "--config",
        str(scratch / "scope.toml"),
        "--report-format",
        "json",
        "--report-path",
        str(scratch / "gitleaks.json"),
        "--exit-code",
        "1",
        "--redact",
        "--no-banner",
        "--ignore-gitleaks-allow",
        "--gitleaks-ignore-path",
        str(scratch / "ignore"),
    ]
    assert detect["cwd"] == str(repo.resolve())
    assert scratch.name.startswith("bob-gitleaks-")
    assert not scratch.exists()
    assert _seen(run) == _PASSED


def test_gitleaks_output_stays_out_of_the_callers_stdout_and_stderr(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    bin_dir = _install(tmp_path, monkeypatch, Gitleaks((Detect("[]", 0),)))

    run = run_secrets_gate(repo, Config(), {})

    assert [call["argv"][1] for call in _calls(bin_dir)] == ["--version", "detect"]
    assert capfd.readouterr() == ("", "")
    assert _seen(run) == _PASSED


def test_the_scope_config_escapes_and_dedupes_the_excludes(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = _install(tmp_path, monkeypatch, Gitleaks((Detect("[]", 0),)))

    run = run_secrets_gate(repo, Config(exclude=("gen+x", "tests", "gen+x", ".git")), {})

    detect = _calls(bin_dir)[1]
    assert detect["config"] == (
        "[extend]\n"
        "useDefault = true\n"
        "[[allowlists]]\n"
        r"paths = [ '''(^|/)gen\+x(/|$)''' , '''(^|/)tests(/|$)''' , "
        r"'''(^|/)\.git(/|$)''' , '''(^|/)\.bob(/|$)''' ]"
        "\n"
    )
    assert _seen(run) == _PASSED


def test_gitleaks_runs_without_the_config_and_pytest_env(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITLEAKS_CONFIG", "/elsewhere/gitleaks.toml")
    monkeypatch.setenv("GITLEAKS_CONFIG_TOML", "[extend]")
    monkeypatch.setenv("PYTEST_ADDOPTS", "-x")
    monkeypatch.setenv("BOB_KEEP", "yes")
    bin_dir = _install(tmp_path, monkeypatch, Gitleaks((Detect("[]", 0),)))

    run = run_secrets_gate(repo, Config(), {})

    assert _seen(run) == _PASSED
    assert [(call["argv"][1], call["env"]) for call in _calls(bin_dir)] == [
        (
            "--version",
            {
                "GITLEAKS_CONFIG": False,
                "GITLEAKS_CONFIG_TOML": False,
                "PYTEST_ADDOPTS": False,
                "BOB_KEEP": True,
            },
        ),
        (
            "detect",
            {
                "GITLEAKS_CONFIG": False,
                "GITLEAKS_CONFIG_TOML": False,
                "PYTEST_ADDOPTS": False,
                "BOB_KEEP": True,
            },
        ),
    ]


def _seen(run: SecretsRun) -> dict[str, object]:
    reason = run.result.reason
    return {
        "exit_code": run.exit_code,
        "name": run.result.name,
        "status": run.result.status,
        "reason": None if reason is None else in_both(reason),
        "ledger": run.ledger,
        "versions": run.versions,
    }


def _report(*rows: tuple[str, int, str]) -> str:
    return json.dumps([{"File": file, "StartLine": line, "RuleID": rule} for file, line, rule in rows])


def _hex(body: str | bytes | None) -> str | None:
    if body is None:
        return None
    if isinstance(body, str):
        return body.encode().hex()
    return body.hex()


def _install_bob_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home_bin = tmp_path / "bh" / "bin"
    home_bin.mkdir(parents=True)
    stub = home_bin / "gitleaks"
    stub.write_text(f"#!{sys.executable}\n{_BOB_HOME_STUB}")
    stub.chmod(0o755)
    monkeypatch.setenv("BOB_HOME", str(tmp_path / "bh"))
    return home_bin


def _install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, plan: Gitleaks) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "plan.json").write_text(json.dumps(plan.encoded()))
    fake = bin_dir / "gitleaks"
    fake.write_text(f"#!{sys.executable}\n{_FAKE}")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir))
    return bin_dir


def _calls(bin_dir: Path) -> list[dict[str, object]]:
    log = bin_dir / "calls.jsonl"
    if not log.is_file():
        return []
    return [json.loads(line) for line in log.read_text().splitlines()]
