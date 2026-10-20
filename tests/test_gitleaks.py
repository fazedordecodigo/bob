"""gitleaks 8.30.1: tabela, download conferido e instalação em BOB_HOME."""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import socket
import subprocess
import tarfile
import tempfile
import threading
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import bob_quality.gitleaks as gitleaks
from bob_quality.gitleaks import (
    DEFAULT_BASE_URL,
    VERSION,
    GitleaksError,
    asset_url,
    base_url,
    ensure_gitleaks,
    installed_version,
    platform_key,
)
from bob_quality.messages import msg, reason, render, t
from bob_quality.tools import ToolError
from bob_quality.user_dirs import BobHome, bob_home

_SCRIPT: bytes = (
    b'#!/bin/sh\ncase "$1" in\n  --version) echo "gitleaks version 8.30.1" ;;\n'
    b"  version) echo 8.30.1 ;;\n  *) exit 2 ;;\nesac\n"
)
_ASSET = "gitleaks_8.30.1_linux_x64.tar.gz"
_PARAMS = {
    "system": "S",
    "machine": "M",
    "value": "V",
    "url": "U",
    "status": "X",
    "asset": "A",
    "path": "P",
    "detail": "D",
}
_MESSAGES = {
    "gitleaks.platform": {
        "en": (
            "gitleaks: {system}/{machine} is not in the table. "
            "Supported: linux x64/arm64, darwin x64/arm64."
        ),
        "pt-BR": (
            "gitleaks: {system}/{machine} não está na tabela. "
            "Suportadas: linux x64/arm64, darwin x64/arm64."
        ),
    },
    "gitleaks.url_not_allowed": {
        "en": (
            "gitleaks: BOB_GITLEAKS_BASE_URL={value} is not allowed "
            "(https, or http only on 127.0.0.1/localhost). Fix the variable."
        ),
        "pt-BR": (
            "gitleaks: BOB_GITLEAKS_BASE_URL={value} não é permitida "
            "(https, ou http só em 127.0.0.1/localhost). Corrija a variável."
        ),
    },
    "gitleaks.download": {
        "en": "gitleaks: download of {url} failed ({status}). Check the network and try again.",
        "pt-BR": "gitleaks: download de {url} falhou ({status}). Confira a rede e tente de novo.",
    },
    "gitleaks.integrity": {
        "en": "gitleaks: the sha256 of {asset} does not match. Nothing was installed. Try again.",
        "pt-BR": "gitleaks: o sha256 de {asset} não confere. Nada foi instalado. Tente de novo.",
    },
    "gitleaks.extract": {
        "en": (
            "gitleaks: {asset} does not have the expected gitleaks binary. "
            "Nothing was installed. Open an issue."
        ),
        "pt-BR": (
            "gitleaks: {asset} não tem o binário gitleaks esperado. "
            "Nada foi instalado. Abra uma issue."
        ),
    },
    "gitleaks.write": {
        "en": "gitleaks: could not write {path} ({detail}). Check the permissions.",
        "pt-BR": "gitleaks: não consegui gravar {path} ({detail}). Confira as permissões.",
    },
}


def _archive(members: list[tuple[str, str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, kind, data in members:
            info = tarfile.TarInfo(name)
            if kind == "file":
                info.type = tarfile.REGTYPE
                info.mode = 0o755
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = data.decode()
                tar.addfile(info)
            elif kind == "dir":
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
    return buffer.getvalue()


def _good() -> bytes:
    return _archive(
        [
            ("LICENSE", "file", b"x"),
            ("README.md", "file", b"y"),
            ("gitleaks", "file", _SCRIPT),
        ]
    )


def _leftovers(tmp: Path) -> list[str]:
    if not tmp.is_dir():
        return []
    return sorted(path.name for path in tmp.iterdir() if path.name.startswith("bob-gitleaks-"))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        host = self.server
        host.requests.append(f"GET {self.path}")
        queue = host.routes.get(self.path)
        if not queue:
            self._send(404, b"")
            return
        code, body = queue[0]
        if len(queue) > 1:
            del queue[0]
        self._send(code, body)

    def _send(self, code: int, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class _Server(ThreadingHTTPServer):
    routes: dict[str, list[tuple[int, bytes]]]
    requests: list[str]
    base: str


class _Fake:
    def __init__(
        self,
        server: _Server,
        sleeps: list[float],
        home: BobHome,
        serve: Callable[..., None],
        tmp: Path,
    ) -> None:
        self.server = server
        self.sleeps = sleeps
        self.home = home
        self.serve = serve
        self.tmp = tmp


@pytest.fixture
def server() -> Iterator[_Server]:
    httpd = _Server(("127.0.0.1", 0), _Handler)
    httpd.routes = {}
    httpd.requests = []
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    httpd.base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        yield httpd
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


@pytest.fixture
def fake(server: _Server, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> _Fake:
    monkeypatch.setattr(gitleaks, "platform_key", lambda *_args, **_kwargs: ("linux", "x64"))
    monkeypatch.setenv("BOB_GITLEAKS_BASE_URL", server.base)
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(tmp))
    sleeps: list[float] = []
    monkeypatch.setattr(gitleaks.time, "sleep", sleeps.append)
    home = bob_home({"BOB_HOME": str(tmp_path / "bh")})

    def serve(data: bytes, sha: str | None = None) -> None:
        server.routes[f"/{_ASSET}"] = [(200, data)]
        monkeypatch.setitem(gitleaks.ASSETS, ("linux", "x64"), (_ASSET, sha or _sha(data)))

    return _Fake(server, sleeps, home, serve, tmp)


def _spy_mkdir(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, bool, bool]]:
    real = Path.mkdir
    calls: list[tuple[Path, bool, bool]] = []

    def wrapped(
        self: Path,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        calls.append((self, parents, exist_ok))
        real(self, mode, parents, exist_ok)

    monkeypatch.setattr(Path, "mkdir", wrapped)
    return calls


def _spy_tar(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    real = tarfile.open
    modes: list[str] = []

    def wrapped(name: object, mode: str = "r", *args: object, **kwargs: object) -> object:
        modes.append(mode)
        return real(name, mode, *args, **kwargs)

    monkeypatch.setattr(gitleaks.tarfile, "open", wrapped)
    return modes


def _strict_rmtree(monkeypatch: pytest.MonkeyPatch) -> None:
    real = shutil.rmtree

    def wrapped(path: object, ignore_errors: bool = False, *args: object, **kwargs: object) -> None:
        if ignore_errors is not True:
            raise OSError("rmtree")
        real(path, ignore_errors=True)

    monkeypatch.setattr(gitleaks.shutil, "rmtree", wrapped)


def test_version_and_default_base_url() -> None:
    assert VERSION == "8.30.1"
    assert DEFAULT_BASE_URL == (
        "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1"
    )


def test_assets_are_the_four_adr_0014_entries() -> None:
    assert gitleaks.ASSETS == {
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


@pytest.mark.parametrize(
    ("system", "machine", "expected"),
    [
        ("Linux", "x86_64", ("linux", "x64")),
        ("Linux", "amd64", ("linux", "x64")),
        ("Linux", "aarch64", ("linux", "arm64")),
        ("Linux", "arm64", ("linux", "arm64")),
        ("Darwin", "x86_64", ("darwin", "x64")),
        ("Darwin", "arm64", ("darwin", "arm64")),
    ],
)
def test_platform_key_maps_the_ct9_table(
    system: str, machine: str, expected: tuple[str, str]
) -> None:
    assert platform_key(system, machine) == expected
    assert expected in gitleaks.ASSETS


def test_platform_key_defaults_to_this_machine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gitleaks.platform, "system", lambda: "Linux")
    monkeypatch.setattr(gitleaks.platform, "machine", lambda: "aarch64")
    assert platform_key() == ("linux", "arm64")


@pytest.mark.parametrize(
    ("system", "machine"),
    [
        ("Windows", "AMD64"),
        ("Linux", "armv7l"),
        ("Darwin", "aarch64"),
        ("FreeBSD", "x86_64"),
        ("linux", "x86_64"),
    ],
)
def test_platform_key_rejects_other_platforms(system: str, machine: str) -> None:
    with pytest.raises(GitleaksError) as caught:
        platform_key(system, machine)
    assert reason(caught.value) == msg("gitleaks.platform", system=system, machine=machine)


def test_gitleaks_error_is_a_tool_error() -> None:
    assert issubclass(GitleaksError, ToolError)


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({}, DEFAULT_BASE_URL),
        ({"BOB_GITLEAKS_BASE_URL": ""}, DEFAULT_BASE_URL),
        ({"BOB_GITLEAKS_BASE_URL": "https://mirror.example/gl/"}, "https://mirror.example/gl"),
        ({"BOB_GITLEAKS_BASE_URL": "http://127.0.0.1"}, "http://127.0.0.1"),
        ({"BOB_GITLEAKS_BASE_URL": "http://127.0.0.1:8000/"}, "http://127.0.0.1:8000"),
        ({"BOB_GITLEAKS_BASE_URL": "http://localhost"}, "http://localhost"),
        ({"BOB_GITLEAKS_BASE_URL": "http://localhost/gl"}, "http://localhost/gl"),
    ],
)
def test_base_url_accepts_https_and_loopback(env: dict[str, str], expected: str) -> None:
    assert base_url(env) == expected


@pytest.mark.parametrize(
    "value",
    [
        "http://example.com",
        "ftp://127.0.0.1",
        "http://127.0.0.1.example.com",
        "http://localhost.example.com",
        "file:///tmp/gl",
        "http://example.com/",
    ],
)
def test_base_url_rejects_other_urls(value: str) -> None:
    trimmed = value[:-1] if value.endswith("/") else value
    with pytest.raises(GitleaksError) as caught:
        base_url({"BOB_GITLEAKS_BASE_URL": value})
    assert reason(caught.value) == msg("gitleaks.url_not_allowed", value=trimmed)


def test_asset_url_joins_base_and_asset() -> None:
    assert asset_url(("darwin", "arm64")) == (
        DEFAULT_BASE_URL + "/gitleaks_8.30.1_darwin_arm64.tar.gz"
    )
    assert asset_url(("linux", "x64"), "http://127.0.0.1:9") == (
        "http://127.0.0.1:9/gitleaks_8.30.1_linux_x64.tar.gz"
    )


def test_installed_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = bob_home({"BOB_HOME": str(tmp_path / "bh")})
    seen: list[dict[str, object]] = []
    real = subprocess.run

    def wrapped(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.append(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(gitleaks.subprocess, "run", wrapped)
    assert installed_version(home) is None

    binary = home.bin / "gitleaks"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(_SCRIPT)
    binary.chmod(0o755)
    assert installed_version(home) == "8.30.1"

    binary.write_bytes(b'#!/bin/sh\necho "gitleaks version 8.30.1-beta.1"\n')
    binary.chmod(0o755)
    assert installed_version(home) == "8.30.1-beta.1"

    binary.write_bytes(b"#!/bin/sh\nexit 1\n")
    binary.chmod(0o755)
    assert installed_version(home) is None

    binary.write_bytes(b'#!/bin/sh\necho "no version"\n')
    binary.chmod(0o755)
    assert installed_version(home) is None

    binary.write_bytes(_SCRIPT)
    binary.chmod(0o644)
    assert installed_version(home) is None

    binary.unlink()
    binary.symlink_to("missing-gitleaks")
    assert installed_version(home) is None

    assert seen
    for kwargs in seen:
        assert kwargs["timeout"] == 30
        assert kwargs["check"] is False
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["stdin"] is subprocess.DEVNULL


def test_ensure_installs_the_binary_and_the_link(
    fake: _Fake,
    server: _Server,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake.serve(_good())
    calls = _spy_mkdir(monkeypatch)
    modes = _spy_tar(monkeypatch)
    home = fake.home
    assert ensure_gitleaks(home) == home.bin / "gitleaks"
    assert os.readlink(home.bin / "gitleaks") == "../tools/gitleaks/8.30.1/gitleaks"
    binary = home.tools / "gitleaks" / "8.30.1" / "gitleaks"
    assert binary.read_bytes() == _SCRIPT
    assert binary.stat().st_mode & 0o777 == 0o755
    assert installed_version(home) == "8.30.1"
    assert server.requests == [f"GET /{_ASSET}"]
    assert not os.path.lexists(home.bin / "gitleaks.tmp")
    assert not os.path.lexists(binary.parent / "gitleaks.tmp")
    assert os.listdir(binary.parent) == ["gitleaks"]
    assert _leftovers(fake.tmp) == []
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert modes == ["r:gz"]
    recorded = {(path, parents, exist_ok) for path, parents, exist_ok in calls}
    assert (home.bin, True, True) in recorded
    assert (binary.parent, True, True) in recorded


def test_second_ensure_downloads_nothing(fake: _Fake, server: _Server) -> None:
    fake.serve(_good())
    home = fake.home
    first = ensure_gitleaks(home)
    binary = home.tools / "gitleaks" / "8.30.1" / "gitleaks"
    before = binary.stat()
    second = ensure_gitleaks(home)
    after = binary.stat()
    assert second == first == home.bin / "gitleaks"
    assert server.requests == [f"GET /{_ASSET}"]
    assert before.st_mtime_ns == after.st_mtime_ns
    assert before.st_ino == after.st_ino


def test_wrong_version_is_replaced(fake: _Fake, server: _Server) -> None:
    home = fake.home
    home.bin.mkdir(parents=True)
    current = home.bin / "gitleaks"
    current.write_bytes(b'#!/bin/sh\necho "gitleaks version 8.29.0"\n')
    current.chmod(0o755)
    fake.serve(_good())
    ensure_gitleaks(home)
    assert os.readlink(home.bin / "gitleaks") == "../tools/gitleaks/8.30.1/gitleaks"
    assert installed_version(home) == "8.30.1"
    assert server.requests == [f"GET /{_ASSET}"]


@pytest.mark.parametrize("lang", ["en", "pt-BR"])
def test_tampered_archive_fails_integrity_and_installs_nothing(
    fake: _Fake, server: _Server, lang: str
) -> None:
    data = _good()
    fake.serve(data + b"\n", sha=_sha(data))
    with pytest.raises(GitleaksError) as caught:
        ensure_gitleaks(fake.home)
    assert reason(caught.value) == msg("gitleaks.integrity", asset=_ASSET)
    rendered = render(reason(caught.value), lang)
    assert "gitleaks" in rendered
    assert "sha256" in rendered
    home = fake.home
    assert not (home.tools / "gitleaks").exists()
    assert not os.path.lexists(home.bin / "gitleaks")
    assert server.requests == [f"GET /{_ASSET}"]
    assert fake.sleeps == []
    assert _leftovers(fake.tmp) == []


@pytest.mark.parametrize(
    "payload",
    [
        _archive([("LICENSE", "file", b"x")]),
        _archive([("gitleaks", "symlink", b"elsewhere")]),
        _archive([("gitleaks", "dir", b"")]),
        _archive([("bin/gitleaks", "file", _SCRIPT)]),
        _archive([("./gitleaks", "file", _SCRIPT)]),
        _archive(
            [
                ("gitleaks", "file", _SCRIPT),
                ("gitleaks", "file", _SCRIPT),
            ]
        ),
        b"not a tar.gz",
    ],
)
def test_archive_without_the_expected_binary_fails_extraction(
    fake: _Fake, payload: bytes
) -> None:
    fake.serve(payload)
    with pytest.raises(GitleaksError) as caught:
        ensure_gitleaks(fake.home)
    assert reason(caught.value) == msg("gitleaks.extract", asset=_ASSET)
    home = fake.home
    assert not (home.tools / "gitleaks").exists()
    assert not os.path.lexists(home.bin / "gitleaks")
    assert _leftovers(fake.tmp) == []


@pytest.mark.parametrize("code", [404, 429])
def test_http_4xx_is_not_retried(fake: _Fake, server: _Server, code: int) -> None:
    server.routes[f"/{_ASSET}"] = [(code, b"")]
    with pytest.raises(GitleaksError) as caught:
        ensure_gitleaks(fake.home)
    url = f"{server.base}/{_ASSET}"
    assert reason(caught.value) == msg("gitleaks.download", url=url, status=f"HTTP {code}")
    assert server.requests == [f"GET /{_ASSET}"]
    assert fake.sleeps == []


@pytest.mark.parametrize("code", [500, 503])
def test_5xx_is_retried_twice(fake: _Fake, server: _Server, code: int) -> None:
    server.routes[f"/{_ASSET}"] = [(code, b"")]
    with pytest.raises(GitleaksError) as caught:
        ensure_gitleaks(fake.home)
    url = f"{server.base}/{_ASSET}"
    assert reason(caught.value) == msg("gitleaks.download", url=url, status=f"HTTP {code}")
    assert server.requests == [f"GET /{_ASSET}", f"GET /{_ASSET}", f"GET /{_ASSET}"]
    assert fake.sleeps == [1.0, 1.0]
    assert not (fake.home.tools / "gitleaks").exists()


def test_5xx_then_200_installs(
    fake: _Fake, server: _Server, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = _good()
    server.routes[f"/{_ASSET}"] = [(503, b""), (200, data)]
    monkeypatch.setitem(gitleaks.ASSETS, ("linux", "x64"), (_ASSET, _sha(data)))
    assert ensure_gitleaks(fake.home) == fake.home.bin / "gitleaks"
    assert server.requests == [f"GET /{_ASSET}", f"GET /{_ASSET}"]
    assert fake.sleeps == [1.0]


def test_network_error_is_retried_twice(
    fake: _Fake, monkeypatch: pytest.MonkeyPatch
) -> None:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    base = f"http://127.0.0.1:{port}"
    monkeypatch.setenv("BOB_GITLEAKS_BASE_URL", base)
    calls: list[str] = []
    real = gitleaks.urllib.request.urlopen

    def wrapped(url: str, *args: object, **kwargs: object) -> object:
        calls.append(url)
        return real(url, *args, **kwargs)

    monkeypatch.setattr(gitleaks.urllib.request, "urlopen", wrapped)
    with pytest.raises(GitleaksError) as caught:
        ensure_gitleaks(fake.home)
    url = f"{base}/{_ASSET}"
    assert reason(caught.value) == msg(
        "gitleaks.download", url=url, status="ConnectionRefusedError"
    )
    assert calls == [url, url, url]
    assert fake.sleeps == [1.0, 1.0]


def test_download_uses_a_30_s_timeout(
    fake: _Fake, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = _good()
    seen: dict[str, object] = {}

    class _Body:
        def read(self) -> bytes:
            return data

        def __enter__(self) -> _Body:
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

    def opened(url: str, **kwargs: object) -> _Body:
        seen["timeout"] = kwargs["timeout"]
        seen["leftovers"] = _leftovers(fake.tmp)
        return _Body()

    monkeypatch.setattr(gitleaks.urllib.request, "urlopen", opened)
    fake.serve(data)
    ensure_gitleaks(fake.home)
    assert seen["timeout"] == 30
    leftovers = seen["leftovers"]
    assert isinstance(leftovers, list)
    assert len(leftovers) == 1
    assert str(leftovers[0]).startswith("bob-gitleaks-")
    assert _leftovers(fake.tmp) == []


def test_reinstall_over_leftovers(fake: _Fake) -> None:
    home = fake.home
    version = home.tools / "gitleaks" / "8.30.1"
    version.mkdir(parents=True)
    (version / "gitleaks.tmp").write_bytes(b"stale")
    home.bin.mkdir(parents=True)
    (home.bin / "gitleaks.tmp").write_bytes(b"stale")
    fake.serve(_good())
    ensure_gitleaks(home)
    assert os.readlink(home.bin / "gitleaks") == "../tools/gitleaks/8.30.1/gitleaks"
    assert not os.path.lexists(home.bin / "gitleaks.tmp")
    assert not os.path.lexists(version / "gitleaks.tmp")


def test_unsupported_platform_fails_before_any_request(
    server: _Server, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(gitleaks.platform, "system", lambda: "Windows")
    monkeypatch.setattr(gitleaks.platform, "machine", lambda: "AMD64")
    monkeypatch.setenv("BOB_GITLEAKS_BASE_URL", server.base)
    home = bob_home({"BOB_HOME": str(tmp_path / "bh")})
    with pytest.raises(GitleaksError) as caught:
        ensure_gitleaks(home)
    assert reason(caught.value) == msg("gitleaks.platform", system="Windows", machine="AMD64")
    assert server.requests == []
    assert not home.root.exists()


def test_bad_base_url_fails_before_any_request(
    server: _Server, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("BOB_GITLEAKS_BASE_URL", "http://example.com")
    home = bob_home({"BOB_HOME": str(tmp_path / "bh")})
    with pytest.raises(GitleaksError) as caught:
        ensure_gitleaks(home)
    assert reason(caught.value) == msg("gitleaks.url_not_allowed", value="http://example.com")
    assert server.requests == []
    assert not home.root.exists()


def test_write_error_leaves_nothing_in_tools(
    fake: _Fake, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake.serve(_good())
    home = fake.home
    home.root.mkdir()
    home.bin.write_bytes(b"not-a-directory")
    _strict_rmtree(monkeypatch)
    with pytest.raises(GitleaksError) as caught:
        ensure_gitleaks(home)
    message = reason(caught.value)
    assert message.key == "gitleaks.write"
    params = dict(message.params)
    assert params["path"] == str(home.bin)
    assert params["detail"] == "File exists"
    assert not (home.tools / "gitleaks").exists()
    assert _leftovers(fake.tmp) == []


def test_write_error_keeps_what_was_there(
    fake: _Fake, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = fake.home
    old = home.tools / "gitleaks" / "8.29.0" / "gitleaks"
    old.parent.mkdir(parents=True)
    old.write_bytes(b"old")
    home.bin.write_bytes(b"not-a-directory")
    fake.serve(_good())
    _strict_rmtree(monkeypatch)
    with pytest.raises(GitleaksError) as caught:
        ensure_gitleaks(home)
    assert reason(caught.value).key == "gitleaks.write"
    assert old.read_bytes() == b"old"
    assert not (home.tools / "gitleaks" / "8.30.1").exists()
    assert _leftovers(fake.tmp) == []


def test_write_error_without_filename_names_the_destination(
    fake: _Fake, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake.serve(_good())
    real = os.replace

    def broken(src: object, dst: object) -> None:
        if isinstance(dst, Path) and dst.name == "gitleaks" and "tools" in dst.parts:
            raise OSError("disk")
        real(src, dst)

    monkeypatch.setattr(gitleaks.os, "replace", broken)
    with pytest.raises(GitleaksError) as caught:
        ensure_gitleaks(fake.home)
    params = dict(reason(caught.value).params)
    dest = fake.home.tools / "gitleaks" / "8.30.1"
    assert params["path"] == str(dest)
    assert params["detail"] == "OSError"
    assert not (fake.home.tools / "gitleaks").exists()
    assert _leftovers(fake.tmp) == []


def test_timeout_error_is_retried_twice(
    fake: _Fake, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def boom(*_args: object, **_kwargs: object) -> object:
        calls.append(1)
        raise TimeoutError("slow")

    monkeypatch.setattr(gitleaks.urllib.request, "urlopen", boom)
    with pytest.raises(GitleaksError) as caught:
        ensure_gitleaks(fake.home)
    url = f"{fake.server.base}/{_ASSET}"
    assert reason(caught.value) == msg("gitleaks.download", url=url, status="TimeoutError")
    assert calls == [1, 1, 1]
    assert fake.sleeps == [1.0, 1.0]


def test_extractfile_none_fails_extraction(
    fake: _Fake, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gitleaks.tarfile.TarFile, "extractfile", lambda *_args: None)
    fake.serve(_good())
    with pytest.raises(GitleaksError) as caught:
        ensure_gitleaks(fake.home)
    assert reason(caught.value) == msg("gitleaks.extract", asset=_ASSET)
    assert not (fake.home.tools / "gitleaks").exists()
    assert _leftovers(fake.tmp) == []


def test_rollback_removes_temporary_binary(fake: _Fake, monkeypatch: pytest.MonkeyPatch) -> None:
    home = fake.home
    version = home.tools / "gitleaks" / "8.30.1"
    version.mkdir(parents=True)
    (version / "keep").write_bytes(b"keep")
    fake.serve(_good())
    real = os.chmod

    def boom(path: object, mode: int) -> None:
        if str(path).endswith("gitleaks.tmp"):
            raise OSError("disk")
        real(path, mode)

    monkeypatch.setattr(gitleaks.os, "chmod", boom)
    with pytest.raises(GitleaksError):
        ensure_gitleaks(home)
    assert not os.path.lexists(version / "gitleaks.tmp")
    assert (version / "keep").read_bytes() == b"keep"


def test_rollback_removes_temporary_link(fake: _Fake, monkeypatch: pytest.MonkeyPatch) -> None:
    home = fake.home
    version = home.tools / "gitleaks" / "8.30.1"
    version.mkdir(parents=True)
    (version / "keep").write_bytes(b"keep")
    home.bin.mkdir(parents=True)
    fake.serve(_good())
    real = os.replace

    def boom(src: object, dst: object) -> None:
        if isinstance(dst, Path) and dst.parent == home.bin:
            raise OSError("disk")
        real(src, dst)

    monkeypatch.setattr(gitleaks.os, "replace", boom)
    with pytest.raises(GitleaksError):
        ensure_gitleaks(home)
    assert not os.path.lexists(home.bin / "gitleaks.tmp")
    assert not os.path.lexists(home.bin / "gitleaks")
    assert (version / "keep").read_bytes() == b"keep"


def test_write_error_keeps_an_existing_destination(fake: _Fake) -> None:
    home = fake.home
    version = home.tools / "gitleaks" / "8.30.1"
    version.mkdir(parents=True)
    (version / "keep").write_bytes(b"keep")
    home.bin.write_bytes(b"not-a-directory")
    fake.serve(_good())
    with pytest.raises(GitleaksError) as caught:
        ensure_gitleaks(home)
    assert reason(caught.value).key == "gitleaks.write"
    assert (version / "keep").read_bytes() == b"keep"
    assert version.is_dir()


@pytest.mark.parametrize("lang", ["en", "pt-BR"])
@pytest.mark.parametrize("key", list(_MESSAGES))
def test_gitleaks_messages_exist_in_both_languages(lang: str, key: str) -> None:
    template = _MESSAGES[key][lang]
    assert t(lang, key, **_PARAMS) == template.format(**_PARAMS)
