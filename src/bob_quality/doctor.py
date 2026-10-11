"""`bob doctor`: versão esperada e encontrada de cada ferramenta pinada."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from bob_quality.exit_codes import CONFIG_OR_TOOL, PASSED

_VERSION = re.compile(r"\d+\.\d+(?:\.\d+)?")

# Ordem da issue #11. Versões iguais às pinadas no pacote.
# (nome, versão, executável, instrução de instalação)
PINS: tuple[tuple[str, str, str, str], ...] = (
    ("lizard", "1.24.1", "lizard", "pip install 'lizard==1.24.1'"),
    ("coverage.py", "7.16.2", "coverage", "pip install 'coverage==7.16.2'"),
    (
        "node",
        "22.14.0",
        "node",
        "Instale Node.js 22.14.0 (https://nodejs.org/dist/v22.14.0/)",
    ),
    ("c8", "12.0.0", "c8", "npm install c8@12.0.0"),
    ("mutmut", "3.8.0", "mutmut", "pip install 'mutmut==3.8.0'"),
    ("Stryker", "10.0.0", "stryker", "npm install @stryker-mutator/core@10.0.0"),
    ("jscpd", "5.4.1", "jscpd", "npm install jscpd@5.4.1"),
    ("import-linter", "2.15", "lint-imports", "pip install 'import-linter==2.15'"),
    (
        "dependency-cruiser",
        "18.5.0",
        "depcruise",
        "npm install dependency-cruiser@18.5.0",
    ),
)


def run_doctor() -> int:
    lines: list[str] = []
    installs: list[str] = []
    ok = True
    for name, expected, executable, install in PINS:
        found = _found_version(executable)
        if found != expected:
            ok = False
            installs.append(install)
        shown = found if found is not None else "ausente"
        lines.append(f"{name} esperada {expected} encontrada {shown}")
    if installs:
        lines.extend(installs)
    print("\n".join(lines))
    return PASSED if ok else CONFIG_OR_TOOL


def _found_version(executable: str) -> str | None:
    path = _locate(executable)
    if path is None:
        return None
    resolved = Path(path).resolve()
    packaged = _npm_package_version(executable, resolved)
    if packaged is not None:
        return packaged
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


def _npm_package_version(executable: str, resolved: Path) -> str | None:
    for parent in resolved.parents:
        manifest = parent / "package.json"
        if not manifest.is_file():
            continue
        try:
            data = json.loads(manifest.read_text())
        except json.JSONDecodeError:
            return None
        bin_field = data.get("bin")
        if isinstance(bin_field, dict):
            owns = executable in bin_field
        elif isinstance(bin_field, str):
            owns = data.get("name") == executable
        else:
            owns = False
        version = data.get("version")
        if owns and isinstance(version, str):
            return version
        return None
    return None
