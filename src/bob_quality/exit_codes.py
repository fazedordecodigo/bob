"""Exit codes da CLI, conforme a SPEC."""

PASSED = 0
GATE_FAILED = 1
BASELINE_BROKEN = 2
UNWAIVED_SURVIVOR = 3
CONFIG_OR_TOOL = 4


def pytest_passed(code: int) -> bool:
    """A suíte passou. Exit 5 do pytest (nenhum teste coletado) também passa."""
    return code in {0, 5}
