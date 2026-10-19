"""Versões fixadas do plugin (pip/npm), sem intervalo."""

import ast
import errno
import importlib.metadata
import inspect
import json
import os
import re
import sys
from pathlib import Path

import pytest

from bob_quality.doctor import unconditional_exact_pins
from bob_quality.messages import Language, Text, msg, reason, render
from bob_quality.npm_tools import NodeRange, PinSourceError, node_range, pinned_npm_versions
from bob_quality.tools import ToolError

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
_EXACT = re.compile(r"\d+\.\d+\.\d+")


def _json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text())
    assert isinstance(data, dict)
    return data


def _lock_mismatches(
    package: dict[str, object], lock: dict[str, object]
) -> dict[str, tuple[object, object]]:
    """{pacote: (spec do package.json, versão do lock)} para cada dependência divergente."""
    mismatches: dict[str, tuple[object, object]] = {}
    dependencies = package["dependencies"]
    packages = lock["packages"]
    assert isinstance(dependencies, dict)
    assert isinstance(packages, dict)
    for name, spec in dependencies.items():
        entry = packages.get(f"node_modules/{name}", {})
        assert isinstance(entry, dict)
        locked = entry.get("version")
        if locked != spec:
            mismatches[name] = (spec, locked)
    return mismatches


def test_npm_specs_are_exact_versions() -> None:
    dependencies = _json(ROOT / "package.json")["dependencies"]
    assert isinstance(dependencies, dict)
    assert dependencies
    invalid = [
        name
        for name, spec in dependencies.items()
        if not isinstance(spec, str) or _EXACT.fullmatch(spec) is None
    ]
    assert invalid == []


def test_package_lock_matches_package_json() -> None:
    package = _json(ROOT / "package.json")
    lock = _json(ROOT / "package-lock.json")
    assert _lock_mismatches(package, lock) == {}
    packages = lock["packages"]
    assert isinstance(packages, dict)
    root = packages[""]
    assert isinstance(root, dict)
    assert root["dependencies"] == package["dependencies"]


def test_lock_mismatch_names_the_package_and_both_versions() -> None:
    package: dict[str, object] = {
        "dependencies": {"example-tool": "1.2.4", "other-tool": "3.4.5"}
    }
    lock: dict[str, object] = {
        "packages": {
            "node_modules/example-tool": {"version": "1.2.3"},
            "node_modules/other-tool": {"version": "3.4.5"},
        }
    }
    assert _lock_mismatches(package, lock) == {"example-tool": ("1.2.4", "1.2.3")}
    assert _lock_mismatches(package, {"packages": {}}) == {
        "example-tool": ("1.2.4", None),
        "other-tool": ("3.4.5", None),
    }


def test_packaged_package_json_is_the_root_one() -> None:
    packaged = _json(ROOT / "src" / "bob_quality" / "package.json")
    root = _json(ROOT / "package.json")
    assert packaged == root


def test_pins_and_node_range_come_from_the_packaged_package_json() -> None:
    package = _json(ROOT / "package.json")
    assert pinned_npm_versions() == package["dependencies"]
    engines = package["engines"]
    assert isinstance(engines, dict)
    assert str(node_range()) == engines["node"]


@pytest.fixture
def manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "bob_quality").mkdir()
    monkeypatch.setattr(
        "bob_quality.npm_tools.__file__",
        str(tmp_path / "bob_quality" / "npm_tools.py"),
    )
    return tmp_path / "bob_quality" / "package.json"


def test_a_bumped_package_json_changes_the_pins_without_code(manifest: Path) -> None:
    manifest.write_text(
        json.dumps(
            {
                "engines": {"node": ">=24.1.0 <25"},
                "dependencies": {"example-tool": "1.2.4"},
            }
        )
    )
    assert pinned_npm_versions() == {"example-tool": "1.2.4"}
    assert node_range() == NodeRange(floor=(24, 1, 0), below_major=25)
    assert str(node_range()) == ">=24.1.0 <25"


def test_missing_package_json_names_the_file(
    manifest: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(PinSourceError) as caught:
        pinned_npm_versions()
    assert reason(caught.value) == msg(
        "npm.pin_source", path=manifest, detail=os.strerror(errno.ENOENT)
    )
    error = OSError("read failed")
    real = Path.read_bytes

    def read_bytes(self: Path) -> bytes:
        if self == manifest:
            raise error
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    manifest.write_text("{}")
    with pytest.raises(PinSourceError) as blank:
        pinned_npm_versions()
    assert reason(blank.value) == msg(
        "npm.pin_source", path=manifest, detail=str(error)
    )


@pytest.mark.parametrize(
    ("content", "detail"),
    [
        (
            "not json",
            msg("npm.pin_not_json", detail="Expecting value: line 1 column 1 (char 0)"),
        ),
        ("[]", msg("npm.pin_not_object", field="package.json")),
        ("{}", msg("npm.pin_not_object", field="dependencies")),
        ('{"dependencies": []}', msg("npm.pin_not_object", field="dependencies")),
        (
            '{"dependencies": {"example-tool": "^1.2.4"}}',
            msg("npm.pin_not_exact", field="dependencies.example-tool", value="^1.2.4"),
        ),
        (
            '{"dependencies": {"example-tool": "1.2.4-beta.1"}}',
            msg(
                "npm.pin_not_exact",
                field="dependencies.example-tool",
                value="1.2.4-beta.1",
            ),
        ),
        (
            '{"dependencies": {"example-tool": 1}}',
            msg("npm.pin_not_exact", field="dependencies.example-tool", value=1),
        ),
    ],
)
def test_pinned_npm_versions_rejects_a_package_json_out_of_format(
    manifest: Path, content: str, detail: Text
) -> None:
    manifest.write_text(content)
    with pytest.raises(PinSourceError) as caught:
        pinned_npm_versions()
    assert reason(caught.value) == msg("npm.pin_source", path=manifest, detail=detail)


@pytest.mark.parametrize(
    ("content", "detail"),
    [
        ("{}", msg("npm.pin_not_object", field="engines")),
        ('{"engines": {}}', msg("npm.pin_bad_node_range", value=None)),
        ('{"engines": {"node": 22}}', msg("npm.pin_bad_node_range", value=22)),
        (
            '{"engines": {"node": "^22.18.0"}}',
            msg("npm.pin_bad_node_range", value="^22.18.0"),
        ),
        (
            '{"engines": {"node": ">=22.18.0 <24"}}',
            msg("npm.pin_bad_node_range", value=">=22.18.0 <24"),
        ),
        (
            '{"engines": {"node": ">=22.18.0 <23 "}}',
            msg("npm.pin_bad_node_range", value=">=22.18.0 <23 "),
        ),
    ],
)
def test_node_range_rejects_an_engine_out_of_format(
    manifest: Path, content: str, detail: Text
) -> None:
    manifest.write_text(content)
    with pytest.raises(PinSourceError) as caught:
        node_range()
    assert reason(caught.value) == msg("npm.pin_source", path=manifest, detail=detail)


@pytest.mark.parametrize(
    ("lang", "detail", "text"),
    [
        ("en", msg("npm.pin_not_json", detail="x"), "invalid JSON: x"),
        ("pt-BR", msg("npm.pin_not_json", detail="x"), "JSON inválido: x"),
        ("en", msg("npm.pin_not_object", field="engines"), "engines is not an object"),
        (
            "pt-BR",
            msg("npm.pin_not_object", field="engines"),
            "engines não é um objeto",
        ),
        (
            "en",
            msg("npm.pin_not_exact", field="dependencies.a", value="^1.2.4"),
            "dependencies.a = ^1.2.4 is not X.Y.Z",
        ),
        (
            "pt-BR",
            msg("npm.pin_not_exact", field="dependencies.a", value="^1.2.4"),
            "dependencies.a = ^1.2.4 não é X.Y.Z",
        ),
        (
            "en",
            msg("npm.pin_bad_node_range", value="<24"),
            "engines.node = <24 is not >=A.B.C <N with N = A + 1",
        ),
        (
            "pt-BR",
            msg("npm.pin_bad_node_range", value="<24"),
            "engines.node = <24 não é >=A.B.C <N com N = A + 1",
        ),
    ],
)
def test_pin_source_detail_is_written_in_both_languages(
    lang: Language, detail: Text, text: str
) -> None:
    assert render(detail, lang) == text


def test_pin_source_error_is_a_tool_error() -> None:
    assert issubclass(PinSourceError, ToolError)


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
