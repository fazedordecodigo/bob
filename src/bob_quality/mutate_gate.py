"""Braço do gate mutate. Python segue no cache; TypeScript volta um outcome."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from bob_quality.config import Config
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
    """Uma saída. `max_workers` e `baseline` ficam no braço Python."""
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
    noted, code = _note_skip(outcome.result, outcome.exit_code, skip)
    if noted is outcome.result:
        return outcome
    return replace(outcome, result=noted, exit_code=code)


def _note_skip(result: GateResult, code: int, skip: Text | None) -> tuple[GateResult, int]:
    if not skip:
        return result, code
    note = msg("probe.typescript_skipped", reason=skip)
    if result.status == "passed":
        return GateResult("mutate", "warn", note), code
    return GateResult("mutate", result.status, msg("probe.joined", first=result.reason, second=note)), code


def _merged_result(
    python: MutationOutcome,
    typescript: MutationOutcome,
    code: int,
    survivors: list[dict[str, object]],
    summary: dict[str, object],
) -> GateResult:
    if code == 3:
        mutants = ", ".join(
            f"{item['function']}@{item['file']}:{item['line']}"
            for item in survivors
            if not item.get("waiver")
        )
        return GateResult("mutate", "failed", msg("mutate.unwaived", mutants=mutants))
    if code in {2, 4}:
        return _hard_result(python, typescript, code)
    uncovered = summary["no_coverage"]
    total = int(uncovered["total"]) if isinstance(uncovered, dict) else 0
    return _passing_result(total)


def _hard_result(python: MutationOutcome, typescript: MutationOutcome, code: int) -> GateResult:
    sides = [side for side in (python, typescript) if side.exit_code == code]
    if len(sides) == 2:
        return GateResult(
            "mutate",
            sides[0].result.status,
            msg("probe.joined", first=sides[0].result.reason, second=sides[1].result.reason),
        )
    side = typescript if typescript.exit_code == code else python
    return GateResult("mutate", side.result.status, side.result.reason)


def _merge_no_coverage(parts: list[object]) -> dict[str, object]:
    totals: dict[tuple[str, str], int] = {}
    for part in parts:
        if not isinstance(part, dict):
            continue
        rows = part.get("functions")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = (str(row.get("file") or ""), str(row.get("function") or ""))
            totals[key] = totals.get(key, 0) + int(row.get("count") or 0)
    ordered = sorted(totals.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))
    functions = [
        {"file": file, "function": function, "count": count}
        for (file, function), count in ordered
    ]
    return {"total": sum(totals.values()), "functions": functions}


def _labels(outcome: MutationOutcome, key: str) -> list[object]:
    value = outcome.summary.get(key, [])
    if isinstance(value, list):
        return list(value)
    return []


def _summary_part(outcome: MutationOutcome, key: str) -> object:
    return outcome.summary.get(key)


def _worse(current: int, incoming: int) -> int:
    return incoming if incoming > current else current
