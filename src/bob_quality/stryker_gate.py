"""Mutação TypeScript: Stryker incremental em cima do diff.

O cache `.bob/mutation-cache.json` não é escrito aqui. O arquivo
incremental é do processo do Stryker.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from bob_quality.adapters.lizard import LizardParseError, parse_lizard_csv
from bob_quality.adapters.stryker import StrykerParseError, mutants_from_report
from bob_quality.config import Config
from bob_quality.deps_gate import _TS_EXTENSIONS
from bob_quality.diff import function_is_changed
from bob_quality.exit_codes import BASELINE_BROKEN, CONFIG_OR_TOOL
from bob_quality.messages import Text, msg, reason
from bob_quality.models import CyclomaticFunction, GateResult
from bob_quality.mutate import MutationOutcome, _finish, _outcome
from bob_quality.npm_tools import (
    _user_vitest_config,
    installed_npm_version,
    node_missing_message,
    npm_prefix,
)
from bob_quality.probe import relative_path
from bob_quality.tools import ToolError, run_lizard_csv
from bob_quality.waivers import Waiver, WaiverError, apply_waivers, load_waivers

INCREMENTAL_NAME = "stryker-incremental.json"
REPORT_NAME = "stryker-report.json"
CONFIG_NAME = "stryker.config.json"
TEMP_NAME = "stryker-tmp"
MUTATE_EXTENSIONS = _TS_EXTENSIONS
_PLUGIN = Path(__file__).resolve().parent / "js" / "stryker-vitest5-plugin.mjs"
# Frase do ConfigError em @stryker-mutator/core 10.0.0 (3-dry-run-executor).
_DRY_RUN_FAILED = "There were failed tests in the initial test run."
_CORE = "@stryker-mutator/core"
_RUNNER = "@stryker-mutator/vitest-runner"


def run_typescript_mutation(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
    out_dir: Path,
    *,
    python_measured: bool,
) -> tuple[MutationOutcome | None, Text | None]:
    """`(outcome, None)` quando o TypeScript rodou. `(None, motivo)` é skip."""
    if "typescript" not in config.languages:
        return None, None
    missing = _missing_tool()
    if missing is not None:
        if python_measured:
            return None, missing
        return _not_run(missing, {}), None
    try:
        versions = _versions()
        waivers = load_waivers(cwd)
    except (ToolError, WaiverError) as exc:
        return _not_run(reason(exc), {}), None
    waiver_rows = [item.as_dict() for item in waivers]
    try:
        spans = _changed_spans(cwd, config, diff_lines)
    except (ToolError, OSError, LizardParseError) as exc:
        return _not_run(reason(exc), versions, waiver_rows), None
    if not spans:
        return _finish([], [], [], versions, waiver_rows), None
    try:
        return _run(cwd, out_dir, spans, versions, waiver_rows, waivers), None
    except (OSError, json.JSONDecodeError, StrykerParseError) as exc:
        return _not_run(reason(exc), versions, waiver_rows), None


def _missing_tool() -> Text | None:
    missing = node_missing_message()
    if missing is not None:
        return missing
    try:
        prefix = npm_prefix()
        installed_npm_version(prefix, _CORE)
        installed_npm_version(prefix, _RUNNER)
    except ToolError as exc:
        return reason(exc)
    return None


def _versions() -> dict[str, str]:
    prefix = npm_prefix()
    return {
        "stryker": installed_npm_version(prefix, _CORE),
        "stryker-vitest-runner": installed_npm_version(prefix, _RUNNER),
    }


def _changed_spans(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
) -> list[CyclomaticFunction]:
    spans: list[CyclomaticFunction] = []
    seen: set[tuple[str, str, int, int]] = set()
    for language in ("typescript", "javascript"):
        raw = run_lizard_csv(cwd, list(config.include), list(config.exclude), language=language)
        for item in parse_lizard_csv(raw):
            file = relative_path(cwd, item.file)
            key = (file, item.name, item.start_line, item.end_line)
            if key in seen or not _script(file):
                continue
            seen.add(key)
            if not function_is_changed(file, item.start_line, item.end_line, diff_lines):
                continue
            spans.append(
                CyclomaticFunction(file, item.name, item.start_line, item.end_line, item.cc)
            )
    return spans


def _script(file: str) -> bool:
    path = file.replace("\\", "/")
    if path.endswith(".d.ts"):
        return False
    return path.endswith(MUTATE_EXTENSIONS)


def _run(
    cwd: Path,
    out_dir: Path,
    spans: list[CyclomaticFunction],
    versions: dict[str, str],
    waiver_rows: list[dict[str, object]],
    waivers: list[Waiver],
) -> MutationOutcome:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / REPORT_NAME
    incremental_path = out_dir / INCREMENTAL_NAME
    config_path = out_dir / CONFIG_NAME
    prefix = npm_prefix()
    _write_config(cwd, out_dir, config_path, incremental_path, report_path)
    argv = _argv(
        prefix,
        _relative(cwd, config_path),
        _relative(cwd, incremental_path),
        spans,
    )
    completed = _invoke(cwd, report_path, argv)
    if report_path.is_file():
        return _from_report(report_path, spans, versions, waiver_rows, waivers)
    if _dry_run_failed(completed):
        return _baseline(versions, waiver_rows)
    if incremental_path.is_file():
        incremental_path.unlink()
        completed = _invoke(cwd, report_path, argv)
        if report_path.is_file():
            return _from_report(report_path, spans, versions, waiver_rows, waivers)
        if _dry_run_failed(completed):
            return _baseline(versions, waiver_rows)
    return _not_run(msg("stryker.no_report"), versions, waiver_rows)


def _write_config(
    cwd: Path,
    out_dir: Path,
    config_path: Path,
    incremental_path: Path,
    report_path: Path,
) -> None:
    vitest: dict[str, object] = {"related": False}
    user_config = _user_vitest_config(cwd)
    if user_config is not None:
        vitest["configFile"] = str(user_config.resolve())
    payload = {
        "plugins": ["@stryker-mutator/*", str(_PLUGIN)],
        "testRunner": "vitest",
        "vitest": vitest,
        "coverageAnalysis": "perTest",
        "disableTypeChecks": True,
        "thresholds": {"break": None},
        "reporters": ["json"],
        "jsonReporter": {"fileName": _relative(cwd, report_path)},
        "tempDirName": _relative(cwd, out_dir / TEMP_NAME),
        "incremental": True,
        "incrementalFile": _relative(cwd, incremental_path),
    }
    config_path.write_text(json.dumps(payload, indent=2) + "\n")


def _argv(
    prefix: Path,
    config_file: str,
    incremental_file: str,
    spans: list[CyclomaticFunction],
) -> list[str]:
    # O commander do core 10.0.0 fica só com o último `--mutate` repetido.
    ranges = ",".join(f"{span.file}:{span.start_line}-{span.end_line}" for span in spans)
    return [
        "npx",
        "--prefix",
        str(prefix),
        "stryker",
        "run",
        config_file,
        "--incremental",
        "--incrementalFile",
        incremental_file,
        "--mutate",
        ranges,
    ]


def _invoke(
    cwd: Path, report_path: Path, argv: list[str]
) -> subprocess.CompletedProcess[str]:
    report_path.unlink(missing_ok=True)
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}
    return subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=env,
    )


def _dry_run_failed(completed: subprocess.CompletedProcess[str]) -> bool:
    return _DRY_RUN_FAILED in f"{completed.stdout}{completed.stderr}"


def _from_report(
    report_path: Path,
    spans: list[CyclomaticFunction],
    versions: dict[str, str],
    waiver_rows: list[dict[str, object]],
    waivers: list[Waiver],
) -> MutationOutcome:
    payload = json.loads(report_path.read_text())
    if not isinstance(payload, dict):
        raise StrykerParseError(msg("stryker.bad_report", detail=REPORT_NAME))
    mutants = apply_waivers(mutants_from_report(payload, spans), waivers)
    labels = [f"{span.file}::{span.name}" for span in spans]
    return _finish(mutants, labels, [], versions, waiver_rows)


def _baseline(
    versions: dict[str, str], waiver_rows: list[dict[str, object]]
) -> MutationOutcome:
    return _outcome(
        GateResult("mutate", "not_run", msg("probe.baseline_failed")),
        BASELINE_BROKEN,
        versions,
        waivers=waiver_rows,
    )


def _not_run(
    why: Text,
    versions: dict[str, str],
    waiver_rows: list[dict[str, object]] | None = None,
) -> MutationOutcome:
    return _outcome(
        GateResult("mutate", "not_run", why),
        CONFIG_OR_TOOL,
        versions,
        waivers=waiver_rows,
    )


def _relative(cwd: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(cwd.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())
