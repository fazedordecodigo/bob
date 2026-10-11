"""Renderiza o relatório schema v1 em `.bob/report.md` e `report.json`."""

from __future__ import annotations

import json
from pathlib import Path

from bob_quality.models import FunctionMetric, GateStatus, Report

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
        "waivers": report.waivers,
        "survivors": report.survivors,
        "mutation": report.mutation,
        "reproduce": report.reproduce,
        "exit_code": report.exit_code,
    }


def to_markdown(report: Report) -> str:
    lines = ["# Relatório bob", ""]
    if report.waivers or report.mutation is not None:
        lines.extend(_waiver_section(report.waivers))
    lines.extend(_heading_lines(report))
    lines.extend(_verdict_lines(report))
    lines.extend(_focus_lines(report))
    lines.extend(_top_lines(report))
    lines.extend(_debt_lines(report))
    lines.extend(_survivor_lines(report))
    lines.extend(["", "## Como reproduzir", "", "```", report.reproduce, "```", ""])
    return "\n".join(lines)


def _heading_lines(report: Report) -> list[str]:
    return [
        f"- Commit: `{report.commit}`",
        f"- Base: `{report.base}`",
        f"- Data: {report.generated_at}",
        f"- Ferramentas: {_tools(report.tool_versions)}",
        "",
    ]


def _verdict_lines(report: Report) -> list[str]:
    lines = ["## Veredito", ""]
    for gate in report.gates:
        extra = f" ({gate.reason})" if gate.reason else ""
        lines.append(f"- {GATE_MARK[gate.status]} `{gate.name}`: {_status_label(gate.status)}{extra}")
    return lines


def _focus_lines(report: Report) -> list[str]:
    lines = ["", "## Onde focar o review", ""]
    if not report.focus:
        lines.append("- Nenhum arquivo alterado com risco de CRAP.")
        return lines
    for item in report.focus:
        lines.append(f"- `{item['file']}` (risco {item['risk']})")
    return lines


def _top_lines(report: Report) -> list[str]:
    lines = ["", "## Top 5 funções por CRAP (diff)", ""]
    if not report.top_crap:
        lines.append("Nenhuma função alterada medida.")
        return lines
    lines.append("| Função | Arquivo | CC | Cobertura | CRAP | Delta |")
    lines.append("|---|---|---:|---:|---:|---|")
    for fn in report.top_crap:
        lines.append(_top_row(fn))
    return lines


def _top_row(fn: dict[str, object]) -> str:
    loc = f"{fn['file']}:{fn['start_line']}"
    cov = f"{float(fn['coverage']) * 100:.0f}%"
    delta = "—" if fn.get("delta") is None else fn["delta"]
    return f"| {fn['name']} | {loc} | {fn['cc']} | {cov} | {fn['crap']} | {delta} |"


def _debt_lines(report: Report) -> list[str]:
    if not report.old_debt:
        return []
    lines = ["", "## Informação (dívida antiga)", ""]
    for fn in report.old_debt:
        loc = f"{fn['file']}:{fn['start_line']}"
        lines.append(f"- `{fn['name']}` em `{loc}` CRAP {fn['crap']} (fora do diff; não bloqueia)")
    return lines


def _survivor_lines(report: Report) -> list[str]:
    if report.mutation is None:
        return []
    lines = ["", "## Mutantes sobreviventes", ""]
    if not report.survivors:
        lines.append("Nenhum mutante sobrevivente.")
        return lines
    lines.append("| Id | Função | Local | Operador | Waiver |")
    lines.append("|---|---|---|---|---|")
    for item in report.survivors:
        lines.append(_survivor_row(item))
    return lines


def _survivor_row(item: dict[str, object]) -> str:
    waiver = item.get("waiver") or "—"
    operator = str(item.get("operator") or "—").replace("|", "\\|")
    return (
        f"| `{item['id']}` | {item['function']} | {item['file']}:{item['line']} | {operator} | {waiver} |"
    )


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


def _waiver_section(waivers: list[dict[str, object]]) -> list[str]:
    lines = ["## Waivers", ""]
    if not waivers:
        lines.append("Nenhum waiver.")
        lines.append("")
        return lines
    lines.append("| Alvo | Motivo | Autor | Data |")
    lines.append("|---|---|---|---|")
    for item in waivers:
        reason = str(item.get("reason") or "").replace("|", "\\|")
        lines.append(
            f"| `{item.get('id', '')}` | {reason} | {item.get('author', '')} | {item.get('date', '')} |"
        )
    lines.append("")
    return lines


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
