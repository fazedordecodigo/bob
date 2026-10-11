"""`bob doctor`: versão esperada e encontrada de cada ferramenta pinada."""

from __future__ import annotations

import importlib.metadata
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from bob_quality.exit_codes import CONFIG_OR_TOOL, PASSED
from bob_quality.npm_tools import install_npm_dependencies, npm_prefix, npm_setup_hint
from bob_quality.tools import ToolError

_VERSION = re.compile(r"\d+\.\d+(?:\.\d+)?")


@dataclass(frozen=True)
class ToolPin:
    name: str
    expected: str
    executable: str
    install: str
    distribution: str | None = None
    npm_package: str | None = None


# Ordem da issue #11. Versões iguais às pinadas em pyproject.toml e package.json.
PINS: tuple[ToolPin, ...] = (
    ToolPin("lizard", "1.24.1", "lizard", "pip install 'lizard==1.24.1'", distribution="lizard"),
    ToolPin(
        "coverage.py",
        "7.16.2",
        "coverage",
        "pip install 'coverage==7.16.2'",
        distribution="coverage",
    ),
    ToolPin(
        "node",
        "22.14.0",
        "node",
        "Instale Node.js 22.14.0 (https://nodejs.org/dist/v22.14.0/)",
    ),
    ToolPin("c8", "12.0.0", "c8", "npm install c8@12.0.0", npm_package="c8"),
    ToolPin("vitest", "5.0.3", "vitest", "npm install vitest@5.0.3", npm_package="vitest"),
    ToolPin("mutmut", "3.8.0", "mutmut", "pip install 'mutmut==3.8.0'", distribution="mutmut"),
    ToolPin(
        "import-linter",
        "2.15",
        "lint-imports",
        "pip install 'import-linter==2.15'",
        distribution="import-linter",
    ),
)


@dataclass(frozen=True)
class _PinRow:
    line: str
    ok: bool
    install: str | None
    npm_missing: bool


def run_doctor(install: bool = False) -> int:
    if install:
        return _install_then_report()
    return _report_pins()


def _install_then_report() -> int:
    code = install_npm_dependencies()
    if code != 0:
        return code
    return _report_pins()


def _report_pins() -> int:
    rows = [_assess(pin) for pin in PINS]
    lines = [row.line for row in rows]
    installs = _install_lines(rows)
    if installs:
        lines.extend(installs)
    print("\n".join(lines))
    return PASSED if _all_ok(rows) else CONFIG_OR_TOOL


def _all_ok(rows: list[_PinRow]) -> bool:
    return all(row.ok for row in rows)


def _install_lines(rows: list[_PinRow]) -> list[str]:
    installs = [row.install for row in rows if row.install]
    if any(row.npm_missing for row in rows):
        installs.append(_npm_ci_hint())
    return installs


def _assess(pin: ToolPin) -> _PinRow:
    found = _found_version(pin)
    line = f"{pin.name} esperada {pin.expected} encontrada {_shown(found)}"
    if found == pin.expected:
        return _PinRow(line, True, None, False)
    return _PinRow(line, False, _install_text(pin), pin.npm_package is not None)


def _shown(found: str | None) -> str:
    if found is None:
        return "ausente"
    return found


def _install_text(pin: ToolPin) -> str | None:
    if pin.npm_package is not None:
        return None
    return pin.install


def _npm_ci_hint() -> str:
    try:
        return npm_setup_hint(npm_prefix())
    except ToolError as exc:
        return str(exc)


def _found_version(pin: ToolPin) -> str | None:
    packaged = _packaged_version(pin)
    if packaged is not None:
        return packaged
    return _cli_version(pin.executable)


def _packaged_version(pin: ToolPin) -> str | None:
    if pin.distribution is not None:
        return _distribution_version(pin.distribution)
    if pin.npm_package is not None:
        return _npm_package_version(pin.npm_package, pin.executable)
    return None


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
