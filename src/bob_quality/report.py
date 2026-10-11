"""Renderiza o relatório schema v1 em `.bob/report.md` e `report.json`."""

from __future__ import annotations

import json
from pathlib import Path

from bob_quality.models import Clone, FunctionMetric, GateStatus, Report

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
        "clones": [clone_row(clone) for clone in report.clones],
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
            suffix = ", clone" if item.get("clone") else ""
            lines.append(f"- `{item['file']}` (risco {item['risk']}{suffix})")
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
    if report.old_debt:
        lines.extend(["", "## Informação (dívida antiga)", ""])
        for fn in report.old_debt:
            loc = f"{fn['file']}:{fn['start_line']}"
            lines.append(
                f"- `{fn['name']}` em `{loc}` CRAP {fn['crap']} (fora do diff; não bloqueia)"
            )
    lines.extend(["", "## Clones novos", ""])
    lines.extend(_clone_lines(report))
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


def _clone_lines(report: Report) -> list[str]:
    if report.clones:
        return [_clone_line(clone) for clone in report.clones]
    dry = next((gate for gate in report.gates if gate.name == "dry"), None)
    if dry is not None and dry.status == "passed":
        return ["Nenhum clone novo no diff."]
    if dry is not None and dry.reason:
        return [f"Não executado ({dry.reason})."]
    return ["Não executado."]


def _clone_line(clone: Clone) -> str:
    left = f"`{clone.first_file}:{clone.first_start}-{clone.first_end}`"
    right = f"`{clone.second_file}:{clone.second_start}-{clone.second_end}`"
    return (
        f"- {left} ↔ {right} — {clone.lines} linhas, {clone.tokens} tokens, "
        f"similaridade {_similarity(clone)}"
    )


def _similarity(clone: Clone) -> str:
    if clone.similarity is not None:
        return f"{clone.similarity * 100:.0f}%"
    if clone.kind == "exact":
        return "exata"
    if clone.kind:
        return clone.kind
    return "—"


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
