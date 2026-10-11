"""CLI `bob`: orquestra check, crap, dry, deps, mutate, waive e doctor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bob_quality.check import run_check
from bob_quality.doctor import run_doctor
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

    dry = sub.add_parser("dry", help="Reporta clones novos no diff, sem bloquear")
    _add_shared(dry)

    deps = sub.add_parser("deps", help="Verifica ciclos e regras de dependência")
    _add_shared(deps)

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

    doctor = sub.add_parser("doctor", help="Verifica as ferramentas pinadas e as versões instaladas")
    doctor.add_argument(
        "--install",
        action="store_true",
        help="Instala as ferramentas npm com npm ci no pacote (ou num cache do usuário)",
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
    cwd = Path.cwd()
    if args.command == "waive":
        return _waive_command(cwd, args)
    return _dispatch(args, cwd, _resolve_out(cwd, args.out), _resolve_config(cwd, args.config))


def _waive_command(cwd: Path, args: argparse.Namespace) -> int:
    try:
        add_waiver(cwd, args.target, args.reason)
    except WaiverError as exc:
        print(str(exc), file=sys.stderr)
        return CONFIG_OR_TOOL
    return 0


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
    if args.command == "deps":
        return _run_deps(args, cwd, out_dir, config_path)
    if args.command == "mutate":
        return _run_mutate(args, cwd, out_dir, config_path)
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


def _run_deps(
    args: argparse.Namespace,
    cwd: Path,
    out_dir: Path,
    config_path: Path | None,
) -> int:
    return run_check(
        cwd=cwd,
        base=args.base,
        gates=["deps"],
        config_path=config_path,
        out_dir=out_dir,
        fmt="both",
        reproduce=_reproduce("deps", args),
    )


def _run_mutate(
    args: argparse.Namespace,
    cwd: Path,
    out_dir: Path,
    config_path: Path | None,
) -> int:
    return run_check(
        cwd=cwd,
        base=args.base,
        gates=["mutate"],
        config_path=config_path,
        out_dir=out_dir,
        fmt="both",
        max_workers=args.max_workers,
        reproduce=_reproduce("mutate", args),
    )


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
