"""Seam: CLI `bob doctor` (stdout + exit code).

Versões Python e do gitleaks literais. As versões npm e a faixa do Node vêm do
package.json (ADR 0008). Os stubs imitam o `--version` real de node, gitleaks e
das ferramentas Python; as ferramentas npm vêm de um prefixo do bob falso.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from bob_quality.doctor import (
    BinaryPin,
    NodePin,
    NodeSlot,
    NodeVersion,
    NpmPin,
    RequiresDist,
    node_admits,
    node_pin,
    node_range,
    run_doctor,
)
from bob_quality import doctor, gitleaks
from bob_quality.doctor import PINS as DOCTOR_PINS
from bob_quality.doctor import unconditional_exact_pins
from bob_quality.gitleaks import GitleaksError
from bob_quality.user_dirs import bob_home
from bob_quality.doctor import (
    _Expected,
    _PinRow,
    _assess,
    _assess_node,
    _assess_npm,
    _assess_binary,
    _assess_requires_dist,
    _found_version,
    _own_requirements,
    _rows,
)
from bob_quality.messages import Language, msg, t
from bob_quality.npm_tools import pinned_npm_versions

ROOT = Path(__file__).resolve().parents[1]
_PACKAGE = json.loads((ROOT / "package.json").read_text())
_NPM: dict[str, str] = _PACKAGE["dependencies"]

# (nome no relatório, versão pinada, executável, banner de --version)
PINS = (
    ("lizard", "1.24.1", "lizard", "1.24.1"),
    ("deptry", "0.25.1", None, None),
    (
        "coverage.py",
        "7.16.2",
        "coverage",
        "Coverage.py, version 7.16.2 with C extension",
    ),
    ("node", "22.18.0", "node", "v22.18.0"),
    ("c8", _NPM["c8"], None, None),
    ("vitest", _NPM["vitest"], None, None),
    ("jscpd", _NPM["jscpd"], None, None),
    ("eslint", _NPM["eslint"], None, None),
    ("eslint-plugin-sonarjs", _NPM["eslint-plugin-sonarjs"], None, None),
    ("mutmut", "3.8.0", "mutmut", "mutmut, version 3.8.0"),
    ("complexipy", "8.0.1", None, None),
    ("import-linter", "2.15", "lint-imports", "2.15"),
    ("grimp", "3.17", None, None),
    ("diff-cover", "10.6.0", None, None),
    ("bandit", "1.9.4", None, None),
    ("dependency-cruiser", _NPM["dependency-cruiser"], None, None),
    ("gitleaks", "8.30.1", "gitleaks", "8.30.1"),
    ("vulture", "2.16", "vulture", "vulture 2.16"),
    ("knip", _NPM["knip"], None, None),
    ("stryker", _NPM["@stryker-mutator/core"], None, None),
    ("stryker-vitest-runner", _NPM["@stryker-mutator/vitest-runner"], None, None),
)

INSTALL = {
    "lizard": "pip install 'lizard==1.24.1'",
    "coverage.py": "pip install 'coverage==7.16.2'",
    "node": "Install Node.js >=22.18.0 <23 (https://nodejs.org/dist/v22.18.0/)",
    "mutmut": "pip install 'mutmut==3.8.0'",
    "import-linter": "pip install 'import-linter==2.15'",
    "grimp": "pip install 'grimp==3.17'",
    "diff-cover": "pip install 'diff-cover==10.6.0'",
    "complexipy": "pip install 'complexipy==8.0.1'",
    "bandit": "pip install 'bandit==1.9.4'",
}


def _bob_npm_prefix(parent: Path) -> Path:
    """XDG_CACHE_HOME com um prefixo npm do bob completo: o package.json da raiz e cada pacote."""
    xdg = parent / "xdg-cache"
    cache = xdg / "bob-quality"
    if cache.is_dir():
        return xdg
    cache.mkdir(parents=True)
    shutil.copy(ROOT / "package.json", cache / "package.json")
    for name, version in _NPM.items():
        manifest = cache / "node_modules" / name / "package.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"name": name, "version": version}))
    return xdg


def _tree_digest(root: Path) -> list[tuple[str, str]]:
    digest: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        digest.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return digest


def _stub(bin_dir: Path, name: str, banner: str) -> None:
    path = bin_dir / name
    path.write_text(f"#!/bin/sh\nprintf '%s\\n' '{banner}'\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _run_doctor(
    cwd: Path, bin_dir: Path, *args: str, metadata: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("BOB_LANG", None)
    env["PATH"] = str(bin_dir)
    env["XDG_CACHE_HOME"] = str(_bob_npm_prefix(cwd.parent))
    # O dist-info falso vem antes de src, senão o egg-info do editável ganha.
    pythonpath = [str(ROOT / "src")]
    if metadata is not None:
        pythonpath.insert(0, str(metadata))
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    # O trampoline do mutmut procura source_paths no cwd do subprocesso.
    # O doctor roda num repo vazio; sem isto a coleta de stats morre.
    env["MUTANT_UNDER_TEST"] = ""
    return subprocess.run(
        [sys.executable, "-m", "bob_quality", "doctor", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.fixture(autouse=True)
def _empty_bob_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BOB_HOME", str(tmp_path / "bob-home"))


def test_doctor_lists_import_linter_and_dependency_cruiser(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for _name, _expected, executable, banner in PINS:
        if executable is None or banner is None:
            continue
        _stub(bin_dir, executable, banner)

    repo = tmp_path / "repo"
    repo.mkdir()
    result = _run_doctor(repo, bin_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "import-linter expected 2.15 found 2.15" in result.stdout
    cruiser = _NPM["dependency-cruiser"]
    assert f"dependency-cruiser expected {cruiser} found {cruiser}" in result.stdout


def test_doctor_exits_0_and_lists_pinned_versions_when_tools_match(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for _name, _expected, executable, banner in PINS:
        if executable is None or banner is None:
            continue
        _stub(bin_dir, executable, banner)

    repo = tmp_path / "repo"
    repo.mkdir()
    result = _run_doctor(repo, bin_dir)

    assert result.returncode == 0, result.stderr
    assert "node expected >=22.18.0 <23 found 22.18.0" in result.stdout
    for name, expected, _executable, _banner in PINS:
        if name == "node":
            continue
        assert f"{name} expected {expected} found {expected}" in result.stdout
    assert "Install" not in result.stdout


def test_doctor_exits_4_and_prints_install_when_a_tool_is_missing(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, _expected, executable, banner in PINS:
        if name == "node":
            continue
        if executable is None or banner is None:
            continue
        _stub(bin_dir, executable, banner)

    repo = tmp_path / "repo"
    repo.mkdir()
    result = _run_doctor(repo, bin_dir)

    assert result.returncode == 4, result.stderr
    assert "node expected >=22.18.0 <23 found missing" in result.stdout
    assert INSTALL["node"] in result.stdout
    assert INSTALL["lizard"] not in result.stdout


def test_doctor_follows_language_in_bob_yaml(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for _name, _expected, executable, banner in PINS:
        if executable is None or banner is None:
            continue
        _stub(bin_dir, executable, banner)

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "bob.yaml").write_text("language: pt-BR\n")
    result = _run_doctor(repo, bin_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "lizard esperada 1.24.1 encontrada 1.24.1" in result.stdout
    assert "expected" not in result.stdout


def test_doctor_speaks_portuguese_with_lang_pt_br(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, _expected, executable, banner in PINS:
        if name == "node":
            continue
        if executable is None or banner is None:
            continue
        _stub(bin_dir, executable, banner)

    repo = tmp_path / "repo"
    repo.mkdir()
    result = _run_doctor(repo, bin_dir, "--lang", "pt-BR")

    assert result.returncode == 4, result.stderr
    assert "lizard esperada 1.24.1 encontrada 1.24.1" in result.stdout
    assert "node esperada >=22.18.0 <23 encontrada ausente" in result.stdout
    assert "Instale Node.js >=22.18.0 <23 (https://nodejs.org/dist/v22.18.0/)" in result.stdout


def test_doctor_exits_4_and_prints_install_when_version_differs(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, _expected, executable, banner in PINS:
        if name == "node":
            banner = "v1.2.3"
        if executable is None or banner is None:
            continue
        _stub(bin_dir, executable, banner)

    repo = tmp_path / "repo"
    repo.mkdir()
    result = _run_doctor(repo, bin_dir)

    assert result.returncode == 4, result.stderr
    assert "node expected >=22.18.0 <23 found 1.2.3" in result.stdout
    assert INSTALL["node"] in result.stdout
    assert INSTALL["lizard"] not in result.stdout


def _stub_all(bin_dir: Path) -> None:
    for _name, _expected, executable, banner in PINS:
        if executable is None or banner is None:
            continue
        _stub(bin_dir, executable, banner)


def test_doctor_reads_npm_versions_from_the_bob_prefix_not_the_path(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _stub_all(bin_dir)
    _stub(bin_dir, "c8", "0.0.1")
    _stub(bin_dir, "vitest", "0.0.1")
    repo = tmp_path / "repo"
    repo.mkdir()
    result = _run_doctor(repo, bin_dir)
    c8 = _NPM["c8"]
    vitest = _NPM["vitest"]
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"c8 expected {c8} found {c8}" in result.stdout
    assert f"vitest expected {vitest} found {vitest}" in result.stdout
    assert "0.0.1" not in result.stdout


def test_doctor_ignores_the_vitest_installed_in_the_project(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _stub_all(bin_dir)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text(
        json.dumps({"name": "app", "devDependencies": {"vitest": "4.1.0"}})
    )
    vitest = repo / "node_modules" / "vitest" / "package.json"
    vitest.parent.mkdir(parents=True)
    vitest.write_text(json.dumps({"name": "vitest", "version": "4.1.0"}))
    local_bin = repo / "node_modules" / ".bin"
    local_bin.mkdir()
    _stub(local_bin, "vitest", "4.1.0")
    before = _tree_digest(repo)
    result = _run_doctor(repo, bin_dir)
    pinned = _NPM["vitest"]
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"vitest expected {pinned} found {pinned}" in result.stdout
    assert "4.1.0" not in result.stdout
    assert _tree_digest(repo) == before


def test_doctor_ignores_binaries_in_the_project_node_modules(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _stub_all(bin_dir)
    repo = tmp_path / "repo"
    repo.mkdir()
    local_bin = repo / "node_modules" / ".bin"
    local_bin.mkdir(parents=True)
    _stub(local_bin, "gitleaks", "0.0.1")
    _stub(local_bin, "node", "v0.0.1")
    result = _run_doctor(repo, bin_dir)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "gitleaks expected 8.30.1 found 8.30.1" in result.stdout
    assert "node expected >=22.18.0 <23 found 22.18.0" in result.stdout
    assert "0.0.1" not in result.stdout


def test_doctor_reports_interpreter_lizard_not_a_path_shadow(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for _name, _expected, executable, banner in PINS:
        if executable == "lizard":
            banner = "9.9.9"
        if executable is None or banner is None:
            continue
        _stub(bin_dir, executable, banner)

    repo = tmp_path / "repo"
    repo.mkdir()
    result = _run_doctor(repo, bin_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "lizard expected 1.24.1 found 1.24.1" in result.stdout


def test_doctor_pins_match_pyproject_and_package_json() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    requirements = {
        spec.split("==", 1)[0]: spec.split("==", 1)[1]
        for spec in project["project"]["dependencies"]
        if "==" in spec
    }
    npm_packages = [pin.npm_package for pin in DOCTOR_PINS if isinstance(pin, NpmPin)]
    for pin in DOCTOR_PINS:
        if isinstance(pin, RequiresDist):
            assert pin.distribution in requirements
        elif isinstance(pin, BinaryPin):
            assert (pin.name, pin.expected, pin.executable) == ("gitleaks", "8.30.1", "gitleaks")
            assert pin.sha256 == "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"
        else:
            assert isinstance(pin, (NpmPin, NodeSlot))
    assert sorted(npm_packages) == sorted(_NPM)
    assert pinned_npm_versions() == _NPM
    assert "node" not in npm_packages
    assert [pin for pin in DOCTOR_PINS if isinstance(pin, NodeSlot)] == [NodeSlot()]
    assert node_range(node_pin()) == _PACKAGE["engines"]["node"]
    assert [pin.name for pin in DOCTOR_PINS if isinstance(pin, BinaryPin)] == ["gitleaks"]


def test_doctor_expected_versions_match_pip_and_npm_pins(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for _name, _expected, executable, banner in PINS:
        if executable is None or banner is None:
            continue
        _stub(bin_dir, executable, banner)
    repo = tmp_path / "repo"
    repo.mkdir()
    result = _run_doctor(repo, bin_dir)
    assert result.returncode == 0, result.stderr
    expected = _expected_versions(result.stdout)

    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    requirements = {
        spec.split("==", 1)[0]: spec.split("==", 1)[1]
        for spec in project["project"]["dependencies"]
        if "==" in spec
    }
    assert requirements["lizard"] == expected["lizard"]
    assert requirements["coverage"] == expected["coverage.py"]
    assert requirements["mutmut"] == expected["mutmut"]
    assert requirements["import-linter"] == expected["import-linter"]
    assert requirements["grimp"] == expected["grimp"]
    assert requirements["diff-cover"] == expected["diff-cover"]
    assert requirements["complexipy"] == expected["complexipy"]
    assert requirements["bandit"] == expected["bandit"]
    assert "semgrep" not in requirements
    assert "semgrep" not in expected

    package = json.loads((ROOT / "package.json").read_text())
    assert package["private"] is True
    npm = package["dependencies"]
    assert npm["c8"] == expected["c8"]
    assert npm["vitest"] == expected["vitest"]
    assert npm["jscpd"] == expected["jscpd"]
    assert npm["dependency-cruiser"] == expected["dependency-cruiser"]
    assert npm["eslint"] == expected["eslint"]
    assert npm["eslint-plugin-sonarjs"] == expected["eslint-plugin-sonarjs"]
    assert npm["knip"] == expected["knip"]
    assert requirements["vulture"] == expected["vulture"]
    assert npm["@stryker-mutator/core"] == expected["stryker"]
    assert npm["@stryker-mutator/vitest-runner"] == expected["stryker-vitest-runner"]
    assert set(npm) == {
        "@stryker-mutator/core",
        "@stryker-mutator/vitest-runner",
        "c8",
        "dependency-cruiser",
        "eslint",
        "eslint-plugin-sonarjs",
        "jscpd",
        "knip",
        "vitest",
    }


_DECLARED = ("lizard==1.24.1", "coverage==7.16.2", "import-linter==2.15", "mutmut==3.8.0")


def test_doctor_expects_the_grimp_version_bob_declares(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for _name, _expected, executable, banner in PINS:
        if executable is None or banner is None:
            continue
        _stub(bin_dir, executable, banner)
    repo = tmp_path / "repo"
    repo.mkdir()
    meta = _bob_metadata(tmp_path / "meta", *_DECLARED, "grimp==9.9.9")
    result = _run_doctor(repo, bin_dir, metadata=meta)

    assert result.returncode == 4
    assert "grimp expected 9.9.9 found 3.17" in result.stdout
    assert "pip install 'grimp==9.9.9'" in result.stdout
    assert "lizard expected 1.24.1 found 1.24.1" in result.stdout


def test_doctor_fails_grimp_when_bob_pins_it_only_for_dev(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for _name, _expected, executable, banner in PINS:
        if executable is None or banner is None:
            continue
        _stub(bin_dir, executable, banner)
    repo = tmp_path / "repo"
    repo.mkdir()
    meta = _bob_metadata(tmp_path / "meta", *_DECLARED, 'grimp==3.17; extra == "dev"')
    result = _run_doctor(repo, bin_dir, metadata=meta)

    assert result.returncode == 4
    assert "grimp expected missing found 3.17" in result.stdout
    assert "pip install 'grimp" not in result.stdout
    assert "import-linter expected 2.15 found 2.15" in result.stdout


def test_unconditional_exact_pins_keeps_exact_lines() -> None:
    assert unconditional_exact_pins(
        [
            "lizard==1.24.1",
            'pytest==9.1.1; extra == "dev"',
            "grimp==3.17",
            'tomli==2.5.0; python_version < "3.11" and extra == "dev"',
            "rich>=14.2.0",
        ]
    ) == {"lizard": "1.24.1", "grimp": "3.17"}
    assert unconditional_exact_pins(["pkg===1.0"]) == {"pkg": "=1.0"}


def test_own_requirements_keeps_the_grimp_pin() -> None:
    assert "grimp==3.17" in _own_requirements()


def test_assess_requires_dist_matches_the_installed_grimp() -> None:
    row = _assess_requires_dist(RequiresDist("grimp", "grimp"), "3.17")
    assert row.line == msg("doctor.version", name="grimp", expected="3.17", found="3.17")
    assert row.ok is True
    assert row.install is None
    assert row.npm_missing is False


def test_assess_requires_dist_rejects_a_missing_pin() -> None:
    row = _assess_requires_dist(RequiresDist("grimp", "grimp"), None)
    assert row.line == msg(
        "doctor.version",
        name="grimp",
        expected=msg("doctor.missing"),
        found="3.17",
    )
    assert row.ok is False
    assert row.install is None
    assert row.npm_missing is False


def test_assess_requires_dist_names_the_install() -> None:
    row = _assess_requires_dist(RequiresDist("grimp", "grimp"), "9.9.9")
    assert row.line == msg("doctor.version", name="grimp", expected="9.9.9", found="3.17")
    assert row.ok is False
    assert row.install == "pip install 'grimp==9.9.9'"
    assert row.npm_missing is False


def test_assess_reads_the_declared_distribution() -> None:
    row = _assess(RequiresDist("grimp", "grimp"), _expected(python={"grimp": "3.17"}))
    assert row.ok is True
    assert row.line == msg("doctor.version", name="grimp", expected="3.17", found="3.17")



def test_assess_binary_matches_the_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bob_quality.doctor._cli_version",
        lambda executable: "8.30.1" if executable == "gitleaks" else None,
    )
    pin = BinaryPin(
        "gitleaks",
        "8.30.1",
        "gitleaks",
        "https://example.test/gitleaks.tar.gz",
        "abc",
    )
    row = _assess(pin, _expected())
    assert row.line == msg("doctor.version", name="gitleaks", expected="8.30.1", found="8.30.1")
    assert row.ok is True
    assert row.install is None
    assert row.npm_missing is False


def test_assess_binary_mismatch_names_the_url_and_sha256(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("bob_quality.doctor._cli_version", lambda executable: None)
    pin = next(item for item in DOCTOR_PINS if isinstance(item, BinaryPin))
    row = _assess_binary(pin)
    assert row.line == msg(
        "doctor.version",
        name="gitleaks",
        expected="8.30.1",
        found=msg("doctor.missing"),
    )
    assert row.ok is False
    assert row.npm_missing is False
    assert row.install == msg(
        "doctor.install_gitleaks",
        version=pin.expected,
        url=pin.url,
        sha256=pin.sha256,
    )


def test_assess_binary_rejects_a_gitleaks_prerelease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _stub(bin_dir, "gitleaks", "8.30.1-beta.1")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", str(bin_dir))
    pin = next(item for item in DOCTOR_PINS if isinstance(item, BinaryPin))
    assert _assess_binary(pin) == _PinRow(
        msg(
            "doctor.version",
            name="gitleaks",
            expected="8.30.1",
            found="8.30.1-beta.1",
        ),
        False,
        msg(
            "doctor.install_gitleaks",
            version=pin.expected,
            url=pin.url,
            sha256=pin.sha256,
        ),
        False,
    )


def test_gitleaks_checksum_is_the_one_the_workflows_check() -> None:
    pin = next(item for item in DOCTOR_PINS if isinstance(item, BinaryPin))
    for name in (
        ".github/workflows/ci.yml",
        ".github/workflows/bob.yml",
        ".github/workflows/package.yml",
    ):
        text = (ROOT / name).read_text()
        assert pin.url in text
        assert f"{pin.sha256}  /tmp/gitleaks_8.30.1_linux_x64.tar.gz" in text
        assert "sha256sum -c" in text


def _expected(
    python: dict[str, str] | None = None,
    npm: dict[str, str] | None = None,
    node: NodePin | None = None,
) -> _Expected:
    return _Expected(
        python={} if python is None else python,
        npm={} if npm is None else npm,
        node=NodePin(floor=NodeVersion(22, 18, 0)) if node is None else node,
    )


def test_assess_sends_an_npm_pin_to_the_npm_row(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bob_quality.doctor._found_version", lambda pin: "0")
    row = _assess(NpmPin("c8", "c8"), _expected(npm={"c8": "1.0.0"}))
    assert row.line == msg("doctor.version", name="c8", expected="1.0.0", found="0")
    assert row.ok is False
    assert row.install is None
    assert row.npm_missing is True


def test_assess_sends_the_node_slot_to_the_node_row(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bob_quality.doctor._cli_version",
        lambda executable: "24.1.0" if executable == "node" else None,
    )
    row = _assess(NodeSlot(), _expected(node=NodePin(floor=NodeVersion(24, 1, 0))))
    assert row == _PinRow(
        msg("doctor.version", name="node", expected=">=24.1.0 <25", found="24.1.0"),
        True,
        None,
        False,
    )


def test_assess_npm_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bob_quality.doctor._found_version", lambda pin: "1.0.0")
    row = _assess_npm(NpmPin("c8", "c8"), "1.0.0")
    assert row.line == msg("doctor.version", name="c8", expected="1.0.0", found="1.0.0")
    assert row.ok is True
    assert row.install is None
    assert row.npm_missing is False


def test_assess_npm_mismatch_has_no_install_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bob_quality.doctor._found_version", lambda pin: "0")
    row = _assess_npm(NpmPin("c8", "c8"), "1.0.0")
    assert row.line == msg("doctor.version", name="c8", expected="1.0.0", found="0")
    assert row.ok is False
    assert row.install is None
    assert row.npm_missing is True


def test_assess_npm_without_an_expected_version_is_not_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("bob_quality.doctor._found_version", lambda pin: "1.0.0")
    row = _assess_npm(NpmPin("c8", "c8"), None)
    assert row == _PinRow(
        msg("doctor.version", name="c8", expected=msg("doctor.missing"), found="1.0.0"),
        False,
        None,
        False,
    )


def test_found_version_reads_the_bob_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefix = tmp_path / "prefix"
    manifest = prefix / "node_modules" / "c8" / "package.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"name": "c8", "version": "1.0.0"}))
    monkeypatch.setattr("bob_quality.doctor._npm_root", lambda: prefix)
    monkeypatch.setattr("bob_quality.doctor._cli_version", lambda executable: "9.9.9")
    assert _found_version(NpmPin("c8", "c8")) == "1.0.0"


def test_found_version_ignores_the_path_when_the_prefix_lacks_the_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefix = tmp_path / "prefix"
    prefix.mkdir()
    monkeypatch.setattr("bob_quality.doctor._npm_root", lambda: prefix)
    monkeypatch.setattr("bob_quality.doctor._cli_version", lambda executable: "1.0.0")
    assert _found_version(NpmPin("c8", "c8")) is None


def test_vitest_5_0_5_in_the_bob_prefix_passes_when_package_json_pins_5_0_5(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regressão de P1: main com vitest 5.0.5 no package.json e o doctor esperando 5.0.4."""
    packaged = tmp_path / "packaged"
    packaged.mkdir()
    monkeypatch.setattr("bob_quality.npm_tools.__file__", str(packaged / "npm_tools.py"))
    (packaged / "package.json").write_text(
        json.dumps(
            {
                "name": "bob-quality-tools",
                "engines": {"node": ">=22.18.0 <23"},
                "dependencies": {"vitest": "5.0.5"},
            }
        )
    )
    prefix = tmp_path / "prefix"
    manifest = prefix / "node_modules" / "vitest" / "package.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"name": "vitest", "version": "5.0.5"}))
    monkeypatch.setattr("bob_quality.doctor._npm_root", lambda: prefix)
    row = _assess_npm(NpmPin("vitest", "vitest"), pinned_npm_versions()["vitest"])
    assert row == _PinRow(
        msg("doctor.version", name="vitest", expected="5.0.5", found="5.0.5"),
        True,
        None,
        False,
    )


def test_node_pin_comes_from_engines_node_of_the_packaged_package_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packaged = tmp_path / "packaged"
    packaged.mkdir()
    monkeypatch.setattr("bob_quality.npm_tools.__file__", str(packaged / "npm_tools.py"))
    (packaged / "package.json").write_text(
        json.dumps({"engines": {"node": ">=24.1.0 <25"}, "dependencies": {}})
    )
    assert node_pin() == NodePin(floor=NodeVersion(24, 1, 0))
    assert node_range(node_pin()) == ">=24.1.0 <25"


@pytest.mark.parametrize(
    ("lang", "text"),
    [
        ("en", "could not read {path} ({detail}). Reinstall bob."),
        ("pt-BR", "não consegui ler {path} ({detail}). Reinstale o bob."),
    ],
)
def test_doctor_exits_4_with_one_stderr_line_when_package_json_is_unreadable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    lang: Language,
    text: str,
) -> None:
    monkeypatch.setattr(
        "bob_quality.npm_tools.__file__",
        str(tmp_path / "gone" / "npm_tools.py"),
    )
    code = run_doctor(lang=lang)
    captured = capsys.readouterr()
    path = tmp_path / "gone" / "package.json"
    detail = os.strerror(errno.ENOENT)
    assert code == 4
    assert captured.out == ""
    assert captured.err == (
        "bob doctor: package.json: " + text.format(path=path, detail=detail) + "\n"
    )


def test_doctor_runs_only_node_and_gitleaks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    names: list[str] = []

    def which(executable: str) -> str:
        return f"/fake/bin/{executable}"

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        name = Path(args[0]).name
        names.append(name)
        banner = {"node": "v22.18.0", "gitleaks": "8.30.1"}.get(name, "")
        return subprocess.CompletedProcess(args, 0, stdout=banner, stderr="")

    prefix = tmp_path / "empty-prefix"
    prefix.mkdir()
    monkeypatch.setattr("bob_quality.doctor.shutil.which", which)
    monkeypatch.setattr("bob_quality.doctor.subprocess.run", fake_run)
    monkeypatch.setattr("bob_quality.doctor._npm_root", lambda: prefix)
    rows = _rows()
    assert names == ["node", "gitleaks"]
    assert len(rows) == len(DOCTOR_PINS)


_NODE_PRERELEASES = (
    "v22.18.0-rc.1",
    "v22.18.0-beta.1",
    "v22.18.0-nightly20260101a1b2c3d4e5",
    "v22.18.0-pre",
    "v22.18.0-RC.1",
)

_NODE_BANNERS = (
    ("v20.19.0", 4),
    ("v22.18.0", 0),
    ("v22.14.0", 4),
    ("v22.15.0", 4),
    ("v22.17.9", 4),
    ("v22.22.2", 0),
    ("v24.0.0", 4),
    *((banner, 4) for banner in _NODE_PRERELEASES),
)

_NODE_TEXT = {
    "en": (
        "node expected >=22.18.0 <23 found {found}",
        "Install Node.js >=22.18.0 <23 (https://nodejs.org/dist/v22.18.0/)",
    ),
    "pt-BR": (
        "node esperada >=22.18.0 <23 encontrada {found}",
        "Instale Node.js >=22.18.0 <23 (https://nodejs.org/dist/v22.18.0/)",
    ),
}


@pytest.mark.parametrize(
    ("found", "admitted"),
    [
        ("20.19.0", False),
        ("22.13.1", False),
        ("22.14.0", False),
        ("22.15.0", False),
        ("22.17.9", False),
        ("22.18.0", True),
        ("22.22.2", True),
        ("23.0.0", False),
        ("24.0.0", False),
        (None, False),
        *((banner.removeprefix("v"), False) for banner in _NODE_PRERELEASES),
    ],
)
def test_node_admits_the_22_line_from_22_18_0(found: str | None, admitted: bool) -> None:
    assert node_admits(node_pin(), found) is admitted


def test_node_range_prints_the_floor_and_the_next_major() -> None:
    assert node_range(node_pin()) == ">=22.18.0 <23"


@pytest.mark.parametrize("banner", _NODE_PRERELEASES)
def test_assess_node_rejects_a_prerelease_suffix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, banner: str
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _stub(bin_dir, "node", banner)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", str(bin_dir))
    assert _assess_node(node_pin()) == _PinRow(
        msg(
            "doctor.version",
            name="node",
            expected=">=22.18.0 <23",
            found=banner.removeprefix("v"),
        ),
        False,
        msg(
            "doctor.install_node",
            version=">=22.18.0 <23",
            url="https://nodejs.org/dist/v22.18.0/",
        ),
        False,
    )


def test_assess_node_admits_22_22_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bob_quality.doctor._cli_version",
        lambda executable: {"node": "22.22.2"}.get(executable),
    )
    assert _assess_node(node_pin()) == _PinRow(
        msg("doctor.version", name="node", expected=">=22.18.0 <23", found="22.22.2"),
        True,
        None,
        False,
    )


def test_assess_node_rejects_24_with_the_install_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bob_quality.doctor._cli_version",
        lambda executable: {"node": "24.0.0"}.get(executable),
    )
    assert _assess_node(node_pin()) == _PinRow(
        msg("doctor.version", name="node", expected=">=22.18.0 <23", found="24.0.0"),
        False,
        msg(
            "doctor.install_node",
            version=">=22.18.0 <23",
            url="https://nodejs.org/dist/v22.18.0/",
        ),
        False,
    )


@pytest.mark.parametrize("lang", ("en", "pt-BR"))
@pytest.mark.parametrize(("banner", "code"), _NODE_BANNERS)
def test_doctor_accepts_node_22_from_22_18_0(
    tmp_path: Path, lang: str, banner: str, code: int
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, _expected, executable, pin_banner in PINS:
        if name == "node":
            pin_banner = banner
        if executable is None or pin_banner is None:
            continue
        _stub(bin_dir, executable, pin_banner)

    repo = tmp_path / "repo"
    repo.mkdir()
    result = _run_doctor(repo, bin_dir, "--lang", lang)

    line, install = _NODE_TEXT[lang]
    assert result.returncode == code, result.stdout + result.stderr
    assert line.format(found=banner.removeprefix("v")) in result.stdout
    assert (install in result.stdout) is (code == 4)
    assert not (repo / ".bob").exists()


def _bob_metadata(parent: Path, *requires: str) -> Path:
    dist = parent / "bob_quality-0.1.0.dist-info"
    dist.mkdir(parents=True)
    lines = [
        "Metadata-Version: 2.1",
        "Name: bob-quality",
        "Version: 0.1.0",
    ]
    lines.extend(f"Requires-Dist: {requirement}" for requirement in requires)
    (dist / "METADATA").write_text("\n".join(lines) + "\n")
    return parent


def _expected_versions(stdout: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in stdout.splitlines():
        name, rest = line.split(" expected ", 1)
        version, _shown = rest.split(" found ", 1)
        found[name] = version
    return found


def _gitleaks_pin() -> BinaryPin:
    return next(item for item in DOCTOR_PINS if isinstance(item, BinaryPin))


def test_gitleaks_pin_comes_from_the_gitleaks_table() -> None:
    pin = _gitleaks_pin()
    assert pin.expected == gitleaks.VERSION
    assert pin.url == gitleaks.asset_url(("linux", "x64"))
    assert pin.sha256 == gitleaks.ASSETS[("linux", "x64")][1]


def test_doctor_has_no_gitleaks_literals() -> None:
    text = (ROOT / "src" / "bob_quality" / "doctor.py").read_text()
    for _key, (_asset, digest) in gitleaks.ASSETS.items():
        assert digest not in text
    assert "releases/download/v" not in text


def test_doctor_finds_gitleaks_in_bob_home_before_the_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "bh"
    (home / "bin").mkdir(parents=True)
    _stub(home / "bin", "gitleaks", "gitleaks version 8.30.1")
    path_dir = tmp_path / "path"
    path_dir.mkdir()
    _stub(path_dir, "gitleaks", "8.29.0")
    monkeypatch.setenv("BOB_HOME", str(home))
    monkeypatch.setenv("PATH", str(path_dir))
    row = _assess_binary(_gitleaks_pin())
    assert row.ok is True
    assert row.line == msg(
        "doctor.version",
        name="gitleaks",
        expected="8.30.1",
        found="8.30.1",
    )


def test_doctor_cli_finds_gitleaks_in_bob_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "bh"
    (home / "bin").mkdir(parents=True)
    _stub(home / "bin", "gitleaks", "8.30.1")
    monkeypatch.setenv("BOB_HOME", str(home))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, _expected, executable, banner in PINS:
        if name == "gitleaks" or executable is None or banner is None:
            continue
        _stub(bin_dir, executable, banner)
    repo = tmp_path / "repo"
    repo.mkdir()
    result = _run_doctor(repo, bin_dir)
    assert "gitleaks expected 8.30.1 found 8.30.1" in result.stdout


def test_doctor_install_runs_npm_then_gitleaks(monkeypatch: pytest.MonkeyPatch) -> None:
    order: list[object] = []

    def npm(lang: str) -> int:
        order.append("npm")
        assert lang == "en"
        return 0

    def install(home: object) -> None:
        order.append(("gitleaks", home))

    def report(lang: str) -> int:
        order.append("report")
        assert lang == "en"
        return 0

    monkeypatch.setattr(doctor, "install_npm_dependencies", npm)
    monkeypatch.setattr(gitleaks, "ensure_gitleaks", install)
    monkeypatch.setattr(doctor, "_report_pins", report)
    assert run_doctor(install=True, lang="en") == 0
    assert order == ["npm", ("gitleaks", bob_home()), "report"]


def test_doctor_install_stops_when_npm_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor, "install_npm_dependencies", lambda lang: 4)

    def forbid(*args: object, **kwargs: object) -> int:
        raise AssertionError((args, kwargs))

    monkeypatch.setattr(gitleaks, "ensure_gitleaks", forbid)
    monkeypatch.setattr(doctor, "_report_pins", forbid)
    assert run_doctor(install=True) == 4


_INTEGRITY_ASSET = "gitleaks_8.30.1_linux_x64.tar.gz"


@pytest.mark.parametrize("lang", ["en", "pt-BR"])
def test_doctor_install_gitleaks_failure_exits_4(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    lang: Language,
) -> None:
    monkeypatch.setattr(doctor, "install_npm_dependencies", lambda chosen: 0)

    def fail(home: object) -> None:
        raise GitleaksError(msg("gitleaks.integrity", asset=_INTEGRITY_ASSET))

    def report(chosen: str) -> int:
        raise AssertionError(chosen)

    monkeypatch.setattr(gitleaks, "ensure_gitleaks", fail)
    monkeypatch.setattr(doctor, "_report_pins", report)
    assert run_doctor(install=True, lang=lang) == 4
    reason = msg("gitleaks.integrity", asset=_INTEGRITY_ASSET)
    assert capsys.readouterr().err == t(lang, "doctor.error", reason=reason) + "\n"


def test_doctor_install_with_relative_bob_home_exits_4(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("BOB_HOME", "rel")
    monkeypatch.setattr(doctor, "install_npm_dependencies", lambda lang: 0)

    def forbid(home: object) -> None:
        raise AssertionError(home)

    monkeypatch.setattr(gitleaks, "ensure_gitleaks", forbid)
    assert run_doctor(install=True) == 4
    assert capsys.readouterr().err == (
        "bob doctor: BOB_HOME=rel must be absolute. Use an absolute path.\n"
    )


def test_doctor_bob_home_relative_message_in_both_languages() -> None:
    english = "BOB_HOME=V must be absolute. Use an absolute path."
    portuguese = "BOB_HOME=V precisa ser absoluto. Use um caminho absoluto."
    assert t("en", "doctor.bob_home_relative", value="V") == english
    assert t("pt-BR", "doctor.bob_home_relative", value="V") == portuguese
