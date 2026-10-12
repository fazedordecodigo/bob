"""Seam: `install_npm_dependencies` (o `bob doctor --install`) seguido de `npm_prefix`.

O `npm` falso no PATH decide a falha pelo `--prefix`, então o teste vale também
como root. O teste com `npm` real e `node_modules` 555 só roda sem root.
"""

from __future__ import annotations

import errno
import json
import os
import shutil
import stat
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from bob_quality.messages import Language
from bob_quality.npm_tools import install_npm_dependencies, npm_prefix

_MANIFEST = {"name": "bob-quality-tools", "private": True, "dependencies": {"c8": "12.0.0"}}


@pytest.fixture
def package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    package = tmp_path / "pkg"
    modules = package / "node_modules"
    modules.mkdir(parents=True)
    (package / "package.json").write_text(json.dumps(_MANIFEST))
    (modules / ".package-lock.json").write_text("{}")
    modules.chmod(0o555)
    monkeypatch.setattr("bob_quality.npm_tools._plugin_packages", lambda: [package])
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    yield package
    modules.chmod(0o755)


def _fake_npm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failures: dict[Path, str]) -> None:
    """`npm ci --prefix P` falha com o código de `failures[P]`; senão instala c8."""
    cases = "".join(
        f"  '{prefix}') printf 'npm error code {code}\\nnpm error path {prefix}\\n' >&2; exit 243 ;;\n"
        for prefix, code in failures.items()
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    npm = bin_dir / "npm"
    npm.write_text(
        "#!/bin/sh\n"
        '[ "$1 $2 $#" = "ci --prefix 3" ] || { echo "npm falso: argv inesperado: $*" >&2; exit 99; }\n'
        'case "$3" in\n'
        f"{cases}"
        "esac\n"
        'mkdir -p "$3/node_modules/c8"\n'
        'printf \'{"name":"c8","version":"12.0.0"}\' > "$3/node_modules/c8/package.json"\n'
    )
    npm.chmod(npm.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")


@pytest.mark.parametrize("code", ["EACCES", "EPERM", "EROFS"])
def test_denied_npm_ci_installs_in_the_user_cache_and_npm_prefix_finds_it(
    code: str,
    package: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _fake_npm(tmp_path, monkeypatch, {package: code})
    cache = tmp_path / "xdg" / "bob-quality"

    assert install_npm_dependencies("pt-BR") == 0

    assert capsys.readouterr().out == (
        f"npm ci --prefix {package} falhou com {code}; instalando no cache do usuário {cache}\n"
    )
    assert json.loads((cache / "package.json").read_text()) == _MANIFEST
    assert json.loads((cache / "node_modules" / "c8" / "package.json").read_text()) == {
        "name": "c8",
        "version": "12.0.0",
    }
    assert npm_prefix() == cache


def test_rerun_refreshes_an_existing_cache_with_the_package_js(
    package: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (package / "js").mkdir()
    (package / "js" / "flush-coverage.mjs").write_text("// atual\n")
    cache = tmp_path / "xdg" / "bob-quality"
    (cache / "js").mkdir(parents=True)
    (cache / "js" / "stale.mjs").write_text("// antigo\n")
    _fake_npm(tmp_path, monkeypatch, {package: "EACCES"})

    assert install_npm_dependencies("en") == 0

    assert sorted(path.name for path in (cache / "js").iterdir()) == ["flush-coverage.mjs"]
    assert (cache / "js" / "flush-coverage.mjs").read_text() == "// atual\n"


def test_cache_install_falls_back_to_home_cache_without_xdg(
    package: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    monkeypatch.delenv("XDG_CACHE_HOME")
    monkeypatch.setattr("bob_quality.npm_tools.Path.home", classmethod(lambda cls: home))
    _fake_npm(tmp_path, monkeypatch, {package: "EACCES"})

    assert install_npm_dependencies("en") == 0

    assert npm_prefix() == home / ".cache" / "bob-quality"


def test_exit_4_shows_the_cache_command_when_the_fallback_also_fails(
    package: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cache = tmp_path / "xdg" / "bob-quality"
    _fake_npm(tmp_path, monkeypatch, {package: "EACCES", cache: "ENOSPC"})

    assert install_npm_dependencies("en") == 4

    assert capsys.readouterr().out == (
        f"npm ci --prefix {package} failed with EACCES; installing in the user cache {cache}\n"
        f"npm ci --prefix {cache}\n"
        f"npm error code ENOSPC\n"
        f"npm error path {cache}\n"
    )


@pytest.mark.parametrize(
    ("lang", "fallback", "unavailable"),
    [
        ("en", "failed with EACCES; installing in the user cache", "could not prepare the user cache"),
        (
            "pt-BR",
            "falhou com EACCES; instalando no cache do usuário",
            "não foi possível preparar o cache do usuário",
        ),
    ],
)
def test_exit_4_names_the_cache_path_when_the_cache_cannot_be_created(
    lang: Language,
    fallback: str,
    unavailable: str,
    package: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "xdg").write_text("não é diretório")
    cache = tmp_path / "xdg" / "bob-quality"
    _fake_npm(tmp_path, monkeypatch, {package: "EACCES"})

    assert install_npm_dependencies(lang) == 4

    assert capsys.readouterr().out == (
        f"npm ci --prefix {package} {fallback} {cache}\n"
        f"{unavailable} {cache}: {os.strerror(errno.ENOTDIR)}\n"
    )


def test_other_npm_errors_exit_4_on_the_package_without_touching_the_cache(
    package: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _fake_npm(tmp_path, monkeypatch, {package: "ETARGET"})

    assert install_npm_dependencies("en") == 4

    assert capsys.readouterr().out == (
        f"npm ci --prefix {package}\n"
        f"npm error code ETARGET\n"
        f"npm error path {package}\n"
    )
    assert not (tmp_path / "xdg").exists()


def test_install_exits_4_naming_the_missing_plugin_manifest(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("bob_quality.npm_tools._plugin_packages", lambda: [])

    assert install_npm_dependencies("en") == 4

    assert capsys.readouterr().out == (
        "plugin package.json (bob-quality-tools) not found; c8 and vitest are pinned in it\n"
    )


def test_npm_prefix_ignores_a_cache_from_another_manifest(
    package: Path,
    tmp_path: Path,
) -> None:
    stale = tmp_path / "xdg" / "bob-quality"
    (stale / "node_modules").mkdir(parents=True)
    (stale / "package.json").write_text(json.dumps({**_MANIFEST, "dependencies": {"c8": "11.0.0"}}))

    assert npm_prefix() == package


@pytest.mark.skipif(shutil.which("npm") is None, reason="npm ausente")
@pytest.mark.skipif(os.geteuid() == 0, reason="root ignora o modo 555")
def test_real_npm_ci_with_node_modules_555_installs_in_the_user_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Um mutante sem `--prefix` faria o npm real rodar `npm ci` no node_modules do repo.
    if os.environ.get("MUTANT_UNDER_TEST"):
        pytest.skip("o npm real não participa da execução do mutmut")
    root = tmp_path / "root"
    tiny = root / "tiny"
    tiny.mkdir(parents=True)
    (tiny / "package.json").write_text(json.dumps({"name": "tiny", "version": "1.0.0"}))
    subprocess.run(["npm", "pack", "--silent"], cwd=tiny, check=True, capture_output=True)
    package = root / "pkg"
    package.mkdir()
    (package / "package.json").write_text(
        json.dumps({**_MANIFEST, "dependencies": {"tiny": "file:../tiny/tiny-1.0.0.tgz"}})
    )
    subprocess.run(["npm", "install", "--silent"], cwd=package, check=True, capture_output=True)
    monkeypatch.setattr("bob_quality.npm_tools._plugin_packages", lambda: [package])
    monkeypatch.setenv("XDG_CACHE_HOME", str(root))
    modules = package / "node_modules"
    modules.chmod(0o555)
    try:
        assert install_npm_dependencies("en") == 0
    finally:
        modules.chmod(0o755)

    cache = root / "bob-quality"
    assert json.loads((cache / "node_modules" / "tiny" / "package.json").read_text()) == {
        "name": "tiny",
        "version": "1.0.0",
    }
    assert npm_prefix() == cache


def _point_install_at(monkeypatch: pytest.MonkeyPatch, origin: Path, cache_home: Path) -> None:
    monkeypatch.setattr("bob_quality.npm_tools.__file__", str(origin))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_home))


def test_editable_checkout_installs_at_the_repository_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    package = repo / "src" / "bob_quality"
    package.mkdir(parents=True)
    (repo / "package.json").write_text(json.dumps(_MANIFEST))
    (package / "package.json").symlink_to("../../package.json")
    origin = package / "npm_tools.py"
    origin.write_text("")
    _point_install_at(monkeypatch, origin, tmp_path / "xdg")
    _fake_npm(tmp_path, monkeypatch, {})

    assert install_npm_dependencies("en") == 0

    assert not (package / "node_modules").exists()
    assert json.loads((repo / "node_modules" / "c8" / "package.json").read_text()) == {
        "name": "c8",
        "version": "12.0.0",
    }
    assert npm_prefix() == repo


def test_copied_manifest_installs_beside_the_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "site-packages" / "bob_quality"
    package.mkdir(parents=True)
    (package / "package.json").write_text(json.dumps(_MANIFEST))
    origin = package / "npm_tools.py"
    origin.write_text("")
    _point_install_at(monkeypatch, origin, tmp_path / "xdg")
    _fake_npm(tmp_path, monkeypatch, {})

    assert install_npm_dependencies("en") == 0

    assert json.loads((package / "node_modules" / "c8" / "package.json").read_text()) == {
        "name": "c8",
        "version": "12.0.0",
    }
    assert npm_prefix() == package
    assert not (tmp_path / "xdg").exists()
