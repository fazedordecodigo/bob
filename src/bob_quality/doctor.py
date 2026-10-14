"""`bob doctor`: versão esperada e encontrada de cada ferramenta pinada."""

from __future__ import annotations

import importlib.metadata
import json
import re
import shutil
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from bob_quality.exit_codes import CONFIG_OR_TOOL, PASSED
from bob_quality.messages import DEFAULT_LANGUAGE, Language, Text, msg, reason, render
from bob_quality.npm_tools import install_npm_dependencies, npm_prefix, npm_setup_hint
from bob_quality.tools import ToolError

_PRERELEASE = r"[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*"
_VERSION = re.compile(rf"\d+\.\d+(?:\.\d+)?(?:-{_PRERELEASE})?")
_NODE_RELEASE = re.compile(r"(\d+)\.(\d+)\.(\d+)")
_SELF = "bob-quality"


class NodeVersion(NamedTuple):
    major: int
    minor: int
    patch: int


@dataclass(frozen=True)
class RequiresDist:
    name: str
    distribution: str


@dataclass(frozen=True)
class NpmPin:
    name: str
    expected: str
    executable: str
    npm_package: str


@dataclass(frozen=True)
class NodePin:
    floor: NodeVersion


@dataclass(frozen=True)
class BinaryPin:
    name: str
    expected: str
    executable: str
    url: str
    sha256: str


Pin = RequiresDist | NpmPin | NodePin | BinaryPin

NODE = NodePin(floor=NodeVersion(22, 14, 0))

PINS: tuple[Pin, ...] = (
    RequiresDist("lizard", "lizard"),
    RequiresDist("deptry", "deptry"),
    RequiresDist("coverage.py", "coverage"),
    NODE,
    NpmPin("c8", "12.0.0", "c8", npm_package="c8"),
    NpmPin("vitest", "5.0.3", "vitest", npm_package="vitest"),
    NpmPin("jscpd", "5.4.1", "jscpd", npm_package="jscpd"),
    NpmPin("eslint", "9.39.5", "eslint", npm_package="eslint"),
    NpmPin(
        "eslint-plugin-sonarjs",
        "2.0.4",
        "eslint-plugin-sonarjs",
        npm_package="eslint-plugin-sonarjs",
    ),
    RequiresDist("mutmut", "mutmut"),
    RequiresDist("complexipy", "complexipy"),
    RequiresDist("import-linter", "import-linter"),
    RequiresDist("grimp", "grimp"),
    RequiresDist("diff-cover", "diff-cover"),
    RequiresDist("bandit", "bandit"),
    NpmPin(
        "dependency-cruiser",
        "18.5.0",
        "dependency-cruiser",
        npm_package="dependency-cruiser",
    ),
    BinaryPin(
        "gitleaks",
        "8.30.1",
        "gitleaks",
        "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz",
        "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
    ),
    RequiresDist("vulture", "vulture"),
    NpmPin("knip", "6.41.0", "knip", npm_package="knip"),
    NpmPin(
        "stryker",
        "10.0.0",
        "stryker",
        npm_package="@stryker-mutator/core",
    ),
    NpmPin(
        "stryker-vitest-runner",
        "10.0.0",
        "stryker-vitest-runner",
        npm_package="@stryker-mutator/vitest-runner",
    ),
)


@dataclass(frozen=True)
class _PinRow:
    line: Text
    ok: bool
    install: Text | None
    npm_missing: bool


def run_doctor(install: bool = False, lang: Language = DEFAULT_LANGUAGE) -> int:
    if install:
        return _install_then_report(lang)
    return _report_pins(lang)


def _install_then_report(lang: Language) -> int:
    code = install_npm_dependencies(lang)
    if code != 0:
        return code
    return _report_pins(lang)


def _report_pins(lang: Language) -> int:
    rows = _rows()
    print("\n".join(render(line, lang) for line in _lines(rows)))
    return _verdict(rows)


def _rows() -> list[_PinRow]:
    declared = unconditional_exact_pins(_own_requirements())
    rows: list[_PinRow] = []
    for pin in PINS:
        rows.append(_assess(pin, declared))
    return rows


def unconditional_exact_pins(requirements: Iterable[str]) -> dict[str, str]:
    return {
        name: version
        for name, sep, version in (
            line.partition("==") for line in requirements if ";" not in line
        )
        if sep
    }


def _own_requirements() -> list[str]:
    try:
        return importlib.metadata.requires(_SELF) or []
    except importlib.metadata.PackageNotFoundError:
        return []


def _lines(rows: list[_PinRow]) -> list[Text]:
    lines: list[Text] = []
    for row in rows:
        lines.append(row.line)
    lines.extend(_install_lines(rows))
    return lines


def _verdict(rows: list[_PinRow]) -> int:
    if _all_ok(rows):
        return PASSED
    return CONFIG_OR_TOOL


def _all_ok(rows: list[_PinRow]) -> bool:
    for row in rows:
        if not row.ok:
            return False
    return True


def _install_lines(rows: list[_PinRow]) -> list[Text]:
    installs = _explicit_installs(rows)
    _append_npm_hint(installs, rows)
    return installs


def _explicit_installs(rows: list[_PinRow]) -> list[Text]:
    installs: list[Text] = []
    for row in rows:
        _append_install(installs, row)
    return installs


def _append_install(installs: list[Text], row: _PinRow) -> None:
    if row.install:
        installs.append(row.install)


def _append_npm_hint(installs: list[Text], rows: list[_PinRow]) -> None:
    if _any_npm_missing(rows):
        installs.append(_npm_ci_hint())


def _any_npm_missing(rows: list[_PinRow]) -> bool:
    for row in rows:
        if row.npm_missing:
            return True
    return False


def _assess(pin: Pin, declared: Mapping[str, str]) -> _PinRow:
    if isinstance(pin, RequiresDist):
        return _assess_requires_dist(pin, declared.get(pin.distribution))
    if isinstance(pin, NodePin):
        return _assess_node(pin)
    if isinstance(pin, BinaryPin):
        return _assess_binary(pin)
    return _assess_npm(pin)


def _assess_requires_dist(pin: RequiresDist, expected: str | None) -> _PinRow:
    found = _distribution_version(pin.distribution)
    line = msg("doctor.version", name=pin.name, expected=_shown(expected), found=_shown(found))
    if expected is None:
        return _PinRow(line=line, ok=False, install=None, npm_missing=False)
    if found == expected:
        return _PinRow(line=line, ok=True, install=None, npm_missing=False)
    return _PinRow(
        line=line,
        ok=False,
        install=f"pip install '{pin.distribution}=={expected}'",
        npm_missing=False,
    )


def node_admits(pin: NodePin, found: str | None) -> bool:
    version = _node_version(found)
    if version is None:
        return False
    return version.major == pin.floor.major and version >= pin.floor


def node_range(pin: NodePin) -> str:
    return f">={_dotted(pin.floor)} <{pin.floor.major + 1}"


def _node_version(found: str | None) -> NodeVersion | None:
    if found is None:
        return None
    match = _NODE_RELEASE.fullmatch(found)
    if match is None:
        return None
    major, minor, patch = match.groups()
    return NodeVersion(int(major), int(minor), int(patch))


def _dotted(version: NodeVersion) -> str:
    return f"{version.major}.{version.minor}.{version.patch}"


def _node_install(pin: NodePin) -> Text:
    return msg(
        "doctor.install_node",
        version=node_range(pin),
        url=f"https://nodejs.org/dist/v{_dotted(pin.floor)}/",
    )


def _assess_node(pin: NodePin) -> _PinRow:
    found = _cli_version("node")
    line = msg("doctor.version", name="node", expected=node_range(pin), found=_shown(found))
    if node_admits(pin, found):
        return _PinRow(line, True, None, False)
    return _PinRow(line, False, _node_install(pin), False)


def _assess_npm(pin: NpmPin) -> _PinRow:
    found = _found_version(pin)
    line = msg("doctor.version", name=pin.name, expected=pin.expected, found=_shown(found))
    if found == pin.expected:
        return _PinRow(line, True, None, False)
    return _PinRow(line, False, None, True)


def _assess_binary(pin: BinaryPin) -> _PinRow:
    found = _cli_version(pin.executable)
    line = msg("doctor.version", name=pin.name, expected=pin.expected, found=_shown(found))
    if found == pin.expected:
        return _PinRow(line, True, None, False)
    return _PinRow(line, False, _binary_install(pin), False)


def _binary_install(pin: BinaryPin) -> Text:
    return msg(
        "doctor.install_gitleaks",
        version=pin.expected,
        url=pin.url,
        sha256=pin.sha256,
    )


def _shown(found: str | None) -> Text:
    if found is None:
        return msg("doctor.missing")
    return found


def _npm_ci_hint() -> Text:
    try:
        return npm_setup_hint(npm_prefix())
    except ToolError as exc:
        return reason(exc)


def _found_version(pin: NpmPin) -> str | None:
    packaged = _npm_package_version(pin.npm_package, pin.executable)
    if packaged is not None:
        return packaged
    return _cli_version(pin.executable)


def _npm_root() -> Path | None:
    try:
        return npm_prefix()
    except ToolError:
        return None


def _distribution_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _npm_package_version(package_name: str, executable: str) -> str | None:
    return _first_version(
        _cwd_npm_version(package_name),
        _prefix_npm_version(package_name),
        _executable_npm_version(package_name, executable),
    )


def _first_version(*candidates: str | None) -> str | None:
    for candidate in candidates:
        if candidate is not None:
            return candidate
    return None


def _cwd_npm_version(package_name: str) -> str | None:
    path = Path.cwd() / "node_modules" / package_name / "package.json"
    return _manifest_version(path, package_name)


def _prefix_npm_version(package_name: str) -> str | None:
    prefix = _npm_root()
    if prefix is None:
        return None
    path = prefix / "node_modules" / package_name / "package.json"
    return _manifest_version(path, package_name)


def _executable_npm_version(package_name: str, executable: str) -> str | None:
    located = _locate(executable)
    if located is None:
        return None
    return _version_near(Path(located).resolve(), package_name)


def _version_near(path: Path, package_name: str) -> str | None:
    for parent in path.parents:
        version = _manifest_version(parent / "package.json", package_name)
        if version is not None:
            return version
    return None


def _manifest_version(manifest: Path, package_name: str) -> str | None:
    data = _read_json(manifest)
    if not _owns_package(data, package_name):
        return None
    return _string_version(data)


def _owns_package(data: dict[str, object] | None, package_name: str) -> bool:
    return data is not None and data.get("name") == package_name


def _string_version(data: dict[str, object]) -> str | None:
    version = data.get("version")
    if isinstance(version, str):
        return version
    return None


def _read_json(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    return _parse_json(path)


def _parse_json(path: Path) -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        return data
    return None


def _cli_version(executable: str) -> str | None:
    path = _locate(executable)
    if path is None:
        return None
    completed = subprocess.run(
        [path, "--version"],
        check=False,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    match = _VERSION.search(completed.stdout + "\n" + completed.stderr)
    if match is None:
        return None
    return match.group(0)


def _locate(executable: str) -> str | None:
    local = Path.cwd() / "node_modules" / ".bin" / executable
    if local.exists():
        return str(local)
    return shutil.which(executable)
