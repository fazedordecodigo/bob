"""Cria ou atualiza um único comentário de PR com `.bob/report.md`."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
from pathlib import Path

from bob_quality.config import ConfigError, parse_language
from bob_quality.messages import DEFAULT_LANGUAGE, Language, reason, render, t
from github_http import GitHubStatus, next_link, raise_for_status, request

MARKER = "<!-- bob-report -->"
ACTIONS_BOT = "github-actions[bot]"
GITHUB_BODY_LIMIT = 65536


def build_body(report_text: str, lang: Language = DEFAULT_LANGUAGE) -> str:
    note = t(lang, "action.truncated")
    body = f"{MARKER}\n\n{report_text.strip()}\n"
    if len(body) <= GITHUB_BODY_LIMIT:
        return body
    keep = GITHUB_BODY_LIMIT - len(MARKER) - len(note) - 2
    trimmed = report_text.strip()[:keep].rstrip()
    return f"{MARKER}\n\n{trimmed}{note}"


def comment_to_update(comments: list[dict[str, object]]) -> int | None:
    marked = [
        item
        for item in comments
        if _is_actions_bot(item) and MARKER in str(item.get("body") or "")
    ]
    if not marked:
        return None
    return int(marked[-1]["id"])


def _is_actions_bot(comment: dict[str, object]) -> bool:
    user = comment.get("user")
    if not isinstance(user, dict):
        return False
    return user.get("login") == ACTIONS_BOT


def upsert_comment(
    *,
    report_text: str,
    repo: str,
    pr: str,
    api_base: str,
    token: str,
    lang: Language = DEFAULT_LANGUAGE,
) -> None:
    comments = _list_comments(api_base, repo, pr, token, lang)
    body = build_body(report_text, lang)
    target = comment_to_update(comments)
    if target is None:
        status, payload, _headers = request(
            "POST",
            f"{api_base}/repos/{repo}/issues/{pr}/comments",
            token,
            {"body": body},
        )
        raise_for_status(status, payload)
        return
    status, payload, _headers = request(
        "PATCH",
        f"{api_base}/repos/{repo}/issues/comments/{target}",
        token,
        {"body": body},
    )
    raise_for_status(status, payload)


def _list_comments(
    api_base: str, repo: str, pr: str, token: str, lang: Language
) -> list[dict[str, object]]:
    url: str | None = f"{api_base}/repos/{repo}/issues/{pr}/comments?per_page=100"
    collected: list[dict[str, object]] = []
    while url is not None:
        status, payload, headers = request("GET", url, token, None)
        raise_for_status(status, payload)
        page = json.loads(payload.decode())
        if not isinstance(page, list):
            raise RuntimeError(t(lang, "action.comments_invalid"))
        collected.extend(page)
        url = next_link(headers.get("link", ""))
    return collected


def _write_step_summary(text: str) -> None:
    raw = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if not raw:
        return
    path = Path(raw)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    body = text if text.endswith("\n") else f"{text}\n"
    path.write_text(existing + body, encoding="utf-8")


def _action_language(flag: str | None) -> Language:
    if flag is not None:
        return parse_language(flag)
    action = os.environ.get("BOB_LANGUAGE")
    if action:
        return parse_language(action)
    env = os.environ.get("BOB_LANG")
    if env is not None:
        return parse_language(env)
    return DEFAULT_LANGUAGE


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Comenta o relatório do bob no PR")
    parser.add_argument("--report", default=".bob/report.md")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--pr", default=os.environ.get("BOB_PR_NUMBER", ""))
    parser.add_argument("--api-base", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--lang", default=None)
    args = parser.parse_args(argv)
    try:
        lang = _action_language(args.lang)
    except ConfigError as exc:
        print(render(reason(exc), DEFAULT_LANGUAGE), file=sys.stderr)
        return 4
    if not args.repo or not args.pr or not args.token:
        print(t(lang, "action.required"), file=sys.stderr)
        return 4
    report_path = Path(args.report)
    report_missing = not report_path.is_file()
    if report_missing:
        text = t(lang, "action.report_missing", path=report_path.as_posix())
    else:
        text = report_path.read_text(encoding="utf-8")
    try:
        upsert_comment(
            report_text=text,
            repo=args.repo,
            pr=args.pr,
            api_base=args.api_base.rstrip("/"),
            token=args.token,
            lang=lang,
        )
    except GitHubStatus as exc:
        if exc.status == 403:
            _write_step_summary(text)
            return 0
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, RuntimeError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if report_missing:
        print(text, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
