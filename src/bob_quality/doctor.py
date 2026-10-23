"""`bob doctor`: versão esperada e encontrada de cada ferramenta pinada."""

from __future__ import annotations

import importlib.metadata
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from bob_quality import gitleaks
from bob_quality import project_version
from bob_quality import user_dirs
from bob_quality.exit_codes import CONFIG_OR_TOOL, PASSED
from bob_quality.gitleaks import GitleaksError
from bob_quality.messages import DEFAULT_LANGUAGE, Language, Text, msg, reason, render, t
from bob_quality.npm_tools import (
    PinSourceError,
    install_npm_dependencies,
    npm_prefix,
    npm_setup_hint,
    pinned_npm_versions,
)
from bob_quality.npm_tools import node_range as packaged_node_range
from bob_quality.tools import ToolError

# par que os workflows conferem (ci.yml, bob.yml, package.yml)
_GITLEAKS_REFERENCE = ("linux", "x64")
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
    npm_package: str


@dataclass(frozen=True)
class NodePin:
    floor: NodeVersion


@dataclass(frozen=True)
class NodeSlot:
    """Posição do Node em PINS. A faixa vem do package.json empacotado (node_pin)."""


@dataclass(frozen=True)
class BinaryPin:
    name: str
    expected: str
    executable: str
    url: str
    sha256: str


Pin = RequiresDist | NpmPin | NodeSlot | BinaryPin

PINS: tuple[Pin, ...] = (
    RequiresDist("lizard", "lizard"),
    RequiresDist("deptry", "deptry"),
    RequiresDist("coverage.py", "coverage"),
    NodeSlot(),
    NpmPin("c8", "c8"),
    NpmPin("vitest", "vitest"),
    NpmPin("jscpd", "jscpd"),
    NpmPin("eslint", "eslint"),
    NpmPin("eslint-plugin-sonarjs", "eslint-plugin-sonarjs"),
    RequiresDist("mutmut", "mutmut"),
    RequiresDist("complexipy", "complexipy"),
    RequiresDist("import-linter", "import-linter"),
    RequiresDist("grimp", "grimp"),
    RequiresDist("diff-cover", "diff-cover"),
    RequiresDist("bandit", "bandit"),
    NpmPin("dependency-cruiser", "dependency-cruiser"),
    BinaryPin(
        "gitleaks",
        gitleaks.VERSION,
        "gitleaks",
        gitleaks.asset_url(_GITLEAKS_REFERENCE),
        gitleaks.ASSETS[_GITLEAKS_REFERENCE][1],
    ),
    RequiresDist("vulture", "vulture"),
    NpmPin("knip", "knip"),
    NpmPin("stryker", "@stryker-mutator/core"),
    NpmPin("stryker-vitest-runner", "@stryker-mutator/vitest-runner"),
)


@dataclass(frozen=True)
class _PinRow:
    line: Text
    ok: bool
    install: Text | None
    npm_missing: bool


@dataclass(frozen=True)
class _Expected:
    python: Mapping[str, str]
    npm: Mapping[str, str]
    node: NodePin


def node_pin() -> NodePin:
    """Piso do Node lido de engines.node do package.json empacotado (ADR 0008)."""
    major, minor, patch = packaged_node_range().floor
    return NodePin(floor=NodeVersion(major, minor, patch))


def run_doctor(install: bool = False, lang: Language = DEFAULT_LANGUAGE) -> int:
    if install:
        return _install_then_report(lang)
    return _report_pins(lang)


def _install_then_report(lang: Language) -> int:
    code = install_npm_dependencies(lang)
    if code != 0:
        return code
    try:
        home = user_dirs.bob_home()
    except ValueError as exc:
        print(
            t(lang, "doctor.error", reason=msg("doctor.bob_home_relative", value=str(exc))),
            file=sys.stderr,
        )
        return CONFIG_OR_TOOL
    try:
        gitleaks.ensure_gitleaks(home)
    except GitleaksError as exc:
        print(t(lang, "doctor.error", reason=reason(exc)), file=sys.stderr)
        return CONFIG_OR_TOOL
    return _report_pins(lang)


def _report_pins(lang: Language) -> int:
    try:
        rows = _rows()
    except PinSourceError as exc:
        print(t(lang, "doctor.error", reason=reason(exc)), file=sys.stderr)
        return CONFIG_OR_TOOL
    print("\n".join(render(line, lang) for line in _lines(rows)))
    print(render(project_version.skills_line(Path.cwd()), lang))
    return _verdict(rows)


def _rows() -> list[_PinRow]:
    expected = _Expected(
        python=unconditional_exact_pins(_own_requirements()),
        npm=pinned_npm_versions(),
        node=node_pin(),
    )
    rows: list[_PinRow] = []
    for pin in PINS:
        rows.append(_assess(pin, expected))
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


def _assess(pin: Pin, expected: _Expected) -> _PinRow:
    if isinstance(pin, RequiresDist):
        return _assess_requires_dist(pin, expected.python.get(pin.distribution))
    if isinstance(pin, NodeSlot):
        return _assess_node(expected.node)
    if isinstance(pin, BinaryPin):
        return _assess_binary(pin)
    return _assess_npm(pin, expected.npm.get(pin.npm_package))


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


def _assess_npm(pin: NpmPin, expected: str | None) -> _PinRow:
    found = _found_version(pin)
    line = msg("doctor.version", name=pin.name, expected=_shown(expected), found=_shown(found))
    if expected is None:
        return _PinRow(line, False, None, False)
    if found == expected:
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
    """Só o prefixo do bob (ADR 0019): sem node_modules do cwd e sem executável no PATH."""
    return _prefix_npm_version(pin.npm_package)


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


def _prefix_npm_version(package_name: str) -> str | None:
    prefix = _npm_root()
    if prefix is None:
        return None
    path = prefix / "node_modules" / package_name / "package.json"
    return _manifest_version(path, package_name)


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
    return user_dirs.locate_binary(executable)
