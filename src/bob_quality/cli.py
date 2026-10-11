"""CLI `bob`: orquestra check, crap e mutate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bob_quality.check import run_check
from bob_quality.exit_codes import CONFIG_OR_TOOL
from bob_quality.waivers import WaiverError, add_waiver


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bob",
        description="Gates de qualidade para agentes.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Roda os gates pedidos e grava .bob/")
    _add_shared(check)
    check.add_argument(
        "--gates",
        default=None,
        help="Lista separada por vírgula (padrão: crap,dry,deps)",
    )
    check.add_argument(
        "--format",
        default="both",
        choices=("md", "json", "both"),
    )

    crap = sub.add_parser("crap", help="Mede CRAP das funções alteradas")
    _add_shared(crap)
    crap.add_argument("--threshold", type=float, default=None)
    crap.add_argument("--coverage-file", default=None)

    mutate = sub.add_parser("mutate", help="Muta funções alteradas com mutmut")
    _add_shared(mutate)
    mutate.add_argument(
        "--since-last-run",
        action="store_true",
        help="Reusa o cache; já é o comportamento padrão",
    )
    mutate.add_argument("--max-workers", type=int, default=None)

    waive = sub.add_parser("waive", help="Registra um waiver com motivo de uma linha")
    waive.add_argument("target", help="id do mutante ou nome da função")
    waive.add_argument("--reason", default=None)

    return parser


def _add_shared(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base", default=None)
    parser.add_argument("--config", default=None)
    parser.add_argument("--out", default=".bob/")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cwd = Path.cwd()
    if args.command == "waive":
        return _waive_command(cwd, args)
    out_dir, config_path = _resolve_paths(cwd, args)
    return _dispatch(args, cwd, out_dir, config_path)


def _waive_command(cwd: Path, args: argparse.Namespace) -> int:
    try:
        add_waiver(cwd, args.target, args.reason)
    except WaiverError as exc:
        print(str(exc), file=sys.stderr)
        return CONFIG_OR_TOOL
    return 0


def _resolve_paths(cwd: Path, args: argparse.Namespace) -> tuple[Path, Path | None]:
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = cwd / out_dir
    config_path = Path(args.config) if args.config else None
    if config_path is not None and not config_path.is_absolute():
        config_path = cwd / config_path
    return out_dir, config_path


def _dispatch(
    args: argparse.Namespace,
    cwd: Path,
    out_dir: Path,
    config_path: Path | None,
) -> int:
    if args.command == "check":
        return _run_named("check", args, cwd, out_dir, config_path)
    if args.command == "crap":
        return _run_named("crap", args, cwd, out_dir, config_path)
    if args.command == "mutate":
        return _run_named("mutate", args, cwd, out_dir, config_path)
    raise AssertionError("comando não tratado")


def _run_named(
    command: str,
    args: argparse.Namespace,
    cwd: Path,
    out_dir: Path,
    config_path: Path | None,
) -> int:
    coverage_raw = getattr(args, "coverage_file", None) if command == "crap" else None
    return run_check(
        cwd=cwd,
        base=args.base,
        gates=_gates_for(command, args),
        config_path=config_path,
        out_dir=out_dir,
        fmt=getattr(args, "format", "both") if command == "check" else "both",
        threshold=getattr(args, "threshold", None) if command == "crap" else None,
        coverage_file=Path(coverage_raw) if coverage_raw else None,
        max_workers=getattr(args, "max_workers", None) if command == "mutate" else None,
        reproduce=_reproduce(command, args),
    )


def _gates_for(command: str, args: argparse.Namespace) -> list[str] | None:
    if command == "check":
        if not args.gates:
            return None
        return [part.strip() for part in args.gates.split(",")]
    if command == "crap":
        return ["crap"]
    return ["mutate"]


def _reproduce(command: str, args: argparse.Namespace) -> str:
    parts = ["bob", command]
    _append_flag(parts, "--base", getattr(args, "base", None))
    _append_flag(parts, "--gates", getattr(args, "gates", None))
    _append_flag(parts, "--config", getattr(args, "config", None))
    _append_flag(parts, "--out", getattr(args, "out", None), skip={".bob/", ".bob"})
    _append_flag(parts, "--format", getattr(args, "format", None), skip={"both"})
    _append_flag(parts, "--threshold", getattr(args, "threshold", None))
    _append_flag(parts, "--coverage-file", getattr(args, "coverage_file", None))
    _append_flag(parts, "--max-workers", getattr(args, "max_workers", None))
    if getattr(args, "since_last_run", False):
        parts.append("--since-last-run")
    return " ".join(parts)


def _append_flag(
    parts: list[str],
    flag: str,
    value: object,
    skip: set[object] | None = None,
) -> None:
    if value is None or (skip is not None and value in skip):
        return
    parts.extend([flag, str(value)])


if __name__ == "__main__":
    sys.exit(main())
