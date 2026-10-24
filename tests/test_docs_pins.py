"""Paridade do prompt de IA (CT18) e pins dos docs (CT17)."""

from __future__ import annotations

import collections
import itertools
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from bob_quality import gitleaks, npm_tools, user_dirs

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "scripts" / "install.sh"
PROMPTS = {
    "en": ROOT / "docs" / "install-prompt.en.md",
    "pt-BR": ROOT / "docs" / "install-prompt.pt-BR.md",
}
_BLOCK = re.compile(
    r"^```sh bob-step=(?P<id>\S+) platform=(?P<p>\S+)\n(?P<body>.*?)^```$",
    re.M | re.S,
)
_PLATFORMS = ("linux-x64", "linux-arm64", "darwin-x64", "darwin-arm64")
_NOTES = {
    "en": "> Tests/release-check only:",
    "pt-BR": "> Somente testes/release-check:",
}


def _source(name: str) -> str:
    found = re.search(
        rf"^{name}='(.*)'$",
        INSTALL.read_text(encoding="utf-8"),
        re.M,
    )
    assert found is not None
    return found.group(1)


def _blocks(lang: str) -> list[tuple[str, str, str]]:
    text = PROMPTS[lang].read_text(encoding="utf-8")
    return [
        (found.group("id"), found.group("p"), found.group("body"))
        for found in _BLOCK.finditer(text)
    ]


def _bodies(step: str) -> list[tuple[str, str]]:
    return [(p, body) for step_id, p, body in _blocks("en") if step_id == step]


def _expand(p: str) -> tuple[str, ...]:
    if p == "all":
        return _PLATFORMS
    if p == "linux":
        return tuple(item for item in _PLATFORMS if item.startswith("linux-"))
    if p == "darwin":
        return tuple(item for item in _PLATFORMS if item.startswith("darwin-"))
    return (p,)


def test_prompt_blocks_are_the_same_in_both_languages() -> None:
    assert _blocks("en") == _blocks("pt-BR")
    assert len(_blocks("en")) == 19


def test_prompt_steps_follow_install_sh() -> None:
    ids = [k for k, _ in itertools.groupby(b[0] for b in _blocks("en"))]
    assert len(ids) == len(set(ids))
    steps = _source("STEPS").split()
    cut = steps.index("launcher") + 1
    want = steps[:cut] + ["gitleaks"] + steps[cut:] + ["verificação"]
    assert ids == want


def test_prompt_platforms_cover_each_step() -> None:
    seen = [k for k, _ in itertools.groupby(b[0] for b in _blocks("en"))]
    for step in seen:
        got = collections.Counter(x for p, _ in _bodies(step) for x in _expand(p))
        assert got == collections.Counter(_PLATFORMS)


@pytest.mark.parametrize(
    "extra",
    [
        {},
        {"XDG_DATA_HOME": "/x"},
        {"XDG_DATA_HOME": "x"},
        {"BOB_HOME": "/b"},
        {"BOB_HOME": "b"},
    ],
    ids=["none", "xdg_abs", "xdg_rel", "bob_home_abs", "bob_home_rel"],
)
def test_prompt_preamble_matches_bob_home(extra: dict[str, str]) -> None:
    pre = _blocks("en")[0][2].splitlines(keepends=True)[:6]
    preamble = "".join(pre)
    for lang in PROMPTS:
        for _step, _platform, body in _blocks(lang):
            assert body.startswith(preamble)
    env = {"HOME": "/h", "PATH": "/usr/bin:/bin", **extra}
    result = subprocess.run(
        ["sh", "-c", preamble + 'printf %s "$BOB_HOME"\n'],
        env=env,
        capture_output=True,
        text=True,
    )
    if extra == {"BOB_HOME": "b"}:
        assert result.returncode == 4
        assert result.stderr == "bob-prompt: launcher: BOB_HOME=b must be absolute\n"
        with pytest.raises(ValueError):
            user_dirs.bob_home(env)
    else:
        assert result.returncode == 0
        assert result.stdout == str(user_dirs.bob_home(env).root)


def test_prompt_gitleaks_matches_the_pins() -> None:
    for platform, body in _bodies("gitleaks"):
        key = tuple(platform.split("-"))
        asset, sha = gitleaks.ASSETS[key]
        assert f"A={asset}\n" in body
        assert f"S={sha}\n" in body
        versions = set(re.findall(r"(?<![\d.])\d+\.\d+\.\d+(?![\d.])", body))
        assert versions == {gitleaks.VERSION}
        assert gitleaks.DEFAULT_BASE_URL in body


def test_prompt_node_and_python_match_the_pins() -> None:
    node = _bodies("node")[0][1]
    r = npm_tools.node_range()
    assert f"# node: {r}\n" in node
    assert f"{r.floor} <= v < ({r.below_major},)" in node
    floor = re.search(
        r'^requires-python = ">=(\d+)\.(\d+)"$',
        (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
        re.M,
    )
    assert floor is not None
    assert f"({floor.group(1)}, {floor.group(2)})" in _bodies("python")[0][1]


def test_prompt_layout_matches_install_sh() -> None:
    launcher = _bodies("launcher")[0][1]
    assert 'ln -s "versions/$X"' in launcher
    assert "ln -sfn ../current/venv/bin/bob" in launcher
    assert 'L="$HOME/.local/bin/bob"' in launcher
    needle = f"../tools/gitleaks/{gitleaks.VERSION}/gitleaks"
    for _platform, body in _bodies("gitleaks"):
        assert needle in body
    pacote = _bodies("pacote")[0][1]
    assert pacote.index('.complete"\n') > pacote.index('pip" install')


def test_prompt_profile_matches_install_sh() -> None:
    line = _source("PROFILE_LINE")
    perfil = _bodies("perfil")[0][1]
    assert f"LINE='{line}'\n" in perfil
    assert "'#" + line.split(" #", 1)[1] + "'" in perfil
    assert 'R="already-marked:$F"' in perfil
    assert "R=already-marked\n" not in perfil
    assert "S=${SHELL:-}\n" in perfil
    assert '"${SHELL##*/}"' not in perfil


def test_prompt_urls_and_options_match_install_sh() -> None:
    versao = _bodies("versão")[0][1]
    assert f'API="{_source("DEFAULT_API")}"' in versao
    assert f'DL="{_source("DEFAULT_DOWNLOAD")}"' in versao
    allbodies = "".join(b for _, _, b in _blocks("en"))
    curl = "curl " + _source("CURL_OPTS") + " "
    assert allbodies.count("curl -") == allbodies.count(curl) > 0
    pip = 'pip" install ' + _source("PIP_OPTS") + " "
    assert pip in _bodies("pacote")[0][1]


def test_prompt_blocks_never_use_install_sh_or_sudo() -> None:
    dash = shutil.which("dash")
    for lang in PROMPTS:
        for _step, _platform, body in _blocks(lang):
            assert "install.sh" not in body
            assert re.search(r"\bsudo\b", body) is None
            syntax = subprocess.run(
                ["sh", "-n"],
                input=body,
                text=True,
                capture_output=True,
            )
            assert syntax.returncode == 0
            if dash is not None:
                syntax = subprocess.run(
                    ["dash", "-n"],
                    input=body,
                    text=True,
                    capture_output=True,
                )
                assert syntax.returncode == 0


@pytest.mark.parametrize("lang", ["en", "pt-BR"])
def test_bob_version_is_read_only_in_the_prompt(lang: str) -> None:
    text = PROMPTS[lang].read_text(encoding="utf-8")
    cited = {step for step, _p, body in _blocks(lang) if "BOB_VERSION" in body}
    assert cited == {"versão"}
    for _step, _platform, body in _blocks(lang):
        assigned = re.search(r"(^|[;\s])(export\s+)?BOB_VERSION=", body, re.M)
        assert assigned is None
        assert re.search(r'fail "[^"]*BOB_VERSION', body) is None
    outside = _BLOCK.sub("", text)
    mentioned = [line for line in outside.splitlines() if "BOB_VERSION" in line]
    assert len(mentioned) == 1
    assert mentioned[0].startswith(_NOTES[lang])


def test_install_sh_mentions_bob_version_only_when_invalid() -> None:
    found = sorted(
        line.strip()
        for line in INSTALL.read_text(encoding="utf-8").splitlines()
        if "BOB_VERSION" in line
    )
    assert found == sorted(
        [
            '_msg="install: versão: BOB_VERSION=$_p1 inválida. Use vX.Y.Z." ;;',
            '_msg="install: versão: BOB_VERSION=$_p1 is invalid. Use vX.Y.Z." ;;',
            "_pinned=${BOB_VERSION:-}",
        ]
    )


@pytest.mark.parametrize(
    ("lang", "title", "alt", "rules"),
    [
        (
            "en",
            "# Install bob with your AI agent",
            "> Alternative path. The main path is the install.sh one-liner; "
            "if they differ, the one-liner wins.",
            "## Rules",
        ),
        (
            "pt-BR",
            "# Instalar o bob com o seu agente de IA",
            "> Caminho alternativo. O principal é o comando único do install.sh; "
            "em divergência, vale ele.",
            "## Regras",
        ),
    ],
)
def test_prompt_files_have_the_fixed_frame(
    lang: str,
    title: str,
    alt: str,
    rules: str,
) -> None:
    text = PROMPTS[lang].read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == title
    assert lines[2] == alt
    assert lines.count(rules) == 1
    ids = [k for k, _ in itertools.groupby(b[0] for b in _blocks("en"))]
    headings = [line for line in lines if re.fullmatch(r"## \d+\. \S+", line)]
    assert headings == [f"## {n}. {step}" for n, step in enumerate(ids, 1)]
    assert [line for line in lines if line][-1].startswith(_NOTES[lang])
