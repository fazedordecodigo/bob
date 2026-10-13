from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from bob_quality.adapters.deptry import (
    DeptryCapture,
    DeptryRun,
    DeptryViolation,
    parse_deptry_json,
    run_deptry,
)
from bob_quality.adapters.knip import (
    KnipCapture,
    KnipDocument,
    KnipFile,
    KnipHit,
    parse_knip_json,
    run_knip,
)
from bob_quality.adapters.runner import ProcessExit, ProcessFault
from bob_quality.messages import msg, render
from bob_quality.npm_tools import npm_prefix
from bob_quality.tools import ToolError

_ONE = json.dumps(
    {"issues": [{"file": "src/app.ts", "unlisted": [{"name": "left-pad", "line": 4, "col": 1}]}]}
)
_ONE_FILES = (KnipFile("src/app.ts", {"unlisted": (KnipHit("left-pad", 4, 1),)}),)
_VALID = {
    "error": {"code": "DEP001"},
    "module": "requests",
    "location": {"file": "src/app.py", "line": 3},
}


def test_run_deptry_passes_the_version_argv_cwd_and_timeout(tmp_path: Path) -> None:
    calls: list[tuple[list[str], Path, int]] = []
    outputs: list[tuple[str, str]] = []

    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit:
        calls.append((list(args), cwd, timeout))
        if args[-1] == "--version":
            return ProcessExit(0, "deptry 0.25.1\n", "")
        output = Path(args[args.index("--json-output") + 1])
        outputs.append((output.name, output.parent.name))
        output.write_text("[]")
        return ProcessExit(0, "", "")

    capture = run_deptry(tmp_path, ("src",), 17, runner)

    assert calls[0] == ([sys.executable, "-m", "deptry", "--version"], tmp_path, 17)
    assert calls[1][1:] == (tmp_path, 17)
    assert outputs[0][0] == "deptry.json"
    assert outputs[0][1].startswith("bob-deptry-")
    assert capture == DeptryCapture(0, True, DeptryRun("0.25.1", ()), "")


def test_run_deptry_reads_unknown_when_the_banner_has_no_digits(tmp_path: Path) -> None:
    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit:
        if args[-1] == "--version":
            return ProcessExit(0, "deptry\n", "preview")
        Path(args[args.index("--json-output") + 1]).write_text("[]")
        return ProcessExit(1, "", "")

    capture = run_deptry(tmp_path, ("src",), 17, runner)

    assert capture == DeptryCapture(1, True, DeptryRun("unknown", ()), "")


def test_run_deptry_reads_the_version_from_stderr(tmp_path: Path) -> None:
    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit:
        if args[-1] == "--version":
            return ProcessExit(0, "", "deptry 0.25.1\n")
        Path(args[args.index("--json-output") + 1]).write_text("[]")
        return ProcessExit(0, "", "")

    capture = run_deptry(tmp_path, ("src",), 17, runner)

    assert capture.document is not None
    assert capture.document.version == "0.25.1"


def test_run_deptry_reads_unknown_when_the_version_probe_fails(tmp_path: Path) -> None:
    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit | ProcessFault:
        if args[-1] == "--version":
            return ProcessFault("down")
        Path(args[args.index("--json-output") + 1]).write_text("[]")
        return ProcessExit(0, "", "")

    capture = run_deptry(tmp_path, ("src",), 17, runner)

    assert capture == DeptryCapture(0, True, DeptryRun("unknown", ()), "")


def test_parse_deptry_json_keeps_a_bool_line_out_of_the_violation() -> None:
    raw = json.dumps(
        [
            {
                "error": {"code": "DEP001"},
                "module": "requests",
                "location": {"file": "src/app.py", "line": True},
            },
            {
                "error": {"code": "DEP003"},
                "module": "pkg_resources",
                "location": {"file": "src/app.py", "line": 8},
            },
        ]
    )

    assert parse_deptry_json(raw) == (
        DeptryViolation("DEP001", "requests", "src/app.py", None),
        DeptryViolation("DEP003", "pkg_resources", "src/app.py", 8),
    )


def test_parse_deptry_json_rejects_a_partial_violation() -> None:
    assert parse_deptry_json(json.dumps([_VALID])) == (
        DeptryViolation("DEP001", "requests", "src/app.py", 3),
    )
    assert parse_deptry_json(json.dumps([{**_VALID, "location": "src/app.py"}])) is None
    assert parse_deptry_json(json.dumps([{**_VALID, "error": "DEP001"}])) is None
    assert parse_deptry_json(json.dumps([{**_VALID, "error": {"code": 1}}])) is None
    assert parse_deptry_json(json.dumps([{**_VALID, "module": 1}])) is None


def test_parse_knip_json_rejects_issues_that_are_not_a_list() -> None:
    assert parse_knip_json('{"issues": {}}') is None
    assert parse_knip_json('{"issues": []}') == ()
    assert parse_knip_json(_ONE) == _ONE_FILES


def test_parse_knip_json_rejects_a_file_that_is_not_a_string() -> None:
    assert parse_knip_json('{"issues": [{"file": 3}]}') is None
    assert parse_knip_json(_ONE) == _ONE_FILES


def test_parse_knip_json_rejects_a_hit_whose_name_is_not_a_string() -> None:
    raw = json.dumps(
        {"issues": [{"file": "src/app.ts", "unlisted": [{"name": 1, "line": 4}]}]}
    )

    assert parse_knip_json(raw) is None
    assert parse_knip_json(_ONE) == _ONE_FILES


def test_parse_knip_json_keeps_a_bool_line_out_of_the_hit() -> None:
    raw = json.dumps(
        {
            "issues": [
                {
                    "file": "src/app.ts",
                    "unlisted": [
                        {"name": "left-pad", "line": True, "col": 2},
                        {"name": "pkg", "line": 4, "col": 8},
                    ],
                }
            ]
        }
    )

    assert parse_knip_json(raw) == (
        KnipFile(
            "src/app.ts",
            {
                "unlisted": (
                    KnipHit("left-pad", None, 2),
                    KnipHit("pkg", 4, 8),
                )
            },
        ),
    )


def test_parse_knip_json_keeps_the_hit_after_a_nested_list() -> None:
    raw = json.dumps(
        {
            "issues": [
                {
                    "file": "src/app.ts",
                    "unlisted": [
                        [{"name": "nested", "line": 1, "col": 1}],
                        {"name": "after", "line": 2, "col": 3},
                    ],
                }
            ]
        }
    )

    assert parse_knip_json(raw) == (
        KnipFile(
            "src/app.ts",
            {
                "unlisted": (
                    KnipHit("nested", 1, 1),
                    KnipHit("after", 2, 3),
                )
            },
        ),
    )


def test_parse_knip_json_rejects_a_nested_hit_without_a_name() -> None:
    raw = json.dumps({"issues": [{"file": "src/app.ts", "unlisted": [[{"name": 1}]]}]})

    assert parse_knip_json(raw) is None
    assert parse_knip_json(_ONE) == _ONE_FILES


def test_parse_knip_json_rejects_a_hit_value_that_is_not_a_list() -> None:
    raw = json.dumps({"issues": [{"file": "src/app.ts", "unlisted": {"name": "left-pad"}}]})

    assert parse_knip_json(raw) is None
    assert parse_knip_json(_ONE) == _ONE_FILES


def test_run_knip_passes_the_argv_cwd_and_timeout(tmp_path: Path) -> None:
    prefix = str(npm_prefix())
    calls: list[tuple[list[str], Path, int]] = []

    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit:
        calls.append((list(args), cwd, timeout))
        if args[-1] == "--version":
            return ProcessExit(0, "6.41.0\n", "")
        return ProcessExit(1, _ONE, "")

    capture = run_knip(tmp_path, 17, runner)

    assert calls == [
        (["npx", "--no-install", "--prefix", prefix, "knip", "--version"], tmp_path, 17),
        (["npx", "--no-install", "--prefix", prefix, "knip", "--reporter", "json"], tmp_path, 17),
    ]
    assert capture == KnipCapture(1, True, KnipDocument("6.41.0", _ONE_FILES), "")


def test_run_knip_reads_unknown_when_the_banner_has_no_digits(tmp_path: Path) -> None:
    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit:
        if args[-1] == "--version":
            return ProcessExit(0, "knip\n", "preview")
        return ProcessExit(1, _ONE, "")

    capture = run_knip(tmp_path, 17, runner)

    assert capture == KnipCapture(1, True, KnipDocument("unknown", _ONE_FILES), "")


def test_run_knip_reads_the_version_from_stderr(tmp_path: Path) -> None:
    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit:
        if args[-1] == "--version":
            return ProcessExit(0, "", "knip 6.41.0\n")
        return ProcessExit(0, _ONE, "")

    capture = run_knip(tmp_path, 17, runner)

    assert capture.document is not None
    assert capture.document.version == "6.41.0"


def test_run_knip_reads_unknown_when_the_version_probe_fails(tmp_path: Path) -> None:
    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit | ProcessFault:
        if args[-1] == "--version":
            return ProcessFault("down")
        return ProcessExit(0, _ONE, "")

    capture = run_knip(tmp_path, 17, runner)

    assert capture == KnipCapture(0, True, KnipDocument("unknown", _ONE_FILES), "")


def test_run_knip_reports_a_process_fault(tmp_path: Path) -> None:
    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit | ProcessFault:
        if args[-1] == "--version":
            return ProcessExit(0, "6.41.0\n", "")
        return ProcessFault("knip missing")

    capture = run_knip(tmp_path, 17, runner)

    assert capture == KnipCapture(None, False, None, "knip missing")


def test_run_knip_reports_unparseable_json(tmp_path: Path) -> None:
    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit:
        if args[-1] == "--version":
            return ProcessExit(0, "6.41.0\n", "")
        return ProcessExit(2, "not-json", "")

    capture = run_knip(tmp_path, 17, runner)

    assert capture == KnipCapture(2, False, None, msg("supply.knip_json"))
    assert render(capture.detail, "en") == "knip did not write parseable JSON"


def test_run_knip_returns_the_first_tool_error_arg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = msg("npm.manifest_missing")

    def missing() -> None:
        raise ToolError(message, "extra")

    monkeypatch.setattr("bob_quality.adapters.knip.npm_prefix", missing)

    capture = run_knip(tmp_path, 17, _unused_runner)

    assert capture == KnipCapture(None, False, None, message)
    assert render(capture.detail, "en") == (
        "plugin package.json (bob-quality-tools) not found; c8 and vitest are pinned in it"
    )


def test_run_knip_stringifies_a_tool_error_without_args(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing() -> None:
        raise ToolError()

    monkeypatch.setattr("bob_quality.adapters.knip.npm_prefix", missing)

    capture = run_knip(tmp_path, 17, _unused_runner)

    assert capture == KnipCapture(None, False, None, "")


def _unused_runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit:
    raise AssertionError((args, cwd, timeout))
