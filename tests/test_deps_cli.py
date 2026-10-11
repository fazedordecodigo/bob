"""Seam: CLI `bob deps` / `bob check --gates deps` sobre repos-fixture.

Pega exit code, veredito do gate e linhas origem → destino no report.md.
Não pega o formato cru das ferramentas (seam do adaptador).
"""

import json
import os
from pathlib import Path

from bob_quality.cli import main

from helpers import (
    SAFE_CHANGE,
    TS_SAFE_CHANGE,
    commit_on_branch,
    commit_on_main,
    init_python_repo,
    init_ts_repo,
)

LEFT = (Path(__file__).parent / "fixtures" / "python_app" / "cases" / "cycle_left.py").read_text()
RIGHT = (Path(__file__).parent / "fixtures" / "python_app" / "cases" / "cycle_right.py").read_text()
DOMAIN_PY = "VALUE = 1\n"
API_IMPORTS_DOMAIN = "from app.domain import VALUE\n\nAPI = VALUE\n"
API_IS_ALONE = "API = 1\n"
IMPORT_LINTER = """\
[importlinter]
root_packages =
    app

[importlinter:contract:api-not-domain]
name = API não importa domínio
type = forbidden
source_modules =
    app.api
forbidden_modules =
    app.domain
"""
LEFT_TS = 'import { right } from "./right";\nexport const left = right;\n'
RIGHT_TS = 'import { left } from "./left";\nexport const right = left;\n'
DOMAIN_TS = "export const domain = 1;\n"
API_TS = 'import { domain } from "./domain";\nexport const api = domain;\n'
API_TS_ALONE = "export const api = 1;\n"
CRUISER = """\
module.exports = {
  forbidden: [
    {
      name: "api-not-domain",
      severity: "error",
      from: { path: "(^|/)api\\.ts$" },
      to: { path: "(^|/)domain\\.ts$" },
    },
  ],
};
"""


def _invoke(repo: Path, *args: str) -> int:
    previous = os.getcwd()
    os.chdir(repo)
    try:
        return main(list(args))
    finally:
        os.chdir(previous)


def _deps(repo: Path) -> tuple[dict[str, object], str]:
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    return payload, markdown


def test_python_cycle_fails_without_import_linter_config(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    assert not (repo / ".importlinter").exists()
    commit_on_branch(repo, "cycle", "src/app/left.py", LEFT, "add left")
    commit_on_branch(repo, "cycle", "src/app/right.py", RIGHT, "add right")

    code = _invoke(repo, "deps", "--base", "main")
    payload, markdown = _deps(repo)
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")

    assert code == 1, markdown
    assert deps["status"] == "failed"
    assert "## Violações e ciclos de dependência" in markdown
    assert "`app.right → app.left` (Proibido ciclo de dependência)" in markdown


def test_python_cycle_already_on_main_is_information_and_does_not_fail(
    tmp_path: Path,
) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/left.py", LEFT, "old left")
    commit_on_main(repo, "src/app/right.py", RIGHT, "old right")
    commit_on_branch(repo, "safe-change", "src/app/safe.py", SAFE_CHANGE, "touch add")

    code = _invoke(repo, "deps", "--base", "main")
    payload, markdown = _deps(repo)
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")

    assert code == 0, markdown
    assert deps["status"] == "passed"
    assert payload["dependencies"] == []
    assert payload["old_dependencies"] == [
        {
            "origin": "app.right",
            "destination": "app.left",
            "rule": "Proibido ciclo de dependência",
        }
    ]
    assert "`app.right → app.left` (Proibido ciclo de dependência)" in markdown
    assert "fora do diff; não bloqueia" in markdown
    assert "❌ `deps`" not in markdown


def test_check_gates_deps_reports_the_same_python_cycle(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "cycle", "src/app/left.py", LEFT, "add left")
    commit_on_branch(repo, "cycle", "src/app/right.py", RIGHT, "add right")

    code = _invoke(repo, "check", "--base", "main", "--gates", "deps")
    payload, markdown = _deps(repo)

    assert code == 1, markdown
    assert payload["exit_code"] == 1
    assert "`app.right → app.left`" in markdown
    assert "bob check --base main --gates deps" in payload["reproduce"]


def test_python_without_cycle_passes_deps(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "safe-change", "src/app/safe.py", SAFE_CHANGE, "touch tested add")

    code = _invoke(repo, "check", "--base", "main")
    payload, markdown = _deps(repo)
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")

    assert code == 0, markdown
    assert deps["status"] == "passed"
    assert "Nenhuma violação de dependência." in markdown
    assert payload["tool_versions"]["import-linter"] == "2.15"


def test_declared_import_linter_rule_fails_when_broken(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "layers", ".importlinter", IMPORT_LINTER, "declare forbidden contract")
    commit_on_branch(repo, "layers", "src/app/domain.py", DOMAIN_PY, "add domain")
    commit_on_branch(repo, "layers", "src/app/api.py", API_IMPORTS_DOMAIN, "api imports domain")

    code = _invoke(repo, "deps", "--base", "main")
    _payload, markdown = _deps(repo)

    assert code == 1, markdown
    assert "`app.api → app.domain` (API não importa domínio)" in markdown


def test_declared_import_linter_rule_passes_when_kept(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "layers", ".importlinter", IMPORT_LINTER, "declare forbidden contract")
    commit_on_branch(repo, "layers", "src/app/domain.py", DOMAIN_PY, "add domain")
    commit_on_branch(repo, "layers", "src/app/api.py", API_IS_ALONE, "api stays alone")

    code = _invoke(repo, "deps", "--base", "main")
    payload, markdown = _deps(repo)
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")

    assert code == 0, markdown
    assert deps["status"] == "passed"
    assert "app.api → app.domain" not in markdown


def test_typescript_cycle_fails_without_cruiser_config(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    assert not (repo / ".dependency-cruiser.cjs").exists()
    commit_on_branch(repo, "cycle", "src/left.ts", LEFT_TS, "add left")
    commit_on_branch(repo, "cycle", "src/right.ts", RIGHT_TS, "add right")

    code = _invoke(repo, "deps", "--base", "main")
    payload, markdown = _deps(repo)
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")

    assert code == 1, markdown
    assert deps["status"] == "failed"
    assert "`src/left.ts → src/right.ts`" in markdown
    assert "`src/right.ts → src/left.ts`" in markdown
    assert payload["tool_versions"]["dependency-cruiser"] == "18.5.0"


def test_typescript_cycle_already_on_main_is_information_and_does_not_fail(
    tmp_path: Path,
) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_main(repo, "src/left.ts", LEFT_TS, "old left")
    commit_on_main(repo, "src/right.ts", RIGHT_TS, "old right")
    commit_on_branch(repo, "safe-change", "src/safe.ts", TS_SAFE_CHANGE, "touch add")

    code = _invoke(repo, "deps", "--base", "main")
    payload, markdown = _deps(repo)
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")
    old = {
        (item["origin"], item["destination"])
        for item in payload["old_dependencies"]
    }

    assert code == 0, markdown
    assert deps["status"] == "passed"
    assert payload["dependencies"] == []
    assert ("src/left.ts", "src/right.ts") in old
    assert ("src/right.ts", "src/left.ts") in old
    assert "fora do diff; não bloqueia" in markdown
    assert "❌ `deps`" not in markdown


def test_declared_cruiser_rule_fails_when_broken(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(repo, "layers", ".dependency-cruiser.cjs", CRUISER, "declare forbidden rule")
    commit_on_branch(repo, "layers", "src/domain.ts", DOMAIN_TS, "add domain")
    commit_on_branch(repo, "layers", "src/api.ts", API_TS, "api imports domain")

    code = _invoke(repo, "deps", "--base", "main")
    _payload, markdown = _deps(repo)

    assert code == 1, markdown
    assert "`src/api.ts → src/domain.ts` (api-not-domain)" in markdown


def test_declared_cruiser_rule_passes_when_kept(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(repo, "layers", ".dependency-cruiser.cjs", CRUISER, "declare forbidden rule")
    commit_on_branch(repo, "layers", "src/domain.ts", DOMAIN_TS, "add domain")
    commit_on_branch(repo, "layers", "src/api.ts", API_TS_ALONE, "api stays alone")

    code = _invoke(repo, "deps", "--base", "main")
    payload, markdown = _deps(repo)
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")

    assert code == 0, markdown
    assert deps["status"] == "passed"
    assert "src/api.ts → src/domain.ts" not in markdown
