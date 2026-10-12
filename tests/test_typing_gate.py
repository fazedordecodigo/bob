"""Gate typing: veredito puro e `bob check --gates typing`."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from helpers import commit_on_branch, commit_on_main, init_python_repo, init_ts_repo
from jsonschema import Draft202012Validator

from bob_quality.models import GateResult, Report
from bob_quality.report import to_markdown
from bob_quality.typing_gate import (
    Absent,
    Blocked,
    Blocking,
    CheckerName,
    Clear,
    Configured,
    Diagnostic,
    DiagnosticCode,
    Escape,
    Measured,
    NoConfig,
    NothingMeasured,
    OffDiff,
    Unmeasured,
    Waived,
    typing_verdict,
    waiver_id,
)

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "src/bob_quality/schemas/report_v1.json").read_text()
)

_CHECKER = """\
#!/usr/bin/env python3
import pathlib
import sys

root = pathlib.Path.cwd()
name = pathlib.Path(sys.argv[0]).name
if "--version" in sys.argv:
    sys.stdout.write(name + " 1.8.0\\n")
    raise SystemExit(0)
(root / (name + "-argv.txt")).write_text("\\n".join(sys.argv))
stdout = root / (name + "-stdout.txt")
stderr = root / (name + "-stderr.txt")
code = root / (name + "-exit.txt")
if stdout.is_file():
    sys.stdout.write(stdout.read_text())
if stderr.is_file():
    sys.stderr.write(stderr.read_text())
raise SystemExit(int(code.read_text().strip()) if code.is_file() else 0)
"""


def _diagnostic(
    file: str, line: int, code: str, tool: CheckerName = "mypy"
) -> Diagnostic:
    return Diagnostic(file, line, DiagnosticCode(code), tool)


def test_verdict_without_a_configured_slot_is_not_run_even_with_an_escape() -> None:
    verdict = typing_verdict(
        (Absent("python"), Absent("typescript")),
        (Escape("src/app.py", 1, "Any"),),
        {"src/app.py": {1}},
        frozenset(),
    )

    assert verdict == NoConfig()
    assert verdict.status == "not_run"
    assert verdict.exit_code == 0


def test_verdict_ignores_escapes_when_every_checker_missed() -> None:
    miss = Unmeasured("mypy", "missing_executable")
    verdict = typing_verdict(
        (Configured("python", miss),),
        (Escape("src/app.py", 1, "Any"),),
        {"src/app.py": {1}},
        frozenset(),
    )

    assert verdict == NothingMeasured(miss)
    assert verdict.status == "not_run"
    assert verdict.exit_code == 4


def test_verdict_blocks_on_an_unwaived_diff_diagnostic() -> None:
    diagnostic = _diagnostic("src/app.py", 12, "assignment")
    verdict = typing_verdict(
        (Configured("python", Measured("mypy", (diagnostic,))),),
        (),
        {"src/app.py": {12}},
        frozenset(),
    )

    assert isinstance(verdict, Blocked)
    assert verdict.status == "failed"
    assert verdict.exit_code == 1
    assert verdict.head == Blocking(diagnostic)
    assert verdict.rest == ()


def test_verdict_waives_an_exact_id_and_keeps_a_sibling_miss() -> None:
    diagnostic = _diagnostic("src/app.py", 12, "assignment")
    miss = Unmeasured("pyright", "missing_executable")
    verdict = typing_verdict(
        (Configured("python", Measured("mypy", (diagnostic,)), (miss,)),),
        (),
        {"src/app.py": {12}},
        frozenset({waiver_id("src/app.py", 12, "assignment")}),
    )

    assert verdict == Clear((Waived(diagnostic),), (), (miss,))
    assert verdict.status == "passed"
    assert verdict.exit_code == 0


def test_verdict_stores_an_off_diff_diagnostic_even_when_the_id_is_waived() -> None:
    diagnostic = _diagnostic("src/app.py", 4, "assignment")
    verdict = typing_verdict(
        (Configured("python", Measured("mypy", (diagnostic,))),),
        (),
        {"src/app.py": {9}},
        frozenset({waiver_id("src/app.py", 4, "assignment")}),
    )

    assert verdict == Clear((), (OffDiff(diagnostic),), ())
    assert verdict.status == "passed"
    assert verdict.exit_code == 0


def test_verdict_orders_blocking_findings_by_file_line_code_and_tool() -> None:
    later = _diagnostic("src/b.py", 1, "assignment")
    earlier = _diagnostic("src/a.py", 3, "attr-defined", "pyright")
    verdict = typing_verdict(
        (
            Configured(
                "python",
                Measured("pyright", (later, earlier)),
            ),
        ),
        (),
        {"src/a.py": {3}, "src/b.py": {1}},
        frozenset(),
    )

    assert isinstance(verdict, Blocked)
    assert verdict.blocking() == (Blocking(earlier), Blocking(later))
    assert verdict.exit_code == 1


def test_types_section_follows_uncovered_mutants_and_precedes_reproduce() -> None:
    report = Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-12T00:00:00+00:00",
        tool_versions={"mypy": "mypy 1.8.0"},
        gates=[GateResult("typing", "passed", None)],
        focus=[],
        top_crap=[],
        reproduce="bob check --gates typing",
        exit_code=0,
        mutation={"no_coverage": {"total": 0, "functions": []}},
        typing={
            "absent": [],
            "checkers": [{"language": "python", "tool": "mypy", "outcome": "measured"}],
            "findings": [
                {
                    "kind": "diagnostic",
                    "disposition": "off_diff",
                    "file": "src/app.py",
                    "line": 4,
                    "code": "assignment",
                    "tool": "mypy",
                    "waiver_id": "typing:src/app.py:4:assignment",
                }
            ],
        },
    )

    english = to_markdown(report, "en")
    portuguese = to_markdown(report, "pt-BR")

    assert (
        english.index("## Mutants without tests")
        < english.index("## Types")
        < english.index("## How to reproduce")
    )
    assert "| `src/app.py` | 4 | `assignment` | off_diff | `typing:src/app.py:4:assignment` |" in english
    assert (
        portuguese.index("## Mutantes sem teste")
        < portuguese.index("## Tipos")
        < portuguese.index("## Como reproduzir")
    )
    assert "off_diff" in portuguese
    assert "No type findings." not in english


def _path(home: Path, *bindirs: Path) -> str:
    isolated = home / "path-only"
    isolated.mkdir(exist_ok=True)
    git = shutil.which("git")
    assert git is not None
    _link(isolated / "git", Path(git))
    _link(isolated / "python3", Path(sys.executable))
    return os.pathsep.join([*(str(directory) for directory in bindirs), str(isolated)])


def _link(link: Path, target: Path) -> None:
    if link.exists() or link.is_symlink():
        return
    link.symlink_to(target)


def _install(repo: Path, *names: str) -> str:
    bindir = repo / "fake-bin"
    bindir.mkdir()
    for name in names:
        path = bindir / name
        path.write_text(_CHECKER)
        path.chmod(0o755)
    return _path(repo, bindir)


def _checker_output(repo: Path, name: str, stdout: str, exit_code: int, stderr: str = "") -> None:
    (repo / f"{name}-stdout.txt").write_text(stdout)
    (repo / f"{name}-exit.txt").write_text(f"{exit_code}\n")
    if stderr:
        (repo / f"{name}-stderr.txt").write_text(stderr)


def _bob(repo: Path, *args: str, path: str, lang: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key != "BOB_LANG"}
    env["PATH"] = path
    if lang is not None:
        env["BOB_LANG"] = lang
    return subprocess.run(
        [sys.executable, "-m", "bob_quality", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def _json(repo: Path) -> dict[str, object]:
    return json.loads((repo / ".bob" / "report.json").read_text())


def test_no_checker_config_is_not_run_and_exit_0(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=_path(repo))

    assert result.returncode == 0
    assert result.stderr == ""
    payload = _json(repo)
    Draft202012Validator(SCHEMA).validate(payload)
    assert payload["schema_version"] == 1
    assert payload["exit_code"] == 0
    assert payload["gates"] == [
        {"name": "typing", "status": "not_run", "reason": "no checker config"}
    ]
    assert payload["typing"] == {"absent": ["python"], "checkers": [], "findings": []}
    assert "mypy" not in payload["tool_versions"]
    assert "## Types\n\n- no checker config\n" in (repo / ".bob" / "report.md").read_text()


def test_no_checker_config_heading_is_tipos_in_portuguese(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")

    result = _bob(
        repo,
        "check",
        "--lang",
        "pt-BR",
        "--gates",
        "typing",
        "--base",
        "main",
        path=_path(repo),
        lang="pt-BR",
    )

    assert result.returncode == 0
    payload = _json(repo)
    assert payload["gates"] == [
        {"name": "typing", "status": "not_run", "reason": "no checker config"}
    ]
    markdown = (repo / ".bob" / "report.md").read_text()
    assert "## Tipos\n\n- sem configuração de checker\n" in markdown
    assert "## Types" not in markdown


def test_mypy_error_on_a_diff_line_exits_1(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "mypy.ini").write_text("[mypy]\n")
    path = _install(repo, "mypy")
    commit_on_branch(repo, "bad", "src/app/bad.py", 'value: int = "no"\n', "add bad")
    _checker_output(repo, "mypy", "src/app/bad.py:1: error: bad [assignment]\n", 1)

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 1
    payload = _json(repo)
    Draft202012Validator(SCHEMA).validate(payload)
    assert payload["exit_code"] == 1
    assert payload["gates"] == [
        {
            "name": "typing",
            "status": "failed",
            "reason": "typing:src/app/bad.py:1:assignment",
        }
    ]
    assert payload["tool_versions"] == {"mypy": "mypy 1.8.0"}
    argv = (repo / "mypy-argv.txt").read_text().splitlines()
    cache = argv[argv.index("--cache-dir") + 1]
    assert argv[1:] == [
        "--show-error-codes",
        "--no-error-summary",
        "--no-pretty",
        "--no-color-output",
        "--hide-error-context",
        "--no-incremental",
        "--cache-dir",
        cache,
        "src",
    ]
    assert Path(cache).is_absolute()
    assert not Path(cache).is_relative_to(repo.resolve())
    assert payload["typing"] == {
        "absent": [],
        "checkers": [{"language": "python", "tool": "mypy", "outcome": "measured"}],
        "findings": [
            {
                "kind": "diagnostic",
                "disposition": "blocking",
                "file": "src/app/bad.py",
                "line": 1,
                "code": "assignment",
                "tool": "mypy",
                "waiver_id": "typing:src/app/bad.py:1:assignment",
            }
        ],
    }


def test_the_same_mypy_id_waived_exits_0(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "mypy.ini").write_text("[mypy]\n")
    path = _install(repo, "mypy")
    commit_on_branch(repo, "bad", "src/app/bad.py", 'value: int = "no"\n', "add bad")
    _checker_output(repo, "mypy", "src/app/bad.py:1: error: bad [assignment]\n", 1)
    waiver = repo / ".bob"
    waiver.mkdir()
    (waiver / "waivers.yaml").write_text(
        "waivers:\n"
        "  - id: \"typing:src/app/bad.py:1:assignment\"\n"
        "    reason: kept\n"
        "    author: ada\n"
        "    date: \"2026-10-12\"\n"
    )

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 0
    payload = _json(repo)
    assert payload["exit_code"] == 0
    assert payload["gates"] == [{"name": "typing", "status": "passed", "reason": None}]
    assert payload["typing"] == {
        "absent": [],
        "checkers": [{"language": "python", "tool": "mypy", "outcome": "measured"}],
        "findings": [
            {
                "kind": "diagnostic",
                "disposition": "waived",
                "file": "src/app/bad.py",
                "line": 1,
                "code": "assignment",
                "tool": "mypy",
                "waiver_id": "typing:src/app/bad.py:1:assignment",
            }
        ],
    }


def test_mypy_config_without_the_executable_exits_4(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "mypy.ini").write_text("[mypy]\n")

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=_path(repo))

    assert result.returncode == 4
    payload = _json(repo)
    Draft202012Validator(SCHEMA).validate(payload)
    assert payload["exit_code"] == 4
    assert payload["gates"] == [
        {"name": "typing", "status": "not_run", "reason": "mypy missing from PATH"}
    ]
    assert payload["tool_versions"] == {}
    assert payload["typing"] == {
        "absent": [],
        "checkers": [
            {
                "language": "python",
                "tool": "mypy",
                "outcome": "unmeasured",
                "reason": "missing_executable",
            }
        ],
        "findings": [],
    }


def test_off_diff_diagnostic_is_stored_and_exits_0(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "mypy.ini").write_text("[mypy]\n")
    path = _install(repo, "mypy")
    commit_on_main(repo, "src/app/old.py", "kept = 1\nchanged = 2\n", "base file")
    commit_on_branch(repo, "edit", "src/app/old.py", "kept = 1\nchanged = 3\n", "edit line")
    _checker_output(repo, "mypy", "src/app/old.py:1: error: bad [assignment]\n", 1)

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 0
    payload = _json(repo)
    assert payload["exit_code"] == 0
    assert payload["gates"] == [{"name": "typing", "status": "passed", "reason": None}]
    assert payload["typing"] == {
        "absent": [],
        "checkers": [{"language": "python", "tool": "mypy", "outcome": "measured"}],
        "findings": [
            {
                "kind": "diagnostic",
                "disposition": "off_diff",
                "file": "src/app/old.py",
                "line": 1,
                "code": "assignment",
                "tool": "mypy",
                "waiver_id": "typing:src/app/old.py:1:assignment",
            }
        ],
    }


def test_new_any_blocks_when_setup_cfg_configures_mypy(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "setup.cfg").write_text("[mypy]\nstrict = True\n")
    path = _install(repo, "mypy")
    commit_on_branch(repo, "any", "src/app/loose.py", "from typing import Any\n", "add Any")
    _checker_output(repo, "mypy", "", 0)

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 1
    payload = _json(repo)
    assert payload["exit_code"] == 1
    assert payload["gates"] == [
        {"name": "typing", "status": "failed", "reason": "typing:src/app/loose.py:1:Any"}
    ]
    assert payload["typing"] == {
        "absent": [],
        "checkers": [{"language": "python", "tool": "mypy", "outcome": "measured"}],
        "findings": [
            {
                "kind": "escape",
                "disposition": "blocking",
                "file": "src/app/loose.py",
                "line": 1,
                "code": "Any",
                "waiver_id": "typing:src/app/loose.py:1:Any",
            }
        ],
    }


def test_new_type_ignore_stores_the_normalized_code(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "pyproject.toml").write_text("[tool.mypy]\npretty = false\n")
    path = _install(repo, "mypy")
    source = 'value: int = "no"  # type:ignore[arg-type]\n'
    commit_on_branch(repo, "ignore", "src/app/ignored.py", source, "add ignore")
    _checker_output(repo, "mypy", "", 0)

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 1
    payload = _json(repo)
    assert payload["typing"] == {
        "absent": [],
        "checkers": [{"language": "python", "tool": "mypy", "outcome": "measured"}],
        "findings": [
            {
                "kind": "escape",
                "disposition": "blocking",
                "file": "src/app/ignored.py",
                "line": 1,
                "code": "type: ignore",
                "waiver_id": "typing:src/app/ignored.py:1:type: ignore",
            }
        ],
    }


def test_ts_ignore_inside_a_string_does_not_block(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    (repo / "tsconfig.json").write_text("{}\n")
    path = _install(repo, "tsc")
    source = (
        'const label = "@ts-ignore @ts-expect-error";\n'
        'const hidden = "as any";\n'
        "// @ts-ignore\n"
        "export const value = 1 as  any;\n"
        "// @ts-expect-error\n"
    )
    commit_on_branch(repo, "escape", "src/escaped.ts", source, "add escapes")
    _checker_output(repo, "tsc", "", 0)

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 1
    payload = _json(repo)
    Draft202012Validator(SCHEMA).validate(payload)
    assert payload["exit_code"] == 1
    assert payload["typing"] == {
        "absent": [],
        "checkers": [{"language": "typescript", "tool": "tsc", "outcome": "measured"}],
        "findings": [
            {
                "kind": "escape",
                "disposition": "blocking",
                "file": "src/escaped.ts",
                "line": 3,
                "code": "@ts-ignore",
                "waiver_id": "typing:src/escaped.ts:3:@ts-ignore",
            },
            {
                "kind": "escape",
                "disposition": "blocking",
                "file": "src/escaped.ts",
                "line": 4,
                "code": "as any",
                "waiver_id": "typing:src/escaped.ts:4:as any",
            },
            {
                "kind": "escape",
                "disposition": "blocking",
                "file": "src/escaped.ts",
                "line": 5,
                "code": "@ts-expect-error",
                "waiver_id": "typing:src/escaped.ts:5:@ts-expect-error",
            },
        ],
    }


def test_missing_root_tsconfig_leaves_typescript_not_run(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=_path(repo))

    assert result.returncode == 0
    payload = _json(repo)
    assert payload["exit_code"] == 0
    assert payload["gates"] == [
        {"name": "typing", "status": "not_run", "reason": "no checker config"}
    ]
    assert payload["typing"] == {"absent": ["typescript"], "checkers": [], "findings": []}
    assert payload["tool_versions"] == {}


def test_a_measured_checker_keeps_its_exit_when_a_sibling_is_missing(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "mypy.ini").write_text("[mypy]\n")
    (repo / "pyrightconfig.json").write_text("{}\n")
    path = _install(repo, "mypy")
    commit_on_branch(repo, "bad", "src/app/bad.py", 'value: int = "no"\n', "add bad")
    _checker_output(repo, "mypy", "src/app/bad.py:1: error: bad [assignment]\n", 1)

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 1
    payload = _json(repo)
    assert payload["exit_code"] == 1
    assert payload["gates"] == [
        {
            "name": "typing",
            "status": "failed",
            "reason": "typing:src/app/bad.py:1:assignment",
        }
    ]
    assert payload["tool_versions"] == {"mypy": "mypy 1.8.0"}
    assert "pyright" not in payload["tool_versions"]
    assert payload["typing"] == {
        "absent": [],
        "checkers": [
            {"language": "python", "tool": "mypy", "outcome": "measured"},
            {
                "language": "python",
                "tool": "pyright",
                "outcome": "unmeasured",
                "reason": "missing_executable",
            },
        ],
        "findings": [
            {
                "kind": "diagnostic",
                "disposition": "blocking",
                "file": "src/app/bad.py",
                "line": 1,
                "code": "assignment",
                "tool": "mypy",
                "waiver_id": "typing:src/app/bad.py:1:assignment",
            }
        ],
    }


def test_mypy_exit_2_is_outside_measurement(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / ".mypy.ini").write_text("[mypy]\n")
    path = _install(repo, "mypy")
    _checker_output(repo, "mypy", "src/app/bad.py:1: error: bad [assignment]\n", 2)

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 4
    payload = _json(repo)
    assert payload["exit_code"] == 4
    assert payload["gates"] == [
        {"name": "typing", "status": "not_run", "reason": "mypy exited 2"}
    ]
    assert payload["typing"] == {
        "absent": [],
        "checkers": [
            {
                "language": "python",
                "tool": "mypy",
                "outcome": "unmeasured",
                "reason": "exit_outside_measurement",
            }
        ],
        "findings": [],
    }
    assert payload["tool_versions"] == {"mypy": "mypy 1.8.0"}


def test_clean_mypy_exit_with_an_error_line_is_unparseable(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "mypy.ini").write_text("[mypy]\n")
    path = _install(repo, "mypy")
    _checker_output(repo, "mypy", "other/a.py:1: error: bad [assignment]\n", 0)

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 4
    payload = _json(repo)
    assert payload["gates"] == [
        {"name": "typing", "status": "not_run", "reason": "mypy output was unparseable"}
    ]
    assert payload["typing"] == {
        "absent": [],
        "checkers": [
            {
                "language": "python",
                "tool": "mypy",
                "outcome": "unmeasured",
                "reason": "unparseable_output",
            }
        ],
        "findings": [],
    }


def test_out_of_scope_error_on_a_failing_mypy_stays_a_measurement(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "mypy.ini").write_text("[mypy]\n")
    path = _install(repo, "mypy")
    _checker_output(repo, "mypy", "other/a.py:1: error: bad [assignment]\n", 1)

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 0
    payload = _json(repo)
    assert payload["exit_code"] == 0
    assert payload["gates"] == [{"name": "typing", "status": "passed", "reason": None}]
    assert payload["typing"] == {
        "absent": [],
        "checkers": [{"language": "python", "tool": "mypy", "outcome": "measured"}],
        "findings": [],
    }


def test_unreadable_setup_cfg_does_not_spawn_mypy(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "setup.cfg").write_text("[mypy\n")
    path = _install(repo, "mypy")
    _checker_output(repo, "mypy", "src/app/bad.py:1: error: bad [assignment]\n", 1)

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 4
    payload = _json(repo)
    assert payload["exit_code"] == 4
    assert payload["gates"] == [
        {"name": "typing", "status": "not_run", "reason": "mypy output was unparseable"}
    ]
    assert payload["tool_versions"] == {}
    assert payload["typing"] == {
        "absent": [],
        "checkers": [
            {
                "language": "python",
                "tool": "mypy",
                "outcome": "unmeasured",
                "reason": "unparseable_output",
            }
        ],
        "findings": [],
    }


def test_tsc_diagnostic_on_a_diff_line_exits_1(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    (repo / "tsconfig.json").write_text("{}\n")
    path = _install(repo, "tsc")
    commit_on_branch(repo, "bad", "src/bad.ts", "export const value: number = 1;\n", "add")
    _checker_output(
        repo,
        "tsc",
        "src/bad.ts(1,14): error TS2322: Type 'number' is not assignable.\n",
        2,
    )

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 1
    payload = _json(repo)
    assert (repo / "tsc-argv.txt").read_text().splitlines()[1:] == [
        "--noEmit",
        "--pretty",
        "false",
        "--incremental",
        "false",
        "-p",
        "tsconfig.json",
    ]
    assert payload["exit_code"] == 1
    assert payload["gates"] == [
        {"name": "typing", "status": "failed", "reason": "typing:src/bad.ts:1:TS2322"}
    ]
    assert payload["typing"] == {
        "absent": [],
        "checkers": [{"language": "typescript", "tool": "tsc", "outcome": "measured"}],
        "findings": [
            {
                "kind": "diagnostic",
                "disposition": "blocking",
                "file": "src/bad.ts",
                "line": 1,
                "code": "TS2322",
                "tool": "tsc",
                "waiver_id": "typing:src/bad.ts:1:TS2322",
            }
        ],
    }


def test_a_clean_measurement_keeps_exit_0_when_a_sibling_is_missing(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "mypy.ini").write_text("[mypy]\n")
    (repo / "pyrightconfig.json").write_text("{}\n")
    path = _install(repo, "mypy")
    _checker_output(repo, "mypy", "", 0)

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 0
    payload = _json(repo)
    assert payload["exit_code"] == 0
    assert payload["gates"] == [{"name": "typing", "status": "passed", "reason": None}]
    assert payload["tool_versions"] == {"mypy": "mypy 1.8.0"}
    assert payload["typing"] == {
        "absent": [],
        "checkers": [
            {"language": "python", "tool": "mypy", "outcome": "measured"},
            {
                "language": "python",
                "tool": "pyright",
                "outcome": "unmeasured",
                "reason": "missing_executable",
            },
        ],
        "findings": [],
    }
    assert "No type findings." in (repo / ".bob" / "report.md").read_text()


def test_mypy_diagnostic_on_stderr_still_blocks(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "mypy.ini").write_text("[mypy]\n")
    path = _install(repo, "mypy")
    commit_on_branch(repo, "bad", "src/app/bad.py", 'value: int = "no"\n', "add bad")
    _checker_output(repo, "mypy", "", 1, stderr="src/app/bad.py:1: error: bad [assignment]\n")

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 1
    payload = _json(repo)
    assert payload["gates"] == [
        {
            "name": "typing",
            "status": "failed",
            "reason": "typing:src/app/bad.py:1:assignment",
        }
    ]
    assert payload["typing"]["findings"] == [
        {
            "kind": "diagnostic",
            "disposition": "blocking",
            "file": "src/app/bad.py",
            "line": 1,
            "code": "assignment",
            "tool": "mypy",
            "waiver_id": "typing:src/app/bad.py:1:assignment",
        }
    ]


def test_sourceless_tsc_line_does_not_drop_a_source_diagnostic(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    (repo / "tsconfig.json").write_text("{}\n")
    path = _install(repo, "tsc")
    commit_on_branch(repo, "bad", "src/bad.ts", "export const value: number = 1;\n", "add")
    _checker_output(
        repo,
        "tsc",
        "error TS5058: The specified path does not exist.\n"
        "src/bad.ts(1,14): error TS2322: no\n",
        1,
    )

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 1
    payload = _json(repo)
    assert payload["exit_code"] == 1
    assert payload["typing"] == {
        "absent": [],
        "checkers": [{"language": "typescript", "tool": "tsc", "outcome": "measured"}],
        "findings": [
            {
                "kind": "diagnostic",
                "disposition": "blocking",
                "file": "src/bad.ts",
                "line": 1,
                "code": "TS2322",
                "tool": "tsc",
                "waiver_id": "typing:src/bad.ts:1:TS2322",
            }
        ],
    }


def test_pyright_diagnostic_on_a_diff_line_exits_1(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "pyrightconfig.json").write_text("{}\n")
    path = _install(repo, "pyright")
    commit_on_branch(repo, "bad", "src/app/bad.py", 'value: int = "no"\n', "add bad")
    _checker_output(
        repo,
        "pyright",
        "src/app/bad.py:1:1 - error: bad (reportGeneralTypeIssues)\n",
        1,
    )

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 1
    payload = _json(repo)
    assert (repo / "pyright-argv.txt").read_text().splitlines()[1:] == ["src"]
    assert payload["typing"] == {
        "absent": [],
        "checkers": [{"language": "python", "tool": "pyright", "outcome": "measured"}],
        "findings": [
            {
                "kind": "diagnostic",
                "disposition": "blocking",
                "file": "src/app/bad.py",
                "line": 1,
                "code": "reportGeneralTypeIssues",
                "tool": "pyright",
                "waiver_id": "typing:src/app/bad.py:1:reportGeneralTypeIssues",
            }
        ],
    }


def test_include_is_a_path_prefix_and_exclude_matches_any_segment(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    (repo / "mypy.ini").write_text("[mypy]\n")
    path = _install(repo, "mypy")
    commit_on_branch(repo, "hidden", "src/tests/hidden.py", "x = 1\n", "add hidden")
    _checker_output(
        repo,
        "mypy",
        "src/tests/hidden.py:1: error: bad [assignment]\n"
        "src2/a.py:1: error: bad [assignment]\n",
        1,
    )

    result = _bob(repo, "check", "--gates", "typing", "--base", "main", path=path)

    assert result.returncode == 0
    payload = _json(repo)
    assert payload["exit_code"] == 0
    assert payload["gates"] == [{"name": "typing", "status": "passed", "reason": None}]
    assert payload["typing"] == {
        "absent": [],
        "checkers": [{"language": "python", "tool": "mypy", "outcome": "measured"}],
        "findings": [],
    }
