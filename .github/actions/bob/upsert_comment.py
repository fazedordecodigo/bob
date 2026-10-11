"""Cria ou atualiza um único comentário de PR com `.bob/report.md`."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from github_links import next_link

MARKER = "<!-- bob-report -->"
GITHUB_BODY_LIMIT = 65536
_TRUNCATION_NOTE = "\n\n_…relatório truncado para caber no comentário do GitHub._\n"


def build_body(report_text: str) -> str:
    body = f"{MARKER}\n\n{report_text.strip()}\n"
    if len(body) <= GITHUB_BODY_LIMIT:
        return body
    keep = GITHUB_BODY_LIMIT - len(MARKER) - len(_TRUNCATION_NOTE) - 2
    trimmed = report_text.strip()[:keep].rstrip()
    return f"{MARKER}\n\n{trimmed}{_TRUNCATION_NOTE}"


def comment_to_update(comments: list[dict[str, object]]) -> int | None:
    marked = [item for item in comments if MARKER in str(item.get("body") or "")]
    if not marked:
        return None
    return int(marked[-1]["id"])


def upsert_comment(
    *,
    report_text: str,
    repo: str,
    pr: str,
    api_base: str,
    token: str,
) -> None:
    comments = _list_comments(api_base, repo, pr, token)
    body = build_body(report_text)
    target = comment_to_update(comments)
    if target is None:
        status, payload, _headers = _request(
            "POST",
            f"{api_base}/repos/{repo}/issues/{pr}/comments",
            token,
            {"body": body},
        )
        _raise_for_status(status, payload)
        return
    status, payload, _headers = _request(
        "PATCH",
        f"{api_base}/repos/{repo}/issues/comments/{target}",
        token,
        {"body": body},
    )
    _raise_for_status(status, payload)


def _list_comments(api_base: str, repo: str, pr: str, token: str) -> list[dict[str, object]]:
    url: str | None = f"{api_base}/repos/{repo}/issues/{pr}/comments?per_page=100"
    collected: list[dict[str, object]] = []
    while url is not None:
        status, payload, headers = _request("GET", url, token, None)
        _raise_for_status(status, payload)
        page = json.loads(payload.decode())
        if not isinstance(page, list):
            raise RuntimeError("lista de comentários inválida")
        collected.extend(page)
        url = next_link(headers.get("link", ""))
    return collected


def _raise_for_status(status: int, payload: bytes) -> None:
    if status >= 400:
        raise RuntimeError(f"GitHub API {status}: {payload.decode()[:300]}")


def _request(
    method: str,
    url: str,
    token: str,
    payload: dict[str, object] | None,
) -> tuple[int, bytes, dict[str, str]]:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2026-03-10")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request) as response:
            raw_headers = {key.lower(): value for key, value in response.headers.items()}
            return response.status, response.read(), raw_headers
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Comenta o relatório do bob no PR")
    parser.add_argument("--report", default=".bob/report.md")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--pr", default=os.environ.get("BOB_PR_NUMBER", ""))
    parser.add_argument("--api-base", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    args = parser.parse_args(argv)
    if not args.repo or not args.pr or not args.token:
        print("repo, pr e token são obrigatórios", file=sys.stderr)
        return 4
    report_path = Path(args.report)
    report_missing = not report_path.is_file()
    if report_missing:
        text = f"`{report_path.as_posix()}` não foi gerado."
    else:
        text = report_path.read_text(encoding="utf-8")
    try:
        upsert_comment(
            report_text=text,
            repo=args.repo,
            pr=args.pr,
            api_base=args.api_base.rstrip("/"),
            token=args.token,
        )
    except (OSError, RuntimeError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if report_missing:
        print(text, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
