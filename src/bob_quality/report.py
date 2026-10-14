"""Renderiza o relatório schema v1 em `.bob/report.md` e `report.json`."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import get_args

from bob_quality.config import ConfigError
from bob_quality.exit_codes import (
    BASELINE_BROKEN,
    CONFIG_OR_TOOL,
    GATE_FAILED,
    PASSED,
    UNWAIVED_SURVIVOR,
)
from bob_quality.messages import Language, Message, Text, msg, render
from bob_quality.models import (
    Clone,
    DeadSection,
    DepViolation,
    Fail,
    Finding,
    FunctionMetric,
    GateResult,
    GateStatus,
    Judged,
    KnipKind,
    LedgerRow,
    OffDiff,
    PythonDead,
    Report,
    SecretLedger,
    SecretRow,
    SecurityReport,
    Severity,
    TypeScriptDead,
    VultureKind,
    Warn,
    Waived,
)

JSON_LANGUAGE: Language = "en"
_VULTURE_KIND: dict[str, VultureKind] = {kind: kind for kind in get_args(VultureKind)}
_KNIP_KIND: dict[str, KnipKind] = {kind: kind for kind in get_args(KnipKind)}

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
    }
    if report.security is not None:
        payload["security"] = _security_json(report.security)
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
    lines.extend(_types_lines(report))
    lines.extend(_secrets_lines(report))
    lines.extend(_dead_lines(report))
    lines.extend(_security_lines(report))
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


_EFFECT = {
    "fail": "security.effect.fail",
    "warn": "security.effect.warn",
    "waived": "security.effect.waived",
    "off_diff": "security.effect.off_diff",
}


def _security_json(security: SecurityReport) -> dict[str, object]:
    return {
        "findings": [_security_finding(item) for item in security.findings],
        "unmeasured": list(security.unmeasured),
    }


def _security_finding(item: Judged) -> dict[str, object]:
    finding = item.finding
    waiver = item.reason if isinstance(item, Waived) else None
    return {
        "tool": finding.tool,
        "rule": finding.rule,
        "file": finding.file,
        "line": finding.line,
        "end_line": finding.end_line,
        "severity": finding.severity,
        "disposition": item.kind,
        "waiver": waiver,
    }


def _security_lines(report: Report) -> list[Text]:
    security = report.security
    if security is None:
        return []
    lines: list[Text] = ["", msg("report.security"), ""]
    if security.findings:
        lines.append(msg("report.security_header"))
        lines.append("|---|---|---|---|---|---|")
        lines.extend(_security_row(item) for item in security.findings)
        return lines
    if security.unmeasured:
        gate = _gate_named(report, "security")
        if gate is not None and gate.reason is not None:
            lines.append(gate.reason)
            return lines
    lines.append(msg("report.security_none"))
    return lines


def _security_row(item: Judged) -> Message:
    finding = item.finding
    if finding.line == finding.end_line:
        location = f"{finding.file}:{finding.line}"
    else:
        location = f"{finding.file}:{finding.line}-{finding.end_line}"
    waiver = "—"
    if isinstance(item, Waived):
        waiver = item.reason.replace("|", "\\|")
    return msg(
        "report.security_row",
        tool=_cell(finding.tool),
        rule=_cell(finding.rule),
        location=_cell(location),
        severity=finding.severity,
        disposition=msg(_EFFECT[item.kind]),
        waiver=waiver,
    )


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


_SAVED_EXIT_CODES = frozenset(
    {PASSED, GATE_FAILED, BASELINE_BROKEN, UNWAIVED_SURVIVOR, CONFIG_OR_TOOL}
)
_CLONE_TEXT = ("first_file", "second_file")
_CLONE_INT = ("first_start", "first_end", "second_start", "second_end", "lines", "tokens")
_REQUIRED_SAVED = (
    "schema_version",
    "commit",
    "base",
    "generated_at",
    "tool_versions",
    "gates",
    "focus",
    "top_crap",
    "reproduce",
    "exit_code",
)


def write_saved_markdown(source: Path, destination: Path, lang: Language) -> int:
    text, code = render_saved(source, lang)
    _replace_text(destination, text)
    return code


def render_saved(source: Path, lang: Language) -> tuple[str, int]:
    report = load_saved_report(source)
    return to_markdown(report, lang), report.exit_code


def load_saved_report(directory: Path) -> Report:
    path = directory / "report.json"
    payload = _saved_object(_read_saved(path), path)
    _require_saved(payload, path)
    _schema_version(payload["schema_version"], path)
    return _saved_report(payload, path)


def _read_saved(path: Path) -> object:
    if not path.is_file():
        raise ConfigError(msg("report.input_missing", path=path))
    try:
        return json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise _invalid_saved(path) from None


def _saved_object(payload: object, path: Path) -> dict[str, object]:
    if isinstance(payload, dict):
        return payload
    raise _invalid_saved(path)


def _require_saved(payload: dict[str, object], path: Path) -> None:
    if any(key not in payload for key in _REQUIRED_SAVED):
        raise _invalid_saved(path)


def _schema_version(value: object, path: Path) -> None:
    if type(value) is not int or value != 1:
        raise _invalid_saved(path)


def _saved_report(payload: dict[str, object], path: Path) -> Report:
    return Report(
        schema_version=1,
        commit=_text(payload["commit"], path),
        base=_text(payload["base"], path),
        generated_at=_text(payload["generated_at"], path),
        tool_versions=_versions(payload["tool_versions"], path),
        gates=_gates(payload["gates"], path),
        focus=_focus_rows(payload["focus"], path),
        top_crap=_metric_rows(payload["top_crap"], path),
        old_debt=_debt_rows(payload.get("old_debt", []), path),
        dependencies=_edge_rows(payload.get("dependencies", []), path),
        old_dependencies=_edge_rows(payload.get("old_dependencies", []), path),
        clones=_clones(payload.get("clones", []), path),
        reproduce=_text(payload["reproduce"], path),
        exit_code=_exit_code(payload["exit_code"], path),
        waivers=_dicts(payload.get("waivers", []), path),
        survivors=_survivor_rows(payload.get("survivors", []), path),
        mutation=_optional_mutation(payload, path),
        dead_code=_dead_section(payload, path),
        secrets=_secrets(payload, path),
        security=_security(payload, path),
        typing=_typing(payload, path),
    )


_JUDGED = {"fail": Fail, "warn": Warn, "off_diff": OffDiff}


def _security(payload: dict[str, object], path: Path) -> SecurityReport | None:
    if "security" not in payload:
        return None
    value = payload["security"]
    if not isinstance(value, dict) or "findings" not in value or "unmeasured" not in value:
        raise _invalid_saved(path)
    findings = tuple(_judged(row, path) for row in _dicts(value["findings"], path))
    return SecurityReport(findings, tuple(_string_list(value["unmeasured"], path)))


def _judged(row: dict[str, object], path: Path) -> Judged:
    finding = Finding(
        _text(row.get("tool"), path),
        _text(row.get("rule"), path),
        _text(row.get("file"), path),
        _integer(row.get("line"), path),
        _integer(row.get("end_line"), path),
        Severity(_text(row.get("severity"), path)),
    )
    disposition = row.get("disposition")
    waiver = row.get("waiver")
    if disposition == "waived":
        if not isinstance(waiver, str) or waiver == "":
            raise _invalid_saved(path)
        return Waived(finding, waiver)
    kind = _JUDGED.get(disposition) if isinstance(disposition, str) else None
    if kind is None or waiver is not None:
        raise _invalid_saved(path)
    return kind(finding)


def _typing(payload: dict[str, object], path: Path) -> dict[str, object] | None:
    if "typing" not in payload:
        return None
    value = payload["typing"]
    if not isinstance(value, dict) or "findings" not in value:
        raise _invalid_saved(path)
    for row in _dicts(value["findings"], path):
        _text(row.get("file"), path)
        _integer(row.get("line"), path)
        _text(row.get("code"), path)
        _text(row.get("disposition"), path)
        _text(row.get("waiver_id"), path)
    return value


def _string_list(value: object, path: Path) -> list[str]:
    if not isinstance(value, list):
        raise _invalid_saved(path)
    return [_text(item, path) for item in value]


def _secrets(payload: dict[str, object], path: Path) -> SecretLedger | None:
    if "secrets" not in payload:
        return None
    try:
        rows = tuple(_secret_row(row, path) for row in _dicts(payload["secrets"], path))
        return SecretLedger(rows)
    except ValueError:
        raise _invalid_saved(path) from None


def _secret_row(row: dict[str, object], path: Path) -> SecretRow:
    return SecretRow(
        _text(row.get("file"), path),
        _integer(row.get("line"), path),
        _text(row.get("rule_id"), path),
    )


def _dead_section(payload: dict[str, object], path: Path) -> DeadSection | None:
    if "dead_code" not in payload:
        return None
    value = payload["dead_code"]
    if not isinstance(value, dict) or "symbols" not in value:
        raise _invalid_saved(path)
    rows = tuple(_ledger_row(row, path) for row in _dicts(value["symbols"], path))
    return DeadSection(rows)


def _ledger_row(row: dict[str, object], path: Path) -> LedgerRow:
    file = _text(row.get("file"), path)
    line = _integer(row.get("line"), path)
    if line < 1:
        raise _invalid_saved(path)
    return LedgerRow(_dead_symbol(row, file, line, path), _waiver(row, path))


def _waiver(row: dict[str, object], path: Path) -> str | None:
    if "waiver" not in row or row["waiver"] is None:
        return None
    return _text(row["waiver"], path)


def _dead_symbol(
    row: dict[str, object], file: str, line: int, path: Path
) -> PythonDead | TypeScriptDead:
    name = _text(row.get("name"), path)
    kind = row.get("kind")
    if not isinstance(kind, str):
        raise _invalid_saved(path)
    language = row.get("language")
    if language == "python":
        found = _VULTURE_KIND.get(kind)
        if found is None:
            raise _invalid_saved(path)
        return PythonDead(file, line, name, found, _confidence(row, path))
    if language == "typescript":
        found = _KNIP_KIND.get(kind)
        if found is None:
            raise _invalid_saved(path)
        if row.get("confidence") is not None:
            raise _invalid_saved(path)
        return TypeScriptDead(file, line, name, found)
    raise _invalid_saved(path)


def _confidence(row: dict[str, object], path: Path) -> int:
    value = row.get("confidence")
    if type(value) is int and 0 <= value <= 100:
        return value
    raise _invalid_saved(path)


def _exit_code(value: object, path: Path) -> int:
    if type(value) is int and value in _SAVED_EXIT_CODES:
        return value
    raise _invalid_saved(path)


def _versions(value: object, path: Path) -> dict[str, str]:
    if not isinstance(value, dict):
        raise _invalid_saved(path)
    versions: dict[str, str] = {}
    for key, item in value.items():
        versions[key] = _text(item, path)
    return versions


def _gates(value: object, path: Path) -> list[GateResult]:
    return [_gate(row, path) for row in _dicts(value, path)]


def _gate(row: dict[str, object], path: Path) -> GateResult:
    reason = row.get("reason")
    if reason is not None and not isinstance(reason, str):
        raise _invalid_saved(path)
    return GateResult(_text(row.get("name"), path), _status(row.get("status"), path), reason)


def _status(value: object, path: Path) -> GateStatus:
    if value == "passed":
        return "passed"
    if value == "warn":
        return "warn"
    if value == "failed":
        return "failed"
    if value == "not_run":
        return "not_run"
    raise _invalid_saved(path)


def _focus_rows(value: object, path: Path) -> list[dict[str, object]]:
    rows = _dicts(value, path)
    for row in rows:
        _text(row.get("file"), path)
        if "risk" not in row:
            raise _invalid_saved(path)
    return rows


def _metric_rows(value: object, path: Path) -> list[dict[str, object]]:
    rows = _dicts(value, path)
    for row in rows:
        _metric_row(row, path)
    return rows


def _metric_row(row: dict[str, object], path: Path) -> None:
    _text(row.get("name"), path)
    _text(row.get("file"), path)
    _integer(row.get("start_line"), path)
    _number(row.get("coverage"), path)
    _number(row.get("cc"), path)
    _number(row.get("crap"), path)
    if "delta" in row and row["delta"] is not None:
        _number(row["delta"], path)


def _debt_rows(value: object, path: Path) -> list[dict[str, object]]:
    rows = _dicts(value, path)
    for row in rows:
        _text(row.get("name"), path)
        _text(row.get("file"), path)
        _integer(row.get("start_line"), path)
        _number(row.get("crap"), path)
    return rows


def _edge_rows(value: object, path: Path) -> list[dict[str, object]]:
    rows = _dicts(value, path)
    for row in rows:
        _text(row.get("origin"), path)
        _text(row.get("destination"), path)
        _text(row.get("rule"), path)
    return rows


def _clones(value: object, path: Path) -> list[Clone]:
    return [_clone(row, path) for row in _dicts(value, path)]


def _clone(row: dict[str, object], path: Path) -> Clone:
    texts = {key: _text(row.get(key), path) for key in _CLONE_TEXT}
    ints = {key: _integer(row.get(key), path) for key in _CLONE_INT}
    return Clone(
        first_file=texts["first_file"],
        first_start=ints["first_start"],
        first_end=ints["first_end"],
        second_file=texts["second_file"],
        second_start=ints["second_start"],
        second_end=ints["second_end"],
        lines=ints["lines"],
        tokens=ints["tokens"],
        similarity=_optional_number(row, "similarity", path),
        kind=_optional_text(row, "kind", path),
    )


def _survivor_rows(value: object, path: Path) -> list[dict[str, object]]:
    rows = _dicts(value, path)
    for row in rows:
        _text(row.get("id"), path)
        _text(row.get("function"), path)
        _text(row.get("file"), path)
        _integer(row.get("line"), path)
    return rows


def _optional_mutation(payload: dict[str, object], path: Path) -> dict[str, object] | None:
    if "mutation" not in payload or payload["mutation"] is None:
        return None
    value = payload["mutation"]
    if not isinstance(value, dict):
        raise _invalid_saved(path)
    if "no_coverage" in value:
        _no_coverage(value["no_coverage"], path)
    return value


def _no_coverage(value: object, path: Path) -> None:
    if not isinstance(value, dict):
        raise _invalid_saved(path)
    _integer(value.get("total"), path)
    for row in _dicts(value.get("functions"), path):
        _text(row.get("file"), path)
        _text(row.get("function"), path)
        _integer(row.get("count"), path)


def _dicts(value: object, path: Path) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise _invalid_saved(path)
    rows: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            raise _invalid_saved(path)
        rows.append(item)
    return rows


def _optional_number(row: dict[str, object], key: str, path: Path) -> float | None:
    if key not in row or row[key] is None:
        return None
    return _number(row[key], path)


def _optional_text(row: dict[str, object], key: str, path: Path) -> str:
    if key not in row:
        return ""
    return _text(row[key], path)


def _text(value: object, path: Path) -> str:
    if isinstance(value, str):
        return value
    raise _invalid_saved(path)


def _integer(value: object, path: Path) -> int:
    if type(value) is int:
        return value
    raise _invalid_saved(path)


def _number(value: object, path: Path) -> float:
    if type(value) in {int, float}:
        return float(value)
    raise _invalid_saved(path)


def _replace_text(destination: Path, text: str) -> None:
    temporary = destination.with_name(destination.name + ".tmp")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(text)
        os.replace(temporary, destination)
    except OSError:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise ConfigError(msg("report.output_failed", path=destination)) from None


def _invalid_saved(path: Path) -> ConfigError:
    return ConfigError(msg("report.input_invalid", path=path))
