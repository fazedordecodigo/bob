"""Adaptadores do gate supply. O transporte e o processo são injetados."""

import json
import subprocess
from pathlib import Path

from bob_quality.adapters.deptry import (
    DeptryViolation,
    parse_deptry_json,
    run_deptry,
)
from bob_quality.adapters.knip import KnipHit, parse_knip_json, run_knip
from bob_quality.adapters.manifests import AddedPackage, added_packages
from bob_quality.adapters.registries import (
    AdvisoriesFound,
    AdvisoriesUndecided,
    DecidedAdvisory,
    HttpFault,
    HttpOk,
    PackageExists,
    PackageMissing,
    PackageUndecided,
    UndecidedRecord,
    probe_advisories,
    probe_existence,
)
from bob_quality.adapters.runner import ProcessExit, ProcessFault
from bob_quality.diff import changed_lines
from bob_quality.messages import msg, render

RAW = Path(__file__).parent / "fixtures" / "raw"
DEPTRY = (RAW / "deptry.json").read_text()
KNIP = (RAW / "knip.json").read_text()
OSV = (RAW / "osv-batch.json").read_bytes()


def test_parse_deptry_json_keeps_every_code_and_a_null_line() -> None:
    assert parse_deptry_json(DEPTRY) == (
        DeptryViolation("DEP001", "requests", "src/app.py", 3),
        DeptryViolation("DEP003", "pkg_resources", "src/app.py", None),
        DeptryViolation("DEP002", "unused", "pyproject.toml", 10),
    )


def test_parse_deptry_json_rejects_a_document_that_is_not_a_list() -> None:
    assert parse_deptry_json('{"violations": []}') is None


def test_run_deptry_returns_exit_1_and_ignores_dep002_not_dep003(tmp_path: Path) -> None:
    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit:
        assert timeout == 30
        if args[-1] == "--version":
            return ProcessExit(0, "deptry 0.25.1\n", "")
        assert args[1:3] == ["-m", "deptry"]
        assert args[3:5] == ["src", "lib"]
        assert args[args.index("--ignore") + 1] == "DEP002,DEP004,DEP005"
        Path(args[args.index("--json-output") + 1]).write_text(DEPTRY)
        return ProcessExit(1, "", "")

    capture = run_deptry(tmp_path, ("src", "lib"), 30, runner)

    assert capture.exit_code == 1
    assert capture.parsed is True
    assert capture.document is not None
    assert capture.document.version == "0.25.1"
    assert capture.document.violations[0] == DeptryViolation("DEP001", "requests", "src/app.py", 3)


def test_run_deptry_keeps_the_exit_when_the_json_does_not_parse(tmp_path: Path) -> None:
    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit | ProcessFault:
        if args[-1] == "--version":
            return ProcessExit(0, "deptry 0.25.1\n", "")
        Path(args[args.index("--json-output") + 1]).write_text("not-json")
        return ProcessExit(1, "", "")

    capture = run_deptry(tmp_path, ("src",), 30, runner)

    assert capture.exit_code == 1
    assert capture.parsed is False
    assert capture.document is None
    assert render(capture.detail, "en") == "deptry did not write parseable JSON"


def test_run_deptry_has_no_exit_when_the_process_times_out(tmp_path: Path) -> None:
    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit | ProcessFault:
        if args[-1] == "--version":
            return ProcessExit(0, "deptry 0.25.1\n", "")
        return ProcessFault(msg("tool.detail", tool="deptry", detail="timed out"))

    capture = run_deptry(tmp_path, ("src",), 30, runner)

    assert capture.exit_code is None
    assert capture.parsed is False
    assert render(capture.detail, "en") == "deptry: timed out"


def test_parse_knip_json_keeps_unlisted_unresolved_and_a_missing_line() -> None:
    document = parse_knip_json(KNIP)

    assert document is not None
    assert document[0].file == "src/app.ts"
    assert document[0].by_type["unlisted"] == (KnipHit("left-pad", 4, 20),)
    assert document[0].by_type["unresolved"] == (
        KnipHit("missing-pkg", 8, 1),
        KnipHit("./local", 9, 1),
    )
    assert document[0].by_type["dependencies"] == (KnipHit("unused-dep", 1, 1),)
    assert document[0].by_type["duplicates"] == (KnipHit("twin", 2, 1),)
    assert document[1].by_type["unlisted"] == (KnipHit("lodash", None, None),)


def test_run_knip_returns_exit_1_without_an_include_filter(tmp_path: Path) -> None:
    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit:
        assert "knip" in args
        assert "--include" not in args
        assert "--cache" not in args
        if args[-1] == "--version":
            return ProcessExit(0, "6.41.0\n", "")
        assert args[-2:] == ["--reporter", "json"]
        return ProcessExit(1, KNIP, "")

    capture = run_knip(tmp_path, 30, runner)

    assert capture.exit_code == 1
    assert capture.parsed is True
    assert capture.document is not None
    assert capture.document.version == "6.41.0"
    assert capture.document.files[0].by_type["unlisted"] == (KnipHit("left-pad", 4, 20),)


def test_probe_existence_reads_404_200_and_an_undecided_status() -> None:
    def transport(method: str, url: str, body: bytes | None, timeout: int) -> HttpOk:
        assert method == "GET"
        assert body is None
        assert timeout == 30
        if url == "https://pypi.org/pypi/cool-pkg/json":
            return HttpOk(404, b"missing")
        if url == "https://registry.npmjs.org/@scope%2Fleft-pad":
            return HttpOk(200, b'{"name":"@scope/left-pad"}')
        if url == "https://pypi.org/pypi/requests/json":
            return HttpOk(200, b'{"info":{"name":"requests"}}')
        return HttpOk(500, b"{}")

    missing = probe_existence(AddedPackage("pypi", "Cool_Pkg", None, "pyproject.toml", 4), 30, transport)
    scoped = probe_existence(AddedPackage("npm", "@scope/left-pad", "1.2.3", "package.json", 2), 30, transport)
    present = probe_existence(AddedPackage("pypi", "requests", "2.32.3", "pyproject.toml", 5), 30, transport)
    other = probe_existence(AddedPackage("npm", "odd", None, "package.json", 3), 30, transport)

    assert missing == PackageMissing()
    assert scoped == PackageExists()
    assert present == PackageExists()
    assert other == PackageUndecided("undecided")


def test_probe_existence_keeps_timeout_and_dns_as_undecided() -> None:
    def transport(method: str, url: str, body: bytes | None, timeout: int) -> HttpFault:
        if "slow" in url:
            return HttpFault("timeout")
        return HttpFault("dns")

    assert probe_existence(AddedPackage("npm", "slow", None, "package.json", 1), 30, transport) == (
        PackageUndecided("timeout")
    )
    assert probe_existence(AddedPackage("npm", "ghost", None, "package.json", 1), 30, transport) == (
        PackageUndecided("dns")
    )


def test_probe_advisories_posts_one_batch_per_index_and_skips_an_unpinned_name() -> None:
    calls: list[tuple[str, str, object]] = []

    def transport(method: str, url: str, body: bytes | None, timeout: int) -> HttpOk:
        assert body is not None
        payload = json.loads(body)
        calls.append((method, url, payload))
        ecosystem = payload["queries"][0]["package"]["ecosystem"]
        if ecosystem == "PyPI":
            return HttpOk(200, OSV)
        return HttpOk(200, b'{"results":[{"vulns":[]}]}')

    packages = (
        AddedPackage("pypi", "requests", "2.32.3", "pyproject.toml", 4),
        AddedPackage("pypi", "flask", "3.0.0", "pyproject.toml", 5),
        AddedPackage("pypi", "bare", None, "pyproject.toml", 6),
        AddedPackage("npm", "left-pad", "1.2.3", "package.json", 8),
    )

    probes = probe_advisories(packages, 30, transport)

    assert calls == [
        (
            "POST",
            "https://api.osv.dev/v1/querybatch",
            {
                "queries": [
                    {"package": {"name": "requests", "ecosystem": "PyPI"}, "version": "2.32.3"},
                    {"package": {"name": "flask", "ecosystem": "PyPI"}, "version": "3.0.0"},
                ]
            },
        ),
        (
            "POST",
            "https://api.osv.dev/v1/querybatch",
            {
                "queries": [
                    {"package": {"name": "left-pad", "ecosystem": "npm"}, "version": "1.2.3"},
                ]
            },
        ),
    ]
    assert probes[0] == AdvisoriesFound(
        (
            DecidedAdvisory("GHSA-1111-2222-3333", "CRITICAL"),
            DecidedAdvisory("GHSA-aaaa-bbbb-cccc", "MODERATE"),
            DecidedAdvisory("PYSEC-1", "HIGH"),
            UndecidedRecord("undecided", "GHSA-0000-0000-0000"),
        )
    )
    assert probes[1] == AdvisoriesFound(())
    assert probes[2] == AdvisoriesUndecided("undecided")
    assert probes[3] == AdvisoriesFound(())


def test_probe_advisories_marks_the_whole_batch_when_the_body_is_not_aligned() -> None:
    def transport(method: str, url: str, body: bytes | None, timeout: int) -> HttpOk | HttpFault:
        if body is not None and b"flask" in body:
            return HttpFault("timeout")
        return HttpOk(200, b'{"results":[]}')

    packages = (
        AddedPackage("pypi", "requests", "2.32.3", "pyproject.toml", 4),
        AddedPackage("npm", "flask", "3.0.0", "package.json", 5),
    )

    assert probe_advisories(packages, 12, transport) == (
        AdvisoriesUndecided("undecided"),
        AdvisoriesUndecided("timeout"),
    )


def test_added_packages_keeps_a_new_root_pin_and_ignores_a_version_bump(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "pyproject.toml").write_text(_PYPROJECT_BASE)
    (repo / "requirements.txt").write_text("legacy==1.0.0\n")
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    (repo / "pyproject.toml").write_text(_PYPROJECT_HEAD)
    (repo / "requirements.txt").write_text("legacy==2.0.0\nflask>=2\n")
    (repo / "poetry.lock").write_text('[[package]]\nname = "flask"\nversion = "3.0.1"\n')
    _commit(repo, "head")

    found = added_packages(repo, "main", changed_lines(repo, "main"), "pypi", ("src",), ("vendor",))

    assert found == (
        AddedPackage("pypi", "requests", "2.32.3", "pyproject.toml", 4),
        AddedPackage("pypi", "cool-pkg", None, "pyproject.toml", 6),
        AddedPackage("pypi", "flask", "3.0.1", "requirements.txt", 2),
    )


def test_added_packages_counts_every_name_in_a_manifest_the_base_does_not_have(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    (repo / "README.md").write_text("base\n")
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    (repo / "requirements.txt").write_text("added==1.2.3\n")
    _commit(repo, "head")

    found = added_packages(repo, "main", changed_lines(repo, "main"), "pypi", ("src",), ())

    assert found == (AddedPackage("pypi", "added", "1.2.3", "requirements.txt", 1),)


def test_added_packages_reads_npm_locks_and_skips_an_excluded_manifest(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "package.json").write_text("{}\n")
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    (repo / "package.json").write_text(_PACKAGE_HEAD)
    (repo / "package-lock.json").write_text(_LOCK)
    vendor = repo / "vendor"
    vendor.mkdir()
    (vendor / "package.json").write_text('{"dependencies":{"secret":"1.0.0"}}\n')
    _commit(repo, "head")

    found = added_packages(
        repo, "main", changed_lines(repo, "main"), "npm", (".",), ("vendor",)
    )

    assert found == (
        AddedPackage("npm", "left-pad", "1.2.3", "package.json", 3),
        AddedPackage("npm", "@scope/pkg", "1.2.3", "package.json", 6),
        AddedPackage("npm", "ranged", "4.5.6", "package.json", 7),
    )


_PYPROJECT_BASE = """\
[project]
name = "demo"
dependencies = [
  "Flask==1.0.0",
]

[project.optional-dependencies]
dev = [
  "pytest==8.0.0",
]

[tool.poetry.dependencies]
python = "^3.10"
rich = "12.0.0"
"""

_PYPROJECT_HEAD = """\
[project]
name = "demo"
dependencies = [
  "requests==2.32.3",
  "Flask==2.0.0",
  "Cool_Pkg",
  "local @ git+https://example.com/local.git",
]

[project.optional-dependencies]
dev = [
  "pytest==9.1.1",
]

[tool.poetry.dependencies]
python = "^3.10"
rich = "13.0.0"
skipped = { path = "../skipped" }
"""

_PACKAGE_HEAD = """\
{
  "dependencies": {
    "left-pad": "1.2.3"
  },
  "devDependencies": {
    "@scope/pkg": "1.2.3",
    "ranged": "^4.0.0"
  },
  "optionalDependencies": {
    "local": "file:../local"
  }
}
"""

_LOCK = """\
{
  "packages": {
    "node_modules/ranged": {"version": "4.5.6"},
    "node_modules/left-pad": {"version": "9.9.9"}
  }
}
"""


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "bob-test@example.com")
    _git(repo, "config", "user.name", "bob-test")
    return repo


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
