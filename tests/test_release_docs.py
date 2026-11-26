from __future__ import annotations

import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PT_DOCS = ROOT / "website/i18n/pt-BR/docusaurus-plugin-content-docs/current"


def test_current_release_is_in_the_changelog_and_docs() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    tag = f"v{project['project']['version']}"
    release_url = f"https://github.com/fazedordecodigo/bob/releases/tag/{tag}"
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    headings = re.findall(r"^## (.+)$", changelog, re.MULTILINE)
    assert headings[0] == "Unreleased"
    assert tag in headings[1:]

    for directory in (DOCS, PT_DOCS):
        index = (directory / "README.md").read_text(encoding="utf-8")
        changelog_page = (directory / "changelog.md").read_text(encoding="utf-8")
        for content in (index, changelog_page):
            assert release_url in content
            assert f"](release-checks/{tag}.md)" in content
        headings = re.findall(r"^## (.+)$", changelog_page, re.MULTILINE)
        assert headings[0] == "Unreleased"
        assert tag in headings[1:]


def test_v0_1_0_stable_entry_contains_only_its_release_notes() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    _, heading, remaining = changelog.partition("\n## v0.1.0\n")
    assert heading
    release_entry = remaining.split("\n## ", 1)[0]
    release_url = "https://github.com/fazedordecodigo/bob/releases/tag/v0.1.0"
    assert f"[stable release]({release_url})" in release_entry
    assert "The `bob setup` help names everything the command installs" in release_entry


def test_post_tag_notes_stay_unreleased() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    _, unreleased_heading, entries = changelog.partition("\n## Unreleased\n")
    assert unreleased_heading
    unreleased_entry = entries.split("\n## ", 1)[0]
    _, release_heading, entries = entries.partition("\n## v0.1.0\n")
    assert release_heading
    release_entry = entries.split("\n## ", 1)[0]

    for note in (
        "`bob doctor` checks the Semgrep version",
        "O `bob doctor` verifica a versão do Semgrep",
        "`bob mutate --since-last-run` limits the Python run",
        "`bob mutate --since-last-run` limita a corrida Python",
    ):
        assert note in unreleased_entry
        assert note not in release_entry


def _markdown_targets(page: Path) -> set[Path]:
    links = re.findall(r"\]\(([^:#)]+\.md)(?:#[^)]*)?\)", page.read_text(encoding="utf-8"))
    return {(page.parent / link).resolve() for link in links}


def test_docs_index_covers_the_markdown_pages() -> None:
    index = DOCS / "README.md"
    adr_index = DOCS / "architecture" / "adrs.md"
    index_targets = _markdown_targets(index)
    assert adr_index in index_targets
    targets = index_targets | _markdown_targets(adr_index)
    pages = set(DOCS.rglob("*.md")) - {index}
    assert pages <= targets, "Missing links from the docs index or its ADR index"
    assert targets <= pages | {index}, "Broken links in the docs index or its ADR index"


def test_aidlc_state_records_the_completed_docs_sync() -> None:
    state = (ROOT / "aidlc-docs" / "aidlc-state.md").read_text(encoding="utf-8")
    assert "A sincronização de `aidlc-docs/` foi concluída" in state
    assert "aguardando PR mecânico de sincronização" not in state
    assert "Próximo: PR mecânico de sincronização" not in state
