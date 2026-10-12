"""Gate de segredos: o veredito sai da partição, não do exit do gitleaks."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from bob_quality.config import Config
from bob_quality.diff import function_is_changed
from bob_quality.exit_codes import CONFIG_OR_TOOL, GATE_FAILED, PASSED
from bob_quality.messages import Text, msg, reason
from bob_quality.models import SECRET_PREFIX, GateResult, SecretLedger, SecretRow
from bob_quality.waivers import WaiverError, load_waivers

_VERSION = re.compile(r"\d+\.\d+(?:\.\d+)?")
_DROPPED_ENV = frozenset({"GITLEAKS_CONFIG", "GITLEAKS_CONFIG_TOML"})


@dataclass(frozen=True)
class SecretsJudgment:
    """Resultado puro. Exit 4 não cabe aqui."""

    ledger: SecretLedger
    result: GateResult
    exit_code: int

    def __post_init__(self) -> None:
        blocked = bool(self.ledger.blocking)
        if self.result.name != "secrets":
            raise ValueError("secrets")
        if blocked:
            if self.exit_code != GATE_FAILED or self.result.status != "failed":
                raise ValueError("blocking rows are exit 1")
            return
        if self.exit_code != PASSED or self.result.status != "passed":
            raise ValueError("no blocking rows is exit 0")


def judge_secrets(
    findings: tuple[SecretRow, ...],
    diff_lines: dict[str, set[int]],
    waiver_ids: frozenset[str],
) -> SecretsJudgment:
    """Parte as linhas e tira o exit só de `blocking`."""
    applicable = {item for item in waiver_ids if item.startswith(SECRET_PREFIX)}
    blocking: list[SecretRow] = []
    outside: list[SecretRow] = []
    for row in _deduped(findings):
        if row.waiver_id() in applicable:
            continue
        if function_is_changed(row.file, row.line, row.line, diff_lines):
            blocking.append(row)
        else:
            outside.append(row)
    blocked = bool(blocking)
    return SecretsJudgment(
        SecretLedger(tuple(blocking), tuple(outside)),
        GateResult(
            "secrets",
            "failed" if blocked else "passed",
            _reason(len(blocking), len(outside)),
        ),
        GATE_FAILED if blocked else PASSED,
    )


def _deduped(findings: tuple[SecretRow, ...]) -> tuple[SecretRow, ...]:
    chosen: dict[str, SecretRow] = {}
    for row in findings:
        chosen.setdefault(row.waiver_id(), row)
    return tuple(sorted(chosen.values(), key=lambda row: (row.file, row.line, row.rule_id)))


def _reason(blocking: int, outside: int) -> Text | None:
    new = _count_reason(blocking, "secrets.new_one", "secrets.new_many")
    old = _count_reason(outside, "secrets.outside_one", "secrets.outside_many")
    if new is None:
        return old
    if old is None:
        return new
    return msg("probe.joined", first=new, second=old)


def _count_reason(count: int, one: str, many: str) -> Text | None:
    if count == 0:
        return None
    if count == 1:
        return msg(one)
    return msg(many, count=count)


@dataclass(frozen=True)
class SecretsRun:
    """O que o check guarda.

    `ledger is None` é `not_run` e exit 4. Com ledger, o exit é 1 só quando
    `blocking` não está vazio.
    """

    result: GateResult
    ledger: SecretLedger | None
    exit_code: int
    versions: dict[str, str]

    def __post_init__(self) -> None:
        if self.result.name != "secrets":
            raise ValueError("secrets")
        if self.ledger is None:
            if self.exit_code != CONFIG_OR_TOOL or self.result.status != "not_run":
                raise ValueError("unmeasured secrets is exit 4")
            return
        SecretsJudgment(self.ledger, self.result, self.exit_code)


class GitleaksParseError(Exception):
    """O corpo não é o array de achados que este gate aceita."""


def run_secrets_gate(
    cwd: Path,
    config: Config,
    diff_lines: dict[str, set[int]],
) -> SecretsRun:
    """Varre `paths.include` e julga. O JSON bruto morre no diretório temporário."""
    roots = _roots(cwd, config)
    if isinstance(roots, Text):
        return _unmeasured(roots)
    if _gitleaks_ignore(roots):
        return _unmeasured(msg("secrets.gitleaksignore"))
    binary = shutil.which("gitleaks")
    if binary is None:
        return _unmeasured(msg("tool.missing", tool="gitleaks"))
    version = _read_version(binary)
    if version is None:
        return _unmeasured(msg("secrets.version"))
    versions = {"gitleaks": version}
    try:
        waiver_ids = frozenset(item.id for item in load_waivers(cwd))
    except WaiverError as exc:
        return _unmeasured(reason(exc), versions)
    with tempfile.TemporaryDirectory(prefix="bob-gitleaks-") as tmp:
        found = _scan_roots(Path(tmp), binary, roots, cwd, config)
    if found is None:
        return _unmeasured(msg("secrets.unreadable"), versions)
    judgment = judge_secrets(found, diff_lines, waiver_ids)
    return SecretsRun(judgment.result, judgment.ledger, judgment.exit_code, versions)


def _unmeasured(why: Text, versions: dict[str, str] | None = None) -> SecretsRun:
    return SecretsRun(
        GateResult("secrets", "not_run", why),
        None,
        CONFIG_OR_TOOL,
        versions or {},
    )


def _roots(cwd: Path, config: Config) -> list[Path] | Text:
    missing: list[str] = []
    roots: list[Path] = []
    for name in config.include:
        root = (cwd / name).resolve()
        if not root.is_dir():
            missing.append(name)
            continue
        roots.append(root)
    if missing:
        return msg("secrets.include_missing", paths=", ".join(missing))
    return roots


def _gitleaks_ignore(roots: list[Path]) -> bool:
    for root in roots:
        if (root / ".gitleaksignore").is_file():
            return True
    return False


def _read_version(binary: str) -> str | None:
    try:
        completed = subprocess.run(
            [binary, "--version"],
            check=False,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            env=_child_env(),
        )
    except OSError:
        return None
    match = _VERSION.search(completed.stdout + "\n" + completed.stderr)
    if match is None:
        return None
    return match.group(0)


def _scan_roots(
    tmp: Path,
    binary: str,
    roots: list[Path],
    cwd: Path,
    config: Config,
) -> tuple[SecretRow, ...] | None:
    config_file = tmp / "scope.toml"
    config_file.write_text(_scope_toml(config))
    ignore_dir = tmp / "ignore"
    ignore_dir.mkdir()
    report = tmp / "gitleaks.json"
    rows: list[SecretRow] = []
    for source in roots:
        found = _scan(binary, source, report, config_file, ignore_dir, cwd)
        if found is None:
            return None
        rows.extend(found)
    return tuple(rows)


def _scan(
    binary: str,
    source: Path,
    report: Path,
    config_file: Path,
    ignore_dir: Path,
    cwd: Path,
) -> tuple[SecretRow, ...] | None:
    if report.exists():
        report.unlink()
    try:
        completed = subprocess.run(
            _argv(binary, source, report, config_file, ignore_dir),
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            env=_child_env(),
        )
    except OSError:
        return None
    raw = _read_report(report)
    return _classify(completed.returncode, raw, cwd)


def _argv(
    binary: str,
    source: Path,
    report: Path,
    config_file: Path,
    ignore_dir: Path,
) -> list[str]:
    return [
        binary,
        "detect",
        "--no-git",
        "--source",
        str(source),
        "--config",
        str(config_file),
        "--report-format",
        "json",
        "--report-path",
        str(report),
        "--exit-code",
        "1",
        "--redact",
        "--no-banner",
        "--ignore-gitleaks-allow",
        "--gitleaks-ignore-path",
        str(ignore_dir),
    ]


def _read_report(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        return path.read_text()
    except UnicodeDecodeError:
        return None


def _classify(code: int, raw: str | None, cwd: Path) -> tuple[SecretRow, ...] | None:
    if code not in {0, 1} or raw is None:
        return None
    try:
        return _parse_gitleaks_json(raw, cwd)
    except GitleaksParseError:
        return None


def _parse_gitleaks_json(raw: str, cwd: Path) -> tuple[SecretRow, ...]:
    body = _json_array(raw)
    rows: list[SecretRow] = []
    for item in body:
        row = _finding_row(item, cwd)
        if row is not None:
            rows.append(row)
    return tuple(rows)


def _json_array(raw: str) -> list[object]:
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        raise GitleaksParseError(msg("secrets.unreadable")) from None
    if not isinstance(body, list):
        raise GitleaksParseError(msg("secrets.unreadable"))
    return body


def _finding_row(item: object, cwd: Path) -> SecretRow | None:
    if not isinstance(item, dict):
        raise GitleaksParseError(msg("secrets.unreadable"))
    file_name = _required_text(item, "File")
    rule_id = _required_text(item, "RuleID")
    start = _start_line(item)
    if start is None:
        return None
    return SecretRow(_repo_file(file_name, cwd), start, rule_id)


def _required_text(item: dict[str, object], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or value == "":
        raise GitleaksParseError(msg("secrets.unreadable"))
    return value


def _start_line(item: dict[str, object]) -> int | None:
    if "StartLine" not in item:
        raise GitleaksParseError(msg("secrets.unreadable"))
    start = item["StartLine"]
    if isinstance(start, bool) or not isinstance(start, int):
        raise GitleaksParseError(msg("secrets.unreadable"))
    if start < 1:
        return None
    return start


def _repo_file(name: str, cwd: Path) -> str:
    text = name.replace("\\", "/")
    if text.startswith("./"):
        text = text[2:]
    root = cwd.resolve()
    path = Path(text)
    if not path.is_absolute():
        path = root / path
    try:
        relative = path.resolve().relative_to(root)
    except (ValueError, OSError, RuntimeError):
        raise GitleaksParseError(msg("secrets.unreadable")) from None
    shown = relative.as_posix()
    if shown == ".":
        raise GitleaksParseError(msg("secrets.unreadable"))
    return shown


def _child_env() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if key not in _DROPPED_ENV and not key.startswith("PYTEST_")
    }


def _scope_toml(config: Config) -> str:
    names: list[str] = []
    for name in (*config.exclude, ".git", ".bob"):
        if name not in names:
            names.append(name)
    parts = [f"'''(^|/){re.escape(name)}(/|$)'''" for name in names]
    return "[extend]\nuseDefault = true\n[[allowlists]]\npaths = [ " + " , ".join(parts) + " ]\n"
