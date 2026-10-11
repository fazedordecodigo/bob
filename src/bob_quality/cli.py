"""CLI `bob`: orquestra check, crap e doctor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bob_quality.check import run_check
from bob_quality.doctor import run_doctor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bob",
        description="Gates de qualidade para agentes (CRAP nesta fatia).",
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

    doctor = sub.add_parser("doctor", help="Verifica as ferramentas pinadas e as versões instaladas")
    doctor.add_argument(
        "--install",
        action="store_true",
        help="Instala c8 e vitest com npm ci no pacote (ou num cache do usuário)",
    )

    return parser


def _add_shared(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base", default=None)
    parser.add_argument("--config", default=None)
    parser.add_argument("--out", default=".bob/")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        return run_doctor(install=args.install)
    return _run_measured(args)


def _run_measured(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    out_dir = _under_cwd(Path(args.out), cwd)
    config_path = _optional_path(args.config, cwd)
    runner = _MEASURED.get(args.command)
    if runner is None:
        raise AssertionError("comando não tratado")
    return runner(args, cwd, out_dir, config_path)


def _under_cwd(path: Path, cwd: Path) -> Path:
    if path.is_absolute():
        return path
    return cwd / path


def _optional_path(raw: str | None, cwd: Path) -> Path | None:
    if not raw:
        return None
    return _under_cwd(Path(raw), cwd)


_MEASURED = {}


def _run_check_command(
    args: argparse.Namespace,
    cwd: Path,
    out_dir: Path,
    config_path: Path | None,
) -> int:
    return run_check(
        cwd=cwd,
        base=args.base,
        gates=_split_gates(args.gates),
        config_path=config_path,
        out_dir=out_dir,
        fmt=args.format,
        reproduce=_reproduce("check", args),
    )


def _split_gates(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return _csv(raw)


def _csv(raw: str) -> list[str]:
    parts: list[str] = []
    for part in raw.split(","):
        parts.append(part.strip())
    return parts


def _coverage_file(raw: str | None) -> Path | None:
    if not raw:
        return None
    return Path(raw)


def _run_crap_command(
    args: argparse.Namespace,
    cwd: Path,
    out_dir: Path,
    config_path: Path | None,
) -> int:
    return run_check(
        cwd=cwd,
        base=args.base,
        gates=["crap"],
        config_path=config_path,
        out_dir=out_dir,
        fmt="both",
        threshold=args.threshold,
        coverage_file=_coverage_file(args.coverage_file),
        reproduce=_reproduce("crap", args),
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


_MEASURED["check"] = _run_check_command
_MEASURED["crap"] = _run_crap_command


if __name__ == "__main__":
    sys.exit(main())
