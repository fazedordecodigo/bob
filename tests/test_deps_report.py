"""Seções de dependência do report.md, montadas direto do `Report`."""

from bob_quality.models import GateResult, Report
from bob_quality.report import to_markdown

OLD_CYCLE = {"origin": "app.b", "destination": "app.a", "rule": "Ciclo"}
NEW_EDGE = {"origin": "app.api", "destination": "app.domain", "rule": "Camadas"}


def _report(gates: list[GateResult], **extra: object) -> Report:
    return Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-11T00:00:00+00:00",
        tool_versions={"import-linter": "2.15"},
        gates=gates,
        focus=[],
        top_crap=[],
        reproduce="bob deps",
        **extra,
    )


def test_markdown_with_mutation_lists_waivers_dependencies_and_old_cycles() -> None:
    report = _report(
        [GateResult("deps", "passed", None)],
        old_dependencies=[OLD_CYCLE],
        mutation={"remutated": [], "reused": []},
    )

    assert to_markdown(report) == (
        "# Relatório bob\n\n"
        "## Waivers\n\nNenhum waiver.\n\n"
        "- Commit: `abc`\n- Base: `main`\n- Data: 2026-10-11T00:00:00+00:00\n"
        "- Ferramentas: import-linter 2.15\n\n"
        "## Veredito\n\n- ✅ `deps`: passou\n\n"
        "## Onde focar o review\n\n- Nenhum arquivo alterado com risco de CRAP.\n\n"
        "## Top 5 funções por CRAP (diff)\n\nNenhuma função alterada medida.\n\n"
        "## Violações e ciclos de dependência\n\n- Nenhuma violação de dependência.\n\n"
        "## Informação (dependências fora do diff)\n\n"
        "- `app.b → app.a` (Ciclo) (fora do diff; não bloqueia)\n\n"
        "## Clones novos\n\nNão executado.\n\n"
        "## Mutantes sobreviventes\n\nNenhum mutante sobrevivente.\n\n"
        "## Como reproduzir\n\n```\nbob deps\n```\n"
    )


def test_markdown_with_mutation_puts_each_waiver_in_the_table() -> None:
    waiver = {"id": "m.x__mutmut_1", "reason": "equivalente", "author": "E", "date": "2026-10-11"}
    report = _report(
        [GateResult("deps", "passed", None)],
        waivers=[waiver],
        mutation={"remutated": [], "reused": []},
    )

    assert to_markdown(report).startswith(
        "# Relatório bob\n\n## Waivers\n\n| Alvo | Motivo | Autor | Data |\n|---|---|---|---|\n"
        "| `m.x__mutmut_1` | equivalente | E | 2026-10-11 |\n\n"
    )


def test_markdown_without_mutation_or_old_cycles_skips_those_sections() -> None:
    markdown = to_markdown(_report([GateResult("deps", "passed", None)]))

    assert "## Waivers" not in markdown
    assert "## Informação (dependências fora do diff)" not in markdown


def test_deps_section_says_not_run_when_the_gate_is_absent_or_skipped() -> None:
    absent = to_markdown(_report([]))
    skipped = to_markdown(_report([GateResult("deps", "not_run", "Node ausente")]))

    expected = "## Violações e ciclos de dependência\n\n- Gate não executado.\n"
    assert expected in absent
    assert expected in skipped


def test_failed_deps_gate_lists_each_edge_instead_of_the_reason() -> None:
    report = _report([GateResult("deps", "failed", "motivo")], dependencies=[NEW_EDGE])

    markdown = to_markdown(report)

    assert (
        "## Violações e ciclos de dependência\n\n- `app.api → app.domain` (Camadas)\n"
    ) in markdown
    assert "- motivo" not in markdown
