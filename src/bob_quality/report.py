"""Renderiza o relatório schema v1 em `.bob/report.md` e `report.json`."""

from __future__ import annotations

import json
from pathlib import Path

from bob_quality.models import DepViolation, FunctionMetric, GateResult, GateStatus, Report

GATE_MARK: dict[GateStatus, str] = {
    "passed": "✅",
    "warn": "⚠️",
    "failed": "❌",
    "not_run": "⏭️",
}


def write_report(report: Report, out_dir: Path, fmt: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if fmt in {"json", "both"}:
        (out_dir / "report.json").write_text(json.dumps(to_json(report), indent=2) + "\n")
    if fmt in {"md", "both"}:
        (out_dir / "report.md").write_text(to_markdown(report))


def to_json(report: Report) -> dict[str, object]:
    return {
        "schema_version": report.schema_version,
        "commit": report.commit,
        "base": report.base,
        "generated_at": report.generated_at,
        "tool_versions": report.tool_versions,
        "gates": [
            {"name": gate.name, "status": gate.status, "reason": gate.reason}
            for gate in report.gates
        ],
        "focus": report.focus,
        "top_crap": report.top_crap,
        "old_debt": report.old_debt,
        "dependencies": report.dependencies,
        "old_dependencies": report.old_dependencies,
        "reproduce": report.reproduce,
        "exit_code": report.exit_code,
    }


def to_markdown(report: Report) -> str:
    lines = [
        "# Relatório bob",
        "",
        f"- Commit: `{report.commit}`",
        f"- Base: `{report.base}`",
        f"- Data: {report.generated_at}",
        f"- Ferramentas: {_tools(report.tool_versions)}",
        "",
        "## Veredito",
        "",
    ]
    for gate in report.gates:
        mark = GATE_MARK[gate.status]
        label = _status_label(gate.status)
        extra = f" ({gate.reason})" if gate.reason else ""
        lines.append(f"- {mark} `{gate.name}`: {label}{extra}")
    lines.extend(["", "## Onde focar o review", ""])
    if report.focus:
        for item in report.focus:
            lines.append(f"- `{item['file']}` (risco {item['risk']})")
    else:
        lines.append("- Nenhum arquivo alterado com risco de CRAP.")
    lines.extend(["", "## Top 5 funções por CRAP (diff)", ""])
    if report.top_crap:
        lines.append("| Função | Arquivo | CC | Cobertura | CRAP | Delta |")
        lines.append("|---|---|---:|---:|---:|---|")
        for fn in report.top_crap:
            loc = f"{fn['file']}:{fn['start_line']}"
            cov = f"{float(fn['coverage']) * 100:.0f}%"
            delta = "—" if fn.get("delta") is None else fn["delta"]
            lines.append(
                f"| {fn['name']} | {loc} | {fn['cc']} | {cov} | {fn['crap']} | {delta} |"
            )
    else:
        lines.append("Nenhuma função alterada medida.")
    lines.extend(_old_debt_lines(report))
    lines.extend(_dependency_lines(report))
    lines.extend(
        [
            "",
            "## Como reproduzir",
            "",
            "```",
            report.reproduce,
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _old_debt_lines(report: Report) -> list[str]:
    if not report.old_debt:
        return []
    lines = ["", "## Informação (dívida antiga)", ""]
    for fn in report.old_debt:
        loc = f"{fn['file']}:{fn['start_line']}"
        lines.append(
            f"- `{fn['name']}` em `{loc}` CRAP {fn['crap']} (fora do diff; não bloqueia)"
        )
    return lines


def _dependency_lines(report: Report) -> list[str]:
    lines = ["", "## Violações e ciclos de dependência", ""]
    lines.extend(_dependency_items(report))
    lines.extend(_old_dependency_lines(report))
    return lines


def _dependency_items(report: Report) -> list[str]:
    gate = _gate_named(report, "deps")
    if gate is None or gate.status == "not_run":
        return ["- Gate não executado."]
    if gate.status == "failed" and not report.dependencies:
        return [f"- {gate.reason}"]
    if not report.dependencies:
        return ["- Nenhuma violação de dependência."]
    return [_dependency_item(item) for item in report.dependencies]


def _dependency_item(item: dict[str, object]) -> str:
    return f"- `{item['origin']} → {item['destination']}` ({item['rule']})"


def _gate_named(report: Report, name: str) -> GateResult | None:
    for gate in report.gates:
        if gate.name == name:
            return gate
    return None


def _old_dependency_lines(report: Report) -> list[str]:
    if not report.old_dependencies:
        return []
    lines = ["", "## Informação (dependências fora do diff)", ""]
    for item in report.old_dependencies:
        lines.append(f"{_dependency_item(item)} (fora do diff; não bloqueia)")
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


def _tools(versions: dict[str, str]) -> str:
    if not versions:
        return "—"
    return ", ".join(f"{name} {ver}" for name, ver in versions.items())


def _status_label(status: str) -> str:
    labels = {
        "passed": "passou",
        "warn": "aviso",
        "failed": "falhou",
        "not_run": "não executado",
    }
    return labels[status]
