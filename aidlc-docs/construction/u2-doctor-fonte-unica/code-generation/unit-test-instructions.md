# U2 — Instruções de teste da unit

## Preparação (igual ao `AGENTS.md` e ao `ci.yml`)
1. Python 3.10 ou 3.12; Node `>=22.18.0 <23`.
2. `python -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'`
3. `npm ci` na raiz.
4. gitleaks 8.30.1 no `PATH`, baixado e conferido por sha256 como em `.github/workflows/ci.yml`.
5. `rm -rf src/bob_quality/node_modules` (se existir, muda o prefixo que `npm_prefix()` escolhe).
6. Nada de `.bob/`, `mutants/`, `dist/` ou `node_modules/` no commit.

## Comando por unit (não é o comando geral)
`python -m pytest -q tests/test_npm_pin.py tests/test_doctor.py tests/test_ts_cli.py tests/test_gate_publications.py tests/test_action_workflow.py tests/test_messages.py`
Esperado: última linha `N passed` com `0 failed` e sem `error`. `skipped` só os que já pulam na `main` com o mesmo ambiente (nenhum novo).

## Regressão
`python -m pytest -q` → `0 failed`, `0 errors`. Linha de base na `main`: 18 failed (run 39159800836).

## Metas
- Linhas alteradas em `src/`: 100% cobertas.
- CRAP < 10 por função alterada; mutate: 0 sobreviventes sem waiver.
- `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → exit 0.

## Dados e dublês
| Dublê | Onde | Para quê |
|---|---|---|
| `manifest` (fixture): troca `bob_quality.npm_tools.__file__` por `tmp_path/bob_quality/npm_tools.py` | `test_npm_pin.py` | `package.json` empacotado sintético (bump, erros de formato, arquivo ausente) |
| `_bob_npm_prefix(parent)`: `XDG_CACHE_HOME` com `bob-quality/package.json` (cópia da raiz) e `node_modules/<pacote>/package.json` | `test_doctor.py::_run_doctor` | prefixo do bob pronto, sem `npm ci` |
| `_stub(bin_dir, nome, banner)` | `test_doctor.py` | `node`, `gitleaks` e CLIs Python no `PATH` |
| `_tree_digest(root)` | `test_doctor.py` | sha256 de cada arquivo do projeto antes e depois (NFR5) |
| `monkeypatch` de `_npm_root`, `_cli_version`, `shutil.which`, `subprocess.run` | `test_doctor.py` | testes em processo de `_found_version`, `_assess*`, `_rows` |
| Versões sintéticas: `1.0.0`, `1.2.3`, `1.2.4`, `3.4.5`, `9.9.9`, `0.0.1`, `4.1.0`, `24.1.0` | testes novos | nenhuma versão npm real literal em `test_npm_pin.py` (Pronto 1) |

## Mapa teste → regra
| Regra / Pronto | Teste |
|---|---|
| R1, Pronto 1 | `test_pins_and_node_range_come_from_the_packaged_package_json`, `test_a_bumped_package_json_changes_the_pins_without_code`, `test_doctor_pins_match_pyproject_and_package_json` |
| R2 | `test_node_range_rejects_an_engine_out_of_format` (6), `test_node_pin_comes_from_engines_node_of_the_packaged_package_json` |
| R3 | `test_npm_specs_are_exact_versions`, `test_pinned_npm_versions_rejects_a_package_json_out_of_format` (7) |
| R4, Pronto 3 | `test_package_lock_matches_package_json`, `test_lock_mismatch_names_the_package_and_both_versions` |
| R5 | `test_found_version_reads_the_bob_prefix`, `test_found_version_ignores_the_path_when_the_prefix_lacks_the_package`, `test_doctor_reads_npm_versions_from_the_bob_prefix_not_the_path` |
| R6, R7, Pronto 4 | `test_doctor_ignores_the_vitest_installed_in_the_project`, `test_doctor_ignores_binaries_in_the_project_node_modules` |
| R8 | `test_doctor_runs_only_node_and_gitleaks` |
| R9 | testes existentes de saída do doctor (en e pt-BR), sem mudança de texto |
| Pronto 2 | `test_vitest_5_0_5_in_the_bob_prefix_passes_when_package_json_pins_5_0_5`; `bob doctor` no CI |
| Erros | `test_missing_package_json_names_the_file`, `test_doctor_exits_4_with_one_stderr_line_when_package_json_is_unreadable` (en, pt-BR), `test_pin_source_detail_is_written_in_both_languages` (8), `test_pin_source_error_is_a_tool_error` |
