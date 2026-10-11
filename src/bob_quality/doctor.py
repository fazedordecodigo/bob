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
from bob_quality.npm_tools import install_npm_dependencies, npm_ci_command, npm_prefix
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


def run_doctor(install: bool = False) -> int:
    if install:
        code = install_npm_dependencies()
        if code != 0:
            return code
    lines: list[str] = []
    installs: list[str] = []
    npm_missing = False
    ok = True
    for pin in PINS:
        found = _found_version(pin)
        if found != pin.expected:
            ok = False
            if pin.npm_package is not None:
                npm_missing = True
            else:
                installs.append(pin.install)
        shown = found if found is not None else "ausente"
        lines.append(f"{pin.name} esperada {pin.expected} encontrada {shown}")
    if npm_missing:
        installs.append(_npm_ci_hint())
    if installs:
        lines.extend(installs)
    print("\n".join(lines))
    return PASSED if ok else CONFIG_OR_TOOL


def _npm_ci_hint() -> str:
    try:
        return npm_ci_command(npm_prefix())
    except ToolError as exc:
        return str(exc)


def _found_version(pin: ToolPin) -> str | None:
    if pin.distribution is not None:
        return _distribution_version(pin.distribution)
    if pin.npm_package is not None:
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
    direct = Path.cwd() / "node_modules" / package_name / "package.json"
    version = _manifest_version(direct, package_name)
    if version is not None:
        return version
    prefix = _npm_root()
    if prefix is not None:
        bundled = prefix / "node_modules" / package_name / "package.json"
        version = _manifest_version(bundled, package_name)
    if version is not None:
        return version
    located = _locate(executable)
    if located is None:
        return None
    for parent in Path(located).resolve().parents:
        version = _manifest_version(parent / "package.json", package_name)
        if version is not None:
            return version
    return None


def _manifest_version(manifest: Path, package_name: str) -> str | None:
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text())
    except json.JSONDecodeError:
        return None
    if data.get("name") != package_name:
        return None
    version = data.get("version")
    if not isinstance(version, str):
        return None
    return version


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
