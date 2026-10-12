"""Comentário único do relatório no PR (seam da Action, via API)."""

import os
import subprocess
import sys
from pathlib import Path

from github_api_fake import GitHubApi, serve

ROOT = Path(__file__).resolve().parents[1]
UPSERT = ROOT / ".github" / "actions" / "bob" / "upsert_comment.py"
MARKER = "<!-- bob-report -->"


def _upsert(
    report: Path,
    api_base: str,
    pr: str = "8",
    summary: Path | None = None,
    lang: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = None
    if summary is not None:
        env = {**os.environ, "GITHUB_STEP_SUMMARY": str(summary)}
    command = [
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
    ]
    if lang is not None:
        command.extend(["--lang", lang])
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        env=env,
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
    existing = {
        "id": 42,
        "body": f"{MARKER}\n\nrelatório antigo\n",
        "user": {"login": "github-actions[bot]"},
    }
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
    assert "_…report truncated to fit in the GitHub comment._" in body
    assert "linha de mutante" in body


def test_long_report_truncation_note_follows_pt_br(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("# Relatório bob\n\n" + ("linha de mutante\n" * 10000))
    api = GitHubApi()
    server, base = serve(api)
    try:
        result = _upsert(report, base, lang="pt-BR")
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    body = str(api.comments[0]["body"])
    assert "_…relatório truncado para caber no comentário do GitHub._" in body


def test_missing_report_still_posts_a_single_comment(tmp_path: Path) -> None:
    missing = tmp_path / "report.md"
    api = GitHubApi()
    server, base = serve(api)
    try:
        result = _upsert(missing, base)
    finally:
        server.shutdown()

    assert result.returncode != 0
    assert len(api.comments) == 1
    body = str(api.comments[0]["body"])
    assert MARKER in body
    assert result.stderr == f"`{missing.as_posix()}` was not generated.\n"
    assert "report.md" in body


def test_missing_report_error_follows_pt_br(tmp_path: Path) -> None:
    missing = tmp_path / "report.md"
    api = GitHubApi()
    server, base = serve(api)
    try:
        result = _upsert(missing, base, lang="pt-BR")
    finally:
        server.shutdown()

    assert result.returncode != 0
    assert result.stderr == f"`{missing.as_posix()}` não foi gerado.\n"


def test_human_comment_quoting_the_marker_is_not_overwritten(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("# Relatório bob\n\n- ❌ `crap`: falhou\n")
    api = GitHubApi()
    api.add_comment(f"{MARKER}\n\nrelatório do bot\n", login="github-actions[bot]")
    api.add_comment(f"veja {MARKER} no relatório\n", login="alice")
    server, base = serve(api)
    try:
        result = _upsert(report, base)
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    assert len(api.comments) == 2
    assert "❌ `crap`: falhou" in str(api.comments[0]["body"])
    assert "relatório do bot" not in str(api.comments[0]["body"])
    assert str(api.comments[1]["body"]) == f"veja {MARKER} no relatório\n"
    assert api.comments[1]["user"] == {"login": "alice"}


def test_a_human_marker_alone_does_not_get_replaced(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("# Relatório bob\n\n- ❌ `crap`: falhou\n")
    api = GitHubApi()
    api.add_comment(f"{MARKER}\n\nnota humana\n", login="alice")
    server, base = serve(api)
    try:
        result = _upsert(report, base)
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    assert len(api.comments) == 2
    assert str(api.comments[0]["body"]) == f"{MARKER}\n\nnota humana\n"
    assert "❌ `crap`: falhou" in str(api.comments[1]["body"])
    assert api.comments[1]["user"] == {"login": "github-actions[bot]"}


def test_forbidden_comment_goes_to_the_job_summary_and_does_not_fail(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("# Relatório bob\n\n- ✅ `crap`: passou\n")
    summary = tmp_path / "summary.md"
    api = GitHubApi()
    api.write_status = 403
    server, base = serve(api)
    try:
        result = _upsert(report, base, summary=summary)
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    assert api.comments == []
    written = summary.read_text()
    assert "# Relatório bob" in written
    assert "✅ `crap`: passou" in written


def test_comment_api_failure_other_than_forbidden_still_fails(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("# Relatório bob\n\n- ✅ `crap`: passou\n")
    api = GitHubApi()
    api.write_status = 500
    server, base = serve(api)
    try:
        result = _upsert(report, base)
    finally:
        server.shutdown()

    assert result.returncode != 0
    assert api.comments == []


def test_missing_repo_pr_or_token_is_an_english_error() -> None:
    result = subprocess.run(
        [sys.executable, str(UPSERT), "--repo", "", "--pr", "", "--token", "", "--lang", "en"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 4
    assert result.stderr == "repo, pr, and token are required\n"


def test_missing_repo_pr_or_token_follows_pt_br() -> None:
    result = subprocess.run(
        [sys.executable, str(UPSERT), "--repo", "", "--pr", "", "--token", "", "--lang", "pt-BR"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 4
    assert result.stderr == "repo, pr e token são obrigatórios\n"


def test_invalid_comment_list_is_an_english_error(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("# bob report\n")
    api = GitHubApi()
    api.comment_pages = [{"nope": True}]
    server, base = serve(api)
    try:
        result = _upsert(report, base, lang="en")
    finally:
        server.shutdown()

    assert result.returncode == 1
    assert result.stderr == "invalid comment list\n"


def test_invalid_comment_list_follows_pt_br(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("# bob report\n")
    api = GitHubApi()
    api.comment_pages = [{"nope": True}]
    server, base = serve(api)
    try:
        result = _upsert(report, base, lang="pt-BR")
    finally:
        server.shutdown()

    assert result.returncode == 1
    assert result.stderr == "lista de comentários inválida\n"


def test_empty_lang_on_the_comment_script_exits_4(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("# bob report\n")
    api = GitHubApi()
    server, base = serve(api)
    try:
        result = _upsert(report, base, lang="")
    finally:
        server.shutdown()

    assert result.returncode == 4
    assert result.stderr == 'invalid language: "" (use en or pt-BR)\n'
    assert api.comments == []
