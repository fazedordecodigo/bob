from __future__ import annotations

from pathlib import Path

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
