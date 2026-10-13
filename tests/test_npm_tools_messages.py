"""Mensagens e fallback do prefixo npm. Mata mutantes que só mudam o texto."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bob_quality.npm_tools import (
    ToolError,
    installed_npm_version,
    node_missing_message,
    npm_prefix,
    npm_setup_hint,
    user_npm_cache,
)
from helpers import in_both


def test_npm_prefix_names_the_missing_plugin_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bob_quality.npm_tools._plugin_packages", lambda: [])
    with pytest.raises(ToolError) as caught:
        npm_prefix()
    assert in_both(caught.value) == (
        "plugin package.json (bob-quality-tools) not found; c8 and vitest are pinned in it",
        "package.json do plugin (bob-quality-tools) não encontrado; "
        "c8 e vitest ficam fixados nele",
    )


@pytest.mark.parametrize("absent", ["node", "npx"])
def test_node_counts_as_missing_when_node_or_npx_is_absent(
    absent: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "bob_quality.npm_tools.shutil.which",
        lambda name: None if name == absent else f"/usr/bin/{name}",
    )
    assert in_both(node_missing_message()) == (
        "Node missing: install Node.js to measure TypeScript (c8 and vitest via npx)",
        "Node ausente: instale Node.js para medir TypeScript (c8 e vitest via npx)",
    )


def test_node_is_present_when_node_and_npx_are_on_the_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("bob_quality.npm_tools.shutil.which", lambda name: f"/usr/bin/{name}")
    assert node_missing_message() is None


def test_npm_prefix_uses_the_package_dir_when_nothing_is_installed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "package.json").write_text(json.dumps({"name": "bob-quality-tools"}))
    monkeypatch.setattr("bob_quality.npm_tools._plugin_packages", lambda: [package])
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "empty-cache"))
    assert npm_prefix() == package


def test_writable_directory_hint_is_npm_ci_on_that_path(tmp_path: Path) -> None:
    assert npm_setup_hint(tmp_path) == f"npm ci --prefix {tmp_path}"


def test_readonly_directory_hint_is_doctor_install(tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    blocked.chmod(0o555)
    try:
        assert npm_setup_hint(blocked) == "bob doctor --install"
    finally:
        blocked.chmod(0o755)


def test_user_npm_cache_honors_xdg_and_the_directory_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert user_npm_cache() == tmp_path / "bob-quality"


def test_user_npm_cache_defaults_to_home_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setattr(
        "bob_quality.npm_tools.Path.home",
        classmethod(lambda cls: tmp_path),
    )
    assert user_npm_cache() == tmp_path / ".cache" / "bob-quality"


def test_npm_prefix_prefers_a_ready_user_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "package.json").write_text(json.dumps({"name": "bob-quality-tools"}))
    cache_root = tmp_path / "cache"
    cache = cache_root / "bob-quality"
    (cache / "node_modules").mkdir(parents=True)
    (cache / "package.json").write_text(json.dumps({"name": "bob-quality-tools"}))
    monkeypatch.setattr("bob_quality.npm_tools._plugin_packages", lambda: [package])
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_root))
    assert npm_prefix() == cache


def _cache_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    manifest: dict[str, object],
    files: dict[str, str],
) -> tuple[Path, Path]:
    package = tmp_path / "pkg"
    package.mkdir()
    encoded = json.dumps(manifest)
    (package / "package.json").write_text(encoded)
    cache_root = tmp_path / "cache"
    cache = cache_root / "bob-quality"
    (cache / "node_modules").mkdir(parents=True)
    (cache / "package.json").write_text(encoded)
    for name, body in files.items():
        destination = cache / "node_modules" / name
        destination.mkdir()
        (destination / "package.json").write_text(body)
    monkeypatch.setattr("bob_quality.npm_tools._plugin_packages", lambda: [package])
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_root))
    return package, cache


@pytest.mark.parametrize(
    ("dependencies", "files", "winner"),
    [
        ({"c8": "12.0.0"}, {"c8": '{"name": "c8", "version": "12.0.0"}'}, "cache"),
        ({"c8": "12.0.0"}, {"c8": '{"name": "c8", "version": "11.0.0"}'}, "package"),
        ({"c8": "12.0.0"}, {}, "package"),
        (
            {"tiny": "file:../tiny/tiny-1.0.0.tgz"},
            {"tiny": '{"name": "tiny", "version": "1.0.0"}'},
            "cache",
        ),
        ({"c8": "12.0.0"}, {"c8": "[]"}, "package"),
    ],
)
def test_npm_prefix_takes_the_cache_only_when_installed_versions_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dependencies: dict[str, str],
    files: dict[str, str],
    winner: str,
) -> None:
    package, cache = _cache_pair(
        tmp_path,
        monkeypatch,
        {"name": "bob-quality-tools", "dependencies": dependencies},
        files,
    )
    assert npm_prefix() == {"cache": cache, "package": package}[winner]


def test_npm_prefix_reuses_the_cache_for_an_rc_spec_when_the_package_is_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _package, cache = _cache_pair(
        tmp_path,
        monkeypatch,
        {"name": "bob-quality-tools", "dependencies": {"c8": "12.0.0-rc.1"}},
        {"c8": '{"name": "c8", "version": "9.9.9"}'},
    )
    assert npm_prefix() == cache


def test_npm_prefix_rejects_a_cache_whose_dependencies_are_not_an_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package, _cache = _cache_pair(
        tmp_path,
        monkeypatch,
        {"name": "bob-quality-tools", "dependencies": []},
        {},
    )
    assert npm_prefix() == package


def test_missing_npm_package_message_keeps_the_prefix_and_the_hint(tmp_path: Path) -> None:
    with pytest.raises(ToolError) as caught:
        installed_npm_version(tmp_path, "c8")
    assert in_both(caught.value) == (
        f"plugin npm dependencies missing: npm ci --prefix {tmp_path}",
        f"dependências npm do plugin ausentes: npm ci --prefix {tmp_path}",
    )


def test_installed_npm_version_returns_the_declared_version(tmp_path: Path) -> None:
    pkg = tmp_path / "node_modules" / "c8"
    pkg.mkdir(parents=True)
    (pkg / "package.json").write_text(json.dumps({"name": "c8", "version": "12.0.0"}))
    assert installed_npm_version(tmp_path, "c8") == "12.0.0"


@pytest.mark.parametrize("body", ["{", "[]", "{}"])
def test_illegible_npm_version_names_the_package(tmp_path: Path, body: str) -> None:
    pkg = tmp_path / "node_modules" / "c8"
    pkg.mkdir(parents=True)
    (pkg / "package.json").write_text(body)
    with pytest.raises(ToolError) as caught:
        installed_npm_version(tmp_path, "c8")
    assert in_both(caught.value) == ("unreadable c8 version", "versão de c8 ilegível")
