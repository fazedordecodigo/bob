"""Nomes diretos no HEAD que o manifesto da base não tem."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from bob_quality.models import SupplyIndex

_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?")
_EXACT = re.compile(r"^={2,3}\s*([^\s,*]+)\s*$")
_NPM_EXACT = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
_QUOTED = re.compile(r'"([^"\\]*)"|\'([^\'\\]*)\'')
_POETRY_KEY = re.compile(r"^([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*=\s*(.+)$")
_NPM_SECTIONS = (
    "dependencies",
    "devDependencies",
    "optionalDependencies",
    "peerDependencies",
)
_NPM_SKIP = ("file:", "link:", "workspace:", "git+", "git:", "github:", "http:", "https:")


@dataclass(frozen=True)
class AddedPackage:
    index: SupplyIndex
    name: str
    version: str | None
    file: str
    line: int


@dataclass(frozen=True)
class _Decl:
    name: str
    version: str | None
    line: int


def added_packages(
    cwd: Path,
    base: str,
    diff_lines: Mapping[str, set[int]],
    index: SupplyIndex,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
) -> tuple[AddedPackage, ...]:
    found: list[AddedPackage] = []
    seen: set[tuple[str, str]] = set()
    for path in _manifests(cwd, index, include, exclude):
        relative = path.relative_to(cwd).as_posix()
        found.extend(_from_manifest(cwd, base, diff_lines, index, path, relative, seen))
    return tuple(found)


def pep503(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _from_manifest(
    cwd: Path,
    base: str,
    diff_lines: Mapping[str, set[int]],
    index: SupplyIndex,
    path: Path,
    relative: str,
    seen: set[tuple[str, str]],
) -> list[AddedPackage]:
    text = path.read_text()
    head = _declarations(text, index, path.name)
    base_names = _base_names(cwd, base, relative, index, path.name)
    if base_names is None:
        return []
    lines = diff_lines.get(relative, set())
    rows: list[AddedPackage] = []
    for decl in head:
        stored = pep503(decl.name) if index == "pypi" else decl.name
        if stored in base_names or decl.line not in lines or (relative, stored) in seen:
            continue
        seen.add((relative, stored))
        version = decl.version or _locked(cwd, path, index, stored)
        rows.append(AddedPackage(index, stored, version, relative, decl.line))
    return rows


def _base_names(
    cwd: Path, base: str, relative: str, index: SupplyIndex, filename: str
) -> set[str] | None:
    shown = _git_show(cwd, base, relative)
    if shown is None:
        return None
    names = set()
    for decl in _declarations(shown, index, filename):
        names.add(pep503(decl.name) if index == "pypi" else decl.name)
    return names


def _git_show(cwd: Path, base: str, relative: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "show", f"{base}:{relative}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if completed.returncode == 0:
        return completed.stdout
    if _missing_blob(completed.stderr):
        return ""
    return None


def _missing_blob(stderr: str) -> bool:
    return "does not exist" in stderr or "exists on disk" in stderr


def _locked(cwd: Path, manifest: Path, index: SupplyIndex, name: str) -> str | None:
    if index == "npm":
        return _npm_locked(manifest, name)
    return _python_locked(cwd, manifest, name)


def _python_locked(cwd: Path, manifest: Path, name: str) -> str | None:
    candidates = (
        manifest.parent / "poetry.lock",
        manifest.parent / "uv.lock",
        cwd / "poetry.lock",
        cwd / "uv.lock",
    )
    for path in candidates:
        found = _toml_lock(path, name)
        if found is not None:
            return found
    return None


def _toml_lock(path: Path, name: str) -> str | None:
    if not path.is_file():
        return None
    current: str | None = None
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped == "[[package]]":
            current = None
            continue
        if stripped.startswith("name = "):
            current = _quoted_value(stripped.split("=", 1)[1].strip())
            continue
        if current is None or pep503(current) != name or not stripped.startswith("version = "):
            continue
        return _quoted_value(stripped.split("=", 1)[1].strip())
    return None


def _npm_locked(manifest: Path, name: str) -> str | None:
    for filename in ("package-lock.json", "npm-shrinkwrap.json"):
        found = _npm_lock_file(manifest.parent / filename, name)
        if found is not None:
            return found
    return None


def _npm_lock_file(path: Path, name: str) -> str | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    packaged = _lock_field(payload.get("packages"), f"node_modules/{name}")
    if packaged is not None:
        return packaged
    return _lock_field(payload.get("dependencies"), name)


def _lock_field(table: object, key: str) -> str | None:
    if not isinstance(table, dict):
        return None
    entry = table.get(key)
    if not isinstance(entry, dict):
        return None
    version = entry.get("version")
    if isinstance(version, str) and version:
        return version
    return None


def _manifests(
    cwd: Path,
    index: SupplyIndex,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
) -> tuple[Path, ...]:
    found: list[Path] = []
    seen: set[Path] = set()
    for path in _root_manifests(cwd, index):
        _keep(found, seen, cwd, path, exclude)
    for root in include:
        base = cwd / root
        if base.is_dir():
            _walk(found, seen, cwd, base, index, exclude)
    return tuple(found)


def _root_manifests(cwd: Path, index: SupplyIndex) -> tuple[Path, ...]:
    if index == "npm":
        return (cwd / "package.json",) if (cwd / "package.json").is_file() else ()
    paths = [cwd / "pyproject.toml"]
    paths.extend(sorted(cwd.glob("requirements*.txt")))
    return tuple(path for path in paths if path.is_file())


def _walk(
    found: list[Path],
    seen: set[Path],
    cwd: Path,
    base: Path,
    index: SupplyIndex,
    exclude: tuple[str, ...],
) -> None:
    for dirpath, dirnames, filenames in os.walk(base):
        current = Path(dirpath)
        dirnames[:] = [
            name
            for name in dirnames
            if not _excluded((current / name).relative_to(cwd).as_posix(), exclude)
        ]
        for filename in filenames:
            if _manifest_name(filename, index):
                _keep(found, seen, cwd, current / filename, exclude)


def _keep(
    found: list[Path], seen: set[Path], cwd: Path, path: Path, exclude: tuple[str, ...]
) -> None:
    if not path.is_file() or path in seen:
        return
    if _excluded(path.relative_to(cwd).as_posix(), exclude):
        return
    seen.add(path)
    found.append(path)


def _manifest_name(filename: str, index: SupplyIndex) -> bool:
    if index == "npm":
        return filename == "package.json"
    if filename == "pyproject.toml":
        return True
    return filename.startswith("requirements") and filename.endswith(".txt")


def _excluded(relative: str, exclude: tuple[str, ...]) -> bool:
    parts = Path(relative).parts
    for pattern in exclude:
        token = pattern.strip("/")
        if token and token in parts:
            return True
    return False


def _python_declarations(text: str) -> tuple[_Decl, ...]:
    section = ""
    collecting = False
    rows: list[_Decl] = []
    for number, raw in enumerate(text.splitlines(), 1):
        section, collecting, found = _python_line(section, collecting, raw, number)
        rows.extend(found)
    return tuple(rows)


def _python_line(
    section: str, collecting: bool, raw: str, number: int
) -> tuple[str, bool, tuple[_Decl, ...]]:
    stripped = raw.split("#", 1)[0].strip()
    header = _header(stripped)
    if header is not None:
        return header, False, ()
    if not stripped:
        return section, collecting, ()
    if _opens_requirement_array(section, stripped):
        return section, "]" not in stripped, _requirement_rows(_strings(stripped), number)
    if collecting:
        return section, "]" not in stripped, _requirement_rows(_strings(stripped), number)
    poetry = _poetry_row(section, stripped, number)
    if poetry is None:
        return section, False, ()
    return section, False, (poetry,)


def _requirement_declarations(text: str) -> tuple[_Decl, ...]:
    rows: list[_Decl] = []
    for number, raw in enumerate(text.splitlines(), 1):
        stripped = raw.split("#", 1)[0].strip()
        parsed = _requirement(stripped)
        if parsed is not None:
            rows.append(_Decl(parsed[0], parsed[1], number))
    return tuple(rows)


def _declarations(text: str, index: SupplyIndex, filename: str) -> tuple[_Decl, ...]:
    if index == "npm":
        return _npm_declarations(text)
    if filename.startswith("requirements") and filename.endswith(".txt"):
        return _requirement_declarations(text)
    return _python_declarations(text)


def _header(stripped: str) -> str | None:
    if stripped.startswith("[") and stripped.endswith("]"):
        return stripped[1:-1].strip()
    return None


def _opens_requirement_array(section: str, stripped: str) -> bool:
    if "=" not in stripped or "[" not in stripped:
        return False
    key = stripped.split("=", 1)[0].strip()
    if section == "project" and key == "dependencies":
        return True
    if section == "project.optional-dependencies":
        return True
    return section == "dependency-groups"


def _strings(stripped: str) -> tuple[str, ...]:
    return tuple(double or single for double, single in _QUOTED.findall(stripped))


def _requirement_rows(values: tuple[str, ...], number: int) -> tuple[_Decl, ...]:
    rows = []
    for value in values:
        parsed = _requirement(value.strip())
        if parsed is not None:
            rows.append(_Decl(parsed[0], parsed[1], number))
    return tuple(rows)


def _poetry_row(section: str, stripped: str, number: int) -> _Decl | None:
    if not _poetry_section(section):
        return None
    match = _POETRY_KEY.match(stripped)
    if match is None:
        return None
    name, value = match.group(1), match.group(2).strip()
    if name == "python" or _poetry_skips(value):
        return None
    return _Decl(name, _poetry_version(value), number)


def _poetry_section(section: str) -> bool:
    if section == "tool.poetry.dependencies":
        return True
    return section.startswith("tool.poetry.group.") and section.endswith(".dependencies")


def _poetry_skips(value: str) -> bool:
    return "path =" in value or "git =" in value or "url =" in value


def _poetry_version(value: str) -> str | None:
    quoted = _inline_version(value) if value.startswith("{") else _quoted_value(value)
    if quoted is not None and _NPM_EXACT.match(quoted):
        return quoted
    return None


def _inline_version(value: str) -> str | None:
    if "version" not in value:
        return None
    for double, single in _QUOTED.findall(value.split("version", 1)[1]):
        return double or single
    return None


def _quoted_value(value: str) -> str | None:
    match = _QUOTED.search(value)
    if match is None:
        return None
    return match.group(1) or match.group(2)


def _requirement(stripped: str) -> tuple[str, str | None] | None:
    if not stripped or stripped.startswith(("-", ".", "/")):
        return None
    if "://" in stripped or " @" in stripped:
        return None
    match = _NAME.match(stripped)
    if match is None:
        return None
    spec = _spec(stripped[match.end() :].strip())
    if spec is None:
        return None
    return match.group(0), _exact_version(spec)


def _spec(spec: str) -> str | None:
    if spec.startswith("["):
        end = spec.find("]")
        if end < 0:
            return None
        spec = spec[end + 1 :].strip()
    if "://" in spec or spec.startswith("@"):
        return None
    return spec


def _exact_version(spec: str) -> str | None:
    match = _EXACT.match(spec)
    if match is None:
        return None
    return match.group(1)


def _npm_declarations(text: str) -> tuple[_Decl, ...]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return ()
    if not isinstance(payload, dict):
        return ()
    rows: list[_Decl] = []
    for section in _NPM_SECTIONS:
        table = payload.get(section)
        if isinstance(table, dict):
            rows.extend(_npm_rows(text, section, table))
    return tuple(rows)


def _npm_rows(text: str, section: str, table: dict[object, object]) -> tuple[_Decl, ...]:
    rows = []
    for name, spec in table.items():
        row = _npm_row(text, section, name, spec)
        if row is not None:
            rows.append(row)
    return tuple(rows)


def _npm_row(text: str, section: str, name: object, spec: object) -> _Decl | None:
    if not isinstance(name, str) or not isinstance(spec, str) or _npm_skip(spec):
        return None
    line = _npm_line(text, section, name)
    if line is None:
        return None
    return _Decl(name, _npm_exact(spec), line)


def _npm_skip(spec: str) -> bool:
    return spec.startswith(_NPM_SKIP) or spec.startswith(".") or spec.startswith("/")


def _npm_exact(spec: str) -> str | None:
    if _NPM_EXACT.match(spec):
        return spec
    return None


def _npm_line(text: str, section: str, name: str) -> int | None:
    depth = 0
    inside = False
    for number, line in enumerate(text.splitlines(), 1):
        if inside:
            depth += line.count("{") - line.count("}")
        else:
            depth, inside = _enter_section(line, section)
        if inside and _package_on_line(line, section, name):
            return number
        if depth <= 0:
            inside = False
    return None


def _enter_section(line: str, section: str) -> tuple[int, bool]:
    if f'"{section}"' not in line:
        return 0, False
    return line.count("{") - line.count("}"), True


def _package_on_line(line: str, section: str, name: str) -> bool:
    rest = line.split(f'"{section}"', 1)[-1]
    return f'"{name}"' in rest
