"""Gate de segredos: o veredito sai da partição, não do exit do gitleaks."""

from __future__ import annotations

from dataclasses import dataclass

from bob_quality.diff import function_is_changed
from bob_quality.exit_codes import GATE_FAILED, PASSED
from bob_quality.messages import Text, msg
from bob_quality.models import SECRET_PREFIX, GateResult, SecretLedger, SecretRow


@dataclass(frozen=True)
class SecretsJudgment:
    """Resultado puro. Exit 4 não cabe aqui."""

    ledger: SecretLedger
    result: GateResult
    exit_code: int

    def __post_init__(self) -> None:
        blocked = bool(self.ledger.blocking)
        if self.result.name != "secrets":
            raise ValueError("secrets")
        if blocked:
            if self.exit_code != GATE_FAILED or self.result.status != "failed":
                raise ValueError("blocking rows are exit 1")
            return
        if self.exit_code != PASSED or self.result.status != "passed":
            raise ValueError("no blocking rows is exit 0")


def judge_secrets(
    findings: tuple[SecretRow, ...],
    diff_lines: dict[str, set[int]],
    waiver_ids: frozenset[str],
) -> SecretsJudgment:
    """Parte as linhas e tira o exit só de `blocking`."""
    applicable = {item for item in waiver_ids if item.startswith(SECRET_PREFIX)}
    blocking: list[SecretRow] = []
    outside: list[SecretRow] = []
    for row in _deduped(findings):
        if row.waiver_id() in applicable:
            continue
        if function_is_changed(row.file, row.line, row.line, diff_lines):
            blocking.append(row)
        else:
            outside.append(row)
    blocked = bool(blocking)
    return SecretsJudgment(
        SecretLedger(tuple(blocking), tuple(outside)),
        GateResult(
            "secrets",
            "failed" if blocked else "passed",
            _reason(len(blocking), len(outside)),
        ),
        GATE_FAILED if blocked else PASSED,
    )


def _deduped(findings: tuple[SecretRow, ...]) -> tuple[SecretRow, ...]:
    chosen: dict[str, SecretRow] = {}
    for row in findings:
        chosen.setdefault(row.waiver_id(), row)
    return tuple(sorted(chosen.values(), key=lambda row: (row.file, row.line, row.rule_id)))


def _reason(blocking: int, outside: int) -> Text | None:
    new = _count_reason(blocking, "secrets.new_one", "secrets.new_many")
    old = _count_reason(outside, "secrets.outside_one", "secrets.outside_many")
    if new is None:
        return old
    if old is None:
        return new
    return msg("probe.joined", first=new, second=old)


def _count_reason(count: int, one: str, many: str) -> Text | None:
    if count == 0:
        return None
    if count == 1:
        return msg(one)
    return msg(many, count=count)
