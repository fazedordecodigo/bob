"""Gate de cheiros em testes alterados. A contribuição de exit é sempre 0."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

from bob_quality.config import Config, SourceLanguage
from bob_quality.messages import Text, msg
from bob_quality.models import GateResult, TestSmell
from bob_quality.waivers import Waiver, load_waivers

WarningContribution = Literal[0]


@dataclass(frozen=True)
class LanguageMeasured:
    language: SourceLanguage
    findings: tuple[TestSmell, ...]
    eslint_version: str | None = None


@dataclass(frozen=True)
class LanguageBroken:
    language: Literal["typescript"]
    detail: Text
    eslint_version: str | None = None


@dataclass(frozen=True)
class LanguageSkipped:
    language: Literal["typescript"]


LanguageOutcome = LanguageMeasured | LanguageBroken | LanguageSkipped


def waiver_id(smell: TestSmell) -> str:
    return f"tests:{smell.file}:{smell.line}:{smell.rule}"


def test_smell(
    file: str,
    line: int,
    rule: str,
    changed: frozenset[int],
) -> TestSmell | None:
    if line not in changed:
        return None
    return TestSmell(file, line, rule)


def apply_test_waivers(
    findings: tuple[TestSmell, ...],
    waivers: Sequence[Waiver],
) -> tuple[TestSmell, ...]:
    reasons = {item.id: item.reason for item in waivers}
    applied: list[TestSmell] = []
    for smell in findings:
        reason = reasons.get(waiver_id(smell))
        if reason is None:
            applied.append(smell)
            continue
        applied.append(TestSmell(smell.file, smell.line, smell.rule, reason))
    return tuple(applied)


def fold_outcomes(
    outcomes: tuple[LanguageOutcome, ...],
) -> tuple[GateResult, tuple[TestSmell, ...]]:
    measured: list[LanguageMeasured] = []
    broken: list[LanguageBroken] = []
    for outcome in outcomes:
        if isinstance(outcome, LanguageMeasured):
            measured.append(outcome)
            continue
        if isinstance(outcome, LanguageBroken):
            broken.append(outcome)
            continue
        if isinstance(outcome, LanguageSkipped):
            continue
        raise AssertionError(type(outcome))
    detail = _join_details(tuple(item.detail for item in broken))
    if not measured:
        reason = detail if detail is not None else msg("test_smells.nothing_measured")
        return GateResult("test_smells", "not_run", reason), ()
    findings = tuple(
        sorted(
            (smell for item in measured for smell in item.findings),
            key=_by_location,
        )
    )
    unwaived = sum(1 for smell in findings if smell.waiver is None)
    if unwaived == 0:
        return GateResult("test_smells", "passed", detail), findings
    count = msg(_count_key(unwaived), count=unwaived)
    reason = count if detail is None else msg("test_smells.with_detail", head=count, detail=detail)
    return GateResult("test_smells", "warn", reason), findings


def run_test_smells_gate(
    cwd: Path,
    config: Config,
    diff_lines: Mapping[str, set[int]],
) -> tuple[GateResult, tuple[TestSmell, ...], WarningContribution, dict[str, str]]:
    waivers = load_waivers(cwd)
    outcomes = _outcomes(config, cwd, diff_lines)
    result, findings = fold_outcomes(_waived(outcomes, waivers))
    return result, findings, 0, _versions(outcomes)


def measure_python(
    _cwd: Path,
    _diff_lines: Mapping[str, set[int]],
) -> LanguageMeasured:
    return LanguageMeasured("python", ())


def measure_typescript(
    _cwd: Path,
    _diff_lines: Mapping[str, set[int]],
) -> LanguageOutcome:
    return LanguageSkipped("typescript")


def _outcomes(
    config: Config,
    cwd: Path,
    diff_lines: Mapping[str, set[int]],
) -> tuple[LanguageOutcome, ...]:
    found: list[LanguageOutcome] = []
    for language in config.languages:
        if language == "python":
            found.append(measure_python(cwd, diff_lines))
            continue
        if language == "typescript":
            found.append(measure_typescript(cwd, diff_lines))
            continue
        raise AssertionError(language)
    return tuple(found)


def _waived(
    outcomes: tuple[LanguageOutcome, ...],
    waivers: Sequence[Waiver],
) -> tuple[LanguageOutcome, ...]:
    return tuple(_waive_one(outcome, waivers) for outcome in outcomes)


def _waive_one(outcome: LanguageOutcome, waivers: Sequence[Waiver]) -> LanguageOutcome:
    if isinstance(outcome, LanguageMeasured):
        return LanguageMeasured(
            outcome.language,
            apply_test_waivers(outcome.findings, waivers),
            outcome.eslint_version,
        )
    if isinstance(outcome, (LanguageBroken, LanguageSkipped)):
        return outcome
    raise AssertionError(type(outcome))


def _versions(outcomes: tuple[LanguageOutcome, ...]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for outcome in outcomes:
        version = _eslint_version(outcome)
        if version is not None:
            versions["eslint"] = version
    return versions


def _eslint_version(outcome: LanguageOutcome) -> str | None:
    if isinstance(outcome, LanguageSkipped):
        return None
    if isinstance(outcome, (LanguageMeasured, LanguageBroken)):
        return outcome.eslint_version
    raise AssertionError(type(outcome))


def _join_details(details: tuple[Text, ...]) -> Text | None:
    if not details:
        return None
    joined = details[0]
    for detail in details[1:]:
        joined = msg("probe.joined", first=joined, second=detail)
    return joined


def _count_key(unwaived: int) -> str:
    if unwaived == 1:
        return "test_smells.one"
    return "test_smells.many"


def _by_location(smell: TestSmell) -> tuple[str, int, str]:
    return smell.file, smell.line, smell.rule
