"""Versões fixadas do plugin (pip/npm), sem intervalo."""

import ast
import importlib.metadata
import json
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

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


def test_every_library_bob_imports_is_an_exact_pin() -> None:
    """O grafo do ciclo importa grimp dentro de um `python -c`.

    Uma biblioteca importada no topo de um módulo, ou num código-fonte guardado numa constante
    de módulo, tem pin `==` no pyproject.toml.
    """
    pins = _exact_pins()
    owners = importlib.metadata.packages_distributions()
    pinned = {module: pins.get(owners[module][0]) for module in _third_party_imports()}
    assert pinned == {"grimp": "3.17", "importlinter": "2.15", "yaml": "6.0.3"}


def _exact_pins() -> dict[str, str]:
    """`{distribution: version}` do pyproject.toml em disco, sem reinstalar."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    return {
        name: version
        for name, sep, version in (
            spec.partition("==")
            for spec in project["project"]["dependencies"]
            if ";" not in spec
        )
        if sep
    }


def _third_party_imports() -> set[str]:
    names: set[str] = set()
    for path in (ROOT / "src" / "bob_quality").rglob("*.py"):
        if "node_modules" in path.parts:
            continue
        body = ast.parse(path.read_text()).body
        names |= _imports(body)
        names |= _imports_in_constants(body)
    return {name for name in names if name not in sys.stdlib_module_names and name != "bob_quality"}


def _imports_in_constants(body: list[ast.stmt]) -> set[str]:
    names: set[str] = set()
    for node in body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        source = node.value.value
        if isinstance(source, str):
            names |= _imports(_parsed_or_empty(source))
    return names


def _imports(body: list[ast.stmt]) -> set[str]:
    # Só o corpo. Função aninhada e `if` de módulo ficam de fora.
    names: set[str] = set()
    for node in body:
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".", 1)[0])
    return names


def _parsed_or_empty(source: str) -> list[ast.stmt]:
    try:
        return ast.parse(source).body
    except SyntaxError:
        return []
