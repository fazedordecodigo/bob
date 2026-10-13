from __future__ import annotations

import io
import os
import re
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from bob_quality.cli import _stop_code, main
from helpers import init_python_repo, run_bob

_COMMAND_GROUP = re.compile(r"\{([^{}]+)\}")


def _usage_4(result: subprocess.CompletedProcess[str], repo: Path) -> None:
    assert result.returncode == 4, result.stderr
    assert result.stderr.startswith("usage: bob"), result.stderr
    assert "error:" in result.stderr, result.stderr
    assert "baseline" not in result.stderr.lower(), result.stderr
    assert not (repo / ".bob").exists(), repo


def _invoke(
    repo: Path, *args: str, bob_lang: str | None = None
) -> subprocess.CompletedProcess[str]:
    previous_cwd = Path.cwd()
    previous_env = os.environ.copy()
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        os.environ.pop("BOB_LANG", None)
        if bob_lang is not None:
            os.environ["BOB_LANG"] = bob_lang
        os.chdir(repo)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(list(args))
    finally:
        os.chdir(previous_cwd)
        os.environ.clear()
        os.environ.update(previous_env)
    return subprocess.CompletedProcess(
        ["bob", *args], code, stdout.getvalue(), stderr.getvalue()
    )


def _flat(text: str) -> str:
    return " ".join(text.split())


def _help_0(result: subprocess.CompletedProcess[str], repo: Path) -> None:
    assert result.returncode == 0, result.stderr
    assert not (repo / ".bob").exists(), repo


def _commands(repo: Path) -> tuple[str, ...]:
    result = run_bob(repo, "--help")
    assert result.returncode == 0, result.stderr
    match = _COMMAND_GROUP.search(result.stdout)
    assert match is not None, result.stdout
    names = tuple(part.strip() for part in match.group(1).split(",") if part.strip())
    assert names, result.stdout
    return names


def test_missing_command_exits_4(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path), tmp_path)


def test_unknown_command_exits_4(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path, "publish"), tmp_path)


def test_every_command_rejects_an_unknown_flag(tmp_path: Path) -> None:
    for command in _commands(tmp_path):
        _usage_4(run_bob(tmp_path, command, "--not-a-real-flag"), tmp_path)


def test_check_format_outside_choices(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path, "check", "--format", "xml"), tmp_path)


def test_numeric_flags_reject_text(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path, "mutate", "--max-workers", "nope"), tmp_path)
    _usage_4(run_bob(tmp_path, "crap", "--threshold", "nope"), tmp_path)


def test_waive_without_a_target(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path, "waive"), tmp_path)


def test_waive_reason_without_a_value(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path, "waive", "classify", "--reason"), tmp_path)


def test_doctor_rejects_config_and_base(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path, "doctor", "--config"), tmp_path)
    _usage_4(run_bob(tmp_path, "doctor", "--config", "bob.yaml"), tmp_path)
    _usage_4(run_bob(tmp_path, "doctor", "--base"), tmp_path)
    _usage_4(run_bob(tmp_path, "doctor", "--base", "main"), tmp_path)


def test_missing_lang_and_config_values(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path, "--lang"), tmp_path)
    _usage_4(run_bob(tmp_path, "--config"), tmp_path)
    _usage_4(run_bob(tmp_path, "check", "--lang"), tmp_path)
    _usage_4(run_bob(tmp_path, "check", "--config"), tmp_path)


def test_config_before_the_command_names_the_fix(tmp_path: Path) -> None:
    commands = tuple(
        command
        for command in _commands(tmp_path)
        if "--config" in _invoke(tmp_path, command, "--help").stdout
    )
    assert commands == ("check", "crap", "dry", "deps", "mutate")
    for command in commands:
        result = _invoke(tmp_path, "--config", "ci.yaml", command)
        _usage_4(result, tmp_path)
        assert result.stderr.splitlines()[-1] == (
            f"bob: error: --config goes after the command: bob {command} --config ci.yaml"
        )
    equals = _invoke(tmp_path, "--config=ci.yaml", "check")
    _usage_4(equals, tmp_path)
    assert equals.stderr.splitlines()[-1] == (
        "bob: error: --config goes after the command: bob check --config ci.yaml"
    )


def test_config_before_a_command_without_config(tmp_path: Path) -> None:
    doctor = _invoke(tmp_path, "--config", "ci.yaml", "doctor")
    _usage_4(doctor, tmp_path)
    assert doctor.stderr.splitlines()[-1] == "bob: error: doctor does not accept --config"
    assert "bob doctor --config" not in doctor.stderr

    waive = _invoke(tmp_path, "--config", "ci.yaml", "waive", "fn", "--reason", "r")
    _usage_4(waive, tmp_path)
    assert waive.stderr.splitlines()[-1] == "bob: error: waive does not accept --config"
    assert "bob doctor --config" not in waive.stderr
    assert "bob waive --config" not in waive.stderr


def test_config_hint_quotes_a_path_with_spaces(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "--config", "my ci.yaml", "crap")
    _usage_4(result, tmp_path)
    assert result.stderr.splitlines()[-1] == (
        "bob: error: --config goes after the command: bob crap --config 'my ci.yaml'"
    )


def test_top_level_help_hides_config(tmp_path: Path) -> None:
    top = _invoke(tmp_path, "--help")
    check = _invoke(tmp_path, "check", "--help")
    _help_0(top, tmp_path)
    _help_0(check, tmp_path)
    assert "--config" not in top.stdout
    assert "--config" in check.stdout


def test_the_full_parser_reports_a_missing_flag_value(tmp_path: Path) -> None:
    lang = _invoke(tmp_path, "--lang")
    _usage_4(lang, tmp_path)
    assert lang.stderr.splitlines()[-1] == "bob: error: argument --lang: expected one argument"
    assert "[--config CONFIG]" not in lang.stderr

    config = _invoke(tmp_path, "check", "--config")
    _usage_4(config, tmp_path)
    assert config.stderr.splitlines()[-1] == (
        "bob check: error: argument --config: expected one argument"
    )


def test_shared_flag_before_the_command(tmp_path: Path) -> None:
    for command in _commands(tmp_path):
        _usage_4(run_bob(tmp_path, "--base", "main", command), tmp_path)


def test_help_exits_0(tmp_path: Path) -> None:
    _help_0(run_bob(tmp_path, "--help"), tmp_path)
    _help_0(run_bob(tmp_path, "-h"), tmp_path)
    _help_0(run_bob(tmp_path, "--lang", "en", "--help"), tmp_path)
    for command in _commands(tmp_path):
        _help_0(run_bob(tmp_path, command, "--help"), tmp_path)


def test_main_returns_the_process_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["--help"]) == 0
    assert main(["check", "--help"]) == 0
    assert main(["check", "--format", "xml"]) == 4
    assert not (tmp_path / ".bob").exists()


def test_omitted_argv_reads_lang_from_the_process_arguments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BOB_LANG", raising=False)
    monkeypatch.setattr(sys, "argv", ["bob", "--lang", "pt-BR", "--help"])
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = main()

    assert code == 0
    assert "Gates de qualidade para agentes." in _flat(stdout.getvalue())
    assert not (tmp_path / ".bob").exists()


def test_invalid_lang_masks_a_later_usage_error(tmp_path: Path) -> None:
    result = run_bob(tmp_path, "--lang", "nope", "check", "--format", "xml")
    assert result.returncode == 4, result.stderr
    assert "invalid language" in result.stderr, result.stderr
    assert "xml" not in result.stderr, result.stderr
    assert "baseline" not in result.stderr.lower(), result.stderr
    assert not (tmp_path / ".bob").exists(), tmp_path


_COMMANDS = ("check", "crap", "dry", "deps", "mutate", "report", "waive", "doctor")

_TOP_HELP = (
    "usage: bob",
    "Quality gates for agents.",
    "{check,crap,dry,deps,mutate,report,waive,doctor}",
    "Run the requested gates and write .bob/",
    "Measure CRAP of the changed functions",
    "Report new clones in the diff, without blocking",
    "Check dependency cycles and rules",
    "Mutate the changed functions with mutmut",
    "Render report.json from a directory as Markdown",
    "Record a waiver with a one-line reason",
    "Check the pinned tools and the installed versions",
    "Output language: en or pt-BR (default: en)",
)

_SUB_HELP = {
    "check": (
        "usage: bob check",
        "--gates GATES",
        "Comma-separated list (default: crap,dry,deps)",
        "--format {md,json,both}",
    ),
    "crap": ("usage: bob crap", "--threshold THRESHOLD", "--coverage-file COVERAGE_FILE"),
    "dry": ("usage: bob dry",),
    "deps": ("usage: bob deps",),
    "mutate": (
        "usage: bob mutate",
        "--since-last-run]",
        "Reuse the cache; already the default behavior",
        "--max-workers MAX_WORKERS",
    ),
    "report": (
        "usage: bob report",
        "--in DIR",
        "--out FILE",
        "Render report.json from a directory as Markdown",
    ),
    "waive": (
        "usage: bob waive",
        "--reason REASON",
        "target",
        "mutant id or function name",
    ),
    "doctor": (
        "usage: bob doctor",
        "--install]",
        "Install the npm tools with npm ci in the package (or in a user cache)",
    ),
}


def _usage_argv() -> tuple[tuple[str, ...], ...]:
    scenarios = [
        (),
        ("publish",),
        ("check", "--format", "xml"),
        ("mutate", "--max-workers", "nope"),
        ("crap", "--threshold", "nope"),
        ("crap", "--threshold", "-inf"),
        ("waive",),
        ("waive", "classify", "--reason"),
        ("doctor", "--config"),
        ("doctor", "--config", "bob.yaml"),
        ("doctor", "--base"),
        ("doctor", "--base", "main"),
        ("--lang",),
        ("--config",),
        ("check", "--lang"),
        ("check", "--config"),
    ]
    for command in _COMMANDS:
        scenarios.append((command, "--not-a-real-flag"))
        scenarios.append(("--base", "main", command))
    return tuple(scenarios)


def test_in_process_usage_exits_4_without_a_report(tmp_path: Path) -> None:
    for args in _usage_argv():
        _usage_4(_invoke(tmp_path, *args), tmp_path)


def test_in_process_help_lists_every_command_and_flag(tmp_path: Path) -> None:
    top = _invoke(tmp_path, "--help")
    short = _invoke(tmp_path, "-h")
    _help_0(top, tmp_path)
    _help_0(short, tmp_path)
    shown = _flat(top.stdout)
    assert [text for text in _TOP_HELP if text not in shown] == []
    assert _flat(short.stdout) == shown

    for command, phrases in _SUB_HELP.items():
        result = _invoke(tmp_path, command, "--help")
        _help_0(result, tmp_path)
        flattened = _flat(result.stdout)
        assert [text for text in phrases if text not in flattened] == [], command


def _repo(dest: Path, language: str | None = None) -> Path:
    repo = init_python_repo(dest)
    if language is not None:
        config = repo / "bob.yaml"
        config.write_text(config.read_text() + f"language: {language}\n")
    return repo


def _heading(repo: Path) -> str:
    return (repo / ".bob" / "report.md").read_text().splitlines()[0]


def test_default_format_writes_both_reports(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")

    result = _invoke(repo, "check", "--gates", "nope", "--base", "main")

    assert result.returncode == 0, result.stderr
    assert _heading(repo) == "# bob report"
    assert (repo / ".bob" / "report.json").is_file()


def test_format_md_and_json_write_one_file_each(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")

    markdown = _invoke(
        repo, "check", "--gates", "nope", "--base", "main", "--format", "md", "--out", "md-out"
    )
    data = _invoke(
        repo,
        "check",
        "--gates",
        "nope",
        "--base",
        "main",
        "--format",
        "json",
        "--out",
        "json-out",
    )

    assert markdown.returncode == 0, markdown.stderr
    assert (repo / "md-out" / "report.md").is_file()
    assert not (repo / "md-out" / "report.json").exists()
    assert data.returncode == 0, data.stderr
    assert (repo / "json-out" / "report.json").is_file()
    assert not (repo / "json-out" / "report.md").exists()


_WAIVE_EN = "waiver without a reason: pass --reason with one line\n"
_WAIVE_PT = "waiver sem motivo: informe --reason com uma linha\n"


def _waive_language(repo: Path, *args: str, bob_lang: str | None = None) -> str:
    result = _invoke(repo, "waive", "classify", *args, bob_lang=bob_lang)
    assert result.returncode == 4, result.stderr
    return result.stderr


def test_language_follows_flag_then_env_then_yaml_then_config(tmp_path: Path) -> None:
    assert _waive_language(_repo(tmp_path / "flag"), "--lang", "pt-BR") == _WAIVE_PT
    assert _waive_language(_repo(tmp_path / "env"), bob_lang="pt-BR") == _WAIVE_PT
    assert _waive_language(_repo(tmp_path / "yaml", "pt-BR")) == _WAIVE_PT

    from_config = _repo(tmp_path / "config")
    (from_config / "custom.yaml").write_text("language: pt-BR\n")
    configured = _invoke(
        from_config, "check", "--config", "custom.yaml", "--gates", "nope", "--base", "main"
    )
    assert configured.returncode == 0, configured.stderr
    assert _heading(from_config) == "# Relatório bob"

    assert _waive_language(_repo(tmp_path / "override", "pt-BR"), "--lang", "en", bob_lang="pt-BR") == (
        _WAIVE_EN
    )


def test_missing_config_names_the_file_the_gate_opens(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    missing = repo / "missing.yaml"

    result = _invoke(repo, "check", "--gates", "nope", "--base", "main", "--config", "missing.yaml")

    assert result.returncode == 4, result.stderr
    report = (repo / ".bob" / "report.json").read_text()
    assert missing.as_posix() in report
    assert "config file not found" in report


def test_invalid_language_is_english_on_stderr_and_writes_nothing(tmp_path: Path) -> None:
    flagged = _invoke(tmp_path, "--lang", "nope", "check", "--format", "xml")
    repo = tmp_path / "yaml"
    repo.mkdir()
    (repo / "bob.yaml").write_text("language: fr\n")
    configured = _invoke(repo, "check", "--gates", "nope")

    assert flagged.returncode == 4
    assert flagged.stderr == "invalid language: nope (use en or pt-BR)\n"
    assert flagged.stdout == ""
    assert "xml" not in flagged.stderr
    assert configured.returncode == 4
    assert configured.stderr == "bob.yaml: language must be en or pt-BR\n"
    assert configured.stdout == ""
    assert not (repo / ".bob").exists()


def test_bad_config_and_waivers_exit_4_before_a_report(tmp_path: Path) -> None:
    config_repo = tmp_path / "config"
    config_repo.mkdir()
    custom = config_repo / "custom.yaml"
    custom.write_text("crap: 5\n")
    config = _invoke(config_repo, "check", "--config", "custom.yaml", "--gates", "nope")

    waiver_repo = tmp_path / "waiver"
    waiver_repo.mkdir()
    bob = waiver_repo / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text("- a\n")
    waiver = _invoke(waiver_repo, "doctor")

    assert config.returncode == 4
    assert config.stderr == f"{custom.as_posix()}: crap must be a mapping\n"
    assert config.stdout == ""
    assert not (config_repo / ".bob").exists()
    assert waiver.returncode == 4
    assert waiver.stderr == ".bob/waivers.yaml must be a mapping\n"
    assert waiver.stdout == ""
    assert not (bob / "report.md").exists()


def test_since_last_run_is_a_flag(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "mutate", "--since-last-run")

    assert result.returncode == 4, result.stderr
    assert "usage:" not in result.stderr, result.stderr
    assert "baseline" not in result.stderr.lower()


def test_doctor_speaks_the_selected_language(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "doctor", "--lang", "pt-BR")

    assert result.returncode in (0, 4), result.stderr
    assert "esperada" in result.stdout
    assert "expected" not in result.stdout


def test_doctor_install_invokes_npm_ci(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[object] = []

    def fake(lang: object) -> int:
        seen.append(lang)
        return 4

    monkeypatch.setattr("bob_quality.doctor.install_npm_dependencies", fake)

    result = _invoke(tmp_path, "doctor", "--install")

    assert seen == ["en"]
    assert result.returncode == 4
    assert "lizard" not in result.stdout


def test_waive_records_the_reason_and_translates_a_missing_one(tmp_path: Path) -> None:
    saved = _invoke(tmp_path, "waive", "classify", "--reason", "because")
    missing = _invoke(tmp_path, "waive", "other", "--lang", "pt-BR")

    assert saved.returncode == 0, saved.stderr
    text = (tmp_path / ".bob" / "waivers.yaml").read_text()
    assert "classify" in text
    assert "because" in text
    assert missing.returncode == 4
    assert missing.stderr == "waiver sem motivo: informe --reason com uma linha\n"


def test_stop_code_names_an_unexpected_result() -> None:
    with pytest.raises(AssertionError, match="^object$"):
        _stop_code(object())


def test_numeric_flags_reject_out_of_range_values(tmp_path: Path) -> None:
    _usage_4(run_bob(tmp_path, "crap", "--threshold=nan"), tmp_path)
    _usage_4(run_bob(tmp_path, "mutate", "--max-workers", "65"), tmp_path)


@pytest.mark.parametrize(
    "value",
    [
        "nan",
        "NaN",
        "-nan",
        "+nan",
        "inf",
        "Infinity",
        "-inf",
        "1e309",
        "-1e309",
        "-1",
        "-0.5",
        "0",
        "-0",
        "0.0",
        "+0",
        "-0.0",
        "1e-324",
        "nope",
        "",
    ],
)
def test_threshold_outside_the_crap_limit_exits_4(tmp_path: Path, value: str) -> None:
    result = _invoke(tmp_path, "crap", f"--threshold={value}")

    _usage_4(result, tmp_path)
    assert result.stdout == ""
    assert result.stderr.splitlines()[-1] == (
        "bob crap: error: argument --threshold: "
        f"invalid value: '{value}' (use a finite number greater than 0)"
    )


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "-1",
        "-0",
        "00",
        "+0",
        "65",
        "1000",
        "1_000",
        "100000000000000000000",
        "4.0",
        "1e3",
        "nope",
        "",
    ],
)
def test_max_workers_outside_1_to_64_exits_4(tmp_path: Path, value: str) -> None:
    result = _invoke(tmp_path, "mutate", f"--max-workers={value}")

    _usage_4(result, tmp_path)
    assert result.stdout == ""
    assert result.stderr.splitlines()[-1] == (
        "bob mutate: error: argument --max-workers: "
        f"invalid value: '{value}' (use an integer from 1 to 64)"
    )


def _dispatched(repo: Path, monkeypatch: pytest.MonkeyPatch, *args: str) -> dict[str, object]:
    seen: dict[str, object] = {}

    def fake(**kwargs: object) -> int:
        seen.update(kwargs)
        return 0

    monkeypatch.setattr("bob_quality.cli.run_check", fake)
    result = _invoke(repo, *args)
    assert result.returncode == 0, result.stderr
    return seen


@pytest.mark.parametrize(
    ("value", "limit"),
    [
        ("5e-324", float("5e-324")),
        ("0.5", 0.5),
        ("10", 10.0),
        ("1e308", float("1e308")),
    ],
)
def test_threshold_inside_the_crap_limit_reaches_the_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str, limit: float
) -> None:
    assert _dispatched(tmp_path, monkeypatch, "crap", "--threshold", value)["threshold"] == limit


@pytest.mark.parametrize(("value", "count"), [("1", 1), ("64", 64)])
def test_max_workers_inside_1_to_64_reaches_the_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str, count: int
) -> None:
    assert _dispatched(tmp_path, monkeypatch, "mutate", "--max-workers", value)["max_workers"] == count


def test_numeric_flag_errors_stay_english_under_pt_br(tmp_path: Path) -> None:
    threshold = _invoke(tmp_path, "crap", "--lang", "pt-BR", "--threshold=nan")
    workers = _invoke(tmp_path, "mutate", "--max-workers=65", bob_lang="pt-BR")

    _usage_4(threshold, tmp_path)
    _usage_4(workers, tmp_path)
    assert threshold.stdout == ""
    assert workers.stdout == ""
    assert threshold.stderr.splitlines()[-1] == (
        "bob crap: error: argument --threshold: "
        "invalid value: 'nan' (use a finite number greater than 0)"
    )
    assert workers.stderr.splitlines()[-1] == (
        "bob mutate: error: argument --max-workers: "
        "invalid value: '65' (use an integer from 1 to 64)"
    )


def test_cli_doc_states_the_worker_ceiling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doc = (Path(__file__).resolve().parents[1] / "docs" / "cli.md").read_text(encoding="utf-8")
    match = re.search(r"`--max-workers` aceita um inteiro de 1 a (\d+)", doc)
    assert match is not None, "docs/cli.md must state the --max-workers ceiling"
    ceiling = int(match.group(1))

    _usage_4(_invoke(tmp_path, "mutate", f"--max-workers={ceiling + 1}"), tmp_path)
    seen = _dispatched(tmp_path, monkeypatch, "mutate", "--max-workers", str(ceiling))
    assert seen["max_workers"] == ceiling
