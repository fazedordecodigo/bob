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
    mutate.add_argument("--since-last-run", action="store_true")
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
        try:
            add_waiver(cwd, args.target, args.reason)
        except WaiverError as exc:
            print(str(exc), file=sys.stderr)
            return CONFIG_OR_TOOL
        return 0
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = cwd / out_dir
    config_path = Path(args.config) if args.config else None
    if config_path is not None and not config_path.is_absolute():
        config_path = cwd / config_path

    if args.command == "check":
        gates = [part.strip() for part in args.gates.split(",")] if args.gates else None
        reproduce = _reproduce("check", args)
        return run_check(
            cwd=cwd,
            base=args.base,
            gates=gates,
            config_path=config_path,
            out_dir=out_dir,
            fmt=args.format,
            reproduce=reproduce,
        )
    if args.command == "crap":
        coverage = Path(args.coverage_file) if args.coverage_file else None
        reproduce = _reproduce("crap", args)
        return run_check(
            cwd=cwd,
            base=args.base,
            gates=["crap"],
            config_path=config_path,
            out_dir=out_dir,
            fmt="both",
            threshold=args.threshold,
            coverage_file=coverage,
            reproduce=reproduce,
        )
    if args.command == "mutate":
        reproduce = _reproduce("mutate", args)
        return run_check(
            cwd=cwd,
            base=args.base,
            gates=["mutate"],
            config_path=config_path,
            out_dir=out_dir,
            fmt="both",
            max_workers=args.max_workers,
            reproduce=reproduce,
        )
    raise AssertionError("comando não tratado")


def _reproduce(command: str, args: argparse.Namespace) -> str:
    parts = ["bob", command]
    if getattr(args, "base", None):
        parts.extend(["--base", args.base])
    if getattr(args, "gates", None):
        parts.extend(["--gates", args.gates])
    if getattr(args, "config", None):
        parts.extend(["--config", args.config])
    if getattr(args, "out", None) and args.out not in {".bob/", ".bob"}:
        parts.extend(["--out", args.out])
    if getattr(args, "format", None) and args.format != "both":
        parts.extend(["--format", args.format])
    if getattr(args, "threshold", None) is not None:
        parts.extend(["--threshold", str(args.threshold)])
    if getattr(args, "coverage_file", None):
        parts.extend(["--coverage-file", args.coverage_file])
    if getattr(args, "since_last_run", False):
        parts.append("--since-last-run")
    if getattr(args, "max_workers", None) is not None:
        parts.extend(["--max-workers", str(args.max_workers)])
    return " ".join(parts)


if __name__ == "__main__":
    sys.exit(main())
