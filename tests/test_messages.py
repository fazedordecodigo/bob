"""Catálogo i18n: paridade entre en e pt-BR e renderização."""

from string import Formatter

from bob_quality.messages import CATALOG, msg, reason, render, t


def _fields(template: str) -> set[str]:
    return {name for _text, name, _spec, _conv in Formatter().parse(template) if name is not None}


def test_catalog_covers_exactly_en_and_pt_br() -> None:
    assert sorted(CATALOG) == ["en", "pt-BR"]


def test_both_languages_have_the_same_keys() -> None:
    assert sorted(CATALOG["en"]) == sorted(CATALOG["pt-BR"])


def test_both_languages_use_the_same_placeholders() -> None:
    mismatched = {
        key: (_fields(template), _fields(CATALOG["pt-BR"][key]))
        for key, template in CATALOG["en"].items()
        if _fields(template) != _fields(CATALOG["pt-BR"][key])
    }

    assert mismatched == {}


def test_render_fills_the_template_in_each_language() -> None:
    invalid = msg("config.invalid_language", value="fr")

    assert render(invalid, "en") == "invalid language: fr (use en or pt-BR)"
    assert render(invalid, "pt-BR") == "idioma inválido: fr (use en ou pt-BR)"


def test_render_renders_nested_messages_in_the_same_language() -> None:
    skipped = msg("probe.typescript_skipped", reason=msg("deps.node_missing"))

    assert render(skipped, "en") == (
        "TypeScript skipped: Node missing: install Node.js for the dependency gate "
        "(dependency-cruiser via npx)"
    )
    assert render(skipped, "pt-BR") == (
        "TypeScript pulado: Node ausente: instale Node.js para o gate de dependências "
        "(dependency-cruiser via npx)"
    )


def test_render_keeps_raw_tool_text_untouched() -> None:
    assert render("fatal: bad revision 'nope'", "pt-BR") == "fatal: bad revision 'nope'"


def test_render_formats_numbers_and_repr_conversions() -> None:
    assert render(msg("dry.clones", count=2), "en") == "2 new clones in the diff"
    assert render(msg("lizard.unexpected_row", row=["a", 1]), "pt-BR") == (
        "linha CSV inesperada: ['a', 1]"
    )


def test_t_renders_a_key_with_params() -> None:
    assert t("pt-BR", "doctor.version", name="lizard", expected="1.24.1", found="1.0") == (
        "lizard esperada 1.24.1 encontrada 1.0"
    )
    assert t("en", "doctor.missing") == "missing"


def test_reason_keeps_the_message_an_exception_carries() -> None:
    assert reason(ValueError(msg("jscpd.invalid_json"))) == msg("jscpd.invalid_json")


def test_reason_falls_back_to_the_raw_exception_text() -> None:
    assert reason(ValueError("raw stderr")) == "raw stderr"
    assert reason(ValueError()) == ""
