# Checkpoint da U4 (u4-bob-yaml) — B4
Preparado pelo Arquiteto em 22/10/2026 08:52 (UTC-3) para o checkpoint do Emerson. Base: `main` @ `b142631935df7cad40f241501969dfea03595057` (squash do #199, T1c, pai `bb08a2c`).
Formato: não há `checkpoint*.md` nas units anteriores; o checkpoint da U3 é o parágrafo "Checkpoint da U3" no `construction/u3-gitleaks/trace.md`. Este arquivo segue as tabelas do `trace.md` e das `T*-verificacao.md`.
Fontes: só leituras remotas (API pública do GitHub por curl, `raw.githubusercontent.com` e cursor-github para check runs, workflow runs e logs dos jobs). Sem clone.

## Confirmação do merge e da `main`
- PR #199: `state: closed`, `merged: true`, `merge_commit_sha` `b142631935df7cad40f241501969dfea03595057`, `merged_at` 2026-10-22T11:26:20Z (**08:26:20 UTC-3**), `merged_by` fazedordecodigo (Emerson). Head `3a49309`.
- `GET commits/main` → `b142631935df7cad40f241501969dfea03595057`, pai único `bb08a2c`, mensagem "ET-u4-bob-yaml-T1c: Documentar o not_run "no code to measure" com exit 0".
- Árvore: `git/commits/3a49309…` e `git/commits/b142631…` têm a mesma `tree` `86645a240ee8ef5fdde5fe1e77dc3e2ba5c506bb`. O conteúdo da `main` é exatamente o do head do #199; os checks que só rodam em PR (`bob / check`, `bob / cold`, `website / build`) valem para a `main`.

## Veredito: pronto para o checkpoint do Emerson
O Comando de Verificação passa na `main` `b142631` (pytest `4520 passed` em 3.10 e 3.12; `verify-install / linux-x64` com 9 `ok`, passo 5 em 6 s, harness em 173 s). Todos os critérios da B4 e os 4 prontos da U4 atendem. Das 14 metas de NFR, 13 atendem e a U4-N14 fica Não verificado (sem medição remota de rede). Os 5 PRs estão mergeados pelo Emerson. As lacunas L1–L3, documentais e minhas, já foram corrigidas. L4 e L5 são de antes da U4 e ficam fora do escopo. Nenhuma bloqueia o checkpoint.

## 1. Comando de Verificação aprovado na `main` `b142631`
Comando (`verification-command.md`, aprovado no 2.9):
`python3 -m venv /tmp/dev && /tmp/dev/bin/pip install -e '.[dev]' && /tmp/dev/bin/pytest && sh scripts/verify-install.sh`

| Parte | Evidência remota | Resultado |
|---|---|---|
| `pip install -e '.[dev]'` + `pytest` | workflow `CI` (`.github/workflows/ci.yml`: `python -m pip install -e ".[dev]"` e `python -m pytest`), push em `b142631`, run 39770582897: jobs `pytest (3.10)` `success` em 15m29s, `4520 passed, 3 warnings in 849.68s`; `pytest (3.12)` `success` em 20m53s, `4520 passed, 3 warnings`; 0 failed, 0 errors | Atende |
| `sh scripts/verify-install.sh` | workflow `verify-install`, push em `b142631`, run 39770582943 (job 119796797457), `success` em 3m20s; log: `Run sh scripts/verify-install.sh` e 9 linhas `ok`: 1, 2 (`tempo 54 s`), 3, 4, 5 (`tempo 6 s`), 7 (`tempo 0 s`), 8, 9a, 9b; de 11:26:35 a 11:29:27 UTC = **173 s** | Atende |
| Passos da U4 (5, 7, 8 parcial) | mesmo log: `verify-install: passo 5: tempo 6 s`, `passo 5: ok`, `passo 7: ok`, `passo 8: ok` | Atende |
| Sem regressão nos passos que já existem (1, 2, 3, 4, 9a, 9b) | mesmo log: todos `ok` | Atende |
| Pacote | workflow `package`, run 39770583274, `dist` `success` (1m25s) | Atende |
| Qualidade (`bob / check`, `bob / cold`) | só em PR; head do #199 (`3a49309`, mesma árvore): `bob / check` `success` 11m58s (comentário do `bob`: `crap,dry,deps,mutate` 4 ✅, 0 sobreviventes, 0 sem teste), `bob / cold` `success` 1m17s | Atende |
| Docs (`website / build`) | só em PR; head do #199: `success` 2m25s (build en e pt-BR `[SUCCESS]`, `npm test` 14/14). O push em `b142631` também rodou o workflow `pages`: job `build` `success` (2m20s) | Atende |
| Passos 6, 9c, 10–14 | ainda não existem no harness (U5, U7, U6, U8, U9). Fora do escopo da U4 pelo bolt-plan (B4: passos 5, 7, 8 parcial) | Não se aplica |
| Matriz (Linux arm64, macOS x64/arm64) | só Linux x64 no CI; matriz na U9 | Não verificado (U9) |
| `VERIFY_REMOTE=1` | só depois de uma release com a U4 (I32) | Não verificado (U9) |

### Checks no push da `main` `b142631` (início 22/10 08:26 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| package / dist | package, 39770583274 | success | 1m25s |
| verify-install / linux-x64 | verify-install, 39770582943 | success, 9 `ok`, passo 5 em 6 s, harness em 173 s | 3m20s |
| CI / pytest (3.10) | CI, 39770582897 | success, `4520 passed, 3 warnings` | 15m29s |
| CI / pytest (3.12) | CI, 39770582897 | success, `4520 passed, 3 warnings` | 20m53s |
| pages / build | pages, 39770583009 | success | 2m20s |
| pages / deploy | pages, 39770583009 | **failure** (não exigido; ver lacuna L5) | 0m03s |

## 2. Critérios da B4 (bolt-plan) e "Pronto quando" da U4 → evidência
| Critério | Evidência | Resultado |
|---|---|---|
| B4: `paths.include` = `[src]` (projeto com `src/`) | passo 5, caso `src` (`cmp` com `expected_bob_yaml "[src]"`), verde na `main`; `test_write_creates_src_when_src_has_code` (T1, #195); `test_harness_expects_the_ct7_text[src]` (T3, #198) | Atende |
| B4: `paths.include` = `[app]` (código só em `app/`) | passo 5, caso `app`; `test_write_lists_every_code_folder_in_code_point_order` (T1); `test_harness_expects_the_ct7_text[app]` (T3) | Atende |
| B4: `paths.include` = `["."]` (sem código) | passo 5, caso `sem-codigo`; `test_no_code_is_dot_and_created_no_code`, `test_code_only_in_the_root_is_dot` (T1); `test_bob_yaml_step_warns_when_there_is_no_code` (T2, #196); `test_harness_expects_the_ct7_text[.]` (T3) | Atende |
| B4: preservação do `bob.yaml` existente | passos 7 (`digest` igual e linha `  preserved: bob.yaml (already exists; not changed)`) e 8 (sha igual + mesma linha); `test_existing_bob_yaml_is_preserved[file,link,dir]`, `test_second_write_is_preserved_and_changes_nothing` (T1); `test_bob_yaml_step_reports_preserved` (T2); `test_steps_7_and_8_check_the_preserved_lines` (T3) | Atende |
| B4: preservação dos waivers | passo 8 (sha de `.bob/waivers.yaml` igual + `  preserved: .bob/waivers.yaml (bob does not change it)`); `test_bob_yaml_step_lists_existing_waivers[file,symlink,directory]`, `test_bob_yaml_step_reaches_the_summary` (T2) | Atende |
| `not_run` sem código com exit 0 (Q1 = A, T1b) | passo 5, caso `sem-codigo`: `bob check --base HEAD --gates crap,dry,deps` não sai 4 (o script só para em 4; o previsto é 0); `test_measure_skips_crap_and_coverage_without_code`, `test_measure_finds_no_code_outside_the_include_rule[4]`, `test_a_repo_without_code_skips_crap_and_coverage_and_exits_0` (T1b, #197); e2e da T1b (7 `EXIT:0`, ⏭️ "no code to measure"); docs D1–D7 (T1c, #199) | Atende |
| Não regressão: com código, falha do coverage segue 4 | `test_measure_runs_crap_and_coverage_when_there_is_code[3]`, `test_a_missing_coverage_file_keeps_the_coverage_gate_a_tool_failure` (T1b); `test_a_missing_coverage_file_stays_a_tool_failure` (guarda sem edição) | Atende |
| Pronto 1: os 3 projetos e `bob check` ≠ 4 nos 3 | passo 5 verde na `main` | Atende |
| Pronto 2: aviso de pasta sem código só no 3º | passo 5 (`grep -Fx` do texto en: obrigatório em `sem-codigo`, proibido em `src`/`app`); `test_step_5_checks_the_no_code_warning`; texto pt por `test_bob_yaml_step_no_code_warning_reaches_the_output[pt-BR]` (I27) | Atende |
| Pronto 3: demais chaves = README, sem `languages` | `test_render_config_is_the_ct7_text` (T1, com o comando de paridade com `README.pt-BR.md`); passo 5 (`cmp` byte a byte com o CT7) | Atende |
| Pronto 4: `bob.yaml` e waivers com o mesmo hash; resumo lista os dois | passo 8 | Atende |
| DoD 1–6 (bolt-plan) | prontos acima; Comando de Verificação (item 1); passos da U4 no PR da T3; CT7 implementado (T1) e consumidos sem mudança; PRs citam unit/FR/US/CT (verificações); merges pelo Emerson (item 3) | Atende |

### Metas de NFR da U4 (`nfr-requirements.md`)
| ID | Alvo | Medido | Evidência | Resultado |
|---|---|---|---|---|
| U4-N1 | `bob check … crap,dry,deps` ≠ 4 em 3 de 3 | 3 de 3 | passo 5 verde (`main`, #198, #199) | Atende |
| U4-N2 | `[src]`, `[app]`, `["."]` (3 de 3) | 3 de 3 | passo 5 | Atende |
| U4-N3 | 0 bytes diferentes do CT7; sem `languages` | 0 | passo 5 (`cmp`); `test_render_config_is_the_ct7_text`; `test_harness_expects_the_ct7_text` (3) | Atende |
| U4-N4 | aviso em 1 de 3 (só `sem-codigo`) | 1 de 3 | passo 5 | Atende |
| U4-N5 | 0 bytes alterados; 2 linhas `preserved:` | 0; 2 | passo 8 | Atende |
| U4-N6 | 0 arquivos alterados na 2ª execução; `st_mtime_ns` igual | 0; igual | passo 7 (`digest`); `test_second_write_is_preserved_and_changes_nothing` (`st_mtime_ns`, `tests/test_init_config.py:361-369`) | Atende |
| U4-N7 | 0 `bob.yaml.tmp-*`; 0 `bob.yaml` criado depois de falha | 0; 0 | `test_config_error_removes_the_temporary`, `test_rename_error_removes_the_temporary`, `test_write_error_leaves_no_temporary` (T1) | Atende |
| U4-N8 | 0 chamadas ao git, leituras e escritas com `bob.yaml` existente | 0 | `test_existing_bob_yaml_is_preserved[file,link,dir]` (git e `load_config` proibidos, sem temporário; `T1-verificacao.md`) | Atende |
| U4-N9 | 6 chaves × 2 idiomas com teste exato | 12 de 12 | `test_setup_messages_exist_in_both_languages` (+12 casos, T2) | Atende |
| U4-N10 | passo 5 ≤ 180 s | 5 s (local, #198); 7 s (CI #198, `bb08a2c`, #199); **6 s** (`main` `b142631`) | logs do `verify-install / linux-x64` | Atende |
| U4-N11 | harness inteiro ≤ 900 s | 146 s (local); 206 s (#198); 202 s (`bb08a2c`); **173 s** (`main` `b142631`) | logs do `verify-install / linux-x64` | Atende |
| U4-N12 | `sh -n` e `dash -n` exit 0 | 0; 0 | rodados na box sobre o script do head do #198 (o #199 não muda o script) | Atende |
| U4-N13 | 0 failed + errors; CRAP < 10; 0 sobreviventes sem waiver (0 waivers novos); linhas novas de `src/` 100% cobertas | 0; máx. 4.0; 0 (0 novos); 100% | CI `pytest` (3.10, 3.12) em todos os PRs e na `main`; comentários do `bob` (#195, #196, #197: CRAP máx. 4.0; "No surviving mutants"); `bob check … coverage` exit 0 com cobertura do diff 100% nos corpos de #195, #196, #197 | Atende |
| U4-N14 | 0 requisições de rede nos testes novos | — | nenhuma verificação remota mede rede; os testes usam `tmp_path` e `git` local (ET e leitura de `tests/test_init_config.py` sem `http`, `socket`, `urllib`), mas não há contagem de requisições | Não verificado |

Metas herdadas sem rebaixamento: passo 2 ≤ 300 s (U3-N1): 54 s na `main`; passo 7 ≤ 60 s (U1-N13/U3-N5): `tempo 0 s` na `main`.

## 3. PRs da U4
| PR | Tarefa (ET) | Head | Merge (SHA) | Merge (UTC-3) | Checks no head | pytest | Rodadas de correção |
|---|---|---|---|---|---|---|---|
| [#195](https://github.com/fazedordecodigo/bob/pull/195) | T1 (v2) | `49cd38b` | `0d85510b8fd9d578619ce6e7adbde231b66bdd85` | 20/10 20:33:04 | 6/6 verdes (verify-install em 3m37s) | 4476 passed | 2 (a 2ª veio da ET v2) |
| [#197](https://github.com/fazedordecodigo/bob/pull/197) | T1b (v1) | `953f91b` | `637ec39dfe55db138553b827a6bb8a72905476f1` | 21/10 10:37:21 | 6/6 verdes (verify-install em 3m48s) | 4486 passed | 0 |
| [#196](https://github.com/fazedordecodigo/bob/pull/196) | T2 (v3) | `0990f84` | `031957f6c41dcc4e3b0bf3d998c346d0eee7b456` | 21/10 12:32:41 | 6/6 verdes (verify-install em 3m33s) | 4513 passed | 0 na retomada; parou no passo 0 da v2 (`EXIT 4`, "No data to report.") e foi retomado na v3 sobre `637ec39`, no mesmo PR, sem force-push |
| [#198](https://github.com/fazedordecodigo/bob/pull/198) | T3 (v2) | `79e7ad3` | `bb08a2c0fd2ceed93223c3f4cd052b86b7cce5de` | 22/10 00:43:39 | 6/6 verdes (verify-install em 3m48s) | 4520 passed | 0; **verificado depois do merge** (box fora do ar de 21/10 14:48 até o merge) |
| [#199](https://github.com/fazedordecodigo/bob/pull/199) | T1c (v1) | `3a49309` | `b142631935df7cad40f241501969dfea03595057` | 22/10 08:26:20 | 7/7 verdes (6 + `website / build` 2m25s; verify-install em 3m51s) | 4520 passed | 0 |

Todos mergeados por `fazedordecodigo` (Emerson), conferidos por `GET pulls/<n>`. Relatórios: `code-generation/tasks/T1-verificacao.md`, `T1b-verificacao.md`, `T2-verificacao.md`, `T3-verificacao.md`, `T1c-verificacao.md`. Contagem do pytest: 4476 → 4486 (+10, T1b) → 4513 (+27, T2) → 4520 (+7, T3) → 4520 (T1c, só docs).

## 4. Lacunas e pendências
| # | Lacuna | Estado (22/10, UTC-3) | Dono |
|---|---|---|---|
| L1 | Versão do CT7 não incrementada por causa da emenda E2 | **Feita** em 22/10 08:54: `contract-summary.md` l.23 e l.252 em `v2`; o texto da E2 já estava no CT7 (l.322, registro na l.324); nota nova no "Registro" (l.948) com o que mudou, a aprovação do Emerson (20/10 21:42) e a entrega (T1b #197, T1c #199) | Arquiteto |
| L2 | "fica para o Analista" em `T1b-emenda.md:25` e `trace.md:58` (I33) | **Feita** em 22/10 08:54: as duas frases dizem que o `contract-summary.md` é do Arquiteto e que o CT7 subiu para v2 em 22/10/2026 | Arquiteto |
| L3 | `construction/u4-bob-yaml/trace.md` desatualizado | **Feita** em 22/10 08:54: estado "aguardando o checkpoint do Emerson"; T1, T2, T3 e T1c com PR, head, merge e verificação (T1b já estava certa); DoD com 6 checks mais `website / build` na T1c; FR4.4 e DoD com a T1c | Arquiteto |
| L4 | 28 vulnerabilidades high no `npm ci` do site (`website / build` do #199). Já existiam; o #199 não toca `package.json` nem o lockfile | Registrada; fora do escopo da U4 | Emerson decide (issue ou unit futura) |
| L5 | Workflow `pages` falha na `main`: job `deploy`, passo "Configure GitHub Pages" → `Get Pages site failed … Not Found` (GitHub Pages não habilitado no repo). Já falhava antes, no run 39284313345 (`752d235`, 19/10 13:17 UTC-3), no mesmo passo. Não é check exigido; o `pages / build` passou | Registrada; fora do escopo da U4 | Emerson (configuração do repo) |
| L6 | U4-N14 (testes herméticos, 0 requisições de rede) sem medição remota | Não verificado | 3.6 / estratégia de testes |
| L7 | `bob / check` do CI roda `crap,dry,deps,mutate`; o gate `coverage` dos 5 só tem a evidência colada nos corpos dos PRs (exit 0, cobertura do diff 100%) | Registrada (vale desde a U3) | — |
| L8 | Herdados para 3.6/U9: matriz macOS/arm64; `VERIFY_REMOTE=1` só depois de uma release com a U4 (I32); gates com `include ["."]` em projetos reais | Não verificado (U9) | — |
| L9 | O #198 foi mergeado antes da verificação. A verificação pós-merge aprovou sem desvios; fica o registro de que, nesta unit, um merge não esperou o "aprovado para checkpoint" | Registrada | Maestro |

## Registro
- 22/10/2026 08:26 (UTC-3): o Emerson mergeou o #199 (`b142631`).
- 22/10/2026 08:52 (UTC-3): checkpoint preparado. `traceability.json` (U4 `T1c` e PR 199 `merged`) e `code-generation/trace.md` atualizados.
- 22/10/2026 08:54 (UTC-3): L1–L3 corrigidas (CT7 em v2 no `contract-summary.md`; frases do "Analista" em `T1b-emenda.md` e `trace.md`; `trace.md` da U4 no estado real).
