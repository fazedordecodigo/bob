from __future__ import annotations

import json
import math
import socket
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Union

from bob_quality.adapters.manifests import AddedPackage, pep503
from bob_quality.models import Severity, UndecidedCause

_OSV = "https://api.osv.dev/v1/querybatch"
_VULN = "https://api.osv.dev/v1/vulns/"
_NPM_SAFE = "@"
_SEVERITIES = frozenset({"CRITICAL", "HIGH", "MODERATE", "LOW"})
_AV3 = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}
_AC3 = {"L": 0.77, "H": 0.44}
_PR3 = {"N": 0.85, "L": 0.62, "H": 0.27}
_PR3_CHANGED = {"N": 0.85, "L": 0.68, "H": 0.5}
_UI3 = {"N": 0.85, "R": 0.62}
_CIA3 = {"H": 0.56, "L": 0.22, "N": 0.0}
_AV2 = {"L": 0.395, "A": 0.646, "N": 1.0}
_AC2 = {"H": 0.35, "M": 0.61, "L": 0.71}
_AU2 = {"M": 0.45, "S": 0.56, "N": 0.704}
_CIA2 = {"N": 0.0, "P": 0.275, "C": 0.66}


@dataclass(frozen=True)
class HttpOk:
    status: int
    body: bytes


@dataclass(frozen=True)
class HttpFault:
    cause: UndecidedCause


HttpResult = HttpOk | HttpFault
Transport = Callable[[str, str, bytes | None, int], HttpResult]


@dataclass(frozen=True)
class PackageExists:
    pass


@dataclass(frozen=True)
class PackageMissing:
    pass


@dataclass(frozen=True)
class PackageUndecided:
    cause: UndecidedCause


Existence = PackageExists | PackageMissing | PackageUndecided


@dataclass(frozen=True)
class DecidedAdvisory:
    advisory_id: str
    severity: Severity


@dataclass(frozen=True)
class UndecidedRecord:
    cause: UndecidedCause
    advisory_id: str


@dataclass(frozen=True)
class AdvisoriesFound:
    records: tuple[Union[DecidedAdvisory, UndecidedRecord], ...]


@dataclass(frozen=True)
class AdvisoriesUndecided:
    cause: UndecidedCause


AdvisoryProbe = AdvisoriesFound | AdvisoriesUndecided


def probe_existence(
    package: AddedPackage,
    timeout_seconds: int,
    transport: Transport | None = None,
) -> Existence:
    client = _default_transport if transport is None else transport
    result = client("GET", _existence_url(package), None, timeout_seconds)
    return _existence(result)


def probe_advisories(
    packages: tuple[AddedPackage, ...],
    timeout_seconds: int,
    transport: Transport | None = None,
) -> tuple[AdvisoryProbe, ...]:
    probes: list[AdvisoryProbe | None] = [None] * len(packages)
    grouped: dict[str, list[int]] = {"pypi": [], "npm": []}
    for index, package in enumerate(packages):
        if package.version is None:
            probes[index] = AdvisoriesUndecided("undecided")
            continue
        grouped[package.index].append(index)
    client = _default_transport if transport is None else transport
    for index, positions in grouped.items():
        _fill_batch(probes, packages, positions, index, timeout_seconds, client)
    return tuple(probe for probe in probes if probe is not None)


def _default_transport(method: str, url: str, body: bytes | None, timeout: int) -> HttpResult:
    request = urllib.request.Request(url, data=body, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return HttpOk(response.status, response.read())
    except urllib.error.HTTPError as exc:
        return HttpOk(exc.code, exc.read())
    except TimeoutError:
        return HttpFault("timeout")
    except urllib.error.URLError as exc:
        return HttpFault(_url_cause(exc))


def _url_cause(exc: urllib.error.URLError) -> UndecidedCause:
    reason = exc.reason
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(reason, socket.gaierror):
        return "dns"
    return "undecided"


def _existence_url(package: AddedPackage) -> str:
    if package.index == "pypi":
        name = urllib.parse.quote(pep503(package.name))
        return f"https://pypi.org/pypi/{name}/json"
    name = urllib.parse.quote(package.name, safe=_NPM_SAFE)
    return f"https://registry.npmjs.org/{name}"


def _existence(result: HttpResult) -> Existence:
    if isinstance(result, HttpFault):
        return PackageUndecided(result.cause)
    if result.status == 404:
        return PackageMissing()
    if result.status == 200 and _names_package(result.body):
        return PackageExists()
    return PackageUndecided("undecided")


def _names_package(body: bytes) -> bool:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    if isinstance(payload.get("name"), str) and payload["name"]:
        return True
    info = payload.get("info")
    return isinstance(info, dict) and isinstance(info.get("name"), str) and bool(info["name"])


def _fill_batch(
    probes: list[AdvisoryProbe | None],
    packages: tuple[AddedPackage, ...],
    positions: list[int],
    index: str,
    timeout: int,
    transport: Transport,
) -> None:
    if not positions:
        return
    batch = tuple(packages[item] for item in positions)
    answered = _query_batch(index, batch, timeout, transport)
    for position, probe in zip(positions, answered):
        probes[position] = probe


def _query_batch(
    index: str,
    packages: tuple[AddedPackage, ...],
    timeout: int,
    transport: Transport,
) -> tuple[AdvisoryProbe, ...]:
    body = json.dumps({"queries": [_query(index, package) for package in packages]}).encode()
    result = transport("POST", _OSV, body, timeout)
    if isinstance(result, HttpFault):
        return tuple(AdvisoriesUndecided(result.cause) for _package in packages)
    if result.status != 200:
        return tuple(AdvisoriesUndecided("undecided") for _package in packages)
    parsed = _parse_batch(result.body, len(packages))
    return tuple(_resolve(probe, timeout, transport) for probe in parsed)


def _query(index: str, package: AddedPackage) -> dict[str, object]:
    ecosystem = "PyPI" if index == "pypi" else "npm"
    name = pep503(package.name) if index == "pypi" else package.name
    return {"package": {"name": name, "ecosystem": ecosystem}, "version": package.version}


def _parse_batch(body: bytes, count: int) -> tuple[AdvisoryProbe, ...]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return _undecided_batch(count)
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list) or len(results) != count:
        return _undecided_batch(count)
    return tuple(_one_result(item) for item in results)


def _resolve(probe: AdvisoryProbe, timeout: int, transport: Transport) -> AdvisoryProbe:
    if isinstance(probe, AdvisoriesUndecided):
        return probe
    return AdvisoriesFound(
        tuple(_vuln_document(record.advisory_id, timeout, transport) for record in probe.records)
    )


def _vuln_document(
    advisory_id: str, timeout: int, transport: Transport
) -> DecidedAdvisory | UndecidedRecord:
    result = transport("GET", f"{_VULN}{advisory_id}", None, timeout)
    if isinstance(result, HttpFault):
        return UndecidedRecord(result.cause, advisory_id)
    if result.status != 200:
        return UndecidedRecord("undecided", advisory_id)
    document = _json_object(result.body)
    if document is None:
        return UndecidedRecord("undecided", advisory_id)
    record = _record(document)
    if isinstance(record, DecidedAdvisory):
        return record
    if isinstance(record, UndecidedRecord):
        return UndecidedRecord(record.cause, advisory_id)
    return UndecidedRecord("undecided", advisory_id)


def _json_object(body: bytes) -> dict[str, object] | None:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _undecided_batch(count: int) -> tuple[AdvisoryProbe, ...]:
    return tuple(AdvisoriesUndecided("undecided") for _index in range(count))


def _one_result(item: object) -> AdvisoryProbe:
    if not isinstance(item, dict) or not isinstance(item.get("vulns", []), list):
        return AdvisoriesUndecided("undecided")
    records = tuple(_record(vuln) for vuln in item.get("vulns", []) if isinstance(vuln, dict))
    kept = tuple(record for record in records if record is not None)
    return AdvisoriesFound(kept)


def _record(vuln: dict[str, object]) -> DecidedAdvisory | UndecidedRecord | None:
    advisory_id = _advisory_id(vuln)
    if advisory_id is None:
        return None
    severity = _severity(vuln)
    if severity is None:
        return UndecidedRecord("undecided", advisory_id)
    return DecidedAdvisory(advisory_id, severity)


def _advisory_id(vuln: dict[str, object]) -> str | None:
    names = _ids(vuln)
    for name in names:
        if name.startswith("GHSA-"):
            return name
    if names:
        return names[0]
    return None


def _ids(vuln: dict[str, object]) -> list[str]:
    names: list[str] = []
    if isinstance(vuln.get("id"), str):
        names.append(vuln["id"])
    aliases = vuln.get("aliases")
    if isinstance(aliases, list):
        names.extend(item for item in aliases if isinstance(item, str))
    return names


def _severity(vuln: dict[str, object]) -> Severity | None:
    label = _database_severity(vuln.get("database_specific"))
    if label is not None:
        return label
    score = _cvss_score(vuln.get("severity"), "CVSS_V3")
    if score is None:
        score = _cvss_score(vuln.get("severity"), "CVSS_V2")
    return _band(score)


def _database_severity(value: object) -> Severity | None:
    if not isinstance(value, dict):
        return None
    label = value.get("severity")
    if isinstance(label, str) and label in _SEVERITIES:
        return label
    return None


def _cvss_score(entries: object, family: str) -> float | None:
    if not isinstance(entries, list):
        return None
    for entry in entries:
        score = _entry_score(entry, family)
        if score is not None:
            return score
    return None


def _entry_score(entry: object, family: str) -> float | None:
    if not isinstance(entry, dict) or entry.get("type") != family:
        return None
    return _parse_score(entry.get("score"), family)


def _parse_score(score: object, family: str) -> float | None:
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        return float(score)
    if not isinstance(score, str):
        return None
    numeric = _numeric(score)
    if numeric is not None:
        return numeric
    if family == "CVSS_V3":
        return _cvss3(score)
    return _cvss2(score)


def _numeric(score: str) -> float | None:
    try:
        return float(score)
    except ValueError:
        return None


def _band(score: float | None) -> Severity | None:
    if score is None:
        return None
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MODERATE"
    if score >= 0.1:
        return "LOW"
    return None


def _cvss3(vector: str) -> float | None:
    metrics = _metrics(vector)
    changed = metrics.get("S") == "C"
    values = _cvss3_values(metrics, changed)
    if values is None:
        return None
    return _cvss3_base(*values, changed)


def _cvss3_values(metrics: dict[str, str], changed: bool) -> tuple[float, float, float, float, float, float, float] | None:
    privileges = _PR3_CHANGED if changed else _PR3
    try:
        return (
            _AV3[metrics["AV"]],
            _AC3[metrics["AC"]],
            privileges[metrics["PR"]],
            _UI3[metrics["UI"]],
            _CIA3[metrics["C"]],
            _CIA3[metrics["I"]],
            _CIA3[metrics["A"]],
        )
    except KeyError:
        return None


def _cvss3_base(
    attack: float,
    complexity: float,
    privileges: float,
    interaction: float,
    confidentiality: float,
    integrity: float,
    availability: float,
    changed: bool,
) -> float:
    impact_sub = 1 - (1 - confidentiality) * (1 - integrity) * (1 - availability)
    if changed:
        impact = 7.52 * (impact_sub - 0.029) - 3.25 * (impact_sub - 0.02) ** 15
    else:
        impact = 6.42 * impact_sub
    exploitability = 8.22 * attack * complexity * privileges * interaction
    if impact <= 0:
        return 0.0
    if changed:
        return _roundup(min(1.08 * (impact + exploitability), 10))
    return _roundup(min(impact + exploitability, 10))


def _cvss2(vector: str) -> float | None:
    metrics = _metrics(vector)
    try:
        impact = _cvss2_impact(metrics)
        exploitability = 20 * _AV2[metrics["AV"]] * _AC2[metrics["AC"]] * _AU2[metrics["Au"]]
    except KeyError:
        return None
    if impact == 0:
        return 0.0
    return _round1((0.6 * impact + 0.4 * exploitability - 1.5) * 1.176)


def _cvss2_impact(metrics: dict[str, str]) -> float:
    confidentiality = _CIA2[metrics["C"]]
    integrity = _CIA2[metrics["I"]]
    availability = _CIA2[metrics["A"]]
    return 10.41 * (1 - (1 - confidentiality) * (1 - integrity) * (1 - availability))


def _metrics(vector: str) -> dict[str, str]:
    found: dict[str, str] = {}
    parts = vector.split("/")
    if parts and parts[0].startswith("CVSS:"):
        parts = parts[1:]
    for part in parts:
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        found[key] = value
    return found


def _roundup(value: float) -> float:
    scaled = int(value * 100000 + 0.5)
    if scaled % 10000 == 0:
        return scaled / 100000
    return (scaled // 10000 + 1) / 10


def _round1(value: float) -> float:
    return math.floor(value * 10 + 0.5) / 10
