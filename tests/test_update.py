"""bob update e bob --version (C10, CT11, ADR 0025)."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from bob_quality import cli, gitleaks, install_skills, update
from bob_quality.messages import msg, t
from helpers import run_bob

ROOT = Path(__file__).resolve().parents[1]
API = update.DEFAULT_API
DL = update.DEFAULT_DOWNLOAD + "/v1.2.3/"
ACCEPT = {"Accept": "application/vnd.github+json"}
BODY = (
    b'printf "%s|%s|%s|%s|%s|%s\\n" "$0" "$*" "$BOB_VERSION" '
    b'"$(pwd -P)" "${FOO:-}" "${BOB_RELEASES_URL:-}" > "$UPD_LOG"\n'
    b'exit "${UPD_RC:-0}"\n'
)
_MESSAGE_KEYS = (
    "cli.update",
    "cli.version",
    "version.bob",
    "update.error",
    "update.up_to_date",
    "update.project_only",
    "update.upgrading",
    "update.api_failed",
    "update.bad_response",
    "update.url_not_allowed",
    "update.tmp_failed",
    "update.download_failed",
    "update.download_missing",
    "update.integrity",
    "update.install_failed",
)
_EXPECTED = {
    "en": {
        "cli.update": "Update bob and this project to the latest published release",
        "cli.version": "Show the bob version and the project skills version",
        "version.bob": "bob V",
        "update.error": "bob update: R",
        "update.up_to_date": "bob update: already on the newest release (v9.9.9).",
        "update.project_only": "bob update: updating the project to v9.9.9.",
        "update.upgrading": "bob update: updating from v1.0.0 to v9.9.9.",
        "update.api_failed": "versão: could not read the latest release (S). Try again.",
        "update.bad_response": "invalid response",
        "update.url_not_allowed": (
            "versão: BOB_RELEASES_URL=U is not allowed. "
            "Use https://, or http:// only on 127.0.0.1 or localhost."
        ),
        "update.tmp_failed": "download: could not create a temporary folder (D).",
        "update.download_failed": "download: U failed (S). Check the network and try again.",
        "update.download_missing": (
            "download: release v9.9.9 is incomplete (A missing). Open an issue."
        ),
        "update.integrity": (
            "integridade: the sha256 of F does not match. Nothing was installed. Try again."
        ),
        "update.install_failed": "instalar: could not run sh (D).",
    },
    "pt-BR": {
        "cli.update": "Atualiza o bob e este projeto para a última release publicada",
        "cli.version": "Mostra a versão do bob e a das skills do projeto",
        "version.bob": "bob V",
        "update.error": "bob update: R",
        "update.up_to_date": "bob update: já está na release mais nova (v9.9.9).",
        "update.project_only": "bob update: atualizando o projeto para v9.9.9.",
        "update.upgrading": "bob update: atualizando de v1.0.0 para v9.9.9.",
        "update.api_failed": "versão: não consegui ler a última release (S). Tente de novo.",
        "update.bad_response": "resposta inválida",
        "update.url_not_allowed": (
            "versão: BOB_RELEASES_URL=U não é permitida. "
            "Use https://, ou http:// só em 127.0.0.1 ou localhost."
        ),
        "update.tmp_failed": "download: não consegui criar uma pasta temporária (D).",
        "update.download_failed": "download: U falhou (S). Confira a rede e tente de novo.",
        "update.download_missing": (
            "download: a release v9.9.9 está incompleta (A ausente). Abra uma issue."
        ),
        "update.integrity": (
            "integridade: o sha256 de F não confere. Nada foi instalado. Tente de novo."
        ),
        "update.install_failed": "instalar: não consegui rodar o sh (D).",
    },
}


class _Body:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> _Body:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._payload


class _Net:
    def __init__(self) -> None:
        self.routes: dict[str, list[bytes | BaseException]] = {}
        self.calls: list[tuple[str, dict[str, str], float]] = []

    def urlopen(self, request: urllib.request.Request, timeout: float) -> _Body:
        self.calls.append((request.full_url, dict(request.header_items()), timeout))
        pending = self.routes.get(request.full_url)
        if not pending:
            pytest.fail(request.full_url)
        item = pending.pop(0)
        if isinstance(item, BaseException):
            raise item
        return _Body(item)


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture(autouse=True)
def _isolated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, sleeps: list[float]
) -> None:
    monkeypatch.setenv("BOB_HOME", str(tmp_path / "bob-home"))
    monkeypatch.delenv("BOB_RELEASES_URL", raising=False)
    monkeypatch.delenv("BOB_LANG", raising=False)
    monkeypatch.delenv("BOB_VERSION", raising=False)
    gitconfig = tmp_path / "gitconfig"
    gitconfig.write_bytes(b"")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("UPD_LOG", str(tmp_path / "upd.log"))
    monkeypatch.setattr(update.time, "sleep", sleeps.append)
    temporary = tmp_path / "t"
    temporary.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temporary))


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "proj"
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


@pytest.fixture
def net(monkeypatch: pytest.MonkeyPatch) -> _Net:
    double = _Net()
    monkeypatch.setattr(update.urllib.request, "urlopen", double.urlopen)
    return double


def _version(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    def fake(name: str) -> str:
        if name != "bob-quality":
            pytest.fail(name)
        return value

    monkeypatch.setattr(update.importlib.metadata, "version", fake)


def _skills(project: Path, version: str | None, skip: tuple[str, ...] = ()) -> None:
    if version is None:
        return
    for name in install_skills.manifest_skill_names():
        if name in skip:
            continue
        folder = project / ".agents" / "skills" / name
        folder.mkdir(parents=True)
        (folder / ".bob-version").write_text(f"{version}\n")


def _sums(script: bytes) -> bytes:
    text = (
        "0" * 64
        + "  bob_quality-1.2.3-py3-none-any.whl\n"
        + hashlib.sha256(script).hexdigest()
        + "  install.sh\n"
    )
    return text.encode()


def _latest(tag: str = "v1.2.3") -> bytes:
    return json.dumps({"tag_name": tag, "prerelease": False}).encode()


def _logged(tmp_path: Path) -> list[str]:
    return (tmp_path / "upd.log").read_text().rstrip("\n").split("|")


def _tree(root: Path) -> tuple[tuple[str, bytes], ...]:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rows.append((path.relative_to(root).as_posix(), path.read_bytes()))
    return tuple(rows)


def _http(url: str, code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, code, "x", {}, None)


def _release(net: _Net, sums: bytes | None = None) -> None:
    net.routes[API] = [_latest()]
    net.routes[DL + "install.sh"] = [BODY]
    net.routes[DL + "SHA256SUMS"] = [_sums(BODY) if sums is None else sums]


def _no_space(*_args: object, **_kwargs: object) -> None:
    raise OSError(28, "no space")


@pytest.mark.parametrize(
    ("pkg", "skills"),
    [("1.2.3", "1.2.3"), ("1.2.4", "1.2.4")],
    ids=("same", "newer"),
)
def test_up_to_date_prints_and_changes_nothing(
    project: Path,
    net: _Net,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    pkg: str,
    skills: str,
) -> None:
    _version(monkeypatch, pkg)
    _skills(project, skills)
    net.routes[API] = [_latest()]
    before = _tree(project)
    assert update.run_update(project, "en") == 0
    out, _err = capsys.readouterr()
    assert out == "bob update: already on the newest release (v1.2.3).\n"
    assert net.calls == [(API, ACCEPT, 30)]
    assert _tree(project) == before
    assert not (tmp_path / "upd.log").exists()


@pytest.mark.parametrize(
    ("skills", "skip"),
    [("1.2.2", ()), (None, ()), ("1.2.3", ("harden",))],
    ids=("old", "none", "partial"),
)
def test_old_project_runs_setup_without_download(
    project: Path,
    net: _Net,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    skills: str | None,
    skip: tuple[str, ...],
) -> None:
    _version(monkeypatch, "1.2.3")
    _skills(project, skills, skip)
    net.routes[API] = [_latest()]
    seen: list[tuple[Path, str]] = []

    def fake(path: Path, lang: str) -> int:
        seen.append((path, lang))
        return 7

    monkeypatch.setattr(update.setup_cmd, "run_setup", fake)
    assert update.run_update(project, "en") == 7
    out, _err = capsys.readouterr()
    assert out == "bob update: updating the project to v1.2.3.\n"
    assert seen == [(project.resolve(), "en")]
    assert net.calls == [(API, ACCEPT, 30)]


@pytest.mark.parametrize(
    ("lang", "line"),
    [
        ("en", "bob update: updating from v1.2.2 to v1.2.3.\n"),
        ("pt-BR", "bob update: atualizando de v1.2.2 para v1.2.3.\n"),
    ],
    ids=("en", "pt-BR"),
)
def test_new_release_downloads_checks_and_runs_install_sh(
    project: Path,
    net: _Net,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    lang: str,
    line: str,
) -> None:
    _version(monkeypatch, "1.2.2")
    _release(net)
    assert update.run_update(project, lang) == 0
    out, _err = capsys.readouterr()
    assert out == line
    assert net.calls == [
        (API, ACCEPT, 30),
        (DL + "install.sh", {}, 30),
        (DL + "SHA256SUMS", {}, 30),
    ]
    logged = _logged(tmp_path)
    assert logged[1:] == [f"--lang {lang}", "v1.2.3", str(project.resolve()), "", ""]
    script = Path(logged[0])
    assert script.name == "install.sh"
    assert script.parent.name.startswith("bob-update.")
    assert script.parent.parent == tmp_path / "t"
    assert list((tmp_path / "t").iterdir()) == []


def test_install_sh_exit_code_is_returned(
    project: Path,
    net: _Net,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _version(monkeypatch, "1.2.2")
    monkeypatch.setenv("UPD_RC", "3")
    _release(net)
    assert update.run_update(project, "en") == 3


def test_install_keeps_the_environment_and_pins_the_tag(
    project: Path,
    net: _Net,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _version(monkeypatch, "1.2.2")
    monkeypatch.setenv("FOO", "bar")
    monkeypatch.setenv("BOB_RELEASES_URL", "http://127.0.0.1:9/")
    api = "http://127.0.0.1:9/api/releases/latest"
    base = "http://127.0.0.1:9/download/v1.2.3/"
    net.routes[api] = [_latest()]
    net.routes[base + "install.sh"] = [BODY]
    net.routes[base + "SHA256SUMS"] = [_sums(BODY)]
    assert update.run_update(project, "en") == 0
    assert _logged(tmp_path)[2:] == [
        "v1.2.3",
        str(project.resolve()),
        "bar",
        "http://127.0.0.1:9/",
    ]
    assert [call[0] for call in net.calls] == [
        api,
        base + "install.sh",
        base + "SHA256SUMS",
    ]


@pytest.mark.parametrize("value", ["ftp://x", "http://example.com", "http://127.0.0.2/"])
def test_releases_url_rejects(
    project: Path,
    net: _Net,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("BOB_RELEASES_URL", value)
    assert update.run_update(project, "en") == 4
    _out, err = capsys.readouterr()
    reason = msg("update.url_not_allowed", url=value.removesuffix("/"))
    assert err == t("en", "update.error", reason=reason) + "\n"
    assert net.calls == []


@pytest.mark.parametrize(
    ("value", "api"),
    [
        ("https://m.example/", "https://m.example/api/releases/latest"),
        ("http://localhost", "http://localhost/api/releases/latest"),
        ("http://127.0.0.1:8//", "http://127.0.0.1:8//api/releases/latest"),
    ],
)
def test_releases_url_builds_the_urls(
    project: Path,
    net: _Net,
    monkeypatch: pytest.MonkeyPatch,
    value: str,
    api: str,
) -> None:
    monkeypatch.setenv("BOB_RELEASES_URL", value)
    _version(monkeypatch, "1.2.3")
    _skills(project, "1.2.3")
    net.routes[api] = [_latest()]
    assert update.run_update(project, "en") == 0
    assert net.calls[0][0] == api


@pytest.mark.parametrize(
    ("items", "status"),
    [
        ([_http(API, 404)], "HTTP 404"),
        ([_http(API, 429)], "HTTP 429"),
        ([_http(API, 503), _http(API, 503), _http(API, 503)], "HTTP 503"),
        (
            [urllib.error.URLError(ConnectionRefusedError()) for _item in range(3)],
            "ConnectionRefusedError",
        ),
        ([TimeoutError(), TimeoutError(), TimeoutError()], "TimeoutError"),
    ],
    ids=("404", "429", "503", "refused", "timeout"),
)
def test_api_errors_exit_4(
    project: Path,
    net: _Net,
    capsys: pytest.CaptureFixture[str],
    sleeps: list[float],
    items: list[BaseException],
    status: str,
) -> None:
    net.routes[API] = list(items)
    assert update.run_update(project, "en") == 4
    _out, err = capsys.readouterr()
    assert err == (
        f"bob update: versão: could not read the latest release ({status}). Try again.\n"
    )
    assert len(net.calls) == len(items)
    assert sleeps == [1.0] * (len(items) - 1)


@pytest.mark.parametrize(
    "body",
    [
        b"{}",
        b"[]",
        b"not json",
        b'{"tag_name": "1.2.3"}',
        b'{"tag_name": "v1.2"}',
        b'{"tag_name": 5}',
        b'{"tag_name": "v1.2.3-rc1"}',
    ],
)
def test_bad_tag_is_an_invalid_response(
    project: Path,
    net: _Net,
    capsys: pytest.CaptureFixture[str],
    body: bytes,
) -> None:
    net.routes[API] = [body]
    assert update.run_update(project, "en") == 4
    _out, err = capsys.readouterr()
    assert err == (
        "bob update: versão: could not read the latest release (invalid response). "
        "Try again.\n"
    )


def test_retry_then_success(
    project: Path,
    net: _Net,
    monkeypatch: pytest.MonkeyPatch,
    sleeps: list[float],
) -> None:
    _version(monkeypatch, "1.2.3")
    _skills(project, "1.2.3")
    net.routes[API] = [_http(API, 503), _latest()]
    assert update.run_update(project, "en") == 0
    assert len(net.calls) == 2
    assert sleeps == [1.0]


@pytest.mark.parametrize(
    ("case", "stderr"),
    [
        (
            "script_404",
            "bob update: download: release v1.2.3 is incomplete "
            "(install.sh missing). Open an issue.\n",
        ),
        (
            "sums_404",
            "bob update: download: release v1.2.3 is incomplete "
            "(SHA256SUMS missing). Open an issue.\n",
        ),
        (
            "script_500",
            f"bob update: download: {DL}install.sh failed (HTTP 500). "
            "Check the network and try again.\n",
        ),
    ],
    ids=("script_404", "sums_404", "script_500"),
)
def test_download_errors(
    project: Path,
    net: _Net,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
    stderr: str,
) -> None:
    _version(monkeypatch, "1.2.2")
    script = DL + "install.sh"
    sums = DL + "SHA256SUMS"
    net.routes[API] = [_latest()]
    if case == "script_404":
        net.routes[script] = [_http(script, 404)]
    elif case == "sums_404":
        net.routes[script] = [BODY]
        net.routes[sums] = [_http(sums, 404)]
    else:
        net.routes[script] = [_http(script, 500), _http(script, 500), _http(script, 500)]
    assert update.run_update(project, "en") == 4
    _out, err = capsys.readouterr()
    assert err == stderr
    assert not (tmp_path / "upd.log").exists()
    assert list((tmp_path / "t").iterdir()) == []


def _bad_sums(kind: str) -> bytes:
    wheel = "0" * 64 + "  bob_quality-1.2.3-py3-none-any.whl\n"
    if kind == "absent":
        return wheel.encode()
    digest = hashlib.sha256(b"x" if kind == "wrong" else BODY).hexdigest()
    if kind == "upper":
        digest = digest.upper()
    return (wheel + digest + "  install.sh\n").encode()


@pytest.mark.parametrize("kind", ("wrong", "absent", "upper"), ids=("wrong", "absent", "upper"))
def test_integrity_failures(
    project: Path,
    net: _Net,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kind: str,
) -> None:
    _version(monkeypatch, "1.2.2")
    _release(net, _bad_sums(kind))
    assert update.run_update(project, "en") == 4
    _out, err = capsys.readouterr()
    assert err == (
        "bob update: integridade: the sha256 of install.sh does not match. "
        "Nothing was installed. Try again.\n"
    )
    assert not (tmp_path / "upd.log").exists()
    assert list((tmp_path / "t").iterdir()) == []


def test_sums_first_matching_line_wins(
    project: Path,
    net: _Net,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _version(monkeypatch, "1.2.2")
    _release(net, b"h1  wheel  install.sh\n" + _sums(BODY))
    assert update.run_update(project, "en") == 0
    assert (tmp_path / "upd.log").exists()


@pytest.mark.parametrize("case", ("mkdtemp", "write"), ids=("mkdtemp", "write"))
def test_tmp_failures(
    project: Path,
    net: _Net,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
) -> None:
    _version(monkeypatch, "1.2.2")
    _release(net)
    if case == "mkdtemp":
        monkeypatch.setattr(update.tempfile, "mkdtemp", _no_space)
    else:
        monkeypatch.setattr(Path, "write_bytes", _no_space)
    assert update.run_update(project, "en") == 4
    _out, err = capsys.readouterr()
    assert err == (
        "bob update: download: could not create a temporary folder ([Errno 28] no space).\n"
    )
    assert not (tmp_path / "upd.log").exists()


def test_sh_failure(
    project: Path,
    net: _Net,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _version(monkeypatch, "1.2.2")
    _release(net)
    real = update.subprocess.run

    def fake(argv, *a, **k):
        if argv and argv[0] == "sh":
            raise FileNotFoundError(2, "No such file or directory")
        return real(argv, *a, **k)

    monkeypatch.setattr(update.subprocess, "run", fake)
    assert update.run_update(project, "en") == 4
    _out, err = capsys.readouterr()
    assert err == (
        "bob update: instalar: could not run sh "
        "([Errno 2] No such file or directory).\n"
    )
    assert list((tmp_path / "t").iterdir()) == []


@pytest.mark.parametrize("case", ("not_root", "bob_home"), ids=("not_root", "bob_home"))
def test_project_errors(
    project: Path,
    net: _Net,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
) -> None:
    if case == "not_root":
        plain = tmp_path / "plain"
        plain.mkdir()
        code = update.run_update(plain, "en")
        reason = msg("setup.not_git_root", path=plain.resolve())
        expected = t("en", "update.error", reason=reason) + "\n"
    else:
        monkeypatch.setenv("BOB_HOME", "rel")
        code = update.run_update(project, "en")
        expected = (
            "bob update: projeto: BOB_HOME=rel must be absolute. Use an absolute path.\n"
        )
    assert code == 4
    _out, err = capsys.readouterr()
    assert err == expected
    assert net.calls == []


@pytest.mark.parametrize("case", ("ten", "dev"), ids=("ten", "dev"))
def test_version_compare_is_numeric(
    project: Path,
    net: _Net,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
) -> None:
    if case == "ten":
        _version(monkeypatch, "1.10.0")
        _skills(project, "1.10.0")
        net.routes[API] = [_latest("v1.9.9")]
        assert update.run_update(project, "en") == 0
        out, _err = capsys.readouterr()
        assert out == "bob update: already on the newest release (v1.9.9).\n"
        return
    _version(monkeypatch, "1.2.3.dev0")
    _release(net)
    assert update.run_update(project, "en") == 0
    out, _err = capsys.readouterr()
    assert out == "bob update: updating from v1.2.3.dev0 to v1.2.3.\n"
    assert (tmp_path / "upd.log").exists()


@pytest.mark.parametrize(
    ("lang", "second"),
    [
        ("en", "project skills: 1.2.3 (.agents/skills)"),
        ("pt-BR", "skills do projeto: 1.2.3 (.agents/skills)"),
    ],
)
def test_version_lines(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
    lang: str,
    second: str,
) -> None:
    _version(monkeypatch, "1.2.3")
    _skills(project, "1.2.3")
    assert update.version_lines(project, lang) == ["bob 1.2.3", second]


@pytest.mark.parametrize(
    ("where", "args", "out"),
    [
        (
            "proj",
            ("--version",),
            "bob 1.2.3\nproject skills: 1.2.3 (.agents/skills)\n",
        ),
        (
            "plain",
            ("--lang", "pt-BR", "--version"),
            "bob 1.2.3\nskills do projeto: não instaladas\n",
        ),
    ],
)
def test_cli_version_flag(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    where: str,
    args: tuple[str, ...],
    out: str,
) -> None:
    _version(monkeypatch, "1.2.3")
    if where == "proj":
        _skills(project, "1.2.3")
        folder = project
    else:
        folder = tmp_path / "plain"
        folder.mkdir()
    result = run_bob(folder, *args)
    assert result.returncode == 0
    assert result.stdout == out
    assert result.stderr == ""
    assert not (folder / ".bob").exists()


def test_cli_update_dispatches(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[Path, str]] = []

    def fake(path: Path, lang: str) -> int:
        seen.append((path, lang))
        return 5

    monkeypatch.setattr(cli, "run_update", fake)
    result = run_bob(project, "update", "--lang", "pt-BR")
    assert result.returncode == 5
    assert len(seen) == 1
    assert seen[0][0].resolve() == project.resolve()
    assert seen[0][1] == "pt-BR"


@pytest.mark.parametrize("lang", ("en", "pt-BR"))
@pytest.mark.parametrize("key", _MESSAGE_KEYS)
def test_update_messages_exist_in_both_languages(lang: str, key: str) -> None:
    rendered = t(
        lang,
        key,
        tag="v9.9.9",
        old="1.0.0",
        status="S",
        url="U",
        detail="D",
        asset="A",
        file="F",
        reason="R",
        version="V",
    )
    assert rendered == _EXPECTED[lang][key]


def test_constants_match_install_sh_and_gitleaks() -> None:
    install = (ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
    api = re.search(r"^DEFAULT_API='(.*)'$", install, re.MULTILINE)
    download = re.search(r"^DEFAULT_DOWNLOAD='(.*)'$", install, re.MULTILINE)
    assert api is not None
    assert download is not None
    assert update.DEFAULT_API == api.group(1)
    assert update.DEFAULT_DOWNLOAD == download.group(1)
    assert update._ALLOWED_URL.pattern == gitleaks._ALLOWED_URL.pattern
    assert update._RETRYABLE == gitleaks._RETRYABLE
    timing = (update._TIMEOUT_S, update._ATTEMPTS, update._PAUSE_S)
    pinned = (gitleaks._TIMEOUT_S, gitleaks._ATTEMPTS, gitleaks._PAUSE_S)
    assert timing == pinned == (30, 3, 1.0)


def test_http_500_is_retried(
    project: Path,
    net: _Net,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    sleeps: list[float],
) -> None:
    _version(monkeypatch, "1.2.2")
    _release(net)
    script = DL + "install.sh"
    net.routes[script] = [_http(script, 500), _http(script, 500), _http(script, 500)]
    assert update.run_update(project, "en") == 4
    _out, err = capsys.readouterr()
    assert err == (
        f"bob update: download: {script} failed (HTTP 500). "
        "Check the network and try again.\n"
    )
    script_calls = [url for url, _headers, _timeout in net.calls if url == script]
    assert len(script_calls) == 3
    assert sleeps == [1.0, 1.0]
    assert not (tmp_path / "upd.log").exists()
    assert list((tmp_path / "t").iterdir()) == []


def test_install_passes_check_false(
    project: Path,
    net: _Net,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _version(monkeypatch, "1.2.2")
    _release(net)
    real = update.subprocess.run
    kwargs: dict[str, object] = {}

    def fake(argv, *a, **k):
        nonlocal kwargs
        if argv and argv[0] == "sh":
            kwargs = k
            return subprocess.CompletedProcess(argv, 0)
        return real(argv, *a, **k)

    monkeypatch.setattr(update.subprocess, "run", fake)
    assert update.run_update(project, "en") == 0
    assert kwargs["check"] is False


def test_setup_context_receives_home_lang_version(
    project: Path,
    net: _Net,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _version(monkeypatch, "1.2.3")
    _skills(project, "1.2.3")
    net.routes[API] = [_latest()]
    real = update.setup_cmd.SetupContext
    seen: list[dict[str, object]] = []

    def wrapper(**fields):
        seen.append(fields)
        return real(**fields)

    monkeypatch.setattr(update.setup_cmd, "SetupContext", wrapper)
    assert update.run_update(project, "en") == 0
    fields = seen[0]
    assert fields["home"] == update.user_dirs.bob_home()
    assert fields["lang"] == "en"
    assert fields["version"] == "1.2.3"
    assert fields["project"] == project.resolve()


def test_version_default_is_suppressed() -> None:
    namespace = cli.build_parser().parse_args(["doctor"])
    assert "version" not in vars(namespace)
