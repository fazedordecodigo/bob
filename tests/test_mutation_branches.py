from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from bob_quality.adapters.lizard import LizardParseError
from bob_quality.adapters.stryker import StrykerParseError
from bob_quality.config import Config
from bob_quality.messages import msg
from bob_quality.models import Clone, CyclomaticFunction, DepViolation, FunctionMetric, GateResult
from bob_quality.mutate import STRYKER_MUTANTS_NAME, MutationOutcome
from bob_quality.stryker_gate import _from_report
from bob_quality.tools import ToolError
from bob_quality.waivers import Waiver, WaiverError
from helpers import in_both

_WAIVER = {
    "id": "src/safe.ts:9",
    "reason": "kept so the waiver list is observable",
    "author": "test",
    "date": "2026-10-12",
}
_VERSIONS = {"stryker": "10.0.0", "stryker-vitest-runner": "10.0.0"}


def _write_waiver(repo: Path) -> None:
    bob = repo / ".bob"
    bob.mkdir(parents=True)
    (bob / "waivers.yaml").write_text(
        "waivers:\n"
        "- id: src/safe.ts:9\n"
        "  reason: kept so the waiver list is observable\n"
        "  author: test\n"
        "  date: '2026-10-12'\n"
    )


def _outcome(
    code: int,
    *,
    status: str,
    reason: object = None,
    versions: dict[str, str] | None = None,
    waivers: list[dict[str, object]] | None = None,
    survivors: list[dict[str, object]] | None = None,
    summary: dict[str, object] | None = None,
) -> MutationOutcome:
    return MutationOutcome(
        result=GateResult("mutate", status, reason),
        exit_code=code,
        versions={"mutmut": "3.8.0"} if versions is None else versions,
        waivers=[] if waivers is None else waivers,
        survivors=[] if survivors is None else survivors,
        summary={
            "remutated": [],
            "reused": [],
            "no_coverage": {"total": 0, "functions": []},
        }
        if summary is None
        else summary,
    )


def test_python_only_forwards_workers_and_does_not_invent_a_skip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from bob_quality import mutate_gate

    seen: dict[str, object] = {}
    outcome = _outcome(0, status="passed")

    def fake(*_args: object, **kwargs: object) -> MutationOutcome:
        seen.update(kwargs)
        return outcome

    original_merge = mutate_gate._merge

    def spy(python: MutationOutcome | None, typescript: MutationOutcome | None, skip: object):
        seen["typescript"] = typescript
        seen["skip"] = skip
        return original_merge(python, typescript, skip)

    monkeypatch.setattr(mutate_gate, "run_mutation_gate", fake)
    monkeypatch.setattr(mutate_gate, "_merge", spy)

    got = mutate_gate.run_mutate_gate(
        tmp_path,
        Config(),
        {},
        tmp_path,
        max_workers=3,
        baseline=2,
    )

    assert got is outcome
    assert seen["max_workers"] == 3
    assert seen["baseline"] == 2
    assert seen["typescript"] is None
    assert seen["skip"] is None


def test_merge_keeps_the_worse_exit_and_both_sides() -> None:
    from bob_quality.mutate_gate import _merge

    python = _outcome(
        0,
        status="passed",
        versions={"mutmut": "3.8.0"},
        waivers=[{"id": "py"}],
        survivors=[
            {"function": "alpha", "file": "a.py", "line": 1, "waiver": "because"},
            {"function": "beta", "file": "b.py", "line": 2, "waiver": None},
        ],
        summary={
            "remutated": ["a.py::alpha"],
            "reused": ["a.py::old"],
            "no_coverage": {
                "total": 1,
                "functions": [{"file": "a.py", "function": "alpha", "count": 1}],
            },
        },
    )
    typescript = _outcome(
        3,
        status="failed",
        versions={"stryker": "10.0.0"},
        survivors=[
            {"function": "gamma", "file": "c.ts", "line": 3, "waiver": None},
        ],
        summary={
            "remutated": ["c.ts::gamma"],
            "reused": ["c.ts::old"],
            "no_coverage": {
                "total": 3,
                "functions": [
                    {"file": "a.py", "function": "alpha", "count": 2},
                    {"file": "c.ts", "function": "gamma", "count": 1},
                ],
            },
        },
    )
    skip = msg("npm.deps_missing", hint="npm ci")

    merged = _merge(python, typescript, skip)
    bare = _merge(python, typescript, None)

    assert merged.exit_code == 3
    assert merged.result.name == "mutate"
    assert merged.result.status == "failed"
    assert bare.result.name == "mutate"
    assert bare.result.status == "failed"
    assert in_both(bare.result.reason) == (
        "survivor without waiver: beta@b.py:2, gamma@c.ts:3",
        "sobrevivente sem waiver: beta@b.py:2, gamma@c.ts:3",
    )
    assert merged.versions == {"mutmut": "3.8.0", "stryker": "10.0.0"}
    assert merged.waivers == [{"id": "py"}]
    assert merged.survivors == [*python.survivors, *typescript.survivors]
    assert merged.summary == {
        "remutated": ["a.py::alpha", "c.ts::gamma"],
        "reused": ["a.py::old", "c.ts::old"],
        "no_coverage": {
            "total": 4,
            "functions": [
                {"file": "a.py", "function": "alpha", "count": 3},
                {"file": "c.ts", "function": "gamma", "count": 1},
            ],
        },
    }
    assert in_both(merged.result.reason) == (
        "survivor without waiver: beta@b.py:2, gamma@c.ts:3; "
        "TypeScript skipped: plugin npm dependencies missing: npm ci",
        "sobrevivente sem waiver: beta@b.py:2, gamma@c.ts:3; "
        "TypeScript pulado: dependências npm do plugin ausentes: npm ci",
    )


def test_merge_reports_the_side_that_hit_the_worse_hard_exit() -> None:
    from bob_quality.mutate_gate import _merge

    python = _outcome(4, status="not_run", reason=msg("stryker.no_report"))
    typescript = _outcome(2, status="not_run", reason=msg("probe.baseline_failed"))

    merged = _merge(python, typescript, None)

    assert merged is not python
    assert merged.exit_code == 4
    assert merged.result.name == "mutate"
    assert merged.result.status == "not_run"
    assert in_both(merged.result.reason) == (
        "Stryker did not write the report",
        "o Stryker não gravou o relatório",
    )


def test_merge_reports_typescript_when_only_that_side_hit_the_hard_exit() -> None:
    from bob_quality.mutate_gate import _merge

    python = _outcome(2, status="failed", reason=msg("probe.baseline_failed"))
    typescript = _outcome(4, status="not_run", reason=msg("stryker.no_report"))

    merged = _merge(python, typescript, None)

    assert merged.exit_code == 4
    assert merged.result.name == "mutate"
    assert merged.result.status == "not_run"
    assert in_both(merged.result.reason) == (
        "Stryker did not write the report",
        "o Stryker não gravou o relatório",
    )


def test_a_missing_language_is_returned_unchanged_until_a_skip_is_noted() -> None:
    from bob_quality.mutate_gate import _merge

    python = _outcome(0, status="passed", waivers=[{"id": "py"}])
    typescript = _outcome(3, status="failed", versions={"stryker": "10.0.0"})

    assert _merge(python, None, None) is python
    assert _merge(None, typescript, None) is typescript

    noted = _merge(python, None, msg("npm.deps_missing", hint="npm ci"))
    assert noted.exit_code == 0
    assert noted.waivers == [{"id": "py"}]
    assert noted.result.name == "mutate"
    assert noted.result.status == "warn"
    assert in_both(noted.result.reason) == (
        "TypeScript skipped: plugin npm dependencies missing: npm ci",
        "TypeScript pulado: dependências npm do plugin ausentes: npm ci",
    )


def test_merge_joins_both_hard_failures_and_warns_for_uncovered_mutants() -> None:
    from bob_quality.mutate_gate import _merge, _merge_no_coverage

    python = _outcome(2, status="not_run", reason=msg("probe.baseline_failed"))
    typescript = _outcome(2, status="failed", reason=msg("stryker.no_report"))
    joined = _merge(python, typescript, None)

    assert joined.exit_code == 2
    assert joined.result.name == "mutate"
    assert joined.result.status == "not_run"
    assert in_both(joined.result.reason) == (
        "baseline tests failed before measuring; Stryker did not write the report",
        "testes da baseline falharam antes de medir; o Stryker não gravou o relatório",
    )

    quiet = {
        "remutated": [],
        "reused": [],
        "no_coverage": {
            "total": 1,
            "functions": [{"file": "a.py", "function": "add", "count": 1}],
        },
    }
    warned = _merge(
        _outcome(0, status="passed", summary=quiet),
        _outcome(
            0,
            status="passed",
            summary={
                "remutated": [],
                "reused": [],
                "no_coverage": {
                    "total": 1,
                    "functions": [{"file": "a.py", "function": "add", "count": 2}],
                },
            },
        ),
        None,
    )

    assert warned.exit_code == 0
    assert warned.result.name == "mutate"
    assert warned.result.status == "warn"
    assert in_both(warned.result.reason) == (
        "3 mutants without a test",
        "3 mutantes sem teste",
    )
    assert warned.summary["no_coverage"] == {
        "total": 3,
        "functions": [{"file": "a.py", "function": "add", "count": 3}],
    }
    assert _merge_no_coverage(
        [
            "nope",
            {"functions": None},
            {
                "functions": [
                    None,
                    {"count": None},
                    {"file": "a.py", "function": "zeta", "count": 1},
                    {"file": "b.py", "function": "scale", "count": 1},
                    {"file": "a.py", "function": "add", "count": 4},
                ]
            },
        ]
    ) == {
        "total": 6,
        "functions": [
            {"file": "a.py", "function": "add", "count": 4},
            {"file": "a.py", "function": "zeta", "count": 1},
            {"file": "b.py", "function": "scale", "count": 1},
            {"file": "", "function": "", "count": 0},
        ],
    }


def test_equal_exit_codes_keep_the_first_value() -> None:
    from bob_quality.mutate_gate import _worse

    class _Code(int):
        pass

    python = _Code(2)
    typescript = _Code(2)

    assert _worse(python, typescript) is python
    assert _worse(python, _Code(4)) == 4
    assert _worse(_Code(4), typescript) == 4


def test_a_label_that_is_not_a_list_counts_as_empty() -> None:
    from bob_quality.mutate_gate import _merge

    summary = {
        "remutated": "nope",
        "reused": [],
        "no_coverage": {"total": 0, "functions": []},
    }

    merged = _merge(_outcome(0, status="passed", summary=summary), _outcome(0, status="passed"), None)

    assert merged.summary["remutated"] == []
    assert merged.summary["reused"] == []


def test_typescript_mutation_ignores_a_repo_without_that_language(tmp_path: Path) -> None:
    from bob_quality.stryker_gate import run_typescript_mutation

    assert run_typescript_mutation(
        tmp_path, Config(), {}, tmp_path, python_measured=False
    ) == (None, None)


def test_a_summary_without_its_label_list_is_a_bug() -> None:
    from bob_quality.mutate_gate import _merge

    broken = _outcome(0, status="passed", summary={"reused": [], "no_coverage": {"total": 0, "functions": []}})

    with pytest.raises(KeyError, match="remutated"):
        _merge(broken, _outcome(0, status="passed"), None)


def test_merge_without_either_language_names_the_bug() -> None:
    from bob_quality.mutate_gate import _merge

    with pytest.raises(RuntimeError, match="^mutate gate had neither language$"):
        _merge(None, None, None)


def test_absorb_records_every_gate_argument_and_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from bob_quality import check as check_mod

    config = Config(languages=("python", "typescript"))
    diff = {"src/safe.ts": {2}, "src/app.py": {4}}
    coverage = tmp_path / "coverage.json"
    out = tmp_path / "out"
    metric = FunctionMetric(
        lang="python",
        module="app",
        name="add",
        file="src/app.py",
        start_line=1,
        end_line=4,
        cc=1,
        coverage=1.0,
        crap=1.0,
        changed=True,
    )
    clone = Clone("src/a.ts", 1, 4, "src/b.ts", 1, 4, 4, 20)
    violation = DepViolation("app", "legacy", "cycle", True)
    mutation = _outcome(0, status="passed", versions={"mutmut": "3.8.0", "stryker": "10.0.0"})
    seen: dict[str, object] = {}

    def crap(**kwargs: object):
        seen["crap"] = kwargs
        return GateResult("crap", "passed"), [metric], 0, {"lizard": "1.24.1"}, 2

    def dry(**kwargs: object):
        seen["dry"] = kwargs
        return GateResult("dry", "warn", "clone"), [clone], 0, {"jscpd": "5.4.1"}

    def deps(cwd: Path, got_config: Config, files: set[str]):
        seen["deps"] = (cwd, got_config, files)
        return GateResult("deps", "passed"), 1, {"import-linter": "2.15"}, [violation]

    def mutate(**kwargs: object) -> MutationOutcome:
        seen["mutate"] = kwargs
        return mutation

    monkeypatch.setattr(check_mod, "run_crap_gate", crap)
    monkeypatch.setattr(check_mod, "run_dry_gate", dry)
    monkeypatch.setattr(check_mod, "run_deps_gate", deps)
    monkeypatch.setattr(check_mod, "run_mutate_gate", mutate)

    state = check_mod._measure(
        tmp_path,
        config,
        diff,
        10.0,
        coverage,
        ["crap", "dry", "deps", "mutate", "nope"],
        out,
        4,
    )

    assert seen["crap"] == {
        "cwd": tmp_path,
        "config": config,
        "diff_lines": diff,
        "max_crap": 10.0,
        "coverage_file": coverage,
    }
    assert seen["dry"] == {"cwd": tmp_path, "config": config, "diff_lines": diff}
    assert seen["deps"] == (tmp_path, config, set(diff))
    assert seen["mutate"] == {
        "cwd": tmp_path,
        "config": config,
        "diff_lines": diff,
        "out_dir": out,
        "max_workers": 4,
        "baseline": 2,
    }
    assert state.metrics == [metric]
    assert state.baseline == 2
    assert state.clones == [clone]
    assert state.violations == [violation]
    assert state.mutation is mutation
    assert state.exit_code == 1
    assert state.versions == {
        "lizard": "1.24.1",
        "jscpd": "5.4.1",
        "import-linter": "2.15",
        "mutmut": "3.8.0",
        "stryker": "10.0.0",
    }
    assert [(gate.name, gate.status) for gate in state.gates] == [
        ("crap", "passed"),
        ("dry", "warn"),
        ("deps", "passed"),
        ("mutate", "passed"),
        ("nope", "not_run"),
    ]
    assert in_both(state.gates[-1].reason) == (
        "gate not implemented in this slice",
        "gate não implementado nesta fatia",
    )


def _lizard(file: str, name: str, start: int, end: int, cc: int) -> str:
    return f"1,{cc},1,0,1,0,{file},{name},{name},{start},{end}"


def test_changed_spans_keep_both_languages_and_the_include_roots(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from bob_quality import stryker_gate

    calls: list[tuple[object, object, object]] = []

    def fake_csv(cwd: Path, include: object, exclude: object, language: str = "") -> str:
        calls.append((include, exclude, language))
        assert cwd == tmp_path
        if language == "typescript":
            return "\n".join(
                [
                    _lizard("src/types.d.ts", "ghost", 1, 1, 1),
                    _lizard("src/safe.ts", "add", 1, 4, 2),
                    _lizard("src/safe.ts", "add", 1, 4, 2),
                    _lizard("src/safe.ts", "scale", 6, 9, 3),
                ]
            )
        if language == "javascript":
            return _lizard("src/extra.js", "extra", 1, 3, 4)
        return ""

    monkeypatch.setattr(stryker_gate, "run_lizard_csv", fake_csv)
    config = Config(languages=("typescript",), include=("src", "lib"), exclude=("dist",))

    spans = stryker_gate._changed_spans(
        tmp_path,
        config,
        {"src/safe.ts": {2}, "src/extra.js": {1}},
    )

    assert calls == [
        (["src", "lib"], ["dist"], "typescript"),
        (["src", "lib"], ["dist"], "javascript"),
    ]
    assert [(item.file, item.name, item.cc) for item in spans] == [
        ("src/safe.ts", "add", 2),
        ("src/extra.js", "extra", 4),
    ]


def test_invoke_drops_pytest_variables_and_captures_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from bob_quality import stryker_gate

    report = tmp_path / "stryker-report.json"
    report.write_text("stale")
    seen: dict[str, object] = {}

    def fake(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["args"] = args
        seen.update(kwargs)
        assert not report.exists()
        return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")

    monkeypatch.setattr(stryker_gate.subprocess, "run", fake)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_mutation_branches.py")
    monkeypatch.setenv("BOB_KEEP", "yes")

    completed = stryker_gate._invoke(tmp_path, report, ["npx", "stryker"])

    assert completed.stdout == "ok"
    assert seen["cwd"] == tmp_path
    assert seen["capture_output"] is True
    assert seen["text"] is True
    assert seen["stdin"] is subprocess.DEVNULL
    env = seen["env"]
    assert isinstance(env, dict)
    assert "PYTEST_CURRENT_TEST" not in env
    assert env["BOB_KEEP"] == "yes"


def test_relative_outside_the_repo_is_absolute(tmp_path: Path) -> None:
    from bob_quality.stryker_gate import _relative

    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside" / "report.json"
    outside.parent.mkdir()
    outside.write_text("{}\n")

    assert _relative(repo, outside) == str(outside.resolve())


def test_run_creates_a_missing_parent_and_carries_versions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from bob_quality import stryker_gate

    out = tmp_path / "missing" / "bob"
    span = CyclomaticFunction("src/safe.ts", "add", 1, 4, 1)

    def invoke(cwd: Path, report: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
        assert cwd == tmp_path
        report.write_text(
            json.dumps(
                {
                    "files": {
                        "src/safe.ts": {
                            "mutants": [
                                {
                                    "id": "0",
                                    "mutatorName": "ArithmeticOperator",
                                    "status": "Killed",
                                    "location": {
                                        "start": {"line": 2, "column": 1},
                                        "end": {"line": 2, "column": 2},
                                    },
                                }
                            ]
                        }
                    }
                }
            )
        )
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")

    monkeypatch.setattr(stryker_gate, "_write_config", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stryker_gate, "_argv", lambda *_args, **_kwargs: ["npx"])
    monkeypatch.setattr(stryker_gate, "_invoke", invoke)

    outcome = stryker_gate._run(tmp_path, out, [span], _VERSIONS, [_WAIVER], [])

    assert out.is_dir()
    assert outcome.exit_code == 0
    assert outcome.versions == _VERSIONS
    assert outcome.waivers == [_WAIVER]
    assert outcome.summary["remutated"] == ["src/safe.ts::add"]


def test_a_dry_run_after_the_retry_is_still_baseline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from bob_quality import stryker_gate

    out = tmp_path / "bob"
    out.mkdir()
    incremental = out / "stryker-incremental.json"
    incremental.write_text("{}\n")
    seen: list[Path] = []

    def invoke(cwd: Path, _report: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
        seen.append(cwd)
        if len(seen) == 1:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="no report")
        return subprocess.CompletedProcess(
            argv,
            1,
            stdout="",
            stderr="There were failed tests in the initial test run.",
        )

    monkeypatch.setattr(stryker_gate, "_write_config", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stryker_gate, "_argv", lambda *_args, **_kwargs: ["npx"])
    monkeypatch.setattr(stryker_gate, "_invoke", invoke)

    outcome = stryker_gate._run(
        tmp_path,
        out,
        [CyclomaticFunction("src/safe.ts", "add", 1, 4, 1)],
        _VERSIONS,
        [_WAIVER],
        [],
    )

    assert seen == [tmp_path, tmp_path]
    assert not incremental.exists()
    assert outcome.exit_code == 2
    assert outcome.result.name == "mutate"
    assert outcome.result.status == "not_run"
    assert outcome.versions == _VERSIONS
    assert outcome.waivers == [_WAIVER]
    assert in_both(outcome.result.reason) == (
        "baseline tests failed before measuring",
        "testes da baseline falharam antes de medir",
    )


def test_a_json_list_is_not_a_stryker_report(tmp_path: Path) -> None:
    from bob_quality.stryker_gate import _from_report

    report = tmp_path / "stryker-report.json"
    report.write_text("[]\n")

    with pytest.raises(StrykerParseError) as caught:
        _from_report(report, [], _VERSIONS, [_WAIVER], [])

    assert in_both(caught.value) == (
        "invalid Stryker report: stryker-report.json",
        "relatório do Stryker inválido: stryker-report.json",
    )


def test_from_report_keeps_versions_and_waiver_rows(tmp_path: Path) -> None:
    from bob_quality.stryker_gate import _from_report

    report = tmp_path / "stryker-report.json"
    report.write_text(json.dumps({"files": {}}))
    span = CyclomaticFunction("src/safe.ts", "add", 1, 4, 1)

    outcome = _from_report(report, [span], _VERSIONS, [_WAIVER], [])

    assert outcome.versions == _VERSIONS
    assert outcome.waivers == [_WAIVER]
    assert outcome.summary["remutated"] == ["src/safe.ts::add"]
    assert outcome.exit_code == 0


def test_from_report_records_the_mutants_for_bob_waive_and_shows_each_target(
    tmp_path: Path,
) -> None:
    def row(mutant_id: str, status: str, column: int) -> dict[str, object]:
        return {
            "id": mutant_id,
            "mutatorName": "ArithmeticOperator",
            "status": status,
            "location": {
                "start": {"line": 2, "column": column},
                "end": {"line": 2, "column": column + 1},
            },
        }

    report = tmp_path / "stryker-report.json"
    report.write_text(
        json.dumps(
            {"files": {"src/safe.ts": {"mutants": [row("0", "Survived", 3), row("1", "Killed", 7)]}}}
        )
    )
    span = CyclomaticFunction("src/safe.ts", "add", 1, 4, 1)
    waived = Waiver("src/safe.ts::add::ArithmeticOperator@2:3-2:4", "porque", "ada", "2026-10-12")

    outcome = _from_report(report, [span], _VERSIONS, [_WAIVER], [waived])
    recorded = json.loads((tmp_path / STRYKER_MUTANTS_NAME).read_text())

    assert recorded == {
        "mutants": [
            {
                "id": "src/safe.ts:0",
                "function": "add",
                "file": "src/safe.ts",
                "line": 2,
                "operator": "ArithmeticOperator@2:3-2:4",
                "status": "survived",
                "waiver": "porque",
            },
            {
                "id": "src/safe.ts:1",
                "function": "add",
                "file": "src/safe.ts",
                "line": 2,
                "operator": "ArithmeticOperator@2:7-2:8",
                "status": "killed",
                "waiver": None,
            },
        ]
    }
    assert outcome.exit_code == 0
    assert outcome.survivors == [
        {**recorded["mutants"][0], "target": "src/safe.ts::add::ArithmeticOperator@2:3-2:4"}
    ]


def test_tool_and_waiver_errors_exit_4_without_versions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from bob_quality import stryker_gate

    monkeypatch.setattr(stryker_gate, "_missing_tool", lambda: None)
    config = Config(languages=("typescript",))

    def broken_versions() -> dict[str, str]:
        raise ToolError(msg("npm.deps_missing", hint="npm ci"))

    monkeypatch.setattr(stryker_gate, "_versions", broken_versions)
    outcome, skip = stryker_gate.run_typescript_mutation(tmp_path, config, {}, tmp_path, python_measured=False)
    assert skip is None
    assert outcome is not None
    assert outcome.exit_code == 4
    assert outcome.versions == {}
    assert outcome.waivers == []
    assert in_both(outcome.result.reason) == (
        "plugin npm dependencies missing: npm ci",
        "dependências npm do plugin ausentes: npm ci",
    )

    monkeypatch.setattr(stryker_gate, "_versions", lambda: dict(_VERSIONS))

    def broken_waivers(_cwd: Path) -> list[object]:
        raise WaiverError(msg("waiver.list_required", path=".bob/waivers.yaml", field="waivers"))

    monkeypatch.setattr(stryker_gate, "load_waivers", broken_waivers)
    outcome, skip = stryker_gate.run_typescript_mutation(tmp_path, config, {}, tmp_path, python_measured=False)
    assert skip is None
    assert outcome is not None
    assert outcome.versions == {}
    assert in_both(outcome.result.reason) == (
        ".bob/waivers.yaml: waivers must be a list",
        ".bob/waivers.yaml: waivers deve ser uma lista",
    )


def test_later_failures_keep_versions_and_the_loaded_waivers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from bob_quality import stryker_gate

    _write_waiver(tmp_path)
    monkeypatch.setattr(stryker_gate, "_missing_tool", lambda: None)
    monkeypatch.setattr(stryker_gate, "_versions", lambda: dict(_VERSIONS))
    config = Config(languages=("typescript",))

    def lizard_fails(*_args: object, **_kwargs: object) -> list[CyclomaticFunction]:
        raise LizardParseError(msg("lizard.unexpected_row", row=["short"]))

    monkeypatch.setattr(stryker_gate, "_changed_spans", lizard_fails)
    outcome, skip = stryker_gate.run_typescript_mutation(tmp_path, config, {}, tmp_path, python_measured=False)
    assert skip is None
    assert outcome is not None
    assert outcome.exit_code == 4
    assert outcome.versions == _VERSIONS
    assert outcome.waivers == [_WAIVER]
    assert in_both(outcome.result.reason)[0].startswith("unexpected CSV row:")

    monkeypatch.setattr(stryker_gate, "_changed_spans", lambda *_args, **_kwargs: [])
    outcome, skip = stryker_gate.run_typescript_mutation(tmp_path, config, {}, tmp_path, python_measured=False)
    assert skip is None
    assert outcome is not None
    assert outcome.exit_code == 0
    assert outcome.result == GateResult("mutate", "passed")
    assert outcome.versions == _VERSIONS
    assert outcome.waivers == [_WAIVER]
    assert outcome.summary == {
        "remutated": [],
        "reused": [],
        "no_coverage": {"total": 0, "functions": []},
    }

    def disk(*_args: object, **_kwargs: object) -> MutationOutcome:
        raise OSError("disk")

    monkeypatch.setattr(
        stryker_gate,
        "_changed_spans",
        lambda *_args, **_kwargs: [CyclomaticFunction("src/safe.ts", "add", 1, 4, 1)],
    )
    monkeypatch.setattr(stryker_gate, "_run", disk)
    outcome, skip = stryker_gate.run_typescript_mutation(tmp_path, config, {}, tmp_path, python_measured=False)
    assert skip is None
    assert outcome is not None
    assert outcome.exit_code == 4
    assert outcome.versions == _VERSIONS
    assert outcome.waivers == [_WAIVER]
    assert in_both(outcome.result.reason) == ("disk", "disk")


def test_unchanged_function_does_not_hide_the_next_changed_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from bob_quality import stryker_gate

    def fake_csv(_cwd: Path, _include: object, _exclude: object, language: str = "") -> str:
        if language != "typescript":
            return ""
        return "\n".join(
            [
                _lizard("src/old.ts", "old", 1, 3, 1),
                _lizard("src/safe.ts", "add", 5, 8, 2),
            ]
        )

    monkeypatch.setattr(stryker_gate, "run_lizard_csv", fake_csv)

    spans = stryker_gate._changed_spans(
        tmp_path,
        Config(languages=("typescript",)),
        {"src/safe.ts": {6}},
    )

    assert [(item.name, item.cc) for item in spans] == [("add", 2)]
