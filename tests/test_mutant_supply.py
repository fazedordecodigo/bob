from __future__ import annotations

import sys
from pathlib import Path

import pytest

from helpers import _git
from bob_quality.adapters.deptry import DeptryCapture, DeptryRun, DeptryViolation
from bob_quality.adapters.knip import KnipHit
from bob_quality.adapters.manifests import AddedPackage
from bob_quality.adapters.registries import DecidedAdvisory, HttpFault, UndecidedRecord
from bob_quality.adapters.runner import ProcessExit, ProcessFault
from bob_quality.config import Config
from bob_quality.diff import changed_lines
from bob_quality.models import (
    Advisory,
    MissingPackage,
    RowBlock,
    SupplyFinding,
    UndeclaredImport,
    UnverifiedAdvisory,
    UnverifiedExistence,
)
from bob_quality.supply import (
    _accept,
    _advisory_record,
    _captured,
    _dedupe_key,
    _deptry_findings,
    _import_line,
    _import_lines,
    _knip_file,
    _knip_hit,
    _measure_language,
    _relative,
    _reported_rows,
    judge,
    run_supply_gate,
)


def test_accept_rejects_a_parsed_exit_when_the_document_is_missing(tmp_path: Path) -> None:
    findings: list[SupplyFinding] = []
    versions: dict[str, str] = {}

    accepted = _accept(
        DeptryCapture(0, True, None, ""),
        "deptry",
        "pypi",
        _deptry_findings,
        tmp_path,
        Config(),
        {},
        "main",
        None,
        findings,
        versions,
    )

    assert accepted is False
    assert findings == []
    assert versions == {}


def test_accept_rejects_an_unmeasured_exit_that_still_has_a_document(tmp_path: Path) -> None:
    findings: list[SupplyFinding] = []
    versions: dict[str, str] = {}

    accepted = _accept(
        DeptryCapture(2, True, DeptryRun("9.9.9", ()), ""),
        "deptry",
        "pypi",
        _deptry_findings,
        tmp_path,
        Config(),
        {},
        "main",
        None,
        findings,
        versions,
    )

    assert accepted is False
    assert findings == []
    assert versions == {}


def test_advisory_record_keeps_the_package_and_the_decision() -> None:
    package = AddedPackage("pypi", "left", "1.2.3", "pyproject.toml", 4)

    assert _advisory_record(package, DecidedAdvisory("GHSA-1111", "HIGH")) == Advisory(
        "GHSA-1111",
        "pypi",
        "left",
        "HIGH",
        "pyproject.toml",
        4,
    )
    assert _advisory_record(package, UndecidedRecord("timeout", "GHSA-2222")) == UnverifiedAdvisory(
        "pypi",
        "left",
        "pyproject.toml",
        4,
        "timeout",
        "GHSA-2222",
    )


def test_captured_is_false_without_an_exit_and_true_for_a_found_exit() -> None:
    assert _captured(None, True) is False
    assert _captured(1, True) is True


def test_dedupe_key_returns_the_kind_and_the_identity() -> None:
    assert _dedupe_key(MissingPackage("pypi", "left", "pyproject.toml", 4)) == (
        "package",
        "pypi",
        "left",
    )
    assert _dedupe_key(UnverifiedExistence("npm", "left-pad", "package.json", 2, "timeout")) == (
        "package",
        "npm",
        "left-pad",
    )
    assert _dedupe_key(UndeclaredImport("src/app.py", "requests", 3)) == (
        "undeclared",
        "src/app.py",
        "requests",
        3,
    )
    assert _dedupe_key(Advisory("GHSA-1111", "pypi", "left", "HIGH", "pyproject.toml", 4)) == (
        "advisory",
        "GHSA-1111",
    )
    assert _dedupe_key(
        UnverifiedAdvisory("npm", "left-pad", "package.json", 2, "dns", "GHSA-2222")
    ) == ("unverified-advisory", "npm", "left-pad", "GHSA-2222")


def test_deptry_findings_skip_a_foreign_code_and_keep_the_next_line(tmp_path: Path) -> None:
    app = tmp_path / "src" / "app.py"
    document = DeptryRun(
        "0.25.1",
        (
            DeptryViolation("DEP002", "unused", "pyproject.toml", 10),
            DeptryViolation("DEP001", "ghost", "src/app.py", None),
            DeptryViolation("DEP001", "requests", str(app), 4),
            DeptryViolation("DEP003", "pkg_resources", "src/pkg.py", 7),
        ),
    )

    assert _deptry_findings(tmp_path, document) == (
        UndeclaredImport("src/app.py", "requests", 4),
        UndeclaredImport("src/pkg.py", "pkg_resources", 7),
    )


def test_import_line_matches_each_import_form() -> None:
    assert _import_line("  import left-pad") is True
    assert _import_line("import('left-pad')") is True
    assert _import_line("export { ready }") is True
    assert _import_line("} from 'left-pad'") is True
    assert _import_line("const left = require('left-pad')") is True
    assert _import_line("const ready = true") is False


def test_import_lines_keep_the_import_when_the_file_has_invalid_bytes(tmp_path: Path) -> None:
    source = tmp_path / "src" / "app.ts"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"note left-pad\nimport left-pad \xff\n")

    assert _import_lines(tmp_path, "src/app.ts", "left-pad") == (2,)
    assert _import_lines(tmp_path, "src/missing.ts", "left-pad") == ()


def test_knip_file_reads_unresolved_when_unlisted_is_absent() -> None:
    hit = KnipHit("left-pad", 4, 1)

    assert _knip_file(Path("."), "src/app.ts", {"unresolved": (hit,)}) == (
        UndeclaredImport("src/app.ts", "left-pad", 4),
    )


def test_knip_hit_keeps_an_unresolved_package_and_an_unlisted_relative(tmp_path: Path) -> None:
    package = _knip_hit(tmp_path, "src/app.ts", "unresolved", KnipHit("left-pad", 4, 1))
    relative = _knip_hit(tmp_path, "src/app.ts", "unlisted", KnipHit("./local", 2, 1))
    skipped = _knip_hit(tmp_path, "src/app.ts", "unresolved", KnipHit("./local", 9, 1))

    assert package == (UndeclaredImport("src/app.ts", "left-pad", 4),)
    assert relative == (UndeclaredImport("src/app.ts", "./local", 2),)
    assert skipped == ()


def test_measure_python_passes_the_cwd_and_timeout_to_deptry(tmp_path: Path) -> None:
    calls: list[tuple[list[str], Path, int]] = []

    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit:
        calls.append((list(args), cwd, timeout))
        if args[-1] == "--version":
            return ProcessExit(0, "deptry 0.25.1\n", "")
        Path(args[args.index("--json-output") + 1]).write_text("[]")
        return ProcessExit(0, "", "")

    findings: list[SupplyFinding] = []
    versions: dict[str, str] = {}
    measured = _measure_language(
        "python",
        tmp_path,
        Config(supply_timeout_seconds=17),
        {},
        "main",
        runner,
        None,
        findings,
        versions,
    )

    assert measured is True
    assert calls[0] == ([sys.executable, "-m", "deptry", "--version"], tmp_path, 17)
    assert calls[1][1:] == (tmp_path, 17)
    assert versions == {"deptry": "0.25.1"}
    assert findings == []


def test_measure_typescript_keeps_the_npm_package_and_the_registry_timeout(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "package.json").write_text('{\n  "name": "demo"\n}\n')
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    (repo / "package.json").write_text(
        '{\n  "dependencies": {\n    "left-pad": "1.2.3"\n  }\n}\n'
    )
    _commit(repo, "head")
    calls: list[tuple[list[str], Path, int]] = []
    seen: list[tuple[str, int]] = []

    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit:
        calls.append((list(args), cwd, timeout))
        if args[-1] == "--version":
            return ProcessExit(0, "6.41.0\n", "")
        return ProcessExit(0, '{"issues": []}', "")

    def transport(method: str, url: str, body: bytes | None, timeout: int) -> HttpFault:
        seen.append((method, timeout))
        return HttpFault("dns")

    findings: list[SupplyFinding] = []
    versions: dict[str, str] = {}
    measured = _measure_language(
        "typescript",
        repo,
        Config(supply_timeout_seconds=17),
        changed_lines(repo, "main"),
        "main",
        runner,
        transport,
        findings,
        versions,
    )

    assert measured is True
    assert calls[0][1:] == (repo, 17)
    assert calls[1][1:] == (repo, 17)
    assert seen == [("GET", 17), ("POST", 17)]
    assert versions == {"knip": "6.41.0"}
    assert findings == [
        UnverifiedExistence("npm", "left-pad", "package.json", 3, "dns"),
        UnverifiedAdvisory("npm", "left-pad", "package.json", 3, "dns"),
    ]


def test_measure_language_skips_a_language_without_a_tool(tmp_path: Path) -> None:
    calls: list[tuple[list[str], Path, int]] = []

    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit:
        calls.append((list(args), cwd, timeout))
        return ProcessExit(0, "", "")

    findings: list[SupplyFinding] = []
    versions: dict[str, str] = {}
    measured = _measure_language(
        "ruby",
        tmp_path,
        Config(),
        {},
        "main",
        runner,
        None,
        findings,
        versions,
    )

    assert measured is False
    assert calls == []
    assert findings == []
    assert versions == {}


def test_reported_rows_drop_every_row_when_no_language_was_measured() -> None:
    row = RowBlock(MissingPackage("pypi", "left", "pyproject.toml", 4))

    assert _reported_rows((), (row,)) == ()
    assert _reported_rows(("python",), (row,)) == (row,)


def test_relative_keeps_a_relative_path_and_drops_the_cwd(tmp_path: Path) -> None:
    assert _relative(tmp_path, "src/app.py") == "src/app.py"
    assert _relative(tmp_path, str(tmp_path / "src" / "app.py")) == "src/app.py"


def test_judge_keeps_the_row_after_an_off_diff_finding() -> None:
    off = MissingPackage("pypi", "gone", "README.md", 1)
    kept = UndeclaredImport("src/app.py", "requests", 3)

    judgment = judge(
        (off, kept),
        {"src/app.py": {3}, "pyproject.toml": {14}},
        frozenset(),
        frozenset(),
    )

    assert judgment.rows == (RowBlock(kept),)
    assert judgment.status == "failed"
    assert judgment.exit_code == 1


def test_judge_keeps_the_row_after_a_duplicate_key() -> None:
    first = MissingPackage("pypi", "same", "pyproject.toml", 14)
    duplicate = UnverifiedExistence("pypi", "same", "pyproject.toml", 14, "timeout")
    later = UndeclaredImport("src/app.py", "requests", 3)

    judgment = judge(
        (first, duplicate, later),
        {"pyproject.toml": {14}, "src/app.py": {3}},
        frozenset(),
        frozenset(),
    )

    assert judgment.rows == (RowBlock(first), RowBlock(later))
    assert judgment.status == "failed"
    assert judgment.exit_code == 1


def test_run_supply_gate_uses_the_default_runner_for_cwd_and_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[list[str], Path, int]] = []

    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessFault:
        calls.append((list(args), cwd, timeout))
        return ProcessFault("stopped")

    monkeypatch.setattr("bob_quality.supply.default_runner", runner)

    result, code, versions, supply = run_supply_gate(
        tmp_path,
        Config(supply_timeout_seconds=17),
        {},
        "main",
    )

    assert calls[0] == ([sys.executable, "-m", "deptry", "--version"], tmp_path, 17)
    assert calls[1][1:] == (tmp_path, 17)
    assert code == 4
    assert result.status == "not_run"
    assert versions == {}
    assert supply.measured == ()
    assert supply.skipped == ("python",)
    assert supply.rows == ()


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
