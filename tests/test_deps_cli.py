"""Seam: CLI `bob deps` / `bob check --gates deps` sobre repos-fixture.

Pega exit code, veredito do gate e linhas origem → destino no report.md.
Não pega o formato cru das ferramentas (seam do adaptador).
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from helpers import (
    SAFE_CHANGE,
    TS_SAFE_CHANGE,
    commit_on_branch,
    commit_on_main,
    init_mixed_repo,
    init_python_repo,
    init_ts_repo,
    run_bob,
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
    return run_bob(repo, *args).returncode


def _deps(repo: Path) -> tuple[dict[str, object], str]:
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    return payload, markdown


def test_deps_exits_4_when_grimp_cannot_build_the_import_graph(tmp_path: Path) -> None:
    repo = init_python_repo(tmp_path / "repo")
    commit_on_branch(repo, "bad", "src/app/broken.py", "def (\n", "syntax error")

    code = _invoke(repo, "deps", "--base", "main")
    payload, markdown = _deps(repo)
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")

    assert code == 4, markdown
    assert deps["status"] == "not_run"
    assert "grimp" in (deps["reason"] or "").lower()


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
    assert "## Dependency violations and cycles" in markdown
    assert "`app.right → app.left` (Proibido ciclo de dependência)" in markdown


A_PY = "from app.b import VALUE as B\n\nVALUE = B\n"
B_PY = "from app.c import VALUE as C\n\nVALUE = C\n"
C_PY = "from app.a import VALUE as A\n\nVALUE = A\n"
B_TOUCHED = "from app.c import VALUE as C\n\nVALUE = C\nTOUCHED = 1\n"


Y_A = "from y.b import VALUE as B\n\nVALUE = B\n"
Y_B = "from y.a import VALUE as A\n\nVALUE = A\n"
X_B = "VALUE = 1\n"


def test_changing_x_b_does_not_mark_y_b_in_the_diff(tmp_path: Path) -> None:
    """`src/x/b.py` e `src/x/y/b.py` não são o módulo `y.b` em `src/y/b.py`."""
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/y/__init__.py", "", "package y")
    commit_on_main(repo, "src/y/a.py", Y_A, "add y.a")
    commit_on_main(repo, "src/y/b.py", Y_B, "add y.b")
    commit_on_branch(repo, "lookalike", "src/x/b.py", X_B, "touch x/b.py")
    commit_on_branch(repo, "lookalike", "src/x/y/b.py", X_B, "touch x/y/b.py")

    code = _invoke(repo, "deps", "--base", "main")
    payload, markdown = _deps(repo)
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")

    assert code == 0, markdown
    assert deps["status"] == "passed"
    assert payload["dependencies"] == []
    assert "outside the diff; does not block" in markdown


def test_python_three_cycle_blocks_when_only_the_middle_module_changes(
    tmp_path: Path,
) -> None:
    """a→b→c→a: mudar só b.py bloqueia, mesmo que o import-linter cite só c→a."""
    repo = init_python_repo(tmp_path / "repo")
    commit_on_main(repo, "src/app/a.py", A_PY, "add a")
    commit_on_main(repo, "src/app/b.py", B_PY, "add b")
    commit_on_main(repo, "src/app/c.py", C_PY, "add c")
    commit_on_branch(repo, "touch-b", "src/app/b.py", B_TOUCHED, "touch middle module")

    code = _invoke(repo, "deps", "--base", "main")
    payload, markdown = _deps(repo)
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")

    assert code == 1, markdown
    assert deps["status"] == "failed"
    assert payload["dependencies"]
    assert "❌ `deps`" in markdown


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
    assert "outside the diff; does not block" in markdown
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
    assert "No dependency violations." in markdown
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


A_TS = 'import { b } from "./b";\nexport const a = b;\n'
B_TS = 'import { c } from "./c";\nexport const b = c;\n'
C_TS = 'import { a } from "./a";\nexport const c = a;\n'
B_TS_TOUCHED = 'import { c } from "./c";\nexport const b = c;\nexport const touched = 1;\n'


def test_typescript_three_cycle_blocks_when_only_the_middle_module_changes(
    tmp_path: Path,
) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_main(repo, "src/a.ts", A_TS, "add a")
    commit_on_main(repo, "src/b.ts", B_TS, "add b")
    commit_on_main(repo, "src/c.ts", C_TS, "add c")
    commit_on_branch(repo, "touch-b", "src/b.ts", B_TS_TOUCHED, "touch middle module")

    code = _invoke(repo, "deps", "--base", "main")
    payload, markdown = _deps(repo)
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")

    assert code == 1, markdown
    assert deps["status"] == "failed"
    assert payload["dependencies"]
    assert "❌ `deps`" in markdown


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
    assert "outside the diff; does not block" in markdown
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


def test_mixed_repo_without_node_measures_python_deps_and_skips_typescript(
    tmp_path: Path,
) -> None:
    repo = init_mixed_repo(tmp_path / "repo")
    commit_on_branch(repo, "touch", "src/app/safe.py", SAFE_CHANGE, "touch python")

    code, payload, markdown = _deps_without_node(repo)
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")

    assert code == 0, markdown
    assert deps["status"] == "warn"
    assert deps["reason"].startswith("TypeScript skipped:")
    assert "Node missing" in deps["reason"]
    assert "import-linter" in payload["tool_versions"]
    assert "⚠️ `deps`: warning (TypeScript skipped:" in markdown


def test_mixed_repo_without_node_still_fails_a_new_python_dependency_violation(
    tmp_path: Path,
) -> None:
    repo = init_mixed_repo(tmp_path / "repo")
    left = "from app.right import RIGHT\n\nLEFT = RIGHT\n"
    right = "from app.left import LEFT\n\nRIGHT = LEFT\n"
    commit_on_branch(repo, "cycle", "src/app/left.py", left, "add left")
    commit_on_branch(repo, "cycle", "src/app/right.py", right, "add right")

    code, payload, markdown = _deps_without_node(repo)
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")

    assert code == 1, markdown
    assert deps["status"] == "failed"
    assert "app.right → app.left" in deps["reason"]
    assert "TypeScript skipped:" in deps["reason"]
    assert "❌ `deps`" in markdown


def test_typescript_repo_without_node_keeps_deps_exit_4(tmp_path: Path) -> None:
    repo = init_ts_repo(tmp_path / "repo")
    commit_on_branch(repo, "touch", "src/safe.ts", "export const add = 1;\n", "touch")

    code, payload, markdown = _deps_without_node(repo)
    deps = next(gate for gate in payload["gates"] if gate["name"] == "deps")

    assert code == 4, markdown
    assert deps["status"] == "not_run"
    assert "Node missing" in deps["reason"]
    assert "TypeScript skipped" not in deps["reason"]


def _deps_without_node(repo: Path) -> tuple[int, dict[str, object], str]:
    bindir = repo.parent / "bin"
    bindir.mkdir()
    os.symlink(shutil.which("git"), bindir / "git")
    result = subprocess.run(
        [sys.executable, "-m", "bob_quality", "deps", "--base", "main"],
        cwd=repo,
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": str(bindir)},
    )
    code = result.returncode
    payload = json.loads((repo / ".bob" / "report.json").read_text())
    markdown = (repo / ".bob" / "report.md").read_text()
    return code, payload, markdown
