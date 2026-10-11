"""Comentário único do relatório no PR (seam da Action, via API)."""

import subprocess
import sys
from pathlib import Path

from github_api_fake import GitHubApi, serve

ROOT = Path(__file__).resolve().parents[1]
UPSERT = ROOT / ".github" / "actions" / "bob" / "upsert_comment.py"
MARKER = "<!-- bob-report -->"


def _upsert(report: Path, api_base: str, pr: str = "8") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(UPSERT),
            "--report",
            str(report),
            "--repo",
            "fazedordecodigo/bob",
            "--pr",
            pr,
            "--api-base",
            api_base,
            "--token",
            "test-token",
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_second_push_updates_the_same_pull_request_comment(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("# Relatório bob\n\n- ✅ `crap`: passou\n")
    api = GitHubApi()
    server, base = serve(api)
    try:
        created = _upsert(report, base)
        report.write_text("# Relatório bob\n\n- ❌ `crap`: falhou\n")
        updated = _upsert(report, base)
    finally:
        server.shutdown()

    assert created.returncode == 0, created.stderr
    assert updated.returncode == 0, updated.stderr
    assert len(api.comments) == 1
    body = str(api.comments[0]["body"])
    assert MARKER in body
    assert "❌ `crap`: falhou" in body
    assert "✅ `crap`: passou" not in body


def test_updates_the_bob_comment_when_it_is_not_on_the_first_page(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("# Relatório bob\n\n- ⏭️ `mutate`: não executado\n")
    api = GitHubApi()
    existing = {"id": 42, "body": f"{MARKER}\n\nrelatório antigo\n"}
    api.comment_pages = [[{"id": 1, "body": "comentário de outra ferramenta"}], [existing]]
    api.comments.append(existing)
    server, base = serve(api)
    try:
        result = _upsert(report, base)
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    assert len(api.comments) == 1
    assert "não executado" in str(api.comments[0]["body"])


def test_long_report_still_fits_in_one_github_comment(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("# Relatório bob\n\n" + ("linha de mutante\n" * 10000))
    api = GitHubApi()
    server, base = serve(api)
    try:
        result = _upsert(report, base)
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    assert len(api.comments) == 1
    body = str(api.comments[0]["body"])
    assert len(body) <= 65536
    assert body.startswith(MARKER)
    assert "truncado" in body
    assert "linha de mutante" in body


def test_missing_report_still_posts_a_single_comment(tmp_path: Path) -> None:
    missing = tmp_path / "report.md"
    api = GitHubApi()
    server, base = serve(api)
    try:
        result = _upsert(missing, base)
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    assert len(api.comments) == 1
    body = str(api.comments[0]["body"])
    assert MARKER in body
    assert "report.md" in body
