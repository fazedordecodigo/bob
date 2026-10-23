"""bob update e bob --version (C10, CT11, ADR 0025)."""

from __future__ import annotations

import hashlib
import http.client
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from pathlib import Path

from bob_quality import project_version, setup_cmd, user_dirs
from bob_quality.exit_codes import CONFIG_OR_TOOL, PASSED
from bob_quality.messages import Language, msg, render, t

DEFAULT_API = "https://api.github.com/repos/fazedordecodigo/bob/releases/latest"
DEFAULT_DOWNLOAD = "https://github.com/fazedordecodigo/bob/releases/download"
_PKG = "bob-quality"
_ENV_URL = "BOB_RELEASES_URL"
_PIN_ENV = "BOB_VERSION"
_ACCEPT = {"Accept": "application/vnd.github+json"}
_TIMEOUT_S = 30
_ATTEMPTS = 3
_PAUSE_S = 1.0
_RETRYABLE = (
    urllib.error.URLError,
    TimeoutError,
    ConnectionError,
    http.client.HTTPException,
)
_ALLOWED_URL = re.compile(
    r"https://.*|http://(?:127\.0\.0\.1|localhost)(?:$|:.*|/.*)"
)
_TAG_RE = re.compile(r"v\d+\.\d+\.\d+")
_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")
_TAG_KEY = "tag_name"
_API_SUFFIX = "/api/releases/latest"
_DOWNLOAD_SUFFIX = "/download"
_SLASH = "/"
_SCRIPT = "install.sh"
_SUMS = "SHA256SUMS"
_SUMS_SEP = b"  "
_NL = b"\n"
_NOT_FOUND = 404
_FIRST_SERVER_ERROR = 500
_TMP_PREFIX = "bob-update."
_SH = "sh"
_LANG_FLAG = "--lang"


class UpdateError(Exception):
    pass


def version_lines(project: Path, lang: Language) -> list[str]:
    return [
        t(lang, "version.bob", version=importlib.metadata.version(_PKG)),
        render(project_version.skills_line(project), lang),
    ]


def _urls(env: Mapping[str, str]) -> tuple[str, str]:
    value = env.get(_ENV_URL) or ""
    if value == "":
        return (DEFAULT_API, DEFAULT_DOWNLOAD)
    base = value[:-1] if value.endswith(_SLASH) else value
    if _ALLOWED_URL.fullmatch(base) is None:
        raise UpdateError(msg("update.url_not_allowed", url=base))
    return (base + _API_SUFFIX, base + _DOWNLOAD_SUFFIX)


def _status(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return type(exc.reason).__name__
    return type(exc).__name__


def _read(url: str, headers: Mapping[str, str]) -> bytes:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=_TIMEOUT_S) as response:
        return response.read()


def _fetch(url: str, headers: Mapping[str, str]) -> bytes | BaseException:
    for attempt in range(_ATTEMPTS):
        try:
            return _read(url, headers)
        except _RETRYABLE as exc:
            failure = exc
        if isinstance(failure, urllib.error.HTTPError) and failure.code < _FIRST_SERVER_ERROR:
            return failure
        if attempt + 1 == _ATTEMPTS:
            return failure
        time.sleep(_PAUSE_S)


def _latest_tag(api: str) -> str:
    fetched = _fetch(api, _ACCEPT)
    if isinstance(fetched, BaseException):
        raise UpdateError(msg("update.api_failed", status=_status(fetched)))
    try:
        data = json.loads(fetched)
    except ValueError:
        data = None
    tag = data.get(_TAG_KEY) if isinstance(data, dict) else None
    if not isinstance(tag, str) or _TAG_RE.fullmatch(tag) is None:
        raise UpdateError(msg("update.api_failed", status=msg("update.bad_response")))
    return tag


def _numbers(text: str) -> tuple[int, ...] | None:
    match = _VERSION_RE.fullmatch(text)
    if match is None:
        return None
    return tuple(int(group) for group in match.groups())


def _download(base: str, tag: str, asset: str) -> bytes:
    url = f"{base}/{tag}/{asset}"
    fetched = _fetch(url, {})
    if isinstance(fetched, urllib.error.HTTPError) and fetched.code == _NOT_FOUND:
        raise UpdateError(msg("update.download_missing", tag=tag, asset=asset))
    if isinstance(fetched, BaseException):
        raise UpdateError(
            msg("update.download_failed", url=url, status=_status(fetched))
        )
    return fetched


def _sum_for(sums: bytes, name: bytes) -> bytes | None:
    for line in sums.split(_NL):
        digest, _sep, found = line.partition(_SUMS_SEP)
        if found == name:
            return digest
    return None


def _install(project: Path, lang: Language, tag: str, base: str) -> int:
    try:
        tmp = tempfile.mkdtemp(prefix=_TMP_PREFIX)
    except OSError as exc:
        raise UpdateError(msg("update.tmp_failed", detail=str(exc)))
    try:
        script = _download(base, tag, _SCRIPT)
        sums = _download(base, tag, _SUMS)
        digest = hashlib.sha256(script).hexdigest().encode()
        if _sum_for(sums, _SCRIPT.encode()) != digest:
            raise UpdateError(msg("update.integrity", file=_SCRIPT))
        path = Path(tmp) / _SCRIPT
        try:
            path.write_bytes(script)
        except OSError as exc:
            raise UpdateError(msg("update.tmp_failed", detail=str(exc)))
        try:
            completed = subprocess.run(
                [_SH, str(path), _LANG_FLAG, lang],
                cwd=project,
                env={**os.environ, _PIN_ENV: tag},
                check=False,
            )
        except OSError as exc:
            raise UpdateError(msg("update.install_failed", detail=str(exc)))
        return completed.returncode
    finally:
        shutil.rmtree(tmp)


def run_update(project: Path, lang: Language) -> int:
    try:
        return _run(project.resolve(), lang)
    except UpdateError as exc:
        print(t(lang, "update.error", reason=exc.args[0]), file=sys.stderr)
        return CONFIG_OR_TOOL


def _run(project: Path, lang: Language) -> int:
    try:
        home = user_dirs.bob_home()
    except ValueError as exc:
        raise UpdateError(msg("setup.bob_home_relative", value=str(exc)))
    version = importlib.metadata.version(_PKG)
    checked = setup_cmd.step_projeto(
        setup_cmd.SetupContext(
            project=project, home=home, lang=lang, version=version
        )
    )
    if checked.error is not None:
        raise UpdateError(checked.error)
    api, base = _urls(os.environ)
    tag = _latest_tag(api)
    latest = _numbers(tag[1:])
    current = _numbers(version)
    if current is not None and current >= latest:
        skills = project_version.read_project_skills(project)
        if skills.state == "installed" and _numbers(skills.versions[0]) >= latest:
            print(t(lang, "update.up_to_date", tag=tag))
            return PASSED
        print(t(lang, "update.project_only", tag=tag))
        return setup_cmd.run_setup(project, lang)
    print(t(lang, "update.upgrading", old=version, tag=tag))
    return _install(project, lang, tag, base)
