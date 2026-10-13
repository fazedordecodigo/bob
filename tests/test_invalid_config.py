from __future__ import annotations

from pathlib import Path

import pytest
from helpers import in_both, run_bob

from bob_quality.waivers import WaiverError, load_waivers

_COMMANDS = (
    ("check", "--gates", "nope"),
    ("crap",),
    ("dry",),
    ("deps",),
    ("mutate",),
    ("doctor",),
    ("waive", "fn", "--reason", "because"),
)

_BROKEN_YAML = (
    ("crap: [1\n", "invalid YAML in bob.yaml: while parsing a flow sequence\n"),
    ("crap: 5\n", "bob.yaml: crap must be a mapping\n"),
    (
        "crap:\n  max_per_function: abc\n",
        "bob.yaml: crap.max_per_function must be a number\n",
    ),
    ("paths: 5\n", "bob.yaml: paths must be a mapping\n"),
    ("languages: 5\n", "bob.yaml: languages must be a list of strings\n"),
    ("dependencies: [1]\n", "bob.yaml: dependencies must be a mapping\n"),
    ("base: [main]\n", "bob.yaml: base must be a string\n"),
    (
        "base: main\nbase: trunk\n",
        "invalid YAML in bob.yaml: found duplicate key 'base' on line 2\n",
    ),
    (
        "crap:\n  scope: all\n  scope: changed\n",
        "invalid YAML in bob.yaml: found duplicate key 'scope' on line 3\n",
    ),
)


def _write_waivers(tmp_path: Path, text: str) -> None:
    bob = tmp_path / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text(text)


def test_load_waivers_rejects_invalid_yaml_in_both_languages(tmp_path: Path) -> None:
    _write_waivers(tmp_path, "waivers: [\n")

    with pytest.raises(WaiverError) as caught:
        load_waivers(tmp_path)

    assert in_both(caught.value) == (
        "invalid YAML in .bob/waivers.yaml: while parsing a flow node",
        "YAML inválido em .bob/waivers.yaml: while parsing a flow node",
    )


def test_load_waivers_rejects_a_duplicate_key(tmp_path: Path) -> None:
    _write_waivers(
        tmp_path,
        "waivers:\n"
        "  - id: fn\n"
        "    id: other\n"
        "    reason: because\n"
        "    author: ada\n"
        "    date: '2026-10-11'\n",
    )

    with pytest.raises(WaiverError) as caught:
        load_waivers(tmp_path)

    assert in_both(caught.value) == (
        "invalid YAML in .bob/waivers.yaml: found duplicate key 'id' on line 3",
        "YAML inválido em .bob/waivers.yaml: found duplicate key 'id' on line 3",
    )


def test_load_waivers_reads_a_merge_chain(tmp_path: Path) -> None:
    _write_waivers(
        tmp_path,
        "waivers:\n"
        "  - &a {id: fn, reason: because, author: ada, date: '2026-10-11'}\n"
        "  - &b {<<: *a, id: second}\n"
        "  - {<<: *b, id: third}\n",
    )

    loaded = load_waivers(tmp_path)

    assert [(item.id, item.reason) for item in loaded] == [
        ("fn", "because"),
        ("second", "because"),
        ("third", "because"),
    ]


def test_load_waivers_reads_one_entry(tmp_path: Path) -> None:
    _write_waivers(
        tmp_path,
        "waivers:\n"
        "  - id: fn\n"
        "    reason: because\n"
        "    author: ada\n"
        "    date: '2026-10-11'\n",
    )

    loaded = load_waivers(tmp_path)

    assert [(item.id, item.reason, item.author, item.date) for item in loaded] == [
        ("fn", "because", "ada", "2026-10-11")
    ]


@pytest.mark.parametrize("text", ["", "null\n", "{}\n", "waivers:\n", "waivers: []\n"])
def test_load_waivers_treats_missing_entries_as_an_empty_list(
    tmp_path: Path, text: str
) -> None:
    _write_waivers(tmp_path, text)

    assert load_waivers(tmp_path) == []


def test_load_waivers_rejects_a_file_that_is_not_a_mapping(tmp_path: Path) -> None:
    _write_waivers(tmp_path, "- 1\n")

    with pytest.raises(WaiverError) as caught:
        load_waivers(tmp_path)

    assert in_both(caught.value) == (
        ".bob/waivers.yaml must be a mapping",
        ".bob/waivers.yaml deve ser um mapeamento",
    )


def test_load_waivers_rejects_a_waivers_value_that_is_not_a_list(tmp_path: Path) -> None:
    _write_waivers(tmp_path, "waivers: 1\n")

    with pytest.raises(WaiverError) as caught:
        load_waivers(tmp_path)

    assert in_both(caught.value) == (
        ".bob/waivers.yaml: waivers must be a list",
        ".bob/waivers.yaml: waivers deve ser uma lista",
    )


@pytest.mark.parametrize(
    ("text", "english", "portuguese"),
    [
        (
            "waivers: [5]\n",
            ".bob/waivers.yaml: waivers[0] must be a mapping",
            ".bob/waivers.yaml: waivers[0] deve ser um mapeamento",
        ),
        (
            "waivers:\n  - id: fn\n    author: ada\n    date: '2026-10-11'\n",
            ".bob/waivers.yaml: waivers[0].reason must be a string",
            ".bob/waivers.yaml: waivers[0].reason deve ser um texto",
        ),
        (
            "waivers:\n  - reason: because\n    author: ada\n    date: '2026-10-11'\n",
            ".bob/waivers.yaml: waivers[0].id must be a string",
            ".bob/waivers.yaml: waivers[0].id deve ser um texto",
        ),
        (
            "waivers:\n  - id: fn\n    reason: because\n    date: '2026-10-11'\n",
            ".bob/waivers.yaml: waivers[0].author must be a string",
            ".bob/waivers.yaml: waivers[0].author deve ser um texto",
        ),
        (
            "waivers:\n  - id: fn\n    reason: because\n    author: ada\n",
            ".bob/waivers.yaml: waivers[0].date must be a string",
            ".bob/waivers.yaml: waivers[0].date deve ser um texto",
        ),
        (
            "waivers:\n"
            "  - id: fn\n"
            "    reason: because\n"
            "    author: ada\n"
            "    date: '2026-10-11'\n"
            "  - 5\n",
            ".bob/waivers.yaml: waivers[1] must be a mapping",
            ".bob/waivers.yaml: waivers[1] deve ser um mapeamento",
        ),
        (
            "waivers:\n"
            "  - id: fn\n"
            "    reason: because\n"
            "    author: ada\n"
            "    date: '2026-10-11'\n"
            "  - id: other\n"
            "    author: ada\n"
            "    date: '2026-10-11'\n",
            ".bob/waivers.yaml: waivers[1].reason must be a string",
            ".bob/waivers.yaml: waivers[1].reason deve ser um texto",
        ),
    ],
)
def test_load_waivers_names_the_bad_field(
    tmp_path: Path, text: str, english: str, portuguese: str
) -> None:
    _write_waivers(tmp_path, text)

    with pytest.raises(WaiverError) as caught:
        load_waivers(tmp_path)

    assert in_both(caught.value) == (english, portuguese)


def _files(repo: Path) -> set[str]:
    return {
        path.relative_to(repo).as_posix()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }


@pytest.mark.parametrize("command", _COMMANDS)
@pytest.mark.parametrize(("text", "stderr"), _BROKEN_YAML)
@pytest.mark.parametrize("lang", [None, "pt-BR"])
def test_broken_bob_yaml_exits_4_in_english_and_writes_nothing(
    tmp_path: Path,
    command: tuple[str, ...],
    text: str,
    stderr: str,
    lang: str | None,
) -> None:
    (tmp_path / "bob.yaml").write_text(text)
    before = _files(tmp_path)
    args = ("--lang", lang, *command) if lang is not None else command

    result = run_bob(tmp_path, *args)

    assert result.returncode == 4
    assert result.stderr == stderr
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert _files(tmp_path) == before


def test_explicit_config_names_that_file(tmp_path: Path) -> None:
    custom = tmp_path / "custom.yaml"
    custom.write_text("crap: 5\n")

    result = run_bob(tmp_path, "check", "--config", "custom.yaml", "--gates", "nope")

    assert result.returncode == 4
    assert result.stderr == f"{custom.as_posix()}: crap must be a mapping\n"
    assert result.stdout == ""
    assert not (tmp_path / ".bob").exists()


_SHAPE_COMMANDS = (
    ("check",),
    ("doctor",),
    ("waive", "fn", "--reason", "because"),
)

_BAD_WAIVER_SHAPE = (
    ("- a\n", ".bob/waivers.yaml must be a mapping\n"),
    ("waivers: x\n", ".bob/waivers.yaml: waivers must be a list\n"),
    ("waivers: [5]\n", ".bob/waivers.yaml: waivers[0] must be a mapping\n"),
    (
        "waivers:\n  - id: fn\n    author: ada\n    date: '2026-10-11'\n",
        ".bob/waivers.yaml: waivers[0].reason must be a string\n",
    ),
)

_HUGE_THRESHOLD = "1" + "0" * 400

_SEMANTIC_YAML = (
    ("mutation: {}\n", "bob.yaml: unknown key mutation\n"),
    ("duplication:\n  tool: jscpd\n", "bob.yaml: unknown key duplication.tool\n"),
    ("dependencies:\n  violation: fail\n", "bob.yaml: unknown key dependencies.violation\n"),
    ("crap:\n  max_per_functon: 10\n", "bob.yaml: unknown key crap.max_per_functon\n"),
    ("crap:\n  scope: Changed\n", "bob.yaml: crap.scope must be changed or all\n"),
    ("languages: [ruby]\n", "bob.yaml: languages[0] must be python or typescript\n"),
    (
        "languages: [python, ruby]\n",
        "bob.yaml: languages[1] must be python or typescript\n",
    ),
    ("languages: ['']\n", "bob.yaml: languages[0] must be python or typescript\n"),
    ("languages: []\n", "bob.yaml: languages must not be empty\n"),
    ("languages: [python, python]\n", "bob.yaml: languages[1] repeats python\n"),
    ("languages: [ruby, ruby]\n", "bob.yaml: languages[0] must be python or typescript\n"),
    ("crap:\n  max_per_function: true\n", "bob.yaml: crap.max_per_function must be a number\n"),
    (
        f"crap:\n  max_per_function: {_HUGE_THRESHOLD}\n",
        "bob.yaml: crap.max_per_function must be finite\n",
    ),
    ("crap:\n  max_per_function: .nan\n", "bob.yaml: crap.max_per_function must be finite\n"),
    ("crap:\n  max_per_function: .inf\n", "bob.yaml: crap.max_per_function must be finite\n"),
    ("crap:\n  max_per_function: -.inf\n", "bob.yaml: crap.max_per_function must be finite\n"),
    ("crap:\n  max_per_function: 0\n", "bob.yaml: crap.max_per_function must be greater than 0\n"),
    (
        "crap:\n  max_per_function: 0.0\n",
        "bob.yaml: crap.max_per_function must be greater than 0\n",
    ),
    ("crap:\n  max_per_function: -1\n", "bob.yaml: crap.max_per_function must be greater than 0\n"),
    (
        "duplication:\n  min_tokens: true\n",
        "bob.yaml: duplication.min_tokens must be an integer\n",
    ),
    (
        'duplication:\n  min_tokens: "1"\n',
        "bob.yaml: duplication.min_tokens must be an integer\n",
    ),
    (
        "duplication:\n  min_tokens: 1.5\n",
        "bob.yaml: duplication.min_tokens must be an integer\n",
    ),
    (
        "duplication:\n  min_tokens: .inf\n",
        "bob.yaml: duplication.min_tokens must be an integer\n",
    ),
    (
        "duplication:\n  min_tokens: null\n",
        "bob.yaml: duplication.min_tokens must be an integer\n",
    ),
    (
        "duplication:\n  min_tokens: -1\n",
        "bob.yaml: duplication.min_tokens must be greater than 0\n",
    ),
    (
        "duplication:\n  min_tokens: 0\n",
        "bob.yaml: duplication.min_tokens must be greater than 0\n",
    ),
    (
        "duplication:\n  new_clones: block\n",
        "bob.yaml: duplication.new_clones must be warn or fail\n",
    ),
    ("duplication:\n  new_clones: 5\n", "bob.yaml: duplication.new_clones must be a string\n"),
    (
        "duplication:\n  max_new_clones: -1\n",
        "bob.yaml: duplication.max_new_clones must be at least 0\n",
    ),
    (
        "duplication:\n  max_new_clones: 1.5\n",
        "bob.yaml: duplication.max_new_clones must be an integer\n",
    ),
    (
        "duplication:\n  max_new_clones: true\n",
        "bob.yaml: duplication.max_new_clones must be an integer\n",
    ),
    ("duplication:\n  min_lines: -1\n", "bob.yaml: duplication.min_lines must be at least 0\n"),
    ("duplication:\n  min_lines: true\n", "bob.yaml: duplication.min_lines must be an integer\n"),
    (
        "duplication:\n  min_similarity: 101\n",
        "bob.yaml: duplication.min_similarity must be at most 100\n",
    ),
    (
        "duplication:\n  min_similarity: -1\n",
        "bob.yaml: duplication.min_similarity must be at least 0\n",
    ),
    (
        "duplication:\n  min_similarity: .nan\n",
        "bob.yaml: duplication.min_similarity must be finite\n",
    ),
    (
        'duplication:\n  min_similarity: "90"\n',
        "bob.yaml: duplication.min_similarity must be a number\n",
    ),
    ("duplication: 0\n", "bob.yaml: duplication must be a mapping\n"),
    ("duplication: false\n", "bob.yaml: duplication must be a mapping\n"),
    ('duplication: ""\n', "bob.yaml: duplication must be a mapping\n"),
    ("duplication: [1]\n", "bob.yaml: duplication must be a mapping\n"),
    ("test_smells: false\n", "bob.yaml: test_smells accepts only true\n"),
    ("test_smells: {}\n", "bob.yaml: test_smells accepts only true\n"),
    ("test_smells:\n  enabled: true\n", "bob.yaml: test_smells accepts only true\n"),
    ("test_smells: 1\n", "bob.yaml: test_smells accepts only true\n"),
    (
        "dead_code:\n  min_confidence: 101\n",
        "bob.yaml: dead_code.min_confidence must be an integer from 0 to 100\n",
    ),
    (
        "dead_code:\n  min_confidence: -1\n",
        "bob.yaml: dead_code.min_confidence must be an integer from 0 to 100\n",
    ),
    (
        "dead_code:\n  min_confidence: true\n",
        "bob.yaml: dead_code.min_confidence must be an integer\n",
    ),
    (
        "dead_code:\n  min_confidence: 1.5\n",
        "bob.yaml: dead_code.min_confidence must be an integer\n",
    ),
    ("0\n", "bob.yaml must be a mapping\n"),
    ("false\n", "bob.yaml must be a mapping\n"),
    ('""\n', "bob.yaml must be a mapping\n"),
)

_WAIVER_ENTRY = (
    "  - id: fn\n"
    "    reason: {reason}\n"
    "    author: ada\n"
    "    date: '2026-10-11'\n"
)

_BAD_WAIVER_VALUES = (
    ("0\n", ".bob/waivers.yaml must be a mapping\n"),
    ("false\n", ".bob/waivers.yaml must be a mapping\n"),
    ('""\n', ".bob/waivers.yaml must be a mapping\n"),
    ("waivers: 0\n", ".bob/waivers.yaml: waivers must be a list\n"),
    ("waivers: false\n", ".bob/waivers.yaml: waivers must be a list\n"),
    ('waivers: ""\n', ".bob/waivers.yaml: waivers must be a list\n"),
    ("notes: hi\n", ".bob/waivers.yaml: unknown key notes\n"),
    (
        "waivers:\n" + _WAIVER_ENTRY.format(reason='""'),
        ".bob/waivers.yaml: waivers[0].reason must be one non-empty line\n",
    ),
    (
        "waivers:\n" + _WAIVER_ENTRY.format(reason='"   "'),
        ".bob/waivers.yaml: waivers[0].reason must be one non-empty line\n",
    ),
    (
        "waivers:\n" + _WAIVER_ENTRY.format(reason='"a\\nb"'),
        ".bob/waivers.yaml: waivers[0].reason must be one non-empty line\n",
    ),
    (
        "waivers:\n" + _WAIVER_ENTRY.format(reason='"a\\rb"'),
        ".bob/waivers.yaml: waivers[0].reason must be one non-empty line\n",
    ),
    (
        "waivers:\n"
        + _WAIVER_ENTRY.format(reason="because")
        + "  - id: other\n"
        '    reason: ""\n'
        "    author: ada\n"
        "    date: '2026-10-11'\n",
        ".bob/waivers.yaml: waivers[1].reason must be one non-empty line\n",
    ),
    (
        "waivers:\n"
        "  - id: fn\n"
        "    reason: because\n"
        "    author: ada\n"
        "    date: '2026-10-11'\n"
        "    note: ignored\n",
        ".bob/waivers.yaml: unknown key waivers[0].note\n",
    ),
    (
        "waivers:\n  - note: ignored\n",
        ".bob/waivers.yaml: unknown key waivers[0].note\n",
    ),
    (
        "waivers:\n"
        "  - id: fn\n"
        "    reason: one\n"
        "    author: ada\n"
        "    date: '2026-10-11'\n"
        "  - id: fn\n"
        "    reason: two\n"
        "    author: ada\n"
        "    date: '2026-10-11'\n",
        ".bob/waivers.yaml: waivers[1].id repeats waivers[0].id\n",
    ),
    (
        "waivers:\n"
        '  - id: " fn "\n'
        "    reason: one\n"
        "    author: ada\n"
        "    date: '2026-10-11'\n"
        "  - id: fn\n"
        "    reason: two\n"
        "    author: ada\n"
        "    date: '2026-10-11'\n",
        ".bob/waivers.yaml: waivers[1].id repeats waivers[0].id\n",
    ),
)


@pytest.mark.parametrize("command", _SHAPE_COMMANDS)
@pytest.mark.parametrize(("text", "stderr"), _BAD_WAIVER_SHAPE)
@pytest.mark.parametrize("lang", [None, "pt-BR"])
def test_wrong_waiver_shape_exits_4_in_english_and_writes_no_report(
    tmp_path: Path,
    command: tuple[str, ...],
    text: str,
    stderr: str,
    lang: str | None,
) -> None:
    bob = tmp_path / ".bob"
    bob.mkdir()
    waiver = bob / "waivers.yaml"
    waiver.write_text(text)
    before = waiver.read_bytes()
    args = ("--lang", lang, *command) if lang is not None else command

    result = run_bob(tmp_path, *args)

    assert result.returncode == 4
    assert result.stderr == stderr
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert waiver.read_bytes() == before
    assert not (bob / "report.md").exists()
    assert not (bob / "report.json").exists()


@pytest.mark.parametrize("command", _COMMANDS)
@pytest.mark.parametrize(("text", "stderr"), _SEMANTIC_YAML)
@pytest.mark.parametrize("lang", [None, "pt-BR"])
def test_invalid_semantic_config_exits_4_in_english_and_writes_nothing(
    tmp_path: Path,
    command: tuple[str, ...],
    text: str,
    stderr: str,
    lang: str | None,
) -> None:
    (tmp_path / "bob.yaml").write_text(text)
    before = _files(tmp_path)
    args = ("--lang", lang, *command) if lang is not None else command

    result = run_bob(tmp_path, *args)

    assert result.returncode == 4
    assert result.stderr == stderr
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert _files(tmp_path) == before


_MISSING_INCLUDE = (
    (
        "paths:\n  include: [missing-root]\n",
        "bob.yaml: paths.include does not exist: missing-root\n",
    ),
)


@pytest.mark.parametrize("command", _COMMANDS)
@pytest.mark.parametrize(("text", "stderr"), _MISSING_INCLUDE)
@pytest.mark.parametrize("lang", [None, "pt-BR"])
def test_missing_include_exits_4_in_english_and_writes_nothing(
    tmp_path: Path,
    command: tuple[str, ...],
    text: str,
    stderr: str,
    lang: str | None,
) -> None:
    (tmp_path / "bob.yaml").write_text(text)
    before = _files(tmp_path)
    args = ("--lang", lang, *command) if lang is not None else command

    result = run_bob(tmp_path, *args)

    assert result.returncode == 4
    assert result.stderr == stderr
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert _files(tmp_path) == before


def test_missing_include_names_each_absent_entry(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "bob.yaml").write_text("paths:\n  include: [src, gone, also-gone]\n")

    result = run_bob(tmp_path, "check", "--lang", "pt-BR")

    assert result.returncode == 4
    assert result.stderr == "bob.yaml: paths.include does not exist: gone, also-gone\n"
    assert result.stdout == ""
    assert not (tmp_path / ".bob").exists()


def test_explicit_config_names_a_missing_include(tmp_path: Path) -> None:
    custom = tmp_path / "custom.yaml"
    custom.write_text("paths:\n  include: [nope]\n")

    result = run_bob(tmp_path, "crap", "--config", "custom.yaml")

    assert result.returncode == 4
    assert result.stderr == f"{custom.as_posix()}: paths.include does not exist: nope\n"
    assert result.stdout == ""
    assert not (tmp_path / ".bob").exists()


@pytest.mark.parametrize("command", _COMMANDS)
@pytest.mark.parametrize(("text", "stderr"), _BAD_WAIVER_VALUES)
@pytest.mark.parametrize("lang", [None, "pt-BR"])
def test_invalid_waiver_values_exit_4_in_english_and_write_no_report(
    tmp_path: Path,
    command: tuple[str, ...],
    text: str,
    stderr: str,
    lang: str | None,
) -> None:
    bob = tmp_path / ".bob"
    bob.mkdir()
    waiver = bob / "waivers.yaml"
    waiver.write_text(text)
    before = waiver.read_bytes()
    args = ("--lang", lang, *command) if lang is not None else command

    result = run_bob(tmp_path, *args)

    assert result.returncode == 4
    assert result.stderr == stderr
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert waiver.read_bytes() == before
    assert not (bob / "report.md").exists()
    assert not (bob / "report.json").exists()


@pytest.mark.parametrize("reason", ["", "   ", "a\nb", "a\rb"])
def test_waive_rejects_a_reason_that_is_not_one_line(tmp_path: Path, reason: str) -> None:
    result = run_bob(tmp_path, "waive", "fn", "--reason", reason)

    assert result.returncode == 4
    assert result.stderr == "waiver without a reason: pass --reason with one line\n"
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert not (tmp_path / ".bob" / "report.md").exists()
    assert not (tmp_path / ".bob" / "report.json").exists()


@pytest.mark.parametrize(
    ("text", "english", "portuguese"),
    [
        (
            "0\n",
            ".bob/waivers.yaml must be a mapping",
            ".bob/waivers.yaml deve ser um mapeamento",
        ),
        (
            "false\n",
            ".bob/waivers.yaml must be a mapping",
            ".bob/waivers.yaml deve ser um mapeamento",
        ),
        (
            '""\n',
            ".bob/waivers.yaml must be a mapping",
            ".bob/waivers.yaml deve ser um mapeamento",
        ),
        (
            "waivers: 0\n",
            ".bob/waivers.yaml: waivers must be a list",
            ".bob/waivers.yaml: waivers deve ser uma lista",
        ),
        (
            "waivers: false\n",
            ".bob/waivers.yaml: waivers must be a list",
            ".bob/waivers.yaml: waivers deve ser uma lista",
        ),
        (
            'waivers: ""\n',
            ".bob/waivers.yaml: waivers must be a list",
            ".bob/waivers.yaml: waivers deve ser uma lista",
        ),
        (
            "notes: hi\n",
            ".bob/waivers.yaml: unknown key notes",
            ".bob/waivers.yaml: chave desconhecida notes",
        ),
        (
            "notes: hi\nextra: there\n",
            ".bob/waivers.yaml: unknown key notes",
            ".bob/waivers.yaml: chave desconhecida notes",
        ),
        (
            "waivers:\n" + _WAIVER_ENTRY.format(reason='""'),
            ".bob/waivers.yaml: waivers[0].reason must be one non-empty line",
            ".bob/waivers.yaml: waivers[0].reason deve ser uma linha não vazia",
        ),
        (
            "waivers:\n" + _WAIVER_ENTRY.format(reason='"   "'),
            ".bob/waivers.yaml: waivers[0].reason must be one non-empty line",
            ".bob/waivers.yaml: waivers[0].reason deve ser uma linha não vazia",
        ),
        (
            "waivers:\n" + _WAIVER_ENTRY.format(reason='"a\\nb"'),
            ".bob/waivers.yaml: waivers[0].reason must be one non-empty line",
            ".bob/waivers.yaml: waivers[0].reason deve ser uma linha não vazia",
        ),
        (
            "waivers:\n" + _WAIVER_ENTRY.format(reason='"a\\rb"'),
            ".bob/waivers.yaml: waivers[0].reason must be one non-empty line",
            ".bob/waivers.yaml: waivers[0].reason deve ser uma linha não vazia",
        ),
        (
            "waivers:\n"
            "  - id: fn\n"
            "    reason: because\n"
            "    author: ada\n"
            "    date: '2026-10-11'\n"
            "    note: ignored\n",
            ".bob/waivers.yaml: unknown key waivers[0].note",
            ".bob/waivers.yaml: chave desconhecida waivers[0].note",
        ),
        (
            "waivers:\n  - note: ignored\n",
            ".bob/waivers.yaml: unknown key waivers[0].note",
            ".bob/waivers.yaml: chave desconhecida waivers[0].note",
        ),
        (
            "waivers:\n"
            "  - id: fn\n"
            "    reason: one\n"
            "    author: ada\n"
            "    date: '2026-10-11'\n"
            "  - id: fn\n"
            "    reason: two\n"
            "    author: ada\n"
            "    date: '2026-10-11'\n",
            ".bob/waivers.yaml: waivers[1].id repeats waivers[0].id",
            ".bob/waivers.yaml: waivers[1].id repete waivers[0].id",
        ),
    ],
)
def test_load_waivers_rejects_closed_values(
    tmp_path: Path, text: str, english: str, portuguese: str
) -> None:
    _write_waivers(tmp_path, text)

    with pytest.raises(WaiverError) as caught:
        load_waivers(tmp_path)

    assert in_both(caught.value) == (english, portuguese)


def test_load_waivers_rejects_an_entry_with_an_extra_key(tmp_path: Path) -> None:
    _write_waivers(
        tmp_path,
        "waivers:\n"
        "  - id: fn\n"
        "    reason: '  because  '\n"
        "    author: ada\n"
        "    date: '2026-10-11'\n"
        "    note: ignored\n",
    )

    with pytest.raises(WaiverError) as caught:
        load_waivers(tmp_path)

    assert in_both(caught.value) == (
        ".bob/waivers.yaml: unknown key waivers[0].note",
        ".bob/waivers.yaml: chave desconhecida waivers[0].note",
    )


@pytest.mark.parametrize(
    ("lang", "stderr"),
    [
        (
            None,
            "no survivor matches src/app/m.py::fn:"
            " copy file::function or a Target from the last mutation report\n",
        ),
        (
            "pt-BR",
            "nenhum sobrevivente casa com src/app/m.py::fn:"
            " copie arquivo::função ou um Alvo do último relatório de mutação\n",
        ),
    ],
)
def test_waive_without_a_mutation_report_keeps_the_yaml(
    tmp_path: Path, lang: str | None, stderr: str
) -> None:
    _write_waivers(
        tmp_path,
        "waivers:\n"
        "  - id: src/app/m.py::fn\n"
        "    reason: old\n"
        "    author: ada\n"
        "    date: '2026-10-11'\n",
    )
    before = (tmp_path / ".bob" / "waivers.yaml").read_bytes()
    args = ("waive", "src/app/m.py::fn", "--reason", "replaced")
    if lang is not None:
        args = ("--lang", lang, *args)

    result = run_bob(tmp_path, *args)

    assert result.returncode == 4
    assert result.stdout == ""
    assert result.stderr == stderr
    assert (tmp_path / ".bob" / "waivers.yaml").read_bytes() == before
    assert not (tmp_path / ".bob" / "report.md").exists()
    assert not (tmp_path / ".bob" / "report.json").exists()


@pytest.mark.parametrize("command", _COMMANDS)
@pytest.mark.parametrize("lang", [None, "pt-BR"])
def test_broken_waivers_yaml_exits_4_in_english_and_writes_nothing(
    tmp_path: Path, command: tuple[str, ...], lang: str | None
) -> None:
    bob = tmp_path / ".bob"
    bob.mkdir()
    waiver = bob / "waivers.yaml"
    waiver.write_text("waivers: [\n")
    before = waiver.read_bytes()
    args = ("--lang", lang, *command) if lang is not None else command

    result = run_bob(tmp_path, *args)

    assert result.returncode == 4
    assert result.stderr == "invalid YAML in .bob/waivers.yaml: while parsing a flow node\n"
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert waiver.read_bytes() == before
    assert not (bob / "report.md").exists()
    assert not (bob / "report.json").exists()
