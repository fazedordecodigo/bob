from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from bob_quality.adapters.deptry import DeptryCapture, DeptryRun, run_deptry
from bob_quality.adapters.knip import KnipCapture, KnipDocument, KnipHit, run_knip
from bob_quality.adapters.manifests import AddedPackage, added_packages
from bob_quality.adapters.registries import (
    AdvisoriesFound,
    AdvisoriesUndecided,
    AdvisoryProbe,
    DecidedAdvisory,
    Existence,
    PackageMissing,
    PackageUndecided,
    Transport,
    UndecidedRecord,
    probe_advisories,
    probe_existence,
)
from bob_quality.adapters.runner import Runner, default_runner
from bob_quality.config import Config
from bob_quality.exit_codes import CONFIG_OR_TOOL, GATE_FAILED, PASSED
from bob_quality.messages import Text, msg
from bob_quality.models import (
    Advisory,
    GateResult,
    MissingPackage,
    RowBlock,
    RowWarn,
    RowWaived,
    SupplyFinding,
    SupplyLanguage,
    SupplyReport,
    SupplyRow,
    UndeclaredImport,
    UnverifiedAdvisory,
    UnverifiedExistence,
    Waiverable,
)
from bob_quality.waivers import Waiver, load_waivers

_FOUND_EXITS = frozenset({1})
_UNDECLARED = frozenset({"DEP001", "DEP003"})


@dataclass(frozen=True)
class Judgment:
    status: Literal["passed", "warn", "failed"]
    exit_code: Literal[0, 1]
    reason: Text | None
    rows: tuple[SupplyRow, ...]


def waiver_id(finding: Waiverable) -> str:
    if isinstance(finding, MissingPackage):
        return f"supply:missing:{finding.index}:{finding.name}"
    if isinstance(finding, UndeclaredImport):
        return f"supply:undeclared:{finding.file}:{finding.module}"
    return f"supply:osv:{finding.advisory_id}"


def supply_waiver_ids(waivers: tuple[Waiver, ...]) -> frozenset[str]:
    return frozenset(item.id for item in waivers if item.id.startswith("supply:"))


def judge(
    findings: tuple[SupplyFinding, ...],
    diff_lines: Mapping[str, set[int]],
    fail_severities: frozenset[str],
    waiver_ids: frozenset[str],
) -> Judgment:
    return _judgment(_rows(findings, diff_lines, fail_severities, waiver_ids))


def finish(
    judgment: Judgment,
    languages_measured: tuple[SupplyLanguage, ...],
) -> tuple[GateResult, Literal[0, 1, 4]]:
    if languages_measured:
        return _copy(judgment)
    return GateResult("supply", "not_run", msg("supply.unmeasured")), CONFIG_OR_TOOL


def tool_measured(exit_code: int, parsed: bool, found_exits: frozenset[int]) -> bool:
    if not parsed:
        return False
    return exit_code == 0 or exit_code in found_exits


def _rows(
    findings: tuple[SupplyFinding, ...],
    diff_lines: Mapping[str, set[int]],
    fail_severities: frozenset[str],
    waiver_ids: frozenset[str],
) -> tuple[SupplyRow, ...]:
    seen: set[tuple[object, ...]] = set()
    rows: list[SupplyRow] = []
    for finding in findings:
        if not _on_diff(finding, diff_lines):
            continue
        key = _dedupe_key(finding)
        if key in seen:
            continue
        seen.add(key)
        rows.append(_row(finding, fail_severities, waiver_ids))
    return tuple(rows)


def _on_diff(finding: SupplyFinding, diff_lines: Mapping[str, set[int]]) -> bool:
    return finding.line in diff_lines.get(finding.file, ())


def _dedupe_key(finding: SupplyFinding) -> tuple[object, ...]:
    if isinstance(finding, (MissingPackage, UnverifiedExistence)):
        return ("package", finding.index, finding.name)
    if isinstance(finding, UndeclaredImport):
        return ("undeclared", finding.file, finding.module, finding.line)
    if isinstance(finding, Advisory):
        return ("advisory", finding.advisory_id)
    return ("unverified-advisory", finding.index, finding.name, finding.advisory_id)


def _row(
    finding: SupplyFinding,
    fail_severities: frozenset[str],
    waiver_ids: frozenset[str],
) -> SupplyRow:
    if isinstance(finding, UnverifiedExistence):
        return RowWarn(finding)
    if isinstance(finding, UnverifiedAdvisory):
        return RowWarn(finding)
    if isinstance(finding, Advisory):
        return _advisory_row(finding, fail_severities, waiver_ids)
    return _block_or_waive(finding, waiver_ids)


def _advisory_row(
    finding: Advisory,
    fail_severities: frozenset[str],
    waiver_ids: frozenset[str],
) -> SupplyRow:
    if finding.severity in fail_severities:
        return _block_or_waive(finding, waiver_ids)
    return _warn_or_waive(finding, waiver_ids)


def _block_or_waive(finding: Waiverable, waiver_ids: frozenset[str]) -> RowBlock | RowWaived:
    identifier = waiver_id(finding)
    if identifier in waiver_ids:
        return RowWaived(finding, identifier)
    return RowBlock(finding)


def _warn_or_waive(finding: Advisory, waiver_ids: frozenset[str]) -> RowWarn | RowWaived:
    identifier = waiver_id(finding)
    if identifier in waiver_ids:
        return RowWaived(finding, identifier)
    return RowWarn(finding)


def _judgment(rows: tuple[SupplyRow, ...]) -> Judgment:
    blocked = _first_block(rows)
    if blocked is not None:
        return Judgment("failed", GATE_FAILED, _block_reason(blocked), rows)
    warnings = _warn_count(rows)
    if warnings:
        return Judgment("warn", PASSED, _warn_reason(warnings), rows)
    return Judgment("passed", PASSED, None, rows)


def _first_block(rows: tuple[SupplyRow, ...]) -> RowBlock | None:
    for row in rows:
        if isinstance(row, RowBlock):
            return row
    return None


def _warn_count(rows: tuple[SupplyRow, ...]) -> int:
    return sum(1 for row in rows if isinstance(row, RowWarn))


def _warn_reason(warnings: int) -> Text:
    if warnings == 1:
        return msg("supply.warn_one")
    return msg("supply.warn_many", count=warnings)


def _block_reason(row: RowBlock) -> Text:
    finding = row.finding
    if isinstance(finding, MissingPackage):
        return msg(
            "supply.block_missing",
            index=finding.index,
            name=finding.name,
            file=finding.file,
            line=finding.line,
        )
    if isinstance(finding, UndeclaredImport):
        return msg(
            "supply.block_undeclared",
            module=finding.module,
            file=finding.file,
            line=finding.line,
        )
    return msg(
        "supply.block_advisory",
        severity=finding.severity,
        advisory=finding.advisory_id,
        name=finding.name,
        file=finding.file,
        line=finding.line,
    )


def _copy(judgment: Judgment) -> tuple[GateResult, Literal[0, 1]]:
    return GateResult("supply", judgment.status, judgment.reason), judgment.exit_code


def run_supply_gate(
    cwd: Path,
    config: Config,
    diff_lines: Mapping[str, set[int]],
    base: str,
    runner: Runner | None = None,
    transport: Transport | None = None,
) -> tuple[GateResult, int, dict[str, str], SupplyReport]:
    process = default_runner if runner is None else runner
    client = transport
    measured: list[SupplyLanguage] = []
    skipped: list[SupplyLanguage] = []
    findings: list[SupplyFinding] = []
    versions: dict[str, str] = {}
    for language in config.languages:
        if _measure_language(
            language, cwd, config, diff_lines, base, process, client, findings, versions
        ):
            measured.append(language)
        else:
            skipped.append(language)
    languages = tuple(measured)
    judgment = judge(
        tuple(findings),
        diff_lines,
        frozenset(config.osv_fail_severities),
        supply_waiver_ids(tuple(load_waivers(cwd))),
    )
    result, code = finish(judgment, languages)
    return result, code, versions, SupplyReport(languages, tuple(skipped), _reported_rows(languages, judgment.rows))


def _measure_language(
    language: SupplyLanguage,
    cwd: Path,
    config: Config,
    diff_lines: Mapping[str, set[int]],
    base: str,
    runner: Runner,
    transport: Transport | None,
    findings: list[SupplyFinding],
    versions: dict[str, str],
) -> bool:
    if language == "python":
        capture = run_deptry(cwd, config.include, config.supply_timeout_seconds, runner)
        return _accept(
            capture, "deptry", "pypi", _deptry_findings, cwd, config, diff_lines, base, transport, findings, versions
        )
    if language == "typescript":
        capture = run_knip(cwd, config.supply_timeout_seconds, runner)
        return _accept(
            capture, "knip", "npm", _knip_findings, cwd, config, diff_lines, base, transport, findings, versions
        )
    return False


def _accept(
    capture: DeptryCapture | KnipCapture,
    tool: str,
    index: Literal["pypi", "npm"],
    collect: Callable[[Path, DeptryRun | KnipDocument], tuple[UndeclaredImport, ...]],
    cwd: Path,
    config: Config,
    diff_lines: Mapping[str, set[int]],
    base: str,
    transport: Transport | None,
    findings: list[SupplyFinding],
    versions: dict[str, str],
) -> bool:
    if not _captured(capture.exit_code, capture.parsed) or capture.document is None:
        return False
    versions[tool] = capture.document.version
    findings.extend(collect(cwd, capture.document))
    findings.extend(_registry_findings(cwd, config, diff_lines, base, index, transport))
    return True


def _captured(exit_code: int | None, parsed: bool) -> bool:
    if exit_code is None:
        return False
    return tool_measured(exit_code, parsed, _FOUND_EXITS)


def _deptry_findings(cwd: Path, document: DeptryRun) -> tuple[UndeclaredImport, ...]:
    rows: list[UndeclaredImport] = []
    for violation in document.violations:
        if violation.code not in _UNDECLARED or violation.line is None:
            continue
        rows.append(UndeclaredImport(_relative(cwd, violation.file), violation.module, violation.line))
    return tuple(rows)


def _knip_findings(cwd: Path, document: KnipDocument) -> tuple[UndeclaredImport, ...]:
    rows: list[UndeclaredImport] = []
    for item in document.files:
        rows.extend(_knip_file(cwd, item.file, item.by_type))
    return tuple(rows)


def _knip_file(
    cwd: Path, file: str, by_type: Mapping[str, tuple[KnipHit, ...]]
) -> tuple[UndeclaredImport, ...]:
    rows: list[UndeclaredImport] = []
    for kind in ("unlisted", "unresolved"):
        for hit in by_type.get(kind, ()):
            rows.extend(_knip_hit(cwd, file, kind, hit))
    return tuple(rows)


def _knip_hit(cwd: Path, file: str, kind: str, hit: KnipHit) -> tuple[UndeclaredImport, ...]:
    if kind == "unresolved" and (hit.name.startswith(".") or hit.name.startswith("/")):
        return ()
    if hit.line is not None:
        return (UndeclaredImport(file, hit.name, hit.line),)
    return tuple(
        UndeclaredImport(file, hit.name, number) for number in _import_lines(cwd, file, hit.name)
    )


def _import_lines(cwd: Path, file: str, specifier: str) -> tuple[int, ...]:
    path = cwd / file
    if not path.is_file():
        return ()
    numbers = []
    for number, text in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if specifier in text and _import_line(text):
            numbers.append(number)
    return tuple(numbers)


def _import_line(text: str) -> bool:
    stripped = text.strip()
    if stripped.startswith(("import ", "import(", "export ")):
        return True
    return " from " in stripped or "require(" in stripped


def _registry_findings(
    cwd: Path,
    config: Config,
    diff_lines: Mapping[str, set[int]],
    base: str,
    index: Literal["pypi", "npm"],
    transport: Transport | None,
) -> tuple[SupplyFinding, ...]:
    packages = added_packages(cwd, base, diff_lines, index, config.include, config.exclude)
    if not packages:
        return ()
    timeout = config.supply_timeout_seconds
    rows: list[SupplyFinding] = []
    existences: list[Existence] = []
    for package in packages:
        existence = probe_existence(package, timeout, transport)
        existences.append(existence)
        rows.extend(_existence_finding(package, existence))
    probes = probe_advisories(packages, timeout, transport)
    for package, existence, probe in zip(packages, existences, probes, strict=True):
        if _offline_package(existence, probe):
            continue
        rows.extend(_advisory_findings(package, probe))
    return tuple(rows)


def _offline_package(existence: Existence, probe: AdvisoryProbe) -> bool:
    return isinstance(existence, PackageUndecided) and isinstance(probe, AdvisoriesUndecided)


def _existence_finding(package: AddedPackage, existence: Existence) -> tuple[SupplyFinding, ...]:
    if isinstance(existence, PackageMissing):
        return (MissingPackage(package.index, package.name, package.file, package.line),)
    if isinstance(existence, PackageUndecided):
        return (
            UnverifiedExistence(
                package.index, package.name, package.file, package.line, existence.cause
            ),
        )
    return ()


def _advisory_findings(
    package: AddedPackage, probe: AdvisoriesFound | AdvisoriesUndecided
) -> tuple[SupplyFinding, ...]:
    if isinstance(probe, AdvisoriesUndecided):
        return (
            UnverifiedAdvisory(package.index, package.name, package.file, package.line, probe.cause),
        )
    return tuple(_advisory_record(package, record) for record in probe.records)


def _advisory_record(
    package: AddedPackage, record: DecidedAdvisory | UndecidedRecord
) -> SupplyFinding:
    if isinstance(record, DecidedAdvisory):
        return Advisory(
            record.advisory_id,
            package.index,
            package.name,
            record.severity,
            package.file,
            package.line,
        )
    return UnverifiedAdvisory(
        package.index,
        package.name,
        package.file,
        package.line,
        record.cause,
        record.advisory_id,
    )


def _reported_rows(
    languages: tuple[SupplyLanguage, ...], rows: tuple[SupplyRow, ...]
) -> tuple[SupplyRow, ...]:
    if not languages:
        return ()
    return rows


def _relative(cwd: Path, file: str) -> str:
    path = Path(file)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.relative_to(cwd).as_posix()
    except ValueError:
        return path.as_posix()
