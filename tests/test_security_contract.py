"""Contrato in-process dos scanners, do gate e do relatório. A CLI sozinha não mata o mutante."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from helpers import in_both

from bob_quality.churn import ChurnUnavailable
from bob_quality.config import Config
from bob_quality.exit_codes import CONFIG_OR_TOOL, GATE_FAILED, PASSED
from bob_quality.messages import msg
from bob_quality.models import (
    Fail,
    Finding,
    FunctionMetric,
    GateResult,
    Measured,
    OffDiff,
    Report,
    SecurityReport,
    Severity,
    Unmeasured,
    Waived,
    Warn,
)
from bob_quality.mutate import MutationOutcome
from bob_quality.security_gate import (
    FailSeverities,
    _baseline,
    _fold,
    _git_detail,
    _join,
    _scan_row,
    judge,
    run_security_gate,
)
from bob_quality.security_scanners import (
    _BANDIT_EXCLUDE,
    ScanContext,
    _bandit_argv,
    _bandit_installed,
    _reject_bad_table,
    _semgrep_argv,
    _semgrep_installed,
    distribution_version,
    scanners_for,
    severity_vocabulary,
)

_POLICY = FailSeverities(frozenset(Severity(label) for label in ("HIGH", "CRITICAL", "ERROR")))
_VOCABULARY = (
    "HIGH",
    "MEDIUM",
    "LOW",
    "UNDEFINED",
    "CRITICAL",
    "ERROR",
    "WARNING",
    "INFO",
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    source = repo / "src"
    source.mkdir(parents=True)
    (source / "app.py").write_text("def ready():\n    return 1\n")
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "user.email", "bob-test@example.com")
    _git(repo, "config", "user.name", "bob-test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    return repo


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _high(line: int = 1) -> Finding:
    return Finding("bandit", "B602", "src/app.py", line, line, Severity("HIGH"))


def _bandit_stdout(severity: str) -> str:
    return json.dumps(
        {
            "results": [
                {
                    "test_id": "B602",
                    "filename": "src/app.py",
                    "issue_severity": severity,
                    "line_number": 1,
                }
            ]
        }
    )


def test_scanner_commands_are_pinned(tmp_path: Path) -> None:
    ini = tmp_path / "empty.ini"
    ini.write_text("#\n")
    ctx = ScanContext(
        exclude=("tests", "node_modules", "dist"),
        targets=("src",),
        merge_base="abc123",
        scan_root=tmp_path,
        empty_ini=ini,
        suffixes=(".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"),
    )

    assert _bandit_argv(ctx) == [
        sys.executable,
        "-m",
        "bandit",
        "--recursive",
        "--format",
        "json",
        "--quiet",
        "--severity-level",
        "all",
        "--confidence-level",
        "all",
        "--ignore-nosec",
        "--ini",
        str(ini),
        "--exclude",
        ",".join((*_BANDIT_EXCLUDE, "tests", "node_modules", "dist")),
        "src",
    ]
    binary = str(Path(sys.executable).parent / "semgrep")
    assert _semgrep_argv(ctx) == [
        binary,
        "scan",
        "--disable-version-check",
        "--metrics=off",
        "--disable-nosem",
        "--error",
        "--quiet",
        "--json",
        "--baseline-commit",
        "abc123",
        "--config",
        str(tmp_path / ".semgrep"),
        "--exclude",
        "tests",
        "--exclude",
        "node_modules",
        "--exclude",
        "dist",
        "--include",
        "*.ts",
        "--include",
        "*.tsx",
        "--include",
        "*.js",
        "--include",
        "*.jsx",
        "--include",
        "*.mjs",
        "--include",
        "*.cjs",
        "src",
    ]


def test_scanner_table_rejects_a_broken_row_and_publishes_the_vocabulary() -> None:
    bandit = scanners_for(("python",))[0]
    semgrep = scanners_for(("typescript",))[0]

    assert scanners_for(("python",)) == (bandit,)
    assert scanners_for(()) == ()
    assert severity_vocabulary() == _VOCABULARY
    assert distribution_version("bandit") == "1.9.4"
    assert distribution_version("semgrep") == "1.180.0"
    assert distribution_version("bob-missing-distribution") is None
    assert _bandit_installed() is True
    assert _semgrep_installed() is True
    _reject_bad_table((bandit, semgrep))

    with pytest.raises(RuntimeError, match="^duplicate scanner language: python$"):
        _reject_bad_table((bandit, replace(bandit, tool="other")))
    with pytest.raises(RuntimeError, match="^duplicate severity label: bandit$"):
        _reject_bad_table((replace(bandit, labels=("HIGH", "HIGH")),))
    with pytest.raises(RuntimeError, match="^empty measurement exits: bandit$"):
        _reject_bad_table((replace(bandit, measurement_exits=frozenset()),))


def test_a_duplicate_waiver_is_not_run(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    waiver_dir = repo / ".bob"
    waiver_dir.mkdir()
    (waiver_dir / "waivers.yaml").write_text(
        "waivers:\n"
        "  - {id: sast:bandit:B602, reason: one, author: ada, date: '2026-10-12'}\n"
        "  - {id: sast:bandit:B602, reason: two, author: ada, date: '2026-10-12'}\n"
    )

    result, code, versions, report = run_security_gate(repo, Config(), "main", {})

    assert result.name == "security"
    assert result.status == "not_run"
    assert result.reason is not None
    assert in_both(result.reason) == (
        ".bob/waivers.yaml: waivers[1].id repeats waivers[0].id",
        ".bob/waivers.yaml: waivers[1].id repete waivers[0].id",
    )
    assert code == CONFIG_OR_TOOL
    assert versions == {}
    assert report == SecurityReport((), ())


def test_bandit_scan_pins_the_process_and_an_empty_include(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    seen: dict[str, object] = {}

    def fake(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["argv"] = list(argv)
        seen["kwargs"] = kwargs
        ini = Path(argv[argv.index("--ini") + 1])
        seen["ini"] = (ini.name, ini.parent.name, ini.read_text())
        return subprocess.CompletedProcess(argv, 0, stdout='{"results": []}', stderr="")

    monkeypatch.setattr("bob_quality.security_gate.subprocess.run", fake)
    result, code, versions, report = run_security_gate(repo, Config(), "main", {})

    assert (result, code, report.findings, report.unmeasured) == (
        GateResult("security", "passed"),
        PASSED,
        (),
        (),
    )
    assert versions == {"bandit": "1.9.4"}
    kwargs = seen["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["cwd"] == repo
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["check"] is False
    assert kwargs["timeout"] == 180
    argv = seen["argv"]
    assert isinstance(argv, list)
    assert argv[:12] == [
        sys.executable,
        "-m",
        "bandit",
        "--recursive",
        "--format",
        "json",
        "--quiet",
        "--severity-level",
        "all",
        "--confidence-level",
        "all",
        "--ignore-nosec",
    ]
    assert argv[argv.index("--exclude") + 1] == ",".join(
        (*_BANDIT_EXCLUDE, *Config().exclude)
    )
    assert argv[-1] == "src"
    assert seen["ini"] == ("empty.ini", seen["ini"][1], "#\n")
    assert str(seen["ini"][1]).startswith("bob-bandit-")

    seen.clear()
    result, code, versions, report = run_security_gate(
        repo, Config(include=("missing",)), "main", {}
    )
    assert seen == {}
    assert (result, code, versions, report) == (
        GateResult("security", "passed"),
        PASSED,
        {"bandit": "1.9.4"},
        SecurityReport((), ()),
    )


def test_a_high_hit_fails_and_a_low_hit_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    stdout = {"text": _bandit_stdout("HIGH")}

    def fake(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, stdout=stdout["text"], stderr="")

    monkeypatch.setattr("bob_quality.security_gate.subprocess.run", fake)
    diff = {"src/app.py": {1}}
    result, code, versions, report = run_security_gate(repo, Config(), "main", diff)

    assert code == GATE_FAILED
    assert result.status == "failed"
    assert in_both(result.reason) == (
        "1 findings in security.fail_severities",
        "1 achados em security.fail_severities",
    )
    assert versions == {"bandit": "1.9.4"}
    assert report.unmeasured == ()
    assert report.findings == (Fail(_high()),)

    stdout["text"] = _bandit_stdout("LOW")
    result, code, _versions, report = run_security_gate(repo, Config(), "main", diff)
    low = Finding("bandit", "B602", "src/app.py", 1, 1, Severity("LOW"))
    assert (result.status, code, report.findings) == ("warn", PASSED, (Warn(low),))
    assert in_both(result.reason) == (
        "1 findings outside security.fail_severities",
        "1 achados fora de security.fail_severities",
    )


def test_missing_rules_and_a_missing_tool_stay_unmeasured(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    result, code, versions, report = run_security_gate(
        repo, Config(languages=("typescript",)), "main", {}
    )

    assert result.name == "security"
    assert result.status == "not_run"
    assert code == CONFIG_OR_TOOL
    assert versions == {}
    assert report == SecurityReport((), ("semgrep",))
    assert in_both(result.reason) == in_both(msg("security.rules_missing"))

    hidden = replace(scanners_for(("python",))[0], installed=lambda: False)
    missed = _scan_row(repo, Config(), hidden, None, None)
    assert missed == Unmeasured("bandit", msg("tool.missing", tool="bandit"))

    semgrep = scanners_for(("typescript",))[0]
    missed = _scan_row(repo, Config(languages=("typescript",)), semgrep, None, None)
    assert missed == Unmeasured("semgrep", msg("security.worktree_failed", detail=""))


def test_a_failed_worktree_names_the_git_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    real = subprocess.run

    def fake(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if list(argv[:3]) == ["git", "worktree", "add"]:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="fatal: boom\n")
        return real(argv, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("bob_quality.security_gate.subprocess.run", fake)
    semgrep = scanners_for(("typescript",))[0]
    missed = _scan_row(repo, Config(languages=("typescript",)), semgrep, "abc123", None)

    assert missed == Unmeasured(
        "semgrep", msg("security.worktree_failed", detail="fatal: boom")
    )


def test_baseline_uses_this_repo_and_names_a_bad_base(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    rows = scanners_for(("python",))
    assert _baseline(repo, "main", rows) == (None, None)

    sha = subprocess.check_output(
        ["git", "merge-base", "main", "HEAD"], cwd=repo, text=True
    ).strip()
    assert _baseline(repo, "main", scanners_for(("typescript",))) == (sha, None)

    baseline, error = _baseline(repo, "not-a-base", scanners_for(("typescript",)))
    assert baseline is None
    assert error is not None
    assert in_both(error)[0].startswith("semgrep worktree failed: ")
    assert in_both(error)[1].startswith("worktree do semgrep falhou: ")


def test_git_detail_keeps_the_last_line() -> None:
    noisy = subprocess.CompletedProcess(["git"], 1, stdout="", stderr="noise\nbad ref\n")
    assert _git_detail(noisy) == "bad ref"
    empty = subprocess.CompletedProcess(["git"], 4, stdout="", stderr="   ")
    assert _git_detail(empty) == "exit 4"
    stdout_only = subprocess.CompletedProcess(["git"], 1, stdout="from stdout\n", stderr="")
    assert _git_detail(stdout_only) == "from stdout"


def test_fold_joins_a_failure_with_what_was_not_measured() -> None:
    finding = _high()
    measured = Measured("bandit", "1.9.4", (finding,))
    missed = Unmeasured("semgrep", msg("tool.missing", tool="semgrep"))
    low = Finding("bandit", "B602", "src/app.py", 1, 1, Severity("LOW"))
    off = Finding("bandit", "B602", "src/other.py", 9, 9, Severity("HIGH"))

    result, code, versions, report = _fold(
        (measured, missed), {"src/app.py": {1}}, _POLICY, ()
    )
    assert result == GateResult(
        "security",
        "failed",
        msg(
            "probe.joined",
            first=msg("security.failed", count=1),
            second=missed.reason,
        ),
    )
    assert code == GATE_FAILED
    assert versions == {"bandit": "1.9.4"}
    assert report == SecurityReport((Fail(finding),), ("semgrep",))

    warned, warn_code, _versions, warn_report = _fold(
        (Measured("bandit", "1.9.4", (low, off)), missed),
        {"src/app.py": {1}},
        _POLICY,
        (),
    )
    assert warned.status == "warn"
    assert warn_code == PASSED
    assert warned.reason == missed.reason
    assert warn_report.findings == (Warn(low), OffDiff(off))

    result, code, versions, report = _fold((missed,), {}, _POLICY, ())
    assert result == GateResult("security", "not_run", missed.reason)
    assert code == CONFIG_OR_TOOL
    assert versions == {}
    assert report == SecurityReport((), ("semgrep",))

    assert in_both(_join([])) == (
        "missing tool: security",
        "ferramenta ausente: security",
    )
    joined = _join(
        [msg("tool.missing", tool="bandit"), msg("tool.missing", tool="semgrep")]
    )
    assert in_both(joined) == (
        "missing tool: bandit; missing tool: semgrep",
        "ferramenta ausente: bandit; ferramenta ausente: semgrep",
    )


def test_judge_returns_the_same_finding() -> None:
    low = Finding("bandit", "B602", "src/app.py", 1, 1, Severity("LOW"))
    assert judge(low, {"src/app.py": {1}}, _POLICY, ()) == Warn(low)


def test_an_empty_waiver_reason_is_rejected() -> None:
    with pytest.raises(ValueError, match="^reason$"):
        Waived(_high(), "")
    assert Waived(_high(), "kept").reason == "kept"


def test_measure_forwards_security_and_assemble_publishes_it(tmp_path: Path, monkeypatch) -> None:
    from bob_quality import check as check_mod
    from bob_quality.models import Clone, DepViolation

    security = SecurityReport((), ("semgrep",))
    result = GateResult("security", "warn", msg("security.warn", count=1))
    seen: dict[str, object] = {}

    def fake(cwd: Path, config: Config, base: str, diff_lines: dict[str, set[int]]):
        seen["call"] = (cwd, config, base, diff_lines)
        return result, PASSED, {"bandit": "1.9.4"}, security

    monkeypatch.setattr(check_mod, "run_security_gate", fake)
    config = Config()
    diff = {"src/app.py": {1}}
    state = check_mod._measure(
        tmp_path,
        config,
        "main",
        diff,
        10.0,
        None,
        ["security"],
        tmp_path,
        None,
        False,
        None,
    )
    assert seen["call"] == (tmp_path, config, "main", diff)
    assert state.security is security
    assert state.gates == [result]
    assert state.versions == {"bandit": "1.9.4"}
    assert state.exit_code == PASSED

    changed = FunctionMetric(
        "python", "app", "add", "src/app.py", 1, 4, 1, 1.0, 4.0, True
    )
    old = FunctionMetric(
        "python", "old", "legacy", "src/old.py", 1, 20, 12, 0.0, 30.0, False
    )
    clone = Clone("src/a.py", 1, 2, "src/b.py", 1, 2, 2, 10)
    state.metrics = [changed, old]
    state.clones = [clone]
    state.violations = [
        DepViolation("app", "legacy", "cycle", True),
        DepViolation("old", "legacy", "cycle", False),
    ]
    state.loaded_waivers = [{"id": "idle"}]
    state.mutation = MutationOutcome(
        GateResult("mutate", "passed"),
        PASSED,
        {"mutmut": "3.8.0"},
        [{"id": "m", "reason": "because", "author": "ada", "date": "2026-10-12"}],
        [{"file": "src/survivor.py", "blocking": True}],
        {"remutated": ["src/app.py::add"], "reused": []},
    )
    report = check_mod._assemble(
        state, "abc123", "main", diff, 10.0, "bob check", ChurnUnavailable()
    )

    assert report.schema_version == 1
    assert report.commit == "abc123"
    assert report.base == "main"
    assert report.generated_at.endswith("+00:00")
    assert report.tool_versions == {"bandit": "1.9.4"}
    assert report.gates == [result]
    assert report.clones == [clone]
    assert report.reproduce == "bob check"
    assert report.exit_code == PASSED
    assert report.churn == ChurnUnavailable()
    assert report.security is security
    assert report.secrets is None
    assert report.dead_code is None
    assert report.waivers == state.mutation.waivers
    assert report.survivors == [{"file": "src/survivor.py", "blocking": True}]
    assert report.mutation == {"remutated": ["src/app.py::add"], "reused": []}
    assert report.top_crap[0]["name"] == "add"
    assert report.old_debt[0]["file"] == "src/old.py"
    assert [item["origin"] for item in report.dependencies] == ["app"]
    assert [item["origin"] for item in report.old_dependencies] == ["old"]
    assert any(row["file"] == "src/survivor.py" for row in report.focus)

    state.mutation = None
    idle = check_mod._assemble(
        state, "abc123", "main", diff, 10.0, "bob check", ChurnUnavailable()
    )
    assert idle.mutation is None
    assert idle.waivers == [{"id": "idle"}]
    assert idle.survivors == []
    assert idle.security is security


def test_security_section_renders_a_hit_a_gap_and_an_empty_scan() -> None:
    from bob_quality.report import to_json, to_markdown

    finding = Finding("bandit", "B|602", "src/app.py", 1, 3, Severity("HIGH"))
    waived = Finding("semgrep", "rule", "src/app.ts", 2, 2, Severity("ERROR"))
    report = _report(
        SecurityReport((Fail(finding), Waived(waived, "a|b")), ()),
        GateResult("security", "failed", msg("security.failed", count=1)),
    )
    english = to_markdown(report, "en")
    portuguese = to_markdown(report, "pt-BR")
    assert "| bandit | B\\|602 | src/app.py:1-3 | HIGH | fail | — |" in english
    assert "| semgrep | rule | src/app.ts:2 | ERROR | waived | a\\|b |" in english
    assert "| bandit | B\\|602 | src/app.py:1-3 | HIGH | falha | — |" in portuguese
    assert "dispensado" in portuguese
    payload = to_json(report)
    keys = list(payload)
    assert keys[keys.index("security") + 1] == "churn"
    assert keys[keys.index("churn") + 1] == "reproduce"
    assert payload["security"] == {
        "findings": [
            {
                "tool": "bandit",
                "rule": "B|602",
                "file": "src/app.py",
                "line": 1,
                "end_line": 3,
                "severity": "HIGH",
                "disposition": "fail",
                "waiver": None,
            },
            {
                "tool": "semgrep",
                "rule": "rule",
                "file": "src/app.ts",
                "line": 2,
                "end_line": 2,
                "severity": "ERROR",
                "disposition": "waived",
                "waiver": "a|b",
            },
        ],
        "unmeasured": [],
    }

    gap = _report(
        SecurityReport((), ("semgrep",)),
        GateResult("security", "not_run", msg("tool.missing", tool="semgrep")),
    )
    assert "missing tool: semgrep" in to_markdown(gap, "en")
    assert "No findings." not in to_markdown(gap, "en")
    assert to_json(gap)["security"] == {"findings": [], "unmeasured": ["semgrep"]}

    empty = _report(SecurityReport((), ()), GateResult("security", "passed"))
    assert "No findings." in to_markdown(empty, "en")
    assert "Nenhum achado." in to_markdown(empty, "pt-BR")

    absent = _report(None, GateResult("security", "passed"))
    assert "## Security" not in to_markdown(absent, "en")
    assert "security" not in to_json(absent)


def test_run_check_pins_arguments_and_the_waiver_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bob_quality import check as check_mod

    config = Config()
    diff = {"src/app.py": {1}}
    opened = (config, "origin/main", 12.5, "abc123", diff)
    early = Report(
        schema_version=1,
        commit="early",
        base="origin/main",
        generated_at="2026-10-13T00:00:00+00:00",
        tool_versions={},
        gates=[],
        focus=[],
        top_crap=[],
        reproduce="bob check",
        exit_code=CONFIG_OR_TOOL,
    )
    loaded: list[object] = [[{"id": "idle"}], early]
    opens: list[tuple[object, ...]] = []
    measures: list[tuple[object, ...]] = []
    loads: list[tuple[object, ...]] = []
    written: list[tuple[object, ...]] = []

    def fake_open(
        cwd: Path,
        base: str | None,
        config_path: Path | None,
        threshold: float | None,
        command: str,
        gates: list[str],
    ) -> tuple[Config, str, float, str, dict[str, set[int]]]:
        opens.append((cwd, base, config_path, threshold, command, gates))
        return opened

    def fake_measure(
        cwd: Path,
        measured_config: Config,
        base: str,
        diff_lines: dict[str, set[int]],
        max_crap: float,
        coverage_file: Path | None,
        gates: list[str],
        out_dir: Path,
        max_workers: int | None,
        dry_fail: bool,
        max_new_clones: int | None,
    ) -> check_mod._Measured:
        measures.append(
            (
                cwd,
                measured_config,
                base,
                diff_lines,
                max_crap,
                coverage_file,
                gates,
                out_dir,
                max_workers,
                dry_fail,
                max_new_clones,
            )
        )
        state = check_mod._Measured()
        state.metrics = [
            FunctionMetric(
                "python", "old", "legacy", "src/old.py", 1, 20, 12, 0.0, 20.0, False
            )
        ]
        return state

    def fake_load(
        cwd: Path, base: str, command: str, gates: list[str]
    ) -> list[dict[str, object]] | Report:
        loads.append((cwd, base, command, gates))
        item = loaded.pop(0)
        assert isinstance(item, (list, Report))
        return item

    def fake_written(report: Report, out_dir: Path, fmt: str, lang: str) -> int:
        written.append((report, out_dir, fmt, lang))
        return report.exit_code

    monkeypatch.setattr(check_mod, "_open", fake_open)
    monkeypatch.setattr(check_mod, "_measure", fake_measure)
    monkeypatch.setattr(check_mod, "_load_idle_waivers", fake_load)
    monkeypatch.setattr(check_mod, "_written", fake_written)

    coverage = tmp_path / "coverage.json"
    config_path = tmp_path / "bob.yaml"
    out_dir = tmp_path / "out"
    code = check_mod.run_check(
        tmp_path,
        base="origin/main",
        gates=None,
        config_path=config_path,
        out_dir=out_dir,
        fmt="json",
        threshold=12.5,
        coverage_file=coverage,
        reproduce=None,
        max_workers=3,
        lang="pt-BR",
    )
    assert code == PASSED
    assert opens == [
        (tmp_path, "origin/main", config_path, 12.5, "bob check", list(check_mod.DEFAULT_GATES))
    ]
    assert measures == [
        (
            tmp_path,
            config,
            "origin/main",
            diff,
            12.5,
            coverage,
            list(check_mod.DEFAULT_GATES),
            out_dir,
            3,
            False,
            None,
        )
    ]
    assert loads == [(tmp_path, "origin/main", "bob check", list(check_mod.DEFAULT_GATES))]
    report, got_out, fmt, lang = written[0]
    assert isinstance(report, Report)
    assert report.commit == "abc123"
    assert report.base == "origin/main"
    assert report.reproduce == "bob check"
    assert report.waivers == [{"id": "idle"}]
    assert report.survivors == []
    assert report.mutation is None
    assert report.security is None
    assert report.exit_code == PASSED
    assert report.old_debt[0]["name"] == "legacy"
    assert report.old_debt[0]["crap"] == 20.0
    assert got_out == out_dir
    assert fmt == "json"
    assert lang == "pt-BR"

    failed = check_mod.run_check(
        tmp_path,
        base="origin/main",
        gates=None,
        config_path=config_path,
        out_dir=out_dir,
        fmt="json",
        threshold=12.5,
        coverage_file=coverage,
        reproduce=None,
        max_workers=3,
        lang="pt-BR",
    )
    assert failed == CONFIG_OR_TOOL
    assert written[1] == (early, out_dir, "json", "pt-BR")


def _report(security: SecurityReport | None, gate: GateResult) -> Report:
    return Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-13T00:00:00+00:00",
        tool_versions={},
        gates=[gate],
        focus=[],
        top_crap=[],
        security=security,
    )
