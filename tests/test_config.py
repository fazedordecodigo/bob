"""`bob.yaml` e o idioma da saída: flag, BOB_LANG, yaml e padrão en."""

from pathlib import Path

import pytest

from bob_quality.config import (
    Config,
    ConfigError,
    configured_language,
    load_config,
    resolve_language,
)
from bob_quality.messages import reason, render

FULL_YAML = """\
base: origin/develop
language: pt-BR
languages: [python, typescript]
paths:
  include: [lib]
  exclude: [vendor]
crap:
  max_per_function: 7
  scope: all
dependencies:
  python: deps.ini
  typescript: deps.cjs
duplication:
  min_tokens: 80
"""


def _config_error(path: Path) -> tuple[str, str]:
    with pytest.raises(ConfigError) as caught:
        load_config(None, path)
    message = reason(caught.value)
    return render(message, "en"), render(message, "pt-BR")


def test_load_config_reads_every_key(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text(FULL_YAML)

    assert load_config(None, tmp_path) == Config(
        base="origin/develop",
        languages=["python", "typescript"],
        include=["lib"],
        exclude=["vendor"],
        max_crap=7.0,
        crap_scope="all",
        python_deps_config="deps.ini",
        typescript_deps_config="deps.cjs",
        min_tokens=80,
        language="pt-BR",
    )


def test_load_config_defaults_without_a_file(tmp_path: Path) -> None:
    assert load_config(None, tmp_path) == Config(
        base="origin/main",
        languages=["python"],
        include=["src"],
        exclude=["tests", "node_modules", "dist"],
        max_crap=10.0,
        crap_scope="changed",
        python_deps_config=".importlinter",
        typescript_deps_config=".dependency-cruiser.cjs",
        min_tokens=50,
        language=None,
    )


def test_load_config_defaults_for_an_empty_file(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("")

    assert load_config(None, tmp_path) == Config()


def test_load_config_reads_an_explicit_path(tmp_path: Path) -> None:
    explicit = tmp_path / "custom.yaml"
    explicit.write_text("base: trunk\n")

    assert load_config(explicit, tmp_path).base == "trunk"


def test_load_config_rejects_a_missing_explicit_path(tmp_path: Path) -> None:
    missing = tmp_path / "nope.yaml"

    with pytest.raises(ConfigError) as caught:
        load_config(missing, tmp_path)

    assert render(reason(caught.value), "en") == f"config file not found: {missing}"
    assert render(reason(caught.value), "pt-BR") == (
        f"arquivo de configuração não encontrado: {missing}"
    )


def test_load_config_rejects_a_list(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("- base\n")

    assert _config_error(tmp_path) == (
        "bob.yaml must be a mapping",
        "bob.yaml deve ser um mapeamento",
    )


def test_load_config_keeps_the_default_min_tokens_without_the_key(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("duplication:\n  other: 1\n")

    assert load_config(None, tmp_path).min_tokens == 50


def test_load_config_rejects_duplication_that_is_not_a_mapping(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("duplication: [1]\n")

    assert _config_error(tmp_path) == (
        "duplication must be a mapping",
        "duplication deve ser um mapeamento",
    )


def test_load_config_rejects_min_tokens_that_is_not_an_integer(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("duplication:\n  min_tokens: many\n")

    assert _config_error(tmp_path) == (
        "duplication.min_tokens must be an integer",
        "duplication.min_tokens deve ser um inteiro",
    )


def test_load_config_rejects_an_unknown_language(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("language: fr\n")

    assert _config_error(tmp_path) == (
        "invalid language: fr (use en or pt-BR)",
        "idioma inválido: fr (use en ou pt-BR)",
    )


@pytest.mark.parametrize("line", ["language:\n", 'language: ""\n'])
def test_load_config_treats_an_empty_language_as_unset(tmp_path: Path, line: str) -> None:
    (tmp_path / "bob.yaml").write_text(line)

    assert load_config(None, tmp_path) == Config()


def test_configured_language_reads_bob_yaml(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("language: pt-BR\n")

    assert configured_language(None, tmp_path) == "pt-BR"


def test_configured_language_reads_an_explicit_path(tmp_path: Path) -> None:
    explicit = tmp_path / "custom.yaml"
    explicit.write_text("language: pt-BR\n")

    assert configured_language(explicit, tmp_path) == "pt-BR"


def test_configured_language_leaves_a_broken_config_to_the_check(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("language: fr\n")

    assert configured_language(None, tmp_path) is None


@pytest.mark.parametrize(
    ("flag", "env", "configured", "expected"),
    [
        ("pt-BR", "en", "en", "pt-BR"),
        ("en", "pt-BR", "pt-BR", "en"),
        (None, "pt-BR", "en", "pt-BR"),
        (None, "en", "pt-BR", "en"),
        ("", "", "pt-BR", "pt-BR"),
        (None, None, "pt-BR", "pt-BR"),
        (None, None, None, "en"),
        ("en", "fr", None, "en"),
    ],
)
def test_resolve_language_prefers_flag_then_env_then_yaml_then_en(
    flag: str | None, env: str | None, configured: str | None, expected: str
) -> None:
    assert resolve_language(flag, env, configured) == expected


@pytest.mark.parametrize(("flag", "env", "shown"), [("fr", None, "fr"), (None, "pt-br", "pt-br")])
def test_resolve_language_rejects_an_unknown_value(
    flag: str | None, env: str | None, shown: str
) -> None:
    with pytest.raises(ConfigError) as caught:
        resolve_language(flag, env, "pt-BR")

    assert render(reason(caught.value), "en") == f"invalid language: {shown} (use en or pt-BR)"
