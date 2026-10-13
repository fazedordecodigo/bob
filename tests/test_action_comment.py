"""Comentário único do relatório no PR (seam da Action, via API)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from bob_quality.messages import Language
from github_api_fake import GitHubApi, serve
from helpers import BAD_LANGUAGE_YAML, LANGUAGE_CASES, LanguageCase

ROOT = Path(__file__).resolve().parents[1]
UPSERT = ROOT / ".github" / "actions" / "bob" / "upsert_comment.py"
MARKER = "<!-- bob-report -->"
REQUIRED: dict[Language, str] = {
    "en": "repo, pr, and token are required\n",
    "pt-BR": "repo, pr e token são obrigatórios\n",
}
TRUNCATED_PT = "\n\n_…relatório truncado para caber no comentário do GitHub._\n"


def _lang_env(
    *, input_: str | None = None, bob_lang: str | None = None
) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"BOB_LANG", "BOB_LANGUAGE"}
    }
    if input_ is not None:
        env["BOB_LANGUAGE"] = input_
    if bob_lang is not None:
        env["BOB_LANG"] = bob_lang
    return env


def _upsert(
    report: Path,
    api_base: str,
    *,
    cwd: Path,
    pr: str = "8",
    lang: str | None = None,
    env: dict[str, str] | None = None,
    summary: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    run_env = _lang_env() if env is None else dict(env)
    if summary is not None:
        run_env["GITHUB_STEP_SUMMARY"] = str(summary)
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
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=run_env,
    )


def _required(
    cwd: Path, *args: str, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(UPSERT),
            "--repo",
            "",
            "--pr",
            "",
            "--token",
            "",
            *args,
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _required_on_api(
    cwd: Path, *args: str, env: dict[str, str]
) -> tuple[subprocess.CompletedProcess[str], GitHubApi]:
    api = GitHubApi()
    server, base = serve(api)
    try:
        result = _required(cwd, "--api-base", base, *args, env=env)
    finally:
        server.shutdown()
    return result, api


def test_second_push_updates_the_same_pull_request_comment(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("# Relatório bob\n\n- ✅ `crap`: passou\n")
    api = GitHubApi()
    server, base = serve(api)
    try:
        created = _upsert(report, base, cwd=tmp_path)
        report.write_text("# Relatório bob\n\n- ❌ `crap`: falhou\n")
        updated = _upsert(report, base, cwd=tmp_path)
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
        result = _upsert(report, base, cwd=tmp_path)
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
        result = _upsert(report, base, cwd=tmp_path)
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
        result = _upsert(report, base, cwd=tmp_path, lang="pt-BR")
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
        result = _upsert(missing, base, cwd=tmp_path)
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
        result = _upsert(missing, base, cwd=tmp_path, lang="pt-BR")
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
        result = _upsert(report, base, cwd=tmp_path)
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
        result = _upsert(report, base, cwd=tmp_path)
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
        result = _upsert(report, base, cwd=tmp_path, summary=summary)
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
        result = _upsert(report, base, cwd=tmp_path)
    finally:
        server.shutdown()

    assert result.returncode != 0
    assert api.comments == []


def test_missing_repo_pr_or_token_is_an_english_error(tmp_path: Path) -> None:
    result = _required(tmp_path, "--lang", "en", env=_lang_env())

    assert result.returncode == 4
    assert result.stderr == "repo, pr, and token are required\n"


def test_missing_repo_pr_or_token_follows_pt_br(tmp_path: Path) -> None:
    result = _required(tmp_path, "--lang", "pt-BR", env=_lang_env())

    assert result.returncode == 4
    assert result.stderr == "repo, pr e token são obrigatórios\n"


def test_invalid_comment_list_is_an_english_error(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("# bob report\n")
    api = GitHubApi()
    api.comment_pages = [{"nope": True}]
    server, base = serve(api)
    try:
        result = _upsert(report, base, cwd=tmp_path, lang="en")
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
        result = _upsert(report, base, cwd=tmp_path, lang="pt-BR")
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
        result = _upsert(report, base, cwd=tmp_path, lang="")
    finally:
        server.shutdown()

    assert result.returncode == 4
    assert result.stderr == 'invalid language: "" (use en or pt-BR)\n'
    assert api.comments == []


@pytest.mark.parametrize("case", LANGUAGE_CASES)
def test_comment_errors_follow_input_then_bob_lang_then_bob_yaml_then_en(
    tmp_path: Path, case: LanguageCase
) -> None:
    if case.configured is not None:
        (tmp_path / "bob.yaml").write_text(f"language: {case.configured}\n")

    result, api = _required_on_api(
        tmp_path, env=_lang_env(input_=case.flag, bob_lang=case.env)
    )

    assert result.returncode == 4
    assert result.stderr == REQUIRED[case.expected]
    assert api.comments == []


def test_yaml_pt_br_translates_the_truncation_note_and_keeps_report_bytes(
    tmp_path: Path,
) -> None:
    (tmp_path / "bob.yaml").write_text("language: pt-BR\n")
    kept = "CRAP >= 10.0: messy@src/app/risky.py:1\n"
    report = tmp_path / "report.md"
    report.write_text(kept + ("linha de mutante\n" * 10000))
    api = GitHubApi()
    server, base = serve(api)
    try:
        result = _upsert(report, base, cwd=tmp_path)
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    body = str(api.comments[0]["body"])
    assert kept in body
    assert TRUNCATED_PT in body
    assert "_…report truncated to fit in the GitHub comment._" not in body


def test_yaml_pt_br_translates_the_missing_report_error(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("language: pt-BR\n")
    missing = tmp_path / "report.md"
    api = GitHubApi()
    server, base = serve(api)
    try:
        result = _upsert(missing, base, cwd=tmp_path)
    finally:
        server.shutdown()

    text = f"`{missing.as_posix()}` não foi gerado."
    assert result.returncode == 1
    assert result.stderr == f"{text}\n"
    assert len(api.comments) == 1
    assert text in str(api.comments[0]["body"])


def test_yaml_pt_br_translates_an_invalid_comment_list(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("language: pt-BR\n")
    report = tmp_path / "report.md"
    report.write_text("# bob report\n")
    api = GitHubApi()
    api.comment_pages = [{"nope": True}]
    server, base = serve(api)
    try:
        result = _upsert(report, base, cwd=tmp_path)
    finally:
        server.shutdown()

    assert result.returncode == 1
    assert result.stderr == "lista de comentários inválida\n"
    assert api.comments == []


@pytest.mark.parametrize(
    ("args", "input_", "stderr"),
    [
        (("--lang", "en"), None, "repo, pr, and token are required\n"),
        ((), "en", "repo, pr, and token are required\n"),
        (("--lang", "en"), "pt-BR", "repo, pr, and token are required\n"),
    ],
)
def test_lang_and_action_input_beat_bob_yaml(
    tmp_path: Path, args: tuple[str, ...], input_: str | None, stderr: str
) -> None:
    (tmp_path / "bob.yaml").write_text("language: pt-BR\n")

    result, api = _required_on_api(tmp_path, *args, env=_lang_env(input_=input_))

    assert result.returncode == 4
    assert result.stderr == stderr
    assert api.comments == []


def test_empty_action_input_lets_bob_yaml_win(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("language: pt-BR\n")

    result, api = _required_on_api(tmp_path, env=_lang_env(input_=""))

    assert result.returncode == 4
    assert result.stderr == "repo, pr e token são obrigatórios\n"
    assert api.comments == []


def test_empty_bob_lang_exits_4(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("language: pt-BR\n")

    result, api = _required_on_api(tmp_path, env=_lang_env(bob_lang=""))

    assert result.returncode == 4
    assert result.stderr == 'invalid language: "" (use en or pt-BR)\n'
    assert api.comments == []


def test_invalid_action_input_fails_before_a_bad_yaml_language(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("language: pt-br\n")

    result, api = _required_on_api(tmp_path, env=_lang_env(input_="fr"))

    assert result.returncode == 4
    assert result.stderr == "invalid language: fr (use en or pt-BR)\n"
    assert api.comments == []


@pytest.mark.parametrize(("text", "stderr"), BAD_LANGUAGE_YAML)
@pytest.mark.parametrize("lang", [None, "en"])
def test_bad_yaml_posts_nothing(
    tmp_path: Path, text: str, stderr: str, lang: str | None
) -> None:
    (tmp_path / "bob.yaml").write_text(text)
    report = tmp_path / "report.md"
    report.write_text("# bob report\n\nkept bytes\n")
    api = GitHubApi()
    server, base = serve(api)
    try:
        result = _upsert(report, base, cwd=tmp_path, lang=lang)
    finally:
        server.shutdown()

    assert result.returncode == 4
    assert result.stderr == stderr
    assert result.stdout == ""
    assert api.comments == []


def test_bad_duplication_does_not_block_the_yaml_language(tmp_path: Path) -> None:
    (tmp_path / "bob.yaml").write_text("language: pt-BR\nduplication: [1]\n")

    result, api = _required_on_api(tmp_path, env=_lang_env())

    assert result.returncode == 4
    assert result.stderr == "repo, pr e token são obrigatórios\n"
    assert api.comments == []
