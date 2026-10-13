"""`bob.yaml` e o idioma da saída: flag, BOB_LANG, yaml e padrão en."""

from pathlib import Path

import pytest

from bob_quality.config import (
    Config,
    ConfigError,
    _Bound,
    _Check,
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
  new_clones: fail
  max_new_clones: 2
  min_similarity: 90
  min_lines: 8
"""


def _config_error(path: Path) -> tuple[str, str]:
    with pytest.raises(ConfigError) as caught:
        load_config(None, path)
    message = reason(caught.value)
    return render(message, "en"), render(message, "pt-BR")


def test_load_config_reads_every_key(tmp_path: Path) -> None:
    (tmp_path / "lib").mkdir()
    (tmp_path / "bob.yaml").write_text(FULL_YAML)

    loaded = load_config(None, tmp_path)

    assert type(loaded.max_crap) is float
    assert type(loaded.min_similarity) is float
    assert loaded == Config(
        base="origin/develop",
        languages=["python", "typescript"],
        include=["lib"],
        exclude=["vendor"],
        max_crap=7.0,
        crap_scope="all",
        python_deps_config="deps.ini",
        typescript_deps_config="deps.cjs",
        min_tokens=80,
        new_clones="fail",
        max_new_clones=2,
        min_similarity=90.0,
        min_lines=8,
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
        new_clones="warn",
        max_new_clones=0,
        min_similarity=0.0,
        min_lines=0,
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


@pytest.mark.parametrize(
    "text",
    [
        "{}\n",
        "duplication: {}\n",
        "duplication:\n",
        "duplication: null\n",
        "base: trunk\n",
    ],
)
def test_load_config_keeps_the_default_min_tokens_without_the_key(
    tmp_path: Path, text: str
) -> None:
    (tmp_path / "bob.yaml").write_text(text)

    assert load_config(None, tmp_path).min_tokens == 50


def test_load_config_rejects_zero_min_tokens(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("duplication:\n  min_tokens: 0\n")

    assert _config_error(tmp_path) == (
        "bob.yaml: duplication.min_tokens must be greater than 0",
        "bob.yaml: duplication.min_tokens deve ser maior que 0",
    )


@pytest.mark.parametrize(
    "text",
    [
        "{}\n",
        "dead_code:\n",
        "dead_code: null\n",
        "dead_code: {}\n",
        "dead_code:\n  min_confidence:\n",
        "dead_code:\n  min_confidence: null\n",
    ],
)
def test_load_config_omits_min_confidence_when_the_key_is_absent(
    tmp_path: Path, text: str
) -> None:
    (tmp_path / "bob.yaml").write_text(text)

    assert load_config(None, tmp_path).dead_code_min_confidence is None


@pytest.mark.parametrize(("text", "value"), [("0", 0), ("80", 80), ("100", 100)])
def test_load_config_stores_a_present_min_confidence(
    tmp_path: Path, text: str, value: int
) -> None:
    (tmp_path / "bob.yaml").write_text(f"dead_code:\n  min_confidence: {text}\n")

    assert load_config(None, tmp_path).dead_code_min_confidence == value


@pytest.mark.parametrize(
    ("text", "english", "portuguese"),
    [
        (
            "dead_code:\n  min_confidence: 101\n",
            "bob.yaml: dead_code.min_confidence must be an integer from 0 to 100",
            "bob.yaml: dead_code.min_confidence deve ser um inteiro de 0 a 100",
        ),
        (
            "dead_code:\n  min_confidence: -1\n",
            "bob.yaml: dead_code.min_confidence must be an integer from 0 to 100",
            "bob.yaml: dead_code.min_confidence deve ser um inteiro de 0 a 100",
        ),
        (
            "dead_code:\n  min_confidence: true\n",
            "bob.yaml: dead_code.min_confidence must be an integer",
            "bob.yaml: dead_code.min_confidence deve ser um inteiro",
        ),
        (
            "dead_code:\n  min_confidence: 1.5\n",
            "bob.yaml: dead_code.min_confidence must be an integer",
            "bob.yaml: dead_code.min_confidence deve ser um inteiro",
        ),
    ],
)
def test_load_config_rejects_an_illegal_min_confidence(
    tmp_path: Path, text: str, english: str, portuguese: str
) -> None:
    (tmp_path / "bob.yaml").write_text(text)

    assert _config_error(tmp_path) == (english, portuguese)


def test_config_accepts_absent_and_zero_min_confidence() -> None:
    assert Config().dead_code_min_confidence is None
    assert Config(dead_code_min_confidence=0).dead_code_min_confidence == 0
    assert Config(dead_code_min_confidence=100).dead_code_min_confidence == 100


@pytest.mark.parametrize("value", [101, -1, True, 1.5])
def test_config_rejects_an_illegal_min_confidence(value: object) -> None:
    with pytest.raises(ValueError) as caught:
        Config(dead_code_min_confidence=value)

    assert caught.value.args == ("dead_code_min_confidence",)


def test_load_config_stores_one_min_token(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("duplication:\n  min_tokens: 1\n")

    assert load_config(None, tmp_path).min_tokens == 1


@pytest.mark.parametrize(
    "text",
    [
        "duplication:\n  new_clones:\n",
        'duplication:\n  new_clones: ""\n',
        "duplication:\n  max_new_clones: 3\n",
    ],
)
def test_load_config_keeps_warn_when_new_clones_is_absent(tmp_path: Path, text: str) -> None:
    (tmp_path / "bob.yaml").write_text(text)

    assert load_config(None, tmp_path).new_clones == "warn"


@pytest.mark.parametrize(
    ("text", "attr", "expected"),
    [
        ("duplication:\n  min_similarity: 100\n", "min_similarity", 100.0),
        ("duplication:\n  min_similarity: 0\n", "min_similarity", 0.0),
        ("duplication:\n  min_similarity: 57.5\n", "min_similarity", 57.5),
        ("duplication:\n  max_new_clones: 0\n  new_clones: fail\n", "max_new_clones", 0),
        ("duplication:\n  max_new_clones:\n", "max_new_clones", 0),
        ("duplication:\n  min_lines: 0\n", "min_lines", 0),
        ("duplication:\n  min_lines:\n", "min_lines", 0),
    ],
)
def test_load_config_accepts_the_duplication_limits_at_their_bounds(
    tmp_path: Path, text: str, attr: str, expected: object
) -> None:
    (tmp_path / "bob.yaml").write_text(text)

    assert getattr(load_config(None, tmp_path), attr) == expected


def test_load_config_stores_all_as_the_crap_scope(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("crap:\n  scope: all\n")

    assert load_config(None, tmp_path).crap_scope == "all"


@pytest.mark.parametrize("text", ["crap:\n  scope:\n", 'crap:\n  scope: ""\n', "{}\n"])
def test_load_config_stores_changed_when_scope_is_absent(tmp_path: Path, text: str) -> None:
    (tmp_path / "bob.yaml").write_text(text)

    assert load_config(None, tmp_path).crap_scope == "changed"


def test_load_config_rejects_an_empty_languages_list(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("languages: []\n")

    assert _config_error(tmp_path) == (
        "bob.yaml: languages must not be empty",
        "bob.yaml: languages não deve ser vazio",
    )


@pytest.mark.parametrize("text", ["languages:\n", "languages: null\n", "{}\n"])
def test_load_config_stores_python_when_languages_is_absent(
    tmp_path: Path, text: str
) -> None:
    (tmp_path / "bob.yaml").write_text(text)

    assert load_config(None, tmp_path).languages == ("python",)


def test_load_config_keeps_languages_in_file_order(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("languages: [typescript, python]\n")

    assert load_config(None, tmp_path).languages == ("typescript", "python")


def test_load_config_reads_an_empty_mapping_as_the_defaults(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("{}\n")

    assert load_config(None, tmp_path) == Config()


@pytest.mark.parametrize(
    "text",
    ["duplication: [1]\n", "duplication: 0\n", "duplication: false\n", 'duplication: ""\n'],
)
def test_load_config_rejects_duplication_that_is_not_a_mapping(
    tmp_path: Path, text: str
) -> None:
    (tmp_path / "bob.yaml").write_text(text)

    assert _config_error(tmp_path) == (
        "bob.yaml: duplication must be a mapping",
        "bob.yaml: duplication deve ser um mapeamento",
    )


@pytest.mark.parametrize(
    "text",
    [
        "duplication:\n  min_tokens: many\n",
        "duplication:\n  min_tokens: null\n",
    ],
)
def test_load_config_rejects_min_tokens_that_is_not_an_integer(
    tmp_path: Path, text: str
) -> None:
    (tmp_path / "bob.yaml").write_text(text)

    assert _config_error(tmp_path) == (
        "bob.yaml: duplication.min_tokens must be an integer",
        "bob.yaml: duplication.min_tokens deve ser um inteiro",
    )


@pytest.mark.parametrize(
    ("text", "english", "portuguese"),
    [
        (
            "crap: 5\n",
            "bob.yaml: crap must be a mapping",
            "bob.yaml: crap deve ser um mapeamento",
        ),
        (
            "crap:\n  max_per_function: abc\n",
            "bob.yaml: crap.max_per_function must be a number",
            "bob.yaml: crap.max_per_function deve ser um número",
        ),
        (
            "crap:\n  max_per_function: true\n",
            "bob.yaml: crap.max_per_function must be a number",
            "bob.yaml: crap.max_per_function deve ser um número",
        ),
        (
            "crap:\n  scope: [changed]\n",
            "bob.yaml: crap.scope must be a string",
            "bob.yaml: crap.scope deve ser um texto",
        ),
        (
            "paths: 5\n",
            "bob.yaml: paths must be a mapping",
            "bob.yaml: paths deve ser um mapeamento",
        ),
        (
            "paths:\n  include: src\n",
            "bob.yaml: paths.include must be a list of strings",
            "bob.yaml: paths.include deve ser uma lista de textos",
        ),
        (
            "paths:\n  exclude: 1\n",
            "bob.yaml: paths.exclude must be a list of strings",
            "bob.yaml: paths.exclude deve ser uma lista de textos",
        ),
        (
            "languages: python\n",
            "bob.yaml: languages must be a list of strings",
            "bob.yaml: languages deve ser uma lista de textos",
        ),
        (
            "languages: [python, 1]\n",
            "bob.yaml: languages must be a list of strings",
            "bob.yaml: languages deve ser uma lista de textos",
        ),
        (
            "dependencies: 5\n",
            "bob.yaml: dependencies must be a mapping",
            "bob.yaml: dependencies deve ser um mapeamento",
        ),
        (
            "dependencies:\n  python: 1\n",
            "bob.yaml: dependencies.python must be a string",
            "bob.yaml: dependencies.python deve ser um texto",
        ),
        (
            "dependencies:\n  typescript: 1\n",
            "bob.yaml: dependencies.typescript must be a string",
            "bob.yaml: dependencies.typescript deve ser um texto",
        ),
        (
            "base: [main]\n",
            "bob.yaml: base must be a string",
            "bob.yaml: base deve ser um texto",
        ),
        (
            "duplication:\n  new_clones: 5\n",
            "bob.yaml: duplication.new_clones must be a string",
            "bob.yaml: duplication.new_clones deve ser um texto",
        ),
        (
            'duplication:\n  min_similarity: "90"\n',
            "bob.yaml: duplication.min_similarity must be a number",
            "bob.yaml: duplication.min_similarity deve ser um número",
        ),
        (
            "duplication:\n  max_new_clones: 1.5\n",
            "bob.yaml: duplication.max_new_clones must be an integer",
            "bob.yaml: duplication.max_new_clones deve ser um inteiro",
        ),
        (
            "duplication:\n  max_new_clones: true\n",
            "bob.yaml: duplication.max_new_clones must be an integer",
            "bob.yaml: duplication.max_new_clones deve ser um inteiro",
        ),
        (
            "duplication:\n  min_lines: true\n",
            "bob.yaml: duplication.min_lines must be an integer",
            "bob.yaml: duplication.min_lines deve ser um inteiro",
        ),
    ],
)
def test_load_config_rejects_a_wrong_value_type(
    tmp_path: Path, text: str, english: str, portuguese: str
) -> None:
    (tmp_path / "bob.yaml").write_text(text)

    assert _config_error(tmp_path) == (english, portuguese)


def test_load_config_names_an_explicit_file_on_a_wrong_type(tmp_path: Path) -> None:
    explicit = tmp_path / "custom.yaml"
    explicit.write_text("crap:\n  max_per_function: abc\n")

    with pytest.raises(ConfigError) as caught:
        load_config(explicit, tmp_path)

    assert render(reason(caught.value), "en") == (
        f"{explicit.as_posix()}: crap.max_per_function must be a number"
    )


def test_load_config_treats_null_and_empty_collections_as_defaults(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text(
        "base:\n"
        "paths:\n"
        "  include:\n"
        "  exclude: []\n"
        "crap:\n"
        "  max_per_function:\n"
        "  scope: \"\"\n"
        "dependencies:\n"
        "  python:\n"
        "  typescript: \"\"\n"
    )

    assert load_config(None, tmp_path) == Config()


def test_load_config_keeps_numeric_thresholds_and_string_lists(tmp_path: Path) -> None:
    (tmp_path / "lib").mkdir()
    (tmp_path / "bob.yaml").write_text(
        "base: trunk\n"
        "languages: [python, typescript]\n"
        "paths:\n"
        "  include: [lib]\n"
        "  exclude: [vendor]\n"
        "crap:\n"
        "  max_per_function: 10.5\n"
        "  scope: all\n"
        "dependencies:\n"
        "  python: deps.ini\n"
        "  typescript: deps.cjs\n"
    )

    loaded = load_config(None, tmp_path)

    assert loaded.base == "trunk"
    assert loaded.languages == ("python", "typescript")
    assert loaded.include == ("lib",)
    assert loaded.exclude == ("vendor",)
    assert loaded.max_crap == 10.5
    assert loaded.crap_scope == "all"
    assert loaded.python_deps_config == "deps.ini"
    assert loaded.typescript_deps_config == "deps.cjs"


def test_load_config_rejects_a_missing_include_path(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("paths:\n  include: [missing-root]\n")

    assert _config_error(tmp_path) == (
        "bob.yaml: paths.include does not exist: missing-root",
        "bob.yaml: paths.include não existe: missing-root",
    )


def test_load_config_names_every_missing_include_in_order(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text(
        "paths:\n  include: [missing-root, also-gone]\n"
    )

    assert _config_error(tmp_path) == (
        "bob.yaml: paths.include does not exist: missing-root, also-gone",
        "bob.yaml: paths.include não existe: missing-root, also-gone",
    )


def test_load_config_names_only_the_missing_include(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "bob.yaml").write_text("paths:\n  include: [src, gone]\n")

    assert _config_error(tmp_path) == (
        "bob.yaml: paths.include does not exist: gone",
        "bob.yaml: paths.include não existe: gone",
    )


def test_load_config_keeps_an_include_entry_that_exists(tmp_path: Path) -> None:
    (tmp_path / "lib").mkdir()
    (tmp_path / "one.py").write_text("x = 1\n")
    (tmp_path / "bob.yaml").write_text("paths:\n  include: [lib, one.py]\n")

    loaded = load_config(None, tmp_path)

    assert loaded.include == ("lib", "one.py")


def test_load_config_rejects_invalid_yaml(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text(":\n  - [\n")

    assert _config_error(tmp_path) == (
        "invalid YAML in bob.yaml: while parsing a block mapping",
        "YAML inválido em bob.yaml: while parsing a block mapping",
    )


def test_load_config_rejects_a_duplicate_key(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("base: main\nbase: trunk\n")

    assert _config_error(tmp_path) == (
        "invalid YAML in bob.yaml: found duplicate key 'base' on line 2",
        "YAML inválido em bob.yaml: found duplicate key 'base' on line 2",
    )

    (tmp_path / "bob.yaml").write_text("crap:\n  scope: all\n  scope: changed\n")

    assert _config_error(tmp_path) == (
        "invalid YAML in bob.yaml: found duplicate key 'scope' on line 3",
        "YAML inválido em bob.yaml: found duplicate key 'scope' on line 3",
    )


def test_load_config_lets_an_explicit_key_override_a_merged_one(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text(
        "crap:\n  <<: {max_per_function: 12, scope: all}\n  max_per_function: 15\n"
    )

    loaded = load_config(None, tmp_path)

    assert loaded.max_crap == 15.0
    assert loaded.crap_scope == "all"


def test_load_config_rejects_an_unhashable_key_with_exit_4_text(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("? [a]\n: 1\n")

    assert _config_error(tmp_path) == (
        "invalid YAML in bob.yaml: while constructing a mapping",
        "YAML inválido em bob.yaml: while constructing a mapping",
    )


def test_load_config_rejects_a_numeric_language(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("language: 5\n")

    assert _config_error(tmp_path) == (
        "bob.yaml: language must be a string",
        "bob.yaml: language deve ser um texto",
    )


def test_load_config_rejects_an_unknown_language(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("language: fr\n")

    assert _config_error(tmp_path) == (
        "bob.yaml: language must be en or pt-BR",
        "bob.yaml: language deve ser en ou pt-BR",
    )


@pytest.mark.parametrize("line", ["language:\n", 'language: ""\n'])
def test_load_config_treats_an_empty_language_as_unset(tmp_path: Path, line: str) -> None:
    (tmp_path / "bob.yaml").write_text(line)

    assert load_config(None, tmp_path) == Config()


def _set_bob_lang(monkeypatch: pytest.MonkeyPatch, env: str | None) -> None:
    monkeypatch.delenv("BOB_LANG", raising=False)
    if env is not None:
        monkeypatch.setenv("BOB_LANG", env)


@pytest.mark.parametrize("language", ["en", "pt-BR"])
def test_resolve_language_reads_bob_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, language: str
) -> None:
    _set_bob_lang(monkeypatch, None)
    (tmp_path / "bob.yaml").write_text(f"language: {language}\n")

    assert resolve_language(None, None, tmp_path) == language


def test_resolve_language_reads_an_explicit_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_bob_lang(monkeypatch, None)
    explicit = tmp_path / "custom.yaml"
    explicit.write_text("language: pt-BR\n")

    assert resolve_language(None, explicit, tmp_path) == "pt-BR"


def test_resolve_language_rejects_an_unknown_yaml_language(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_bob_lang(monkeypatch, None)
    (tmp_path / "bob.yaml").write_text("language: fr\n")

    with pytest.raises(ConfigError) as caught:
        resolve_language(None, None, tmp_path)

    assert render(reason(caught.value), "en") == "bob.yaml: language must be en or pt-BR"


def test_resolve_language_rejects_a_numeric_yaml_language(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_bob_lang(monkeypatch, None)
    (tmp_path / "bob.yaml").write_text("language: 5\n")

    with pytest.raises(ConfigError) as caught:
        resolve_language(None, None, tmp_path)

    assert render(reason(caught.value), "en") == "bob.yaml: language must be a string"


def test_resolve_language_rejects_a_yaml_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_bob_lang(monkeypatch, None)
    (tmp_path / "bob.yaml").write_text("- base\n")

    with pytest.raises(ConfigError) as caught:
        resolve_language(None, None, tmp_path)

    assert render(reason(caught.value), "en") == "bob.yaml must be a mapping"


def test_resolve_language_rejects_invalid_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_bob_lang(monkeypatch, None)
    (tmp_path / "bob.yaml").write_text(":\n  - [\n")

    with pytest.raises(ConfigError) as caught:
        resolve_language(None, None, tmp_path)

    assert render(reason(caught.value), "en") == (
        "invalid YAML in bob.yaml: while parsing a block mapping"
    )


def test_resolve_language_rejects_a_duplicate_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_bob_lang(monkeypatch, None)
    (tmp_path / "bob.yaml").write_text("language: en\nlanguage: pt-BR\n")

    with pytest.raises(ConfigError) as caught:
        resolve_language(None, None, tmp_path)

    assert render(reason(caught.value), "en") == (
        "invalid YAML in bob.yaml: found duplicate key 'language' on line 2"
    )


def test_resolve_language_keeps_pt_br_when_another_key_is_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_bob_lang(monkeypatch, None)
    (tmp_path / "bob.yaml").write_text("language: pt-BR\nduplication: [1]\n")

    assert resolve_language(None, None, tmp_path) == "pt-BR"


@pytest.mark.parametrize("text", ["base: trunk\n", "language:\n", 'language: ""\n'])
def test_resolve_language_falls_back_to_en_without_a_language_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str
) -> None:
    _set_bob_lang(monkeypatch, None)
    (tmp_path / "bob.yaml").write_text(text)

    assert resolve_language(None, None, tmp_path) == "en"


@pytest.mark.parametrize(
    ("flag", "env", "configured", "expected"),
    [
        ("pt-BR", "en", "en", "pt-BR"),
        ("en", "pt-BR", "pt-BR", "en"),
        (None, "pt-BR", "en", "pt-BR"),
        (None, "en", "pt-BR", "en"),
        (None, None, "pt-BR", "pt-BR"),
        (None, None, None, "en"),
        ("en", "fr", None, "en"),
    ],
)
def test_resolve_language_prefers_flag_then_env_then_yaml_then_en(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    flag: str | None,
    env: str | None,
    configured: str | None,
    expected: str,
) -> None:
    _set_bob_lang(monkeypatch, env)
    if configured is not None:
        (tmp_path / "bob.yaml").write_text(f"language: {configured}\n")

    assert resolve_language(flag, None, tmp_path) == expected


@pytest.mark.parametrize(("flag", "env", "shown"), [("fr", None, "fr"), (None, "pt-br", "pt-br")])
def test_resolve_language_rejects_an_unknown_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flag: str | None, env: str | None, shown: str
) -> None:
    _set_bob_lang(monkeypatch, env)
    (tmp_path / "bob.yaml").write_text("language: pt-BR\n")

    with pytest.raises(ConfigError) as caught:
        resolve_language(flag, None, tmp_path)

    assert render(reason(caught.value), "en") == f"invalid language: {shown} (use en or pt-BR)"


@pytest.mark.parametrize(
    ("flag", "env"),
    [("", "pt-BR"), (None, ""), ("", None)],
)
def test_resolve_language_rejects_an_empty_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flag: str | None, env: str | None
) -> None:
    _set_bob_lang(monkeypatch, env)
    (tmp_path / "bob.yaml").write_text("language: pt-BR\n")

    with pytest.raises(ConfigError) as caught:
        resolve_language(flag, None, tmp_path)

    assert render(reason(caught.value), "en") == 'invalid language: "" (use en or pt-BR)'


@pytest.mark.parametrize(
    ("flag", "env", "shown"),
    [("fr", None, "fr"), (None, "fr", "fr"), (None, "", '""')],
)
def test_flag_error_comes_before_the_yaml_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    flag: str | None,
    env: str | None,
    shown: str,
) -> None:
    _set_bob_lang(monkeypatch, env)
    (tmp_path / "bob.yaml").write_text("language: pt-br\n")

    with pytest.raises(ConfigError) as caught:
        resolve_language(flag, None, tmp_path)

    assert render(reason(caught.value), "en") == f"invalid language: {shown} (use en or pt-BR)"


def test_bad_yaml_language_fails_even_when_the_flag_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_bob_lang(monkeypatch, None)
    (tmp_path / "bob.yaml").write_text("language: pt-br\n")

    with pytest.raises(ConfigError) as caught:
        resolve_language("en", None, tmp_path)

    assert render(reason(caught.value), "en") == "bob.yaml: language must be en or pt-BR"


@pytest.mark.parametrize(
    ("text", "english", "portuguese"),
    [
        (
            "mutation: {}\n",
            "bob.yaml: unknown key mutation",
            "bob.yaml: chave desconhecida mutation",
        ),
        (
            "duplication:\n  tool: jscpd\n",
            "bob.yaml: unknown key duplication.tool",
            "bob.yaml: chave desconhecida duplication.tool",
        ),
        (
            "crap:\n  scope: Changed\n",
            "bob.yaml: crap.scope must be changed or all",
            "bob.yaml: crap.scope deve ser changed ou all",
        ),
        (
            "languages: [ruby]\n",
            "bob.yaml: languages[0] must be python or typescript",
            "bob.yaml: languages[0] deve ser python ou typescript",
        ),
        (
            "languages: [python, ruby]\n",
            "bob.yaml: languages[1] must be python or typescript",
            "bob.yaml: languages[1] deve ser python ou typescript",
        ),
        (
            "base:\ncrap:\n  max_per_function: -1\n",
            "bob.yaml: crap.max_per_function must be greater than 0",
            "bob.yaml: crap.max_per_function deve ser maior que 0",
        ),
        (
            'base: ""\ncrap:\n  max_per_function: -1\n',
            "bob.yaml: crap.max_per_function must be greater than 0",
            "bob.yaml: crap.max_per_function deve ser maior que 0",
        ),
        (
            "languages: []\ncrap:\n  max_per_function: -1\n",
            "bob.yaml: languages must not be empty",
            "bob.yaml: languages não deve ser vazio",
        ),
        (
            "languages: [python, python]\n",
            "bob.yaml: languages[1] repeats python",
            "bob.yaml: languages[1] repete python",
        ),
        (
            "languages: [ruby, ruby]\n",
            "bob.yaml: languages[0] must be python or typescript",
            "bob.yaml: languages[0] deve ser python ou typescript",
        ),
        (
            "crap:\n  max_per_function: " + "1" + "0" * 400 + "\n",
            "bob.yaml: crap.max_per_function must be finite",
            "bob.yaml: crap.max_per_function deve ser finito",
        ),
        (
            "crap:\n  max_per_function: .nan\n",
            "bob.yaml: crap.max_per_function must be finite",
            "bob.yaml: crap.max_per_function deve ser finito",
        ),
        (
            "crap:\n  max_per_function: .inf\n",
            "bob.yaml: crap.max_per_function must be finite",
            "bob.yaml: crap.max_per_function deve ser finito",
        ),
        (
            "crap:\n  max_per_function: -.inf\n",
            "bob.yaml: crap.max_per_function must be finite",
            "bob.yaml: crap.max_per_function deve ser finito",
        ),
        (
            "crap:\n  max_per_function: 0\n",
            "bob.yaml: crap.max_per_function must be greater than 0",
            "bob.yaml: crap.max_per_function deve ser maior que 0",
        ),
        (
            "duplication:\n  min_tokens: -1\n",
            "bob.yaml: duplication.min_tokens must be greater than 0",
            "bob.yaml: duplication.min_tokens deve ser maior que 0",
        ),
        (
            "duplication:\n  min_tokens: 0\n",
            "bob.yaml: duplication.min_tokens must be greater than 0",
            "bob.yaml: duplication.min_tokens deve ser maior que 0",
        ),
        (
            "duplication:\n  new_clones: block\n",
            "bob.yaml: duplication.new_clones must be warn or fail",
            "bob.yaml: duplication.new_clones deve ser warn ou fail",
        ),
        (
            "duplication:\n  max_new_clones: -1\n",
            "bob.yaml: duplication.max_new_clones must be at least 0",
            "bob.yaml: duplication.max_new_clones deve ser no mínimo 0",
        ),
        (
            "duplication:\n  min_lines: -1\n",
            "bob.yaml: duplication.min_lines must be at least 0",
            "bob.yaml: duplication.min_lines deve ser no mínimo 0",
        ),
        (
            "duplication:\n  min_similarity: 101\n",
            "bob.yaml: duplication.min_similarity must be at most 100",
            "bob.yaml: duplication.min_similarity deve ser no máximo 100",
        ),
        (
            "duplication:\n  min_similarity: 100.5\n",
            "bob.yaml: duplication.min_similarity must be at most 100",
            "bob.yaml: duplication.min_similarity deve ser no máximo 100",
        ),
        (
            "duplication:\n  min_similarity: -1\n",
            "bob.yaml: duplication.min_similarity must be at least 0",
            "bob.yaml: duplication.min_similarity deve ser no mínimo 0",
        ),
        (
            "duplication:\n  min_similarity: .nan\n",
            "bob.yaml: duplication.min_similarity must be finite",
            "bob.yaml: duplication.min_similarity deve ser finito",
        ),
    ],
)
def test_load_config_rejects_an_illegal_semantic_value(
    tmp_path: Path, text: str, english: str, portuguese: str
) -> None:
    (tmp_path / "bob.yaml").write_text(text)

    assert _config_error(tmp_path) == (english, portuguese)


@pytest.mark.parametrize(
    ("kwargs", "name"),
    [
        ({"crap_scope": "nope"}, "crap_scope"),
        ({"max_crap": 0}, "max_crap"),
        ({"max_crap": float("nan")}, "max_crap"),
        ({"max_crap": float("inf")}, "max_crap"),
        ({"max_crap": 10**400}, "max_crap"),
        ({"min_tokens": -1}, "min_tokens"),
        ({"min_tokens": 0}, "min_tokens"),
        ({"min_tokens": True}, "min_tokens"),
        ({"new_clones": "block"}, "new_clones"),
        ({"max_new_clones": -1}, "max_new_clones"),
        ({"min_similarity": 101}, "min_similarity"),
        ({"min_lines": -1}, "min_lines"),
        ({"languages": ("python", "ruby")}, "languages"),
        ({"languages": ()}, "languages"),
        ({"languages": ("python", "python")}, "languages"),
        ({"languages": "python"}, "languages"),
    ],
)
def test_config_rejects_an_illegal_in_process_value(kwargs: dict[str, object], name: str) -> None:
    with pytest.raises(ValueError) as caught:
        Config(**kwargs)

    assert caught.value.args == (name,)


def test_config_rejects_an_empty_language() -> None:
    with pytest.raises(ValueError) as caught:
        Config(language="")

    assert caught.value.args == ("language",)


def test_check_rejects_a_bound_that_is_not_a_real_number() -> None:
    with pytest.raises(ValueError) as caught:
        _Bound("gt", True)

    assert caught.value.args == ("gt",)
    _Bound("gt", 0)


def test_check_rejects_a_choice_list_that_is_not_a_pair() -> None:
    with pytest.raises(ValueError) as caught:
        _Check("one_of", choices=("only",))

    assert caught.value.args == ("one_of",)
    with pytest.raises(ValueError) as members:
        _Check("members", choices=())

    assert members.value.args == ("members",)
    with pytest.raises(ValueError) as language:
        _Check("language")

    assert language.value.args == ("language",)
    _Check("one_of", choices=("changed", "all"))
    _Check("language", choices=("en", "pt-BR"))
    _Check("string")


def test_schema_literals_match_config_fields() -> None:
    from dataclasses import fields
    from typing import get_args

    import bob_quality.config as config_module

    assert set(config_module.SOURCE_LANGUAGES) == set(get_args(config_module.SourceLanguage))
    assert set(config_module.CRAP_SCOPES) == set(get_args(config_module.CrapScope))
    assert set(config_module.NEW_CLONES_MODES) == set(get_args(config_module.NewClonesMode))
    assert {item.name for item in fields(config_module.Config)} == _schema_attrs(
        config_module._SCHEMA
    )


def _schema_attrs(node: object) -> set[str]:
    attrs: set[str] = set()
    attr = getattr(node, "attr")
    if isinstance(attr, str) and attr != "":
        attrs.add(attr)
    for child in getattr(node, "children"):
        attrs |= _schema_attrs(child)
    return attrs
