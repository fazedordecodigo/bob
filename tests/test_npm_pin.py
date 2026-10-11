"""Versões npm fixadas do plugin (c8, jscpd e vitest), sem intervalo."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_c8_and_vitest_are_pinned_in_package_json_and_lock() -> None:
    package = json.loads((ROOT / "package.json").read_text())
    lock = json.loads((ROOT / "package-lock.json").read_text())
    dependencies = package["dependencies"]

    assert dependencies == {"c8": "12.0.0", "jscpd": "5.4.1", "vitest": "5.0.3"}
    assert lock["packages"]["node_modules/c8"]["version"] == "12.0.0"
    assert lock["packages"]["node_modules/jscpd"]["version"] == "5.4.1"
    assert lock["packages"]["node_modules/vitest"]["version"] == "5.0.3"
