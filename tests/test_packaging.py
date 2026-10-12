"""Empacotamento (issue #10, docs/SPEC.md, seção Empacotamento).

Seams:

1. Manifestos lidos pelos agentes: `.claude-plugin/plugin.json` (Claude Code,
   Copilot e Devin), `.claude-plugin/marketplace.json` e `.cursor-plugin/plugin.json`.
2. Instalador `bob_quality.install_skills`: recebe argv e devolve exit code,
   stdout, stderr e a árvore de skills no projeto.
3. Seção Empacotamento de `docs/SPEC.md`: aponta os manifestos e não cita pasta de skill.

Os nomes esperados são literais: as três skills do bob.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from bob_quality import install_skills

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
BOB_CHECK_SKILL = ROOT / "skills" / "bob-check" / "SKILL.md"
CLAUDE_PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
CLAUDE_MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
CURSOR_PLUGIN = ROOT / ".cursor-plugin" / "plugin.json"

BOB_SKILLS = ["bob-check", "harden", "review-report"]
RETIRED_SKILL_NAMES = (
    "ask-matt",
    "code-review",
    "codebase-design",
    "diagnosing-bugs",
    "domain-modeling",
    "grill-me",
    "grill-with-docs",
    "grilling",
    "handoff",
    "implement",
    "implement-spec",
    "improve-codebase-architecture",
    "pr",
    "prototype",
    "research",
    "retro",
    "setup-matt-pocock-skills",
    "tdd",
    "teach",
    "to-questionnaire",
    "to-spec",
    "to-tickets",
    "triage",
    "wait-what",
    "wayfinder",
    "wizard",
    "writing-for-agents",
)

# Schema do Cursor tem additionalProperties: false. Chave fora daqui invalida o plugin.
CURSOR_ALLOWED_KEYS = {
    "name",
    "displayName",
    "description",
    "version",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "logo",
    "rules",
    "agents",
    "skills",
    "commands",
    "hooks",
    "mcpServers",
    "variables",
    "publisher",
    "category",
    "tags",
    "minClientVersions",
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _skill_folders(entries: list[str]) -> list[Path]:
    """Mesma leitura dos agentes: cada entrada é a pasta de uma skill."""
    return [ROOT / entry for entry in entries]


def _frontmatter(skill_md: Path) -> dict:
    _, block, _ = skill_md.read_text(encoding="utf-8").split("---\n", 2)
    return yaml.safe_load(block)


def test_manifests_name_bob_with_mit_license_and_pyproject_version() -> None:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    for path in (CLAUDE_PLUGIN, CLAUDE_MARKETPLACE, CURSOR_PLUGIN):
        data = _json(path)
        assert data["name"] == "bob", path
    for path in (CLAUDE_PLUGIN, CURSOR_PLUGIN):
        data = _json(path)
        assert data["license"] == "MIT", path
        assert data["version"] == version, path


def test_marketplace_lists_only_bob_from_the_plugin_root() -> None:
    marketplace = _json(CLAUDE_MARKETPLACE)
    assert marketplace["owner"] == {"name": "Emerson Delatorre"}
    assert [plugin["name"] for plugin in marketplace["plugins"]] == ["bob"]
    entry = marketplace["plugins"][0]
    assert entry["source"] == "./"


def test_cursor_manifest_uses_only_schema_keys_and_displays_bob() -> None:
    cursor = _json(CURSOR_PLUGIN)
    assert set(cursor) <= CURSOR_ALLOWED_KEYS
    assert cursor["displayName"] == "bob"


def test_cursor_and_claude_manifests_list_the_same_skills() -> None:
    cursor_skills = _json(CURSOR_PLUGIN)["skills"]
    assert cursor_skills == _json(CLAUDE_PLUGIN)["skills"]
    assert len(cursor_skills) == len(BOB_SKILLS)


_SKILL_PATH = re.compile(
    r"(?<![\w.-])(?:\.[\\/])?skills[\\/][\w.\\/-]*",
    re.IGNORECASE,
)


def _packaging_section(text: str) -> str:
    lines = text.splitlines()
    start = lines.index("**Empacotamento**:")
    end = next(index for index in range(start + 1, len(lines)) if lines[index].startswith("#"))
    return "\n".join(lines[start:end])


def _spec_violations(section: str, entries: list[str]) -> list[str]:
    violations: list[str] = []
    for entry in entries:
        if entry in section:
            violations.append(f"entrada {entry}")
        bare = entry.removeprefix("./")
        if bare != entry and bare in section:
            violations.append(f"entrada {bare}")
    violations.extend(f"caminho {match}" for match in _SKILL_PATH.findall(section))
    return violations


def test_spec_points_to_the_manifest_instead_of_listing_skills() -> None:
    text = (ROOT / "docs" / "SPEC.md").read_text(encoding="utf-8")
    section = _packaging_section(text)

    assert section != ""
    assert text.split(section, 1)[1].lstrip("\n").startswith("## Testing Decisions")
    assert _spec_violations(section, _json(CLAUDE_PLUGIN)["skills"]) == []
    assert ".claude-plugin/plugin.json" in section
    assert "fonte única" in section
    assert ".cursor-plugin/plugin.json" in section
    assert "Não há `.plugin/`" in section


@pytest.mark.parametrize(
    ("spec", "entries", "violations"),
    [
        (
            "- skills/bob-check",
            ["./skills/bob-check"],
            ["entrada skills/bob-check", "caminho skills/bob-check"],
        ),
        (
            "\n".join(
                [
                    "**Empacotamento**:",
                    "- o campo `skills` de `.claude-plugin/plugin.json` é a fonte única da lista de skills. "
                    "`.cursor-plugin/plugin.json` repete a mesma lista.",
                    "",
                    "- ./skills/grupo/aninhada",
                    "",
                    "## Next",
                ]
            ),
            ["./skills/grupo/aninhada"],
            [
                "entrada ./skills/grupo/aninhada",
                "entrada skills/grupo/aninhada",
                "caminho ./skills/grupo/aninhada",
            ],
        ),
    ],
    ids=["sem-ponto-barra", "depois-da-linha-em-branco"],
)
def test_spec_violations_catch_a_bare_skill_path_and_one_after_a_blank_line(
    spec: str, entries: list[str], violations: list[str]
) -> None:
    if spec.startswith("**Empacotamento**:"):
        section = _packaging_section(spec)
        assert "## Next" not in section
        assert "\n\n- ./skills/grupo/aninhada" in section
    else:
        section = spec
    assert _spec_violations(section, entries) == violations


@pytest.mark.parametrize(
    ("spec", "violations"),
    [
        ("Skills/bob-check", ["caminho Skills/bob-check"]),
        ("SKILLS/BOB-CHECK", ["caminho SKILLS/BOB-CHECK"]),
        ("Skills/", ["caminho Skills/"]),
        ("SKILLS/", ["caminho SKILLS/"]),
        ("skills\\bob-check", ["caminho skills\\bob-check"]),
        (".\\Skills\\example\\SKILL.md", ["caminho .\\Skills\\example\\SKILL.md"]),
        ("minha-skills/x", []),
        (".skills/x", []),
        (".github/skills", []),
        (".agents/skills", []),
    ],
    ids=[
        "skills-capitalizado",
        "skills-maiusculo",
        "pasta-skills-capitalizada",
        "pasta-skills-maiuscula",
        "barra-invertida",
        "ponto-barra-invertida",
        "prefixo-hifen",
        "prefixo-ponto",
        "github-skills",
        "agents-skills",
    ],
)
def test_spec_violations_catch_case_and_backslash_skill_paths(
    spec: str, violations: list[str]
) -> None:
    assert _spec_violations(spec, []) == violations


def test_each_manifest_entry_is_a_relative_skill_folder() -> None:
    for entry in _json(CLAUDE_PLUGIN)["skills"]:
        assert entry.startswith("./"), entry
        assert ".." not in Path(entry).parts, entry
        assert (ROOT / entry / "SKILL.md").is_file(), entry


def test_manifest_reaches_exactly_the_expected_skills() -> None:
    folders = _skill_folders(_json(CLAUDE_PLUGIN)["skills"])
    assert sorted(folder.name for folder in folders) == sorted(BOB_SKILLS)


def test_each_reachable_skill_declares_its_folder_name_and_a_description() -> None:
    for folder in _skill_folders(_json(CLAUDE_PLUGIN)["skills"]):
        meta = _frontmatter(folder / "SKILL.md")
        assert meta["name"] == folder.name, folder
        assert isinstance(meta["description"], str) and meta["description"], folder


# O instalador roda no processo do pytest: o mutmut só associa um teste a uma
# função quando o trampolim dela dispara aqui, nunca num subprocesso.
def _install(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = install_skills.main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def _installed(*dests: str) -> str:
    return "".join(f"{len(BOB_SKILLS)} skills em {d}\n" for d in dests)


def test_copilot_installs_every_manifest_skill_flat_into_github_skills(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = _install(capsys, "--project", str(tmp_path), "copilot")

    dest = tmp_path / ".github" / "skills"
    assert result == (0, _installed(".github/skills"), "")
    assert sorted(path.name for path in dest.iterdir()) == sorted(BOB_SKILLS)
    assert (dest / "bob-check" / "SKILL.md").read_bytes() == BOB_CHECK_SKILL.read_bytes()


def test_targets_that_share_a_folder_write_it_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = _install(capsys, "--project", str(tmp_path), "devin", "agents", "copilot")

    assert result == (0, _installed(".agents/skills", ".github/skills"), "")
    installed = sorted(path.name for path in (tmp_path / ".agents" / "skills").iterdir())
    assert installed == sorted(BOB_SKILLS)


def _files(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_reinstall_replaces_bob_skills_and_keeps_the_projects_own(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / ".github" / "skills"
    (dest / "mine").mkdir(parents=True)
    (dest / "mine" / "SKILL.md").write_text("minha skill\n")
    (dest / "bob-check").mkdir()
    (dest / "bob-check" / "stale.md").write_text("de uma versão antiga\n")

    first = _install(capsys, "--project", str(tmp_path), "copilot")
    after_first = _files(dest)
    second = _install(capsys, "--project", str(tmp_path), "copilot")

    assert first == second == (0, _installed(".github/skills"), "")
    assert (dest / "mine" / "SKILL.md").read_text() == "minha skill\n"
    assert not (dest / "bob-check" / "stale.md").exists()
    assert (dest / "bob-check" / "SKILL.md").read_bytes() == BOB_CHECK_SKILL.read_bytes()
    assert _files(dest) == after_first


# Texto que o instalador antigo copiava de skills/vendor/mattpocock/NOTICE (2347154).
OLD_INSTALL_NOTICE = """\
Matt Pocock agent skills, vendored for the bob plugin.

Source:  https://github.com/mattpocock/skills
Commit:  49dd158d1076134a641b33efb035946536778336
Date:    2026-10-09
License: MIT (see LICENSE in this directory)
Copyright (c) 2026 Matt Pocock

This tree is a verbatim copy of the upstream `skills/` directory at that
commit, plus the upstream LICENSE. Do not edit the vendored files; re-copy
from the pin above.
"""


def _kept(path: Path, reason: str) -> str:
    return f"aviso: {path} ficou, porque {reason}."


def test_reinstall_removes_a_retired_folder_only_when_its_notice_is_the_old_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert len(RETIRED_SKILL_NAMES) == 27
    assert len(set(RETIRED_SKILL_NAMES)) == 27
    dest = tmp_path / ".github" / "skills"
    (dest / "mine").mkdir(parents=True)
    (dest / "mine" / "SKILL.md").write_text("minha skill\n")
    for name in RETIRED_SKILL_NAMES:
        folder = dest / name
        folder.mkdir()
        (folder / "SKILL.md").write_text("antiga\n")
        (folder / "NOTICE").write_text(OLD_INSTALL_NOTICE)

    first = _install(capsys, "--project", str(tmp_path), "copilot")
    after_first = _files(dest)
    second = _install(capsys, "--project", str(tmp_path), "copilot")

    assert first == second == (0, _installed(".github/skills"), "")
    assert (dest / "mine" / "SKILL.md").read_text() == "minha skill\n"
    for name in RETIRED_SKILL_NAMES:
        assert not (dest / name).exists(), name
    assert not any(path.endswith("/NOTICE") or path == "NOTICE" for path in after_first)
    assert sorted(path.name for path in dest.iterdir()) == sorted([*BOB_SKILLS, "mine"])
    assert _files(dest) == after_first


def test_reinstall_keeps_a_user_skill_that_only_shares_a_retired_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / ".github" / "skills"
    (dest / "tdd").mkdir(parents=True)
    (dest / "tdd" / "SKILL.md").write_text("minha revisão\n")
    (dest / "tdd" / "NOTICE").write_text("aviso meu\n")
    (dest / "code-review").mkdir()
    (dest / "code-review" / "SKILL.md").write_text("sem notice\n")
    expected = "\n".join(
        sorted(
            [
                _kept(dest / "tdd", "o NOTICE não é o da instalação antiga"),
                _kept(dest / "code-review", "o NOTICE não é o da instalação antiga"),
            ]
        )
    ) + "\n"

    first = _install(capsys, "--project", str(tmp_path), "copilot")
    after_first = _files(dest)
    second = _install(capsys, "--project", str(tmp_path), "copilot")

    assert (dest / "tdd" / "SKILL.md").read_text() == "minha revisão\n"
    assert (dest / "tdd" / "NOTICE").read_text() == "aviso meu\n"
    assert (dest / "code-review" / "SKILL.md").read_text() == "sem notice\n"
    assert not (dest / "code-review" / "NOTICE").exists()
    assert first[0] == second[0] == 0
    assert first[1] == second[1] == _installed(".github/skills")
    assert "\n".join(sorted(first[2].splitlines())) + "\n" == expected
    assert "\n".join(sorted(second[2].splitlines())) + "\n" == expected
    assert _files(dest) == after_first


def test_reinstall_keeps_a_file_named_like_a_retired_skill(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / ".github" / "skills"
    dest.mkdir(parents=True)
    (dest / "pr").write_text("não é pasta\n")
    warning = _kept(dest / "pr", "é um arquivo ou um link simbólico") + "\n"

    first = _install(capsys, "--project", str(tmp_path), "copilot")
    after_first = _files(dest)
    second = _install(capsys, "--project", str(tmp_path), "copilot")

    assert first == second == (0, _installed(".github/skills"), warning)
    assert (dest / "pr").read_text() == "não é pasta\n"
    assert (dest / "pr").is_file()
    assert not (dest / "pr").is_symlink()
    assert _files(dest) == after_first


def test_reinstall_keeps_a_symlink_named_like_a_retired_skill(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / ".github" / "skills"
    dest.mkdir(parents=True)
    outside = tmp_path / "alvo"
    outside.mkdir()
    (outside / "SKILL.md").write_text("alvo\n")
    link = dest / "grill-me"
    link.symlink_to(outside, target_is_directory=True)
    warning = _kept(link, "é um arquivo ou um link simbólico") + "\n"

    first = _install(capsys, "--project", str(tmp_path), "copilot")
    after_first = _files(dest)
    second = _install(capsys, "--project", str(tmp_path), "copilot")

    assert first == second == (0, _installed(".github/skills"), warning)
    assert link.is_symlink()
    assert link.readlink() == outside
    assert (outside / "SKILL.md").read_text() == "alvo\n"
    assert _files(dest) == after_first


def test_reinstall_keeps_a_retired_folder_when_its_notice_is_a_symlink(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / ".github" / "skills"
    folder = dest / "tdd"
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text("minha\n")
    original = tmp_path / "notice-real"
    original.write_text(OLD_INSTALL_NOTICE)
    notice = folder / "NOTICE"
    notice.symlink_to(original)
    warning = _kept(folder, "o NOTICE não é o da instalação antiga") + "\n"

    first = _install(capsys, "--project", str(tmp_path), "copilot")
    after_first = _files(dest)
    second = _install(capsys, "--project", str(tmp_path), "copilot")

    assert (folder / "SKILL.md").read_text() == "minha\n"
    assert notice.is_symlink()
    assert notice.readlink() == original
    assert original.read_text() == OLD_INSTALL_NOTICE
    assert first == second == (0, _installed(".github/skills"), warning)
    assert _files(dest) == after_first


def test_every_installed_skill_carries_the_plugin_license(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = _install(capsys, "--project", str(tmp_path), "copilot", "devin")

    assert result == (0, _installed(".github/skills", ".agents/skills"), "")
    for dest in (tmp_path / ".github" / "skills", tmp_path / ".agents" / "skills"):
        for name in BOB_SKILLS:
            assert (dest / name / "LICENSE").read_bytes() == (ROOT / "LICENSE").read_bytes(), name
            assert not (dest / name / "NOTICE").exists(), name


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_each_skill_bundles_the_nearest_license_inside_the_plugin(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "plugin"
    _write(tmp_path / "LICENSE", "fora do plugin\n")
    _write(source / "skills" / "solta" / "SKILL.md", "solta\n")
    _write(source / "skills" / "vendor" / "LICENSE", "do vendor\n")
    _write(source / "skills" / "vendor" / "NOTICE", "aviso do vendor\n")
    _write(source / "skills" / "vendor" / "propria" / "SKILL.md", "propria\n")
    _write(source / "skills" / "vendor" / "propria" / "agents" / "openai.yaml", "interface: propria\n")
    _write(source / "skills" / "vendor" / "propria" / "LICENSE", "da propria\n")
    _write(source / "skills" / "vendor" / "herdada" / "SKILL.md", "herdada\n")
    # propria vem antes da solta: se o continue virar break, o aviso da solta some.
    skills = ["./skills/vendor/propria", "./skills/solta", "./skills/vendor/herdada"]
    _write(source / ".claude-plugin" / "plugin.json", json.dumps({"skills": skills}))
    source_before = _files(source)
    project = tmp_path / "projeto"

    result = _install(
        capsys, "--project", str(project), "--source", str(source), "copilot", "devin"
    )

    installed = {
        "solta/SKILL.md": b"solta\n",
        "propria/SKILL.md": b"propria\n",
        "propria/LICENSE": b"da propria\n",
        "propria/agents/openai.yaml": b"interface: propria\n",
        "herdada/SKILL.md": b"herdada\n",
        "herdada/LICENSE": b"do vendor\n",
    }
    assert result == (
        0,
        "3 skills em .github/skills\n3 skills em .agents/skills\n",
        "aviso: a skill solta não tem LICENSE entre a pasta dela e a raiz do plugin "
        f"{source}; instalada sem licença.\n",
    )
    for dest in (project / ".github" / "skills", project / ".agents" / "skills"):
        assert _files(dest) == installed
    assert _files(source) == source_before

    real = _install(capsys, "--project", str(tmp_path / "repo"), "copilot")
    assert real == (0, _installed(".github/skills"), "")


def test_relative_source_from_the_repo_installs_bob_skills_with_the_root_license(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(ROOT)

    result = _install(capsys, "--project", str(tmp_path), "--source", ".", "copilot", "devin")

    assert result == (0, _installed(".github/skills", ".agents/skills"), "")
    license_bytes = (ROOT / "LICENSE").read_bytes()
    for dest in (tmp_path / ".github" / "skills", tmp_path / ".agents" / "skills"):
        for name in BOB_SKILLS:
            assert (dest / name / "LICENSE").read_bytes() == license_bytes, name


def test_partial_copy_without_root_license_names_the_root_it_searched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "parcial"
    shutil.copytree(ROOT / ".claude-plugin", source / ".claude-plugin")
    shutil.copytree(ROOT / "skills", source / "skills")
    project = tmp_path / "projeto"
    source_arg = str(source)

    result = _install(capsys, "--project", str(project), "--source", source_arg, "copilot")

    warnings = "".join(
        f"aviso: a skill {name} não tem LICENSE entre a pasta dela e a raiz do plugin "
        f"{source_arg}; instalada sem licença.\n"
        for name in BOB_SKILLS
    )
    assert result == (0, _installed(".github/skills"), warnings)
    dest = project / ".github" / "skills"
    for name in BOB_SKILLS:
        assert not (dest / name / "LICENSE").exists(), name


def test_project_defaults_to_the_current_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = _install(capsys, "agents")

    assert result == (0, _installed(".agents/skills"), "")
    assert (tmp_path / ".agents" / "skills" / "bob-check" / "SKILL.md").is_file()


def test_unknown_target_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as raised:
        install_skills.main(["--project", str(tmp_path), "copilot", "vscode"])

    assert raised.value.code == 2
    assert "'vscode'" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_source_without_manifest_exits_4_and_suggests_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "vazio"
    source.mkdir()
    project = tmp_path / "projeto"

    result = _install(capsys, "--project", str(project), "--source", str(source), "copilot")

    manifest = source / ".claude-plugin" / "plugin.json"
    assert result == (
        4,
        "",
        f"manifesto não encontrado: {manifest}. Passe --source com a raiz do plugin bob.\n",
    )
    assert not project.exists()


@pytest.mark.parametrize(
    ("content", "detail"),
    [
        (b"{", "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"),
        (b"\xff", "'utf-8' codec can't decode byte 0xff in position 0: invalid start byte"),
    ],
    ids=["json-quebrado", "bytes-fora-do-utf8"],
)
def test_invalid_json_exits_4_and_shows_where_it_broke(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: bytes, detail: str
) -> None:
    manifest = tmp_path / "plugin" / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_bytes(content)
    project = tmp_path / "projeto"

    result = _install(
        capsys, "--project", str(project), "--source", str(tmp_path / "plugin"), "copilot"
    )

    assert result == (
        4,
        "",
        f"JSON inválido em {manifest}: {detail}\n",
    )
    assert not project.exists()


@pytest.mark.parametrize(
    "content",
    ['["./skills/bob-check"]', "[]", "1", '"x"'],
    ids=["raiz-nao-objeto", "lista-vazia", "numero", "texto"],
)
def test_manifest_root_that_is_not_an_object_exits_4(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: str
) -> None:
    manifest = tmp_path / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir()
    manifest.write_text(content)

    result = _install(capsys, "--project", str(tmp_path), "--source", str(tmp_path), "copilot")

    assert result == (4, "", f"manifesto não é objeto JSON: {manifest}\n")
    assert not (tmp_path / ".github").exists()


@pytest.mark.parametrize(
    "content",
    ['{"skills": "./skills/"}', '{"skills": [1]}'],
    ids=["skills-texto", "pasta-nao-texto"],
)
def test_malformed_manifest_exits_4_and_names_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: str
) -> None:
    manifest = tmp_path / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir()
    manifest.write_text(content)

    result = _install(capsys, "--project", str(tmp_path), "--source", str(tmp_path), "copilot")

    assert result == (
        4,
        "",
        f"manifesto inválido (skills deve ser uma lista de pastas): {manifest}\n",
    )
    assert not (tmp_path / ".github").exists()


@pytest.mark.parametrize(
    ("entry", "folder"),
    [("./skills/", "skills"), ("./sumiu", "sumiu")],
    ids=["pasta-que-agrupa-skills", "pasta-inexistente"],
)
def test_entry_without_skill_md_exits_4_before_writing_anything(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], entry: str, folder: str
) -> None:
    source = tmp_path / "plugin"
    (source / "skills" / "uma").mkdir(parents=True)
    (source / "skills" / "uma" / "SKILL.md").write_text("---\nname: uma\n---\n")
    manifest = source / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({"skills": ["./skills/uma", entry]}))
    project = tmp_path / "projeto"

    result = _install(capsys, "--project", str(project), "--source", str(source), "copilot")

    assert result == (
        4,
        "",
        f"pasta de skill sem SKILL.md: {source / folder} (listada em {manifest})\n",
    )
    assert not project.exists()


def test_module_mode_installs_copilot_and_devin(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "bob_quality.install_skills", "--project", str(tmp_path), "copilot", "devin"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        _installed(".github/skills", ".agents/skills"),
        "",
    )
    assert (tmp_path / ".github/skills/bob-check/SKILL.md").read_bytes() == BOB_CHECK_SKILL.read_bytes()
    assert sorted(path.name for path in (tmp_path / ".agents/skills").iterdir()) == sorted(BOB_SKILLS)


def test_script_mode_runs_from_the_clone_without_site_packages(tmp_path: Path) -> None:
    # `-S` tira o site-packages: um import do pacote bob_quality quebraria o
    # script num diretório de plugin. Sob o mutmut o arquivo é uma cópia que
    # importa o próprio mutmut de lá.
    if "MUTANT_UNDER_TEST" in os.environ:
        pytest.skip("sob o mutmut o script mutado depende do site-packages")
    script = ROOT / "src" / "bob_quality" / "install_skills.py"
    result = subprocess.run(
        [sys.executable, "-S", str(script), "--project", str(tmp_path), "agents"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert (result.returncode, result.stdout, result.stderr) == (0, _installed(".agents/skills"), "")
    assert sorted(path.name for path in (tmp_path / ".agents/skills").iterdir()) == sorted(BOB_SKILLS)


def test_symlink_at_a_current_skill_stays_and_the_install_finishes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / ".github" / "skills"
    dest.mkdir(parents=True)
    outside = tmp_path / "fora"
    bob_target = outside / "bob-check"
    bob_target.mkdir(parents=True)
    (bob_target / "KEEP").write_text("bob\n")
    (dest / "bob-check").symlink_to(bob_target, target_is_directory=True)
    harden_target = outside / "sumiu"
    (dest / "harden").symlink_to(harden_target)
    report_file = outside / "review-report"
    report_file.write_text("relatorio\n")
    (dest / "review-report").symlink_to(report_file)

    result = _install(capsys, "--project", str(tmp_path), "copilot")

    warnings = "".join(
        _kept(dest / name, "é um link simbólico") + "\n" for name in BOB_SKILLS
    )
    assert result == (0, _installed(".github/skills"), warnings)
    assert (dest / "bob-check").readlink() == bob_target
    assert (bob_target / "KEEP").read_text() == "bob\n"
    assert list(bob_target.iterdir()) == [bob_target / "KEEP"]
    assert (dest / "harden").readlink() == harden_target
    assert not harden_target.exists()
    assert (dest / "review-report").readlink() == report_file
    assert report_file.read_text() == "relatorio\n"
    assert sorted(path.name for path in dest.iterdir()) == sorted(BOB_SKILLS)


def test_unreadable_retired_notice_stays_and_the_install_finishes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / ".github" / "skills"
    locked = dest / "tdd"
    locked.mkdir(parents=True)
    (locked / "SKILL.md").write_text("antiga\n")
    notice = locked / "NOTICE"
    notice.write_text(OLD_INSTALL_NOTICE)
    notice.chmod(0)
    gone = dest / "code-review"
    gone.mkdir()
    (gone / "SKILL.md").write_text("sai\n")
    (gone / "NOTICE").write_text(OLD_INSTALL_NOTICE)
    try:
        result = _install(capsys, "--project", str(tmp_path), "copilot")
    finally:
        notice.chmod(0o644)

    denied = f"[Errno 13] Permission denied: '{notice}'"
    assert result == (0, _installed(".github/skills"), _kept(locked, denied) + "\n")
    assert (locked / "SKILL.md").read_text() == "antiga\n"
    assert notice.read_text() == OLD_INSTALL_NOTICE
    assert not gone.exists()
    for name in BOB_SKILLS:
        assert (dest / name / "SKILL.md").read_bytes() == (ROOT / "skills" / name / "SKILL.md").read_bytes()


def test_unreadable_retired_folder_stays_and_the_install_finishes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    if os.geteuid() == 0:
        pytest.skip("root ignora o chmod 000")
    dest = tmp_path / ".agents" / "skills"
    locked = dest / "ask-matt"
    locked.mkdir(parents=True)
    (locked / "SKILL.md").write_text("antiga\n")
    notice = locked / "NOTICE"
    notice.write_text(OLD_INSTALL_NOTICE)
    gone = dest / "tdd"
    gone.mkdir()
    (gone / "SKILL.md").write_text("sai\n")
    (gone / "NOTICE").write_text(OLD_INSTALL_NOTICE)
    locked.chmod(0)
    try:
        result = _install(capsys, "--project", str(tmp_path), "agents")
    finally:
        locked.chmod(0o755)

    denied = f"[Errno 13] Permission denied: '{notice}'"
    assert result == (0, _installed(".agents/skills"), _kept(locked, denied) + "\n")
    assert (locked / "SKILL.md").read_text() == "antiga\n"
    assert notice.read_text() == OLD_INSTALL_NOTICE
    assert not gone.exists()
    for name in BOB_SKILLS:
        assert (dest / name / "SKILL.md").read_bytes() == (ROOT / "skills" / name / "SKILL.md").read_bytes()
