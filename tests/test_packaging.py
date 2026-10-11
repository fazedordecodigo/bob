"""Empacotamento (issue #10, docs/SPEC.md, seção Empacotamento).

Seams:

1. Manifestos lidos pelos agentes: `.claude-plugin/plugin.json` (Claude Code,
   Copilot e Devin), `.claude-plugin/marketplace.json` e `.cursor-plugin/plugin.json`.
2. Instalador `bob_quality.install_skills`: recebe argv e devolve exit code,
   stdout, stderr e a árvore de skills no projeto.

Os nomes esperados são literais: as três skills do bob mais a seleção do
plugin upstream do Pocock (engineering/ e productivity/), sem misc/ nem in-progress/.
"""

from __future__ import annotations

import json
import os
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
TDD_SKILL = ROOT / "skills" / "vendor" / "mattpocock" / "engineering" / "tdd" / "SKILL.md"
CLAUDE_PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
CLAUDE_MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
CURSOR_PLUGIN = ROOT / ".cursor-plugin" / "plugin.json"

EXPECTED_SKILLS = [
    "ask-matt",
    "bob-check",
    "code-review",
    "codebase-design",
    "diagnosing-bugs",
    "domain-modeling",
    "grill-me",
    "grill-with-docs",
    "grilling",
    "handoff",
    "harden",
    "implement",
    "implement-spec",
    "improve-codebase-architecture",
    "pr",
    "prototype",
    "research",
    "retro",
    "review-report",
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
]

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
    """Mesma leitura dos agentes: cada pasta listada, um nível, `<nome>/SKILL.md`."""
    return [
        child
        for entry in entries
        for child in (ROOT / entry).iterdir()
        if (child / "SKILL.md").is_file()
    ]


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
        assert "Matt Pocock" in data["description"], path


def test_marketplace_lists_only_bob_from_the_plugin_root() -> None:
    marketplace = _json(CLAUDE_MARKETPLACE)
    assert marketplace["owner"] == {"name": "Emerson Delatorre"}
    assert [plugin["name"] for plugin in marketplace["plugins"]] == ["bob"]
    entry = marketplace["plugins"][0]
    assert entry["source"] == "./"
    assert "Matt Pocock" in entry["description"]


def test_cursor_manifest_uses_only_schema_keys_and_the_claude_skill_dirs() -> None:
    cursor = _json(CURSOR_PLUGIN)
    assert set(cursor) <= CURSOR_ALLOWED_KEYS
    assert cursor["displayName"] == "bob"
    assert cursor["skills"] == _json(CLAUDE_PLUGIN)["skills"]


def test_manifest_skill_dirs_are_relative_and_exist() -> None:
    for entry in _json(CLAUDE_PLUGIN)["skills"]:
        assert entry.startswith("./"), entry
        assert ".." not in Path(entry).parts, entry
        assert (ROOT / entry).is_dir(), entry


def test_manifest_reaches_exactly_the_expected_skills() -> None:
    folders = _skill_folders(_json(CLAUDE_PLUGIN)["skills"])
    assert sorted(folder.name for folder in folders) == EXPECTED_SKILLS


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


def test_copilot_installs_every_manifest_skill_flat_into_github_skills(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = _install(capsys, "--project", str(tmp_path), "copilot")

    dest = tmp_path / ".github" / "skills"
    assert result == (0, "30 skills em .github/skills\n", "")
    assert sorted(path.name for path in dest.iterdir()) == EXPECTED_SKILLS
    assert (dest / "tdd" / "SKILL.md").read_bytes() == TDD_SKILL.read_bytes()
    assert (dest / "tdd" / "agents" / "openai.yaml").is_file()


def test_targets_that_share_a_folder_write_it_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = _install(capsys, "--project", str(tmp_path), "devin", "agents", "copilot")

    assert result == (0, "30 skills em .agents/skills\n30 skills em .github/skills\n", "")
    installed = sorted(path.name for path in (tmp_path / ".agents" / "skills").iterdir())
    assert installed == EXPECTED_SKILLS


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
    (dest / "tdd").mkdir()
    (dest / "tdd" / "stale.md").write_text("de uma versão antiga\n")

    first = _install(capsys, "--project", str(tmp_path), "copilot")
    after_first = _files(dest)
    second = _install(capsys, "--project", str(tmp_path), "copilot")

    assert first == second == (0, "30 skills em .github/skills\n", "")
    assert (dest / "mine" / "SKILL.md").read_text() == "minha skill\n"
    assert not (dest / "tdd" / "stale.md").exists()
    assert (dest / "tdd" / "SKILL.md").read_bytes() == TDD_SKILL.read_bytes()
    assert _files(dest) == after_first


def test_project_defaults_to_the_current_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = _install(capsys, "agents")

    assert result == (0, "30 skills em .agents/skills\n", "")
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
    "content",
    ["{", '{"skills": "./skills/"}', '{"skills": [1]}'],
    ids=["json-quebrado", "skills-texto", "pasta-nao-texto"],
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
        f"manifesto inválido (skills deve ser uma lista de pastas): {manifest}."
        " Passe --source com a raiz do plugin bob.\n",
    )
    assert not (tmp_path / ".github").exists()


def test_missing_skill_folder_exits_4_before_writing_anything(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "plugin"
    (source / "skills" / "uma").mkdir(parents=True)
    (source / "skills" / "uma" / "SKILL.md").write_text("---\nname: uma\n---\n")
    manifest = source / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({"skills": ["./skills/", "./sumiu/"]}))
    project = tmp_path / "projeto"

    result = _install(capsys, "--project", str(project), "--source", str(source), "copilot")

    assert result == (
        4,
        "",
        f"pasta de skills não encontrada: {source / 'sumiu'} (listada em {manifest})."
        " Passe --source com a raiz do plugin bob.\n",
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
        "30 skills em .github/skills\n30 skills em .agents/skills\n",
        "",
    )
    assert (tmp_path / ".github/skills/tdd/SKILL.md").read_bytes() == TDD_SKILL.read_bytes()
    assert sorted(path.name for path in (tmp_path / ".agents/skills").iterdir()) == EXPECTED_SKILLS


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

    assert (result.returncode, result.stdout, result.stderr) == (0, "30 skills em .agents/skills\n", "")
    assert sorted(path.name for path in (tmp_path / ".agents/skills").iterdir()) == EXPECTED_SKILLS
