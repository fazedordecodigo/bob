"""CLI `bob`: orquestra check, crap, dry, deps, mutate, waive e doctor."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from bob_quality.check import run_check
from bob_quality.config import Config, ConfigError, reject_config_types, resolve_language
from bob_quality.doctor import run_doctor
from bob_quality.exit_codes import CONFIG_OR_TOOL, PASSED
from bob_quality.messages import DEFAULT_LANGUAGE, Language, reason, render, t
from bob_quality.waivers import WaiverError, add_waiver, reject_waiver_syntax


class _Parser(argparse.ArgumentParser):
    class Help(Exception):
        pass

    class Usage(Exception):
        pass

    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        if message is not None:
            sys.stderr.write(message)
        if status == 0:
            raise self.Help
        raise self.Usage


@dataclass(frozen=True)
class _HelpShown:
    pass


@dataclass(frozen=True)
class _Rejected:
    pass


@dataclass(frozen=True)
class _Ready:
    lang: Language
    args: argparse.Namespace


_Invocation = _HelpShown | _Rejected | _Ready


def build_parser(lang: Language = DEFAULT_LANGUAGE) -> _Parser:
    parser = _Parser(
        prog="bob",
        description=t(lang, "cli.description"),
    )
    _add_lang(parser, lang)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help=t(lang, "cli.check"))
    _add_shared(check, lang)
    check.add_argument("--gates", help=t(lang, "cli.gates"))
    check.add_argument(
        "--format",
        default="both",
        choices=("md", "json", "both"),
    )

    crap = sub.add_parser("crap", help=t(lang, "cli.crap"))
    _add_shared(crap, lang)
    crap.add_argument("--threshold", type=_max_crap)
    crap.add_argument("--coverage-file")

    dry = sub.add_parser("dry", help=t(lang, "cli.dry"))
    _add_shared(dry, lang)

    deps = sub.add_parser("deps", help=t(lang, "cli.deps"))
    _add_shared(deps, lang)

    mutate = sub.add_parser("mutate", help=t(lang, "cli.mutate"))
    _add_shared(mutate, lang)
    mutate.add_argument(
        "--since-last-run",
        action="store_true",
        help=t(lang, "cli.since_last_run"),
    )
    mutate.add_argument("--max-workers", type=_max_workers)

    waive = sub.add_parser("waive", help=t(lang, "cli.waive"))
    waive.add_argument("target", help=t(lang, "cli.waive_target"))
    waive.add_argument("--reason")
    _add_lang(waive, lang)

    doctor = sub.add_parser("doctor", help=t(lang, "cli.doctor"))
    doctor.add_argument(
        "--install",
        action="store_true",
        help=t(lang, "cli.install"),
    )
    _add_lang(doctor, lang)

    return parser


# O mutmut abre um Pool com esse número de processos, e cada um segura dois
# descritores no processo pai. Com 256 arquivos abertos, o padrão do macOS, 128 já falham.
_WORKER_CEILING = 64


def _max_crap(text: str) -> float:
    try:
        return Config(max_crap=float(text)).max_crap
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid value: {text!r} (use a finite number greater than 0)"
        ) from None


def _max_workers(text: str) -> int:
    try:
        count = int(text)
        if 1 <= count <= _WORKER_CEILING:
            return count
    except ValueError:
        pass
    raise argparse.ArgumentTypeError(
        f"invalid value: {text!r} (use an integer from 1 to {_WORKER_CEILING})"
    )


def _add_shared(parser: argparse.ArgumentParser, lang: Language) -> None:
    parser.add_argument("--base", default=None)
    parser.add_argument("--config", default=None)
    parser.add_argument("--out", default=".bob/")
    _add_lang(parser, lang)


def _add_lang(parser: argparse.ArgumentParser, lang: Language) -> None:
    parser.add_argument("--lang", default=None, help=t(lang, "cli.lang"))


def _parse(argv: list[str] | None) -> _Invocation:
    try:
        lang = _language(argv)
        args = build_parser(lang).parse_args(argv)
    except ConfigError as exc:
        print(render(reason(exc), DEFAULT_LANGUAGE), file=sys.stderr)
        return _Rejected()
    except _Parser.Usage:
        return _Rejected()
    except _Parser.Help:
        return _HelpShown()
    return _Ready(lang, args)


def _stop_code(seen: _HelpShown | _Rejected) -> int:
    if isinstance(seen, _HelpShown):
        return PASSED
    if isinstance(seen, _Rejected):
        return CONFIG_OR_TOOL
    raise AssertionError(type(seen).__name__)


def main(argv: list[str] | None = None) -> int:
    seen = _parse(argv)
    if not isinstance(seen, _Ready):
        return _stop_code(seen)
    lang = seen.lang
    args = seen.args
    cwd = Path.cwd()
    blocked = _blocked_config(cwd, getattr(args, "config", None))
    if blocked is not None:
        return blocked
    if args.command == "doctor":
        return run_doctor(install=args.install, lang=lang)
    if args.command == "waive":
        return _waive_command(cwd, args, lang)
    return _dispatch(
        args, cwd, _resolve_out(cwd, args.out), _resolve_config(cwd, args.config), lang
    )


def _language(argv: list[str] | None) -> Language:
    """Lido antes do parser completo, para a ajuda já sair no idioma escolhido."""
    early = _Parser(prog="bob")
    early._option_string_actions.pop("-h")
    early._option_string_actions.pop("--help")
    early.add_argument("--lang")
    early.add_argument("--config")
    known, _rest = early.parse_known_args(argv)
    cwd = Path.cwd()
    return resolve_language(known.lang, _resolve_config(cwd, known.config), cwd)


def _blocked_config(cwd: Path, config: str | None) -> int | None:
    try:
        reject_config_types(_resolve_config(cwd, config), cwd)
        reject_waiver_syntax(cwd)
    except (ConfigError, WaiverError) as exc:
        print(render(reason(exc), DEFAULT_LANGUAGE), file=sys.stderr)
        return CONFIG_OR_TOOL
    return None


def _waive_command(cwd: Path, args: argparse.Namespace, lang: Language) -> int:
    try:
        add_waiver(cwd, args.target, args.reason)
    except WaiverError as exc:
        print(render(reason(exc), lang), file=sys.stderr)
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
    lang: Language,
) -> int:
    if args.command == "check":
        return _run_check(args, cwd, out_dir, config_path, lang)
    if args.command == "crap":
        return _run_crap(args, cwd, out_dir, config_path, lang)
    if args.command == "dry":
        return _run_dry(args, cwd, out_dir, config_path, lang)
    if args.command == "deps":
        return _run_deps(args, cwd, out_dir, config_path, lang)
    if args.command == "mutate":
        return _run_mutate(args, cwd, out_dir, config_path, lang)
    raise AssertionError("comando não tratado")


def _run_check(
    args: argparse.Namespace,
    cwd: Path,
    out_dir: Path,
    config_path: Path | None,
    lang: Language,
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
        lang=lang,
    )


def _run_crap(
    args: argparse.Namespace,
    cwd: Path,
    out_dir: Path,
    config_path: Path | None,
    lang: Language,
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
        lang=lang,
    )


def _run_dry(
    args: argparse.Namespace,
    cwd: Path,
    out_dir: Path,
    config_path: Path | None,
    lang: Language,
) -> int:
    return run_check(
        cwd=cwd,
        base=args.base,
        gates=["dry"],
        config_path=config_path,
        out_dir=out_dir,
        fmt="both",
        reproduce=_reproduce("dry", args),
        lang=lang,
    )


def _run_deps(
    args: argparse.Namespace,
    cwd: Path,
    out_dir: Path,
    config_path: Path | None,
    lang: Language,
) -> int:
    return run_check(
        cwd=cwd,
        base=args.base,
        gates=["deps"],
        config_path=config_path,
        out_dir=out_dir,
        fmt="both",
        reproduce=_reproduce("deps", args),
        lang=lang,
    )


def _run_mutate(
    args: argparse.Namespace,
    cwd: Path,
    out_dir: Path,
    config_path: Path | None,
    lang: Language,
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
        lang=lang,
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
