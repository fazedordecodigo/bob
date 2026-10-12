"""Copia as skills do plugin bob para a pasta de skills de cada agente no projeto.

Roda como `python -m bob_quality.install_skills` ou direto de um clone
(`python3 src/bob_quality/install_skills.py`), por isso usa só a stdlib.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
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


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        skills = _skills(args.source)
    except SourceError as exc:
        print(str(exc), file=sys.stderr)
        return CONFIG_ERROR
    for skill, attribution in skills.items():
        if attribution:
            continue
        print(
            f"aviso: a skill {skill.name} não tem LICENSE entre a pasta dela e a raiz do plugin "
            f"{args.source}; instalada sem licença.",
            file=sys.stderr,
        )
    for dest in dict.fromkeys(TARGETS[name] for name in args.targets):
        _install(skills, args.project / dest)
        print(f"{len(skills)} skills em {dest}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument("--source", type=Path, default=PLUGIN_ROOT)
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
    if notice.is_file() and notice.read_bytes() == RETIRED_NOTICE:
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
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill, target)
        for path in attribution:
            shutil.copy2(path, target / path.name)


if __name__ == "__main__":
    sys.exit(main())
