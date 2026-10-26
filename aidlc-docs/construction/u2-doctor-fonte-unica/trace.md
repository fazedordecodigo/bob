# U2 — Rastreabilidade (US/FR/NFR/CT → passo → tarefa → prova)

Escopo: só esta unit. Cadeia fechada em 2026-10-18 23:3x (UTC-3) e espelhada em `inception/units/traceability.json` (U2: `status`, `tasks`, `prs`, `tests`).

| Origem | Item | Passo(s) | Tarefa | Prova |
|---|---|---|---|---|
| US1.4 crit. 2 | Projeto com vitest/eslint em outra versão → doctor confere as do bob e sai 0 | P2, P6 | T1 | `test_doctor_ignores_the_vitest_installed_in_the_project` |
| US1.4 crit. 1 (contribui) | 0 bytes mudam no projeto | P2, P6 | T1 | mesmo teste (`_tree_digest` antes = depois) |
| US1.1 crit. 5 (contribui) | Ferramentas que o doctor confere nas versões pinadas | P1, P4, P6 | T1 | `test_pins_and_node_range_come_from_the_packaged_package_json`; `bob doctor` = 0 no job `package / dist` |
| FR2.1 | Ferramentas nas versões pinadas (fonte única) | P1, P3, P4, P6 | T1 | `test_doctor_pins_match_pyproject_and_package_json`, `test_a_bumped_package_json_changes_the_pins_without_code` |
| FR2.5 | Doctor confere as ferramentas do bob, não as do projeto | P2, P6 | T1 | `test_doctor_ignores_the_vitest_installed_in_the_project`, `test_doctor_ignores_binaries_in_the_project_node_modules`, `test_found_version_ignores_the_path_when_the_prefix_lacks_the_package` |
| FR1.5 (CT8) | `run_doctor` mostra o resultado; consumido pela U1 | P6 | T1 | testes de saída do doctor (en/pt-BR) inalterados |
| NFR5 | 0 bytes alterados no projeto | P2, P6 | T1 | `test_doctor_ignores_the_vitest_installed_in_the_project` |
| NFR9 / CT1 | Erro em uma linha, passo e ação | P5, P6 | T1 | `test_doctor_exits_4_with_one_stderr_line_when_package_json_is_unreadable[en,pt-BR]` |
| CT8 | `PinSourceError`, `pinned_npm_versions()`, `NodeRange`, `node_range()`, `doctor.node_range(pin)` | P4, P6 | T1 | `tests/test_npm_pin.py` (11 testes novos) |
| ADR 0008 | `package.json` empacotado é a fonte única | P1, P4 | T1 | `rg` de literais → exit 1 |
| ADR 0019 | npm só do prefixo do bob; binários só do `PATH` | P6 | T1 | `test_found_version_reads_the_bob_prefix`, `test_doctor_runs_only_node_and_gitleaks` |
| Pronto 1 | Sem versão npm literal em `doctor.py` e `test_npm_pin.py` | P1, P6 | T1 | `rg -n -F …` → exit 1 |
| Pronto 2 | `bob doctor` = 0 com vitest 5.0.5 | P2, P8 | T1 | `test_vitest_5_0_5_in_the_bob_prefix_passes_when_package_json_pins_5_0_5`; `bob doctor` no PR |
| Pronto 3 | Lock divergente → teste falha | P1 | T1 | `test_lock_mismatch_names_the_package_and_both_versions`, `test_package_lock_matches_package_json` |
| Pronto 4 | vitest 4.x no cwd → doctor 0 com a versão do bob | P2 | T1 | `test_doctor_ignores_the_vitest_installed_in_the_project` |
| Pronto 5 | Job `package` da `main` volta a passar | P8, P9 | T1 | check `package / dist` no PR; run na `main` depois do merge (Arquiteto) |
| DoD 3 | `verify-install.sh --only` | — | — | N/A para U2 (I7: prova só por pytest; harness é da U1) |
| DoD 6 | Merge pelo Emerson | P9 | T1 | critério de aceite da ET |

## Mudanças de contrato a registrar (fora desta pasta, pelo Maestro)
- CT8: `NODE` (constante) → `node_pin()` (função); `NpmPin(name, npm_package)` sem `expected`/`executable`; marcador `NodeSlot` em `PINS`. Sem consumidor fora dos testes.
- I9 (nova): o teste "install.sh tem a mesma faixa de Node/Python" de CT8 vai para a U1 (o `install.sh` ainda não existe).

## Fechamento da cadeia (US/FR → T1 → PR → testes)
Fechada em 2026-10-18 23:3x (UTC-3), por leitura remota de `fazedordecodigo/bob` (sem clone).

| US/FR | Tarefa | PR | Testes na `main` (todos conferidos em `053dcaab`) |
|---|---|---|---|
| US1.4 (crit. 1 e 2) | T1 | [#183](https://github.com/fazedordecodigo/bob/pull/183) | `tests/test_doctor.py::test_doctor_ignores_the_vitest_installed_in_the_project`, `::test_doctor_ignores_binaries_in_the_project_node_modules` |
| US1.1 crit. 5 (contribui) | T1 | #183 | `tests/test_npm_pin.py::test_pins_and_node_range_come_from_the_packaged_package_json`, `tests/test_doctor.py::test_doctor_pins_match_pyproject_and_package_json` |
| FR2.1 | T1 | #183 | `tests/test_npm_pin.py::test_npm_specs_are_exact_versions`, `::test_package_lock_matches_package_json`, `::test_packaged_package_json_is_the_root_one`, `::test_a_bumped_package_json_changes_the_pins_without_code`, `tests/test_doctor.py::test_vitest_5_0_5_in_the_bob_prefix_passes_when_package_json_pins_5_0_5`, `::test_node_pin_comes_from_engines_node_of_the_packaged_package_json`, `::test_assess_npm_matches`, `::test_assess_npm_mismatch_has_no_install_line`, `::test_assess_sends_an_npm_pin_to_the_npm_row`, `::test_assess_npm_without_an_expected_version_is_not_ok` |
| FR2.5 | T1 | #183 | `tests/test_doctor.py::test_doctor_reads_npm_versions_from_the_bob_prefix_not_the_path`, `::test_found_version_reads_the_bob_prefix`, `::test_found_version_ignores_the_path_when_the_prefix_lacks_the_package`, `::test_doctor_ignores_the_vitest_installed_in_the_project`, `::test_doctor_ignores_binaries_in_the_project_node_modules` |
| NFR5 | T1 | #183 | `tests/test_doctor.py::test_doctor_ignores_the_vitest_installed_in_the_project` (`_tree_digest` antes = depois) |
| CT1 / CT8 | T1 | #183 | `tests/test_npm_pin.py::test_missing_package_json_names_the_file`, `::test_pinned_npm_versions_rejects_a_package_json_out_of_format`, `::test_node_range_rejects_an_engine_out_of_format`, `::test_pin_source_detail_is_written_in_both_languages`, `::test_pin_source_error_is_a_tool_error`, `tests/test_doctor.py::test_doctor_exits_4_with_one_stderr_line_when_package_json_is_unreadable`, `::test_assess_sends_the_node_slot_to_the_node_row`, `::test_assess_reads_the_declared_distribution`, `::test_assess_binary_matches_the_cli` |
| ADR 0019 | T1 | #183 | `tests/test_doctor.py::test_doctor_runs_only_node_and_gitleaks` |
| Pronto 3 | T1 | #183 | `tests/test_npm_pin.py::test_lock_mismatch_names_the_package_and_both_versions`, `::test_package_lock_matches_package_json` |

- Contagem: 22 testes novos e 6 reescritos, os 28 com o nome exato da ET, presentes em `tests/test_npm_pin.py` e `tests/test_doctor.py` da `main` @ `053dcaab7796f8885c4830ee3a5f6bf1fc75d65a`. O teste removido `test_npm_tools_are_pinned_in_package_json_and_lock` não existe mais.
- Arquivos do PR (9): `CHANGELOG.md`, `src/bob_quality/{doctor,messages,npm_tools}.py`, `tests/{test_action_workflow,test_doctor,test_gate_publications,test_npm_pin,test_ts_cli}.py`.

## Evidência
| Item | Valor | Fonte |
|---|---|---|
| PR | #183, head `30519d10074c8b2354a4e3bd96b5bd7291bafeb1`, base `d2e26bd` | API do GitHub |
| Merge | `13a2792b539a99bc3ee094931a9630c4836cd83a`, 2026-10-18 23:11:17 (UTC-3), por `fazedordecodigo` | API do GitHub |
| Suíte inteira | `python -m pytest -q` → 4118 passed, 0 failed, 0 errors (linha de base na `main` antiga: 18 failed) | corpo do PR #183 |
| Comando escopado | 145 passed, 0 failed | corpo do PR #183 |
| Checks do head (5 verdes) | CI `pytest (3.10)` success 22:55:45; CI `pytest (3.12)` success 23:02:44; `package / dist` success 22:46:15; `bob / check` success 23:02:37; `bob / cold` success 22:46:22 (UTC-3) | check-runs de `30519d1` |
| Check de terceiro | `Graphify Formal Verification` = neutral (não é do repo; não bloqueia) | check-runs de `30519d1` |
| `bob doctor` | sai `0`, `vitest expected 5.0.5 found 5.0.5`, 0,39 s | corpo do PR #183 |
| Pronto 5 (job de empacotamento da `main`) | `package / dist` success em `13a2792` (23:13:00) e em `053dcaab` (23:14:33) (UTC-3) | check-runs da `main` |
| CI `pytest` da `main` depois do merge | em `053dcaab` (HEAD, com o #182): `pytest (3.10)` success 23:24:49 e `pytest (3.12)` success 23:32:12 (UTC-3); às 23:2x estavam em andamento | check-runs da `main`, conferidos 23:45 (UTC-3) |
| Checkpoint | aprovado pelo Emerson, via Maestro, 2026-10-18 23:11 (UTC-3): "Aprovo o checkpoint da U2. Vou fazer o merge do #183. Pode seguir para a U1." | Maestro |
| DoD 3 | N/A (I7) | este arquivo |
