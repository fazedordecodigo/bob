"""Mata o que sobrou do gate de segurança. Cada assert compara com um literal."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest
from helpers import in_both

from bob_quality.adapters.bandit import BanditParseError, parse_bandit
from bob_quality.adapters.sast_json import at, parsed_results
from bob_quality.adapters.semgrep import SemgrepParseError, parse_semgrep
from bob_quality.config import Config, ConfigError, load_config
from bob_quality.exit_codes import GATE_FAILED, PASSED
from bob_quality.messages import msg
from bob_quality.models import (
    Fail,
    Finding,
    GateResult,
    Measured,
    Report,
    SecurityReport,
    Severity,
    Unmeasured,
)
from bob_quality.security_gate import (
    _baseline,
    _detached,
    _git,
    _merge_base,
    _note_dropped,
    _rules_ready,
    _scan_at,
    _scan_row,
    _status,
    run_security_gate,
    security_verdict,
)
from bob_quality.security_scanners import (
    Scanner,
    _bandit_installed,
    _distribution_installed,
    _semgrep_installed,
    scanners_for,
)
from bob_quality.security_scanners import InPlace


def test_detached_worktree_names_the_directory_and_removes_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bob_quality import security_gate

    created: list[str] = []
    calls: list[tuple[Path | None, tuple[str, ...]]] = []
    removed: list[tuple[Path, bool]] = []
    real_mkdtemp = tempfile.mkdtemp
    real_rmtree = shutil.rmtree

    def spy_mkdtemp(prefix: str | None = None) -> str:
        assert prefix == "bob-semgrep-"
        path = real_mkdtemp(prefix=prefix)
        created.append(path)
        return path

    def spy_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        calls.append((cwd, args))
        if args[:2] == ("worktree", "add"):
            return subprocess.CompletedProcess(args, 1, "", "fatal: boom")
        return subprocess.CompletedProcess(args, 0, "", "")

    def spy_rmtree(path: Path, ignore_errors: bool = False) -> None:
        removed.append((path, ignore_errors))
        if ignore_errors is not True:
            raise OSError("busy")
        real_rmtree(path, ignore_errors=True)

    monkeypatch.setattr(security_gate.tempfile, "mkdtemp", spy_mkdtemp)
    monkeypatch.setattr(security_gate, "_git", spy_git)
    monkeypatch.setattr(security_gate.shutil, "rmtree", spy_rmtree)

    with pytest.raises(security_gate._PrepError) as caught:
        next(_detached(tmp_path))

    parent = Path(created[0]).resolve()
    root = parent / "head"
    assert caught.value.detail == "fatal: boom"
    assert calls == [(tmp_path, ("worktree", "add", "--detach", str(root), "HEAD"))]
    assert removed == [(parent, True)]
    assert not parent.exists()

    calls.clear()
    removed.clear()

    def spy_git_ok(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        calls.append((cwd, args))
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(security_gate, "_git", spy_git_ok)
    generated = _detached(tmp_path)
    yielded = next(generated)
    generated.close()

    parent = Path(created[1]).resolve()
    root = parent / "head"
    assert yielded == root
    assert calls == [
        (tmp_path, ("worktree", "add", "--detach", str(root), "HEAD")),
        (tmp_path, ("worktree", "remove", "--force", str(root))),
        (tmp_path, ("worktree", "prune")),
    ]
    assert removed == [(parent, True)]
    assert not parent.exists()


def test_git_keeps_a_failed_command(monkeypatch: pytest.MonkeyPatch) -> None:
    from bob_quality import security_gate

    seen: dict[str, object] = {}

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["kwargs"] = kwargs
        return subprocess.CompletedProcess(args, 1, "", "fatal")

    monkeypatch.setattr(security_gate.subprocess, "run", fake_run)
    completed = _git(Path("/tmp/bob-sec"), "status")

    assert completed.returncode == 1
    kwargs = seen["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["check"] is False
    assert kwargs["cwd"] == Path("/tmp/bob-sec")
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True


def test_run_security_gate_forwards_the_repo_and_the_baseline_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bob_quality import security_gate

    note = msg("security.worktree_failed", detail="fatal: boom")
    seen: dict[str, object] = {}

    def fake_baseline(cwd: Path, base: str, rows: tuple[Scanner, ...]) -> tuple[None, object]:
        seen["cwd"] = cwd
        seen["base"] = base
        seen["rows"] = rows
        return None, note

    def fake_scan(
        cwd: Path,
        config: Config,
        row: Scanner,
        baseline: str | None,
        baseline_error: object,
    ) -> Unmeasured:
        seen["scan"] = (cwd, config, row.tool, baseline, baseline_error)
        return Unmeasured(row.tool, note)

    monkeypatch.setattr(security_gate, "_baseline", fake_baseline)
    monkeypatch.setattr(security_gate, "_scan_row", fake_scan)
    config = Config()
    run_security_gate(tmp_path, config, "main", {})

    assert seen["cwd"] == tmp_path
    assert seen["base"] == "main"
    assert seen["scan"] == (tmp_path, config, "bandit", None, note)


def test_baseline_and_merge_base_keep_the_git_detail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bob_quality import security_gate

    def boom(cwd: Path, base: str) -> str:
        raise security_gate._PrepError("fatal: boom")

    monkeypatch.setattr(security_gate, "_merge_base", boom)
    baseline, err = _baseline(tmp_path, "main", scanners_for(("typescript",)))

    assert baseline is None
    assert in_both(err) == (
        "semgrep worktree failed: fatal: boom",
        "worktree do semgrep falhou: fatal: boom",
    )

    def fake_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        assert (cwd, args) == (tmp_path, ("merge-base", "main", "HEAD"))
        return subprocess.CompletedProcess(args, 1, "", "fatal: boom")

    monkeypatch.setattr(security_gate, "_git", fake_git)
    with pytest.raises(security_gate._PrepError) as caught:
        _merge_base(tmp_path, "main")
    assert caught.value.detail == "fatal: boom"


def test_scan_row_sends_the_baseline_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bob_quality import security_gate

    seen: list[str | None] = []

    def fake_at(root: Path, config: Config, row: Scanner, baseline: str) -> Measured:
        seen.append(baseline)
        return Measured(row.tool, "1", ())

    def fake_root(plan: object, cwd: Path):
        yield cwd

    monkeypatch.setattr(security_gate, "_scan_at", fake_at)
    monkeypatch.setattr(security_gate, "_scan_root", fake_root)
    bandit = scanners_for(("python",))[0]
    semgrep = scanners_for(("typescript",))[0]

    _scan_row(tmp_path, Config(), bandit, None, None)
    _scan_row(tmp_path, Config(), semgrep, "abc123", None)

    assert seen == ["", "abc123"]


def test_scan_at_pins_the_context_the_crash_and_the_parse_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bob_quality import security_gate

    (tmp_path / "src").mkdir()
    contexts: list[object] = []
    parsed: list[Path] = []
    mode = {"crash": True}

    def argv(ctx: object) -> list[str]:
        contexts.append(ctx)
        return ["echo"]

    def parse(stdout: str, root: Path) -> tuple[Finding, ...]:
        parsed.append(root)
        assert stdout == "{}"
        return ()

    row = Scanner(
        tool="bandit",
        language="python",
        distribution="missing-dist-xyz",
        labels=("HIGH",),
        measurement_exits=frozenset({0, 1}),
        needs_baseline=False,
        root=InPlace(),
        rules_dir=None,
        suffixes=(".py",),
        argv=argv,
        parse=parse,
        installed=lambda: True,
    )

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if mode["crash"]:
            raise OSError("boom")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(security_gate.subprocess, "run", fake_run)
    crashed = _scan_at(tmp_path, Config(include=("src",)), row, "abc123")

    assert isinstance(crashed, Unmeasured)
    assert in_both(crashed.reason) == ("bandit: boom", "bandit: boom")
    ctx = contexts[0]
    assert ctx.merge_base == "abc123"
    assert ctx.scan_root == tmp_path
    assert ctx.suffixes == (".py",)
    assert ctx.targets == ("src",)

    mode["crash"] = False
    measured = _scan_at(tmp_path, Config(include=("src",)), row, "abc123")
    assert isinstance(measured, Measured)
    assert measured.version == ""
    assert parsed == [tmp_path]

    pinned = _scan_at(
        tmp_path,
        Config(include=("src",)),
        replace(row, pinned_version="1.180.0"),
        "abc123",
    )
    assert isinstance(pinned, Measured)
    assert pinned.version == "1.180.0"


def test_rules_ready_accepts_yml_and_yaml_only(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert _rules_ready(missing) is False

    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "readme.txt").write_text("x")
    assert _rules_ready(notes) is False

    yml = tmp_path / "yml"
    yml.mkdir()
    (yml / "rule.yml").write_text("rules: []\n")
    assert _rules_ready(yml) is True

    yaml = tmp_path / "yaml"
    yaml.mkdir()
    (yaml / "rule.yaml").write_text("rules: []\n")
    assert _rules_ready(yaml) is True


def test_status_and_verdict_name_the_security_gate() -> None:
    with pytest.raises(KeyError) as caught:
        _status(9)
    assert caught.value.args == (9,)

    finding = Finding("bandit", "B101", "src/app.py", 1, 1, Severity("LOW"))
    result, code = security_verdict((Fail(finding),))
    assert code == GATE_FAILED
    assert result.name == "security"
    assert result.status == "failed"
    assert in_both(result.reason) == (
        "1 findings in security.fail_severities",
        "1 achados em security.fail_severities",
    )


def test_a_dropped_scanner_keeps_its_name_and_an_empty_failure_reason() -> None:
    note = msg("tool.missing", tool="semgrep")
    failed, code = _note_dropped(GateResult("security", "failed", None), GATE_FAILED, [note])
    assert code == GATE_FAILED
    assert failed.name == "security"
    assert failed.status == "failed"
    assert in_both(failed.reason) == in_both(note)

    warned, warned_code = _note_dropped(GateResult("security", "passed"), PASSED, [note])
    assert warned_code == PASSED
    assert warned.name == "security"
    assert warned.status == "warn"
    assert in_both(warned.reason) == in_both(note)


def test_installed_checks_name_the_distribution(monkeypatch: pytest.MonkeyPatch) -> None:
    from bob_quality import security_scanners as scanners

    assert _distribution_installed("no-such-bob-distribution") is False
    seen: list[str] = []

    def fake(name: str) -> bool:
        seen.append(name)
        return name == "bandit"

    monkeypatch.setattr(scanners, "_distribution_installed", fake)
    assert _bandit_installed() is True
    assert seen == ["bandit"]

    monkeypatch.setattr(scanners.shutil, "which", lambda name: None)
    assert _semgrep_installed() is False


def test_vocabulary_rejects_a_non_list_with_the_string_list_key() -> None:
    from bob_quality.config import _Check, _vocabulary

    assert _vocabulary(_Check("vocabulary", choices=("HIGH", "CRITICAL")), 4) == (
        "config.key_string_list",
        "",
        {},
    )


def test_fail_severities_that_are_not_strings_name_the_key(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("security:\n  fail_severities: 4\n")
    with pytest.raises(ConfigError) as caught:
        load_config(None, tmp_path)
    assert in_both(caught.value) == (
        "bob.yaml: security.fail_severities must be a list of strings",
        "bob.yaml: security.fail_severities deve ser uma lista de textos",
    )


def test_security_section_keeps_the_blank_lines_and_the_separator() -> None:
    from bob_quality.report import to_markdown

    finding = Finding("bandit", "B602", "src/app.py", 1, 1, Severity("HIGH"))
    report = Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-13T00:00:00+00:00",
        tool_versions={},
        gates=[GateResult("security", "failed", msg("security.failed", count=1))],
        focus=[],
        top_crap=[],
        security=SecurityReport((Fail(finding),), ()),
    )
    lines = to_markdown(report, "en").splitlines()
    index = lines.index("## Security")
    assert lines[index - 1] == ""
    assert lines[index + 1] == ""
    assert lines[index + 2] == "| Tool | Rule | Location | Severity | Disposition | Waiver |"
    assert lines[index + 3] == "|---|---|---|---|---|---|"

    gap = Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-13T00:00:00+00:00",
        tool_versions={},
        gates=[GateResult("security", "not_run")],
        focus=[],
        top_crap=[],
        security=SecurityReport((), ("semgrep",)),
    )
    assert "\n## Security\n\nNo findings.\n" in to_markdown(gap, "en")


def test_parsers_name_invalid_json_and_a_missing_results_list(tmp_path: Path) -> None:
    with pytest.raises(BanditParseError) as bandit_json:
        parse_bandit("{", tmp_path)
    assert in_both(bandit_json.value) == ("bandit: invalid JSON", "bandit: JSON inválido")

    with pytest.raises(BanditParseError) as bandit_list:
        parse_bandit("[]", tmp_path)
    assert in_both(bandit_list.value) == (
        "bandit: JSON without a results list",
        "bandit: JSON sem a lista results",
    )

    with pytest.raises(BanditParseError) as bandit_object:
        parse_bandit("{}", tmp_path)
    assert in_both(bandit_object.value) == (
        "bandit: JSON without a results list",
        "bandit: JSON sem a lista results",
    )

    with pytest.raises(SemgrepParseError) as semgrep_json:
        parse_semgrep("{", tmp_path)
    assert in_both(semgrep_json.value) == ("semgrep: invalid JSON", "semgrep: JSON inválido")

    with pytest.raises(SemgrepParseError) as semgrep_list:
        parse_semgrep("[]", tmp_path)
    assert in_both(semgrep_list.value) == (
        "semgrep: JSON without a results list",
        "semgrep: JSON sem a lista results",
    )

    with pytest.raises(SemgrepParseError) as semgrep_object:
        parse_semgrep("{}", tmp_path)
    assert in_both(semgrep_object.value) == (
        "semgrep: JSON without a results list",
        "semgrep: JSON sem a lista results",
    )

    with pytest.raises(BanditParseError) as direct:
        parsed_results(
            "{",
            BanditParseError,
            msg("bandit.invalid_json"),
            msg("bandit.no_results"),
            lambda item: None,
        )
    assert in_both(direct.value) == ("bandit: invalid JSON", "bandit: JSON inválido")


def test_an_absolute_path_stays_inside_the_scan_root(tmp_path: Path) -> None:
    source = tmp_path / "src" / "app.py"
    source.parent.mkdir()
    source.write_text("x = 1\n")
    found = at("bandit", "B101", str(source), tmp_path, 1, 1, "HIGH")
    assert found == Finding("bandit", "B101", "src/app.py", 1, 1, Severity("HIGH"))
