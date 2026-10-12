"""Config inválida sai 4, em inglês no stderr, sem gravar nada."""

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
)


def test_load_waivers_rejects_invalid_yaml_in_both_languages(tmp_path: Path) -> None:
    bob = tmp_path / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text("waivers: [\n")

    with pytest.raises(WaiverError) as caught:
        load_waivers(tmp_path)

    assert in_both(caught.value) == (
        "invalid YAML in .bob/waivers.yaml: while parsing a flow node",
        "YAML inválido em .bob/waivers.yaml: while parsing a flow node",
    )


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
