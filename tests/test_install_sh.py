"""scripts/install.sh (CT2): comando único."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from bob_quality.npm_tools import node_range
from bob_quality.user_dirs import bob_home

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install.sh"

_ALLOWED = (
    "uname",
    "git",
    "python3",
    "node",
    "npm",
    "curl",
    "sha256sum",
    "shasum",
    "mktemp",
    "rm",
    "mkdir",
    "ln",
    "readlink",
    "cat",
    "awk",
    "grep",
    "sed",
    "tr",
    "id",
)
_SOURCE_NAMES = (
    "STEPS",
    "DEFAULT_API",
    "DEFAULT_DOWNLOAD",
    "CURL_OPTS",
    "PIP_OPTS",
    "NODE_FLOOR",
    "NODE_BELOW",
    "PYTHON_FLOOR",
)
_SOURCE = {
    "STEPS": (
        "projeto plataforma python node ferramentas versão "
        "download integridade pacote launcher setup"
    ),
    "DEFAULT_API": "https://api.github.com/repos/fazedordecodigo/bob/releases/latest",
    "DEFAULT_DOWNLOAD": "https://github.com/fazedordecodigo/bob/releases/download",
    "CURL_OPTS": "-fsSL --connect-timeout 15 --max-time 300 --retry 2",
    "PIP_OPTS": "--disable-pip-version-check --no-input",
    "NODE_FLOOR": "22.18.0",
    "NODE_BELOW": "23",
    "PYTHON_FLOOR": "3.10",
}
_CT2_STEPS = (
    "projeto",
    "plataforma",
    "python",
    "node",
    "ferramentas",
    "versão",
    "download",
    "integridade",
    "pacote",
    "launcher",
    "setup",
)
_PREREQ_CASES = (
    "not_root",
    "git_missing",
    "platform",
    "python_missing",
    "python_old",
    "python_venv",
    "node_missing",
    "node_out",
    "node_rc",
    "npm_missing",
    "curl_missing",
)
_PROGRESS = (
    "install: projeto: ok",
    "install: plataforma: ok",
    "install: python: ok",
    "install: node: ok",
    "install: ferramentas: ok",
    "install: versão: v9.9.9",
    "install: download: ok",
    "install: integridade: ok",
    "install: pacote: ok",
    "install: launcher: ok",
)


def _lines(text: str) -> list[str]:
    return text.splitlines()


def _script_text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _assign(name: str) -> str:
    match = re.search(rf"^{name}='(.*)'$", _script_text(), re.M)
    assert match is not None
    return match.group(1)


def _pins() -> dict[str, str]:
    floor = _assign("NODE_FLOOR")
    return {
        "py": _assign("PYTHON_FLOOR"),
        "node": floor,
        "below": _assign("NODE_BELOW"),
        "major": floor.split(".", 1)[0],
    }


def _msg(lang: str, key: str, **values: str) -> str:
    pins = _pins()
    values.setdefault("floor", pins["py"])
    values.setdefault("below", pins["below"])
    values.setdefault("major", pins["major"])
    templates = _TEMPLATES[lang]
    return templates[key].format(**values)


_EN_NODE_MISSING = (
    "install: node: node not found, required >={floor} <{below}. "
    "Install Node {floor} or newer from the {major} line."
)
_PT_NODE_MISSING = (
    "install: node: node não encontrado, exigido >={floor} <{below}. "
    "Instale o Node {floor} ou mais novo da linha {major}."
)
_EN_NODE_OUT = (
    "install: node: found {found}, required >={floor} <{below}. "
    "Install Node {floor} or newer from the {major} line."
)
_PT_NODE_OUT = (
    "install: node: encontrado {found}, exigido >={floor} <{below}. "
    "Instale o Node {floor} ou mais novo da linha {major}."
)
_TEMPLATES = {
    "en": {
        "usage_unknown": "install: usage: unknown argument {arg}. Run with --help.",
        "usage_lang_value": (
            "install: usage: --lang needs a value (en or pt-BR). Run with --help."
        ),
        "usage_lang_invalid": "install: usage: invalid language {value}. Use en or pt-BR.",
        "bob_home_relative": (
            "install: launcher: BOB_HOME={value} must be absolute. "
            "Use an absolute path."
        ),
        "git_missing": "install: projeto: git not found. Install git and run again.",
        "not_root": (
            "install: projeto: {dir} is not the root of a git repository. "
            "Run in the project root."
        ),
        "platform": (
            "install: plataforma: {os}/{arch} is not supported. "
            "Supported: Linux and macOS, x64 and arm64."
        ),
        "python_missing": (
            "install: python: python3 not found. Install Python {floor} or newer."
        ),
        "python_old": (
            "install: python: found {found}, required >={floor}. "
            "Install Python {floor} or newer."
        ),
        "python_venv": (
            "install: python: the venv module is not available. "
            "On Ubuntu, install the python3-venv package."
        ),
        "node_missing": _EN_NODE_MISSING,
        "node_out": _EN_NODE_OUT,
        "npm_missing": (
            "install: node: npm not found. Install npm with Node and run again."
        ),
        "tool_missing": (
            "install: ferramentas: {name} not found. Install {name} and run again."
        ),
        "url_not_allowed": (
            "install: versão: BOB_RELEASES_URL={url} is not allowed. "
            "Use https://, or http:// only on 127.0.0.1 or localhost."
        ),
        "tmp_failed": (
            "install: versão: could not create a temporary folder in {dir}. "
            "Check TMPDIR."
        ),
        "version_invalid": "install: versão: BOB_VERSION={value} is invalid. Use vX.Y.Z.",
        "api_failed": (
            "install: versão: could not read the latest release ({status}). "
            "Try again later."
        ),
        "download_failed": (
            "install: download: {url} failed ({status}). "
            "Check the network and try again."
        ),
        "download_missing": (
            "install: download: release {tag} is incomplete ({asset} missing). "
            "Open an issue."
        ),
        "integrity": (
            "install: integridade: the sha256 of {file} does not match. "
            "Nothing was installed. Try again."
        ),
        "pip_failed": (
            "install: pacote: pip failed. See the output above and try again."
        ),
        "launcher_failed": (
            "install: launcher: could not create {path} ({err}). Check the permissions."
        ),
        "launcher_warning": (
            "install: launcher: warning: {path} already exists and is not bob's; "
            "left as is."
        ),
    },
    "pt-BR": {
        "usage_unknown": "install: uso: argumento desconhecido {arg}. Rode com --help.",
        "usage_lang_value": (
            "install: uso: --lang precisa de um valor (en ou pt-BR). Rode com --help."
        ),
        "git_missing": "install: projeto: git não encontrado. Instale o git e rode de novo.",
        "bob_home_relative": (
            "install: launcher: BOB_HOME={value} precisa ser absoluto. "
            "Use um caminho absoluto."
        ),
        "not_root": (
            "install: projeto: {dir} não é a raiz de um repositório git. "
            "Rode na raiz do projeto."
        ),
        "platform": (
            "install: plataforma: {os}/{arch} não é suportada. "
            "Suportadas: Linux e macOS, x64 e arm64."
        ),
        "python_missing": (
            "install: python: python3 não encontrado. "
            "Instale um Python {floor} ou mais novo."
        ),
        "python_old": (
            "install: python: encontrado {found}, exigido >={floor}. "
            "Instale um Python {floor} ou mais novo."
        ),
        "python_venv": (
            "install: python: o módulo venv não está disponível. "
            "No Ubuntu, instale o pacote python3-venv."
        ),
        "node_missing": _PT_NODE_MISSING,
        "node_out": _PT_NODE_OUT,
        "npm_missing": (
            "install: node: npm não encontrado. "
            "Instale o npm junto com o Node e rode de novo."
        ),
        "tool_missing": (
            "install: ferramentas: {name} não encontrado. Instale {name} e rode de novo."
        ),
        "url_not_allowed": (
            "install: versão: BOB_RELEASES_URL={url} não é permitida. "
            "Use https://, ou http:// só em 127.0.0.1 ou localhost."
        ),
        "tmp_failed": (
            "install: versão: não consegui criar uma pasta temporária em {dir}. "
            "Confira o TMPDIR."
        ),
        "version_invalid": "install: versão: BOB_VERSION={value} inválida. Use vX.Y.Z.",
        "api_failed": (
            "install: versão: não consegui ler a última release ({status}). "
            "Tente de novo mais tarde."
        ),
        "download_failed": (
            "install: download: {url} falhou ({status}). Confira a rede e tente de novo."
        ),
        "download_missing": (
            "install: download: a release {tag} está incompleta ({asset} ausente). "
            "Abra uma issue."
        ),
        "integrity": (
            "install: integridade: o sha256 de {file} não confere. "
            "Nada foi instalado. Tente de novo."
        ),
        "pip_failed": "install: pacote: pip falhou. Veja a saída acima e tente de novo.",
        "launcher_failed": (
            "install: launcher: não consegui criar {path} ({err}). Confira as permissões."
        ),
        "launcher_warning": (
            "install: launcher: aviso: {path} já existe e não é do bob; ficou como está."
        ),
    },
}


def _help_lines(lang: str) -> list[str]:
    pins = _pins()
    needs = (
        f"git, python3 >={pins['py']} with venv, "
        f"node >={pins['node']} <{pins['below']} with npm, curl, sha256sum or shasum."
    )
    if lang == "pt-BR":
        precisa = (
            f"git, python3 >={pins['py']} com venv, "
            f"node >={pins['node']} <{pins['below']} com npm, curl, sha256sum ou shasum."
        )
        return [
            "Uso: sh install.sh [--lang en|pt-BR] [--help]",
            (
                "Instala o bob para este usuário e o prepara no projeto atual "
                "(rode na raiz do projeto git)."
            ),
            "Precisa de: " + precisa,
        ]
    return [
        "Usage: sh install.sh [--lang en|pt-BR] [--help]",
        (
            "Installs bob for this user and sets it up in the current project "
            "(run it in the git project root)."
        ),
        "Needs: " + needs,
    ]


def _wheel_record_hash(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return "sha256=" + encoded


def _fake_wheel(dest: Path, version: str) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    module = (
        "import os\n"
        "import sys\n"
        "\n"
        "\n"
        "def main():\n"
        "    log = os.environ['FAKE_BOB_LOG']\n"
        "    with open(log, 'a', encoding='utf-8') as handle:\n"
        "        handle.write(' '.join(sys.argv[1:]))\n"
        "        handle.write('\\n')\n"
        "        handle.write('stdin=' + repr(sys.stdin.read()))\n"
        "        handle.write('\\n')\n"
        "    return int(os.environ.get('FAKE_BOB_RC', '0'))\n"
    ).encode()
    dist = f"bob_quality-{version}.dist-info"
    metadata = (
        f"Metadata-Version: 2.1\nName: bob-quality\nVersion: {version}\n"
    ).encode()
    wheel_meta = (
        "Wheel-Version: 1.0\n"
        "Generator: bob-test\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n"
    ).encode()
    entry = b"[console_scripts]\nbob = fakebob:main\n"
    files = {
        "fakebob.py": module,
        f"{dist}/METADATA": metadata,
        f"{dist}/WHEEL": wheel_meta,
        f"{dist}/entry_points.txt": entry,
    }
    lines = [
        f"{name},{_wheel_record_hash(data)},{len(data)}"
        for name, data in sorted(files.items())
    ]
    lines.append(f"{dist}/RECORD,,")
    files[f"{dist}/RECORD"] = ("\n".join(lines) + "\n").encode()
    path = dest / f"bob_quality-{version}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return path


def _sums_text(directory: Path) -> str:
    rows: list[tuple[str, str]] = []
    for path in directory.iterdir():
        if path.name == "SHA256SUMS" or not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append((path.name, f"{digest}  {path.name}\n"))
    rows.sort(key=lambda item: item[0])
    return "".join(row for _name, row in rows)


def _mirror(
    tmp_path: Path,
    tags: tuple[str, ...] = ("v9.9.9",),
    latest: str = "v9.9.9",
    sums: str | None = None,
) -> Path:
    mirror = tmp_path / "mirror"
    release = mirror / "api" / "releases"
    release.mkdir(parents=True, exist_ok=True)
    payload = {
        "tag_name": latest,
        "name": latest,
        "draft": False,
        "prerelease": False,
    }
    (release / "latest").write_text(json.dumps(payload) + "\n", encoding="utf-8")
    for tag in tags:
        folder = mirror / "download" / tag
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SCRIPT, folder / "install.sh")
        _fake_wheel(folder, tag[1:])
        text = _sums_text(folder) if sums is None else sums
        (folder / "SHA256SUMS").write_text(text, encoding="utf-8")
    latest_dir = mirror / "latest" / "download"
    latest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SCRIPT, latest_dir / "install.sh")
    return mirror


@pytest.fixture
def server(tmp_path: Path):
    mirror = tmp_path / "mirror"
    mirror.mkdir(parents=True, exist_ok=True)
    seen: list[tuple[str, str, int]] = []

    class Handler(SimpleHTTPRequestHandler):
        recorded = seen

        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=str(mirror), **kwargs)

        def log_message(self, format: str, *args: object) -> None:
            return

        def log_request(self, code: object = "-", size: object = "-") -> None:
            if isinstance(code, int):
                status = int(code)
            else:
                status = int(str(code))
            path = self.path.split("?", 1)[0]
            self.recorded.append((self.command, path, status))

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[:2]
    try:
        yield f"http://{host}:{port}", seen
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _write_stub(directory: Path, name: str, body: str) -> None:
    path = directory / name
    if path.is_symlink() or path.exists():
        path.unlink()
    if not body.endswith("\n"):
        body = body + "\n"
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _toolbox(
    tmp_path: Path,
    drop: tuple[str, ...] = (),
    stubs: dict[str, str] | None = None,
) -> Path:
    given = {} if stubs is None else stubs
    tools = tmp_path / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    skipped = {"node", "npm", "python3", *drop}
    for name in _ALLOWED:
        if name in skipped or name in given:
            continue
        found = shutil.which(name)
        if found:
            (tools / name).symlink_to(found)
    if "python3" not in drop and "python3" not in given:
        (tools / "python3").symlink_to(sys._base_executable)
    if "node" not in drop and "node" not in given:
        _write_stub(tools, "node", "#!/bin/sh\nprintf '%s\\n' 'v" + _assign("NODE_FLOOR") + "'\n")
    if "npm" not in drop and "npm" not in given:
        _write_stub(tools, "npm", "#!/bin/sh\nprintf '%s\\n' '10.0.0'\n")
    for name, body in given.items():
        _write_stub(tools, name, body)
    return tools


def _run(
    project: Path,
    env_extra: dict[str, str],
    args: tuple[str, ...] = (),
    path: str | None = None,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[str]:
    base = Path(tempfile.mkdtemp(prefix="bob-install-"))
    home = base / "home"
    temp = base / "t"
    home.mkdir()
    temp.mkdir()
    env = {
        "HOME": str(home),
        "TMPDIR": str(temp),
        "PATH": path if path is not None else str(_toolbox(base)),
        "LANG": "C.UTF-8",
        **env_extra,
    }
    result = subprocess.run(
        ["/bin/sh", str(SCRIPT), *args],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        input=stdin,
        check=False,
    )
    result.home = Path(env["HOME"])  # type: ignore[attr-defined]
    result.tmpdir = Path(env["TMPDIR"])  # type: ignore[attr-defined]
    return result


def _empty(path: Path) -> bool:
    return list(path.iterdir()) == []


def _bob_root(home: Path) -> Path:
    return home / ".local" / "share" / "bob-quality"


@pytest.fixture
def git_project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    project.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=project, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=project, check=True)
    source = project / "src"
    source.mkdir()
    (source / "app.py").write_text("print(1)\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=project, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=project, check=True)
    return project.resolve()


def _digest(root: Path) -> dict[str, tuple[str, str | None, str | None]]:
    found: dict[str, tuple[str, str | None, str | None]] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        under_git = rel == ".git" or rel.startswith(".git/")
        under_hooks = rel == ".git/hooks" or rel.startswith(".git/hooks/")
        if under_git and not under_hooks:
            continue
        if path.is_symlink():
            found[rel] = ("symlink", None, os.readlink(path))
        elif path.is_dir():
            found[rel] = ("dir", None, None)
        else:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            found[rel] = ("file", digest, None)
    return found


def _resolve_fn() -> str:
    match = re.search(
        r"^resolve_bob_home\(\) \{\n.*?^\}$",
        _script_text(),
        re.M | re.S,
    )
    assert match is not None
    return match.group(0)


def _sh_home(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    full = {"HOME": "/h", **env}
    script = _resolve_fn() + "\nresolve_bob_home"
    return subprocess.run(
        ["env", "-i", *[f"{key}={value}" for key, value in full.items()], "sh", "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )


def _progress_before(case: str) -> list[str]:
    order = {
        "not_root": 0,
        "git_missing": 0,
        "platform": 1,
        "python_missing": 2,
        "python_old": 2,
        "python_venv": 2,
        "node_missing": 3,
        "node_out": 3,
        "node_rc": 3,
        "npm_missing": 3,
        "curl_missing": 4,
    }
    return [
        "install: projeto: ok",
        "install: plataforma: ok",
        "install: python: ok",
        "install: node: ok",
    ][: order[case]]


def _prereq_message(lang: str, case: str, project: Path) -> str:
    pins = _pins()
    node_floor = {"floor": pins["node"], "below": pins["below"], "major": pins["major"]}
    if case == "not_root":
        here = subprocess.check_output(["pwd", "-P"], cwd=project / "src", text=True).strip()
        return _msg(lang, "not_root", dir=here)
    if case == "git_missing":
        return _msg(lang, "git_missing")
    if case == "platform":
        return _msg(lang, "platform", os="FreeBSD", arch="x86_64")
    if case == "python_missing":
        return _msg(lang, "python_missing")
    if case == "python_old":
        return _msg(lang, "python_old", found="3.9.18")
    if case == "python_venv":
        return _msg(lang, "python_venv")
    if case == "node_missing":
        return _msg(lang, "node_missing", **node_floor)
    if case == "node_out":
        return _msg(lang, "node_out", found="v20.0.0", **node_floor)
    if case == "node_rc":
        return _msg(lang, "node_out", found="v22.18.0-rc.1", **node_floor)
    if case == "npm_missing":
        return _msg(lang, "npm_missing")
    return _msg(lang, "tool_missing", name="curl")


def _prereq_run(
    case: str,
    project: Path,
    lang: str,
) -> subprocess.CompletedProcess[str]:
    extra = {"BOB_LANG": lang} if lang == "pt-BR" else {}
    cwd = project
    drop: tuple[str, ...] = ()
    stubs: dict[str, str] = {}
    if case == "not_root":
        cwd = project / "src"
    elif case == "git_missing":
        drop = ("git",)
    elif case == "platform":
        stubs["uname"] = (
            "#!/bin/sh\n"
            "case \"${1-}\" in\n"
            "  -s) printf '%s\\n' FreeBSD ;;\n"
            "  -m) printf '%s\\n' x86_64 ;;\n"
            "esac\n"
            "exit 0\n"
        )
    elif case == "python_missing":
        drop = ("python3",)
    elif case == "python_old":
        stubs["python3"] = "#!/bin/sh\nprintf '%s\\n' '3.9.18'\nexit 0\n"
    elif case == "python_venv":
        stubs["python3"] = (
            "#!/bin/sh\n"
            "case \"${2-}\" in\n"
            "  *version_info*) printf '%s\\n' '3.12.0'; exit 0 ;;\n"
            "esac\n"
            "exit 1\n"
        )
    elif case == "node_missing":
        drop = ("node",)
    elif case == "node_out":
        stubs["node"] = "#!/bin/sh\nprintf '%s\\n' 'v20.0.0'\n"
    elif case == "node_rc":
        stubs["node"] = "#!/bin/sh\nprintf '%s\\n' 'v22.18.0-rc.1'\n"
    elif case == "npm_missing":
        drop = ("npm",)
    elif case == "curl_missing":
        drop = ("curl",)
    base = Path(tempfile.mkdtemp(prefix="bob-prereq-"))
    return _run(cwd, extra, path=str(_toolbox(base, drop=drop, stubs=stubs)))


def _assert_install_stdout(stdout: str, version_line: str = "install: versão: v9.9.9") -> None:
    expected = [
        "install: projeto: ok",
        "install: plataforma: ok",
        "install: python: ok",
        "install: node: ok",
        "install: ferramentas: ok",
        version_line,
        "install: download: ok",
        "install: integridade: ok",
        "install: pacote: ok",
        "install: launcher: ok",
    ]
    lines = _lines(stdout)
    progress = [line for line in lines if line.startswith("install:")]
    assert progress == expected
    integ = lines.index("install: integridade: ok")
    pack = lines.index("install: pacote: ok")
    for index, line in enumerate(lines):
        if line.startswith("install:"):
            continue
        assert integ < index < pack


def _assert_layout(home: Path, version: str, wheel: Path) -> None:
    root = _bob_root(home)
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert (root / "versions" / version / "venv" / "bin" / "python").is_file()
    assert (root / "versions" / version / ".complete").read_bytes() == (digest + "\n").encode()
    assert os.readlink(root / "current") == f"versions/{version}"
    assert os.readlink(root / "bin" / "bob") == "../current/venv/bin/bob"
    assert os.readlink(home / ".local" / "bin" / "bob") == str(root / "bin" / "bob")
    assert not (root / "current.tmp").exists()


def _log_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_install_sh_is_posix() -> None:
    checked = subprocess.run(["sh", "-n", str(SCRIPT)], check=False)
    assert checked.returncode == 0
    dash = shutil.which("dash")
    if dash:
        checked = subprocess.run([dash, "-n", str(SCRIPT)], check=False)
        assert checked.returncode == 0


def test_install_sh_shape() -> None:
    text = _script_text()
    assert text.startswith("#!/bin/sh\n")
    assert "\r" not in text
    assert text.endswith("\n")
    assert _lines(text)[-1] == 'main "$@"'
    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    repo = Path(top.stdout.strip() or str(ROOT))
    listed = subprocess.run(
        ["git", "ls-files", "-s", "scripts/install.sh"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert listed.stdout.startswith("100755")


def test_single_source_lines() -> None:
    text = _script_text()
    for name in _SOURCE_NAMES:
        found = re.findall(rf"^{name}='(.*)'$", text, re.M)
        assert found == [_SOURCE[name]]
    assert _SOURCE["STEPS"].split() == list(_CT2_STEPS)
    once = (
        "DEFAULT_API",
        "DEFAULT_DOWNLOAD",
        "CURL_OPTS",
        "PIP_OPTS",
        "NODE_FLOOR",
        "PYTHON_FLOOR",
    )
    for name in once:
        assert text.count(_SOURCE[name]) == 1


def test_node_and_python_ranges_match_the_package() -> None:
    span = node_range()
    assert _assign("NODE_FLOOR") == ".".join(map(str, span.floor))
    assert _assign("NODE_BELOW") == str(span.below_major)
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert ">=" + _assign("PYTHON_FLOOR") == project["project"]["requires-python"]


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"XDG_DATA_HOME": "/x"},
        {"XDG_DATA_HOME": "/x/"},
        {"XDG_DATA_HOME": "rel"},
        {"BOB_HOME": "/b"},
        {"BOB_HOME": "/b/"},
        {"XDG_DATA_HOME": "/x", "BOB_HOME": "/b"},
    ],
)
def test_bob_home_matches_user_dirs(env: dict[str, str]) -> None:
    result = _sh_home(env)
    assert result.returncode == 0, result.stderr
    assert not result.stdout.endswith("\n")
    assert result.stdout == str(bob_home({"HOME": "/h", **env}).root)


def test_relative_bob_home_matches_user_dirs() -> None:
    result = _sh_home({"BOB_HOME": "rel"})
    assert result.returncode == 1
    assert result.stdout == ""
    with pytest.raises(ValueError):
        bob_home({"HOME": "/h", "BOB_HOME": "rel"})


@pytest.mark.parametrize(
    ("args", "lang"),
    [(("--help",), "en"), (("--lang", "pt-BR", "--help"), "pt-BR")],
)
def test_help_in_both_languages(tmp_path: Path, args: tuple[str, ...], lang: str) -> None:
    result = _run(tmp_path, {}, args=args)
    assert result.returncode == 0
    assert result.stdout == "\n".join(_help_lines(lang)) + "\n"
    assert result.stderr == ""
    assert _empty(result.home)  # type: ignore[attr-defined]
    assert _empty(result.tmpdir)  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("args", "extra", "expected"),
    [
        (("--foo",), {}, ("en", "usage_unknown", {"arg": "--foo"})),
        (
            ("--lang", "pt-BR", "--foo"),
            {},
            ("pt-BR", "usage_unknown", {"arg": "--foo"}),
        ),
        (("--lang",), {}, ("en", "usage_lang_value", {})),
        (("--lang", "xx"), {}, ("en", "usage_lang_invalid", {"value": "xx"})),
        ((), {"BOB_LANG": "xx"}, ("en", "usage_lang_invalid", {"value": "xx"})),
    ],
)
def test_usage_errors_exit_4(
    tmp_path: Path,
    args: tuple[str, ...],
    extra: dict[str, str],
    expected: tuple[str, str, dict[str, str]],
) -> None:
    lang, key, values = expected
    result = _run(tmp_path, extra, args=args)
    assert result.returncode == 4
    assert result.stderr == _msg(lang, key, **values) + "\n"
    assert result.stdout == ""


def test_bob_version_is_offered_only_in_its_own_error(tmp_path: Path) -> None:
    messages: list[str] = []
    reads: list[str] = []
    markers = ("is invalid. Use vX.Y.Z.", "inválida. Use vX.Y.Z.")
    for line in _script_text().splitlines():
        if "BOB_VERSION" not in line:
            continue
        if any(marker in line for marker in markers):
            messages.append(line)
        else:
            reads.append(line)
    assert len(messages) == 2
    for line in reads:
        assert "install:" not in line
        assert re.search(r"\$\{?BOB_VERSION", line)
    for args in (("--help",), ("--lang", "pt-BR", "--help")):
        result = _run(tmp_path, {}, args=args)
        assert "BOB_VERSION" not in result.stdout
        assert "BOB_VERSION" not in result.stderr


def test_install_sh_never_mentions_sudo() -> None:
    assert "sudo" not in _script_text()


@pytest.mark.parametrize("lang", ["en", "pt-BR"])
@pytest.mark.parametrize("case", _PREREQ_CASES)
def test_failed_prerequisite_writes_nothing(
    git_project: Path,
    lang: str,
    case: str,
) -> None:
    before = _digest(git_project)
    result = _prereq_run(case, git_project, lang)
    assert result.returncode == 4
    assert result.stderr == _prereq_message(lang, case, git_project) + "\n"
    assert _lines(result.stdout) == _progress_before(case)
    assert _empty(result.home)  # type: ignore[attr-defined]
    assert _empty(result.tmpdir)  # type: ignore[attr-defined]
    assert _digest(git_project) == before


def test_missing_sha_tool(git_project: Path, tmp_path: Path) -> None:
    before = _digest(git_project)
    result = _run(
        git_project,
        {},
        path=str(_toolbox(tmp_path, drop=("sha256sum", "shasum"))),
    )
    assert result.returncode == 4
    assert result.stderr == _msg("en", "tool_missing", name="sha256sum") + "\n"
    assert _empty(result.home)  # type: ignore[attr-defined]
    assert _empty(result.tmpdir)  # type: ignore[attr-defined]
    assert _digest(git_project) == before


def test_full_install_via_the_mirror(
    git_project: Path,
    server: tuple[str, list[tuple[str, str, int]]],
    tmp_path: Path,
) -> None:
    base, requests = server
    _mirror(tmp_path)
    log = tmp_path / "bob.log"
    before = _digest(git_project)
    result = _run(
        git_project,
        {"BOB_RELEASES_URL": base + "/", "FAKE_BOB_LOG": str(log)},
    )
    assert result.returncode == 0, result.stderr
    _assert_install_stdout(result.stdout)
    assert _log_text(log) == "setup --lang en\nstdin=''\n"
    wheel = (
        tmp_path
        / "mirror"
        / "download"
        / "v9.9.9"
        / "bob_quality-9.9.9-py3-none-any.whl"
    )
    _assert_layout(result.home, "9.9.9", wheel)  # type: ignore[attr-defined]
    assert _empty(result.tmpdir)  # type: ignore[attr-defined]
    assert _digest(git_project) == before
    assert requests == [
        ("GET", "/api/releases/latest", 200),
        ("GET", "/download/v9.9.9/bob_quality-9.9.9-py3-none-any.whl", 200),
        ("GET", "/download/v9.9.9/SHA256SUMS", 200),
    ]


def test_lang_pt_br_reaches_bob_setup(
    git_project: Path,
    server: tuple[str, list[tuple[str, str, int]]],
    tmp_path: Path,
) -> None:
    base, _requests = server
    _mirror(tmp_path)
    log = tmp_path / "bob.log"
    result = _run(
        git_project,
        {"BOB_RELEASES_URL": base + "/", "FAKE_BOB_LOG": str(log)},
        args=("--lang", "pt-BR"),
    )
    assert result.returncode == 0, result.stderr
    assert _log_text(log) == "setup --lang pt-BR\nstdin=''\n"


def test_setup_exit_code_is_passed_through(
    git_project: Path,
    server: tuple[str, list[tuple[str, str, int]]],
    tmp_path: Path,
) -> None:
    base, _requests = server
    _mirror(tmp_path)
    result = _run(
        git_project,
        {
            "BOB_RELEASES_URL": base + "/",
            "FAKE_BOB_LOG": str(tmp_path / "bob.log"),
            "FAKE_BOB_RC": "4",
        },
    )
    assert result.returncode == 4


def test_second_run_reuses_the_venv(
    git_project: Path,
    server: tuple[str, list[tuple[str, str, int]]],
    tmp_path: Path,
) -> None:
    base, _requests = server
    _mirror(tmp_path)
    env = {"BOB_RELEASES_URL": base + "/", "FAKE_BOB_LOG": str(tmp_path / "bob.log")}
    first = _run(git_project, env)
    assert first.returncode == 0, first.stderr
    root = _bob_root(first.home)  # type: ignore[attr-defined]
    binary = root / "versions" / "9.9.9" / "venv" / "bin" / "python"
    marker = root / "versions" / "9.9.9" / ".complete"
    inode = binary.stat().st_ino
    modified = marker.stat().st_mtime_ns
    second = _run(git_project, {**env, "HOME": str(first.home)})  # type: ignore[attr-defined]
    assert second.returncode == 0, second.stderr
    assert binary.stat().st_ino == inode
    assert marker.stat().st_mtime_ns == modified
    assert "Successfully installed" not in second.stdout
    assert sorted(path.name for path in (root / "versions").iterdir()) == ["9.9.9"]


def _tamper_sums(directory: Path) -> str:
    text = _sums_text(directory)
    rows = []
    for line in text.splitlines():
        name = line.split("  ", 1)[1]
        if name.startswith("bob_quality-"):
            flipped = "0" if line[0] != "0" else "1"
            line = flipped + line[1:]
        rows.append(line)
    return "\n".join(rows) + "\n"


def test_tampered_wheel_exits_4_and_creates_no_version(
    git_project: Path,
    server: tuple[str, list[tuple[str, str, int]]],
    tmp_path: Path,
) -> None:
    base, _requests = server
    mirror = _mirror(tmp_path)
    folder = mirror / "download" / "v9.9.9"
    (folder / "SHA256SUMS").write_text(_tamper_sums(folder), encoding="utf-8")
    log = tmp_path / "bob.log"
    before = _digest(git_project)
    result = _run(git_project, {"BOB_RELEASES_URL": base + "/", "FAKE_BOB_LOG": str(log)})
    wheel = "bob_quality-9.9.9-py3-none-any.whl"
    assert result.returncode == 4
    assert result.stderr == _msg("en", "integrity", file=wheel) + "\n"
    assert not _bob_root(result.home).exists()  # type: ignore[attr-defined]
    assert not log.exists()
    assert _empty(result.tmpdir)  # type: ignore[attr-defined]
    assert _digest(git_project) == before


def test_missing_wheel_line_is_an_integrity_failure(
    git_project: Path,
    server: tuple[str, list[tuple[str, str, int]]],
    tmp_path: Path,
) -> None:
    base, _requests = server
    mirror = _mirror(tmp_path)
    folder = mirror / "download" / "v9.9.9"
    kept = "".join(
        line + "\n" for line in _sums_text(folder).splitlines() if line.endswith("install.sh")
    )
    (folder / "SHA256SUMS").write_text(kept, encoding="utf-8")
    log = tmp_path / "bob.log"
    result = _run(git_project, {"BOB_RELEASES_URL": base + "/", "FAKE_BOB_LOG": str(log)})
    wheel = "bob_quality-9.9.9-py3-none-any.whl"
    assert result.returncode == 4
    assert result.stderr == _msg("en", "integrity", file=wheel) + "\n"
    assert not _bob_root(result.home).exists()  # type: ignore[attr-defined]
    assert not log.exists()


def test_bob_version_pins_the_tag(
    git_project: Path,
    server: tuple[str, list[tuple[str, str, int]]],
    tmp_path: Path,
) -> None:
    base, requests = server
    _mirror(tmp_path, tags=("v9.9.8", "v9.9.9"), latest="v9.9.9")
    result = _run(
        git_project,
        {
            "BOB_RELEASES_URL": base + "/",
            "FAKE_BOB_LOG": str(tmp_path / "bob.log"),
            "BOB_VERSION": "v9.9.8",
        },
    )
    assert result.returncode == 0, result.stderr
    assert "install: versão: v9.9.8" in _lines(result.stdout)
    root = _bob_root(result.home)  # type: ignore[attr-defined]
    assert (root / "versions" / "9.9.8").is_dir()
    assert not any(path == "/api/releases/latest" for _method, path, _code in requests)


@pytest.mark.parametrize("value", ["9.9.9", "v9.9", "latest"])
def test_invalid_bob_version(git_project: Path, value: str) -> None:
    result = _run(git_project, {"BOB_VERSION": value})
    assert result.returncode == 4
    assert result.stderr == _msg("en", "version_invalid", value=value) + "\n"
    assert not _bob_root(result.home).exists()  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "url",
    ["http://example.com", "ftp://127.0.0.1", "http://127.0.0.1.example.com"],
)
def test_releases_url_must_be_https_or_loopback(git_project: Path, url: str) -> None:
    result = _run(git_project, {"BOB_RELEASES_URL": url})
    assert result.returncode == 4
    assert result.stderr == _msg("en", "url_not_allowed", url=url) + "\n"
    assert _empty(result.tmpdir)  # type: ignore[attr-defined]


def test_api_error_says_try_again_later(
    git_project: Path,
    server: tuple[str, list[tuple[str, str, int]]],
) -> None:
    base, _requests = server
    result = _run(git_project, {"BOB_RELEASES_URL": base})
    assert result.returncode == 4
    assert result.stderr == _msg("en", "api_failed", status="HTTP 404") + "\n"
    assert "BOB_VERSION" not in result.stderr


def test_unreachable_mirror(git_project: Path) -> None:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    result = _run(git_project, {"BOB_RELEASES_URL": f"http://127.0.0.1:{port}"})
    assert result.returncode == 4
    assert result.stderr == _msg("en", "api_failed", status="curl 7") + "\n"


def test_missing_asset_says_release_incomplete(
    git_project: Path,
    server: tuple[str, list[tuple[str, str, int]]],
    tmp_path: Path,
) -> None:
    base, _requests = server
    mirror = _mirror(tmp_path)
    wheel = mirror / "download" / "v9.9.9" / "bob_quality-9.9.9-py3-none-any.whl"
    wheel.unlink()
    result = _run(git_project, {"BOB_RELEASES_URL": base})
    assert result.returncode == 4
    assert result.stderr == _msg(
        "en",
        "download_missing",
        tag="v9.9.9",
        asset="bob_quality-9.9.9-py3-none-any.whl",
    ) + "\n"
    assert not _bob_root(result.home).exists()  # type: ignore[attr-defined]


def test_pip_failure_removes_the_version(
    git_project: Path,
    server: tuple[str, list[tuple[str, str, int]]],
    tmp_path: Path,
) -> None:
    base, _requests = server
    mirror = _mirror(tmp_path)
    folder = mirror / "download" / "v9.9.9"
    wheel = folder / "bob_quality-9.9.9-py3-none-any.whl"
    wheel.write_bytes(b"not a zip\n")
    (folder / "SHA256SUMS").write_text(_sums_text(folder), encoding="utf-8")
    result = _run(git_project, {"BOB_RELEASES_URL": base})
    assert result.returncode == 4
    assert _lines(result.stderr)[-1] == _msg("en", "pip_failed")
    root = _bob_root(result.home)  # type: ignore[attr-defined]
    assert not (root / "versions" / "9.9.9").exists()
    assert not (root / "current").exists()


def test_foreign_local_bin_bob_is_kept(
    git_project: Path,
    server: tuple[str, list[tuple[str, str, int]]],
    tmp_path: Path,
) -> None:
    base, _requests = server
    _mirror(tmp_path)
    home = tmp_path / "kept-home"
    launcher = home / ".local" / "bin" / "bob"
    launcher.parent.mkdir(parents=True)
    launcher.write_bytes(b"mine\n")
    result = _run(
        git_project,
        {
            "BOB_RELEASES_URL": base + "/",
            "FAKE_BOB_LOG": str(tmp_path / "bob.log"),
            "HOME": str(home),
        },
    )
    assert result.returncode == 0, result.stderr
    warning = _msg("en", "launcher_warning", path=str(launcher))
    assert warning in _lines(result.stdout)
    assert launcher.read_bytes() == b"mine\n"


def test_relative_bob_home_fails_before_writing(git_project: Path) -> None:
    result = _run(git_project, {"BOB_HOME": "rel"})
    assert result.returncode == 4
    assert result.stderr == _msg("en", "bob_home_relative", value="rel") + "\n"
    assert _empty(result.home)  # type: ignore[attr-defined]
    assert _empty(result.tmpdir)  # type: ignore[attr-defined]


def test_curl_pipe_sh_works(
    git_project: Path,
    server: tuple[str, list[tuple[str, str, int]]],
    tmp_path: Path,
) -> None:
    base, _requests = server
    _mirror(tmp_path)
    tools = _toolbox(tmp_path / "pipe-tools")
    shell = tools / "sh"
    if not shell.exists():
        shell.symlink_to("/bin/sh")
    home = tmp_path / "pipe-home"
    temp = tmp_path / "pipe-tmp"
    home.mkdir()
    temp.mkdir()
    log = tmp_path / "bob.log"
    result = subprocess.run(
        ["/bin/sh", "-c", 'curl -fsSL "$B/latest/download/install.sh" | sh'],
        cwd=git_project,
        env={
            "HOME": str(home),
            "TMPDIR": str(temp),
            "PATH": str(tools),
            "LANG": "C.UTF-8",
            "BOB_RELEASES_URL": base + "/",
            "FAKE_BOB_LOG": str(log),
            "B": base,
        },
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert _log_text(log) == "setup --lang en\nstdin=''\n"
