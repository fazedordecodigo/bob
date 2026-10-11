"""Versões fixadas do plugin (pip/npm), sem intervalo."""

import importlib.metadata
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_npm_tools_are_pinned_in_package_json_and_lock() -> None:
    package = json.loads((ROOT / "package.json").read_text())
    lock = json.loads((ROOT / "package-lock.json").read_text())
    dependencies = package["dependencies"]

    assert dependencies == {
        "c8": "12.0.0",
        "dependency-cruiser": "18.5.0",
        "jscpd": "5.4.1",
        "vitest": "5.0.3",
    }
    assert lock["packages"]["node_modules/c8"]["version"] == "12.0.0"
    assert lock["packages"]["node_modules/dependency-cruiser"]["version"] == "18.5.0"
    assert lock["packages"]["node_modules/jscpd"]["version"] == "5.4.1"
    assert lock["packages"]["node_modules/vitest"]["version"] == "5.0.3"


def test_import_linter_and_mutmut_are_pinned_in_pyproject() -> None:
    text = (ROOT / "pyproject.toml").read_text()
    assert "import-linter==2.15" in text
    assert "import-linter>=" not in text
    assert "mutmut==3.8.0" in text
    assert "mutmut>=" not in text
    assert importlib.metadata.version("import-linter") == "2.15"
    assert importlib.metadata.version("mutmut") == "3.8.0"
