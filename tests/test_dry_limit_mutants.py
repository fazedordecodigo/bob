"""Testes no processo. O mutmut não associa um subprocesso à função mutada."""

from __future__ import annotations

import argparse
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from bob_quality.check import (
    DEFAULT_GATES,
    _Measured,
    run_check,
)
from bob_quality.cli import (
    _negative_ceiling,
    _reproduce,
    _run_check,
    build_parser,
    main,
)
from bob_quality.config import Config
from bob_quality.dry_gate import _Advise, _Block, _Floors, _budget, _qualifies, _verdict
from bob_quality.messages import Message
from bob_quality.models import Clone, GateResult, Report


def test_max_new_clones_parses_as_an_int() -> None:
    parsed = build_parser().parse_args(["check", "--max-new-clones", "2", "--dry-fail"])
    omitted = build_parser().parse_args(["dry"])

    assert parsed.max_new_clones == 2
    assert parsed.dry_fail is True
    assert omitted.max_new_clones is None
    assert omitted.dry_fail is False


def test_negative_ceiling_rejects_only_a_negative_integer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(["dry", "--max-new-clones", "-1"])

    assert code == 4
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == "--max-new-clones must be at least 0\n"
    assert _negative_ceiling(argparse.Namespace(max_new_clones=0)) is False
    assert _negative_ceiling(argparse.Namespace(max_new_clones=-1)) is True
    assert _negative_ceiling(argparse.Namespace()) is False


def test_run_check_forwards_dry_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    def fake(**kwargs: object) -> int:
        seen.update(kwargs)
        return 0

    monkeypatch.setattr("bob_quality.cli.run_check", fake)
    args = argparse.Namespace(
        gates="dry,deps",
        base="trunk",
        format="json",
        dry_fail=True,
        max_new_clones=0,
    )

    code = _run_check(args, tmp_path, tmp_path / "out", tmp_path / "bob.yaml", "en")

    assert code == 0
    assert seen["gates"] == ["dry", "deps"]
    assert seen["base"] == "trunk"
    assert seen["config_path"] == tmp_path / "bob.yaml"
    assert seen["out_dir"] == tmp_path / "out"
    assert seen["fmt"] == "json"
    assert seen["lang"] == "en"
    assert seen["dry_fail"] is True
    assert seen["max_new_clones"] == 0
    assert seen["reproduce"] == (
        "bob check --base trunk --gates dry,deps --format json --dry-fail --max-new-clones 0"
    )


def test_run_check_without_gates_keeps_the_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    def fake(**kwargs: object) -> int:
        seen.update(kwargs)
        return 0

    monkeypatch.setattr("bob_quality.cli.run_check", fake)
    _run_check(
        argparse.Namespace(gates=None, base=None, format="both", dry_fail=False, max_new_clones=None),
        tmp_path,
        tmp_path,
        None,
        "pt-BR",
    )

    assert seen["gates"] is None
    assert seen["dry_fail"] is False
    assert seen["max_new_clones"] is None
    assert seen["reproduce"] == "bob check"


def test_reproduce_keeps_every_flag_including_a_zero_ceiling() -> None:
    args = argparse.Namespace(
        base="trunk",
        gates="dry,deps",
        config="bob.yaml",
        out="custom",
        format="json",
        threshold=9,
        coverage_file="cov.json",
        max_workers=3,
        since_last_run=True,
        dry_fail=True,
        max_new_clones=0,
    )

    assert _reproduce("check", args) == (
        "bob check --base trunk --gates dry,deps --config bob.yaml --out custom "
        "--format json --threshold 9 --coverage-file cov.json --max-workers 3 "
        "--since-last-run --dry-fail --max-new-clones 0"
    )


def test_reproduce_skips_the_default_out_and_format() -> None:
    for out in (".bob/", ".bob"):
        args = argparse.Namespace(
            out=out,
            format="both",
            since_last_run=False,
            dry_fail=False,
            max_new_clones=None,
        )
        assert _reproduce("dry", args) == "bob dry"


def test_reproduce_of_a_bare_namespace_is_the_command() -> None:
    assert _reproduce("deps", argparse.Namespace()) == "bob deps"


def test_budget_uses_the_flag_ceiling_and_the_fraction() -> None:
    warned = _budget(Config(min_similarity=50, min_lines=7, max_new_clones=9), False, 4)
    forced = _budget(Config(new_clones="warn", max_new_clones=9, min_similarity=50, min_lines=7), True, 4)
    from_file = _budget(
        Config(new_clones="fail", max_new_clones=9, min_similarity=50, min_lines=7),
        False,
        None,
    )
    zero = _budget(Config(new_clones="fail", max_new_clones=9), False, 0)

    assert isinstance(warned, _Advise)
    assert warned.floors == _Floors(0.5, 7)
    assert isinstance(forced, _Block)
    assert forced.allowed == 4
    assert forced.floors == _Floors(0.5, 7)
    assert isinstance(from_file, _Block)
    assert from_file.allowed == 9
    assert isinstance(zero, _Block)
    assert zero.allowed == 0


def test_verdict_names_the_gate_and_the_exact_reason() -> None:
    versions = {"jscpd": "5.4.1"}
    floors = _Floors(0.0, 0)
    one = _clone()
    two = [_clone(), _clone(lines=12)]

    assert _verdict(_Advise(floors), [], versions) == (GateResult("dry", "passed"), [], 0, versions)
    assert _verdict(_Advise(floors), [one], versions) == (
        GateResult("dry", "warn", Message("dry.clone", (("count", 1),))),
        [one],
        0,
        versions,
    )
    warned = _verdict(_Advise(floors), two, versions)
    assert warned[0] == GateResult("dry", "warn", Message("dry.clones", (("count", 2),)))
    assert warned[1:] == (two, 0, versions)
    assert _verdict(_Block(floors, 0), [one], versions) == (
        GateResult("dry", "failed", Message("dry.exceeded_one", (("count", 1), ("limit", 0)))),
        [one],
        1,
        versions,
    )
    failed = _verdict(_Block(floors, 1), two, versions)
    assert failed[0] == GateResult(
        "dry", "failed", Message("dry.exceeded_many", (("count", 2), ("limit", 1)))
    )
    assert failed[1:] == (two, 1, versions)
    at_ceiling = _verdict(_Block(floors, 1), [one], versions)
    assert at_ceiling[0] == GateResult("dry", "warn", Message("dry.clone", (("count", 1),)))
    assert at_ceiling[2] == 0


def test_missing_similarity_counts_as_one_and_the_line_floor_is_inclusive() -> None:
    exact = _clone(lines=5, similarity=None)

    assert _qualifies(exact, _Floors(1.0, 5)) is True
    assert _qualifies(exact, _Floors(1.5, 5)) is False
    assert _qualifies(exact, _Floors(1.0, 6)) is False
    assert _qualifies(_clone(lines=5, similarity=0.5), _Floors(0.5, 5)) is True
    assert _qualifies(_clone(lines=4, similarity=1.0), _Floors(0.0, 5)) is False


def test_run_check_threads_the_defaults_and_the_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    defaults = _drive(monkeypatch, tmp_path)
    out = tmp_path / "out"
    cov = tmp_path / "cov.json"
    code = run_check(
        tmp_path,
        threshold=12.5,
        coverage_file=cov,
        max_workers=3,
        fmt="json",
        lang="pt-BR",
        out_dir=out,
    )

    assert code == 0
    assert defaults["open"] == (tmp_path, None, None, 12.5, "bob check", list(DEFAULT_GATES))
    assert defaults["measure"][3] == 8.0
    assert defaults["measure"][4] == cov
    assert defaults["measure"][5] == list(DEFAULT_GATES)
    assert defaults["measure"][6] == out
    assert defaults["measure"][7] == 3
    assert defaults["measure"][8] == "trunk"
    assert defaults["measure"][9] is False
    assert defaults["measure"][10] is None
    assert defaults["waivers"] == (tmp_path, "trunk", "bob check", list(DEFAULT_GATES))
    assert defaults["state"].loaded_waivers == [{"id": "w"}]
    assert defaults["assemble"][1:] == ("abc", "trunk", {"a.py": {1}}, 8.0, "bob check")
    assert defaults["written"][0] is defaults["report"]
    assert defaults["written"][1:] == (out, "json", "pt-BR")

    forced = _drive(monkeypatch, tmp_path)
    forced_out = tmp_path / "forced"
    code = run_check(
        tmp_path,
        base="origin",
        gates=["dry"],
        config_path=tmp_path / "bob.yaml",
        out_dir=forced_out,
        fmt="md",
        threshold=2.5,
        coverage_file=cov,
        reproduce="bob check --gates dry",
        max_workers=1,
        lang="en",
        dry_fail=True,
        max_new_clones=0,
    )

    assert code == 0
    assert forced["open"] == (
        tmp_path,
        "origin",
        tmp_path / "bob.yaml",
        2.5,
        "bob check --gates dry",
        ["dry"],
    )
    assert forced["measure"][8] == "trunk"
    assert forced["measure"][9] is True
    assert forced["measure"][10] == 0
    assert forced["assemble"][5] == "bob check --gates dry"
    assert forced["written"][1:] == (forced_out, "md", "en")


def test_run_check_returns_a_waiver_report_without_assembling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = _drive(monkeypatch, tmp_path, waiver_report=_sample_report("waiver"))
    out = tmp_path / "out"

    code = run_check(tmp_path, out_dir=out, fmt="md", lang="en")

    assert code == 4
    assert seen["written"] == (seen["waiver"], out, "md", "en")
    assert "assemble" not in seen


def _drive(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    waiver_report: Report | None = None,
) -> dict[str, object]:
    seen: dict[str, object] = {}
    state = _Measured()
    report = _sample_report("assembled")
    config = Config()
    diff = {"a.py": {1}}

    def opened(*args: object) -> tuple[object, ...]:
        seen["open"] = args
        return config, "trunk", 8.0, "abc", diff

    def measured(*args: object) -> _Measured:
        seen["measure"] = args
        return state

    def waivers(*args: object) -> list[dict[str, object]] | Report:
        seen["waivers"] = args
        if waiver_report is not None:
            seen["waiver"] = waiver_report
            return waiver_report
        return [{"id": "w"}]

    def assembled(*args: object) -> Report:
        seen["assemble"] = args
        seen["report"] = report
        return report

    def written(*args: object) -> int:
        seen["written"] = args
        return 4 if waiver_report is not None else 0

    monkeypatch.setattr("bob_quality.check._open", opened)
    monkeypatch.setattr("bob_quality.check._measure", measured)
    monkeypatch.setattr("bob_quality.check._load_idle_waivers", waivers)
    monkeypatch.setattr("bob_quality.check._assemble", assembled)
    monkeypatch.setattr("bob_quality.check._written", written)
    seen["state"] = state
    return seen


def _sample_report(reproduce: str) -> Report:
    return Report(
        schema_version=1,
        commit="abc",
        base="trunk",
        generated_at="t",
        tool_versions={},
        gates=[],
        focus=[],
        top_crap=[],
        reproduce=reproduce,
    )


def _clone(lines: int = 11, similarity: float | None = None) -> Clone:
    return Clone("a.py", 1, lines, "b.py", 1, lines, lines, 20, similarity)
