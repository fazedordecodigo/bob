# Checkpoint da U6 (u6-perfil-shell) — B6
Preparado pelo Arquiteto em 23/10/2026 22:15 (UTC-3) e atualizado no fechamento da U6 em 24/10/2026 07:20 (UTC-3) após o merge da T4 (#210 → `3ced2ce30193ac90035d374ec62f38d86bd63f34`). Status da U6: **Concluída** (`T1`–`T4` mergeadas na `main`, checkpoint aprovado pelo Emerson em 23/10 22:16 UTC-3 e U6-N5 100% `Atende` fechada pela T4).
Formato: o mesmo de `construction/u5-hook-pre-push/checkpoint.md` e `construction/u4-bob-yaml/checkpoint.md`.
Fontes: só leituras remotas (cursor-github para PRs, check runs e logs dos jobs; `raw.githubusercontent.com`). Sem clone. Relatórios: `code-generation/tasks/T1-verificacao.md`, `T2-verificacao.md`, `T3-verificacao.md`, `T4-verificacao.md`.

## Confirmação do merge e da `main`
- PR #207: `merged: true`, `merge_commit_sha` `4de84658badec6523a4f1890c748101bd6d2b870`, `merged_at` 2026-10-24T00:50:21Z (**23/10 21:50:21 UTC-3**), `merged_by` fazedordecodigo (Emerson). Head `81ac85f`, base `377b855`.
- PR #204 (T1): merge `040d744d17e306f27414e0804b7e4d3bb54984c9`, 2026-10-23T03:03:02Z (**23/10 00:03:02 UTC-3**), `merged_by` fazedordecodigo.
- PR #205 (T2): merge `3a0b6cd7a385511d3623c574eb3e56a4fe128d43`, 2026-10-23T11:50:30Z (**23/10 08:50:30 UTC-3**), `merged_by` fazedordecodigo.
- Entre a T2 e a T3 entraram na `main` a U7 T1 (#203) e a U7 T2 (#206, `377b855`). A T3 foi feita e verificada sobre `377b855` (variante A).
- PR #210 (T4): `merged: true`, `merge_commit_sha` `3ced2ce30193ac90035d374ec62f38d86bd63f34`, `merged_at` 2026-10-24T10:14:04Z (**24/10 07:14:04 UTC-3**), `merged_by` fazedordecodigo (Emerson). Head `f8c9f523e1cf463755b9b2a8092e5935184dd6c7`, base `4d1603323ddc13714fa50b5e98487cb0957c7f20` (#208 U7 T3 mergeada).

## Veredito: U6 Concluída (checkpoint aprovado pelo Emerson; T1–T4 mergeadas; 11/11 NFRs Atende)
O Comando de Verificação passa na `main` (`4de8465` no fechamento da T3 e `3ced2ce30193ac90035d374ec62f38d86bd63f34` no fechamento da T4): pytest `4804 passed` em 3.10 e 3.12 no head do #210 (`84 passed` em `tests/test_install_sh.py`, com os 5 casos novos fora do `HOME`), e `verify-install / linux-x64` com 14 linhas `ok` (passo 13 em 11 s no #210 e 8 s no push de `4de8465`). O "pronto quando" da U6 atende: os 5 casos (a)–(e) do passo 13 passam, com a marca única depois de 2 execuções, e a instalação escreve 0 arquivos fora do `HOME` (exceto `$ZDOTDIR/.zshrc` quando `ZDOTDIR` aponta para fora do `HOME` com `zsh`, conforme CT16). Os **71 critérios** das 4 ETs (19 da T1 + 16 da T2 + 26 da T3 + 10 da T4) atendem (**71 Atende, 0 Não atende, 0 Não verificado**). Todas as **11 metas de NFR da U6** atendem (**11 Atende, 0 Não atende, 0 Não verificado**), com a **U6-N5** 100% `Atende` fechada pela T4 (#210 → `3ced2ce`). Os 4 PRs (#204, #205, #207 e #210) foram mergeados pelo Emerson. Houve 2 rodadas de correção na U6 (T1 1, T2 0, T3 1, T4 0), as duas por lacuna da ET.

## 1. Comando de Verificação na `main` `4de8465`
Comando (`verification-command.md`, aprovado no 2.9):
`python3 -m venv /tmp/dev && /tmp/dev/bin/pip install -e '.[dev]' && /tmp/dev/bin/pytest && sh scripts/verify-install.sh`

| Parte | Evidência remota | Resultado |
|---|---|---|
| `sh scripts/verify-install.sh` | workflow `verify-install`, push em `4de8465`, run 40046950904 (job 120730760523), `success`, 00:50:28–00:52:09 UTC (1m41s). Log: `Run sh scripts/verify-install.sh` às 00:50:37 UTC e **12 linhas `ok`**: 1, 2 (`tempo 12 s`), 3, 4, 5 (`tempo 5 s`), 6 (`tempo 1 s`), 7 (`tempo 0 s`), 8, 9a, 9b, 12 (`tempo 9 s`) e **13 (`tempo 8 s`)**. Último `ok` às 00:51:49 UTC. Harness em cerca de **72 s** | Atende |
| Passo da U6 (13) | mesmo log: `verify-install: passo 13: tempo 8 s`, `verify-install: passo 13: ok` | Atende |
| Sem regressão nos passos que já existem (1–9b, 12) | mesmo log: todos `ok` | Atende |
| Pacote | workflow `package`, run 40046950874, `dist` `success` (38 s) | Atende |
| `pip install -e '.[dev]'` + `pytest` | workflow `CI`, push em `4de8465`, run 40046950858. `pytest (3.10)`: `success` em 20m12s, `4790 passed, 3 warnings in 1171.44s`. `pytest (3.12)`: `success` em 15m22s, `4790 passed, 3 warnings in 885.28s`. 0 failed, 0 errors. Os 3 warnings são o `verify_requirements` que já existia | Atende |
| Qualidade (`bob / check`, `bob / cold`) | Só rodam em PR. No head do #207: `bob / check` `success` em 11m29s (crap/dry/deps/mutate ✅, "No surviving mutants") e `bob / cold` `success` em 39 s (`T3-verificacao.md`) | Atende |
| Docs (`website / build`) | Nenhum PR da U6 toca `docs/` nem `website/` (D9). O check não rodou | Não se aplica |
| Passos 9c, 10, 11, 14 | 9c, 10 e 11 são da U7 T3 (ainda não mergeada); 14 é da U8. Fora do escopo da B6 (passo 13) | Não se aplica |
| Matriz (Linux arm64, macOS x64/arm64) | O CI só roda Linux x64. A matriz é da U9 | Não verificado (U9) |
| `VERIFY_REMOTE=1` | O passo 13 baixa o release real só depois de uma release com a U6. Fora do escopo | Não verificado (U9) |

### Checks no push da `main` `4de8465` (início 23/10 21:50 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| package / dist | package, 40046950874 | success | 38 s |
| verify-install / linux-x64 | verify-install, 40046950904 | success, 12 `ok`, passo 13 em 8 s, harness em cerca de 72 s | 1m41s |
| CI / pytest (3.10) | CI, 40046950858 | success, `4790 passed, 3 warnings` | 20m12s |
| CI / pytest (3.12) | CI, 40046950858 | success, `4790 passed, 3 warnings` | 15m22s |

## 2. Critérios da B6 (bolt-plan) e "Pronto quando" da U6 → evidência
| Critério | Evidência | Resultado |
|---|---|---|
| B6 / Pronto: os 5 casos (a)–(e) do passo 13 passam | passo 13 `ok` no #207 (CI 6 s; corpo `--only 13`: 8 s) e na `main` (8 s). `profile_case a|b|c|d|e` em `step_13`; cada falha vira `die_passo 13` (lido em `4de8465`) | Atende |
| B6 / Pronto: `grep -c 'managed-by: bob-quality'` = 1 depois de 2 execuções | `profile_case` (a)–(c): `grep -cF "$_mark" "$_pf"` = 1, depois do laço `for _run in 1 2`; passo 13 `ok`. Também `test_second_run_is_already_marked` (T1) | Atende |
| Pronto 1 (Testing Contract): terminal novo acha o `bob` (FR1.1) | passo 13 (a)–(c): `env -i HOME=… PATH=/usr/bin:/bin sh -c '. "$1"; command -v bob'` = `$HOME/.local/bin/bob`; `test_profile_line_sources_in_sh` (T1) | Atende |
| Pronto 3: perfil sem escrita → aviso e saída 0 | passo 13 (e): rc 0, `  bob doctor: 0`, aviso exato 1 vez, `install: perfil: ok`, arquivo igual; `test_unwritable_profile_warns_and_exits_0[en,pt-BR]` (T1) | Atende |
| CT3: linha `shell profile:` no resumo | `test_profile_text_maps_each_value` (16), `test_profile_line_sits_before_the_doctor_line` (2), `test_profile_line_is_absent_without_the_variable` (2), `test_profile_line_is_in_the_partial_summary` (T2); `test_step_13_summary_lines_are_the_ct3_texts` (T3); passo 13 confere as 4 linhas | Atende |
| DoD (bolt-plan) | prontos acima; Comando de Verificação (item 1); passo com `--only 13` no #207; CT2, CT3, CT6, CT15 e CT16 v2 implementados; PRs citam unit, FR, US, CT e ADR, sem segredo (verificações); merges pelo Emerson | Atende |

**B6 atendida.**

## 3. Critério → evidência por ET
Fonte: as tabelas "Critério → evidência" dos 3 relatórios, resumidas sem mudar o resultado.

### T1 — Passo perfil no `install.sh` (ET v2) × PR #204 (head `a465b85`)
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u6-perfil-shell-T1: …`; `aidlc/u6-perfil-shell/t1-install-perfil` → `main`; base `22d461a` | Atende |
| Fora de rascunho; não mergeado pelo agente | `draft: false`, `merged: false` na verificação | Atende |
| Passo 0 igual ao esperado | corpo: `STEPS=…launcher setup`; `DEFAULT_API=…`; `0`; `0`; `EXIT:0`; `64 passed`; `0` | Atende |
| Exatamente 2 arquivos | `scripts/install.sh` +66/−2; `tests/test_install_sh.py` +317/−1; nenhum proibido | Atende |
| R1 `STEPS` e `PROFILE_LINE` | l.4 `STEPS='…launcher perfil setup'` (107 col.); l.5 `PROFILE_LINE`; `grep -c managed-by` → `1` | Atende |
| R2 `step_perfil` | entre `step_launcher` e `step_setup`; R2a–R2g; sempre `step_ok perfil` | Atende |
| R3 `profile_warning` no stdout | pt-BR e en; texto igual ao da ET | Atende |
| R4 `_run_step` | `perfil) step_perfil ;;` entre `launcher` e `setup` | Atende |
| R5 `step_setup` | `export BOB_INSTALL_PROFILE` antes do `exec` | Atende |
| R6 utilitários; sem `sudo` | só `tail` e `chmod` novos em `_ALLOWED`; `grep -nE '\bsudo\b'` sem linha | Atende |
| A1–A6 | ajustes de `_ALLOWED`, `_SOURCE_NAMES`, `_CT2_STEPS`, `profile_warning`, `FAKE_BOB_ENV`, `umask` | Atende |
| 8 testes, 15 casos, nomes exatos | patch; sem `skip`/`xfail`/`only` | Atende |
| `test_install_sh.py`: 79 passed | corpo: `79 passed`, `EXIT:0` | Atende |
| Suíte inteira 0 failed | CI: `4620 passed, 3 warnings` (3.10 e 3.12) | Atende |
| `sh -n` / `dash -n` | corpo: `RC:0` nos dois | Atende |
| Colunas ≤ 100, exceto `STEPS=` | 0 linhas novas > 100 fora de `STEPS=` (107, exceção da v2) | Atende |
| `bob check … crap,dry,deps,mutate,coverage` → 0 | corpo: `EXIT:0`, 5 gates ✅, 0 waivers novos; comentário do `bob` no CI: 4 ✅, "No surviving mutants" | Atende |
| 6 checks verdes; passo 2 com `bob doctor: 0` | 6/6 `success`; `verify-install` com 11 `ok` | Atende |
| Corpo do PR | seções, `## Decisões tomadas: nenhuma`, `## Bloqueios` / Nenhum, refs U6/CT/ADR/FR/NFR/US | Atende |

**T1: 19 Atende, 0 Não atende, 0 Não verificado.**

### T2 — Linha `perfil do shell` no resumo do `bob setup` (ET v1) × PR #205 (head `f3f8106`)
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u6-perfil-shell-T2: …`; `aidlc/u6-perfil-shell/t2-setup-perfil` → `main`; base `040d744` (rebase mecânico pedido pelo Emerson) | Atende |
| Fora de rascunho; não mergeado pelo agente | `isDraft: false`, `mergedAt: null` na verificação | Atende |
| Passo 0 igual ao esperado | corpo: `0`; `0`; linha `-k hook`; `EXIT:0`; `169 passed`; `EXIT:5`; `166 deselected` | Atende |
| Exatamente 4 arquivos | `messages.py`, `setup_cmd.py`, `test_hermetic.py`, `test_setup_cmd.py`; nenhum proibido | Atende |
| R1 `import os` | entre `importlib.metadata` e `platform` | Atende |
| R2 constantes | 6 constantes depois de `_DOCTOR_NOT_RUN`, ordem e valores exatos | Atende |
| R3 `_profile_text` | `-> Text | None`; regras 1–5; sem `strip`/`startswith`/`split`/regex | Atende |
| R4 `_summary` | linha antes de `_DOCTOR_LINE`; assinaturas intactas | Atende |
| R5 mensagens | 5 chaves em en e pt-BR, textos da tabela | Atende |
| R6 hermetic | `-k "hook or profile"`; id do parâmetro igual | Atende |
| 4 testes + 5 tuplas | 21 casos + 10 de `_MESSAGES` | Atende |
| Contagem | corpo: `210 passed`; `197 passed`; `-k "hook or profile"` `65 passed`; net guard 0; suíte `4651 passed` | Atende |
| Colunas ≤ 100 | 0 linhas novas > 100 | Atende |
| `bob check … coverage` → 0 | corpo: `EXIT:0`; `_profile_text` CRAP 6.0, `_summary` 4.0; diff coverage 100%; 0 sobreviventes; 0 waivers novos | Atende |
| 6 checks verdes | 6/6 `success`; `4651 passed, 3 warnings`; `verify-install` 11 `ok` | Atende |
| Corpo do PR | seções, Rebase, `## Decisões tomadas: nenhuma`, `## Bloqueios` / Nenhum, refs | Atende |

**T2: 16 Atende, 0 Não atende, 0 Não verificado.**

### T3 — Harness: passo 13 (ET v2) × PR #207 (head `81ac85f`)
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u6-perfil-shell-T3: …`; `aidlc/u6-perfil-shell/t3-verify-install` → `main`; base `377b855` | Atende |
| Fora de rascunho; não mergeado pelo agente | `draft: false`, `merged: false` na verificação | Atende |
| Passo 0 (variante A) | corpo: `377b855…`; `STEP_IDS='… 9b 12'`; `PROFILE_LINE`; `10`; 4 linhas do resumo; `1000`; `EXIT:0`; `29 passed`; `EXIT:0`; `1` | Atende |
| Exatamente 3 arquivos | `CHANGELOG.md`, `scripts/verify-install.sh`, `tests/test_verify_install.py` | Atende |
| CHANGELOG: texto exato no topo de `## Unreleased` | en e pt-BR, antes da entrada da U5; texto conferido por script | Atende |
| R1 linhas 2 e 4 | `… 9a, 9b, 12 e 13.`; `STEP_IDS='1 2 3 4 5 6 7 8 9a 9b 12 13'` | Atende |
| R2 `run_oneliner` | `${10}` `SHELL`, `${11}` `BOB_HOME` | Atende |
| R3 `profile_line()` | `sed` exato; valor de `PROFILE_LINE` fora do harness; `expected_hook` da U5 intacto | Atende |
| R4a preparo | casos a–e como na ET | Atende |
| R4b linhas exatas | 8 linhas; `_warn` inteira (131 col., exceção da v2) | Atende |
| R4c execuções | 11 argumentos; rc, última linha, `_want`, aviso no caso e | Atende |
| R4d pós-execuções | conteúdo, modo 644, marca única, `env -i … command -v bob`, perfil a mais | Atende |
| R5 `step_13()` | root recusado, `ensure_2`, `release_pair`, 5 casos, `> 180` → die, `tempo`, `ok 13` | Atende |
| R6 `run_selected` | `13) step_13 ;;` depois de `12)` | Atende |
| A1–A3 | `_HELP`, `test_step_ids_are_the_known_steps`, `--only 15` / `9c` | Atende |
| Helpers e 5 testes com nomes exatos | `test_step_13_is_wired`, `test_run_oneliner_passes_shell_and_bob_home` (4), `test_step_13_summary_lines_are_the_ct3_texts`, `test_step_13_warning_is_the_install_sh_text`, `test_profile_line_comes_from_install_sh` | Atende |
| Teste 5 na forma v2 | `stdout == found.group(1) + "\n"` e `found.group(1) not in _text()` | Atende |
| Sem skip/xfail/only/waiver | diff limpo; waivers pré-existentes (11/10) | Atende |
| `test_verify_install.py`: 37 passed | corpo: `37 passed`; CI 3.10 e 3.12 | Atende |
| Colunas (critério v2) | só a `_warn=` (131) > 100, excetuada | Atende |
| `--only 13` sai 0, ≤ 180 s | corpo: `EXIT:0`, `passo 13: tempo 8 s`, `ok`; `--only 15` → `RC:1`; `sh -n`/`dash -n` RC:0 | Atende |
| Harness inteiro no CI, ≤ 900 s, 12 `ok` | run 40044012834: 90 s, 12 `ok`, `passo 13: tempo 6 s` | Atende |
| Suíte inteira 0 failed / 0 errors | CI 3.10 e 3.12: `4790 passed, 3 warnings` | Atende |
| `bob check … coverage` exit 0; dogfood do mutmut | corpo: `EXIT:0`, 5 gates; CI `bob / check`: 4 ✅, "No surviving mutants", "No new clones" | Atende |
| 6 checks verdes | 6/6 `success` | Atende |
| Corpo do PR | seções, `## Decisões tomadas: nenhuma`, `## Bloqueios` / Nenhum, refs | Atende |

**T3: 26 Atende, 0 Não atende, 0 Não verificado.**

### T4 — Teste: a instalação não escreve fora do `HOME` (ET v1) × PR #210 (head `f8c9f52`)
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Passo 0 colado e igual ao esperado | corpo do #210: checkout em `4d1603323ddc13714fa50b5e98487cb0957c7f20`; `STEP_IDS='1 2 3 4 5 6 7 8 9a 9b 10 11 12 13'`; `3`; `PROFILE_LINE`; `1`; `1`; `1`; `0`; `3`; `assert result.stdout == "/h/.local/bin:/usr/bin:/bin"`; `EXIT:0`; `79 passed`; `0` | Atende |
| Exatamente 1 arquivo (`tests/test_install_sh.py`), só acréscimos | `tests/test_install_sh.py` (+122/−0); `git diff -U0 origin/main...HEAD \| grep -c '^-[^-]'` = `0`; nenhum arquivo proibido | Atende |
| `_tree`, `_tree_diff` e `_outside_run` idênticos à ET | `tests/test_install_sh.py:1555-1600`, logo após `test_profile_line_sources_in_sh`, idênticos linha a linha | Atende |
| Os 2 testes novos com nomes e ids exatos (5 casos); `84 passed` | `test_install_writes_nothing_outside_home[bash,sh,zsh]` (3) e `test_zdotdir_outside_home_is_the_only_outside_write[new,existing]` (2); `84 passed` em `tests/test_install_sh.py`; `-k outside`: `5 passed, 79 deselected` | Atende |
| Provas de sensibilidade 1 e 2 + restauração de `scripts/install.sh` | Prova 1 (`: > .bob-mark` em `step_ok projeto`) → `EXIT:1`, `5 failed`; Prova 2 (`: > "$ZDOTDIR/.zcompdump-bob"` em `step_ok perfil`) → `EXIT:1`, `2 failed, 3 passed`; `scripts/install.sh` restaurado (`git status --porcelain scripts/` vazio) | Atende |
| Colunas ≤ 100 nas linhas novas; sem skip/only/xfail/waiver | máx. 78 colunas (`awk 'length > 101'` = `0`); 0 `skip`/`only`/`xfail`; 0 waivers novos | Atende |
| Suíte inteira 0 failed, 0 errors | CI `pytest (3.10)` e `pytest (3.12)`: `4804 passed, 3 warnings`, 0 failed, 0 errors | Atende |
| `bob check … crap,dry,deps,mutate,coverage` → 0; 0 waivers novos | corpo: `EXIT:0`, 5 gates verdes (cobertura do diff Python 100.00%); CI `bob / check` `success`, 4 ✅, "No surviving mutants", "No new clones" | Atende |
| 6 checks verdes no head | `bob / check`, `bob / cold`, `CI / pytest (3.10)`, `CI / pytest (3.12)`, `package / dist`, `verify-install / linux-x64` (14 `ok`) todos `success` | Atende |
| Corpo do PR e PR não mergeado pelo agente | seções completas, `## Decisões tomadas: nenhuma`, `## Bloqueios` vazio, refs `U6, U6-N5, NFR7, CT2, CT16, ADR 0013, US1.1`; merge humano pelo Emerson (`3ced2ce`) | Atende |

**T4: 10 Atende, 0 Não atende, 0 Não verificado** (12/12 linhas na tabela detalhada de `T4-verificacao.md`).

**Total das ETs (T1–T4): 71 Atende, 0 Não atende, 0 Não verificado.**

## 4. Metas de NFR da U6 (`nfr-requirements.md`)
| ID | Alvo | Medido | Evidência | Resultado |
|---|---|---|---|---|
| U6-N1 | `command -v bob` = `$HOME/.local/bin/bob` em 3 de 3 (a)–(c), com `env -i HOME PATH=/usr/bin:/bin` | 3 de 3 | passo 13 `ok` (#207 e `main`): `profile_case` (a)–(c) faz `env -i "HOME=$_h" PATH=/usr/bin:/bin sh -c '. "$1"; command -v bob'` e morre se ≠ `$_h/.local/bin/bob`; `test_profile_line_sources_in_sh` | Atende |
| U6-N2 | `grep -c 'managed-by: bob-quality'` = `1` em (a)–(c) depois de 2 execuções | 1 em 3 de 3 | passo 13 `ok`: `grep -cF "$_mark"` = 1 depois do laço `for _run in 1 2`; `test_second_run_is_already_marked` | Atende |
| U6-N3 | bytes anteriores iguais em 100% (b); arquivo inteiro igual em (d) e (e) | (b) `alias bob-antes=1\n<linha>\n`; (d) nenhum perfil criado; (e) `# só leitura\n` | passo 13 `ok`: `show_file` em (b) e (e); em (d) os 3 perfis não existem; `test_profile_append_keeps_the_bytes[newline,no-newline]`, `test_profile_symlink_is_written_through` | Atende |
| U6-N4 | código `0` (com `bob setup` 0) e 1 aviso com a linha para colar | rc 0; `  bob doctor: 0`; 1 aviso; nas 2 execuções | passo 13 (e) `ok`: `_rc` = 0, `grep -cxF "$_warn"` = 1, `install: perfil: ok` = 1; `test_unwritable_profile_warns_and_exits_0[en,pt-BR]` | Atende |
| U6-N5 | `sudo` no passo `perfil` = 0; arquivos fora do `HOME` = 0 | `sudo`: 0; arquivos fora do `HOME`: 0 (em `bash`, `sh` e `zsh`, e com `ZDOTDIR` fora do `HOME` apenas `$ZDOTDIR/.zshrc` do CT16) | `sudo`: passo 3 `ok` na `main` (`$T/sudo.log` vazio) e `test_install_sh_never_mentions_sudo` verde. Fora do `HOME` (PR #210, T4 → `3ced2ce`): `test_install_writes_nothing_outside_home[bash,sh,zsh]` prova `_tree_diff(before, after) == {}` fora do `HOME`, de `TMPDIR` e de `.agents`/`.git`/`bob.yaml` do projeto; `test_zdotdir_outside_home_is_the_only_outside_write[new,existing]` prova `set(diff) == {("zdot/.zshrc", ...)}` com `ZDOTDIR` fora do `HOME` (CT16); `84 passed` em `tests/test_install_sh.py` e 2 provas de sensibilidade confirmadas (`.bob-mark` → `5 failed`; `.zcompdump-bob` → `2 failed, 3 passed`) | Atende |
| U6-N6 | linha `perfil do shell:` antes de `bob doctor:` nos 4 valores válidos (4 de 4); 0 linhas para valor inválido | 4 de 4; 0 | `test_profile_text_maps_each_value` (16 casos; o NFR cita 14, a ET da T2 fixou 16, sem rebaixar), `test_profile_line_sits_before_the_doctor_line[en,pt-BR]`, `test_profile_line_is_absent_without_the_variable` (2), verdes no CI do #205; passo 13 confere 4 textos | Atende |
| U6-N7 | passo 13 ≤ 180 s (10 execuções com pacote reusado) | 6 s (CI #207); 8 s (`--only 13`, corpo #207); **8 s** (`main`) | log do `verify-install / linux-x64`: `verify-install: passo 13: tempo 8 s` (run 40046950904); o passo morre se `> 180` | Atende |
| U6-N8 | harness ≤ 900 s | 90 s (#207, job 1m30s); cerca de **72 s** (`main`, job 1m41s) | log do `verify-install / linux-x64` (runs 40044012834 e 40046950904) | Atende |
| U6-N9 | `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` exit 0; CRAP < 10; 0 sobreviventes; 0 waivers novos; coverage ≥ 80.0 e 100% das linhas novas | exit 0 nos 3; CRAP máx. 6.0 (`_profile_text`); 0; 0; diff coverage 100% (T2) | corpos dos #204, #205 e #207 (`EXIT:0`, 5 gates); CI `bob / check` (crap,dry,deps,mutate) `success` nos 3, "No surviving mutants". O `coverage` só aparece no corpo (ver L4). T1 e T3 não mudam `src/` | Atende |
| U6-N10 | 0 linhas no log da guarda em `pytest tests/test_setup_cmd.py -k "hook or profile"` | 0 | `test_u5_tests_open_no_network[tests/test_setup_cmd.py]` com `-k "hook or profile"` (R6 da T2) verde no CI do #205 e do #207; corpo do #205: net guard 0, `65 passed` | Atende |
| U6-N11 | `sh -n` e `dash -n` em `install.sh` e `verify-install.sh` com exit 0 | 0; 0 | `test_install_sh_is_posix` e `test_verify_install_is_posix` verdes no CI; corpo do #204 (`install.sh`) e do #207 (`verify-install.sh`): `RC:0` nos dois | Atende |

**Contagem: 11 Atende, 0 Não atende, 0 Não verificado (100% Atende).**

Metas herdadas sem rebaixamento (log da `main` `4de8465`): passo 2 ≤ 300 s (U3-N1): 12 s. Passo 5 ≤ 180 s (U4-N10): 5 s. Passo 6 ≤ 60 s (U5-N11): 1 s. Passo 7 ≤ 60 s: 0 s. Passo 12 ≤ 240 s (U5-N12): 9 s. Harness ≤ 900 s (U5-N13): cerca de 72 s.

## 5. PRs da U6
| PR | Tarefa (ET) | Head | Merge (SHA) | Merge (UTC-3) | Checks no head | pytest | Rodadas de correção |
|---|---|---|---|---|---|---|---|
| [#204](https://github.com/fazedordecodigo/bob/pull/204) | T1 (v2) | `a465b85` | `040d744d17e306f27414e0804b7e4d3bb54984c9` | 23/10 00:03:02 | 6/6 verdes (verify-install em 4m03s, 11 `ok`) | 4620 passed | 1 |
| [#205](https://github.com/fazedordecodigo/bob/pull/205) | T2 (v1) | `f3f8106` | `3a0b6cd7a385511d3623c574eb3e56a4fe128d43` | 23/10 08:50:30 | 6/6 verdes (verify-install em 4m17s, 11 `ok`) | 4651 passed | 0 (só rebase mecânico sobre `040d744`) |
| [#207](https://github.com/fazedordecodigo/bob/pull/207) | T3 (v2) | `81ac85f` | `4de84658badec6523a4f1890c748101bd6d2b870` | 23/10 21:50:21 | 6/6 verdes (verify-install em 1m30s, 12 `ok`) | 4790 passed | 1 |
| [#210](https://github.com/fazedordecodigo/bob/pull/210) | T4 (v1) | `f8c9f52` | `3ced2ce30193ac90035d374ec62f38d86bd63f34` | 24/10 07:14:04 | 6/6 verdes (verify-install em 2m47s, 14 `ok`) | 4804 passed | 0 |

Os 4 foram mergeados por `fazedordecodigo` (Emerson), conferido por `GET pulls/<n>`.
Contagem do pytest: 4605 → 4620 (+15, T1) → 4651 (+31, T2) → 4782 (U7 T1 e T2) → 4790 (+8, T3) → 4799 (U7 T3) → 4804 (+5, T4).

## 6. Lacunas de ET e rodadas de correção
| Tarefa | Rodadas | Lacuna | Correção | Versão da ET |
|---|---|---|---|---|
| T1 | **1** | O cheque de colunas da v1 (`awk 'length > 101'` = 0) reprovava a linha `STEPS=`. Na base `22d461a` ela já tinha 100 colunas; ` perfil` soma 7 → 107. Ela é a fonte única do CT2 e não pode ser partida | A v2 exclui `+STEPS=` do cheque e da regra de colunas. R1 intacto. O código de produção não mudou na rodada | v1 → **v2** (22/10, `T1-v1.md` guarda a v1) |
| T2 | **0** | Nenhuma. Só rebase mecânico sobre `040d744`, pedido pelo Emerson | — | v1 |
| T3 | **1** | (1) R3 e o teste 5 da v1 proibiam o texto `managed-by` em `verify-install.sh`, mas ele já existe em `expected_hook` da U5. (2) A linha `_warn` de R4b tem 131 colunas, e o teste 4 a confere inteira por `splitlines()`. As duas coisas quebravam a suíte e, com ela, o dogfood do mutmut e os gates `crap`/`coverage` do `bob check` | A v2 troca a proibição por "o valor de `PROFILE_LINE` não aparece no harness" (teste 5: `found.group(1) not in _text()`) e excetua a linha `_warn=` do cheque de colunas. Nenhuma decisão aprovada mudou | v1 → **v2** (23/10 21:15 UTC-3, `T3.v1.md` guarda a v1) |
| T4 | **0** | Nenhuma. Aprovada na 1ª passada contra a ET v1 | — | v1 |

**Rodadas de correção da U6: T1 1, T2 0, T3 1, T4 0 (total 2).** As duas foram lacunas da ET, não erro do agente.
Também na T3, sem contar como rodada: o agente caiu uma vez por erro da plataforma, antes do PR, e foi retomado com a mesma ET.

## 7. Pendências e riscos
| # | Item | Estado (23/10, UTC-3) | Dono |
|---|---|---|---|
| L1 | Passo 13 com `VERIFY_REMOTE=1` (release real) só passa depois de uma release com a U6. Fora do escopo da U6 | Não verificado (U9) | — |
| L2 | U6-N5, parte "arquivos fora do `HOME` = 0": fechada pela ET U6 T4 (PR [#210](https://github.com/fazedordecodigo/bob/pull/210) → `3ced2ce30193ac90035d374ec62f38d86bd63f34`), com snapshot fora do `HOME` em `tests/test_install_sh.py` (`test_install_writes_nothing_outside_home[bash,sh,zsh]` e `test_zdotdir_outside_home_is_the_only_outside_write[new,existing]`, `84 passed`) e 2 provas de sensibilidade | Fechada (T4, #210) | — |
| L3 | Matriz macOS e arm64: U6-N1, N7 e N8 só medidos em Linux x64. O caso (a) usa `SHELL=/bin/zsh` só como valor (o `install.sh` lê o nome, não executa o zsh) | Não verificado (U9) | — |
| L4 | O `bob / check` do CI roda `crap,dry,deps,mutate`. A evidência do gate `coverage` dos 3 PRs só está nos corpos (exit 0; diff 100% na T2) | Registrada (vale desde a U3) | — |
| L5 | A U7 T3 rebaseou sobre `4de8465` (variante B) e foi mergeada no PR [#208](https://github.com/fazedordecodigo/bob/pull/208) (`4d16033`), com `STEP_IDS` `1..13`, `46 passed` em `test_verify_install.py` e o passo 13 verde no CI | Fechada (#208) | — |
| L6 | Root no caso (e): o passo 13 recusa root (`die_passo 13`). Um runner que rode como root falha o passo de propósito | Registrada (R1 do plano) | — |
| L7 | `pytest` no push da `main` `4de8465`: estava em andamento quando comecei. Fechou às 22:10 (UTC-3) com `4790 passed` em 3.10 e 3.12 | Fechada | — |
| L8 | O NFR U6-N6 cita `test_profile_text_maps_each_value` com 14 casos; a ET da T2 e o plano fixaram 16. Mais casos, sem rebaixar a meta. Divergência só de texto no `nfr-requirements.md` (artefato do Analista; não editado) | Registrada | Analista |
| L9 | No `traceability.json`, os PRs 204 e 205 continuam com `state: open` na lista `prs` da U6 (as tarefas T1 e T2 já estão `merged`). Não mexi, porque o pedido era só a T3 e o PR 207 | Registrada | Maestro decide | (corrigido 23/10 22:15: PRs 204 e 205 marcados merged.)
| L10 | Annotation `notice` do `ubuntu-latest` → Ubuntu 26 (L8 da U5). Pode mudar `dash` e `zsh` do runner | Registrada; monitorar | Maestro |
| L11 | Lições para as ETs seguintes (U7 T3 e U8): (a) antes de proibir um literal no arquivo, conferir se ele já existe na base; (b) linha conferida inteira por `splitlines()` precisa de exceção de colunas na própria ET; (c) linha de fonte única perto do limite de colunas entra na exceção desde a v1 | Para a 3.6 e as ETs da U8 | Arquiteto |

## 8. Rastreabilidade US/FR → tarefa → PR → testes (`traceability.json`)
A U6 contribui: US1.1 (crit. 2) e US6.1 (crit. 1); FR1.1 e FR7.1; NFR2, NFR4, NFR5, NFR7 e NFR9. As 3 tarefas citam as mesmas US, FR e NFR. No mapa `stories`/`frs` do JSON, US1.1, US6.1, FR1.1 e FR7.1 apontam para a U1 (dona); a U6 só contribui.

| US / FR | Tarefa | Contratos | PR | Merge | Testes |
|---|---|---|---|---|---|
| US1.1, US6.1 / FR1.1, FR7.1 | T1 — Passo perfil no `install.sh` | CT2, CT6, CT16 | #204 | `040d744` | `tests/test_install_sh.py`: `test_profile_file_follows_the_shell`, `test_zdotdir_holds_the_zshrc`, `test_profile_append_keeps_the_bytes`, `test_second_run_is_already_marked`, `test_local_bin_on_path_writes_nothing`, `test_unwritable_profile_warns_and_exits_0`, `test_profile_symlink_is_written_through`, `test_profile_line_sources_in_sh` |
| US1.1, US6.1 / FR1.1, FR7.1 | T2 — Linha `perfil do shell` no resumo | CT3, CT6 | #205 | `3a0b6cd` | `tests/test_setup_cmd.py`: `test_profile_text_maps_each_value`, `test_profile_line_sits_before_the_doctor_line`, `test_profile_line_is_absent_without_the_variable`, `test_profile_line_is_in_the_partial_summary` (+ guarda `tests/test_hermetic.py` com `-k "hook or profile"`) |
| US1.1, US6.1 / FR1.1, FR7.1 | T3 — Harness: passo 13 | CT15, CT16 | #207 | `4de8465` | `tests/test_verify_install.py`: `test_step_13_is_wired`, `test_run_oneliner_passes_shell_and_bob_home`, `test_step_13_summary_lines_are_the_ct3_texts`, `test_step_13_warning_is_the_install_sh_text`, `test_profile_line_comes_from_install_sh`; harness passo 13 |
| US1.1 / FR1.1 (NFR7, U6-N5) | T4 — Teste: a instalação não escreve fora do `HOME` | CT2, CT16 | #210 | `3ced2ce` | `tests/test_install_sh.py`: `test_install_writes_nothing_outside_home[bash,sh,zsh]`, `test_zdotdir_outside_home_is_the_only_outside_write[new,existing]` |

ADRs: 0013, 0021, 0022, 0023, 0026, 0027. Passo de verificação: 13.

## Registro
- 23/10/2026 21:50 (UTC-3): o Emerson mergeou o #207 (`4de8465`).
- 23/10/2026 22:10 (UTC-3): fechou o último check do push (`CI / pytest (3.10)`), e os 4 ficaram verdes.
- 23/10/2026 22:15 (UTC-3): checkpoint preparado. `traceability.json`: só a U6 T3 (`merged`, `merge_sha`, `merged_at`) e o PR 207 (`merged`). Status da unit sem mudança (`plan_approved`).
- 23/10/2026 22:16 (UTC-3): Emerson aprovou o checkpoint da U6 e pediu para fechar a U6-N5 com a ET U6 T4 depois da U7 T3.
- 23/10/2026 22:57 (UTC-3): Emerson aprovou o plano e a ET da U6 T4.
- 24/10/2026 00:13 (UTC-3): U6 T4 despachada sobre `4d1603323ddc13714fa50b5e98487cb0957c7f20` (`bc-d688f05c-76b1-51a3-9fb0-4daf1348f34c`).
- 24/10/2026 01:48 (UTC-3): PR #210 (`f8c9f52`) verificado contra a ET v1 e aprovado na 1ª passada (`T4-verificacao.md`).
- 24/10/2026 07:14:04 (UTC-3): Emerson mergeou o PR #210 (`3ced2ce30193ac90035d374ec62f38d86bd63f34`). U6-N5 marcada como 100% `Atende` (11/11 NFRs da U6 `Atende`, 71/71 critérios das ETs `Atende`) e U6 fechada como **Concluída** (`completed` no `traceability.json`).
