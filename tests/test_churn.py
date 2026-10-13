from __future__ import annotations

import json
import os
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from helpers import init_python_repo, run_bob

from bob_quality.check import run_check
from bob_quality.churn import (
    ChurnMeasured,
    ChurnUnavailable,
    ChurnWindow,
    FileChurn,
    Hotspot,
    measure_churn,
)
from bob_quality.models import FunctionMetric, Report
from bob_quality.report import _churn_json, _churn_lines, to_json, to_markdown

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "src/bob_quality/schemas/report_v1.json").read_text()
)
_OFFSET = timezone(timedelta(hours=-3))


def test_window_keeps_start_midnight_and_the_end_second(tmp_path: Path) -> None:
    repo, tip = _boundary(tmp_path)
    counted = measure_churn(repo, tip, 90, {"src/a.py": {1}}, ("src",), ())
    one_day = measure_churn(repo, tip, 1, {"src/a.py": {4}}, ("src",), ())

    assert counted == ChurnMeasured(
        ChurnWindow(90, date(2026, 10, 12)),
        (FileChurn("src/a.py", 3, 1.0),),
        (),
    )
    assert counted.file_count() == 1
    assert counted.module_count() == 1
    assert counted.module_names() == ("src",)
    assert one_day == ChurnMeasured(
        ChurnWindow(1, date(2026, 10, 12)),
        (FileChurn("src/a.py", 2, 1.0),),
        (),
    )
    assert measure_churn(repo, tip, 90, {"src/a.py": {9}}, ("src",), ()) == ChurnMeasured(
        ChurnWindow(90, date(2026, 10, 12)),
        (FileChurn("src/a.py", 3, 1.0),),
        (),
    )


def test_commit_date_fixes_the_window_when_the_diff_is_empty(tmp_path: Path) -> None:
    repo, tip = _tree(tmp_path)
    expected = ChurnMeasured(ChurnWindow(90, date(2020, 1, 15)), (), ())

    assert measure_churn(repo, tip, 90, {}, ("src",), ()) == expected
    assert measure_churn(repo, tip, 90, {}, (".",), ()) == expected


def test_hotspot_is_commits_times_cc(tmp_path: Path) -> None:
    repo, tip = _boundary(tmp_path)
    changed = _metric("src/a.py", "alpha", 1, 4, True)
    unchanged = _metric("src/a.py", "old", 8, 9, False)
    scored = measure_churn(repo, tip, 90, {"src/a.py": {1}}, ("src",), (changed, unchanged))
    empty = measure_churn(repo, tip, 90, {"src/a.py": set()}, ("src",), ())

    assert scored == ChurnMeasured(
        ChurnWindow(90, date(2026, 10, 12)),
        (FileChurn("src/a.py", 3, 1.0),),
        (Hotspot("src/a.py", "alpha", 1, 4, 3),),
    )
    assert scored.hotspots[0].hotspot == 12
    assert empty == ChurnMeasured(
        ChurnWindow(90, date(2026, 10, 12)),
        (FileChurn("src/a.py", 3, 0.0),),
        (),
    )
    payload = to_json(_report(scored))
    assert payload["schema_version"] == 1
    assert payload["churn"] == {
        "kind": "measured",
        "window_days": 90,
        "ends_on": "2026-10-12",
        "files": [{"path": "src/a.py", "commits": 3, "relative": 1.0}],
        "hotspots": [
            {
                "file": "src/a.py",
                "function": "alpha",
                "start_line": 1,
                "cc": 4,
                "commits": 3,
                "hotspot": 12,
            }
        ],
        "diffusion": {"files": 1, "modules": 1},
    }
    Draft202012Validator(SCHEMA).validate(payload)
    assert _section(to_markdown(_report(scored), "en"), "## Churn", "## How to reproduce") == (
        "## Churn\n"
        "\n"
        "Window: 90 days ending 2026-10-12.\n"
        "Diffusion: 1 files, 1 modules.\n"
        "Modules: `src`.\n"
        "\n"
        "| File | Commits | Relative |\n"
        "|---|---:|---:|\n"
        "| `src/a.py` | 3 | 1.0000 |\n"
        "\n"
        "| Function | File | CC | Commits | Hotspot |\n"
        "|---|---|---:|---:|---:|\n"
        "| `alpha` | `src/a.py:1` | 4 | 3 | 12 |\n"
        "\n"
    )
    assert _section(to_markdown(_report(scored), "pt-BR"), "## Rotatividade", "## Como reproduzir") == (
        "## Rotatividade\n"
        "\n"
        "Janela: 90 dias terminando em 2026-10-12.\n"
        "Difusão: 1 arquivos, 1 módulos.\n"
        "Módulos: `src`.\n"
        "\n"
        "| Arquivo | Commits | Relativo |\n"
        "|---|---:|---:|\n"
        "| `src/a.py` | 3 | 1.0000 |\n"
        "\n"
        "| Função | Arquivo | CC | Commits | Hotspot |\n"
        "|---|---|---:|---:|---:|\n"
        "| `alpha` | `src/a.py:1` | 4 | 3 | 12 |\n"
        "\n"
    )


def test_include_is_a_segment_prefix_and_a_glob_does_not_widen(tmp_path: Path) -> None:
    repo, tip = _tree(tmp_path)
    changed = {
        "src/a.py": {1},
        "src/b.py": {1},
        "src2/a.py": {1},
        "tests/a.py": {1},
        "a.py": {1},
        "src/*.py": {1},
        "/abs/a.py": {1},
    }
    under_src = measure_churn(repo, tip, 90, changed, ("src",), ())
    dotted = measure_churn(repo, tip, 90, changed, ("./src",), ())
    slashed = measure_churn(repo, tip, 90, changed, ("src/",), ())
    everywhere = measure_churn(repo, tip, 90, changed, (".",), ())
    empty_root = measure_churn(repo, tip, 90, changed, ("",), ())
    dot_slash = measure_churn(repo, tip, 90, changed, ("./",), ())
    outside = _metric("src2/a.py", "beta", 1, 9, True)
    first = _metric("src/a.py", "alpha", 1, 4, True)
    again = _metric("src/a.py", "alpha", 1, 9, True)
    kept = measure_churn(repo, tip, 90, changed, ("src",), (outside, first, again))

    assert under_src.files == (
        FileChurn("src/*.py", 0, None),
        FileChurn("src/a.py", 1, 1.0),
        FileChurn("src/b.py", 2, 1.0),
    )
    assert dotted.files == under_src.files
    assert slashed.files == under_src.files
    assert under_src.module_names() == ("src",)
    assert everywhere.files == (
        FileChurn("a.py", 1, 1.0),
        FileChurn("src/*.py", 0, None),
        FileChurn("src/a.py", 1, 1.0),
        FileChurn("src/b.py", 2, 1.0),
        FileChurn("src2/a.py", 1, 1.0),
        FileChurn("tests/a.py", 1, 1.0),
    )
    assert everywhere.module_names() == (".", "src", "src2", "tests")
    assert everywhere.file_count() == 6
    assert everywhere.module_count() == 4
    assert empty_root.files == everywhere.files
    assert dot_slash.files == everywhere.files
    assert kept.hotspots == (Hotspot("src/a.py", "alpha", 1, 4, 1),)
    assert kept.hotspots[0].hotspot == 4


def test_hotspots_sort_by_product_then_name(tmp_path: Path) -> None:
    repo, tip = _tree(tmp_path)
    metrics = (
        _metric("src/b.py", "m", 2, 4, True),
        _metric("src/a.py", "m", 9, 8, True),
        _metric("src/a.py", "m", 2, 8, True),
        _metric("src/a.py", "a", 3, 8, True),
        _metric("src/b.py", "z", 1, 9, True),
    )
    section = measure_churn(
        repo,
        tip,
        90,
        {"src/a.py": {1}, "src/b.py": {1}},
        ("src",),
        metrics,
    )

    assert [item.path for item in section.files] == ["src/a.py", "src/b.py"]
    assert [item.commits for item in section.files] == [1, 2]
    assert [
        (row.file, row.function, row.start_line, row.hotspot) for row in section.hotspots
    ] == [
        ("src/b.py", "z", 1, 18),
        ("src/a.py", "a", 3, 8),
        ("src/a.py", "m", 2, 8),
        ("src/a.py", "m", 9, 8),
        ("src/b.py", "m", 2, 8),
    ]


def test_dot_include_counts_every_relative_file(tmp_path: Path) -> None:
    repo, tip = _tree(tmp_path)

    section = measure_churn(
        repo, tip, 90, {"a.py": {1}, "src/a.py": {1}}, (".",), ()
    )

    assert section == ChurnMeasured(
        ChurnWindow(90, date(2020, 1, 15)),
        (FileChurn("a.py", 1, 1.0), FileChurn("src/a.py", 1, 1.0)),
        (),
    )


def test_a_skipped_metric_keeps_the_later_hotspot(tmp_path: Path) -> None:
    repo, tip = _tree(tmp_path)
    metrics = (
        _metric("nope.py", "skip", 1, 9, True),
        _metric("src/a.py", "kept", 1, 3, True),
    )

    section = measure_churn(repo, tip, 90, {"src/a.py": {1}}, ("src",), metrics)

    assert section.hotspots == (Hotspot("src/a.py", "kept", 1, 3, 1),)


def test_a_repeated_metric_keeps_the_later_hotspot(tmp_path: Path) -> None:
    repo, tip = _tree(tmp_path)
    metrics = (
        _metric("src/a.py", "kept", 1, 3, True),
        _metric("src/a.py", "kept", 1, 9, True),
        _metric("src/b.py", "later", 2, 4, True),
    )

    section = measure_churn(
        repo, tip, 90, {"src/a.py": {1}, "src/b.py": {1}}, ("src",), metrics
    )

    assert section.hotspots == (
        Hotspot("src/b.py", "later", 2, 4, 2),
        Hotspot("src/a.py", "kept", 1, 3, 1),
    )


def test_signature_text_is_not_a_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, tip = _boundary(tmp_path)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    wrapper = bindir / "git"
    wrapper.write_text(
        "#!/bin/sh\n"
        "PATH=${PATH#*:}\n"
        'out=$(git "$@")\n'
        "code=$?\n"
        'if [ "$2" = log ]; then\n'
        "  printf 'No signature\\n%s' \"$out\"\n"
        "else\n"
        "  printf '%s' \"$out\"\n"
        "fi\n"
        'exit "$code"\n'
    )
    wrapper.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")

    assert measure_churn(repo, tip, 90, {"src/a.py": {1}}, ("src",), ()) == ChurnMeasured(
        ChurnWindow(90, date(2026, 10, 12)),
        (FileChurn("src/a.py", 3, 1.0),),
        (),
    )


def test_two_modules_render_with_a_blank_line_before_the_heading() -> None:
    section = ChurnMeasured(
        ChurnWindow(90, date(2020, 1, 15)),
        (FileChurn("lib/a.py", 1, None), FileChurn("src/b.py", 2, None)),
        (),
    )

    markdown = to_markdown(_report(section), "en")

    assert "\n\n## Churn\n" in markdown
    assert "Modules: `lib`, `src`." in markdown


def test_an_unknown_churn_section_reports_its_type() -> None:
    with pytest.raises(AssertionError) as json_error:
        _churn_json(object())
    with pytest.raises(AssertionError) as markdown_error:
        _churn_lines(object())

    assert json_error.value.args == (object,)
    assert markdown_error.value.args == (object,)


def test_a_missing_commit_date_is_unavailable(tmp_path: Path) -> None:
    repo, _tip = _tree(tmp_path)

    assert measure_churn(tmp_path, "a" * 40, 90, {"src/a.py": {1}}, ("src",), ()) == (
        ChurnUnavailable()
    )
    assert measure_churn(repo, "b" * 40, 90, {"src/a.py": {1}}, ("src",), ()) == ChurnUnavailable()


def test_run_check_keeps_the_gate_exit(tmp_path: Path) -> None:
    repo, tip = _boundary(tmp_path)

    assert run_check(repo, base="main", gates=["nope"], reproduce="bob check") == 0

    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    assert payload["schema_version"] == 1
    assert payload["commit"] == tip
    assert payload["exit_code"] == 0
    assert payload["churn"] == {
        "kind": "measured",
        "window_days": 90,
        "ends_on": "2026-10-12",
        "files": [{"path": "src/a.py", "commits": 3, "relative": 1.0}],
        "hotspots": [],
        "diffusion": {"files": 1, "modules": 1},
    }
    Draft202012Validator(SCHEMA).validate(payload)
    assert _section(markdown, "## Churn", "## How to reproduce") == (
        "## Churn\n"
        "\n"
        "Window: 90 days ending 2026-10-12.\n"
        "Diffusion: 1 files, 1 modules.\n"
        "Modules: `src`.\n"
        "\n"
        "| File | Commits | Relative |\n"
        "|---|---:|---:|\n"
        "| `src/a.py` | 3 | 1.0000 |\n"
        "\n"
        "No changed function to score.\n"
        "\n"
    )

    assert run_check(repo, base="main", gates=["nope"], reproduce="bob check", lang="pt-BR") == 0
    portuguese = (repo / ".bob" / "report.md").read_text()
    assert _section(portuguese, "## Rotatividade", "## Como reproduzir") == (
        "## Rotatividade\n"
        "\n"
        "Janela: 90 dias terminando em 2026-10-12.\n"
        "Difusão: 1 arquivos, 1 módulos.\n"
        "Módulos: `src`.\n"
        "\n"
        "| Arquivo | Commits | Relativo |\n"
        "|---|---:|---:|\n"
        "| `src/a.py` | 3 | 1.0000 |\n"
        "\n"
        "Nenhuma função alterada para pontuar.\n"
        "\n"
    )


def test_early_failure_has_no_zero_diffusion(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    english = run_bob(repo, "check", "--config", "missing.yaml", "--gates", "nope")
    english_md = (repo / ".bob" / "report.md").read_text()
    english_json = json.loads((repo / ".bob" / "report.json").read_text())

    assert english.returncode == 4
    assert english_json["schema_version"] == 1
    assert english_json["exit_code"] == 4
    assert english_json["churn"] == {"kind": "unavailable"}
    assert _section(english_md, "## Churn", "## How to reproduce") == (
        "## Churn\n\nChurn counts are unavailable. The exit code is unchanged.\n\n"
    )
    assert "Diffusion:" not in english_md
    Draft202012Validator(SCHEMA).validate(english_json)

    portuguese = run_bob(
        repo, "--lang", "pt-BR", "check", "--config", "missing.yaml", "--gates", "nope"
    )
    portuguese_md = (repo / ".bob" / "report.md").read_text()
    portuguese_json = json.loads((repo / ".bob" / "report.json").read_text())

    assert portuguese.returncode == 4
    assert portuguese_json["churn"] == {"kind": "unavailable"}
    assert _section(portuguese_md, "## Rotatividade", "## Como reproduzir") == (
        "## Rotatividade\n\n"
        "Contagens de rotatividade indisponíveis. O código de saída não muda.\n\n"
    )
    assert "Difusão:" not in portuguese_md


def test_gates_churn_stays_a_missing_gate(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")

    result = run_bob(repo, "check", "--gates", "churn", "--base", "main")
    markdown = (repo / ".bob" / "report.md").read_text()
    payload = json.loads((repo / ".bob" / "report.json").read_text())

    assert result.returncode == 0, result.stderr
    assert payload["exit_code"] == 0
    assert payload["schema_version"] == 1
    assert payload["gates"] == [
        {
            "name": "churn",
            "status": "not_run",
            "reason": "gate not implemented in this slice",
        }
    ]
    assert payload["churn"]["kind"] == "measured"
    assert payload["churn"]["window_days"] == 90
    assert payload["churn"]["files"] == []
    assert payload["churn"]["hotspots"] == []
    assert payload["churn"]["diffusion"] == {"files": 0, "modules": 0}
    assert "- ⏭️ `churn`: not run (gate not implemented in this slice)" in markdown
    assert _section(markdown, "## Churn", "## How to reproduce") == (
        "## Churn\n"
        "\n"
        f"Window: 90 days ending {payload['churn']['ends_on']}.\n"
        "Diffusion: 0 files, 0 modules.\n"
        "\n"
        "No changed file inside the include paths.\n"
        "\n"
        "No changed function to score.\n"
        "\n"
    )
    Draft202012Validator(SCHEMA).validate(payload)


def test_relative_is_changed_lines_over_file_size(tmp_path: Path) -> None:
    repo = tmp_path / "ratio"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _commit(
        repo,
        "src/quarter.py",
        "one\ntwo\nthree\nfour\n",
        "quarter",
        _stamp("2020-01-15", "10:00:00"),
    )
    _commit(
        repo,
        "src/third.py",
        "one\ntwo\nthree\n",
        "third",
        _stamp("2020-01-15", "11:00:00"),
    )
    _commit(repo, "src/empty.py", "", "empty", _stamp("2020-01-15", "12:00:00"))
    _commit(repo, "src/accent.py", "café\nline\n", "accent", _stamp("2020-01-15", "12:30:00"))
    binary = repo / "src/binary.bin"
    binary.write_bytes(b"\xff\xfe")
    _git(repo, "add", "src/binary.bin")
    _git(repo, "commit", "-m", "binary", when=_stamp("2020-01-15", "13:00:00"))
    tip = _git(repo, "rev-parse", "HEAD")
    changed = _metric("src/quarter.py", "kept", 1, 5, True)

    section = measure_churn(
        repo,
        tip,
        90,
        {
            "src/accent.py": {1},
            "src/quarter.py": {1, 3},
            "src/third.py": {2},
            "src/empty.py": {1},
            "src/gone.py": {1},
            "src/binary.bin": {1},
        },
        ("src",),
        (changed,),
    )

    assert section == ChurnMeasured(
        ChurnWindow(90, date(2020, 1, 15)),
        (
            FileChurn("src/accent.py", 1, 0.5),
            FileChurn("src/binary.bin", 1, None),
            FileChurn("src/empty.py", 1, None),
            FileChurn("src/gone.py", 0, None),
            FileChurn("src/quarter.py", 1, 0.5),
            FileChurn("src/third.py", 1, 1 / 3),
        ),
        (Hotspot("src/quarter.py", "kept", 1, 5, 1),),
    )
    assert section.hotspots[0].hotspot == 5
    payload = to_json(_report(section))
    assert payload["churn"]["files"] == [
        {"path": "src/accent.py", "commits": 1, "relative": 0.5},
        {"path": "src/binary.bin", "commits": 1, "relative": None},
        {"path": "src/empty.py", "commits": 1, "relative": None},
        {"path": "src/gone.py", "commits": 0, "relative": None},
        {"path": "src/quarter.py", "commits": 1, "relative": 0.5},
        {"path": "src/third.py", "commits": 1, "relative": 1 / 3},
    ]
    Draft202012Validator(SCHEMA).validate(payload)
    english = to_markdown(_report(section), "en")
    assert "| `src/accent.py` | 1 | 0.5000 |" in english
    assert "| `src/quarter.py` | 1 | 0.5000 |" in english
    assert "| `src/third.py` | 1 | 0.3333 |" in english
    assert "| `src/empty.py` | 1 | n/a |" in english
    assert "| `src/gone.py` | 0 | n/a |" in english
    portuguese = to_markdown(_report(section), "pt-BR")
    assert "| `src/quarter.py` | 1 | 0.5000 |" in portuguese
    assert "| `src/empty.py` | 1 | n/d |" in portuguese
    assert "| `kept` | `src/quarter.py:1` | 5 | 1 | 5 |" in portuguese


def test_a_shallow_clone_or_a_git_log_error_keeps_the_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, tip = _boundary(tmp_path)
    assert run_check(repo, base="main", gates=["nope"], reproduce="bob check") == 0
    measured = json.loads((repo / ".bob" / "report.json").read_text())
    assert measured["exit_code"] == 0
    assert measured["churn"]["kind"] == "measured"
    assert measured["churn"]["files"] == [
        {"path": "src/a.py", "commits": 3, "relative": 1.0}
    ]

    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", "work", str(repo), str(shallow)],
        check=True,
        capture_output=True,
        text=True,
    )
    full_tip = run_check(repo, base=tip, gates=["nope"], reproduce="bob check")
    shallow_exit = run_check(shallow, base="HEAD", gates=["nope"], reproduce="bob check")
    shallow_payload = json.loads((shallow / ".bob" / "report.json").read_text())

    assert full_tip == 0
    assert shallow_exit == full_tip
    assert shallow_payload["exit_code"] == 0
    assert shallow_payload["schema_version"] == 1

    bindir = tmp_path / "bin"
    bindir.mkdir()
    wrapper = bindir / "git"
    wrapper.write_text(
        "#!/bin/sh\n"
        "PATH=${PATH#*:}\n"
        'if [ "$2" = log ]; then\n'
        "  echo 'fatal: git log failed' >&2\n"
        "  exit 1\n"
        "fi\n"
        'exec git "$@"\n'
    )
    wrapper.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")

    assert run_check(repo, base="main", gates=["nope"], reproduce="bob check") == 0
    broken = json.loads((repo / ".bob" / "report.json").read_text())
    broken_md = (repo / ".bob" / "report.md").read_text()
    assert broken["exit_code"] == measured["exit_code"]
    assert broken["churn"] == {"kind": "unavailable"}
    assert "Churn counts are unavailable. The exit code is unchanged." in broken_md
    Draft202012Validator(SCHEMA).validate(broken)


def _section(markdown: str, heading: str, footer: str) -> str:
    start = markdown.index(heading)
    end = markdown.index(footer)
    return markdown[start:end]


def _report(section: ChurnMeasured | ChurnUnavailable) -> Report:
    return Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2020-01-15T00:00:00+00:00",
        tool_versions={},
        gates=[],
        focus=[],
        top_crap=[],
        churn=section,
    )


def _metric(file: str, name: str, start: int, cc: int, changed: bool) -> FunctionMetric:
    return FunctionMetric(
        lang="python",
        module="ignored.dotted",
        name=name,
        file=file,
        start_line=start,
        end_line=start + 3,
        cc=cc,
        coverage=1.0,
        crap=float(cc),
        changed=changed,
    )


def _stamp(day: str, clock: str) -> str:
    parsed = datetime.strptime(f"{day} {clock}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=_OFFSET)
    return f"{int(parsed.timestamp())} -0300"


def _git(repo: Path, *args: str, when: str | None = None) -> str:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "bob-test"
    env["GIT_AUTHOR_EMAIL"] = "bob-test@example.com"
    env["GIT_COMMITTER_NAME"] = "bob-test"
    env["GIT_COMMITTER_EMAIL"] = "bob-test@example.com"
    if when is not None:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return completed.stdout.strip()


def _commit(repo: Path, path: str, text: str, message: str, when: str) -> None:
    file = repo / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text)
    _git(repo, "add", path)
    _git(repo, "commit", "-m", message, when=when)


def _boundary(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "boundary"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _commit(repo, "README", "base\n", "base", _stamp("2026-07-01", "00:00:00"))
    _git(repo, "checkout", "-b", "work")
    _commit(repo, "src/a.py", "before\n", "before", _stamp("2026-07-14", "23:59:59"))
    _commit(repo, "src/a.py", "start\n", "start", _stamp("2026-07-15", "00:00:00"))
    _commit(repo, "src/a.py", "endsec\n", "endsec", _stamp("2026-10-12", "23:59:59"))
    _commit(repo, "src/a.py", "next\n", "next", _stamp("2026-10-13", "00:00:00"))
    _commit(repo, "src/a.py", "head\n", "head", _stamp("2026-10-12", "12:00:00"))
    return repo, _git(repo, "rev-parse", "HEAD")


def _tree(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "tree"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    for path, text in (
        ("a.py", "root\n"),
        ("src/a.py", "a\n"),
        ("src/b.py", "b\n"),
        ("src2/a.py", "other\n"),
        ("tests/a.py", "test\n"),
    ):
        file = repo / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)
        _git(repo, "add", path)
    _git(repo, "commit", "-m", "files", when=_stamp("2020-01-15", "10:00:00"))
    _commit(repo, "src/b.py", "b again\n", "b again", _stamp("2020-01-15", "18:00:00"))
    return repo, _git(repo, "rev-parse", "HEAD")
