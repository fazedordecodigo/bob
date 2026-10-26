# U4 — Instruções de testes unitários

## Preparação
- Python 3.10+ com `pip install -e '.[dev]'` (como no CI); `git` no `PATH`. Rede: não precisa, exceto no e2e manual da T2 e no harness, que montam o espelho local e baixam o gitleaks para o cache. O e2e da T1b só precisa do `pip install` num venv (Node é opcional: sem Node, o `dry` fica `not_run` com `0`).
- Os testes da U4 criam repositórios git em `tmp_path` (`git init -q`, `git config user.email/name` locais) e não tocam no checkout.

## Comando por tarefa
| Tarefa | Comando | Esperado |
|---|---|---|
| T1 | `python -m pytest -q tests/test_init_config.py` | exit 0; os 23 testes da ET coletados (mais itens por causa dos parametrizados); `0 failed` |
| T1b | `python -m pytest -q tests/test_check_dispatch.py tests/test_check_report.py tests/test_mutation_branches.py` | exit 0; os 5 testes novos (10 casos) coletados; `0 failed` |
| T2 | `python -m pytest -q tests/test_setup_cmd.py tests/test_init_config.py` | exit 0; `0 failed` |
| T3 | `python -m pytest -q tests/test_verify_install.py` e `sh scripts/verify-install.sh --only 5,7,8` | exit 0; harness com `verify-install: passo 2: ok`, `… 5: ok`, `… 7: ok`, `… 8: ok` |
| T1c (só docs, sem teste novo) | `python -m pytest -q tests/test_gate_publications.py tests/test_skills_contract.py` e, em `website/` (Node `>=22.18.0 <23`), `npm ci && npm run build && npm test` | pytest exit 0, `0 failed`; os três `npm` com exit 0, sem link ou âncora quebrada (`onBrokenLinks`/`onBrokenAnchors: 'throw'`); `grep -cF 'no code to measure'` → `docs/exit-codes.md:2`, `README.md:1`, `docs/adr/0003-exit-codes.md:1`; `grep -cF 'nenhum código a medir'` → espelho pt-BR `:1`, `README.pt-BR.md:1` |

## Regressão
- `python -m pytest -q` → exit 0, `0 failed`, sem `error`, em toda tarefa.
- `test_setup_cmd.py::test_setup_does_not_touch_the_project_package_files` passa sem edição a partir da T2 (roda os `STEPS` reais, agora com `bob.yaml`).
- `test_check_report.py::test_a_missing_coverage_file_stays_a_tool_failure` passa sem edição a partir da T1b (projeto com código + erro real de coverage → `4`).
- A partir da T1b, teste que mede `crap` ou `coverage` por `_measure`/`run_check` precisa de código no `include`; o único ajuste previsto é `test_mutation_branches.py::test_absorb_records_every_gate_argument_and_result` (2 linhas que criam `src/app.py`).
- A T1c não muda `src/` nem `tests/`; o título `## Exit 4` de `docs/exit-codes.md` fica igual (âncora `exit-4` citada pela skill `bob-check`, conferida por `test_skills_contract.py`). O PR dela soma o check `website / build` aos 6.
- Harness inteiro (`sh scripts/verify-install.sh`) no check `verify-install / linux-x64` de cada PR: 9 linhas `ok` a partir da T3 (8 antes).

## Comando de Verificação (subconjunto U4)
- Passo 5: `sh scripts/verify-install.sh --only 5` (faz o 2 antes) → `ok 2` e `ok 5`.
- Passos 7 e 8: `sh scripts/verify-install.sh --only 7,8` → `ok 2`, `ok 7`, `ok 8`.

## Metas
`bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → exit 0 (CRAP < 10 por função, 0 sobreviventes, 0 waivers novos, cobertura ≥ 80,0 e 100% das linhas novas de `src/`); `gitleaks` 0 achados (check `check`).

## Mapa pronto → teste
| Pronto | Teste |
|---|---|
| 1 | harness passo 5; `test_init_config.py`: `test_write_creates_src_when_src_has_code`, `test_write_lists_every_code_folder_in_code_point_order`, `test_no_code_is_dot_and_created_no_code`, `test_generated_files_pass_load_config`; `bob check` ≠ 4 sem código: T1b (`test_a_repo_without_code_skips_crap_and_coverage_and_exits_0`, `test_measure_skips_crap_and_coverage_without_code`, e2e da T1b) |
| 2 | harness passo 5; `test_setup_cmd.py`: `test_bob_yaml_step_warns_when_there_is_no_code`, `test_bob_yaml_step_no_code_warning_reaches_the_output` |
| 3 | `test_render_config_is_the_ct7_text`; `test_verify_install.py::test_harness_expects_the_ct7_text` |
| 4 | harness passo 8; `test_existing_bob_yaml_is_preserved`; `test_bob_yaml_step_lists_existing_waivers`; `test_bob_yaml_step_reaches_the_summary` |
