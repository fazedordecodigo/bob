"""Gate de mutação diferencial em Python (mutmut) e cache de funções."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from bob_quality.adapters.lizard import LizardParseError, parse_lizard_csv
from bob_quality.adapters.mutmut import MutmutParseError, mutants_from_raw, mutmut_id_prefix
from bob_quality.config import Config
from bob_quality.diff import function_is_changed
from bob_quality.exit_codes import BASELINE_BROKEN, CONFIG_OR_TOOL, PASSED, UNWAIVED_SURVIVOR
from bob_quality.models import CyclomaticFunction, GateResult, Mutant, MutantStatus
from bob_quality.mutmut_tool import (
    mutmut_results,
    mutmut_show,
    mutmut_version,
    pytest_exit_code,
    run_mutmut,
)
from bob_quality.probe import relative_path
from bob_quality.tools import ToolError, run_lizard_csv
from bob_quality.waivers import Waiver, WaiverError, apply_waivers, load_waivers

CACHE_NAME = "mutation-cache.json"


@dataclass
class MutationOutcome:
    result: GateResult
    exit_code: int
    versions: dict[str, str]
    waivers: list[dict[str, object]]
    survivors: list[dict[str, object]]
    summary: dict[str, object]


def run_mutation_gate(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    out_dir: Path,
    max_workers: int | None = None,
) -> MutationOutcome:
    versions: dict[str, str] = {}
    try:
        versions["mutmut"] = mutmut_version()
    except ToolError as exc:
        return _outcome(
            GateResult("mutate", "not_run", f"ferramenta ausente: {exc}"),
            CONFIG_OR_TOOL,
            versions,
        )
    try:
        waivers = load_waivers(cwd)
    except WaiverError as exc:
        return _outcome(GateResult("mutate", "not_run", str(exc)), CONFIG_OR_TOOL, versions)
    waiver_rows = [item.as_dict() for item in waivers]

    try:
        measured = _measured_functions(cwd, config)
    except (ToolError, OSError, LizardParseError) as exc:
        return _outcome(
            GateResult("mutate", "not_run", str(exc)),
            CONFIG_OR_TOOL,
            versions,
            waivers=waiver_rows,
        )

    cache_path = out_dir / CACHE_NAME
    try:
        cached = _read_cache(cache_path)
    except (OSError, json.JSONDecodeError) as exc:
        return _outcome(
            GateResult("mutate", "not_run", f"cache de mutação inválido: {exc}"),
            CONFIG_OR_TOOL,
            versions,
            waivers=waiver_rows,
        )
    remutate, reuse = _split_functions(measured, diff_lines, cached, cwd, waivers)
    reused_mutants = apply_waivers(_mutants_from_cache(reuse), waivers)
    remutated_labels = [f"{item.file}::{item.name}" for item in remutate]
    reused_labels = [key for key, _entry in reuse]

    if not remutate:
        body = {key: entry for key, entry in reuse}
        _write_cache(cache_path, body)
        return _finish(reused_mutants, remutated_labels, reused_labels, versions, waiver_rows)

    if pytest_exit_code(cwd) not in {0, 5}:
        return _outcome(
            GateResult("mutate", "not_run", "testes da baseline falharam antes de medir"),
            BASELINE_BROKEN,
            versions,
            waivers=waiver_rows,
        )

    cleanup = _install_mutmut_config(cwd, config.include)
    try:
        patterns = [f"{mutmut_id_prefix(item.file, item.name)}*" for item in remutate]
        try:
            run_mutmut(cwd, patterns, max_workers)
            raw_results = mutmut_results(cwd)
        except ToolError as exc:
            return _outcome(
                GateResult("mutate", "not_run", str(exc)),
                CONFIG_OR_TOOL,
                versions,
                waivers=waiver_rows,
            )
        try:
            parsed = mutants_from_raw(raw_results, {})
        except MutmutParseError as exc:
            return _outcome(
                GateResult("mutate", "not_run", str(exc)),
                CONFIG_OR_TOOL,
                versions,
                waivers=waiver_rows,
            )
        selected_ids = [item.id for item in parsed if _belongs(item, remutate)]
        shows: dict[str, str] = {}
        for mutant_id in selected_ids:
            try:
                shows[mutant_id] = mutmut_show(cwd, mutant_id)
            except ToolError:
                continue
        try:
            parsed = mutants_from_raw(raw_results, shows)
        except MutmutParseError as exc:
            return _outcome(
                GateResult("mutate", "not_run", str(exc)),
                CONFIG_OR_TOOL,
                versions,
                waivers=waiver_rows,
            )
    finally:
        cleanup()

    fresh = apply_waivers([item for item in parsed if _belongs(item, remutate)], waivers)
    body = {key: entry for key, entry in reuse}
    body.update(_cache_body(cwd, remutate, fresh))
    _write_cache(cache_path, body)
    return _finish(fresh + reused_mutants, remutated_labels, reused_labels, versions, waiver_rows)


def _split_functions(
    measured: list[CyclomaticFunction],
    diff_lines: dict[str, set[int]],
    cache: dict[str, dict[str, object]],
    cwd: Path,
    waivers: list[Waiver],
) -> tuple[list[CyclomaticFunction], list[tuple[str, dict[str, object]]]]:
    by_key = {f"{item.file}::{item.name}": item for item in measured}
    keys: set[str] = set()
    for item in measured:
        if function_is_changed(item.file, item.start_line, item.end_line, diff_lines):
            keys.add(f"{item.file}::{item.name}")
    for key, entry in cache.items():
        if key in by_key and _has_unwaived_survivor(entry, waivers):
            keys.add(key)
    remutate: list[CyclomaticFunction] = []
    reuse: list[tuple[str, dict[str, object]]] = []
    for key in sorted(keys):
        item = by_key[key]
        entry = cache.get(key)
        digest = _function_hash(cwd, item.file, item.start_line, item.end_line)
        if (
            not isinstance(entry, dict)
            or entry.get("hash") != digest
            or _has_unwaived_survivor(entry, waivers)
        ):
            remutate.append(item)
            continue
        reuse.append((key, entry))
    return remutate, reuse


def _has_unwaived_survivor(entry: dict[str, object], waivers: list[Waiver]) -> bool:
    mutants = entry.get("mutants")
    if not isinstance(mutants, list):
        return False
    rows = [item for item in mutants if isinstance(item, dict) and isinstance(item.get("id"), str)]
    current = apply_waivers([_mutant_from_row(item) for item in rows], waivers)
    return any(item.status == "survived" and not item.waiver for item in current)


def _read_cache(path: Path) -> dict[str, dict[str, object]]:
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text())
    functions = raw.get("functions") if isinstance(raw, dict) else None
    if not isinstance(functions, dict):
        return {}
    return {str(key): value for key, value in functions.items() if isinstance(value, dict)}


def _mutants_from_cache(reuse: list[tuple[str, dict[str, object]]]) -> list[Mutant]:
    mutants: list[Mutant] = []
    for _key, entry in reuse:
        rows = entry.get("mutants")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("id"), str):
                mutants.append(_mutant_from_row(row))
    return mutants


def _mutant_from_row(row: dict[str, object]) -> Mutant:
    waiver = row.get("waiver")
    return Mutant(
        id=str(row["id"]),
        function=str(row.get("function") or ""),
        file=str(row.get("file") or ""),
        line=int(row.get("line") or 0),
        operator=str(row.get("operator") or ""),
        status=_status_from_cache(row.get("status")),
        waiver=waiver if isinstance(waiver, str) and waiver else None,
    )


def _status_from_cache(value: object) -> MutantStatus:
    if value == "killed":
        return "killed"
    if value == "timeout":
        return "timeout"
    if value == "no_coverage":
        return "no_coverage"
    return "survived"


def _finish(
    mutants: list[Mutant],
    remutated: list[str],
    reused: list[str],
    versions: dict[str, str],
    waiver_rows: list[dict[str, object]],
) -> MutationOutcome:
    visible = [item for item in mutants if item.status == "survived"]
    unwaived = [item for item in visible if not item.waiver]
    rows = [_mutant_row(item) for item in visible]
    summary = {"remutated": remutated, "reused": reused}
    if not unwaived:
        return _outcome(
            GateResult("mutate", "passed", None),
            PASSED,
            versions,
            waivers=waiver_rows,
            survivors=rows,
            summary=summary,
        )
    reason = "sobrevivente sem waiver: " + ", ".join(
        f"{item.function}@{item.file}:{item.line}" for item in unwaived
    )
    return _outcome(
        GateResult("mutate", "failed", reason),
        UNWAIVED_SURVIVOR,
        versions,
        waivers=waiver_rows,
        survivors=rows,
        summary=summary,
    )


def focus_with_survivors(
    focus: list[dict[str, object]], survivors: list[dict[str, object]]
) -> list[dict[str, object]]:
    scores: dict[str, float] = {str(item["file"]): float(item["risk"]) for item in focus}
    for item in survivors:
        file = str(item["file"])
        if not file:
            continue
        bump = 0.0 if item.get("waiver") else 100.0
        scores[file] = scores.get(file, 0.0) + bump
    ordered = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    return [{"file": file, "risk": risk} for file, risk in ordered]


def _measured_functions(cwd: Path, config: Config) -> list[CyclomaticFunction]:
    raw = run_lizard_csv(cwd, config.include, config.exclude)
    functions = parse_lizard_csv(raw)
    measured: list[CyclomaticFunction] = []
    for item in functions:
        measured.append(
            CyclomaticFunction(
                file=relative_path(cwd, item.file),
                name=item.name,
                start_line=item.start_line,
                end_line=item.end_line,
                cc=item.cc,
            )
        )
    return measured


def _belongs(mutant: Mutant, functions: list[CyclomaticFunction]) -> bool:
    return any(mutant.id.startswith(mutmut_id_prefix(item.file, item.name)) for item in functions)


def _cache_body(
    cwd: Path, functions: list[CyclomaticFunction], mutants: list[Mutant]
) -> dict[str, object]:
    body: dict[str, object] = {}
    for item in functions:
        prefix = mutmut_id_prefix(item.file, item.name)
        own = [mutant for mutant in mutants if mutant.id.startswith(prefix)]
        key = f"{item.file}::{item.name}"
        body[key] = {
            "hash": _function_hash(cwd, item.file, item.start_line, item.end_line),
            "file": item.file,
            "name": item.name,
            "start_line": item.start_line,
            "end_line": item.end_line,
            "mutants": [_mutant_row(mutant) for mutant in own],
        }
    return body


def _function_hash(cwd: Path, file: str, start: int, end: int) -> str:
    lines = (cwd / file).read_text().splitlines()
    text = "\n".join(lines[start - 1 : end])
    return hashlib.sha256(text.encode()).hexdigest()


def _write_cache(path: Path, functions: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"functions": functions}
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _mutant_row(mutant: Mutant) -> dict[str, object]:
    return {
        "id": mutant.id,
        "function": mutant.function,
        "file": mutant.file,
        "line": mutant.line,
        "operator": mutant.operator,
        "status": mutant.status,
        "waiver": mutant.waiver,
    }


def _install_mutmut_config(cwd: Path, source_paths: list[str]) -> Callable[[], None]:
    if _has_mutmut_config(cwd):
        return lambda: None
    setup = cwd / "setup.cfg"
    created = not setup.exists()
    original = setup.read_text() if setup.exists() else None
    paths = source_paths or ["src"]
    lines = ["[mutmut]", "source_paths ="]
    lines.extend(f"    {path}" for path in paths)
    lines.extend(["also_copy =", "    pytest.ini", ""])
    block = "\n".join(lines)
    if original:
        setup.write_text(original.rstrip() + "\n\n" + block)
    else:
        setup.write_text(block)

    def cleanup() -> None:
        if created:
            setup.unlink(missing_ok=True)
        elif original is not None:
            setup.write_text(original)

    return cleanup


def _has_mutmut_config(cwd: Path) -> bool:
    pyproject = cwd / "pyproject.toml"
    if pyproject.is_file() and "[tool.mutmut]" in pyproject.read_text():
        return True
    setup = cwd / "setup.cfg"
    return setup.is_file() and "[mutmut]" in setup.read_text()


def _outcome(
    result: GateResult,
    exit_code: int,
    versions: dict[str, str],
    waivers: list[dict[str, object]] | None = None,
    survivors: list[dict[str, object]] | None = None,
    summary: dict[str, object] | None = None,
) -> MutationOutcome:
    return MutationOutcome(
        result=result,
        exit_code=exit_code,
        versions=versions,
        waivers=waivers or [],
        survivors=survivors or [],
        summary=summary or {"remutated": [], "reused": []},
    )
