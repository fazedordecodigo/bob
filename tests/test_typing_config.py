"""A chave `typing` no bob.yaml não liga o gate e não guarda estado."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from helpers import init_python_repo, run_bob

from bob_quality.config import Config, load_config

_COMMANDS = (
    ("check", "--gates", "nope"),
    ("crap",),
    ("dry",),
    ("deps",),
    ("mutate",),
    ("doctor",),
    ("waive", "fn", "--reason", "because"),
)


def _files(repo: Path) -> set[str]:
    return {
        path.relative_to(repo).as_posix()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }


@pytest.mark.parametrize("text", ["typing: {}\n", "typing:\n", "typing: null\n"])
def test_typing_mapping_stores_nothing_on_config(tmp_path: Path, text: str) -> None:
    (tmp_path / "bob.yaml").write_text("base: trunk\n" + text)

    assert load_config(None, tmp_path) == Config(base="trunk")


def test_empty_typing_mapping_lets_check_write_the_report(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    config = repo / "bob.yaml"
    config.write_text(config.read_text() + "typing: {}\n")

    result = run_bob(repo, "check", "--gates", "nope", "--base", "main")

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    assert payload["exit_code"] == 0
    assert payload["schema_version"] == 1
    assert payload["gates"] == [
        {
            "name": "nope",
            "status": "not_run",
            "reason": "gate not implemented in this slice",
        }
    ]
    assert "typing" not in payload


@pytest.mark.parametrize("command", _COMMANDS)
@pytest.mark.parametrize(
    ("text", "stderr"),
    [
        ("typing:\n  threshold: 1\n", "bob.yaml: unknown key typing.threshold\n"),
        ("typing: 1\n", "bob.yaml: typing must be a mapping\n"),
        ("typing: []\n", "bob.yaml: typing must be a mapping\n"),
        ("typing: false\n", "bob.yaml: typing must be a mapping\n"),
    ],
)
def test_bad_typing_value_exits_4_and_writes_nothing(
    tmp_path: Path, command: tuple[str, ...], text: str, stderr: str
) -> None:
    (tmp_path / "bob.yaml").write_text(text)
    before = _files(tmp_path)

    result = run_bob(tmp_path, *command)

    assert result.returncode == 4
    assert result.stderr == stderr
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert _files(tmp_path) == before
