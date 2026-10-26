# U5 — Rastreabilidade (u5-hook-pre-push)

Escopo: só esta unit. Estado: **aguardando o checkpoint do Emerson**: Plan Approval do Emerson em 22/10 10:14 (UTC-3); T1 (#200), T2 (#201) e T3 (#202) mergeadas; `main` @ `22d461a` com o Comando de Verificação verde; checkpoint preparado em 22/10 20:45 (UTC-3) em [`checkpoint.md`](checkpoint.md). Status da unit no `traceability.json` sem mudança (`plan_approved`) até a aprovação. Contexto do plano: Base `main` @ `b142631935df7cad40f241501969dfea03595057` (#199, U4 fechada; checkpoint da U4 aprovado pelo Emerson em 22/10 08:55 UTC-3, U5 liberada). Plano escrito em 22/10/2026 09:1x–10:xx UTC-3, com leitura remota do repo (sem clone). (Na escrita do plano, nada estava despachado.) Perguntas: nenhuma.

## FR/US → tarefa → prova
| FR / US | Tarefa | Prova (teste ou passo do harness) |
|---|---|---|
| FR5.1 (hook ativo roda `bob check --gates crap,dry,deps`) | T1, T2, T3 | `test_render_hook_is_the_ct10_text[3]`, `test_hook_marker_is_line_2_of_the_template`, `test_static_hook_runs_the_same_command`, `test_install_creates_the_hook`, `test_install_creates_the_hooks_folder_when_missing`, `test_install_uses_the_common_hooks_of_a_worktree`; `test_hook_step_reports_created`, `test_hook_step_reaches_the_summary`, `test_hook_step_passes_ctx_home_bin_bob`; `tests/test_hook.py` (7); passo 6 (`cmp` com `expected_hook` + push) |
| FR5.2 (push comum, sem ativar ambiente) | T1, T2, T3 | caminho absoluto do launcher no template (`test_render_hook_is_the_ct10_text`, `test_managed_hook_calls_the_bob_next_to_python`); e2e da T2 (push com `env -i HOME PATH=/usr/bin:/bin`); passo 0 da T3; passo 6 (`test_step_6_pushes_with_a_clean_env`) |
| FR5.3 (hook existente não alterado; dev avisado) | T1, T2, T3 | `test_install_preserves_a_foreign_hook[5]`, `test_install_never_follows_a_link_or_a_folder[2]`, `test_install_respects_core_hooks_path[2]`, `test_bad_path_writes_nothing_and_calls_no_git`; `test_hook_step_preserves_a_foreign_hook[3]`, `test_hook_step_respects_core_hooks_path`, `test_hook_step_foreign_warning_reaches_the_output[en,pt-BR]`; passo 8 (sha + linha `preserved:` + aviso) |
| US4.1 crit. 1 (push dispara o hook, bloqueia/libera) | T1, T3 | `tests/test_hook.py` (6 existentes com o hook gerado: bloqueia CRAP > 10 e dependência nova; libera dependência antiga); passo 6; passo 12 |
| US4.1 crit. 2 (< 60 s no repo-fixture) | T1, T3 | `test_pre_push_hook_runs_crap_gate_under_60s`, `test_pre_push_hook_blocks_when_changed_function_exceeds_crap_10` (CI 3.10/3.12); passo 12; tempo do push no passo 6 (U5-N11) |
| US3.2 (hook do dev preservado e listado) | T2, T3 | os de FR5.3 |
| NFR4 (2ª execução sem mudança) | T1, T2, T3 | `test_install_is_unchanged_on_the_second_run`, `test_hook_step_second_run_is_unchanged`, `test_hook_step_reaches_the_summary` (2ª execução); passo 7 (`digest` + mtime do hook) |
| NFR5 (0 bytes alterados no hook existente) | T1, T2, T3 | os de FR5.3 |
| NFR8 (< 60 s) | T1, T3 | os de US4.1 crit. 2 |
| NFR9 (erro claro, en/pt-BR) | T1, T2 | `test_git_command_failed_message_in_both_languages[2]`, `test_git_errors_are_tool_errors[3]`, `test_setup_messages_exist_in_both_languages` (+16), `test_hook_step_bad_bob_path_fails`, `test_hook_step_git_failure_fails`, `test_hook_step_write_error_fails[2]`, `test_hook_step_failure_stops_setup[en,pt-BR]` |
| CT10 | T1 | `tests/test_hook_install.py` (18 testes, 37 casos) |
| CT3 (ordem 7) | T2 | `test_steps_follow_the_ct3_order` (ajustado) |
| CT5 (marca na linha 2 exata) | T1 | `test_hook_marker_is_line_2_of_the_template`, `test_install_preserves_a_foreign_hook` (marca na linha 1, na 3, CRLF, espaço) |
| CT15 (passos 6 e 12; 7 e 8) | T3 | `test_step_ids_are_the_u1_u3_u4_and_u5_steps`, `test_step_6_is_wired`, `test_step_12_runs_the_hook_tests`, `test_step_7_checks_the_hook_mtime`, `test_step_8_checks_the_foreign_hook`, `test_pytest_pin_matches_pyproject`; harness inteiro |
| ADR 0016 | T1, T2 | os de FR5.1 e FR5.3 |
| ADR 0017 (temp + rename; nunca escreve o do dev) | T1 | `test_write_error_leaves_no_temporary[3]`, `test_temporary_is_next_to_the_hook`, `test_install_updates_a_bob_hook_that_differs[2]`, os de FR5.3 |
| Hermeticidade (U5-N16; lacuna U4-N14) | T1, T2 | `test_net_guard_catches_a_connection`, `test_u5_tests_open_no_network[2]` |

## Regras H1–H13 → tarefa → prova
| Regra | Tarefa | Prova |
|---|---|---|
| H1 template | T1 | testes 1, 3, 4 da T1; teste 2 da T3 |
| H2 caminho citável | T1, T2 | teste 2 e 15 da T1; teste 7 da T2 |
| H3 `core.hooksPath` | T1, T2 | teste 11 da T1; teste 5 da T2 |
| H4 `rev-parse --git-path hooks` | T1 | testes 6, 12, 13, 14 da T1 |
| H5 link/não-arquivo | T1, T2 | teste 10 da T1; teste 4 da T2 |
| H6 marca na linha 2 | T1 | teste 9 da T1 |
| H7 igual → unchanged; difere → updated | T1, T2 | testes 7, 8 da T1; testes 2, 3 da T2 |
| H8 cria (com pasta) | T1 | testes 5, 6 da T1 |
| H9 temp + rename | T1 | testes 16, 17 da T1 |
| H10 erros do git | T1, T2 | testes 13, 14, 18 da T1; teste 8 da T2 |
| H11 passo `hook` | T2 | testes 1–13 da T2 |
| H12 sem pergunta; repetível | T2, T3 | teste 2 e 11 da T2; passo 7 |
| H13 estático igual | T1 | teste 4 da T1; comando de sha256 da T1 |

## Pronto da U5 → ET → prova
| Pronto (unit-of-work.md) | ET | Prova |
|---|---|---|
| 1. `git push` para remoto bare com `env -i HOME=$HOME PATH=/usr/bin:/bin` dispara o hook e roda `bob check --gates crap,dry,deps` | T1, T2, T3 | passo 6; e2e da T2; passo 0 da T3 |
| 2. `tests/test_hook.py` passa em < 60 s | T1, T3 | CI `pytest (3.10)`/`(3.12)`; passo 12 |
| 3. Hook alheio: mesmo hash, aviso no resumo. `core.hooksPath`: nada gravado, aviso com a linha | T1, T2, T3 | passo 8; testes de FR5.3; e2e da T2 |
| DoD do Bolt B5: PR cita unit, FR, US e CT; 6 checks; merge pelo Emerson | T1, T2, T3 | critérios de aceite de cada ET; checkpoint da U5 |

## Comando de Verificação → prova
| Passo | Prova |
|---|---|
| 6 | harness passo 6 (T3). CI do PR #202 (`verify-install / linux-x64`, head `03e39e5`): `verify-install: passo 6: tempo 1 s`, `verify-install: passo 6: ok`. `main` `22d461a` (run 39866937636): `passo 6: tempo 1 s`, `ok` |
| 7 | harness passo 7 (T3: + mtime do hook; `digest` já cobre `.git/hooks`). CI do PR #202: `passo 7: tempo 1 s`, `passo 7: ok`. `main` `22d461a`: `passo 7: tempo 0 s`, `ok` |
| 8 (parcial: hook) | harness passo 8 (T3: hook alheio com sha, linha `preserved:` e aviso). CI do PR #202: `passo 8: ok`. `main` `22d461a`: `passo 8: ok` |
| 12 | harness passo 12 (T3); CI `pytest` (T1). CI do PR #202: `passo 12: tempo 14 s`, `passo 12: ok`. `main` `22d461a`: `passo 12: tempo 9 s`, `ok`; CI `pytest` 3.10 e 3.12 `4605 passed` |

## Tarefas e PRs
| Tarefa | ET | Branch | PR | Estado |
|---|---|---|---|---|
| T1 | `code-generation/tasks/T1.md` (v2; v1 em `T1-v1.md`) | `aidlc/u5-hook-pre-push/t1-hook-install` | [#200](https://github.com/fazedordecodigo/bob/pull/200) | verificada em 22/10 13:30 (UTC-3) no head `7b97bc0`: aprovada, 6/6 checks verdes, `4562 passed`; mergeada em 22/10 13:48 (UTC-3), `main` @ `7f9ad59` ([verificação](code-generation/tasks/T1-verificacao.md)) |
| T2 | `code-generation/tasks/T2.md` (v1, base `7f9ad59`) | `aidlc/u5-hook-pre-push/t2-setup-step` | [#201](https://github.com/fazedordecodigo/bob/pull/201) | verificada em 22/10 15:58 (UTC-3) no head `fbd14d0`: aprovada, 6/6 checks verdes, `4597 passed`; mergeada em 22/10 16:32 (UTC-3), `main` @ `144b997` ([verificação](code-generation/tasks/T2-verificacao.md)) |
| T3 | `code-generation/tasks/T3.md` (v1, base `144b997`) | `aidlc/u5-hook-pre-push/t3-verify-install` | [#202](https://github.com/fazedordecodigo/bob/pull/202) | verificada em 22/10 19:03 (UTC-3) no head `03e39e5`: aprovada, 6/6 checks verdes, `4605 passed`, harness com 11 linhas `ok`; mergeada em 22/10 19:42 (UTC-3), `main` @ `22d461a` ([verificação](code-generation/tasks/T3-verificacao.md)) |

## Inconsistências entre docs e código (registradas, sem mudar artefatos do Analista)
| # | Achado | Tratamento |
|---|---|---|
| I35 | O passo 6 do Comando de Verificação diz "a saída tem o relatório do `bob check`", mas o `bob check` não imprime relatório no stdout: grava `.bob/report.md` e `.bob/report.json` | O passo 6 confere `.bob/report.md` (1ª linha `# bob report` e as linhas de `crap`, `dry` e `deps`) e o código `0` do push (D12) |
| I36 | O CT10 traz os avisos só em pt e com o prefixo `hook: aviso:`; o CT1 manda todo texto para o catálogo en/pt-BR, e o `bob setup` já monta o prefixo com `setup.warning_line` | Chaves `setup.warn_hook_foreign` e `setup.warn_hookspath` com o texto pt do CT10 sem o prefixo, mais o en (D9) |
| I37 | O CT10 define `HookResult(state, path)`; o aviso de `core.hooksPath` precisa do valor cru | Campo novo `hooks_path: str = ""`, compatível (D1); nota no Registro do CT10 |
| I38 | O CT10 não diz o que fazer com link, pasta, caminho com `"`/`$`/`` ` ``/`\`/quebra de linha, nem com hook do bob igual em bytes mas com outro modo | Link e não-arquivo → preservados sem leitura; caminho não citável → `HookPathError` (saída 4, nada gravado); só modo diferente → `updated` (D3, D5, D6) |
| I39 | O passo 12 roda `pytest tests/test_hook.py`, mas o workflow `verify-install` não instala `.[dev]` e o CT15 diz que o harness não tem dependência de dev | O passo 12 instala só o pin `pytest==<versão>` do `pyproject.toml` no venv de teste do bob (`$T`, descartável); o harness em si continua sem pytest (D12) |
| I40 | `README.md:319-326` e `docs/guides/pre-push.md` mandam copiar o hook estático; o CT10 diz que o estático fica | Estático intacto; teste de paridade de comando (`test_static_hook_runs_the_same_command`); a cópia manual é preservada com aviso. Atualizar os docs é da U8 |
| I41 | `tests/test_verify_install.py` usa `--only 6` como exemplo de passo desconhecido (I29 da U4) | Ajuste em lista fechada na T3 (`--only 10`) |
| I42 | Na U4 (I26), o item preservado só aparece na linha `preservado:`; o FR5.3 pede aviso ao dev | Hook preservado gera a linha `preservado:` e o aviso com a linha a acrescentar (D9) |
| I43 | Não verificado: no push do passo 6 com `PATH=/usr/bin:/bin`, o `bob check` sai `0`. Pela leitura, sem Node o `dry` fica ⏭️ e soma `0` (`dry_gate.py:73-75`); `crap` e `deps` rodam pelo venv do bob | Passo 0 da T3 mede antes de mexer no script; se sair ≠ 0, para e reporta (R1 do plano) |
| I44 | `VERIFY_REMOTE=1` usa a release publicada, que ainda não tem o passo `hook` | Os passos 6 e 12 só passam no modo remoto depois de uma release com a U5 (fora de escopo da T3) |
- 2026-10-22 10:17 UTC-3: o Emerson deu o Plan Approval às 10:14 ("Aprovo o plano da U5 e as ETs T1 a T3. Pode despachar a T1 sobre a main b142631."), com aviso do Maestro. Despachei a T1 v1 sobre `b142631` para o agente `bc-120d0358-fc94-5c1c-b52a-f77b9bbb79b7`, com os anexos em `/workspace/dispatch/u5-t1/`.
- 2026-10-22 13:30 UTC-3: verifiquei o PR #200 (T1, head `7b97bc0`, base `b142631`) contra a ET v2: aprovado para checkpoint, sem desvios. 7 arquivos, R1–R11 (com `partition` nas duas linhas do R4), 23 testes com nome exato (39/1/2 casos), `sha256` do hook estático igual, CHANGELOG igual ao da ET, linhas ≤ 100 colunas, `bob check` exit 0 com 0 sobreviventes e 0 waivers novos, `4562 passed` no CI (3.10 e 3.12), 6/6 checks verdes. Relatório em `code-generation/tasks/T1-verificacao.md`; `traceability.json` (U5 T1 `verified`, PR 200 `open`) atualizado. O merge é do Emerson.
- 2026-10-22 15:58 UTC-3: verifiquei o PR #201 (T2, head `fbd14d0`, base `7f9ad59`) contra a ET v1: aprovado para checkpoint, sem desvios. 5 arquivos, R1–R8, 8 textos de R7 byte a byte (en e pt-BR) sem chave existente alterada, 13 testes com nome exato (18 casos + 16 de `_MESSAGES` + 1 no hermetic), só os ajustes da lista fechada, linhas ≤ 100 colunas, CHANGELOG igual ao da ET acima da entrada da T1, `bob check` exit 0 com 0 sobreviventes e 0 waivers novos, passo 0 (`41 passed`) e e2e conforme (`SETUP:0` ×3, `BASE:0`, `PUSH:0`, SHAs iguais; `dry` ⏭️ no push sem Node, como no I43), `4597 passed` no CI (3.10 e 3.12), 6/6 checks verdes. Imprecisões da ET anotadas no relatório (`sed -n 1,6p` não mostra os gates; `SETUP:$?` da reexecução é o do `grep`; import da l.21 com 110 colunas). Relatório em `code-generation/tasks/T2-verificacao.md`; `traceability.json` (U5 T2 `verified`, PR 201 `open`) atualizado. Linha da T1 na tabela atualizada para mergeada (`7f9ad59`), conforme o `traceability.json`. O merge é do Emerson.
- 2026-10-22 19:03 UTC-3: verifiquei o PR #202 (T3, head `03e39e5`, base `144b997`) contra a ET v1, depois de esperar os checks (o último fechou às 18:55): aprovado para checkpoint, sem desvios. 3 arquivos, script `100755`, R1–R9 (as 3 linhas `_warn` do R6 exatas e, rodadas em `sh`, iguais à mensagem da T2), `STEP_IDS='1 2 3 4 5 6 7 8 9a 9b 12'`, `expected_hook` (bytes = template do CT10), `step_6`, `pytest_pin` (`pytest==9.1.1`) e `step_12`, 7 testes com nome exato (8 casos), só os ajustes da lista fechada, CHANGELOG igual ao da ET acima da entrada da T2, passo 0 conforme, `bob check` exit 0 sem sobrevivente nem waiver novo, `4605 passed` no CI (3.10 e 3.12), 6/6 checks verdes; `verify-install / linux-x64` com 11 linhas `ok` (passo 6 em 1 s, passo 12 em 14 s). Observação de forma: Decisões como `## Decisões tomadas` + "nenhuma". Relatório em `code-generation/tasks/T3-verificacao.md`; `traceability.json` (U5 T3 `verified`, PR 202 `open`) atualizado; status da unit sem mudança. Linhas da T2 (mergeada em `144b997`) e do estado no topo atualizadas conforme o `traceability.json`. O merge é do Emerson.
- 2026-10-22 20:45 UTC-3: o Emerson mergeou o #202 às 19:42 (`main` @ `22d461a60920ab13e7b09fd654fd0e4686ba14d0`, mesma árvore `c8e7dff` do head `03e39e5`). Esperei os checks do push (o último fechou às 20:02): 4/4 verdes, `4605 passed` em 3.10 e 3.12, `verify-install / linux-x64` com 11 linhas `ok` (passo 6 em 1 s, passo 12 em 9 s, harness em cerca de 146 s); o `pages` não rodou. Checkpoint em [`checkpoint.md`](checkpoint.md): B5 atendida, U5-N1..N16 atendem (16/0/0), U4-N14 segue Não verificado (a guarda não roda os testes da U4; proposta para a 3.6). `traceability.json`: T3 `merged`, PRs 200, 201 e 202 com merge, bloco `checkpoint` com aprovação pendente; status da unit sem mudança. A aprovação é do Emerson.
