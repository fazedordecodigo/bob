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

# Mesmo valor de bob_quality.exit_codes.CONFIG_OR_TOOL. O script roda sem o pacote
# instalado e não pode importá-lo.
CONFIG_ERROR = 4


class SourceError(Exception):
    """A raiz do plugin não tem um manifesto com pastas de skills válidas."""


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        skills = _skill_dirs(args.source)
    except SourceError as exc:
        print(f"{exc}. Passe --source com a raiz do plugin bob.", file=sys.stderr)
        return CONFIG_ERROR
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


def _skill_dirs(source: Path) -> list[Path]:
    """Cada pasta de `skills` no manifesto, um nível: `<nome>/SKILL.md`, como os agentes leem."""
    manifest = source / MANIFEST
    skills: list[Path] = []
    for entry in _skill_entries(manifest):
        skills.extend(_skills_in(source / entry, manifest))
    return skills


def _skill_entries(manifest: Path) -> list[str]:
    data = _read_manifest(manifest)
    entries = data.get("skills") if isinstance(data, dict) else None
    if isinstance(entries, list) and all(isinstance(entry, str) for entry in entries):
        return entries
    raise SourceError(f"manifesto inválido (skills deve ser uma lista de pastas): {manifest}")


def _read_manifest(manifest: Path) -> object:
    try:
        raw = manifest.read_bytes()
    except OSError:
        raise SourceError(f"manifesto não encontrado: {manifest}") from None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def _skills_in(container: Path, manifest: Path) -> list[Path]:
    if not container.is_dir():
        raise SourceError(f"pasta de skills não encontrada: {container} (listada em {manifest})")
    return [child for child in container.iterdir() if (child / "SKILL.md").is_file()]


def _install(skills: list[Path], dest: Path) -> None:
    for skill in skills:
        target = dest / skill.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill, target)


if __name__ == "__main__":
    sys.exit(main())
