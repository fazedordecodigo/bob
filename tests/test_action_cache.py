"""Cache `.bob/mutation-cache.json` da execução anterior, via artefato."""

import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from github_api_fake import GitHubApi, serve

ROOT = Path(__file__).resolve().parents[1]
RESTORE = ROOT / ".github" / "actions" / "bob" / "restore_cache.py"


def _zip_bytes(*members: tuple[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in members:
            archive.writestr(name, content)
    return buffer.getvalue()


def _artifact(
    artifact_id: int,
    run_id: int,
    created_at: str,
    expired: bool = False,
    head_branch: str | None = None,
    repository_id: int | None = None,
    head_repository_id: int | None = None,
) -> dict[str, object]:
    run: dict[str, object] = {"id": run_id}
    if head_branch is not None:
        run["head_branch"] = head_branch
    if repository_id is not None:
        run["repository_id"] = repository_id
    if head_repository_id is not None:
        run["head_repository_id"] = head_repository_id
    return {
        "id": artifact_id,
        "name": "bob-mutation-cache",
        "expired": expired,
        "created_at": created_at,
        "workflow_run": run,
    }


def _restore(
    dest: Path,
    api_base: str,
    run_id: str,
    base_branch: str | None = None,
    head_branch: str | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(RESTORE),
        "--repo",
        "fazedordecodigo/bob",
        "--api-base",
        api_base,
        "--token",
        "test-token",
        "--run-id",
        run_id,
        "--dest",
        str(dest),
    ]
    if base_branch is not None:
        command.extend(["--base-branch", base_branch])
    if head_branch is not None:
        command.extend(["--head-branch", head_branch])
    return subprocess.run(command, capture_output=True, text=True, check=False)


def test_restores_the_newest_mutation_cache_from_a_previous_run(tmp_path: Path) -> None:
    api = GitHubApi()
    api.redirect_downloads = True
    api.artifacts = [
        _artifact(1, 10, "2026-10-01T00:00:00Z", head_branch="feature", repository_id=1, head_repository_id=1),
        _artifact(2, 11, "2026-10-10T00:00:00Z", head_branch="main", repository_id=1, head_repository_id=1),
        _artifact(3, 99, "2026-10-11T00:00:00Z", head_branch="feature", repository_id=1, head_repository_id=1),
        _artifact(4, 12, "2026-10-12T00:00:00Z", expired=True, head_branch="main", repository_id=1, head_repository_id=1),
    ]
    api.zips = {
        1: _zip_bytes(("mutation-cache.json", '{"generation":1}\n')),
        2: _zip_bytes(("mutation-cache.json", '{"generation":2}\n')),
        3: _zip_bytes(("mutation-cache.json", '{"generation":3}\n')),
        4: _zip_bytes(("mutation-cache.json", '{"generation":4}\n')),
    }
    dest = tmp_path / ".bob" / "mutation-cache.json"
    server, base = serve(api)
    try:
        result = _restore(dest, base, "99", base_branch="main", head_branch="feature")
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    assert json.loads(dest.read_text()) == {"generation": 2}
    assert not (dest.parent / "stryker-incremental.json").exists()


def test_restore_keeps_only_same_repo_base_or_head_branch_caches(tmp_path: Path) -> None:
    api = GitHubApi()
    api.artifacts = [
        _artifact(1, 10, "2026-10-01T00:00:00Z", head_branch="main", repository_id=1, head_repository_id=1),
        _artifact(2, 11, "2026-10-10T00:00:00Z", head_branch="feature", repository_id=1, head_repository_id=1),
        _artifact(3, 12, "2026-10-11T00:00:00Z", head_branch="feature", repository_id=1, head_repository_id=99),
        _artifact(4, 13, "2026-10-12T00:00:00Z", head_branch="other", repository_id=1, head_repository_id=1),
        _artifact(5, 14, "2026-10-13T00:00:00Z"),
    ]
    api.zips = {
        1: _zip_bytes(("mutation-cache.json", '{"generation":1}\n')),
        2: _zip_bytes(("mutation-cache.json", '{"generation":2}\n')),
        3: _zip_bytes(("mutation-cache.json", '{"generation":3}\n')),
        4: _zip_bytes(("mutation-cache.json", '{"generation":4}\n')),
        5: _zip_bytes(("mutation-cache.json", '{"generation":5}\n')),
    }
    dest = tmp_path / ".bob" / "mutation-cache.json"
    server, base = serve(api)
    try:
        result = _restore(dest, base, "99", base_branch="main", head_branch="feature")
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    assert json.loads(dest.read_text()) == {"generation": 2}


def test_missing_previous_cache_is_not_an_error(tmp_path: Path) -> None:
    api = GitHubApi()
    dest = tmp_path / ".bob" / "mutation-cache.json"
    server, base = serve(api)
    try:
        result = _restore(dest, base, "99")
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    assert not dest.exists()


def test_restore_ignores_zip_entries_that_escape_the_cache_file(tmp_path: Path) -> None:
    api = GitHubApi()
    api.artifacts = [
        _artifact(1, 10, "2026-10-10T00:00:00Z", head_branch="main", repository_id=1, head_repository_id=1)
    ]
    api.zips = {
        1: _zip_bytes(
            ("../outside.txt", "pwned"),
            (".bob/mutation-cache.json", '{"kept":true}\n'),
        )
    }
    dest = tmp_path / ".bob" / "mutation-cache.json"
    server, base = serve(api)
    try:
        result = _restore(dest, base, "99", base_branch="main", head_branch="feature")
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    assert json.loads(dest.read_text()) == {"kept": True}
    assert not (tmp_path / "outside.txt").exists()
    assert not (tmp_path / ".bob" / "outside.txt").exists()


def test_restore_writes_the_stryker_incremental_file_beside_the_cache(tmp_path: Path) -> None:
    api = GitHubApi()
    api.artifacts = [
        _artifact(1, 10, "2026-10-10T00:00:00Z", head_branch="main", repository_id=1, head_repository_id=1)
    ]
    api.zips = {
        1: _zip_bytes(
            (".bob/mutation-cache.json", '{"generation":2}\n'),
            (".bob/stryker-incremental.json", '{"incremental":true}\n'),
            ("../stryker-incremental.json", "pwned"),
        )
    }
    dest = tmp_path / ".bob" / "mutation-cache.json"
    server, base = serve(api)
    try:
        result = _restore(dest, base, "99", base_branch="main", head_branch="feature")
    finally:
        server.shutdown()

    incremental = dest.parent / "stryker-incremental.json"
    assert result.returncode == 0, result.stderr
    assert json.loads(dest.read_text()) == {"generation": 2}
    assert json.loads(incremental.read_text()) == {"incremental": True}
    assert not (tmp_path / "stryker-incremental.json").exists()


def test_restore_writes_incremental_when_the_mutmut_cache_is_absent(tmp_path: Path) -> None:
    api = GitHubApi()
    api.artifacts = [
        _artifact(1, 10, "2026-10-10T00:00:00Z", head_branch="main", repository_id=1, head_repository_id=1)
    ]
    api.zips = {1: _zip_bytes((".bob/stryker-incremental.json", '{"incremental":true}\n'))}
    dest = tmp_path / ".bob" / "mutation-cache.json"
    server, base = serve(api)
    try:
        result = _restore(dest, base, "99", base_branch="main", head_branch="feature")
    finally:
        server.shutdown()

    assert result.returncode == 0, result.stderr
    assert not dest.exists()
    assert json.loads((dest.parent / "stryker-incremental.json").read_text()) == {"incremental": True}
