"""Renderiza o relatório schema v1 em `.bob/report.md` e `report.json`."""

from __future__ import annotations

import json
from pathlib import Path

from bob_quality.messages import Language, Message, Text, msg, render
from bob_quality.models import (
    Advisory,
    Clone,
    DepViolation,
    FunctionMetric,
    GateResult,
    GateStatus,
    LedgerRow,
    MissingPackage,
    PythonDead,
    Report,
    RowWaived,
    SecretRow,
    SupplyFinding,
    SupplyReport,
    SupplyRow,
    TypeScriptDead,
    UndeclaredImport,
    UnverifiedAdvisory,
    UnverifiedExistence,
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
        **_supply_field(report),
    }
    if report.secrets is not None:
        payload["secrets"] = [secret_row(row) for row in report.secrets.blocking]
    if report.typing is not None:
        payload["typing"] = report.typing
    payload["reproduce"] = report.reproduce
    payload["exit_code"] = report.exit_code
    if report.dead_code is not None:
        payload["dead_code"] = {"symbols": [dead_row(row) for row in report.dead_code.rows]}
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
    lines.extend(_survivor_lines(report, lang))
    lines.extend(_no_coverage_lines(report))
    lines.extend(supply_lines(report))
    lines.extend(_types_lines(report))
    lines.extend(_secrets_lines(report))
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


def _survivor_lines(report: Report, lang: Language) -> list[Text]:
    if report.mutation is None:
        return []
    lines: list[Text] = ["", msg("report.survivors"), ""]
    if not report.survivors:
        lines.append(msg("report.no_survivors"))
        return lines
    lines.append(msg("report.survivor_header"))
    lines.append("|---|---|---|---|---|")
    for item in report.survivors:
        lines.append(_survivor_row(item, lang))
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


def _survivor_row(item: dict[str, object], lang: Language) -> str:
    target = item.get("target")
    first = "`" + str(target).replace("|", "\\|") + "`" if target else "—"
    waiver = item.get("waiver") or "—"
    operator = str(item.get("operator") or "—").replace("|", "\\|")
    return (
        f"| {first} | {item['function']} | {render(_survivor_location(item), lang)} | {operator} | {waiver} |"
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


def _types_lines(report: Report) -> list[Text]:
    found = report.typing
    if not isinstance(found, dict):
        return []
    lines: list[Text] = ["", msg("report.types"), ""]
    lines.extend(_type_body(report, found))
    return lines


def _type_body(report: Report, found: dict[str, object]) -> list[Text]:
    skipped = _not_run_line(report)
    if skipped is not None:
        return [skipped]
    return _finding_table(found.get("findings"))


def _not_run_line(report: Report) -> Text | None:
    gate = _gate_named(report, "typing")
    if gate is None or gate.status != "not_run" or gate.reason is None:
        return None
    return msg("report.types_line", reason=gate.reason)


def _finding_table(findings: object) -> list[Text]:
    if not isinstance(findings, list) or not findings:
        return [msg("report.types_none")]
    rows: list[Text] = [msg("report.types_header"), "|---|---:|---|---|---|"]
    rows.extend(_finding_row(item) for item in findings if isinstance(item, dict))
    return rows


def _finding_row(item: dict[str, object]) -> str:
    file = _cell(item.get("file"))
    code = _cell(item.get("code"))
    waiver = _cell(item.get("waiver_id"))
    disposition = _cell(item.get("disposition"))
    return f"| `{file}` | {item.get('line')} | `{code}` | {disposition} | `{waiver}` |"


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|")


def _secrets_lines(report: Report) -> list[Text]:
    ledger = report.secrets
    if ledger is None:
        return []
    lines: list[Text] = ["", msg("report.secrets"), ""]
    if ledger.blocking:
        lines.extend(_secret_table(ledger.blocking))
    else:
        lines.append(msg("report.no_secrets"))
    if not ledger.outside_diff:
        return lines
    lines.extend(["", msg("report.secrets_outside"), ""])
    lines.extend(_secret_table(ledger.outside_diff))
    return lines


def _secret_table(rows: tuple[SecretRow, ...]) -> list[Text]:
    lines: list[Text] = [msg("report.secrets_header"), "|---|---|---:|---|"]
    lines.extend(_secret_table_row(row) for row in rows)
    return lines


def _secret_table_row(row: SecretRow) -> str:
    return f"| `{row.waiver_id()}` | {row.file} | {row.line} | {row.rule_id} |"


def secret_row(row: SecretRow) -> dict[str, object]:
    return {"file": row.file, "line": row.line, "rule_id": row.rule_id}


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


def _supply_field(report: Report) -> dict[str, object]:
    if report.supply is None:
        return {}
    return {"supply": supply_json(report.supply)}


def supply_json(supply: SupplyReport) -> dict[str, object]:
    return {
        "measured": list(supply.measured),
        "skipped": list(supply.skipped),
        "findings": [_finding_json(row) for row in supply.rows],
    }


def supply_lines(report: Report) -> list[Text]:
    supply = report.supply
    if supply is None:
        return []
    lines: list[Text] = ["", msg("report.supply"), ""]
    lines.extend(_supply_body(report, supply))
    return lines


_EXISTENCE_WHAT = {
    "timeout": "report.supply_unverified_timeout",
    "dns": "report.supply_unverified_dns",
    "undecided": "report.supply_unverified_undecided",
}
_ADVISORY_CAUSE = {
    "timeout": "report.supply_cause_timeout",
    "dns": "report.supply_cause_dns",
    "undecided": "report.supply_cause_undecided",
}
_EFFECT = {
    "block": "report.supply_effect_block",
    "warn": "report.supply_effect_warn",
    "waived": "report.supply_effect_waived",
}
_INDEX_LABEL = {"pypi": "PyPI", "npm": "npm"}


def _supply_body(report: Report, supply: SupplyReport) -> list[Text]:
    if not supply.measured:
        return [_unmeasured_line(report)]
    lines = _measured_lines(supply)
    lines.extend(msg("report.supply_skipped", language=language) for language in supply.skipped)
    return lines


def _unmeasured_line(report: Report) -> Text:
    gate = _gate_named(report, "supply")
    if gate is not None and gate.reason is not None:
        return gate.reason
    return msg("supply.unmeasured")


def _measured_lines(supply: SupplyReport) -> list[Text]:
    if not supply.rows:
        return [msg("report.supply_none")]
    lines: list[Text] = [msg("report.supply_header"), "|---|---|---|---|"]
    lines.extend(_supply_row(row) for row in supply.rows)
    return lines


def _supply_row(row: SupplyRow) -> Message:
    return msg(
        "report.supply_row",
        name=_cell(_row_name(row)),
        where=_cell(_row_where(row)),
        what=_row_what(row),
        effect=msg(_EFFECT[row.effect]),
    )


def _row_name(row: SupplyRow) -> str:
    finding = row.finding
    if isinstance(finding, UndeclaredImport):
        return f"`{finding.module}`"
    return f"`{finding.name}`"


def _row_where(row: SupplyRow) -> str:
    finding = row.finding
    return f"`{finding.file}:{finding.line}`"


def _row_what(row: SupplyRow) -> Text:
    finding = row.finding
    if isinstance(finding, MissingPackage):
        return _missing_what(finding, row)
    if isinstance(finding, UndeclaredImport):
        return _undeclared_what(row)
    if isinstance(finding, Advisory):
        return _advisory_what(finding, row)
    if isinstance(finding, UnverifiedExistence):
        return msg(_EXISTENCE_WHAT[finding.cause])
    return _unverified_advisory_what(finding)


def _missing_what(finding: MissingPackage, row: SupplyRow) -> Text:
    index = _INDEX_LABEL[finding.index]
    waiver = _waiver(row)
    if waiver is None:
        return msg("report.supply_missing", index=index)
    return msg("report.supply_missing_waived", index=index, waiver=waiver)


def _undeclared_what(row: SupplyRow) -> Text:
    waiver = _waiver(row)
    if waiver is None:
        return msg("report.supply_undeclared")
    return msg("report.supply_undeclared_waived", waiver=waiver)


def _advisory_what(finding: Advisory, row: SupplyRow) -> Text:
    waiver = _waiver(row)
    if waiver is None:
        return msg(
            "report.supply_advisory",
            severity=finding.severity,
            advisory=finding.advisory_id,
        )
    return msg(
        "report.supply_advisory_waived",
        severity=finding.severity,
        advisory=finding.advisory_id,
        waiver=waiver,
    )


def _unverified_advisory_what(finding: UnverifiedAdvisory) -> Text:
    if finding.advisory_id is None:
        return msg(_EXISTENCE_WHAT[finding.cause])
    if finding.cause == "no_severity":
        return msg("report.supply_no_severity", advisory=finding.advisory_id)
    return msg(
        "report.supply_unverified_advisory",
        advisory=finding.advisory_id,
        cause=msg(_ADVISORY_CAUSE[finding.cause]),
    )


def _waiver(row: SupplyRow) -> str | None:
    if isinstance(row, RowWaived):
        return row.waiver_id
    return None


def _finding_json(row: SupplyRow) -> dict[str, object]:
    finding = row.finding
    payload = _kind_json(finding)
    payload["effect"] = row.effect
    payload["waiver"] = _waiver(row)
    return payload


def _kind_json(finding: SupplyFinding) -> dict[str, object]:
    if isinstance(finding, MissingPackage):
        return _missing_json(finding)
    if isinstance(finding, UndeclaredImport):
        return _undeclared_json(finding)
    if isinstance(finding, Advisory):
        return _advisory_json(finding)
    if isinstance(finding, UnverifiedExistence):
        return _existence_json(finding)
    return _advisory_gap_json(finding)


def _missing_json(finding: MissingPackage) -> dict[str, object]:
    return {
        "kind": "missing",
        "index": finding.index,
        "name": finding.name,
        "file": finding.file,
        "line": finding.line,
    }


def _undeclared_json(finding: UndeclaredImport) -> dict[str, object]:
    return {
        "kind": "undeclared",
        "file": finding.file,
        "module": finding.module,
        "line": finding.line,
    }


def _advisory_json(finding: Advisory) -> dict[str, object]:
    return {
        "kind": "advisory",
        "advisory": finding.advisory_id,
        "index": finding.index,
        "name": finding.name,
        "severity": finding.severity,
        "file": finding.file,
        "line": finding.line,
    }


def _existence_json(finding: UnverifiedExistence) -> dict[str, object]:
    return {
        "kind": "unverified",
        "question": "existence",
        "index": finding.index,
        "name": finding.name,
        "file": finding.file,
        "line": finding.line,
        "cause": finding.cause,
    }


def _advisory_gap_json(finding: UnverifiedAdvisory) -> dict[str, object]:
    return {
        "kind": "unverified",
        "question": "advisory",
        "advisory": finding.advisory_id,
        "index": finding.index,
        "name": finding.name,
        "file": finding.file,
        "line": finding.line,
        "cause": finding.cause,
    }

