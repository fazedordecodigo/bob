"""Gate de mutação diferencial em Python (mutmut) e cache de funções."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from bob_quality.adapters.lizard import LizardParseError, parse_lizard_csv
from bob_quality.adapters.mutmut import (
    MutmutParseError,
    ids_for_show,
    mutants_from_raw,
    mutation_targets,
    mutmut_id_prefix,
    mutmut_run_patterns,
)
from bob_quality.config import Config
from bob_quality.diff import function_is_changed
from bob_quality.exit_codes import (
    BASELINE_BROKEN,
    CONFIG_OR_TOOL,
    PASSED,
    UNWAIVED_SURVIVOR,
    pytest_passed,
)
from bob_quality.messages import Text, msg, reason
from bob_quality.models import CyclomaticFunction, GateResult, Mutant, MutantStatus
from bob_quality.mutmut_tool import (
    mutmut_results,
    mutmut_show,
    mutmut_version,
    pytest_exit_code,
    run_mutmut,
)
from bob_quality.probe import relative_path
from bob_quality.suite_fingerprint import suite_fingerprint
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
    baseline: int | None = None,
) -> MutationOutcome:
    """`baseline` é o exit do pytest que o gate crap já rodou. Sem ele, o gate roda o pytest."""
    prepared = _prepare_mutation(cwd, config, diff_lines, out_dir)
    if isinstance(prepared, MutationOutcome):
        return prepared
    versions, waivers, waiver_rows, cache, plan = prepared
    if not plan.remutate:
        _write_cache(cache, _publish_body(plan, {}))
        return _finish(
            plan.reused_mutants,
            diff_lines,
            plan.remutated_labels,
            plan.reused_labels,
            versions,
            waiver_rows,
        )
    blocked = _baseline_outcome(cwd, baseline, versions, waiver_rows)
    if blocked is not None:
        return blocked
    fresh = _collect_fresh(cwd, config, plan.remutate, max_workers, versions, waiver_rows, waivers)
    if isinstance(fresh, MutationOutcome):
        return fresh
    _write_cache(cache, _publish_body(plan, _cache_body(cwd, plan.remutate, fresh)))
    return _finish(
        fresh + plan.reused_mutants,
        diff_lines,
        plan.remutated_labels,
        plan.reused_labels,
        versions,
        waiver_rows,
    )


@dataclass(frozen=True)
class _Cache:
    path: Path
    key: dict[str, str]


@dataclass(frozen=True)
class _CacheView:
    held: dict[str, dict[str, object]]
    may_reuse: bool


class _CacheLineError(ValueError):
    pass


@dataclass
class _Plan:
    remutate: list[CyclomaticFunction]
    reuse: list[tuple[str, dict[str, object]]]
    reused_mutants: list[Mutant]
    remutated_labels: list[str]
    reused_labels: list[str]
    carried: dict[str, dict[str, object]]


def _prepare_mutation(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    out_dir: Path,
) -> MutationOutcome | tuple[dict[str, str], list[Waiver], list[dict[str, object]], _Cache, _Plan]:
    versions, missing = _mutmut_versions()
    if missing is not None:
        return missing
    waivers, invalid = _loaded_waivers(cwd, versions)
    if invalid is not None:
        return invalid
    waiver_rows = [item.as_dict() for item in waivers]
    measured, failed = _safe_measured(cwd, config, versions, waiver_rows)
    if failed is not None:
        return failed
    suite = _safe_fingerprint(cwd, versions, waiver_rows)
    if isinstance(suite, MutationOutcome):
        return suite
    cache = _Cache(out_dir / CACHE_NAME, {"mutmut": versions["mutmut"], "suite": suite})
    cached, broken = _safe_cache(cache, versions, waiver_rows)
    if broken is not None:
        return broken
    return versions, waivers, waiver_rows, cache, _plan_functions(
        measured, diff_lines, cached, cwd, waivers
    )


def _mutmut_versions() -> tuple[dict[str, str], MutationOutcome | None]:
    versions: dict[str, str] = {}
    try:
        versions["mutmut"] = mutmut_version()
    except ToolError as exc:
        return versions, _outcome(
            GateResult("mutate", "not_run", msg("tool.missing", tool=reason(exc))),
            CONFIG_OR_TOOL,
            versions,
        )
    return versions, None


def _loaded_waivers(
    cwd: Path, versions: dict[str, str]
) -> tuple[list[Waiver], MutationOutcome | None]:
    try:
        return load_waivers(cwd), None
    except WaiverError as exc:
        return [], _outcome(GateResult("mutate", "not_run", reason(exc)), CONFIG_OR_TOOL, versions)


def _safe_measured(
    cwd: Path,
    config: Config,
    versions: dict[str, str],
    waiver_rows: list[dict[str, object]],
) -> tuple[list[CyclomaticFunction], MutationOutcome | None]:
    try:
        return _measured_functions(cwd, config), None
    except (ToolError, OSError, LizardParseError) as exc:
        return [], _tool_outcome(reason(exc), versions, waiver_rows)


def _safe_fingerprint(
    cwd: Path, versions: dict[str, str], waiver_rows: list[dict[str, object]]
) -> str | MutationOutcome:
    try:
        return suite_fingerprint(cwd)
    except ToolError as exc:
        return _tool_outcome(reason(exc), versions, waiver_rows)


def _safe_cache(
    cache: _Cache,
    versions: dict[str, str],
    waiver_rows: list[dict[str, object]],
) -> tuple[_CacheView, MutationOutcome | None]:
    try:
        return _read_cache(cache), None
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, _CacheLineError) as exc:
        broken = msg("mutate.cache_invalid", detail=str(exc))
        return _CacheView({}, False), _tool_outcome(broken, versions, waiver_rows)


def _plan_functions(
    measured: list[CyclomaticFunction],
    diff_lines: dict[str, set[int]],
    view: _CacheView,
    cwd: Path,
    waivers: list[Waiver],
) -> _Plan:
    remutate, reuse = _split_functions(measured, diff_lines, view, cwd, waivers)
    by_key = {f"{item.file}::{item.name}": item for item in measured}
    return _Plan(
        remutate=remutate,
        reuse=reuse,
        reused_mutants=apply_waivers(_mutants_from_cache(reuse, by_key), waivers),
        remutated_labels=[f"{item.file}::{item.name}" for item in remutate],
        reused_labels=[key for key, _entry in reuse],
        carried=_carried_rows(view, by_key, waivers),
    )


def _carried_rows(
    view: _CacheView,
    by_key: dict[str, CyclomaticFunction],
    waivers: list[Waiver],
) -> dict[str, dict[str, object]]:
    return {
        name: entry
        for name, entry in view.held.items()
        if name in by_key and _carry(entry, waivers)
    }


def _baseline_outcome(
    cwd: Path,
    baseline: int | None,
    versions: dict[str, str],
    waiver_rows: list[dict[str, object]],
) -> MutationOutcome | None:
    try:
        code = pytest_exit_code(cwd) if baseline is None else baseline
    except ToolError as exc:
        return _tool_outcome(reason(exc), versions, waiver_rows)
    if pytest_passed(code):
        return None
    return _outcome(
        GateResult("mutate", "not_run", msg("probe.baseline_failed")),
        BASELINE_BROKEN,
        versions,
        waivers=waiver_rows,
    )


def _collect_fresh(
    cwd: Path,
    config: Config,
    remutate: list[CyclomaticFunction],
    max_workers: int | None,
    versions: dict[str, str],
    waiver_rows: list[dict[str, object]],
    waivers: list[Waiver],
) -> list[Mutant] | MutationOutcome:
    cleanup = _install_mutmut_config(cwd, config.include)
    prepare_mutmut_workspace(cwd)
    try:
        parsed, failed = _run_and_parse(cwd, remutate, max_workers, versions, waiver_rows)
    finally:
        cleanup()
    if failed is not None:
        return failed
    return apply_waivers([item for item in parsed if _belongs(item, remutate)], waivers)


def _run_and_parse(
    cwd: Path,
    remutate: list[CyclomaticFunction],
    max_workers: int | None,
    versions: dict[str, str],
    waiver_rows: list[dict[str, object]],
) -> tuple[list[Mutant], MutationOutcome | None]:
    patterns = [
        pattern for item in remutate for pattern in mutmut_run_patterns(item.file, item.name)
    ]
    try:
        run_mutmut(cwd, patterns, max_workers)
        raw_results = mutmut_results(cwd)
        parsed = mutants_from_raw(raw_results, {})
    except (ToolError, MutmutParseError) as exc:
        return [], _tool_outcome(reason(exc), versions, waiver_rows)
    belonging = [item for item in parsed if _belongs(item, remutate)]
    shows = _shows_for(cwd, ids_for_show(belonging))
    try:
        return _with_file_lines(mutants_from_raw(raw_results, shows), remutate), None
    except MutmutParseError as exc:
        return [], _tool_outcome(reason(exc), versions, waiver_rows)


def _with_file_lines(mutants: list[Mutant], functions: list[CyclomaticFunction]) -> list[Mutant]:
    """O diff do mutmut 3.8 começa na função. A linha do arquivo é start_line + relativa - 1."""
    located: list[Mutant] = []
    for mutant in mutants:
        start = _start_line(mutant, functions)
        if start is None or mutant.line <= 0:
            located.append(mutant)
            continue
        located.append(replace(mutant, line=start + mutant.line - 1))
    return located


def _start_line(mutant: Mutant, functions: list[CyclomaticFunction]) -> int | None:
    for item in functions:
        if mutant.id.startswith(mutmut_id_prefix(item.file, item.name)):
            return item.start_line
    return None


def _shows_for(cwd: Path, mutant_ids: list[str]) -> dict[str, str]:
    shows: dict[str, str] = {}
    for mutant_id in mutant_ids:
        shown = _one_show(cwd, mutant_id)
        if shown is not None:
            shows[mutant_id] = shown
    return shows


def _one_show(cwd: Path, mutant_id: str) -> str | None:
    try:
        return mutmut_show(cwd, mutant_id)
    except ToolError:
        return None


def _tool_outcome(
    why: Text, versions: dict[str, str], waiver_rows: list[dict[str, object]]
) -> MutationOutcome:
    return _outcome(
        GateResult("mutate", "not_run", why), CONFIG_OR_TOOL, versions, waivers=waiver_rows
    )


def _split_functions(
    measured: list[CyclomaticFunction],
    diff_lines: dict[str, set[int]],
    view: _CacheView,
    cwd: Path,
    waivers: list[Waiver],
) -> tuple[list[CyclomaticFunction], list[tuple[str, dict[str, object]]]]:
    by_key = {f"{item.file}::{item.name}": item for item in measured}
    survivor_keys = frozenset(
        name for name, entry in view.held.items() if _has_unwaived_survivor(entry, waivers)
    )
    keys = _candidate_keys(measured, diff_lines, survivor_keys, by_key)
    remutate: list[CyclomaticFunction] = []
    reuse: list[tuple[str, dict[str, object]]] = []
    for key in sorted(keys):
        item = by_key[key]
        entry = _reusable_entry(view, key)
        digest = _function_hash(cwd, item.file, item.start_line, item.end_line)
        if entry is not None and not _needs_remutation(entry, digest, waivers):
            reuse.append((key, entry))
        else:
            remutate.append(item)
    return remutate, reuse


def _reusable_entry(view: _CacheView, key: str) -> dict[str, object] | None:
    if not view.may_reuse:
        return None
    return view.held.get(key)


def _candidate_keys(
    measured: list[CyclomaticFunction],
    diff_lines: dict[str, set[int]],
    survivor_keys: frozenset[str],
    by_key: dict[str, CyclomaticFunction],
) -> set[str]:
    keys = {
        f"{item.file}::{item.name}"
        for item in measured
        if function_is_changed(item.file, item.start_line, item.end_line, diff_lines)
    }
    keys.update(name for name in survivor_keys if name in by_key)
    return keys


def _needs_remutation(entry: dict[str, object], digest: str, waivers: list[Waiver]) -> bool:
    if entry.get("hash") != digest:
        return True
    return _has_unwaived_survivor(entry, waivers)


def _has_unwaived_survivor(entry: dict[str, object], waivers: list[Waiver]) -> bool:
    current = apply_waivers(_cached_mutants(entry), waivers)
    return any(item.status == "survived" and not item.waiver for item in current)


def _carry(entry: dict[str, object], waivers: list[Waiver]) -> bool:
    survived = [
        item for item in apply_waivers(_cached_mutants(entry), waivers) if item.status == "survived"
    ]
    return bool(survived) and all(item.waiver for item in survived)


def _cached_mutants(entry: dict[str, object]) -> list[Mutant]:
    mutants = entry.get("mutants")
    if not isinstance(mutants, list):
        return []
    return [
        _mutant_from_row(item)
        for item in mutants
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]


def _read_cache(cache: _Cache) -> _CacheView:
    if not cache.path.is_file():
        return _CacheView({}, True)
    return _view_cache(json.loads(cache.path.read_bytes().decode()), cache.key)


def _view_cache(raw: object, key: dict[str, str]) -> _CacheView:
    if not isinstance(raw, dict):
        return _CacheView({}, True)
    functions = raw.get("functions")
    held = (
        {str(name): value for name, value in functions.items() if isinstance(value, dict)}
        if isinstance(functions, dict)
        else {}
    )
    for entry in held.values():
        _cached_mutants(entry)
    may_reuse = all(raw.get(field) == key[field] for field in key)
    return _CacheView(held, may_reuse)


def _mutants_from_cache(
    reuse: list[tuple[str, dict[str, object]]],
    functions: dict[str, CyclomaticFunction] | None = None,
) -> list[Mutant]:
    mutants: list[Mutant] = []
    for key, entry in reuse:
        rows = entry.get("mutants")
        if not isinstance(rows, list):
            continue
        start = _reuse_start(key, entry, functions or {})
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("id"), str):
                mutants.append(_mutant_from_row(row, start))
    return mutants


def _reuse_start(
    key: str, entry: dict[str, object], functions: dict[str, CyclomaticFunction]
) -> int | None:
    if entry.get("line_base") == "file":
        return None
    current = functions.get(key)
    if current is not None and current.start_line > 0:
        return current.start_line
    return _cached_start(entry)


def _cached_start(entry: dict[str, object]) -> int | None:
    if entry.get("line_base") == "file":
        return None
    start = entry.get("start_line")
    if isinstance(start, int) and start > 0:
        return start
    return None


def _mutant_line(row: dict[str, object]) -> int:
    try:
        return int(row.get("line") or 0)
    except (ValueError, TypeError) as exc:
        raise _CacheLineError(str(exc))


def _mutant_from_row(row: dict[str, object], file_start: int | None = None) -> Mutant:
    waiver = row.get("waiver")
    line = _mutant_line(row)
    if file_start is not None and line > 0:
        line = file_start + line - 1
    return Mutant(
        id=str(row["id"]),
        function=str(row.get("function") or ""),
        file=str(row.get("file") or ""),
        line=line,
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


def _blocks(mutant: Mutant, diff_lines: dict[str, set[int]]) -> bool:
    if mutant.status != "survived" or mutant.waiver:
        return False
    if not mutant.file or mutant.line <= 0:
        return True
    return mutant.line in diff_lines.get(mutant.file, ())


def _finish(
    mutants: list[Mutant],
    diff_lines: dict[str, set[int]],
    remutated: list[str],
    reused: list[str],
    versions: dict[str, str],
    waiver_rows: list[dict[str, object]],
) -> MutationOutcome:
    visible = [item for item in mutants if item.status == "survived"]
    judged = [(item, _blocks(item, diff_lines)) for item in visible]
    rows = [_reported_survivor(item, blocking) for item, blocking in judged]
    blockers = [item for item, blocking in judged if blocking]
    uncovered = no_coverage_summary(mutants, [*remutated, *reused])
    summary = {"remutated": remutated, "reused": reused, "no_coverage": uncovered}
    if not blockers:
        return _outcome(
            _passing_result(int(uncovered["total"])),
            PASSED,
            versions,
            waivers=waiver_rows,
            survivors=rows,
            summary=summary,
        )
    listed = ", ".join(f"{item.function}@{item.file}:{item.line}" for item in blockers)
    return _outcome(
        GateResult("mutate", "failed", msg("mutate.unwaived", mutants=listed)),
        UNWAIVED_SURVIVOR,
        versions,
        waivers=waiver_rows,
        survivors=rows,
        summary=summary,
    )


def no_coverage_summary(mutants: list[Mutant], labels: list[str]) -> dict[str, object]:
    """O mutmut deixa `file` vazio sem `show`, então o id casa o prefixo.

    O Stryker preenche arquivo e função, e o id não tem esse prefixo.
    """
    counts = [row for row in (_label_count(mutants, label) for label in labels) if row]
    counts.sort(key=_count_order)
    return {
        "total": sum(count for count, _file, _function in counts),
        "functions": [_count_row(row) for row in counts],
    }


def _label_count(mutants: list[Mutant], label: str) -> tuple[int, str, str] | None:
    file, function = label.split("::")
    prefix = mutmut_id_prefix(file, function)
    count = sum(1 for item in mutants if _uncovered(item, file, function, prefix))
    if not count:
        return None
    return count, file, function


def _uncovered(item: Mutant, file: str, function: str, prefix: str) -> bool:
    if item.status != "no_coverage":
        return False
    if item.file == file and item.function == function:
        return True
    return item.id.startswith(prefix)


def _count_order(row: tuple[int, str, str]) -> tuple[int, str, str]:
    count, file, function = row
    return -count, file, function


def _count_row(row: tuple[int, str, str]) -> dict[str, object]:
    count, file, function = row
    return {"file": file, "function": function, "count": count}


def _passing_result(uncovered: int) -> GateResult:
    if not uncovered:
        return GateResult("mutate", "passed")
    key = "mutate.uncovered_one" if uncovered == 1 else "mutate.uncovered_many"
    return GateResult("mutate", "warn", msg(key, count=uncovered))


def focus_with_survivors(
    focus: list[dict[str, object]], survivors: list[dict[str, object]]
) -> list[dict[str, object]]:
    scores: dict[str, float] = {str(item["file"]): float(item["risk"]) for item in focus}
    for item in survivors:
        if not item.get("blocking"):
            continue
        file = str(item["file"])
        if not file:
            continue
        scores[file] = scores.get(file, 0.0) + 100.0
    ordered = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    extras = {str(item["file"]): item for item in focus}
    rows: list[dict[str, object]] = []
    for file, risk in ordered:
        row: dict[str, object] = {"file": file, "risk": risk}
        source = extras.get(file)
        if source is not None and source.get("clone"):
            row["clone"] = True
        rows.append(row)
    return rows


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
    return _named_for_mutmut(cwd, measured)


def _named_for_mutmut(cwd: Path, measured: list[CyclomaticFunction]) -> list[CyclomaticFunction]:
    """O nome do cache é o qualname. A linha inicial é a que o `mutmut show` imprime."""
    try:
        targets = mutation_targets(measured, _read_sources(cwd, measured))
    except MutmutParseError as exc:
        raise ToolError(*exc.args) from exc
    named: list[CyclomaticFunction] = []
    for row, target in zip(measured, targets):
        named.append(replace(row, name=target.qualname(), start_line=target.start_line))
    return named


def _read_sources(cwd: Path, measured: list[CyclomaticFunction]) -> dict[str, str]:
    try:
        return {item.file: (cwd / item.file).read_text() for item in measured}
    except UnicodeDecodeError as exc:
        raise ToolError(str(exc)) from exc


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
            "line_base": "file",
            "mutants": [_mutant_row(mutant) for mutant in own],
        }
    return body


def _function_hash(cwd: Path, file: str, start: int, end: int) -> str:
    lines = (cwd / file).read_text().splitlines()
    text = "\n".join(lines[start - 1 : end])
    return hashlib.sha256(text.encode()).hexdigest()


def _publish_body(plan: _Plan, fresh: dict[str, object]) -> dict[str, object]:
    body: dict[str, object] = dict(plan.carried)
    body.update(dict(plan.reuse))
    body.update(fresh)
    return body


def _write_cache(cache: _Cache, functions: dict[str, object]) -> None:
    cache.path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({**cache.key, "functions": functions}, indent=2) + "\n"
    fd, name = tempfile.mkstemp(dir=cache.path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, cache.path)
    finally:
        temporary.unlink(missing_ok=True)


def _reported_survivor(mutant: Mutant, blocking: bool) -> dict[str, object]:
    return {**_mutant_row(mutant), "blocking": blocking}


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


def prepare_mutmut_workspace(cwd: Path) -> None:
    """Aponta `mutants/node_modules` para o diretório real. Não copia."""
    source = cwd / "node_modules"
    if not source.is_dir():
        return
    dest_root = cwd / "mutants"
    dest_root.mkdir(parents=True, exist_ok=True)
    dest = dest_root / "node_modules"
    if dest.is_symlink() or dest.exists():
        return
    dest.symlink_to(source.resolve(), target_is_directory=True)


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
