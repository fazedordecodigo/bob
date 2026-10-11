"""O erro do mutmut no relatório não pode ser o spinner cortado."""

from bob_quality.mutmut_tool import failure_text

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
