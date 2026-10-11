"""Custo fixo do gate: quais subprocessos rodam a suíte, e com qual ambiente."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from bob_quality import tools
from bob_quality.tools import run_coverage


def _record_runs(
    monkeypatch: pytest.MonkeyPatch, module: ModuleType, returncode: int
) -> list[tuple[list[str], dict[str, object]]]:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, returncode, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    return calls


def test_the_crap_coverage_run_skips_the_mutmut_dogfood(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "leak")
    monkeypatch.setenv("KEEP_ME", "yes")
    monkeypatch.setenv("BOB_SKIP_MUTMUT_DOGFOOD", "stale")
    calls = _record_runs(monkeypatch, tools, 1)
    rc = tmp_path / "coverage.rc"

    assert run_coverage(tmp_path, ["src"], tmp_path / "coverage.json", None) == 1

    [(args, kwargs)] = calls
    assert args == [sys.executable, "-m", "coverage", "run", "--rcfile", str(rc), "-m", "pytest"]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["stdin"] is subprocess.DEVNULL
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert env["BOB_SKIP_MUTMUT_DOGFOOD"] == "1"
    assert env["BOB_COVERAGE_RC"] == str(rc)
    assert env["KEEP_ME"] == "yes"
    assert not any(key.startswith("PYTEST_") for key in env)


@pytest.mark.parametrize("code", [0, 5])
def test_a_coverage_run_that_measured_exports_the_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    calls = _record_runs(monkeypatch, tools, code)
    json_path = tmp_path / "coverage.json"
    rc = str(tmp_path / "coverage.rc")

    assert run_coverage(tmp_path, ["src"], json_path, None) == code

    assert [(args, kwargs["cwd"]) for args, kwargs in calls[1:]] == [
        ([sys.executable, "-m", "coverage", "combine", "--rcfile", rc], tmp_path),
        (
            [sys.executable, "-m", "coverage", "json", "--rcfile", rc, "-o", str(json_path)],
            tmp_path,
        ),
    ]


def test_an_existing_coverage_file_is_only_exported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _record_runs(monkeypatch, tools, 0)
    data = tmp_path / ".coverage"
    json_path = tmp_path / "coverage.json"

    assert run_coverage(tmp_path, ["src"], json_path, data) == 0

    [(args, kwargs)] = calls
    assert args == [sys.executable, "-m", "coverage", "json", "-o", str(json_path)]
    assert kwargs["cwd"] == tmp_path
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert env["COVERAGE_FILE"] == str(data)
