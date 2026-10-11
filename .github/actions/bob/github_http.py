"""Cliente HTTP da API do GitHub usado pelo comentário e pelo cache."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

_REDIRECTS = {301, 302, 303, 307, 308}


class GitHubStatus(Exception):
    def __init__(self, status: int, payload: bytes) -> None:
        self.status = status
        detail = payload.decode()[:300]
        super().__init__(f"GitHub API {status}: {detail}")


def raise_for_status(status: int, payload: bytes) -> None:
    if status >= 400:
        raise GitHubStatus(status, payload)


def next_link(header: str) -> str | None:
    for part in header.split(","):
        if 'rel="next"' not in part:
            continue
        start = part.find("<")
        end = part.find(">")
        if start != -1 and end != -1:
            return part[start + 1 : end]
    return None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> None:
        return None


def request(
    method: str,
    url: str,
    token: str | None,
    payload: dict[str, object] | None = None,
    hops: int = 0,
) -> tuple[int, bytes, dict[str, str]]:
    if hops > 5:
        raise RuntimeError("redirecionamento demais na API do GitHub")
    data = None if payload is None else json.dumps(payload).encode()
    opener = urllib.request.build_opener(_NoRedirect)
    http_request = urllib.request.Request(url, data=data, method=method)
    if token:
        http_request.add_header("Authorization", f"Bearer {token}")
    http_request.add_header("Accept", "application/vnd.github+json")
    http_request.add_header("X-GitHub-Api-Version", "2026-03-10")
    if data is not None:
        http_request.add_header("Content-Type", "application/json")
    try:
        with opener.open(http_request) as response:
            raw_headers = {key.lower(): value for key, value in response.headers.items()}
            return response.status, response.read(), raw_headers
    except urllib.error.HTTPError as exc:
        if exc.code in _REDIRECTS and method == "GET":
            location = exc.headers.get("Location")
            if not location:
                raise RuntimeError("redirecionamento sem Location") from exc
            return request("GET", location, None, None, hops + 1)
        body = exc.read()
        return exc.code, body, {}
