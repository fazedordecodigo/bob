from __future__ import annotations

import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def test_current_release_is_in_the_changelog_and_docs() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    tag = f"v{project['project']['version']}"
    release_url = f"https://github.com/fazedordecodigo/bob/releases/tag/{tag}"
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## {tag}" in changelog.splitlines()
    assert f"[pre-release]({release_url})" in changelog

    for page in ("README.md", "changelog.md"):
        content = (DOCS / page).read_text(encoding="utf-8")
        assert release_url in content
        assert f"](release-checks/{tag}.md)" in content


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
