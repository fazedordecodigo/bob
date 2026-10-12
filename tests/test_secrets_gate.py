"""Gate de segredos: o diff decide o bloqueio e o relatório não leva o valor."""

from __future__ import annotations

from bob_quality.models import SecretRow
from bob_quality.secrets_gate import judge_secrets
from helpers import in_both


def test_judge_secrets_blocks_only_the_changed_unwaived_line() -> None:
    judgment = judge_secrets(
        (
            SecretRow("src/old.py", 2, "generic-api-key"),
            SecretRow("src/app.py", 12, "aws-access-token"),
        ),
        {"src/app.py": {12}},
        frozenset(),
    )

    assert judgment.exit_code == 1
    assert judgment.result.name == "secrets"
    assert judgment.result.status == "failed"
    assert in_both(judgment.result.reason) == (
        "1 new secret in the diff; 1 secret outside the diff",
        "1 segredo novo no diff; 1 segredo fora do diff",
    )
    assert judgment.ledger.blocking == (SecretRow("src/app.py", 12, "aws-access-token"),)
    assert judgment.ledger.outside_diff == (SecretRow("src/old.py", 2, "generic-api-key"),)


def test_judge_secrets_keeps_an_outside_row_without_failing() -> None:
    judgment = judge_secrets(
        (SecretRow("src/old.py", 2, "generic-api-key"),),
        {"src/app.py": {12}},
        frozenset(),
    )

    assert judgment.exit_code == 0
    assert judgment.result.name == "secrets"
    assert judgment.result.status == "passed"
    assert in_both(judgment.result.reason) == (
        "1 secret outside the diff",
        "1 segredo fora do diff",
    )
    assert judgment.ledger.blocking == ()
    assert judgment.ledger.outside_diff == (SecretRow("src/old.py", 2, "generic-api-key"),)


def test_judge_secrets_drops_only_a_whole_secret_waiver_id() -> None:
    row = SecretRow("src/app.py", 12, "aws-access-token")
    diff = {"src/app.py": {12}}

    waived = judge_secrets(
        (row,),
        diff,
        frozenset({"secret:aws-access-token:src/app.py:12"}),
    )
    mutant = judge_secrets((row,), diff, frozenset({"app.billing.x_charge__mutmut_2"}))
    sast = judge_secrets(
        (row,),
        diff,
        frozenset({"sast:bandit:hardcoded-password:src/app.py:12"}),
    )

    assert waived.exit_code == 0
    assert waived.result.status == "passed"
    assert waived.result.reason is None
    assert waived.ledger.blocking == ()
    assert waived.ledger.outside_diff == ()
    assert mutant.exit_code == 1
    assert mutant.result.status == "failed"
    assert mutant.ledger.blocking == (row,)
    assert sast.exit_code == 1
    assert sast.result.status == "failed"
    assert sast.ledger.blocking == (row,)
