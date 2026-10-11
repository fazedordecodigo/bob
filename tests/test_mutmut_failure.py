"""O erro do mutmut no relatório não pode ser o spinner cortado."""

import subprocess
from pathlib import Path

import pytest

from bob_quality import mutmut_tool
from bob_quality.mutmut_tool import failure_text
from bob_quality.tools import ToolError

SPINNER = "⠋ Generating mutants\r⠙ Generating mutants\r⠹ Generating mutants\r"


def test_mutmut_failure_reports_the_error_after_the_spinner() -> None:
    stdout = SPINNER * 40 + (
        "\nTraceback (most recent call last):\n"
        "AssertionError: filtered mutants\n"
        "failed to collect stats. runner returned 1\n"
    )

    text = failure_text(stdout, "")

    assert "failed to collect stats. runner returned 1" in text
    assert "AssertionError: filtered mutants" in text
    assert "⠋" not in text
    assert "Generating mutants" not in text


def test_failure_text_keeps_only_the_error_lines() -> None:
    stdout = "\n".join(
        [
            "",
            "⠋ Generating mutants",
            "Generating mutants",
            "⠋ leaked",
            "⠋⠙",
            "AssertionError: filtered mutants",
            "failed to collect stats. runner returned 1",
        ]
    )

    assert failure_text(stdout, "") == (
        "AssertionError: filtered mutants failed to collect stats. runner returned 1"
    )


def test_failure_text_truncates_to_the_last_400_characters() -> None:
    exact = "A" * 400
    assert failure_text(exact, "") == exact

    longer = "B" * 401
    assert failure_text(longer, "") == "…" + ("B" * 400)


def test_missing_mutmut_is_a_missing_tool(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def missing(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(2, "No such file", "python")

    monkeypatch.setattr(mutmut_tool.subprocess, "run", missing)

    with pytest.raises(ToolError, match=r"ferramenta ausente: .+python"):
        mutmut_tool.mutmut_results(tmp_path)


def test_mutmut_subprocess_timeout_is_a_tool_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def expired(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd="mutmut", timeout=180)

    monkeypatch.setattr(mutmut_tool.subprocess, "run", expired)

    with pytest.raises(ToolError) as caught:
        mutmut_tool.run_mutmut(tmp_path, ["app.weak.x_classify__mutmut*"], 1)

    assert str(caught.value) == "mutmut excedeu o tempo limite"


def test_nonzero_mutmut_keeps_the_error_after_the_spinner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def failed(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args,
            1,
            stdout=SPINNER,
            stderr="failed to collect stats. runner returned 1\n",
        )

    monkeypatch.setattr(mutmut_tool.subprocess, "run", failed)

    with pytest.raises(ToolError) as caught:
        mutmut_tool.mutmut_show(tmp_path, "app.weak.x_classify__mutmut_1")

    assert str(caught.value) == "failed to collect stats. runner returned 1"
    assert "⠋" not in str(caught.value)


def test_nothing_matches_is_its_own_tool_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def failed(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 2, stdout="nothing matches\n", stderr="")

    monkeypatch.setattr(mutmut_tool.subprocess, "run", failed)

    with pytest.raises(ToolError) as caught:
        mutmut_tool.mutmut_results(tmp_path)

    assert str(caught.value) == "nothing matches"


def test_empty_mutmut_failure_names_the_exit_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def failed(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 7, stdout="", stderr="")

    monkeypatch.setattr(mutmut_tool.subprocess, "run", failed)

    with pytest.raises(ToolError) as caught:
        mutmut_tool.mutmut_results(tmp_path)

    assert str(caught.value) == "exit 7"
