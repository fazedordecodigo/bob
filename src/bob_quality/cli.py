"""CLI `bob`: orquestra check, crap e dry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bob_quality.check import run_check


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

    dry = sub.add_parser("dry", help="Reporta clones novos no diff, sem bloquear")
    _add_shared(dry)

    return parser


def _add_shared(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base", default=None)
    parser.add_argument("--config", default=None)
    parser.add_argument("--out", default=".bob/")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cwd = Path.cwd()
    return _dispatch(args, cwd, _resolve_out(cwd, args.out), _resolve_config(cwd, args.config))


def _resolve_out(cwd: Path, raw: str) -> Path:
    out_dir = Path(raw)
    if out_dir.is_absolute():
        return out_dir
    return cwd / out_dir


def _resolve_config(cwd: Path, raw: str | None) -> Path | None:
    if raw is None:
        return None
    path = Path(raw)
    if path.is_absolute():
        return path
    return cwd / path


def _dispatch(
    args: argparse.Namespace,
    cwd: Path,
    out_dir: Path,
    config_path: Path | None,
) -> int:
    if args.command == "check":
        return _run_check(args, cwd, out_dir, config_path)
    if args.command == "crap":
        return _run_crap(args, cwd, out_dir, config_path)
    if args.command == "dry":
        return _run_dry(args, cwd, out_dir, config_path)
    raise AssertionError("comando não tratado")


def _run_check(
    args: argparse.Namespace,
    cwd: Path,
    out_dir: Path,
    config_path: Path | None,
) -> int:
    gates = [part.strip() for part in args.gates.split(",")] if args.gates else None
    return run_check(
        cwd=cwd,
        base=args.base,
        gates=gates,
        config_path=config_path,
        out_dir=out_dir,
        fmt=args.format,
        reproduce=_reproduce("check", args),
    )


def _run_crap(
    args: argparse.Namespace,
    cwd: Path,
    out_dir: Path,
    config_path: Path | None,
) -> int:
    coverage = Path(args.coverage_file) if args.coverage_file else None
    return run_check(
        cwd=cwd,
        base=args.base,
        gates=["crap"],
        config_path=config_path,
        out_dir=out_dir,
        fmt="both",
        threshold=args.threshold,
        coverage_file=coverage,
        reproduce=_reproduce("crap", args),
    )


def _run_dry(
    args: argparse.Namespace,
    cwd: Path,
    out_dir: Path,
    config_path: Path | None,
) -> int:
    return run_check(
        cwd=cwd,
        base=args.base,
        gates=["dry"],
        config_path=config_path,
        out_dir=out_dir,
        fmt="both",
        reproduce=_reproduce("dry", args),
    )


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
    return " ".join(parts)


if __name__ == "__main__":
    sys.exit(main())
