import json
from pathlib import Path

from helpers import _git

from bob_quality.adapters.registries import HttpFault, HttpOk
from bob_quality.adapters.runner import ProcessExit, ProcessFault
from bob_quality.config import Config
from bob_quality.diff import changed_lines
from bob_quality.messages import render
from bob_quality.models import (
    Advisory,
    GateResult,
    MissingPackage,
    Report,
    RowBlock,
    RowWarn,
    SupplyReport,
    UndeclaredImport,
    UnverifiedAdvisory,
    UnverifiedExistence,
)
from bob_quality.report import supply_lines
from bob_quality.supply import run_supply_gate

_VULNS = Path(__file__).parent / "fixtures" / "raw" / "osv"

_IMPORT = json.dumps(
    [
        {
            "error": {"code": "DEP001", "message": "missing"},
            "module": "requests",
            "location": {"file": "src/app.py", "line": 1, "column": 1},
        },
        {
            "error": {"code": "DEP002", "message": "unused"},
            "module": "unused",
            "location": {"file": "pyproject.toml", "line": 5, "column": 1},
        },
        {
            "error": {"code": "DEP003", "message": "transitive"},
            "module": "pkg_resources",
            "location": {"file": "src/app.py", "line": None, "column": None},
        },
    ]
)


def test_run_supply_gate_blocks_a_missing_package(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _pyproject(repo, 'dependencies = [\n]\n')
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    _pyproject(repo, 'dependencies = [\n  "no-such-pkg==1.2.3",\n]\n')
    _commit(repo, "head")

    result, code, versions, supply = run_supply_gate(
        repo,
        Config(),
        _diff(repo),
        "main",
        _deptry("[]"),
        _status(404),
    )

    assert code == 1
    assert result.name == "supply"
    assert result.status == "failed"
    assert supply.measured == ("python",)
    assert supply.skipped == ()
    assert versions == {"deptry": "0.25.1"}
    assert supply.rows == (
        RowBlock(MissingPackage("pypi", "no-such-pkg", "pyproject.toml", 5)),
    )


def test_run_supply_gate_warns_when_the_registry_and_osv_time_out(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _pyproject(repo, 'dependencies = [\n]\n')
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    _pyproject(repo, 'dependencies = [\n  "left==1.0.0",\n]\n')
    _commit(repo, "head")

    result, code, versions, supply = run_supply_gate(
        repo, Config(), _diff(repo), "main", _deptry("[]"), _fault("timeout")
    )

    assert code == 0
    assert result.status == "warn"
    assert versions == {"deptry": "0.25.1"}
    assert supply.rows == (
        RowWarn(UnverifiedExistence("pypi", "left", "pyproject.toml", 5, "timeout")),
    )
    assert _english(result, supply).count("`left`") == 1


def test_run_supply_gate_blocks_an_undeclared_import_while_the_registry_times_out(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    _pyproject(repo, 'dependencies = [\n]\n')
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("x = 1\n")
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    _pyproject(repo, 'dependencies = [\n  "left==1.0.0",\n]\n')
    (repo / "src" / "app.py").write_text("import requests\n")
    _commit(repo, "head")

    result, code, _versions, supply = run_supply_gate(
        repo, Config(), _diff(repo), "main", _deptry(_IMPORT), _fault("dns")
    )

    assert code == 1
    assert result.status == "failed"
    assert supply.rows == (
        RowBlock(UndeclaredImport("src/app.py", "requests", 1)),
        RowWarn(UnverifiedExistence("pypi", "left", "pyproject.toml", 5, "dns")),
    )


def test_run_supply_gate_warns_when_only_osv_times_out(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _pyproject(repo, "dependencies = [\n]\n")
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    _pyproject(repo, 'dependencies = [\n  "left==1.0.0",\n]\n')
    _commit(repo, "head")

    def transport(method: str, url: str, body: bytes | None, timeout: int) -> HttpOk | HttpFault:
        if method == "POST":
            return HttpFault("timeout")
        return HttpOk(200, b'{"info":{"name":"left"}}')

    result, code, _versions, supply = run_supply_gate(
        repo, Config(), _diff(repo), "main", _deptry("[]"), transport
    )

    assert code == 0
    assert result.status == "warn"
    assert supply.rows == (
        RowWarn(UnverifiedAdvisory("pypi", "left", "pyproject.toml", 5, "timeout")),
    )
    assert _english(result, supply).count("`left`") == 1


def test_run_supply_gate_keeps_a_later_package_when_an_earlier_one_is_offline(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    _pyproject(repo, "dependencies = [\n]\n")
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    _pyproject(repo, 'dependencies = [\n  "left==1.0.0",\n  "right==2.0.0",\n]\n')
    _commit(repo, "head")

    def transport(method: str, url: str, body: bytes | None, timeout: int) -> HttpOk | HttpFault:
        if method == "POST" or url.endswith("/left/json"):
            return HttpFault("timeout")
        return HttpOk(200, b'{"info":{"name":"right"}}')

    result, code, _versions, supply = run_supply_gate(
        repo, Config(), _diff(repo), "main", _deptry("[]"), transport
    )

    assert code == 0
    assert result.status == "warn"
    assert supply.rows == (
        RowWarn(UnverifiedExistence("pypi", "left", "pyproject.toml", 5, "timeout")),
        RowWarn(UnverifiedAdvisory("pypi", "right", "pyproject.toml", 6, "timeout")),
    )


def test_run_supply_gate_blocks_a_critical_advisory_from_the_vuln_document(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    _pyproject(repo, "dependencies = [\n]\n")
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    _pyproject(repo, 'dependencies = [\n  "left==1.0.0",\n]\n')
    _commit(repo, "head")

    result, code, _versions, supply = run_supply_gate(
        repo, Config(), _diff(repo), "main", _deptry("[]"), _critical()
    )

    assert code == 1
    assert result.status == "failed"
    assert supply.rows == (
        RowBlock(Advisory("GHSA-crit-0000-0001", "pypi", "left", "CRITICAL", "pyproject.toml", 5)),
    )
    assert (
        "| `left` | `pyproject.toml:5` | CRITICAL advisory GHSA-crit-0000-0001 | blocks |"
        in _english(result, supply)
    )


def test_run_supply_gate_warns_when_the_vuln_document_times_out(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _pyproject(repo, "dependencies = [\n]\n")
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    _pyproject(repo, 'dependencies = [\n  "left==1.0.0",\n]\n')
    _commit(repo, "head")

    result, code, _versions, supply = run_supply_gate(
        repo, Config(), _diff(repo), "main", _deptry("[]"), _vuln_timeout()
    )

    assert code == 0
    assert result.status == "warn"
    assert supply.rows == (
        RowWarn(
            UnverifiedAdvisory(
                "pypi", "left", "pyproject.toml", 5, "timeout", "GHSA-fail-0000-0001"
            )
        ),
    )
    assert (
        "| `left` | `pyproject.toml:5` | advisory GHSA-fail-0000-0001 left unverified (timeout) | warns |"
        in _english(result, supply)
    )


def test_run_supply_gate_exits_4_when_no_language_measures(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "README.md").write_text("base\n")
    _commit(repo, "base")

    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessFault:
        return ProcessFault("deptry missing")

    result, code, versions, supply = run_supply_gate(
        repo, Config(languages=("python", "typescript")), _diff(repo), "main", runner, _status(200)
    )

    assert code == 4
    assert result.status == "not_run"
    assert result.name == "supply"
    assert versions == {}
    assert supply.measured == ()
    assert supply.skipped == ("python", "typescript")
    assert supply.rows == ()


def test_run_supply_gate_keeps_the_language_that_measured(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _pyproject(repo, 'dependencies = [\n]\n')
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    (repo / "README.md").write_text("note\n")
    _commit(repo, "head")

    result, code, versions, supply = run_supply_gate(
        repo,
        Config(languages=("python", "typescript")),
        _diff(repo),
        "main",
        _python_only(),
        _status(404),
    )

    assert code == 0
    assert result.status == "passed"
    assert versions == {"deptry": "0.25.1"}
    assert supply.measured == ("python",)
    assert supply.skipped == ("typescript",)
    assert supply.rows == ()


def test_run_supply_gate_binds_a_null_knip_line_and_drops_relative_specifiers(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    (repo / "src").mkdir()
    (repo / "src" / "app.ts").write_text("export const ready = true\n")
    (repo / "package.json").write_text("{}\n")
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    (repo / "src" / "app.ts").write_text("import local from './local'\nimport lodash from 'lodash'\n")
    _commit(repo, "head")

    result, code, versions, supply = run_supply_gate(
        repo,
        Config(languages=("typescript",)),
        _diff(repo),
        "main",
        _knip(_KNIP),
        _status(200),
    )

    assert code == 1
    assert result.status == "failed"
    assert versions == {"knip": "6.41.0"}
    assert supply.rows == (RowBlock(UndeclaredImport("src/app.ts", "lodash", 2)),)


def test_run_supply_gate_warns_for_a_waived_blocker_beside_a_moderate_advisory(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    _pyproject(repo, 'dependencies = [\n]\n')
    _commit(repo, "base")
    _git(repo, "checkout", "-b", "head")
    _pyproject(repo, 'dependencies = [\n  "left==1.0.0",\n]\n')
    _commit(repo, "head")
    bob = repo / ".bob"
    bob.mkdir()
    (bob / "waivers.yaml").write_text(
        "waivers:\n"
        "  - id: supply:missing:pypi:left\n"
        "    reason: local stub\n"
        "    author: ada\n"
        "    date: '2026-10-11'\n"
    )

    result, code, _versions, supply = run_supply_gate(
        repo, Config(), _diff(repo), "main", _deptry("[]"), _moderate()
    )

    assert code == 0
    assert result.status == "warn"
    assert [row.effect for row in supply.rows] == ["waived", "warn"]
    assert supply.rows[0].waiver_id == "supply:missing:pypi:left"
    assert supply.rows[1].finding.severity == "MODERATE"


_KNIP = json.dumps(
    {
        "issues": [
            {
                "file": "src/app.ts",
                "unlisted": [{"name": "lodash"}],
                "unresolved": [
                    {"name": "./local", "line": 1, "col": 1},
                    {"name": "/abs", "line": 1, "col": 1},
                ],
            }
        ]
    }
)


def _deptry(raw: str):
    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit:
        if args[-1] == "--version":
            return ProcessExit(0, "deptry 0.25.1\n", "")
        Path(args[args.index("--json-output") + 1]).write_text(raw)
        return ProcessExit(0 if raw == "[]" else 1, "", "")

    return runner


def _python_only():
    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit | ProcessFault:
        if "knip" in args:
            return ProcessFault("knip missing")
        if args[-1] == "--version":
            return ProcessExit(0, "deptry 0.25.1\n", "")
        Path(args[args.index("--json-output") + 1]).write_text("[]")
        return ProcessExit(0, "", "")

    return runner


def _knip(raw: str):
    def runner(args: list[str], cwd: Path, timeout: int) -> ProcessExit:
        if args[-1] == "--version":
            return ProcessExit(0, "6.41.0\n", "")
        assert args[-2:] == ["--reporter", "json"]
        assert "--include" not in args
        return ProcessExit(1, raw, "")

    return runner


def _english(result: GateResult, supply: SupplyReport) -> str:
    report = Report(
        schema_version=1,
        commit="abc",
        base="main",
        generated_at="2026-10-13T00:00:00Z",
        tool_versions={"deptry": "0.25.1"},
        gates=[result],
        focus=[],
        top_crap=[],
        supply=supply,
    )
    return "\n".join(render(line, "en") for line in supply_lines(report))


def _critical():
    document = (_VULNS / "GHSA-crit-0000-0001.json").read_bytes()

    def transport(method: str, url: str, body: bytes | None, timeout: int) -> HttpOk:
        assert timeout == 30
        if url.startswith("https://api.osv.dev/v1/vulns/"):
            assert body is None
            return HttpOk(200, document)
        if method == "POST":
            payload = {
                "results": [
                    {
                        "vulns": [
                            {
                                "id": "GHSA-crit-0000-0001",
                                "modified": "2024-06-01T00:00:00Z",
                            }
                        ]
                    }
                ]
            }
            return HttpOk(200, json.dumps(payload).encode())
        return HttpOk(200, b'{"info":{"name":"left"}}')

    return transport


def _vuln_timeout():
    def transport(method: str, url: str, body: bytes | None, timeout: int) -> HttpOk | HttpFault:
        assert timeout == 30
        if url.startswith("https://api.osv.dev/v1/vulns/"):
            return HttpFault("timeout")
        if method == "POST":
            payload = {
                "results": [
                    {
                        "vulns": [
                            {
                                "id": "GHSA-fail-0000-0001",
                                "modified": "2024-01-01T00:00:00Z",
                            }
                        ]
                    }
                ]
            }
            return HttpOk(200, json.dumps(payload).encode())
        return HttpOk(200, b'{"info":{"name":"left"}}')

    return transport


def _status(status: int):
    def transport(method: str, url: str, body: bytes | None, timeout: int) -> HttpOk:
        if method == "POST":
            count = len(json.loads(body or b"{}").get("queries", []))
            payload = {"results": [{"vulns": []} for _item in range(count)]}
            return HttpOk(200, json.dumps(payload).encode())
        return HttpOk(status, b'{"info":{"name":"present"}}' if status == 200 else b"")

    return transport


def _fault(cause: str):
    def transport(method: str, url: str, body: bytes | None, timeout: int) -> HttpFault:
        return HttpFault(cause)

    return transport


def _moderate():
    def transport(method: str, url: str, body: bytes | None, timeout: int) -> HttpOk:
        if url.startswith("https://api.osv.dev/v1/vulns/"):
            payload = {
                "id": "GHSA-2222",
                "modified": "2024-01-01T00:00:00Z",
                "database_specific": {"severity": "MODERATE"},
            }
            return HttpOk(200, json.dumps(payload).encode())
        if method == "GET":
            return HttpOk(404, b"")
        payload = {
            "results": [
                {
                    "vulns": [
                        {"id": "GHSA-2222", "modified": "2024-01-01T00:00:00Z"},
                    ]
                }
            ]
        }
        return HttpOk(200, json.dumps(payload).encode())

    return transport


def _pyproject(repo: Path, dependencies: str) -> None:
    (repo / "pyproject.toml").write_text(
        "[project]\nname = \"demo\"\nversion = \"0.1.0\"\n" + dependencies
    )


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


def _diff(repo: Path) -> dict[str, set[int]]:
    return changed_lines(repo, "main")
