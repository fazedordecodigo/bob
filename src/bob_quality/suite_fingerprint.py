"""Impressão digital da suíte: o que muda o veredito de um mutante sem mudar a função."""

from __future__ import annotations

import configparser
import hashlib
import subprocess
import sys
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath

from bob_quality.tools import ToolError

if sys.version_info >= (3, 11):
    import tomllib
else:
    # No 3.10, o tomli vem com o pytest que o mutmut pinado exige.
    import tomli as tomllib

_SUITE_DIRS = frozenset({"tests", "test"})
_SUITE_NAMES = ("conftest*", "test_*.py", "*_test.py")
_SUITE_CONFIGS = frozenset(
    {
        "pytest.ini",
        "tox.ini",
        "setup.cfg",
        "pyproject.toml",
        "uv.lock",
        "poetry.lock",
        "Pipfile.lock",
        "pdm.lock",
    }
)
_BOB_OUTPUT = frozenset({"mutants", ".bob"})


def suite_fingerprint(cwd: Path) -> str:
    """sha256 dos arquivos que a suíte lê, por caminho e conteúdo."""
    also_copy = _also_copy(cwd)
    digest = hashlib.sha256()
    for name in sorted(_listed_files(cwd)):
        file = cwd / name
        if _read_by_suite(PurePosixPath(name), also_copy) and file.is_file():
            digest.update(f"{name}\0{hashlib.sha256(file.read_bytes()).hexdigest()}\n".encode())
    return digest.hexdigest()


def _listed_files(cwd: Path) -> list[str]:
    """Versionados e não ignorados, como o git vê a árvore de trabalho."""
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard", "-z"],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise ToolError("ferramenta ausente: git") from exc
    if completed.returncode != 0:
        raise ToolError(f"git ls-files falhou: {completed.stderr.strip()}")
    return [name for name in completed.stdout.split("\0") if name]


def _read_by_suite(path: PurePosixPath, also_copy: list[PurePosixPath]) -> bool:
    # O pytest grava __pycache__ a cada execução, e isso não muda a suíte.
    if path.parts[0] in _BOB_OUTPUT or "__pycache__" in path.parts:
        return False
    return _is_test_file(path) or any(entry in (path, *path.parents) for entry in also_copy)


def _is_test_file(path: PurePosixPath) -> bool:
    if _SUITE_DIRS.intersection(path.parts[:-1]) or path.name in _SUITE_CONFIGS:
        return True
    return any(fnmatchcase(path.name, pattern) for pattern in _SUITE_NAMES)


def _also_copy(cwd: Path) -> list[PurePosixPath]:
    """`also_copy` do usuário, na ordem do mutmut 3.8: pyproject, senão setup.cfg."""
    entries = _pyproject_also_copy(cwd / "pyproject.toml")
    if entries is None:
        entries = _setup_cfg_also_copy(cwd / "setup.cfg")
    return [PurePosixPath(entry) for entry in entries]


def _pyproject_also_copy(path: Path) -> list[str] | None:
    if not path.is_file():
        return None
    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
    except tomllib.TOMLDecodeError as exc:
        raise ToolError(f"pyproject.toml ilegível: {exc}") from exc
    mutmut = data.get("tool", {}).get("mutmut")
    if mutmut is None:
        return None
    return [str(entry) for entry in mutmut.get("also_copy", [])]


def _setup_cfg_also_copy(path: Path) -> list[str]:
    parser = configparser.ConfigParser()
    try:
        parser.read(path)
        if not parser.has_option("mutmut", "also_copy"):
            return []
        raw = parser.get("mutmut", "also_copy")
    except configparser.Error as exc:
        raise ToolError(f"setup.cfg ilegível: {exc}") from exc
    return [entry for entry in raw.split("\n") if entry]
