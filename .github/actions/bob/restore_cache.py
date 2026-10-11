"""Restaura `.bob/mutation-cache.json` do artefato mais recente de outra execução."""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from github_links import next_link

CACHE_NAME = "mutation-cache.json"
ARTIFACT_NAME = "bob-mutation-cache"


def select_artifact(artifacts: list[dict[str, object]], current_run_id: str) -> dict[str, object] | None:
    candidates: list[tuple[datetime, dict[str, object]]] = []
    for artifact in artifacts:
        if artifact.get("expired") is True:
            continue
        if str(artifact.get("name") or "") != ARTIFACT_NAME:
            continue
        run = artifact.get("workflow_run")
        run_id = ""
        if isinstance(run, dict):
            run_id = str(run.get("id") or "")
        if run_id == str(current_run_id):
            continue
        created = _created_at(artifact)
        if created is None:
            continue
        candidates.append((created, artifact))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


def extract_cache(payload: bytes, dest: Path) -> bool:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        member = _cache_member(archive)
        if member is None:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(archive.read(member))
    return True


def restore_cache(
    *,
    repo: str,
    api_base: str,
    token: str,
    run_id: str,
    dest: Path,
) -> bool:
    artifacts = _list_artifacts(api_base, repo, token)
    chosen = select_artifact(artifacts, run_id)
    if chosen is None:
        return False
    payload = _download_zip(api_base, repo, token, int(chosen["id"]))
    return extract_cache(payload, dest)


def _created_at(artifact: dict[str, object]) -> datetime | None:
    raw = artifact.get("created_at")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _cache_member(archive: zipfile.ZipFile) -> zipfile.ZipInfo | None:
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts:
            continue
        if path.name == CACHE_NAME:
            return info
    return None


def _list_artifacts(api_base: str, repo: str, token: str) -> list[dict[str, object]]:
    url: str | None = (
        f"{api_base}/repos/{repo}/actions/artifacts?name={ARTIFACT_NAME}&per_page=100"
    )
    found: list[dict[str, object]] = []
    while url is not None:
        status, payload, headers = _open(url, token)
        if status >= 400:
            raise RuntimeError(f"GitHub API {status}: {payload.decode()[:300]}")
        body = json.loads(payload.decode())
        page = body.get("artifacts") if isinstance(body, dict) else None
        if not isinstance(page, list):
            raise RuntimeError("lista de artefatos inválida")
        found.extend(page)
        url = next_link(headers.get("link", ""))
    return found


def _download_zip(api_base: str, repo: str, token: str, artifact_id: int) -> bytes:
    url = f"{api_base}/repos/{repo}/actions/artifacts/{artifact_id}/zip"
    status, payload, _headers = _open(url, token)
    if status >= 400:
        raise RuntimeError(f"GitHub API {status} ao baixar o cache")
    return payload


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


def _open(url: str, token: str | None, hops: int = 0) -> tuple[int, bytes, dict[str, str]]:
    if hops > 5:
        raise RuntimeError("redirecionamento demais ao baixar o cache")
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, method="GET")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2026-03-10")
    try:
        with opener.open(request) as response:
            raw_headers = {key.lower(): value for key, value in response.headers.items()}
            return response.status, response.read(), raw_headers
    except urllib.error.HTTPError as exc:
        if exc.code in {301, 302, 303, 307, 308}:
            location = exc.headers.get("Location")
            if not location:
                raise RuntimeError("redirecionamento sem Location") from exc
            return _open(location, None, hops + 1)
        body = exc.read()
        return exc.code, body, {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Restaura o cache de mutação do bob")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--api-base", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", ""))
    parser.add_argument("--dest", default=".bob/mutation-cache.json")
    args = parser.parse_args(argv)
    if not args.repo or not args.token:
        print("repo e token são obrigatórios", file=sys.stderr)
        return 4
    try:
        restore_cache(
            repo=args.repo,
            api_base=args.api_base.rstrip("/"),
            token=args.token,
            run_id=str(args.run_id),
            dest=Path(args.dest),
        )
    except (
        OSError,
        RuntimeError,
        urllib.error.URLError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
        ValueError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
