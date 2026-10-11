"""Mensagens e fallback do prefixo npm. Mata mutantes que só mudam o texto."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bob_quality.npm_tools import (
    ToolError,
    installed_npm_version,
    npm_prefix,
    npm_setup_hint,
    user_npm_cache,
)


def test_npm_prefix_names_the_missing_plugin_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bob_quality.npm_tools._plugin_packages", lambda: [])
    with pytest.raises(ToolError) as caught:
        npm_prefix()
    assert str(caught.value) == (
        "package.json do plugin (bob-quality-tools) não encontrado; "
        "c8 e vitest ficam fixados nele"
    )


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


def test_missing_npm_package_message_keeps_the_prefix_and_the_hint(tmp_path: Path) -> None:
    with pytest.raises(ToolError) as caught:
        installed_npm_version(tmp_path, "c8")
    assert str(caught.value) == (
        "dependências npm do plugin ausentes: " + f"npm ci --prefix {tmp_path}"
    )


def test_installed_npm_version_returns_the_declared_version(tmp_path: Path) -> None:
    pkg = tmp_path / "node_modules" / "c8"
    pkg.mkdir(parents=True)
    (pkg / "package.json").write_text(json.dumps({"name": "c8", "version": "12.0.0"}))
    assert installed_npm_version(tmp_path, "c8") == "12.0.0"


def test_illegible_npm_version_names_the_package(tmp_path: Path) -> None:
    pkg = tmp_path / "node_modules" / "c8"
    pkg.mkdir(parents=True)
    (pkg / "package.json").write_text("{")
    with pytest.raises(ToolError) as caught:
        installed_npm_version(tmp_path, "c8")
    message = str(caught.value)
    assert "c8" in message
    assert "ilegível" in message
