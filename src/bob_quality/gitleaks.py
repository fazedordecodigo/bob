"""gitleaks 8.30.1: tabela da ADR 0014, download conferido e instalação em BOB_HOME (CT9)."""

from __future__ import annotations

import hashlib
import http.client
import os
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zlib
from collections.abc import Mapping
from pathlib import Path

from bob_quality.messages import msg
from bob_quality.tools import ToolError
from bob_quality.user_dirs import BobHome

VERSION = "8.30.1"
DEFAULT_BASE_URL = f"https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}"
ASSETS: dict[tuple[str, str], tuple[str, str]] = {
    ("linux", "x64"): (
        "gitleaks_8.30.1_linux_x64.tar.gz",
        "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
    ),
    ("linux", "arm64"): (
        "gitleaks_8.30.1_linux_arm64.tar.gz",
        "e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080",
    ),
    ("darwin", "x64"): (
        "gitleaks_8.30.1_darwin_x64.tar.gz",
        "dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709",
    ),
    ("darwin", "arm64"): (
        "gitleaks_8.30.1_darwin_arm64.tar.gz",
        "b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5",
    ),
}

_TIMEOUT_S = 30
_ATTEMPTS = 3
_PAUSE_S = 1.0
_VERSION_RE = re.compile(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?")
_ALLOWED_URL = re.compile(r"https://.*|http://(?:127\.0\.0\.1|localhost)(?:$|:.*|/.*)")
_KEYS = {
    ("Linux", "x86_64"): ("linux", "x64"),
    ("Linux", "amd64"): ("linux", "x64"),
    ("Linux", "aarch64"): ("linux", "arm64"),
    ("Linux", "arm64"): ("linux", "arm64"),
    ("Darwin", "x86_64"): ("darwin", "x64"),
    ("Darwin", "arm64"): ("darwin", "arm64"),
}
_RETRYABLE = (
    urllib.error.URLError,
    TimeoutError,
    ConnectionError,
    http.client.HTTPException,
)
_BINARY_NAME = "gitleaks"


class GitleaksError(ToolError):
    """Falha do passo gitleaks: plataforma, URL, download, sha256, extração ou escrita."""


def platform_key(system: str | None = None, machine: str | None = None) -> tuple[str, str]:
    """Chave de ASSETS para o SO e a arquitetura (CT9); fora da tabela é GitleaksError."""
    chosen = system if system is not None else platform.system()
    arch = machine if machine is not None else platform.machine()
    found = _KEYS.get((chosen, arch))
    if found is None:
        raise GitleaksError(msg("gitleaks.platform", system=chosen, machine=arch))
    return found


def base_url(env: Mapping[str, str] = os.environ) -> str:
    """BOB_GITLEAKS_BASE_URL sem a barra final, ou a release oficial (CT6)."""
    value = env.get("BOB_GITLEAKS_BASE_URL") or ""
    if value == "":
        return DEFAULT_BASE_URL
    trimmed = value[:-1] if value.endswith("/") else value
    if _allowed(trimmed):
        return trimmed
    raise GitleaksError(msg("gitleaks.url_not_allowed", value=trimmed))


def asset_url(key: tuple[str, str], base: str = DEFAULT_BASE_URL) -> str:
    """URL do tar.gz da chave."""
    return f"{base}/{ASSETS[key][0]}"


def installed_version(home: BobHome) -> str | None:
    """Versão de BOB_HOME/bin/gitleaks, ou None se não existe ou não roda."""
    try:
        completed = subprocess.run(
            [str(home.bin / _BINARY_NAME), "--version"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    found = _VERSION_RE.search(completed.stdout)
    if found is None:
        return None
    return found.group(0)


def ensure_gitleaks(home: BobHome) -> Path:
    """Instala o gitleaks 8.30.1 em BOB_HOME se faltar e devolve BOB_HOME/bin/gitleaks."""
    link = home.bin / _BINARY_NAME
    if installed_version(home) == VERSION:
        return link
    key = platform_key()
    asset, digest = ASSETS[key]
    url = asset_url(key, base_url())
    with tempfile.TemporaryDirectory(prefix="bob-gitleaks-") as directory:
        folder = Path(directory)
        payload = _download(url)
        (folder / asset).write_bytes(payload)
        if hashlib.sha256(payload).hexdigest() != digest:
            raise GitleaksError(msg("gitleaks.integrity", asset=asset))
        binary = folder / _BINARY_NAME
        binary.write_bytes(_extract(folder / asset, asset))
        return _install(home, binary.read_bytes())


def _allowed(value: str) -> bool:
    return _ALLOWED_URL.fullmatch(value) is not None


def _client_error(exc: BaseException) -> bool:
    return isinstance(exc, urllib.error.HTTPError) and exc.code < 500


def _read_url(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=_TIMEOUT_S) as response:
        return response.read()


def _status(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return type(exc.reason).__name__
    return type(exc).__name__


def _failure(url: str, exc: BaseException) -> GitleaksError:
    return GitleaksError(msg("gitleaks.download", url=url, status=_status(exc)))


def _fetch(url: str) -> bytes | BaseException:
    for attempt in range(1, _ATTEMPTS + 1):
        try:
            return _read_url(url)
        except _RETRYABLE as exc:
            failure = exc
        if _client_error(failure) or attempt == _ATTEMPTS:
            return failure
        time.sleep(_PAUSE_S)


def _download(url: str) -> bytes:
    fetched = _fetch(url)
    if isinstance(fetched, bytes):
        return fetched
    raise _failure(url, fetched) from fetched


def _regular_member(tar: tarfile.TarFile) -> tarfile.TarInfo:
    found = [item for item in tar.getmembers() if item.name == _BINARY_NAME]
    if len(found) != 1 or not found[0].isreg():
        raise tarfile.ReadError()
    return found[0]


def _member_bytes(archive: Path) -> bytes:
    with tarfile.open(archive, "r:gz") as tar:
        reader = tar.extractfile(_regular_member(tar))
        if reader is None:
            raise tarfile.ReadError()
        return reader.read()


def _extract(archive: Path, asset: str) -> bytes:
    try:
        return _member_bytes(archive)
    except (tarfile.TarError, EOFError, zlib.error, OSError):
        raise GitleaksError(msg("gitleaks.extract", asset=asset)) from None


def _unlink_quiet(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        return


def _write_binary(dest: Path, payload: bytes) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    temporary = dest / "gitleaks.tmp"
    temporary.write_bytes(payload)
    os.chmod(temporary, 0o755)
    os.replace(temporary, dest / _BINARY_NAME)


def _link_binary(home: BobHome) -> None:
    home.bin.mkdir(parents=True, exist_ok=True)
    temporary = home.bin / "gitleaks.tmp"
    _unlink_quiet(temporary)
    os.symlink(f"../tools/gitleaks/{VERSION}/gitleaks", temporary)
    os.replace(temporary, home.bin / _BINARY_NAME)


def _rollback(home: BobHome, dest: Path, existed: bool, dest_existed: bool) -> None:
    _unlink_quiet(dest / "gitleaks.tmp")
    _unlink_quiet(home.bin / "gitleaks.tmp")
    if not existed:
        shutil.rmtree(home.tools / _BINARY_NAME, ignore_errors=True)
        return
    if not dest_existed:
        shutil.rmtree(dest, ignore_errors=True)


def _write_error(dest: Path, exc: OSError) -> GitleaksError:
    path = str(exc.filename) if exc.filename is not None else str(dest)
    detail = exc.strerror or type(exc).__name__
    return GitleaksError(msg("gitleaks.write", path=path, detail=detail))


def _install(home: BobHome, payload: bytes) -> Path:
    dest = home.tools / _BINARY_NAME / VERSION
    existed = (home.tools / _BINARY_NAME).exists()
    dest_existed = dest.exists()
    try:
        _write_binary(dest, payload)
        _link_binary(home)
    except OSError as exc:
        _rollback(home, dest, existed, dest_existed)
        raise _write_error(dest, exc) from exc
    return home.bin / _BINARY_NAME
