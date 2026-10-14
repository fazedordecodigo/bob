from __future__ import annotations

import importlib.metadata
import shutil
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from bob_quality.adapters.bandit import LABELS as _BANDIT_LABELS
from bob_quality.adapters.bandit import parse_bandit
from bob_quality.adapters.semgrep import LABELS as _SEMGREP_LABELS
from bob_quality.adapters.semgrep import parse_semgrep
from bob_quality.models import Finding

# Mesmos tokens de bandit.core.constants.EXCLUDE na 1.9.4. Importar o bandit carregaria o pacote em todo comando.
_BANDIT_EXCLUDE = (
    ".svn",
    "CVS",
    ".bzr",
    ".hg",
    ".git",
    "__pycache__",
    ".tox",
    ".eggs",
    "*.egg",
)
_SEMGREP_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
_MEASURED = frozenset({0, 1})
SEMGREP_VERSION = "1.180.0"
SEMGREP_RUNNER = "uvx"


@dataclass(frozen=True)
class InPlace:
    pass


@dataclass(frozen=True)
class DetachedHead:
    pass


RootPlan = InPlace | DetachedHead


@dataclass(frozen=True)
class ScanContext:
    exclude: tuple[str, ...]
    targets: tuple[str, ...]
    merge_base: str
    scan_root: Path
    empty_ini: Path
    suffixes: tuple[str, ...]


Argv = Callable[[ScanContext], list[str]]
Parse = Callable[[str, Path], tuple[Finding, ...]]
Installed = Callable[[], bool]


@dataclass(frozen=True)
class Scanner:
    tool: str
    language: str
    distribution: str
    labels: tuple[str, ...]
    measurement_exits: frozenset[int]
    needs_baseline: bool
    root: RootPlan
    rules_dir: str | None
    suffixes: tuple[str, ...] | None
    argv: Argv
    parse: Parse
    installed: Installed
    pinned_version: str | None = None
    runner: str | None = None


def _bandit_argv(ctx: ScanContext) -> list[str]:
    excluded = ",".join((*_BANDIT_EXCLUDE, *ctx.exclude))
    return [
        sys.executable,
        "-m",
        "bandit",
        "--recursive",
        "--format",
        "json",
        "--quiet",
        "--severity-level",
        "all",
        "--confidence-level",
        "all",
        "--ignore-nosec",
        "--ini",
        str(ctx.empty_ini),
        "--exclude",
        excluded,
        *ctx.targets,
    ]


def _semgrep_argv(ctx: ScanContext) -> list[str]:
    argv = [
        SEMGREP_RUNNER,
        "--from",
        f"semgrep=={SEMGREP_VERSION}",
        "semgrep",
        "scan",
        "--disable-version-check",
        "--metrics=off",
        "--disable-nosem",
        "--error",
        "--quiet",
        "--json",
        "--baseline-commit",
        ctx.merge_base,
        "--config",
        str(ctx.scan_root / ".semgrep"),
    ]
    for item in ctx.exclude:
        argv.extend(["--exclude", item])
    for suffix in ctx.suffixes:
        argv.extend(["--include", f"*{suffix}"])
    argv.extend(ctx.targets)
    return argv


def _distribution_installed(name: str) -> bool:
    try:
        importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


def _semgrep_installed() -> bool:
    return shutil.which(SEMGREP_RUNNER) is not None


def _bandit_installed() -> bool:
    return _distribution_installed("bandit")


_SCANNERS: tuple[Scanner, ...] = (
    Scanner(
        tool="bandit",
        language="python",
        distribution="bandit",
        labels=_BANDIT_LABELS,
        measurement_exits=_MEASURED,
        needs_baseline=False,
        root=InPlace(),
        rules_dir=None,
        suffixes=None,
        argv=_bandit_argv,
        parse=parse_bandit,
        installed=_bandit_installed,
    ),
    Scanner(
        tool="semgrep",
        language="typescript",
        distribution="semgrep",
        labels=_SEMGREP_LABELS,
        measurement_exits=_MEASURED,
        needs_baseline=True,
        root=DetachedHead(),
        rules_dir=".semgrep",
        suffixes=_SEMGREP_SUFFIXES,
        argv=_semgrep_argv,
        parse=parse_semgrep,
        installed=_semgrep_installed,
        pinned_version=SEMGREP_VERSION,
        runner=SEMGREP_RUNNER,
    ),
)


def _reject_bad_table(rows: tuple[Scanner, ...]) -> None:
    seen_languages: set[str] = set()
    for row in rows:
        if row.language in seen_languages:
            raise RuntimeError(f"duplicate scanner language: {row.language}")
        seen_languages.add(row.language)
        if len(set(row.labels)) != len(row.labels):
            raise RuntimeError(f"duplicate severity label: {row.tool}")
        if len(row.measurement_exits) == 0:
            raise RuntimeError(f"empty measurement exits: {row.tool}")


_reject_bad_table(_SCANNERS)


def severity_vocabulary() -> tuple[str, ...]:
    seen: list[str] = []
    for row in _SCANNERS:
        for label in row.labels:
            if label not in seen:
                seen.append(label)
    return tuple(seen)


def scanners_for(languages: tuple[str, ...]) -> tuple[Scanner, ...]:
    chosen = set(languages)
    return tuple(row for row in _SCANNERS if row.language in chosen)


def distribution_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None
