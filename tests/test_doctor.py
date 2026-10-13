"""Seam: CLI `bob doctor` (stdout + exit code).

Versões literais das ferramentas pinadas. Os stubs imitam o `--version` real;
o teste não importa o catálogo interno.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from bob_quality.doctor import PINS as DOCTOR_PINS
from bob_quality.doctor import RequiresDist, ToolPin, unconditional_exact_pins
from bob_quality.doctor import _assess, _assess_requires_dist, _assess_tool, _own_requirements
from bob_quality.messages import msg

ROOT = Path(__file__).resolve().parents[1]

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
    ("node", "22.14.0", "node", "v22.14.0"),
    ("c8", "12.0.0", "c8", "12.0.0"),
    ("vitest", "5.0.3", "vitest", "5.0.3"),
    ("jscpd", "5.4.1", "jscpd", "jscpd 5.4.1"),
    ("mutmut", "3.8.0", "mutmut", "mutmut, version 3.8.0"),
    ("import-linter", "2.15", "lint-imports", "2.15"),
    ("grimp", "3.17", None, None),
    ("dependency-cruiser", "18.5.0", "dependency-cruiser", "18.5.0"),
    ("knip", "6.41.0", "knip", "6.41.0"),
)

INSTALL = {
    "lizard": "pip install 'lizard==1.24.1'",
    "coverage.py": "pip install 'coverage==7.16.2'",
    "node": "Install Node.js 22.14.0 (https://nodejs.org/dist/v22.14.0/)",
    "c8": "npm install c8@12.0.0",
    "vitest": "npm install vitest@5.0.3",
    "jscpd": "npm install jscpd@5.4.1",
    "mutmut": "pip install 'mutmut==3.8.0'",
    "import-linter": "pip install 'import-linter==2.15'",
    "grimp": "pip install 'grimp==3.17'",
    "dependency-cruiser": "npm install dependency-cruiser@18.5.0",
    "knip": "npm install knip@6.41.0",
}


def _c8_package(parent: Path, *, cli_banner: str) -> Path:
    package = parent / "c8"
    package_bin = package / "bin"
    package_bin.mkdir(parents=True)
    (package / "package.json").write_text(
        json.dumps({"name": "c8", "version": "12.0.0", "bin": {"c8": "./bin/c8.js"}})
    )
    script = package_bin / "c8.js"
    script.write_text(f"#!/bin/sh\nprintf '%s\\n' '{cli_banner}'\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


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
    assert "dependency-cruiser expected 18.5.0 found 18.5.0" in result.stdout


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
    for name, expected, _executable, _banner in PINS:
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
    assert "node expected 22.14.0 found missing" in result.stdout
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
    assert "node esperada 22.14.0 encontrada ausente" in result.stdout
    assert "Instale Node.js 22.14.0 (https://nodejs.org/dist/v22.14.0/)" in result.stdout


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
    assert "node expected 22.14.0 found 1.2.3" in result.stdout
    assert INSTALL["node"] in result.stdout
    assert INSTALL["lizard"] not in result.stdout


def test_doctor_reports_c8_package_version_when_cli_prints_another(tmp_path: Path) -> None:
    """c8 --version repassa a versão do projeto; o doctor mostra a do pacote c8."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = _c8_package(tmp_path / "node_modules", cli_banner="1.0.0")
    (bin_dir / "c8").symlink_to(script)

    for name, _expected, executable, banner in PINS:
        if executable == "c8":
            continue
        if executable is None or banner is None:
            continue
        _stub(bin_dir, executable, banner)

    repo = tmp_path / "repo"
    repo.mkdir()
    result = _run_doctor(repo, bin_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "c8 expected 12.0.0 found 12.0.0" in result.stdout


def test_doctor_finds_npm_tool_installed_in_the_project(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, _expected, executable, banner in PINS:
        if executable == "c8":
            continue
        if executable is None or banner is None:
            continue
        _stub(bin_dir, executable, banner)

    repo = tmp_path / "repo"
    script = _c8_package(repo / "node_modules", cli_banner="1.0.0")
    local_bin = repo / "node_modules" / ".bin"
    local_bin.mkdir()
    (local_bin / "c8").symlink_to(script)

    result = _run_doctor(repo, bin_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "c8 expected 12.0.0 found 12.0.0" in result.stdout


def test_doctor_reads_c8_manifest_when_bin_shim_is_not_a_symlink(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for _name, _expected, executable, banner in PINS:
        if executable == "c8":
            continue
        if executable is None or banner is None:
            continue
        _stub(bin_dir, executable, banner)

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text(json.dumps({"name": "bob", "version": "0.1.0"}))
    _c8_package(repo / "node_modules", cli_banner="12.0.0")
    local_bin = repo / "node_modules" / ".bin"
    local_bin.mkdir()
    shim = local_bin / "c8"
    shim.write_text("#!/bin/sh\nprintf '%s\\n' '0.1.0'\n")
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC)

    result = _run_doctor(repo, bin_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "c8 expected 12.0.0 found 12.0.0" in result.stdout


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
    package = json.loads((ROOT / "package.json").read_text())
    npm = package["dependencies"]

    for pin in DOCTOR_PINS:
        if isinstance(pin, RequiresDist):
            assert pin.distribution in requirements
        elif pin.npm_package is not None:
            assert npm[pin.npm_package] == pin.expected
        else:
            assert pin.name == "node"
    npm_pins = {
        pin.npm_package: pin.expected
        for pin in DOCTOR_PINS
        if isinstance(pin, ToolPin) and pin.npm_package is not None
    }
    assert npm_pins == npm


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

    package = json.loads((ROOT / "package.json").read_text())
    assert package["private"] is True
    npm = package["dependencies"]
    assert npm["c8"] == expected["c8"]
    assert npm["vitest"] == expected["vitest"]
    assert npm["jscpd"] == expected["jscpd"]
    assert npm["dependency-cruiser"] == expected["dependency-cruiser"]
    assert npm["knip"] == expected["knip"]
    assert set(npm) == {"c8", "dependency-cruiser", "jscpd", "knip", "vitest"}


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
    row = _assess(RequiresDist("grimp", "grimp"), {"grimp": "3.17"})
    assert row.ok is True
    assert row.line == msg("doctor.version", name="grimp", expected="3.17", found="3.17")


def test_assess_tool_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bob_quality.doctor._found_version", lambda pin: pin.expected)
    row = _assess_tool(ToolPin("node", "22.14.0", "node", "install node"))
    assert row.line == msg(
        "doctor.version", name="node", expected="22.14.0", found="22.14.0"
    )
    assert row.ok is True
    assert row.install is None
    assert row.npm_missing is False


def test_assess_tool_mismatch_prints_the_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bob_quality.doctor._found_version", lambda pin: "0")
    row = _assess_tool(ToolPin("node", "22.14.0", "node", "install node"))
    assert row.line == msg("doctor.version", name="node", expected="22.14.0", found="0")
    assert row.ok is False
    assert row.install == "install node"
    assert row.npm_missing is False


def test_assess_tool_npm_mismatch_has_no_install_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bob_quality.doctor._found_version", lambda pin: "0")
    row = _assess_tool(ToolPin("c8", "12.0.0", "c8", "npm install c8@12.0.0", npm_package="c8"))
    assert row.line == msg("doctor.version", name="c8", expected="12.0.0", found="0")
    assert row.ok is False
    assert row.install is None
    assert row.npm_missing is True


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
