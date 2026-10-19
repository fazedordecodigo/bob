"""Copia as skills do plugin bob para a pasta de skills de cada agente no projeto.

Roda como `python -m bob_quality.install_skills` ou direto de um clone
(`python3 src/bob_quality/install_skills.py`), por isso usa só a stdlib.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

# Pasta de skills, relativa ao projeto, que cada alvo lê. `.agents/skills` é lida
# por Cursor, Copilot, Devin e Codex.
TARGETS: dict[str, str] = {
    "copilot": ".github/skills",
    "devin": ".agents/skills",
    "agents": ".agents/skills",
}

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(".claude-plugin") / "plugin.json"
ATTRIBUTION = ("LICENSE",)
BOB_VERSION_FILE = ".bob-version"
DUPLICATE_ROOTS = (".claude/skills", ".github/skills")
_S_IFMT = 0o170000
_S_IFDIR = 0o040000
_S_IFREG = 0o100000

# O instalador antigo copiava este NOTICE para dentro de cada skill. 2347154.
RETIRED_NOTICE = b"""\
Matt Pocock agent skills, vendored for the bob plugin.

Source:  https://github.com/mattpocock/skills
Commit:  49dd158d1076134a641b33efb035946536778336
Date:    2026-10-09
License: MIT (see LICENSE in this directory)
Copyright (c) 2026 Matt Pocock

This tree is a verbatim copy of the upstream `skills/` directory at that
commit, plus the upstream LICENSE. Do not edit the vendored files; re-copy
from the pin above.
"""

RETIRED_SKILL_NAMES: frozenset[str] = frozenset(
    (
        "ask-matt",
        "code-review",
        "codebase-design",
        "diagnosing-bugs",
        "domain-modeling",
        "grill-me",
        "grill-with-docs",
        "grilling",
        "handoff",
        "implement",
        "implement-spec",
        "improve-codebase-architecture",
        "pr",
        "prototype",
        "research",
        "retro",
        "setup-matt-pocock-skills",
        "tdd",
        "teach",
        "to-questionnaire",
        "to-spec",
        "to-tickets",
        "triage",
        "wait-what",
        "wayfinder",
        "wizard",
        "writing-for-agents",
    )
)

# Mesmo valor de bob_quality.exit_codes.CONFIG_OR_TOOL. O script roda sem o pacote
# instalado e não pode importá-lo.
CONFIG_ERROR = 4


class SourceError(Exception):
    """A raiz do plugin não tem um manifesto com pastas de skills válidas."""


def default_source() -> Path:
    """Raiz do plugin: a do clone, se tiver o manifesto; senão a cópia dentro do pacote (wheel)."""
    if (PLUGIN_ROOT / MANIFEST).is_file():
        return PLUGIN_ROOT
    return Path(__file__).resolve().parent / "plugin"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    source = args.source if args.source is not None else default_source()
    try:
        skills = _skills(source)
    except SourceError as exc:
        print(str(exc), file=sys.stderr)
        return CONFIG_ERROR
    for skill, attribution in skills.items():
        if attribution:
            continue
        print(
            f"aviso: a skill {skill.name} não tem LICENSE entre a pasta dela e a raiz do plugin "
            f"{source}; instalada sem licença.",
            file=sys.stderr,
        )
    for dest in dict.fromkeys(TARGETS[name] for name in args.targets):
        _install(skills, args.project / dest)
        print(f"{len(skills)} skills em {dest}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument("--source", type=Path)
    parser.add_argument("targets", nargs="+", choices=sorted(TARGETS))
    return parser


def _skills(source: Path) -> dict[Path, list[Path]]:
    """Cada entrada de `skills` é uma pasta com `SKILL.md` direto nela, como os agentes leem.

    Devolve cada pasta com os arquivos de licença que vão junto dela.
    """
    manifest = source / MANIFEST
    skills = [source / entry for entry in _skill_entries(manifest)]
    for skill in skills:
        if not (skill / "SKILL.md").is_file():
            raise SourceError(f"pasta de skill sem SKILL.md: {skill} (listada em {manifest})")
    return {skill: _attribution(skill, source) for skill in skills}


def _attribution(skill: Path, source: Path) -> list[Path]:
    for folder in (skill, *skill.parents):
        if (folder / "LICENSE").is_file():
            return [folder / name for name in ATTRIBUTION if (folder / name).is_file()]
        if folder == source:
            break
    return []


def _skill_entries(manifest: Path) -> list[str]:
    data = _read_manifest(manifest)
    if not isinstance(data, dict):
        raise SourceError(f"manifesto não é objeto JSON: {manifest}")
    entries = data.get("skills")
    if isinstance(entries, list) and all(isinstance(entry, str) for entry in entries):
        return entries
    raise SourceError(f"manifesto inválido (skills deve ser uma lista de pastas): {manifest}")


def _read_manifest(manifest: Path) -> object:
    try:
        raw = manifest.read_bytes()
    except OSError:
        raise SourceError(
            f"manifesto não encontrado: {manifest}. Passe --source com a raiz do plugin bob."
        ) from None
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise SourceError(f"JSON inválido em {manifest}: {exc}") from None


def _skip_reason(child: Path) -> str | None:
    if child.is_symlink() or not child.is_dir():
        return "é um arquivo ou um link simbólico"
    notice = child / "NOTICE"
    try:
        if not (notice.is_file() and not notice.is_symlink()):
            return "o NOTICE não é o da instalação antiga"
        payload = notice.read_bytes()
    except OSError as exc:
        return str(exc)
    if payload == RETIRED_NOTICE:
        return None
    return "o NOTICE não é o da instalação antiga"


def _remove_retired(dest: Path) -> None:
    if not dest.is_dir():
        return
    for child in list(dest.iterdir()):
        if child.name not in RETIRED_SKILL_NAMES:
            continue
        reason = _skip_reason(child)
        if reason is None:
            shutil.rmtree(child)
            continue
        print(f"aviso: {child} ficou, porque {reason}.", file=sys.stderr)


def _install(skills: dict[Path, list[Path]], dest: Path) -> None:
    _remove_retired(dest)
    for skill, attribution in skills.items():
        target = dest / skill.name
        if target.is_symlink():
            print(f"aviso: {target} ficou, porque é um link simbólico.", file=sys.stderr)
            continue
        if target.is_file():
            print(f"aviso: {target} ficou, porque é um arquivo.", file=sys.stderr)
            continue
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill, target)
        for path in attribution:
            shutil.copy2(path, target / path.name)


@dataclass(frozen=True)
class SkillsResult:
    """Resultado de install_project_skills (CT4)."""

    installed: tuple[str, ...]
    unchanged: tuple[str, ...]
    preserved: tuple[Path, ...]
    duplicates: tuple[Path, ...]
    unmarked: tuple[Path, ...] = ()


def install_project_skills(
    project: Path,
    version: str,
    *,
    source: Path | None = None,
) -> SkillsResult:
    """Grava as skills do bob em <project>/.agents/skills com .bob-version, respeitando a posse (CT4)."""
    _require_version(version)
    skills = _skills(default_source() if source is None else source)
    dest = project / ".agents" / "skills"
    dest.mkdir(parents=True, exist_ok=True)
    _purge_leftovers(dest)
    installed: list[str] = []
    unchanged: list[str] = []
    preserved: list[Path] = []
    unmarked: list[Path] = []
    _apply_manifest(dest, skills, version, installed, unchanged, preserved, unmarked)
    _apply_foreign(dest, {skill.name for skill in skills}, preserved)
    return _assemble(
        installed,
        unchanged,
        preserved,
        unmarked,
        _duplicates(project, skills),
    )


def _require_version(version: str) -> None:
    if re.fullmatch(r"\d+\.\d+\.\d+", version) is None:
        raise ValueError(f"versão inválida: {version!r}")


def _purge_leftovers(dest: Path) -> None:
    for child in list(dest.iterdir()):
        if re.fullmatch(r"\..+\.bob-(tmp|old)-\d+", child.name) is not None:
            _remove_path(child)


def _remove_path(path: Path) -> None:
    try:
        path.unlink()
    except IsADirectoryError:
        shutil.rmtree(path)


def _apply_manifest(
    dest: Path,
    skills: dict[Path, list[Path]],
    version: str,
    installed: list[str],
    unchanged: list[str],
    preserved: list[Path],
    unmarked: list[Path],
) -> None:
    for skill, attribution in skills.items():
        _apply_one(
            dest, skill, attribution, version, installed, unchanged, preserved, unmarked
        )


def _apply_one(
    dest: Path,
    skill: Path,
    attribution: list[Path],
    version: str,
    installed: list[str],
    unchanged: list[str],
    preserved: list[Path],
    unmarked: list[Path],
) -> None:
    target = dest / skill.name
    if _missing(target):
        _replace(dest, skill, attribution, version)
        installed.append(skill.name)
        return
    if _kept_as_is(target):
        preserved.append(target)
        return
    if _has_marker(target):
        _update_owned(dest, skill, attribution, version, target, installed, unchanged)
        return
    preserved.append(target)
    unmarked.append(target)


def _missing(target: Path) -> bool:
    return not target.exists() and not target.is_symlink()


def _kept_as_is(target: Path) -> bool:
    return target.is_symlink() or not target.is_dir()


def _has_marker(target: Path) -> bool:
    return _regular(target / BOB_VERSION_FILE)


def _mode(path: Path) -> int | None:
    try:
        return path.lstat().st_mode
    except FileNotFoundError:
        return None


def _kind_is(path: Path, kind: int) -> bool:
    mode = _mode(path)
    return mode is not None and (mode & _S_IFMT) == kind


def _regular(path: Path) -> bool:
    return _kind_is(path, _S_IFREG)


def _update_owned(
    dest: Path,
    skill: Path,
    attribution: list[Path],
    version: str,
    target: Path,
    installed: list[str],
    unchanged: list[str],
) -> None:
    if _current(target, skill, attribution, version):
        unchanged.append(skill.name)
        return
    _replace(dest, skill, attribution, version)
    installed.append(skill.name)


def _current(target: Path, skill: Path, attribution: list[Path], version: str) -> bool:
    return _files(target) == _expected(skill, attribution, version)


def _expected(skill: Path, attribution: list[Path], version: str) -> dict[str, bytes]:
    files = _files(skill)
    for path in attribution:
        files[path.name] = path.read_bytes()
    files[BOB_VERSION_FILE] = f"{version}\n".encode()
    return files


def _files(root: Path) -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    for dirpath, _, filenames in os.walk(root):
        base = Path(dirpath)
        for name in filenames:
            path = base / name
            if _regular(path):
                found[str(path.relative_to(root))] = path.read_bytes()
    return found


def _replace(dest: Path, skill: Path, attribution: list[Path], version: str) -> None:
    name = skill.name
    pid = os.getpid()
    tmp = dest / f".{name}.bob-tmp-{pid}"
    old = dest / f".{name}.bob-old-{pid}"
    tmp.mkdir()
    _fill(tmp, skill, attribution, version)
    target = dest / name
    if target.exists():
        os.replace(target, old)
    os.replace(tmp, target)
    if old.exists():
        _remove_path(old)


def _fill(tmp: Path, skill: Path, attribution: list[Path], version: str) -> None:
    for dirpath, dirnames, filenames in os.walk(skill):
        rel = Path(dirpath).relative_to(skill)
        for name in dirnames:
            (tmp / rel / name).mkdir()
        for name in filenames:
            shutil.copy2(Path(dirpath) / name, tmp / rel / name)
    for path in attribution:
        shutil.copy2(path, tmp / path.name)
    (tmp / BOB_VERSION_FILE).write_bytes(f"{version}\n".encode())


def _apply_foreign(dest: Path, names: set[str], preserved: list[Path]) -> None:
    for child in list(dest.iterdir()):
        _consider(child, names, preserved)


def _consider(child: Path, names: set[str], preserved: list[Path]) -> None:
    if child.name.startswith(".") or child.name in names:
        return
    if _retired(child):
        _remove_path(child)
        return
    preserved.append(child)


def _retired(child: Path) -> bool:
    return _real_dir(child) and _has_marker(child)


def _real_dir(path: Path) -> bool:
    return _kind_is(path, _S_IFDIR)


def _duplicates(project: Path, skills: dict[Path, list[Path]]) -> tuple[Path, ...]:
    found: list[Path] = []
    names = [skill.name for skill in skills]
    for root in DUPLICATE_ROOTS:
        for name in names:
            candidate = project / root / name
            if _duplicate(candidate):
                found.append(candidate)
    return tuple(found)


def _duplicate(path: Path) -> bool:
    return _real_dir(path) and _regular(path / "SKILL.md")


def _assemble(
    installed: list[str],
    unchanged: list[str],
    preserved: list[Path],
    unmarked: list[Path],
    duplicates: tuple[Path, ...],
) -> SkillsResult:
    ordered = tuple(sorted(preserved))
    kept = set(unmarked)
    return SkillsResult(
        installed=tuple(installed),
        unchanged=tuple(unchanged),
        preserved=ordered,
        duplicates=duplicates,
        unmarked=tuple(path for path in ordered if path in kept),
    )


if __name__ == "__main__":
    sys.exit(main())
