"""Restaura o cache de mutação do artefato mais recente de outra execução.

O zip traz `.bob/mutation-cache.json` e, quando existe, `.bob/stryker-incremental.json`.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.error
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from github_http import GitHubStatus, next_link, raise_for_status, request

CACHE_NAME = "mutation-cache.json"
INCREMENTAL_NAME = "stryker-incremental.json"
ARTIFACT_NAME = "bob-mutation-cache"


def select_artifact(
    artifacts: list[dict[str, object]],
    current_run_id: str,
    base_branch: str,
    head_branch: str,
) -> dict[str, object] | None:
    allowed = {branch for branch in (base_branch, head_branch) if branch}
    candidates: list[tuple[datetime, dict[str, object]]] = []
    for artifact in artifacts:
        if artifact.get("expired") is True:
            continue
        if str(artifact.get("name") or "") != ARTIFACT_NAME:
            continue
        run = artifact.get("workflow_run")
        if not isinstance(run, dict):
            continue
        if str(run.get("id") or "") == str(current_run_id):
            continue
        if not _same_repository(run):
            continue
        if str(run.get("head_branch") or "") not in allowed:
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
        wrote_cache = _write_named(archive, CACHE_NAME, dest)
        wrote_incremental = _write_named(
            archive, INCREMENTAL_NAME, dest.parent / INCREMENTAL_NAME
        )
    return wrote_cache or wrote_incremental


def _write_named(archive: zipfile.ZipFile, name: str, dest: Path) -> bool:
    member = _named_member(archive, name)
    if member is None:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(archive.read(member))
    return True


def _same_repository(run: dict[str, object]) -> bool:
    repository_id = run.get("repository_id")
    head_repository_id = run.get("head_repository_id")
    if repository_id is None or head_repository_id is None:
        return False
    return str(repository_id) == str(head_repository_id)


def restore_cache(
    *,
    repo: str,
    api_base: str,
    token: str,
    run_id: str,
    dest: Path,
    base_branch: str,
    head_branch: str,
) -> bool:
    artifacts = _list_artifacts(api_base, repo, token)
    chosen = select_artifact(artifacts, run_id, base_branch, head_branch)
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


def _named_member(archive: zipfile.ZipFile, name: str) -> zipfile.ZipInfo | None:
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts:
            continue
        if path.name == name:
            return info
    return None


def _list_artifacts(api_base: str, repo: str, token: str) -> list[dict[str, object]]:
    url: str | None = (
        f"{api_base}/repos/{repo}/actions/artifacts?name={ARTIFACT_NAME}&per_page=100"
    )
    found: list[dict[str, object]] = []
    while url is not None:
        status, payload, headers = request("GET", url, token)
        raise_for_status(status, payload)
        body = json.loads(payload.decode())
        page = body.get("artifacts") if isinstance(body, dict) else None
        if not isinstance(page, list):
            raise RuntimeError("lista de artefatos inválida")
        found.extend(page)
        url = next_link(headers.get("link", ""))
    return found


def _download_zip(api_base: str, repo: str, token: str, artifact_id: int) -> bytes:
    url = f"{api_base}/repos/{repo}/actions/artifacts/{artifact_id}/zip"
    status, payload, _headers = request("GET", url, token)
    raise_for_status(status, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Restaura o cache de mutação do bob")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--api-base", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", ""))
    parser.add_argument("--base-branch", default=os.environ.get("GITHUB_BASE_REF", ""))
    parser.add_argument("--head-branch", default=os.environ.get("GITHUB_HEAD_REF", ""))
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
            base_branch=str(args.base_branch),
            head_branch=str(args.head_branch),
        )
    except (
        OSError,
        RuntimeError,
        urllib.error.URLError,
        GitHubStatus,
        json.JSONDecodeError,
        zipfile.BadZipFile,
        ValueError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
