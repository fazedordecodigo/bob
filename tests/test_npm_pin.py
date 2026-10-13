"""Versões fixadas do plugin (pip/npm), sem intervalo."""

import ast
import importlib.metadata
import inspect
import json
import sys
from pathlib import Path

from bob_quality.doctor import unconditional_exact_pins

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def test_npm_tools_are_pinned_in_package_json_and_lock() -> None:
    pins = {
        "c8": "12.0.0",
        "dependency-cruiser": "18.5.0",
        "eslint": "9.39.5",
        "eslint-plugin-sonarjs": "2.0.4",
        "jscpd": "5.4.1",
        "vitest": "5.0.3",
    }
    root = json.loads((ROOT / "package.json").read_text())
    plugin = json.loads((ROOT / "src" / "bob_quality" / "package.json").read_text())
    assert root["dependencies"] == pins
    assert plugin["dependencies"] == pins

    lock = json.loads((ROOT / "package-lock.json").read_text())
    packages = lock["packages"]
    for name, version in pins.items():
        assert packages[f"node_modules/{name}"]["version"] == version


def test_import_linter_and_mutmut_are_pinned_in_pyproject() -> None:
    text = (ROOT / "pyproject.toml").read_text()
    assert "import-linter==2.15" in text
    assert "import-linter>=" not in text
    assert "mutmut==3.8.0" in text
    assert "mutmut>=" not in text
    assert importlib.metadata.version("import-linter") == "2.15"
    assert importlib.metadata.version("mutmut") == "3.8.0"


def test_top_level_imports_have_an_exact_pin() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    pins = unconditional_exact_pins(project["project"]["dependencies"])
    owners = _owner_by_module()
    pinned = {
        module: pins.get(owners[module]) for module in _top_level_third_party_imports()
    }
    assert pinned == {"grimp": "3.17", "importlinter": "2.15", "yaml": "6.0.3"}


def test_distribution_for_import_does_not_need_top_level_txt() -> None:
    grimp = importlib.metadata.distribution("grimp")
    importlinter = importlib.metadata.distribution("import-linter")
    assert grimp.read_text("top_level.txt") is None
    assert importlinter.read_text("top_level.txt") is None
    owners = _owner_by_module()
    assert owners["grimp"] == "grimp"
    assert owners["importlinter"] == "import-linter"
    assert owners["yaml"] == "PyYAML"


def test_mutmut_trampoline_is_not_a_product_import() -> None:
    body = ast.parse(
        "from mutmut.mutation.trampoline import wrap_in_trampoline as _mutmut_mutated, MutantDict\n"
        "import grimp\n"
        "import mutmut\n"
    ).body
    assert _top_level_imports(body) == {"grimp", "mutmut"}
    trampoline = ast.parse(
        "from mutmut.mutation.trampoline import wrap_in_trampoline as _mutmut_mutated, MutantDict\n"
    ).body
    assert _top_level_imports(trampoline) == set()


def _top_level_names(dist: importlib.metadata.Distribution) -> set[str]:
    declared = (dist.read_text("top_level.txt") or "").split()
    if declared:
        return set(declared)
    names: set[str] = set()
    for file in dist.files or []:
        name = file.parts[0] if len(file.parts) > 1 else inspect.getmodulename(file)
        if name and "." not in name:
            names.add(name)
    return names


def _owner_by_module() -> dict[str, str]:
    owners: dict[str, str] = {}
    for dist in importlib.metadata.distributions():
        for name in _top_level_names(dist):
            owners.setdefault(name, dist.metadata["Name"])
    return owners


def _top_level_third_party_imports() -> set[str]:
    names: set[str] = set()
    for path in (ROOT / "src" / "bob_quality").rglob("*.py"):
        if "node_modules" in path.parts:
            continue
        body = ast.parse(path.read_text()).body
        names |= _top_level_imports(body)
        names |= _imports_in_constants(body)
    return {name for name in names if name not in sys.stdlib_module_names and name != "bob_quality"}


def _imports_in_constants(body: list[ast.stmt]) -> set[str]:
    names: set[str] = set()
    for node in body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        source = node.value.value
        if isinstance(source, str):
            names |= _top_level_imports(_parsed_or_empty(source))
    return names


def _top_level_imports(body: list[ast.stmt]) -> set[str]:
    names: set[str] = set()
    for node in body:
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif (
            isinstance(node, ast.ImportFrom)
            and node.level == 0
            and node.module
            and node.module != "mutmut.mutation.trampoline"
        ):
            names.add(node.module.split(".", 1)[0])
    return names


def _parsed_or_empty(source: str) -> list[ast.stmt]:
    try:
        return ast.parse(source).body
    except SyntaxError:
        return []
