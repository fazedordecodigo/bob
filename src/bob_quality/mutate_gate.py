from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from bob_quality.config import Config
from bob_quality.exit_codes import PASSED, UNWAIVED_SURVIVOR
from bob_quality.messages import Text, msg
from bob_quality.models import GateResult
from bob_quality.mutate import MutationOutcome, _passing_result, run_mutation_gate
from bob_quality.stryker_gate import run_typescript_mutation


def run_mutate_gate(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    out_dir: Path,
    max_workers: int | None = None,
    baseline: int | None = None,
) -> MutationOutcome:
    python = None
    if "python" in config.languages:
        python = run_mutation_gate(
            cwd,
            config,
            diff_lines,
            out_dir,
            max_workers=max_workers,
            baseline=baseline,
        )
    typescript = None
    skip = None
    if "typescript" in config.languages:
        typescript, skip = run_typescript_mutation(
            cwd,
            config,
            diff_lines,
            out_dir,
            python_measured="python" in config.languages,
        )
    return _merge(python, typescript, skip)


def _merge(
    python: MutationOutcome | None,
    typescript: MutationOutcome | None,
    skip: Text | None,
) -> MutationOutcome:
    if typescript is None:
        return _with_skip(python, skip)
    if python is None:
        return typescript
    code = _worse(python.exit_code, typescript.exit_code)
    survivors = [*python.survivors, *typescript.survivors]
    summary = {
        "remutated": [*_labels(python, "remutated"), *_labels(typescript, "remutated")],
        "reused": [*_labels(python, "reused"), *_labels(typescript, "reused")],
        "no_coverage": _merge_no_coverage(
            [_summary_part(python, "no_coverage"), _summary_part(typescript, "no_coverage")]
        ),
    }
    code = _coverage_exit(code, summary)
    versions = dict(python.versions)
    versions.update(typescript.versions)
    merged = MutationOutcome(
        result=_merged_result(python, typescript, code, survivors, summary),
        exit_code=code,
        versions=versions,
        waivers=python.waivers,
        survivors=survivors,
        summary=summary,
    )
    return _with_skip(merged, skip)


def _with_skip(outcome: MutationOutcome | None, skip: Text | None) -> MutationOutcome:
    if outcome is None:
        raise RuntimeError("mutate gate had neither language")
    noted = _note_skip(outcome.result, skip)
    if noted is outcome.result:
        return outcome
    return replace(outcome, result=noted)


def _note_skip(result: GateResult, skip: Text | None) -> GateResult:
    if not skip:
        return result
    note = msg("probe.typescript_skipped", reason=skip)
    if result.status == "passed":
        return GateResult("mutate", "warn", note)
    return GateResult("mutate", result.status, msg("probe.joined", first=result.reason, second=note))


def _coverage_exit(code: int, summary: dict[str, object]) -> int:
    if code != PASSED:
        return code
    uncovered = summary.get("no_coverage")
    if not isinstance(uncovered, dict):
        return code
    total = uncovered.get("total")
    if isinstance(total, int) and total > 0:
        return UNWAIVED_SURVIVOR
    return code


def _merged_result(
    python: MutationOutcome,
    typescript: MutationOutcome,
    code: int,
    survivors: list[dict[str, object]],
    summary: dict[str, object],
) -> GateResult:
    if code == UNWAIVED_SURVIVOR and _has_unwaived(survivors):
        return _unwaived_result(survivors)
    if code in {2, 4}:
        return _hard_result(python, typescript, code)
    uncovered = summary["no_coverage"]
    return _passing_result(int(uncovered["total"]))


def _has_unwaived(survivors: list[dict[str, object]]) -> bool:
    return any(not item.get("waiver") for item in survivors)


def _unwaived_result(survivors: list[dict[str, object]]) -> GateResult:
    mutants = ", ".join(_unwaived_label(item) for item in survivors if not item.get("waiver"))
    return GateResult("mutate", "failed", msg("mutate.unwaived", mutants=mutants))


def _unwaived_label(item: dict[str, object]) -> str:
    return f"{item['function']}@{item['file']}:{item['line']}"


def _hard_result(python: MutationOutcome, typescript: MutationOutcome, code: int) -> GateResult:
    sides = [side for side in (python, typescript) if side.exit_code == code]
    if len(sides) == 2:
        return _joined_hard(sides[0], sides[1])
    return _one_hard(typescript if typescript.exit_code == code else python)


def _joined_hard(first: MutationOutcome, second: MutationOutcome) -> GateResult:
    return GateResult(
        "mutate",
        first.result.status,
        msg("probe.joined", first=first.result.reason, second=second.result.reason),
    )


def _one_hard(side: MutationOutcome) -> GateResult:
    return GateResult("mutate", side.result.status, side.result.reason)


def _merge_no_coverage(parts: list[object]) -> dict[str, object]:
    totals: dict[tuple[str, str], int] = {}
    for part in parts:
        _add_coverage_part(totals, part)
    return _coverage_body(totals)


def _add_coverage_part(totals: dict[tuple[str, str], int], part: object) -> None:
    if not isinstance(part, dict):
        return
    rows = part.get("functions")
    if not isinstance(rows, list):
        return
    for row in rows:
        _add_coverage_row(totals, row)


def _add_coverage_row(totals: dict[tuple[str, str], int], row: object) -> None:
    if not isinstance(row, dict):
        return
    key = (_coverage_text(row.get("file")), _coverage_text(row.get("function")))
    totals[key] = totals.get(key, 0) + _coverage_count(row.get("count"))


def _coverage_text(value: object) -> str:
    return str(value or "")


def _coverage_count(value: object) -> int:
    return int(value or 0)


def _coverage_body(totals: dict[tuple[str, str], int]) -> dict[str, object]:
    ordered = sorted(totals, key=lambda key: (-totals[key], key[0], key[1]))
    functions = [
        {"file": file, "function": function, "count": totals[(file, function)]}
        for file, function in ordered
    ]
    return {"total": sum(totals.values()), "functions": functions}


def _labels(outcome: MutationOutcome, key: str) -> list[object]:
    value = outcome.summary[key]
    if isinstance(value, list):
        return list(value)
    return []


def _summary_part(outcome: MutationOutcome, key: str) -> object:
    return outcome.summary.get(key)


def _worse(current: int, incoming: int) -> int:
    return incoming if incoming > current else current
