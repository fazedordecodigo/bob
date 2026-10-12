"""Idioma da saída na CLI: --lang, BOB_LANG, `language` no bob.yaml e padrão en."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from helpers import RISKY_SOURCE, commit_on_branch, init_python_repo, run_bob

EN = "en"
PT = "pt-BR"

EXPECTED_MARKDOWN = {
    EN: """\
# bob report

- Commit: `<sha>`
- Base: `main`
- Date: <date>
- Tools: —

## Verdict

- ⏭️ `nope`: not run (gate not implemented in this slice)

## Where to focus the review

- No changed file with CRAP risk.

## Top 5 functions by CRAP (diff)

No changed function measured.

## Dependency violations and cycles

- Gate not run.

## New clones

Not run.

## How to reproduce

```
bob check --base main --gates nope
```
""",
    PT: """\
# Relatório bob

- Commit: `<sha>`
- Base: `main`
- Data: <date>
- Ferramentas: —

## Veredito

- ⏭️ `nope`: não executado (gate não implementado nesta fatia)

## Onde focar o review

- Nenhum arquivo alterado com risco de CRAP.

## Top 5 funções por CRAP (diff)

Nenhuma função alterada medida.

## Violações e ciclos de dependência

- Gate não executado.

## Clones novos

Não executado.

## Como reproduzir

```
bob check --base main --gates nope
```
""",
}


def _repo(tmp_path: Path, language: str | None = None) -> Path:
    repo = init_python_repo(tmp_path / "repo")
    if language is not None:
        config = repo / "bob.yaml"
        config.write_text(config.read_text() + f"language: {language}\n")
    return repo


def _markdown(repo: Path) -> str:
    text = (repo / ".bob" / "report.md").read_text()
    text = re.sub(r"- Commit: `[0-9a-f]+`", "- Commit: `<sha>`", text)
    return re.sub(r"- (Date|Data): .+", r"- \1: <date>", text)


@pytest.mark.parametrize(
    ("flag", "env", "configured", "expected"),
    [
        (None, None, None, EN),
        (PT, None, None, PT),
        (None, PT, None, PT),
        (None, None, PT, PT),
        (None, EN, PT, EN),
        (EN, PT, PT, EN),
        (PT, EN, EN, PT),
    ],
)
def test_report_md_follows_flag_then_env_then_yaml_then_en(
    tmp_path: Path, flag: str | None, env: str | None, configured: str | None, expected: str
) -> None:
    repo = _repo(tmp_path, configured)
    lang_args = ["--lang", flag] if flag else []

    result = run_bob(repo, "check", *lang_args, "--gates", "nope", "--base", "main", bob_lang=env)

    assert result.returncode == 0, result.stderr
    assert _markdown(repo) == EXPECTED_MARKDOWN[expected]


def test_lang_flag_also_works_before_the_command(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    result = run_bob(repo, "--lang", PT, "check", "--gates", "nope", "--base", "main")

    assert result.returncode == 0, result.stderr
    assert _markdown(repo) == EXPECTED_MARKDOWN[PT]


def test_report_json_is_byte_identical_in_both_languages(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    commit_on_branch(repo, "risky", "src/app/risky.py", RISKY_SOURCE, "add untested messy")
    raw: dict[str, bytes] = {}

    for lang in (EN, PT):
        result = run_bob(repo, "check", "--lang", lang, "--gates", "crap,nope", "--base", "main")
        assert result.returncode == 1, result.stderr
        report = (repo / ".bob" / "report.json").read_bytes()
        raw[lang] = re.sub(rb'"generated_at": "[^"]+"', b'"generated_at": ""', report)

    payload = json.loads(raw[EN])
    assert raw[EN] == raw[PT]
    assert payload["gates"] == [
        {"name": "crap", "status": "failed", "reason": "CRAP >= 10.0: messy@src/app/risky.py:1"},
        {"name": "nope", "status": "not_run", "reason": "gate not implemented in this slice"},
    ]
    assert payload["reproduce"] == "bob check --base main --gates crap,nope"


@pytest.mark.parametrize(
    ("args", "env", "shown"),
    [
        (("--lang", "fr"), None, "fr"),
        ((), "pt-br", "pt-br"),
    ],
)
def test_invalid_flag_or_env_exits_4_before_running(
    tmp_path: Path, args: tuple[str, ...], env: str | None, shown: str
) -> None:
    repo = _repo(tmp_path)

    result = run_bob(repo, "check", *args, "--gates", "nope", "--base", "main", bob_lang=env)

    assert result.returncode == 4
    assert result.stderr == f"invalid language: {shown} (use en or pt-BR)\n"
    assert result.stdout == ""
    assert not (repo / ".bob").exists()


@pytest.mark.parametrize(
    ("flag", "shown"),
    [
        (EN, "invalid language: fr (use en or pt-BR)"),
        (PT, "idioma inválido: fr (use en ou pt-BR)"),
    ],
)
def test_invalid_yaml_language_is_a_config_error_in_the_report(
    tmp_path: Path, flag: str, shown: str
) -> None:
    repo = _repo(tmp_path, "fr")

    result = run_bob(repo, "check", "--lang", flag, "--gates", "nope", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 4
    assert payload["gates"] == [
        {"name": "nope", "status": "not_run", "reason": "invalid language: fr (use en or pt-BR)"}
    ]
    assert f"`nope`: {'not run' if flag == EN else 'não executado'} ({shown})" in markdown


def test_valid_yaml_language_survives_another_invalid_key(tmp_path: Path) -> None:
    repo = _repo(tmp_path, PT)
    config = repo / "bob.yaml"
    config.write_text(config.read_text() + "duplication: [1]\n")

    result = run_bob(repo, "check", "--gates", "nope", "--base", "main")
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()

    assert result.returncode == 4
    assert payload["gates"] == [
        {"name": "nope", "status": "not_run", "reason": "duplication must be a mapping"}
    ]
    assert markdown.startswith("# Relatório bob\n")
    assert "duplication deve ser um mapeamento" in markdown


@pytest.mark.parametrize(
    ("args", "env", "expected"),
    [
        (("--help",), None, ["Quality gates for agents.", "Output language: en or pt-BR"]),
        (
            ("--lang", PT, "--help"),
            None,
            ["Gates de qualidade para agentes.", "Roda os gates pedidos e grava .bob/"],
        ),
        (
            ("check", "--help"),
            PT,
            ["Lista separada por vírgula (padrão: crap,dry,deps)", "Idioma da saída: en ou pt-BR"],
        ),
        (("doctor", "--help"), None, ["Install the npm tools with npm ci in the package"]),
    ],
)
def test_help_follows_the_chosen_language(
    tmp_path: Path, args: tuple[str, ...], env: str | None, expected: list[str]
) -> None:
    result = run_bob(_repo(tmp_path), *args, bob_lang=env)
    flattened = " ".join(result.stdout.split())

    assert result.returncode == 0
    assert [text for text in expected if text not in flattened] == []


@pytest.mark.parametrize(
    ("lang", "shown"),
    [
        (EN, "waiver without a reason: pass --reason with one line\n"),
        (PT, "waiver sem motivo: informe --reason com uma linha\n"),
    ],
)
def test_waive_error_follows_the_chosen_language(tmp_path: Path, lang: str, shown: str) -> None:
    result = run_bob(_repo(tmp_path), "waive", "app.x_add__mutmut_1", "--lang", lang)

    assert result.returncode == 4
    assert result.stderr == shown
