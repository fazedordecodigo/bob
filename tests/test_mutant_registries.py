from __future__ import annotations

import io
import socket
import urllib.error
import urllib.request

import pytest

from bob_quality.adapters.manifests import AddedPackage
from bob_quality.adapters.registries import (
    AdvisoriesFound,
    AdvisoriesUndecided,
    HttpFault,
    HttpOk,
    PackageExists,
    PackageUndecided,
    _band,
    _cvss2,
    _cvss3,
    _cvss3_base,
    _database_severity,
    _default_transport,
    _entry_score,
    _existence,
    _existence_url,
    _metrics,
    _names_package,
    _one_result,
    _parse_batch,
    _parse_score,
    _query,
    _query_batch,
    _round1,
    _roundup,
)


def test_band_uses_the_inclusive_cvss_boundaries() -> None:
    assert _band(None) is None
    assert _band(0.0) is None
    assert _band(0.1) == "LOW"
    assert _band(4.0) == "MODERATE"
    assert _band(7.0) == "HIGH"
    assert _band(9.0) == "CRITICAL"


def test_roundup_and_round1_keep_the_tenth() -> None:
    assert _roundup(0.0) == 0.0
    assert _roundup(0.1) == 0.1
    assert _roundup(0.01) == 0.1
    assert _roundup(0.00001) == 0.1
    assert _roundup(0.5) == 0.5
    assert _roundup(1.00001) == 1.1
    assert _round1(1.24) == 1.2


def test_cvss2_scores_a_partial_vector_and_a_zero_impact() -> None:
    assert _cvss2("AV:A/AC:H/Au:M/C:P/I:P/A:P") == 3.7
    assert _cvss2("AV:N/AC:L/Au:N/C:N/I:N/A:N") == 0.0


def test_cvss3_scores_unchanged_and_changed_scope() -> None:
    assert _cvss3("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H") == 9.8
    assert _cvss3("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H") == 10.0
    assert _cvss3("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H") == 8.8
    assert _cvss3("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H") == 9.9
    assert _cvss3("CVSS:3.1/AV:A/AC:H/PR:H/UI:R/S:C/C:L/I:L/A:N") == 3.7
    assert _cvss3("CVSS:3.1/AV:L/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N") == 1.8
    assert _cvss3("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N") == 0.0
    assert _cvss3("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:N/I:N/A:N") == 0.0


def test_cvss3_base_keeps_a_small_impact_and_caps_the_sum_at_ten() -> None:
    assert _cvss3_base(0.85, 0.77, 0.85, 0.85, 0.0, 0.0, 0.05, False) == 4.3
    assert _cvss3_base(1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, False) == 10.0


def test_metrics_drop_the_cvss_prefix_and_keep_later_pairs() -> None:
    assert _metrics("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H") == {
        "AV": "N",
        "AC": "L",
        "PR": "N",
        "UI": "N",
        "S": "U",
        "C": "H",
        "I": "H",
        "A": "H",
    }
    assert _metrics("AV:N/AC:L/junk/Au:N") == {"AV": "N", "AC": "L", "Au": "N"}
    assert _metrics("AV:N:X/AC:L") == {"AV": "N:X", "AC": "L"}


def test_parse_score_rejects_a_bool_and_keeps_an_int_and_a_numeric_string() -> None:
    assert _parse_score(True, "CVSS_V3") is None
    assert _parse_score(False, "CVSS_V3") is None
    assert _parse_score(1, "CVSS_V3") == 1.0
    assert _parse_score("7.5", "CVSS_V3") == 7.5


def test_database_severity_accepts_only_a_known_label() -> None:
    assert _database_severity({"severity": "MODERATE"}) == "MODERATE"
    assert _database_severity({"severity": "nope"}) is None
    assert _database_severity({"severity": ["MODERATE"]}) is None


def test_entry_score_requires_the_family_and_a_dict() -> None:
    assert _entry_score({"type": "CVSS_V3", "score": 7.5}, "CVSS_V3") == 7.5
    assert _entry_score({"type": "CVSS_V3", "score": True}, "CVSS_V3") is None
    assert _entry_score({"type": "CVSS_V2", "score": 7.5}, "CVSS_V3") is None
    assert _entry_score(["x"], "CVSS_V3") is None


def test_names_package_accepts_an_npm_name_and_a_pypi_info_name() -> None:
    assert _names_package(b'{"name":"left-pad"}') is True
    assert _names_package(b'{"info":{"name":"requests"}}') is True
    assert _names_package(b"not-json") is False
    assert _names_package(b"[]") is False
    assert _names_package(b'{"info":{"name":""}}') is False
    assert _names_package(b'{"info":{"name":1}}') is False


def test_existence_needs_status_200_and_a_package_name() -> None:
    assert _existence(HttpOk(200, b'{"name":"left-pad"}')) == PackageExists()
    assert _existence(HttpOk(200, b"{}")) == PackageUndecided("undecided")
    assert _existence(HttpOk(500, b'{"name":"left-pad"}')) == PackageUndecided("undecided")


def test_one_result_and_parse_batch_keep_an_empty_list_and_reject_a_bad_body() -> None:
    assert _one_result([]) == AdvisoriesUndecided("undecided")
    assert _one_result({"vulns": "no"}) == AdvisoriesUndecided("undecided")
    assert _one_result({}) == AdvisoriesFound(())
    assert _parse_batch(b"not-json", 2) == (
        AdvisoriesUndecided("undecided"),
        AdvisoriesUndecided("undecided"),
    )
    assert _parse_batch(b"[1]", 1) == (AdvisoriesUndecided("undecided"),)
    assert _parse_batch(b'{"results":[{"vulns":[]}]}', 1) == (AdvisoriesFound(()),)


def test_query_normalizes_a_pypi_name_and_keeps_an_npm_name() -> None:
    assert _query("pypi", AddedPackage("pypi", "Cool_Pkg", "1.2.3", "pyproject.toml", 4)) == {
        "package": {"name": "cool-pkg", "ecosystem": "PyPI"},
        "version": "1.2.3",
    }
    assert _query("npm", AddedPackage("npm", "Cool_Pkg", "1.2.3", "package.json", 2)) == {
        "package": {"name": "Cool_Pkg", "ecosystem": "npm"},
        "version": "1.2.3",
    }


def test_query_batch_marks_a_non_200_as_undecided() -> None:
    seen: list[tuple[str, str, bytes | None, int]] = []

    def transport(method: str, url: str, body: bytes | None, timeout: int) -> HttpOk:
        seen.append((method, url, body, timeout))
        return HttpOk(503, b"down")

    package = AddedPackage("pypi", "Cool_Pkg", "1.2.3", "pyproject.toml", 4)

    assert _query_batch("pypi", (package,), 12, transport) == (AdvisoriesUndecided("undecided"),)
    assert seen == [
        (
            "POST",
            "https://api.osv.dev/v1/querybatch",
            b'{"queries": [{"package": {"name": "cool-pkg", "ecosystem": "PyPI"}, "version": "1.2.3"}]}',
            12,
        )
    ]


def test_existence_url_quotes_the_name_and_leaves_an_at_sign() -> None:
    assert _existence_url(AddedPackage("npm", "@scope/left-pad", None, "package.json", 1)) == (
        "https://registry.npmjs.org/@scope%2Fleft-pad"
    )
    assert _existence_url(AddedPackage("pypi", "Cool_Pkg", None, "pyproject.toml", 2)) == (
        "https://pypi.org/pypi/cool-pkg/json"
    )


def test_default_transport_sends_the_method_and_reads_the_error_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[urllib.request.Request] = []

    def urlopen(request: urllib.request.Request, timeout: int) -> _Body:
        seen.append(request)
        assert timeout == 9
        if request.full_url.endswith("/error"):
            raise urllib.error.HTTPError(
                request.full_url, 404, "missing", {}, io.BytesIO(b"missing")
            )
        if request.full_url.endswith("/slow"):
            raise urllib.error.URLError(socket.timeout("slow"))
        return _Body(200, b"ok")

    headers: list[str] = []
    real_add = urllib.request.Request.add_header

    def add_header(self: urllib.request.Request, key: str, value: str) -> None:
        headers.append(key)
        real_add(self, key, value)

    monkeypatch.setattr("bob_quality.adapters.registries.urllib.request.urlopen", urlopen)
    monkeypatch.setattr(urllib.request.Request, "add_header", add_header)

    assert _default_transport("POST", "https://example.test/empty", None, 9) == HttpOk(200, b"ok")
    assert seen[-1].get_method() == "POST"
    assert seen[-1].data is None

    assert _default_transport("GET", "https://example.test/body", b"{}", 9) == HttpOk(200, b"ok")
    assert seen[-1].get_method() == "GET"
    assert seen[-1].data == b"{}"
    assert seen[-1].full_url == "https://example.test/body"
    assert seen[-1].get_header("Content-type") == "application/json"
    assert headers == ["Content-Type"]

    assert _default_transport("GET", "https://example.test/error", None, 9) == HttpOk(404, b"missing")
    assert _default_transport("GET", "https://example.test/slow", None, 9) == HttpFault("timeout")


class _Body:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_Body":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False
