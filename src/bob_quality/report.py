"""Renderiza o relatório schema v1 em `.bob/report.md` e `report.json`."""

from __future__ import annotations

import json
from pathlib import Path

from bob_quality.messages import Language, Message, Text, msg, render
from bob_quality.models import (
    Clone,
    CognitiveFunction,
    DepViolation,
    FunctionMetric,
    GateResult,
    GateStatus,
    LedgerRow,
    PythonDead,
    Report,
    TypeScriptDead,
)

JSON_LANGUAGE: Language = "en"

GATE_MARK: dict[GateStatus, str] = {
    "passed": "✅",
    "warn": "⚠️",
    "failed": "❌",
    "not_run": "⏭️",
}

STATUS_LABEL: dict[GateStatus, Message] = {
    "passed": msg("status.passed"),
    "warn": msg("status.warn"),
    "failed": msg("status.failed"),
    "not_run": msg("status.not_run"),
}


def write_report(report: Report, out_dir: Path, fmt: str, lang: Language) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if fmt in {"json", "both"}:
        (out_dir / "report.json").write_text(json.dumps(to_json(report), indent=2) + "\n")
    if fmt in {"md", "both"}:
        (out_dir / "report.md").write_text(to_markdown(report, lang))


def to_json(report: Report) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": report.schema_version,
        "commit": report.commit,
        "base": report.base,
        "generated_at": report.generated_at,
        "tool_versions": report.tool_versions,
        "gates": [
            {"name": gate.name, "status": gate.status, "reason": _json_reason(gate.reason)}
            for gate in report.gates
        ],
        "focus": report.focus,
        "top_crap": report.top_crap,
        "old_debt": report.old_debt,
        "dependencies": _json_dependencies(report.dependencies),
        "old_dependencies": _json_dependencies(report.old_dependencies),
        "clones": [clone_row(clone) for clone in report.clones],
        "waivers": report.waivers,
        "survivors": report.survivors,
        "mutation": report.mutation,
        "reproduce": report.reproduce,
        "exit_code": report.exit_code,
    }
    if _cognitive_requested(report):
        payload["cognitive"] = [cognitive_row(item) for item in report.cognitive]
    if report.dead_code is not None:
        payload["dead_code"] = {
            "symbols": [dead_row(row) for row in report.dead_code.rows]
        }
    return payload


def _json_reason(reason: Text | None) -> str | None:
    if reason is None:
        return None
    return render(reason, JSON_LANGUAGE)


def _json_dependencies(items: list[dict[str, object]]) -> list[dict[str, object]]:
    return [_json_dependency(item) for item in items]


def _json_dependency(item: dict[str, object]) -> dict[str, object]:
    row = dict(item)
    rule = row.get("rule")
    if isinstance(rule, Message):
        row["rule"] = render(rule, JSON_LANGUAGE)
    return row


def to_markdown(report: Report, lang: Language) -> str:
    lines: list[Text] = [msg("report.title"), ""]
    if report.waivers or report.mutation is not None:
        lines.extend(_waiver_section(report.waivers))
    lines.extend(_header(report))
    lines.extend(_verdict_lines(report))
    lines.extend(_focus_lines(report))
    lines.extend(_crap_lines(report))
    lines.extend(_debt_lines(report))
    lines.extend(_dependency_lines(report))
    lines.extend(["", msg("report.clones"), ""])
    lines.extend(_clone_lines(report))
    lines.extend(_survivor_lines(report))
    lines.extend(_no_coverage_lines(report))
    lines.extend(_cognitive_lines(report))
    lines.extend(_dead_lines(report))
    lines.extend(_footer(report, lang))
    return "\n".join(render(line, lang) for line in lines)


def _header(report: Report) -> list[Text]:
    return [
        f"- Commit: `{report.commit}`",
        f"- Base: `{report.base}`",
        msg("report.date", value=report.generated_at),
        msg("report.tools", value=_tools(report.tool_versions)),
        "",
    ]


def _verdict_lines(report: Report) -> list[Text]:
    lines: list[Text] = [msg("report.verdict"), ""]
    for gate in report.gates:
        lines.append(_verdict_line(gate))
    return lines


def _verdict_line(gate: GateResult) -> Message:
    mark = GATE_MARK[gate.status]
    status = STATUS_LABEL[gate.status]
    if gate.reason:
        return msg(
            "report.gate_reason", mark=mark, name=gate.name, status=status, reason=gate.reason
        )
    return msg("report.gate", mark=mark, name=gate.name, status=status)


def _focus_lines(report: Report) -> list[Text]:
    lines: list[Text] = ["", msg("report.focus"), ""]
    if not report.focus:
        lines.append(msg("report.no_focus"))
        return lines
    for item in report.focus:
        key = "report.focus_item_clone" if item.get("clone") else "report.focus_item"
        lines.append(msg(key, file=item["file"], risk=item["risk"]))
    return lines


def _crap_lines(report: Report) -> list[Text]:
    lines: list[Text] = ["", msg("report.top_crap"), ""]
    if not report.top_crap:
        lines.append(msg("report.no_top_crap"))
        return lines
    lines.append(msg("report.crap_header"))
    lines.append("|---|---|---:|---:|---:|---|")
    lines.extend(_crap_row(fn) for fn in report.top_crap)
    return lines


def _crap_row(fn: dict[str, object]) -> str:
    loc = f"{fn['file']}:{fn['start_line']}"
    cov = f"{float(fn['coverage']) * 100:.0f}%"
    delta = "—" if fn.get("delta") is None else fn["delta"]
    return f"| {fn['name']} | {loc} | {fn['cc']} | {cov} | {fn['crap']} | {delta} |"


def _debt_lines(report: Report) -> list[Text]:
    if not report.old_debt:
        return []
    lines: list[Text] = ["", msg("report.old_debt"), ""]
    for fn in report.old_debt:
        loc = f"{fn['file']}:{fn['start_line']}"
        lines.append(msg("report.old_debt_item", name=fn["name"], loc=loc, crap=fn["crap"]))
    return lines


def _survivor_lines(report: Report) -> list[Text]:
    if report.mutation is None:
        return []
    lines: list[Text] = ["", msg("report.survivors"), ""]
    if not report.survivors:
        lines.append(msg("report.no_survivors"))
        return lines
    lines.append(msg("report.survivor_header"))
    lines.append("|---|---|---|---|---|")
    for item in report.survivors:
        lines.append(_survivor_row(item))
    return lines


def _no_coverage_lines(report: Report) -> list[Text]:
    uncovered = (report.mutation or {}).get("no_coverage")
    if not isinstance(uncovered, dict):
        return []
    lines: list[Text] = ["", msg("report.no_coverage"), ""]
    if not uncovered["functions"]:
        lines.append(msg("report.no_uncovered"))
        return lines
    lines.extend([msg("report.uncovered_total", total=uncovered["total"]), ""])
    lines.extend([msg("report.uncovered_header"), "|---|---|---:|"])
    for row in uncovered["functions"]:
        lines.append(f"| {row['function']} | {row['file']} | {row['count']} |")
    return lines


def _survivor_row(item: dict[str, object]) -> Text:
    waiver = item.get("waiver") or "—"
    operator = str(item.get("operator") or "—").replace("|", "\\|")
    return msg(
        "report.survivor_row",
        id=item["id"],
        function=item["function"],
        location=_survivor_location(item),
        operator=operator,
        waiver=waiver,
    )


def _survivor_location(item: dict[str, object]) -> Text:
    location = f"{item['file']}:{item['line']}"
    if item.get("blocking") is False and not item.get("waiver"):
        return msg("report.survivor_outside_diff", location=location)
    return location


def _waiver_section(waivers: list[dict[str, object]]) -> list[Text]:
    lines: list[Text] = ["## Waivers", ""]
    if not waivers:
        lines.append(msg("report.no_waivers"))
        lines.append("")
        return lines
    lines.append(msg("report.waiver_header"))
    lines.append("|---|---|---|---|")
    for item in waivers:
        reason = str(item.get("reason") or "").replace("|", "\\|")
        lines.append(
            f"| `{item.get('id', '')}` | {reason} | {item.get('author', '')} | {item.get('date', '')} |"
        )
    lines.append("")
    return lines


def _cognitive_lines(report: Report) -> list[Text]:
    if not _cognitive_requested(report):
        return []
    lines: list[Text] = ["", msg("report.cognitive"), ""]
    lines.extend(_cognitive_body(report))
    return lines


def _cognitive_body(report: Report) -> list[Text]:
    gate = _gate_named(report, "cognitive")
    if gate is not None and gate.status == "not_run":
        return [msg("report.cognitive_not_run", reason=gate.reason or "")]
    if not report.cognitive:
        return [msg("report.cognitive_none")]
    lines: list[Text] = [msg("report.cognitive_header"), "|---|---|---:|---|---|"]
    lines.extend(_cognitive_row(item) for item in report.cognitive)
    return lines


def _cognitive_row(item: CognitiveFunction) -> Message:
    return msg(
        "report.cognitive_row",
        name=item.name,
        loc=f"{item.file}:{item.start_line}-{item.end_line}",
        score=item.score,
        language=item.language,
        waiver=item.waiver_id(),
    )


def _dead_lines(report: Report) -> list[Text]:
    if report.dead_code is None:
        return []
    lines: list[Text] = ["", msg("report.dead"), ""]
    lines.extend(_dead_body(report, _gate_named(report, "dead_code")))
    return lines


def _dead_body(report: Report, gate: GateResult | None) -> list[Text]:
    if gate is not None and gate.status == "not_run":
        return [msg("report.dead_not_run", reason=gate.reason or "")]
    section = report.dead_code
    if section is None or not section.rows:
        return _dead_empty(gate)
    return [_dead_item(row) for row in section.rows]


def _dead_empty(gate: GateResult | None) -> list[Text]:
    lines = [msg("report.no_dead")]
    if gate is not None and gate.reason:
        lines.append(gate.reason)
    return lines


def _dead_item(row: LedgerRow) -> Message:
    symbol = row.symbol
    return msg(
        "report.dead_item",
        loc=f"{symbol.file}:{symbol.line}",
        kind=msg(f"report.dead_kind.{symbol.kind}"),
        name=symbol.name,
        suffix=_dead_suffix(row),
    )


def _dead_suffix(row: LedgerRow) -> str:
    symbol = row.symbol
    if isinstance(symbol, PythonDead):
        suffix = f" {symbol.confidence}%"
    elif isinstance(symbol, TypeScriptDead):
        suffix = ""
    else:
        raise TypeError(type(symbol).__name__)
    if row.waiver is not None:
        suffix += f" waiver `{row.waiver}`"
    return suffix


def dead_row(row: LedgerRow) -> dict[str, object]:
    symbol = row.symbol
    if isinstance(symbol, PythonDead):
        language = "python"
        confidence: int | None = symbol.confidence
    elif isinstance(symbol, TypeScriptDead):
        language = "typescript"
        confidence = None
    else:
        raise TypeError(type(symbol).__name__)
    return {
        "file": symbol.file,
        "line": symbol.line,
        "name": symbol.name,
        "kind": symbol.kind,
        "language": language,
        "confidence": confidence,
        "waiver": row.waiver,
    }


def _footer(report: Report, lang: Language) -> list[Text]:
    command = f"{report.reproduce} --lang {lang}" if report.reproduce else ""
    return ["", msg("report.reproduce"), "", "```", command, "```", ""]


def cognitive_row(item: CognitiveFunction) -> dict[str, object]:
    return {
        "file": item.file,
        "name": item.name,
        "start_line": item.start_line,
        "end_line": item.end_line,
        "score": item.score,
        "language": item.language,
        "waiver_id": item.waiver_id(),
    }


def _cognitive_requested(report: Report) -> bool:
    return any(gate.name == "cognitive" for gate in report.gates)


def clone_row(clone: Clone) -> dict[str, object]:
    return {
        "first_file": clone.first_file,
        "first_start": clone.first_start,
        "first_end": clone.first_end,
        "second_file": clone.second_file,
        "second_start": clone.second_start,
        "second_end": clone.second_end,
        "lines": clone.lines,
        "tokens": clone.tokens,
        "similarity": clone.similarity,
        "kind": clone.kind,
    }


def _dependency_lines(report: Report) -> list[Text]:
    lines: list[Text] = ["", msg("report.dependencies"), ""]
    lines.extend(_dependency_items(report))
    lines.extend(_old_dependency_lines(report))
    return lines


def _dependency_items(report: Report) -> list[Text]:
    gate = _gate_named(report, "deps")
    if gate is None or gate.status == "not_run":
        return [msg("report.deps_not_run")]
    if gate.status == "failed" and not report.dependencies:
        return [msg("report.deps_failed", reason=gate.reason)]
    if not report.dependencies:
        return [msg("report.no_violations")]
    return [_dependency_item(item) for item in report.dependencies]


def _dependency_item(item: dict[str, object]) -> Message:
    return msg(
        "report.dependency_edge",
        origin=item["origin"],
        destination=item["destination"],
        rule=item["rule"],
    )


def _gate_named(report: Report, name: str) -> GateResult | None:
    for gate in report.gates:
        if gate.name == name:
            return gate
    return None


def _old_dependency_lines(report: Report) -> list[Text]:
    if not report.old_dependencies:
        return []
    lines: list[Text] = ["", msg("report.old_dependencies"), ""]
    for item in report.old_dependencies:
        lines.append(msg("report.old_dependency_item", item=_dependency_item(item)))
    return lines


def violation_rows(items: list[DepViolation], *, in_diff: bool) -> list[dict[str, object]]:
    return [violation_row(item) for item in items if item.in_diff is in_diff]


def violation_row(item: DepViolation) -> dict[str, object]:
    return {"origin": item.origin, "destination": item.destination, "rule": item.rule}


def metric_row(metric: FunctionMetric) -> dict[str, object]:
    return {
        "lang": metric.lang,
        "module": metric.module,
        "name": metric.name,
        "file": metric.file,
        "start_line": metric.start_line,
        "end_line": metric.end_line,
        "cc": metric.cc,
        "coverage": metric.coverage,
        "crap": metric.crap,
        "changed": metric.changed,
        "delta": metric.delta,
    }


def _clone_lines(report: Report) -> list[Text]:
    if report.clones:
        return [_clone_line(clone) for clone in report.clones]
    return [_clone_absent(report)]


def _clone_absent(report: Report) -> Message:
    dry = next((gate for gate in report.gates if gate.name == "dry"), None)
    if dry is not None and dry.status == "passed":
        return msg("report.no_clones")
    if dry is not None and dry.reason:
        return msg("report.clones_not_run_reason", reason=dry.reason)
    return msg("report.clones_not_run")


def _clone_line(clone: Clone) -> Message:
    return msg(
        "report.clone_item",
        left=f"`{clone.first_file}:{clone.first_start}-{clone.first_end}`",
        right=f"`{clone.second_file}:{clone.second_start}-{clone.second_end}`",
        lines=clone.lines,
        tokens=clone.tokens,
        similarity=_similarity(clone),
    )


def _similarity(clone: Clone) -> Text:
    if clone.similarity is not None:
        return f"{clone.similarity * 100:.0f}%"
    if clone.kind == "exact":
        return msg("report.exact")
    if clone.kind:
        return clone.kind
    return "—"


def _tools(versions: dict[str, str]) -> str:
    if not versions:
        return "—"
    return ", ".join(f"{name} {ver}" for name, ver in versions.items())
