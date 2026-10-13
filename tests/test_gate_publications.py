from __future__ import annotations

from pathlib import Path

from bob_quality.doctor import NODE, node_range

ROOT = Path(__file__).resolve().parents[1]

FAST_GATES = "crap,dry,deps"
CI_GATES = FAST_GATES + ",mutate"
HOOK_EXEC = f"exec bob check --gates {FAST_GATES} </dev/null"
HOOK_COMMAND = f"bob check --gates {FAST_GATES}"
CI_COMMAND = f"bob check --gates {CI_GATES}"
SKILL_PARAGRAPH = (
    f"Por padrão, o hook local roda `{HOOK_COMMAND}`. "
    f"O CI roda `{CI_COMMAND}`. "
    f"Um `bob check` sem `--gates` roda `{FAST_GATES}` e não roda `mutate`."
)


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _only_line(text: str, prefix: str) -> str:
    found = [line for line in text.splitlines() if line.startswith(prefix)]
    assert len(found) == 1, found
    return found[0]


def _first_backtick_span(line: str) -> str:
    start = line.find("`")
    if start < 0:
        return ""
    end = line.find("`", start + 1)
    if end < 0:
        return ""
    return line[start + 1 : end]


def test_pre_push_exec_line_is_the_fast_gates() -> None:
    exec_lines = [
        line
        for line in _text("src/bob_quality/hooks/pre-push").splitlines()
        if line.startswith("exec ")
    ]
    assert exec_lines == [HOOK_EXEC]


def test_skill_paragraph_names_the_hook_and_the_ci_command() -> None:
    body = _text("skills/bob-check/SKILL.md")
    assert SKILL_PARAGRAPH in body
    assert "CI: `bob check` (todos os gates, inclusive `mutate`)" not in body
    assert "no CI executa todos" not in body


def test_skill_hook_and_ci_bullets_quote_the_commands() -> None:
    body = _text("skills/bob-check/SKILL.md")
    assert _first_backtick_span(_only_line(body, "- Hook local:")) == HOOK_COMMAND
    assert _first_backtick_span(_only_line(body, "- CI:")) == CI_COMMAND


def test_cli_guide_names_the_hook_gates() -> None:
    body = _text("docs/cli.md")
    assert f"| Hook `pre-push` | `{FAST_GATES}` |" in body
    assert "O script do hook passa `crap,deps`" not in body
    assert "ainda grava o relatório de erro" not in body
    for relative in ("docs/cli.md", "docs/instalacao.md", "docs/README.md", "docs/visao-geral.md"):
        assert "bob check --gates crap,deps" not in _text(relative), relative


def test_guides_do_not_say_invalid_duplication_writes_a_report() -> None:
    stale = "o relatório de erro é gravado no idioma"
    for relative in ("docs/cli.md", "docs/exit-codes.md", "docs/configuracao.md", "docs/relatorios.md"):
        assert stale not in _text(relative), relative


def test_readmes_publish_the_fast_hook_command() -> None:
    english = _text("README.md")
    portuguese = _text("README.pt-BR.md")
    assert f'agent --> hook["pre-push hook<br/>{HOOK_COMMAND}"]' in english
    assert f"runs `{HOOK_COMMAND}`, the fast gates." in english
    assert f'agent --> hook["hook pre-push<br/>{HOOK_COMMAND}"]' in portuguese
    assert f"roda `{HOOK_COMMAND}`, os gates rápidos." in portuguese
    old = "bob check --gates crap,deps"
    assert old not in english
    assert old not in portuguese


_NODE_DOCS = (
    "AGENTS.md",
    "README.md",
    "README.pt-BR.md",
    "docs/instalacao.md",
    "docs/contribuicao.md",
    "docs/cli.md",
    "docs/gates.md",
)


def test_docs_publish_the_node_range_the_doctor_accepts() -> None:
    printed = node_range(NODE)
    assert printed == ">=22.14.0 <23"
    for relative in _NODE_DOCS:
        assert printed in _text(relative), relative
    assert "essa versão exata" not in _text("AGENTS.md")
    assert "any Node other than 22.14.0" not in _text("README.md")
    assert "qualquer Node diferente de 22.14.0" not in _text("README.pt-BR.md")
