"""report.md em cada idioma e report.json sempre igual, montados direto do `Report`."""

from dataclasses import replace

from bob_quality.messages import msg
from bob_quality.models import Clone, GateResult, Report
from bob_quality.report import to_json, to_markdown

WAIVER = {"id": "m.x__mutmut_1", "reason": "equivalent", "author": "E", "date": "2026-10-11"}
SURVIVOR = {
    "id": "app.weak.x_classify__mutmut_1",
    "function": "classify",
    "file": "src/app/weak.py",
    "line": 2,
    "operator": "ROR",
    "waiver": "m.x__mutmut_1",
}
MESSY = {
    "name": "messy",
    "file": "src/app/risky.py",
    "start_line": 1,
    "cc": 4,
    "coverage": 0.0,
    "crap": 20.0,
    "delta": None,
}
LEGACY = {"name": "legacy", "file": "src/app/old.py", "start_line": 3, "crap": 12.0}
ORPHAN = {"file": "src/app/orphan.py", "function": "orphan", "count": 2}


def _rich() -> Report:
    return Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-11T00:00:00+00:00",
        tool_versions={"lizard": "1.24.1", "mutmut": "3.8.0"},
        gates=[
            GateResult("crap", "failed", "CRAP >= 10.0: messy@src/app/risky.py:1"),
            GateResult("dry", "warn", msg("dry.clones", count=3)),
            GateResult("deps", "passed", None),
            GateResult("mutate", "not_run", msg("tool.missing", tool="mutmut")),
        ],
        focus=[
            {"file": "src/app/risky.py", "risk": 20.0},
            {"file": "src/app/twin.py", "risk": 2.0, "clone": True},
        ],
        top_crap=[MESSY],
        old_debt=[LEGACY],
        dependencies=[{"origin": "app.api", "destination": "app.domain", "rule": "layers"}],
        old_dependencies=[{"origin": "app.b", "destination": "app.a", "rule": "cycle"}],
        clones=[
            Clone("src/a.py", 1, 11, "src/b.py", 1, 11, 11, 88, None, "exact"),
            Clone("src/c.py", 2, 9, "src/d.py", 4, 11, 8, 60, 0.93),
            Clone("src/e.py", 1, 5, "src/f.py", 1, 5, 5, 40, None, "near"),
            Clone("src/g.py", 1, 5, "src/h.py", 1, 5, 5, 40),
        ],
        reproduce="bob check --base main",
        waivers=[WAIVER],
        survivors=[SURVIVOR],
        mutation={"remutated": [], "reused": [], "no_coverage": {"total": 2, "functions": [ORPHAN]}},
    )


def _empty(gates: list[GateResult]) -> Report:
    return Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-11T00:00:00+00:00",
        tool_versions={},
        gates=gates,
        focus=[],
        top_crap=[],
        reproduce="bob check",
        mutation={"remutated": [], "reused": [], "no_coverage": {"total": 0, "functions": []}},
    )


RICH_EN = """# bob report

## Waivers

| Target | Reason | Author | Date |
|---|---|---|---|
| `m.x__mutmut_1` | equivalent | E | 2026-10-11 |

- Commit: `abc`
- Base: `main`
- Date: 2026-10-11T00:00:00+00:00
- Tools: lizard 1.24.1, mutmut 3.8.0

## Verdict

- ❌ `crap`: failed (CRAP >= 10.0: messy@src/app/risky.py:1)
- ⚠️ `dry`: warning (3 new clones in the diff)
- ✅ `deps`: passed
- ⏭️ `mutate`: not run (missing tool: mutmut)

## Where to focus the review

- `src/app/risky.py` (risk 20.0)
- `src/app/twin.py` (risk 2.0, clone)

## Top 5 functions by CRAP (diff)

| Function | File | CC | Coverage | CRAP | Delta |
|---|---|---:|---:|---:|---|
| messy | src/app/risky.py:1 | 4 | 0% | 20.0 | — |

## Information (old debt)

- `legacy` at `src/app/old.py:3` CRAP 12.0 (outside the diff; does not block)

## Dependency violations and cycles

- `app.api → app.domain` (layers)

## Information (dependencies outside the diff)

- `app.b → app.a` (cycle) (outside the diff; does not block)

## New clones

- `src/a.py:1-11` ↔ `src/b.py:1-11` — 11 lines, 88 tokens, similarity exact
- `src/c.py:2-9` ↔ `src/d.py:4-11` — 8 lines, 60 tokens, similarity 93%
- `src/e.py:1-5` ↔ `src/f.py:1-5` — 5 lines, 40 tokens, similarity near
- `src/g.py:1-5` ↔ `src/h.py:1-5` — 5 lines, 40 tokens, similarity —

## Surviving mutants

| Id | Function | Location | Operator | Waiver |
|---|---|---|---|---|
| `app.weak.x_classify__mutmut_1` | classify | src/app/weak.py:2 | ROR | m.x__mutmut_1 |

## Mutants without tests

❌ Total: 2. Blocks.

| Function | File | Mutants |
|---|---|---:|
| orphan | src/app/orphan.py | 2 |

## How to reproduce

```
bob check --base main --lang en
```
"""

RICH_PT_BR = """# Relatório bob

## Waivers

| Alvo | Motivo | Autor | Data |
|---|---|---|---|
| `m.x__mutmut_1` | equivalent | E | 2026-10-11 |

- Commit: `abc`
- Base: `main`
- Data: 2026-10-11T00:00:00+00:00
- Ferramentas: lizard 1.24.1, mutmut 3.8.0

## Veredito

- ❌ `crap`: falhou (CRAP >= 10.0: messy@src/app/risky.py:1)
- ⚠️ `dry`: aviso (3 clones novos no diff)
- ✅ `deps`: passou
- ⏭️ `mutate`: não executado (ferramenta ausente: mutmut)

## Onde focar o review

- `src/app/risky.py` (risco 20.0)
- `src/app/twin.py` (risco 2.0, clone)

## Top 5 funções por CRAP (diff)

| Função | Arquivo | CC | Cobertura | CRAP | Delta |
|---|---|---:|---:|---:|---|
| messy | src/app/risky.py:1 | 4 | 0% | 20.0 | — |

## Informação (dívida antiga)

- `legacy` em `src/app/old.py:3` CRAP 12.0 (fora do diff; não bloqueia)

## Violações e ciclos de dependência

- `app.api → app.domain` (layers)

## Informação (dependências fora do diff)

- `app.b → app.a` (cycle) (fora do diff; não bloqueia)

## Clones novos

- `src/a.py:1-11` ↔ `src/b.py:1-11` — 11 linhas, 88 tokens, similaridade exata
- `src/c.py:2-9` ↔ `src/d.py:4-11` — 8 linhas, 60 tokens, similaridade 93%
- `src/e.py:1-5` ↔ `src/f.py:1-5` — 5 linhas, 40 tokens, similaridade near
- `src/g.py:1-5` ↔ `src/h.py:1-5` — 5 linhas, 40 tokens, similaridade —

## Mutantes sobreviventes

| Id | Função | Local | Operador | Waiver |
|---|---|---|---|---|
| `app.weak.x_classify__mutmut_1` | classify | src/app/weak.py:2 | ROR | m.x__mutmut_1 |

## Mutantes sem teste

❌ Total: 2. Bloqueia.

| Função | Arquivo | Mutantes |
|---|---|---:|
| orphan | src/app/orphan.py | 2 |

## Como reproduzir

```
bob check --base main --lang pt-BR
```
"""

EMPTY_EN = """# bob report

## Waivers

No waivers.

- Commit: `abc`
- Base: `main`
- Date: 2026-10-11T00:00:00+00:00
- Tools: —

## Verdict

- ✅ `deps`: passed
- ✅ `dry`: passed

## Where to focus the review

- No changed file with CRAP risk.

## Top 5 functions by CRAP (diff)

No changed function measured.

## Dependency violations and cycles

- No dependency violations.

## New clones

No new clones in the diff.

## Surviving mutants

No surviving mutants.

## Mutants without tests

No mutants without tests.

## How to reproduce

```
bob check --lang en
```
"""


def test_markdown_renders_every_section_in_english() -> None:
    assert to_markdown(_rich(), "en") == RICH_EN


def test_markdown_renders_every_section_in_portuguese() -> None:
    assert to_markdown(_rich(), "pt-BR") == RICH_PT_BR


def test_markdown_renders_the_empty_sections_in_english() -> None:
    report = _empty([GateResult("deps", "passed", None), GateResult("dry", "passed", None)])

    assert to_markdown(report, "en") == EMPTY_EN


def test_markdown_explains_why_dependencies_and_clones_were_not_measured() -> None:
    failed = _empty(
        [
            GateResult("deps", "failed", msg("deps.grimp_unreadable")),
            GateResult("dry", "not_run", msg("dry.node_missing")),
        ]
    )
    skipped = _empty([GateResult("deps", "not_run", None)])

    assert (
        "## Dependency violations and cycles\n\n"
        "- grimp returned an unreadable graph\n\n"
        "## New clones\n\n"
        "Not run (Node missing: install Node.js to run jscpd).\n\n"
    ) in to_markdown(failed, "en")
    assert (
        "## Dependency violations and cycles\n\n- Gate not run.\n\n## New clones\n\nNot run.\n\n"
    ) in to_markdown(skipped, "en")


def test_json_is_the_schema_with_english_reasons_whatever_the_markdown_language() -> None:
    near = Clone("src/c.py", 2, 9, "src/d.py", 4, 11, 8, 60, 0.93)
    report = replace(_rich(), clones=[near], exit_code=3)

    assert to_json(report) == {
        "schema_version": 1,
        "commit": "abc",
        "base": "main",
        "generated_at": "2026-10-11T00:00:00+00:00",
        "tool_versions": {"lizard": "1.24.1", "mutmut": "3.8.0"},
        "gates": [
            {"name": "crap", "status": "failed", "reason": "CRAP >= 10.0: messy@src/app/risky.py:1"},
            {"name": "dry", "status": "warn", "reason": "3 new clones in the diff"},
            {"name": "deps", "status": "passed", "reason": None},
            {"name": "mutate", "status": "not_run", "reason": "missing tool: mutmut"},
        ],
        "focus": [
            {"file": "src/app/risky.py", "risk": 20.0},
            {"file": "src/app/twin.py", "risk": 2.0, "clone": True},
        ],
        "top_crap": [MESSY],
        "old_debt": [LEGACY],
        "dependencies": [{"origin": "app.api", "destination": "app.domain", "rule": "layers"}],
        "old_dependencies": [{"origin": "app.b", "destination": "app.a", "rule": "cycle"}],
        "clones": [
            {
                "first_file": "src/c.py",
                "first_start": 2,
                "first_end": 9,
                "second_file": "src/d.py",
                "second_start": 4,
                "second_end": 11,
                "lines": 8,
                "tokens": 60,
                "similarity": 0.93,
                "kind": "",
            }
        ],
        "waivers": [WAIVER],
        "survivors": [SURVIVOR],
        "mutation": {
            "remutated": [],
            "reused": [],
            "no_coverage": {"total": 2, "functions": [ORPHAN]},
        },
        "reproduce": "bob check --base main",
        "exit_code": 3,
    }


def test_an_empty_reproduce_command_stays_blank_in_markdown() -> None:
    report = replace(_empty([GateResult("deps", "passed", None)]), reproduce="")

    assert "```\n\n```" in to_markdown(report, "en")


def test_catalog_rule_names_stay_english_in_json_and_follow_the_markdown_language() -> None:
    report = replace(
        _empty([GateResult("deps", "failed", "a → b")]),
        dependencies=[
            {"origin": "src/a.ts", "destination": "src/b.ts", "rule": msg("deps.unnamed")},
            {"origin": "app.right", "destination": "app.left", "rule": msg("deps.cycle_rule")},
        ],
    )

    payload = to_json(report)
    assert payload["dependencies"] == [
        {"origin": "src/a.ts", "destination": "src/b.ts", "rule": "dependency"},
        {"origin": "app.right", "destination": "app.left", "rule": "Forbidden dependency cycle"},
    ]
    portuguese = to_markdown(report, "pt-BR")
    english = to_markdown(report, "en")
    assert "`src/a.ts → src/b.ts` (dependência)" in portuguese
    assert "`app.right → app.left` (Proibido ciclo de dependência)" in portuguese
    assert "`src/a.ts → src/b.ts` (dependency)" in english
    assert "`app.right → app.left` (Forbidden dependency cycle)" in english


def test_waiver_rows_escape_pipes_and_leave_missing_fields_blank() -> None:
    piped = {"id": "m.x__mutmut_2", "reason": "a | b", "author": "E", "date": "2026-10-11"}
    report = replace(_empty([]), waivers=[piped, {}])

    assert (
        "## Waivers\n\n"
        "| Target | Reason | Author | Date |\n"
        "|---|---|---|---|\n"
        "| `m.x__mutmut_2` | a \\| b | E | 2026-10-11 |\n"
        "| `` |  |  |  |\n"
    ) in to_markdown(report, "en")


def test_markdown_marks_an_unwaived_survivor_outside_the_diff() -> None:
    outside = {**SURVIVOR, "waiver": None, "blocking": False}
    blocking = {**SURVIVOR, "waiver": None, "blocking": True}
    waived = {**SURVIVOR, "blocking": False}
    report = replace(_rich(), survivors=[outside])

    assert (
        "| `app.weak.x_classify__mutmut_1` | classify | "
        "src/app/weak.py:2 (outside the diff; does not block) | ROR | — |"
    ) in to_markdown(report, "en")
    assert (
        "| `app.weak.x_classify__mutmut_1` | classify | "
        "src/app/weak.py:2 (fora do diff; não bloqueia) | ROR | — |"
    ) in to_markdown(report, "pt-BR")
    assert to_json(report)["survivors"] == [outside]
    blocking_md = to_markdown(replace(_rich(), survivors=[blocking]), "en")
    waived_md = to_markdown(replace(_rich(), survivors=[waived]), "en")
    assert (
        "| `app.weak.x_classify__mutmut_1` | classify | src/app/weak.py:2 | ROR | — |"
    ) in blocking_md
    waived_row = next(line for line in waived_md.splitlines() if "x_classify" in line)
    assert "outside the diff" not in waived_row
