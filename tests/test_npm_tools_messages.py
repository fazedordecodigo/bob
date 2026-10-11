"""Mensagens e fallback do prefixo npm. Mata mutantes que só mudam o texto."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bob_quality.npm_tools import ToolError, installed_npm_version, npm_prefix


def test_npm_prefix_names_the_missing_plugin_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bob_quality.npm_tools._plugin_packages", lambda: [])
    with pytest.raises(ToolError) as caught:
        npm_prefix()
    message = str(caught.value)
    assert message.startswith("package.json do plugin (bob-quality-tools) não encontrado;")
    assert "c8 e vitest ficam fixados nele" in message


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


def test_missing_npm_package_message_keeps_the_prefix_and_the_hint(tmp_path: Path) -> None:
    with pytest.raises(ToolError) as caught:
        installed_npm_version(tmp_path, "c8")
    message = str(caught.value)
    assert message.startswith("dependências npm do plugin ausentes: ")
    assert "npm ci --prefix" in message or message.endswith("bob doctor --install")


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
