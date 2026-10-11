"""O erro do mutmut no relatório não pode ser o spinner cortado."""

import subprocess
from pathlib import Path

import pytest

from bob_quality import mutmut_tool
from bob_quality.mutmut_tool import failure_text
from bob_quality.tools import ToolError

SPINNER = "⠋ Generating mutants\r⠙ Generating mutants\r⠹ Generating mutants\r"
# Fim da saída de `mutmut run` 3.8 quando o pytest recusa o addopts.
BAD_ADDOPTS_STDOUT = (
    "    done in 29ms (2 files mutated, 0 ignored, 0 unmodified)\n\n"
    "⠧ Running stats     \n⠇ Running stats\n⠏ Running stats\n"
)
BAD_ADDOPTS_STDERR = (
    "Traceback (most recent call last):\n"
    '  File "<frozen runpy>", line 198, in _run_module_as_main\n'
    '  File "/tmp/venv/lib/python3.12/site-packages/mutmut/runners/harness.py", line 136,'
    " in execute_pytest\n"
    "    raise BadTestExecutionCommandsException(params)\n"
    "mutmut.runners.harness.BadTestExecutionCommandsException: Failed to run pytest with args:"
    " ['--no-such-flag', '--rootdir=.']. If your config sets debug=true, the original pytest"
    " error should be above.\n"
)
CHAINED = (
    "⠇ Running statsTraceback (most recent call last):\n"
    '  File "tests/test_safe.py", line 9, in test_add\n'
    "    raise KeyError('a')\n"
    "KeyError: 'a'\n\n"
    "During handling of the above exception, another exception occurred:\n\n"
    "Traceback (most recent call last):\n"
    '  File "tests/test_safe.py", line 11, in test_add\n'
    "    EXPECTED.read_text()\n"
    "FileNotFoundError: [Errno 2] No such file or directory: 'expected.txt'\n"
    "1 failed in 0.01s\n"
    "failed to collect stats. runner returned 1\n"
)


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


def _failing_mutmut(monkeypatch: pytest.MonkeyPatch, stdout: str, stderr: str) -> None:
    def failed(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(mutmut_tool.subprocess, "run", failed)


def test_a_mutmut_crash_reports_only_the_final_exception_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _failing_mutmut(monkeypatch, BAD_ADDOPTS_STDOUT, BAD_ADDOPTS_STDERR)

    with pytest.raises(ToolError) as caught:
        mutmut_tool.run_mutmut(tmp_path, ["app.safe.x_add__mutmut*"], None)

    assert str(caught.value) == (
        "mutmut.runners.harness.BadTestExecutionCommandsException: Failed to run pytest with args:"
        " ['--no-such-flag', '--rootdir=.']. If your config sets debug=true, the original pytest"
        " error should be above."
    )


def test_a_chained_traceback_glued_to_the_spinner_reports_the_last_exception(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _failing_mutmut(monkeypatch, CHAINED, "")

    with pytest.raises(ToolError) as caught:
        mutmut_tool.run_mutmut(tmp_path, ["app.safe.x_add__mutmut*"], None)

    assert str(caught.value) == (
        "a suíte passa no repositório e falha dentro de mutants/;"
        " confira also_copy e a configuração [mutmut]:"
        " FileNotFoundError: [Errno 2] No such file or directory: 'expected.txt'"
    )


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

    assert str(caught.value) == (
        "a suíte passa no repositório e falha dentro de mutants/;"
        " confira also_copy e a configuração [mutmut]: failed to collect stats. runner returned 1"
    )


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
