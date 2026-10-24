"""Modelo do release-check e o registro da v0.1.0 (CT13)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs" / "release-checks" / "TEMPLATE.md"
V0_1_0 = ROOT / "docs" / "release-checks" / "v0.1.0.md"
_PAIR = (TEMPLATE, V0_1_0)
_SECTIONS = (
    "Comando de Verificação na matriz (automático)",
    "Verificação manual (projeto do passo 2, skills só em .agents/skills)",
    "Prompt de IA (CT18, alternativa sem install.sh)",
    "Fluxo",
)
_SCRIPT = "Roteiro da release (E0–E6)"
_MANUAL = _SECTIONS[1]
_MATRIX = _SECTIONS[0]
_AGENTS = (
    "Cursor",
    "Claude Code (RA1; ADR 0009 Risco 1)",
    "GitHub Copilot",
    "Devin CLI",
    "Devin web",
)
_RUNNERS = (
    "`ubuntu-latest`",
    "`ubuntu-24.04-arm`",
    "`macos-15-intel`",
    "`macos-15`",
)
_COMMANDS = (
    (
        "gh workflow run release.yml --repo fazedordecodigo/bob "
        "--ref main -f tag=v0.1.0 -f prerelease=true -f dry_run=true"
    ),
    (
        "gh workflow run release.yml --repo fazedordecodigo/bob "
        "--ref main -f tag=v0.1.0 -f prerelease=true -f dry_run=false"
    ),
    (
        "curl -s -o /dev/null -w '%{http_code}' "
        "https://api.github.com/repos/fazedordecodigo/bob/releases/latest"
    ),
    (
        "curl -fsSL https://github.com/fazedordecodigo/bob/releases/download/"
        "v0.1.0/install.sh | BOB_VERSION=v0.1.0 sh"
    ),
    (
        "gh release edit v0.1.0 --repo fazedordecodigo/bob "
        "--prerelease=false --latest"
    ),
)


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _data_rows(path: Path, title: str) -> list[list[str]]:
    lines = _lines(path)
    rows: list[list[str]] = []
    body = False
    for line in lines[lines.index(f"## {title}") + 1 :]:
        if line.startswith("## "):
            break
        if line.startswith("|---"):
            body = True
            continue
        if body and line.startswith("|"):
            rows.append([cell.strip() for cell in line.strip("|").split("|")])
            continue
        if body:
            break
    return rows


def _e_heads(path: Path) -> list[str]:
    found: list[str] = []
    for line in _lines(path):
        for number in range(7):
            head = f"### E{number}"
            if line == head or line.startswith(head + " "):
                found.append(head)
                break
    return found


def test_release_check_titles() -> None:
    assert _lines(TEMPLATE)[0] == "# Release check vX.Y.Z"
    assert _lines(V0_1_0)[0] == "# Release check v0.1.0"
    assert "v0.1.0" not in TEMPLATE.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", _PAIR, ids=["TEMPLATE", "v0.1.0"])
def test_release_checks_have_the_ct13_sections(path: Path) -> None:
    got = [line for line in _lines(path) if line.startswith("## ")]
    want = [f"## {title}" for title in _SECTIONS]
    if path.name == "v0.1.0.md":
        want.append(f"## {_SCRIPT}")
    assert got == want


@pytest.mark.parametrize("path", _PAIR, ids=["TEMPLATE", "v0.1.0"])
def test_manual_table_lists_the_five_agents(path: Path) -> None:
    assert [row[0] for row in _data_rows(path, _MANUAL)] == list(_AGENTS)


@pytest.mark.parametrize("path", _PAIR, ids=["TEMPLATE", "v0.1.0"])
def test_matrix_table_lists_the_four_runners(path: Path) -> None:
    assert [row[1] for row in _data_rows(path, _MATRIX)] == list(_RUNNERS)


def test_v0_1_0_has_the_e0_to_e6_script() -> None:
    lines = _lines(V0_1_0)
    assert _e_heads(V0_1_0) == [f"### E{number}" for number in range(7)]
    for command in _COMMANDS:
        assert command in lines


@pytest.mark.parametrize("path", _PAIR, ids=["TEMPLATE", "v0.1.0"])
def test_release_checks_have_no_relative_links(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    start = 0
    while True:
        found = text.find("](", start)
        if found < 0:
            break
        assert text.startswith("https://", found + 2)
        start = found + 2
