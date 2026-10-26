# Checkpoint da U7 (u7-update-versao) — B7
Preparado pelo Arquiteto em 24/10/2026 00:08 (UTC-3) para o checkpoint do Emerson. Base: `main` @ `4d1603323ddc13714fa50b5e98487cb0957c7f20` (merge do #208, T3, pais `4de84658badec6523a4f1890c748101bd6d2b870` e `002d24e2478f5f668e4a17820423af445a1a3e33`, árvore `4aba24adb6652cf007ab6b5b9430e78765211ce9`).
Formato: o mesmo de `construction/u6-perfil-shell/checkpoint.md`, `construction/u5-hook-pre-push/checkpoint.md` e `construction/u4-bob-yaml/checkpoint.md`.
Fontes: só leituras remotas (`cursor-github` / `gh api` para PRs, check runs e logs dos jobs; `raw.githubusercontent.com` em `4d16033`). Sem clone. Relatórios: `code-generation/tasks/T1-verificacao.md`, `T2-verificacao.md`, `T3-verificacao.md`.

## Confirmação dos merges e da `main`
- PR #203 (T1): `merged: true`, `merge_commit_sha` `675d933188b09bb2f23b88257c40efc850cca632`, `merged_at` 2026-10-23T11:50:52Z (**23/10 08:50:52 UTC-3**), `merged_by` `fazedordecodigo` (Emerson). Head `6d0d2329a8caf56e676859707dd9062bd1801c4c`, base `040d744d17e306f27414e0804b7e4d3bb54984c9`.
- PR #206 (T2): `merged: true`, `merge_commit_sha` `377b855daecb1f0354254c19f1ae62fb36800bab`, `merged_at` 2026-10-23T22:57:12Z (**23/10 19:57:12 UTC-3**), `merged_by` `fazedordecodigo` (Emerson). Head `4c99ff2196665d9d5c63fc2170c511b7468c7936`, base `675d933188b09bb2f23b88257c40efc850cca632`.
- PR #208 (T3): `merged: true`, `merge_commit_sha` `4d1603323ddc13714fa50b5e98487cb0957c7f20`, `merged_at` 2026-10-24T03:00:53Z (**24/10 00:00:53 UTC-3**), `merged_by` `fazedordecodigo` (Emerson). Head `002d24e2478f5f668e4a17820423af445a1a3e33`, base `4de84658badec6523a4f1890c748101bd6d2b870` (variante B, pós-merge da U6 T3 #207).
- Árvore git de `4d1603323ddc13714fa50b5e98487cb0957c7f20`: `4aba24adb6652cf007ab6b5b9430e78765211ce9`, idêntica à do head `002d24e2478f5f668e4a17820423af445a1a3e33` do PR #208.

## Veredito: pronto para o checkpoint do Emerson
O Comando de Verificação passa na `main` `4d16033`: `verify-install / linux-x64` `success` em 1m45s com **14 linhas `ok`** (passo 2 em 13 s, passo 10 em 9 s, passo 11 em 0 s, passo 12 em 8 s, passo 13 em 6 s; harness inteiro em cerca de 78 s), `package / dist` `success` em 41 s, e suíte `pytest` com `4799 passed, 0 failed, 3 warnings` em Python 3.10 e 3.12 na mesma árvore `4aba24a` (runs `40051845095` no head `002d24e` concluídos verdes; run `40056561616` do push em andamento). O "pronto quando" da U7 atende integralmente: o passo 10 atualiza de `v$X` para `v<X.Y.Z+1>`, preserva os 6 arquivos do passo 8, atualiza `.bob-version` nas 3 skills e ignora a pré-release `v99.1.0` e o rascunho `v99.1.1`; o passo 11 sai 0 com `"already on the newest release"`, 1 único pedido à API e `digest` idêntico; o passo 2 confere `bob --version`. Os **68 critérios** das 3 ETs atendem (T1: 17, T2: 21, T3: 30). Todas as **13 metas de NFR da U7** (`U7-N1` a `U7-N13`) atendem (**13 Atende, 0 Não atende, 0 Não verificado**). Os 3 PRs foram mergeados pelo Emerson. Houve 4 rodadas de correção no total (T1: 1, T2: 2, T3: 1), todas por lacunas mecânicas de ET fechadas sem alterar decisões aprovadas. Nenhuma lacuna bloqueia o checkpoint.

## 1. Comando de Verificação na `main` `4d16033`
Comando (`verification-command.md`, aprovado no 2.9):
`python3 -m venv /tmp/dev && /tmp/dev/bin/pip install -e '.[dev]' && /tmp/dev/bin/pytest && sh scripts/verify-install.sh`

| Parte | Evidência remota | Resultado |
|---|---|---|
| `sh scripts/verify-install.sh` | workflow `verify-install`, push em `4d16033`, run `40056561604` (job `120760715673`), `success`, 03:00:58–03:02:43 UTC (1m45s). Log: `Run sh scripts/verify-install.sh` às 03:01:06 UTC e **14 linhas `ok`**: 1, **2 (`tempo 13 s`)**, 3, 4, 5 (`tempo 4 s`), 6 (`tempo 1 s`), 7 (`tempo 0 s`), 8, 9a, 9b, **10 (`tempo 9 s`)**, **11 (`tempo 0 s`)**, 12 (`tempo 8 s`) e 13 (`tempo 6 s`). Último `ok` às 03:02:24 UTC. Harness em cerca de **78 s** | Atende |
| Passos da U7 (2 parcial, 10, 11) | mesmo log: `verify-install: passo 2: tempo 13 s` (`ok`, inclui `check_version`), `verify-install: passo 10: tempo 9 s` (`ok`), `verify-install: passo 11: tempo 0 s` (`ok`) | Atende |
| Sem regressão nos passos anteriores (1–9b, 12, 13) | mesmo log: todos `ok`, incluindo o passo 13 da U6 (`tempo 6 s`, `ok`) | Atende |
| Pacote | workflow `package`, push em `4d16033`, run `40056561603` (job `120760715540`), `dist` `success` (41 s) | Atende |
| `pip install -e '.[dev]'` + `pytest` | mesma árvore `4aba24adb6652cf007ab6b5b9430e78765211ce9` no head `002d24e` (#208, run `40051845095`): `pytest (3.10)` `success` em 14m06s (`4799 passed, 3 warnings in 812.74s`) e `pytest (3.12)` `success` em 16m53s (`4799 passed, 3 warnings in 974.89s`), 0 failed, 0 errors. No push de `4d16033`, o workflow `CI` (run `40056561616`) está em execução sobre a mesma árvore | Atende |
| Qualidade (`bob / check`, `bob / cold`) | Só rodam em PR. No head `002d24e` do #208 (mesma árvore `4aba24a`): `bob / check` `success` em 9m56s (crap/dry/deps/mutate ✅, "No surviving mutants", "No new clones") e `bob / cold` `success` em 36 s (`T3-verificacao.md`) | Atende |
| Docs (`website / build`) | Nenhum PR da U7 toca `docs/` nem `website/` (D9). O check não rodou | Não se aplica |
| Passo 14 (e 9c) | O passo 14 é da U8 T4; o 9c é coberto em pytest (`test_doctor.py`). Fora do escopo da B7 (passos 2 parcial, 10 e 11) | Não se aplica |
| Matriz (Linux arm64, macOS x64/arm64) | O CI só roda Linux x64. A matriz é da U9 | Não verificado (U9) |
| `VERIFY_REMOTE=1` | Os passos 10 e 11 imprimem `não se aplica (VERIFY_REMOTE=1)` e saem 0 (conferido no corpo do #208). A prova contra release real no GitHub fica no release-check da U9 | Não verificado (U9) |

### Checks no push da `main` `4d16033` (início 24/10 00:00:58 UTC-3) e na mesma árvore `4aba24a` (#208)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| package / dist (`4d16033`) | package, 40056561603 | success | 41 s |
| verify-install / linux-x64 (`4d16033`) | verify-install, 40056561604 | success, 14 `ok`, passo 2 em 13 s, passo 10 em 9 s, passo 11 em 0 s, passo 13 em 6 s, harness em ~78 s | 1m45s |
| CI / pytest (3.10) (árvore `4aba24a`, #208; push 40056561616 em curso) | CI, 40051845095 | success, `4799 passed, 3 warnings` | 14m06s |
| CI / pytest (3.12) (árvore `4aba24a`, #208; push 40056561616 em curso) | CI, 40051845095 | success, `4799 passed, 3 warnings` | 16m53s |
| bob / check (PR #208, árvore `4aba24a`) | bob, 40051845149 | success, crap/dry/deps/mutate ✅ | 9m56s |
| bob / cold (PR #208, árvore `4aba24a`) | bob, 40051845149 | success | 36 s |

## 2. Critérios da B7 (bolt-plan), "Pronto quando", FRs, USs, Contratos e ADRs da U7 → evidência
| Requisito / Critério | Evidência | Resultado |
|---|---|---|
| Pronto 1 / FR6.1–FR6.4 / US5.1: `bob update` atualiza de `v-antiga` para `v-nova`, confere sha256 antes do `sh`, atualiza `.bob-version` nas 3 skills, preserva artefatos do usuário e termina com `bob doctor: 0` | passo 10 `ok` (#208 em 17 s; `main` `4d16033` em 9 s): `run_bob 10 … update` em `$T/s8/proj`, `check_version 10` (`bob $NEW_X` e `project skills: $NEW_X (.agents/skills)`), `.bob-version` = `$NEW_X` nas 3 skills, `readlink current == versions/$NEW_X`, 6 arquivos do passo 8 com mesmo sha256, 4 linhas `preserved:`, `grep -cxF '  bob doctor: 0'` = 1; `test_new_release_downloads_checks_and_runs_install_sh[en,pt-BR]`, `test_install_keeps_the_environment_and_pins_the_tag` (T2) | Atende |
| Pronto 1 e 3 / US7.2: pré-release (`v99.1.0`) e rascunho (`v99.1.1`) ignorados pelo `bob update` e pelo comando único | passo 10 `ok` (R6e, R6i): lista exata de 5 pedidos no `bob update` e 4 pedidos no comando único ao espelho `/upd/`, zero pedidos a `v99.1.0`, `v99.1.1` ou `drafts/`, e `install: versão: $NEW_TAG` | Atende |
| Pronto 2 / FR6.5 / US5.2: 2ª execução sai 0 com `"already on the newest release"`, 1 pedido à API e 0 mudanças no projeto | passo 11 `ok` (#208 em 0 s; `main` `4d16033` em 0 s): saída exata `bob update: already on the newest release ($NEW_TAG).`, único pedido `GET /upd/api/releases/latest 200`, `digest` antes == depois; `test_up_to_date_prints_and_changes_nothing[same,newer]` (T2) | Atende |
| Só projeto atrasado → roda `bob setup` sem baixar `install.sh` (FR6.3, CT11) | `test_old_project_runs_setup_without_download[old,none,partial]` e `test_setup_context_receives_home_lang_version` em `tests/test_update.py` (T2 #206) | Atende |
| Passo 2 (parcial) / CT11: `bob --version` mostra `bob <X.Y.Z>` e `project skills: <X.Y.Z> (.agents/skills)` | `check_version 2 "$S2_HOME" "$S2_PROJ" "$T/s2/tmp" "$X"` no passo 2 (`ok` em 13 s na `main`); `test_cli_version_flag[en,pt-BR]`, `test_version_lines[en,pt-BR]`, `test_version_default_is_suppressed` (T2) | Atende |
| CT8 / C08 / ADR 0024 / Q1=A: `project_version.py` e linha `project skills:` como última linha do `bob doctor` | `test_manifest_skill_names_*` (3), `test_every_skill_with_the_same_version_is_installed`, `test_not_installed_cases`, `test_mixed_versions_sort_numerically`, `test_partial_install_is_mixed_with_missing`, `test_invalid_version_files_count_as_missing`, `test_skills_text_in_both_languages`, `test_skills_line_reads_the_project`, `test_doctor_last_line_is_the_project_skills[4]` (T1 #203) | Atende |
| CT4 (acréscimo): `install_skills.manifest_skill_names()` | `src/bob_quality/install_skills.py`; `test_manifest_skill_names_are_the_packaged_skills`, `test_manifest_skill_names_reads_the_given_source`, `test_manifest_skill_names_rejects_a_bad_manifest` (T1 #203) | Atende |
| CT12 / CT14 / ADR 0011 / ADR 0018 / ADR 0025: integridade `SHA256SUMS` antes de gravar/executar e política de rede (`urlopen`, 3 tentativas em rede/5xx, 1 em 4xx/429, `Accept` só na API) | `test_integrity_failures[3]`, `test_sums_first_matching_line_wins`, `test_api_errors_exit_4[5]`, `test_retry_then_success`, `test_http_500_is_retried`, `test_download_errors[3]`, `test_constants_match_install_sh_and_gitleaks` (T2 #206) | Atende |
| CT15 / ADR 0026 / ADR 0027: passos 10 e 11 no harness, `rebrand_wheel`, `CHANGELOG.md` na T3 | `scripts/verify-install.sh` (passos 2, 10, 11), `tests/test_verify_install.py` (46 passed), `CHANGELOG.md` no topo de `## Unreleased` (#208) | Atende |
| DoD (bolt-plan) | prontos acima; Comando de Verificação (item 1); `--only 11` e `--only 2` no #208; CT4, CT8, CT11, CT12, CT14 e CT15 atendidos; PRs citam unit, FR, US, CT e ADR, sem segredo; merges pelo Emerson | Atende |

**B7 atendida.**

## 3. Critério → evidência por ET
Fonte: as tabelas "Critério → evidência" dos 3 relatórios (`T1-verificacao.md`, `T2-verificacao.md`, `T3-verificacao.md`).

### T1 — Versão das skills do projeto (`project_version`) e linha no `bob doctor` (ET v2) × PR #203 (head `6d0d232`)
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u7-update-versao-T1: Versão das skills do projeto (project_version) e linha no bob doctor`; `aidlc/u7-update-versao/t1-project-version` → `main`; base `040d744` (pós-rebase autorizado pelo Emerson) | Atende |
| Fora de rascunho; não mergeado pelo agente | `isDraft: false`, `mergedAt: null` na verificação; mergeado pelo Emerson em `675d933` | Atende |
| Q1 = A antes do despacho | corpo: Q1 = **A** (`mixed (0.1.0, not installed)`), Emerson 22/10 22:17 (UTC-3) | Atende |
| Passo 0 colado e igual ao esperado (v2) | corpo: `RC:2`; `0`; `0`; `EXIT:0`; `116 passed in 7.68s`; `['./skills/bob-check', './skills/harden', './skills/review-report']` | Atende |
| Exatamente 7 arquivos | `doctor.py`, `install_skills.py`, `messages.py`, `project_version.py` (novo), `test_doctor.py`, `test_hermetic.py`, `test_project_version.py` (novo); nenhum proibido | Atende |
| R1 `manifest_skill_names` | depois de `default_source`, antes de `main`; assinatura, docstring e corpo exatos | Atende |
| R2–R7 `project_version.py` | docstring CT8/CT11/ADR 0024; só stdlib + `install_skills` + `messages`; `SkillsState`, `ProjectSkills`, `read_project_skills`, `skills_text`, `skills_line`; `_read_version` sem seguir symlink | Atende |
| R8 `doctor.py` | import `project_version` entre `gitleaks` e `user_dirs`; `print(render(project_version.skills_line(Path.cwd()), lang))` antes de `return _verdict` | Atende |
| R9 mensagens | 5 chaves `version.*` logo depois de `doctor.bob_home_relative` em en e pt-BR | Atende |
| R10 hermetic | `("tests/test_project_version.py",),` no topo de `_UNIT_ARGS` | Atende |
| A1 `test_doctor.py` | `_expected_versions` usa `splitlines()[:-1]`; última linha `project skills: not installed` | Atende |
| 12 testes com nome exato (43 + 4 casos) | 11 `def test_` em `test_project_version.py` + `test_doctor_last_line_is_the_project_skills`; sem `skip`/`xfail`/`only` | Atende |
| Contagem pytest local (corpo) | `174 passed` (43+20+97+4+10); suíte `4668 passed, 3 warnings` | Atende |
| Rede / doctor / colunas | net guard log 0; última linha `project skills: not installed`; 0 linhas novas > 100 colunas | Atende |
| `bob check … crap,dry,deps,mutate,coverage` → 0 | corpo: `EXIT:0`, 5 gates ✅, diff coverage 100%, CRAP máx `read_project_skills` 9.0, 0 waivers novos; CI `bob / check`: 4 gates ✅ | Atende |
| 6 checks verdes | 6/6 `success`; CI pytest 3.10 e 3.12: `4668 passed, 3 warnings`; `verify-install` 11 `ok` | Atende |
| Corpo do PR | Resumo, Passo 0, Arquivos, Testes, Comandos, Rebase, `## Decisões tomadas: nenhuma`, `## Bloqueios` / Nenhum, refs U7, CT4, CT8, CT11, ADR 0018, ADR 0024, Q1, FR6.1, US5.1 | Atende |

**T1: 17 Atende, 0 Não atende, 0 Não verificado.**

### T2 — `bob update` e `bob --version` (ET v3) × PR #206 (head `4c99ff2`)
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u7-update-versao-T2: bob update e bob --version`; `aidlc/u7-update-versao/t2-update` → `main`; base `675d933` | Atende |
| Fora de rascunho; não mergeado pelo agente | `isDraft: false`; merge feito pelo Emerson (`377b855`) | Atende |
| Passo 0 colado e igual ao esperado | corpo: `675d933…`; `RC:2`; `10`; `0`; `13:    ("tests/test_project_version.py",),`; `_COMMANDS = (… "setup")`; `EXIT:0`; `126 passed in 2.48s`; `['check', …, 'waive']` | Atende |
| Exatamente 6 arquivos | `cli.py`, `messages.py`, `update.py` (novo), `test_hermetic.py`, `test_update.py` (novo), `test_usage_exit.py`; nenhum proibido | Atende |
| R1 módulo / imports / nomes públicos | docstring exata; só stdlib + `project_version, setup_cmd, user_dirs, exit_codes, messages`; `DEFAULT_API`, `DEFAULT_DOWNLOAD`, `UpdateError`, `run_update`, `version_lines` | Atende |
| R2 constantes | `update.py:25-57`: valores exatos, `_ALLOWED_URL` igual ao de `gitleaks` (teste 22), `_RETRYABLE`, `_SUMS_SEP = b"  "`, `_FIRST_SERVER_ERROR = 500`, `_TMP_PREFIX = "bob-update."` | Atende |
| R3–R6 | `UpdateError`; `version_lines`; `_urls`; `_status`; `_read` (`timeout=_TIMEOUT_S`); `_fetch` (só `_RETRYABLE`, `code < 500` não repete, `sleep(_PAUSE_S)`) | Atende |
| R7 (v3) | `except ValueError:` levanta `UpdateError(msg("update.api_failed", status=msg("update.bad_response")))` de imediato, sem `data = None`; `_TAG_RE.fullmatch` | Atende |
| R8–R11 | `_numbers`; `_download` (404 → `download_missing`); `_sum_for` (`partition`, 1ª linha); `_install` (`mkdtemp`, `try/finally shutil.rmtree`, sha256 antes de `write_bytes`, `subprocess.run(..., check=False)`) | Atende |
| R12–R13 | `run_update` (`CONFIG_OR_TOOL = 4`); `_run` na ordem R13a–d | Atende |
| Proibidos (literais) | sem `decode(`, `strip`/`rstrip("/")`, `ignore_errors`, `status == "failed"`, `data = None` em `update.py` | Atende |
| R14 `cli.py` | `_Version(argparse.Action)` (`nargs=0`, `default=argparse.SUPPRESS`); `--version`; subparser `update` + `_add_lang`; dispatch `if args.command == "update": return run_update(Path.cwd(), lang)` | Atende |
| R15 mensagens | `cli.update`, `cli.version`, `version.bob` + 12 `update.*` em en e pt-BR (15 chaves × 2) idênticas à tabela | Atende |
| R16 hermetic | `("tests/test_update.py",),` logo após `("tests/test_project_version.py",),` | Atende |
| A1–A3 | `_COMMANDS` termina em `"update"`; `_TOP_HELP` e `_SUB_HELP["update"]` atualizados | Atende |
| 26 testes com nome exato (82 casos) | `tests/test_update.py`: 26 `def test_` na ordem 1–26 (82 casos), incluindo 23–26 da v3 e dublê seletivo no 15; sem `skip`/`xfail`/`only` | Atende |
| Contagens locais (corpo) | `176 passed` (82+79+5+10); net guard `82 passed`, log 0; `rg` URLs → `2`; `bob --version` → 2 linhas; suíte `4782 passed, 3 warnings` | Atende |
| `bob check … crap,dry,deps,mutate,coverage` | corpo: `EXIT:0`, coverage 100%, 0 waivers novos; CI `bob / check`: crap ✅ (máx `main` 8.0), dry ⚠️ 1 clone esperado `gitleaks.py` ↔ `update.py` (ADR 0025), deps ✅, mutate ✅ (0 sobreviventes no diff) | Atende |
| Colunas | 0 linhas novas > 100 colunas | Atende |
| 6 checks verdes | 6/6 `success`; `4782 passed, 3 warnings`; `verify-install` 11 `ok` | Atende |
| Corpo do PR | Resumo, Passo 0, Arquivos, Testes, Comandos, `## Decisões tomadas: nenhuma`, `## Bloqueios` vazio, refs U7, CT1, CT11, CT12, CT14, ADR 0011, ADR 0018, ADR 0025, FR6.1–FR6.5, US5.1, US5.2, US7.2, NFR9 | Atende |

**T2: 21 Atende, 0 Não atende, 0 Não verificado.**

### T3 — Harness: passos 10 e 11 (`bob update`) e `--version` no passo 2 (ET v2) × PR #208 (head `002d24e`)
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u7-update-versao-T3: Harness: passos 10 e 11 (bob update) e --version no passo 2`; `aidlc/u7-update-versao/t3-verify-install` → `main`; base `4de8465` (variante B, U6 T3 mergeada) | Atende |
| Fora de rascunho; não mergeado pelo agente | `isDraft: false`, não mergeado pelo agente; mergeado pelo Emerson em `4d16033` | Atende |
| Passo 0 colado e igual ao esperado | corpo: variante A inicial sobre `377b855` e seção Rebase documentando a variante B sobre `4de8465` (`STEP_IDS` até `13`, `46 passed`) | Atende |
| Exatamente 3 arquivos | `CHANGELOG.md`, `scripts/verify-install.sh`, `tests/test_verify_install.py`; nenhum proibido | Atende |
| CHANGELOG (R-CL): texto exato no topo de `## Unreleased` | 2 parágrafos (en, pt-BR) no topo de `## Unreleased`, acima da entrada da U6; ≤ 100 colunas; texto exato da ET | Atende |
| R1 + R-VI1: linhas 2 e 4 (variante B) | linha 2 `… 9a, 9b, 10, 11, 12 e 13.`; linha 4 `STEP_IDS='1 2 3 4 5 6 7 8 9a 9b 10 11 12 13'` | Atende |
| R2 globais | `STEP8_DONE=0`, `STEP10_DONE=0` após `STEP2_DONE=0`; `NEW_X=`, `NEW_TAG=`, `NEW_WHL=` após `GL_URL=` | Atende |
| R3 `ensure_8()` e `ensure_10()` | logo após `ensure_2`, na mesma forma | Atende |
| R4 passo 2 (`check_version`) | `if [ "$remote" -eq 0 ]; then check_version 2 "$S2_HOME" "$S2_PROJ" "$T/s2/tmp" "$X"; fi` após `check_gitleaks_install` | Atende |
| R5 ordem e posição das funções novas | entre `step_9b` e `pytest_pin`: `next_patch`, `rebrand_wheel`, `sums_two`, `build_update_mirror`, `run_bob`, `check_version`, `step_10`, `step_11` | Atende |
| R5a `next_patch()` | `awk -F. '{ printf "%s.%s.%d
", $1, $2, $3 + 1 }'` | Atende |
| R5b `rebrand_wheel()` | rebatiza `dist-info`, `METADATA` e recalcula `RECORD` em `ZIP_DEFLATED` | Atende |
| R5c `sums_two()` | grava `SHA256SUMS` com wheel e `install.sh` nessa ordem | Atende |
| R5d `build_update_mirror()` | monta `$T/mirror/upd` com `$NEW_TAG` em `latest`, `$TAG`, pré-release `v99.1.0` e rascunho `v99.1.1` | Atende |
| R5e `run_bob()` | `env -i` limpo com repasse das 14 variáveis na ordem de `run_oneliner` | Atende |
| R5f `check_version()` | confere as 2 linhas `bob $5` e `project skills: $5 (.agents/skills)` | Atende |
| R6 + R6a–R6j `step_10()` (incluindo R6d e R6i da v2) | guarda `VERIFY_REMOTE=1`, `ensure_8`, `run_bob 10 … update` ≤ 300 s, `grep -cxF "$_upg"` = 1, `grep -cxF '  bob doctor: 0'` = 1, 5 pedidos `/upd/`, `check_version 10`, 3 skills com `$NEW_X`, `current -> versions/$NEW_X`, 6 arquivos preservados + 4 linhas `preserved:`, comando único em projeto novo com `last_nonempty` == `  bob doctor: 0` e 4 pedidos `/upd/`, `tempo` + `ok 10` | Atende |
| R7 `step_11()` | guarda `VERIFY_REMOTE=1`, `ensure_10`, `run_bob 11 … update` ≤ 30 s, linha `_same`, único pedido `GET /upd/api/releases/latest 200`, `digest` antes == depois, `tempo` + `ok 11` | Atende |
| R8 + R-VI2 `run_selected` | `8) ensure_8 ;;`, `10) ensure_10 ;;`, `11) step_11 ;;`, `12) step_12 ;;`, `13) step_13 ;;` | Atende |
| A1–A3 + R-TV (variante B) | `_HELP`, `test_step_ids_are_the_known_steps` e `test_usage_errors_exit_1_before_preparing` com a lista até `13` | Atende |
| Helpers e 7 testes novos (9 casos) | `_body`, `_sh` + 7 testes entre `test_step_8_checks_the_foreign_hook` e `test_step_12_runs_the_hook_tests`; testes da U6 T3 preservados ao final | Atende |
| Sem skip/xfail/only/waiver | diff limpo; 0 waivers novos | Atende |
| `test_verify_install.py`: 46 passed | corpo e CI 3.10/3.12: `46 passed` | Atende |
| Colunas e POSIX `sh` | 0 linhas novas > 100 chars (linha 2 de R-VI1 com 99 chars / 101 bytes UTF-8 filtrada na v2); `sh -n` e `dash -n` RC:0 | Atende |
| Comandos locais do harness | `--only 11` (passo 10 em 15 s, passo 11 em 0 s), `--only 2` (17 s), `VERIFY_REMOTE=1 --only 10,11` (2 linhas `não se aplica`), `--only 15` (`RC:1`) | Atende |
| Harness inteiro no CI, ≤ 900 s, 14 linhas ok | #208: 2m22s (142 s), 14 `ok`, passo 10 em 17 s, passo 11 em 0 s; `main` `4d16033`: 1m45s (~78 s), 14 `ok`, passo 10 em 9 s, passo 11 em 0 s | Atende |
| Suíte inteira 0 failed / 0 errors | CI 3.10 e 3.12: `4799 passed, 3 warnings` | Atende |
| `bob check … crap,dry,deps,mutate,coverage` exit 0 | corpo: `EXIT:0`, 5 gates; CI `bob / check`: 4 ✅, "No surviving mutants", "No new clones" | Atende |
| 6 checks verdes | 6/6 `success` | Atende |
| Corpo do PR | seções completas, Rebase, `## Decisões tomadas: nenhuma`, `## Bloqueios` vazio, refs U7, CT11, CT12, CT15, ADR 0025–0027, FR6.1–FR6.5, US5.1, US5.2, US7.2, NFR2, NFR9 | Atende |

**T3: 30 Atende, 0 Não atende, 0 Não verificado.**

**Total das ETs da U7: 68 Atende, 0 Não atende, 0 Não verificado.**

## 4. Metas de NFR da U7 (`nfr-requirements.md`)
| ID | Alvo | Medido | Evidência | Resultado |
|---|---|---|---|---|
| U7-N1 | `bob --version` depois do `bob update` no passo 10: as 2 linhas = v-nova; `.bob-version` = v-nova em 3 de 3 skills | `bob $NEW_X` e `project skills: $NEW_X (.agents/skills)`; `.bob-version` = `$NEW_X` em 3 de 3 (`_n1 == _n0 == 3`); `current -> versions/$NEW_X` | passo 10 `ok` (#208 e `main` `4d16033`): `check_version 10`, R6b/R6f/R6g; `test_new_release_downloads_checks_and_runs_install_sh[en,pt-BR]` | Atende |
| U7-N2 | Pedidos ao espelho com `v99.1.0` (pré-release) ou `v99.1.1` (rascunho) = 0 | 0 pedidos a `v99.1.0`, `v99.1.1` ou `drafts/` (5 pedidos exatos no `bob update` e 4 no comando único em projeto novo) | passo 10 `ok` (R6e e R6i) no #208 e na `main` `4d16033` | Atende |
| U7-N3 | 2ª execução sem mudança (FR6.5, NFR4): `digest` do projeto antes/depois igual; exatamente 1 pedido (`api`) | `digest` antes == depois (`cmp -s`); 1 pedido (`GET /upd/api/releases/latest 200`); saída `bob update: already on the newest release ($NEW_TAG).` | passo 11 `ok` (#208 e `main` `4d16033`); `test_up_to_date_prints_and_changes_nothing[same,newer]` | Atende |
| U7-N4 | Preservação (NFR5): hash de `bob.yaml`, `.bob/waivers.yaml`, hook alheio e skill alheia do passo 8 iguais em 4 de 4 | 6 de 6 arquivos preservados com sha256 idêntico + 4 linhas `preserved:` no stdout | passo 10 `ok` (R6h e R6h2) no #208 e na `main` `4d16033` | Atende |
| U7-N5 | Integridade (NFR6): `install.sh` com sha diferente ou sem linha no `SHA256SUMS` → 0 execuções do script e código `4` | 0 execuções do `sh`, código `4`, stderr `update.integrity`, pasta temporária removida | `test_integrity_failures[bad_sha,no_line,empty_sums]` (3 casos) e `test_sums_first_matching_line_wins` em `tests/test_update.py` (#206) | Atende |
| U7-N6 | Rede (CT14): 3 tentativas em rede/`5xx`, 1 em `4xx` (inclusive `429`); pausa 1,0 s; `Accept` só na API; `timeout=30` | 3 tentativas em rede/timeout/`5xx` (incluindo HTTP 500), 1 em `4xx`/`429`, `sleep(1.0)`, `Accept: application/vnd.github+json` só na API, `timeout=30` | `test_api_errors_exit_4[5]`, `test_retry_then_success`, `test_http_500_is_retried`, `test_download_errors[3]`, `test_constants_match_install_sh_and_gitleaks` (#206) | Atende |
| U7-N7 | Tempo do `bob update` (NFR2): `verify-install: passo 10: tempo <s> s` ≤ 300 s | 15 s (`--only 11` corpo #208); 17 s (CI #208); **9 s** (`main` `4d16033`) | log do `verify-install / linux-x64` (runs `40051845048` e `40056561604`); `step_10` morre se `> 300` | Atende |
| U7-N8 | Tempo do "já está": `verify-install: passo 11: tempo <s> s` ≤ 30 s | 0 s (`--only 11` corpo #208); 0 s (CI #208); **0 s** (`main` `4d16033`) | log do `verify-install / linux-x64` (runs `40051845048` e `40056561604`); `step_11` morre se `> 30` | Atende |
| U7-N9 | Harness inteiro (`sh scripts/verify-install.sh`) ≤ 900 s | 142 s (#208, job 2m22s); cerca de **78 s** (`main` `4d16033`, job 1m45s) | log do `verify-install / linux-x64` (runs `40051845048` e `40056561604`) | Atende |
| U7-N10 | Sem privilégio (NFR7): `sudo` no código novo = 0 | 0 menções/chamadas a `sudo` nos 3 PRs | passo 3 `ok` na `main` (`sudo.log` vazio); `test_verify_install_shape` verde no CI; diffs de #203, #206 e #208 sem `sudo` | Atende |
| U7-N11 | Nunca falha calado (NFR9): erros de `bob update` com mensagem no stderr e código `4` em 100% dos caminhos de erro de U1–U6 | 100% dos caminhos de erro testados com código `4` (e propagação do exit code do `install.sh` em U6) | `test_releases_url_rejects[3]`, `test_api_errors_exit_4[5]`, `test_bad_tag_is_an_invalid_response[7]`, `test_download_errors[3]`, `test_integrity_failures[3]`, `test_tmp_failures[2]`, `test_sh_failure`, `test_project_errors[2]`, `test_install_sh_exit_code_is_returned` (#206) | Atende |
| U7-N12 | Qualidade do diff: `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` exit 0; CRAP < 10; 0 sobreviventes; 0 waivers novos; coverage ≥ 80,0 e 100% das linhas novas | exit 0 nos 3 PRs; CRAP máx. 9.0 (`read_project_skills`, T1) e 8.0 (`main`, T2); 0 sobreviventes no diff; 0 waivers novos; diff coverage 100% (T1 e T2; T3 não toca `src/`) | corpos dos #203, #206 e #208 (`EXIT:0`, 5 gates); CI `bob / check` `success` nos 3 (clone `gitleaks.py` ↔ `update.py` esperado no `dry` como warn sem bloquear, ADR 0025; `coverage` no corpo dos PRs, ver L3) | Atende |
| U7-N13 | Testes herméticos (U5-N16): 0 linhas no log da guarda em `pytest tests/test_project_version.py` e `tests/test_update.py` | 0 bytes nos 2 arquivos | `test_u5_tests_open_no_network[tests/test_project_version.py]` e `[tests/test_update.py]` verdes no CI (#203, #206, #208); corpos de #203 e #206 com `BOB_NET_GUARD_LOG` = 0 | Atende |

**Contagem das metas de NFR da U7: 13 Atende, 0 Não atende, 0 Não verificado.**

Metas herdadas sem rebaixamento (log da `main` `4d16033`, run `40056561604`): passo 2 ≤ 300 s (U3-N1): 13 s. Passo 5 ≤ 180 s (U4-N10): 4 s. Passo 6 ≤ 60 s (U5-N11): 1 s. Passo 7 ≤ 60 s: 0 s. Passo 10 ≤ 300 s (U7-N7): 9 s. Passo 11 ≤ 30 s (U7-N8): 0 s. Passo 12 ≤ 240 s (U5-N12): 8 s. Passo 13 ≤ 180 s (U6-N7): 6 s. Harness ≤ 900 s (U5-N13, U6-N8, U7-N9): cerca de 78 s.

## 5. PRs da U7
| PR | Tarefa (ET) | Head | Base | Merge (SHA) | Merge (UTC-3) | Checks no head | pytest | Rodadas de correção |
|---|---|---|---|---|---|---|---|---|
| [#203](https://github.com/fazedordecodigo/bob/pull/203) | T1 (v2) | `6d0d2329a8caf56e676859707dd9062bd1801c4c` | `040d744d17e306f27414e0804b7e4d3bb54984c9` | `675d933188b09bb2f23b88257c40efc850cca632` | 23/10 08:50:52 | 6/6 verdes (`verify-install` 2m46s, 11 `ok`) | 4668 passed | 1 |
| [#206](https://github.com/fazedordecodigo/bob/pull/206) | T2 (v3) | `4c99ff2196665d9d5c63fc2170c511b7468c7936` | `675d933188b09bb2f23b88257c40efc850cca632` | `377b855daecb1f0354254c19f1ae62fb36800bab` | 23/10 19:57:12 | 6/6 verdes (`verify-install` 1m25s, 11 `ok`) | 4782 passed | 2 |
| [#208](https://github.com/fazedordecodigo/bob/pull/208) | T3 (v2) | `002d24e2478f5f668e4a17820423af445a1a3e33` | `4de84658badec6523a4f1890c748101bd6d2b870` | `4d1603323ddc13714fa50b5e98487cb0957c7f20` | 24/10 00:00:53 | 6/6 verdes (`verify-install` 2m22s, 14 `ok`) | 4799 passed | 1 |

Os 3 PRs foram mergeados por `fazedordecodigo` (Emerson), conferido por `GET pulls/<n>`.
Evolução do pytest na U6/U7: 4605 (fim da U5) → 4620 (+15, U6 T1) → 4668 (+48, U7 T1) → 4699 (+31, U6 T2) → 4782 (+83, U7 T2) → 4790 (+8, U6 T3) → **4799** (+9, U7 T3).

## 6. Lacunas de ET e rodadas de correção
| Tarefa | Rodadas | Lacuna | Correção | Versão da ET |
|---|---|---|---|---|
| T1 | **1** | A âncora do Passo 0 na v1 esperava `104 passed` (20+81+3), mas `tests/test_doctor.py` já tinha 93 casos em `22d461a` (`test_doctor_accepts_node_22_from_22_18_0` parametrizado 12×2), totalizando `116 passed` (20+93+3). O agente parou no Passo 0 conforme a regra | A v2 atualizou o esperado do Passo 0 para `116 passed` e os totais derivados (`174 passed`), sem mudar código de produção nem decisão aprovada | v1 → **v2** (`T1-v1.md`, `CORRECAO-v2.md`) |
| T2 | **2** | **Rodada 1 (v1 → v2):** o teste 15 (`test_sh_failure`) substituía `update.subprocess.run` por erro incondicional, fazendo `setup_cmd.step_projeto` (`git rev-parse`) falhar antes do `sh` de R11c. **Rodada 2 (v2 → v3):** 4 mutantes sobreviveram por falta de caso na lista fechada de testes e 1 mutante equivalente em R7 (`data = None` → `data = ""` no `except ValueError` de `json.loads`) | **v2:** dublê seletivo no teste 15 (falha só quando `argv[0] == "sh"`). **v3:** R7 levanta `UpdateError` imediatamente no `except ValueError` (sem `data = None`) e acrescenta os testes 23–26 (`test_http_500_is_retried`, `test_install_passes_check_false`, `test_setup_context_receives_home_lang_version`, `test_version_default_is_suppressed`). Nenhuma decisão aprovada mudou | v1 → v2 → **v3** (`T2-v1.md`, `T2-v2.md`, `CORRECAO-v2.md`, `CORRECAO-v3.md`) |
| T3 | **1** | (1) Em R6d, o `bob update` em Python sem TTY usa buffer de bloco no `stdout`; o `print(update.upgrading)` do processo pai sai no flush final ao encerrar, **depois** da saída do subprocesso `sh install.sh` (`  bob doctor: 0`), então `last_nonempty` via a linha do `bob update` em vez de `  bob doctor: 0`. (2) O cheque `awk 'length > 101'` do diff em locale C contava bytes UTF-8 e acusava a linha 2 de R-VI1 (`99` caracteres, `101` bytes por `ç` e `ã`) | A v2 trocou o cheque de `  bob doctor: 0` em R6d por `grep -cxF '  bob doctor: 0'` (mantendo `last_nonempty` em R6i, onde `run_oneliner` roda `install.sh` direto) e filtrou `# Harness do comando de verificação (CT15):` no comando `awk`. Código de produção (`src/`) intocado | v1 → **v2** (`T3.v1.md`) |

**Rodadas de correção da U7: T1 = 1, T2 = 2, T3 = 1 (total 4; máximo permitido de 2 por ET respeitado em todas).** Todas foram lacunas mecânicas de ET, sem improviso dos agentes.
Também na T3, sem contar como rodada de correção: o 1º agente (`bc-34a643d4-0879-5a33-9521-7e7b5248d612`) caiu 2x por erro de plataforma da Cursor VM antes de abrir PR e foi relançado em `bc-f84f9695-8f2a-5c65-8ed4-b3f4eaa9e5af` com autorização do Emerson, além de receber o steer de rebase mecânico para a variante B sobre `4de8465` após o merge da U6 T3 (#207).

## 7. Pendências e riscos
| # | Item | Estado (24/10, UTC-3) | Dono |
|---|---|---|---|
| L1 | Passos 10 e 11 com `VERIFY_REMOTE=1`: imprimem `não se aplica (VERIFY_REMOTE=1)` e saem 0 (R6, R7). A prova contra release real no GitHub fica no release-check da U9 (CT13) | Não verificado (U9) | — |
| L2 | Matriz macOS (x64/arm64) e Linux arm64: o CI só roda `verify-install / linux-x64`. A matriz completa é da U9 | Não verificado (U9) | — |
| L3 | O `bob / check` do CI roda `crap,dry,deps,mutate`. A evidência do gate `coverage` dos 3 PRs está nos corpos (exit 0; diff coverage 100% na T1 e na T2) e na tabela CRAP do `bob-report` (100% nas funções novas) | Registrada (vale desde a U3) | — |
| L4 | Clone reportado pelo `dry` (`gitleaks.py:148-159` ↔ `update.py:78-89`, 12 linhas): esperado e documentado na ADR 0025 (rede copiada sem importar símbolos privados de `gitleaks`; constantes presas por `test_constants_match_install_sh_and_gitleaks`). Não bloqueia o gate `dry`. Extrair helper compartilhado fica como item opcional de backlog pós-v0.1.0 | Registrada (ADR 0025) | Backlog |
| L5 | `CI / pytest (3.10)` e `CI / pytest (3.12)` no push de `4d16033` (run `40056561616`): em execução no momento da escrita deste checkpoint; a mesma árvore git `4aba24adb6652cf007ab6b5b9430e78765211ce9` já passou nos 2 jobs no PR #208 (run `40051845095`, `4799 passed, 3 warnings`) | Em conclusão no push; árvore já provada | — |
| L6 | Na U6 T4 (despachada em paralelo com a U8 T1 sobre `4d16033`), fecha-se a parte `"arquivos fora do HOME = 0"` da U6-N5 (L2 do checkpoint da U6) | Em despacho (`u6-t4`) | Arquiteto |

## 8. Rastreabilidade US/FR → tarefa → PR → testes (`traceability.json`)
A U7 é dona de **US5.1**, **US5.2**, **US7.2** e **FR6.1–FR6.5**, e contribui para **NFR2, NFR4, NFR5, NFR6, NFR7 e NFR9**.

| US / FR | Tarefa | Contratos / ADRs | PR | Merge | Testes |
|---|---|---|---|---|---|
| US5.1, US5.2 / FR6.1 | T1 — Versão das skills do projeto (`project_version`) e linha no `bob doctor` | CT4, CT8, CT11 / ADR 0018, 0024 | #203 | `675d933` | `tests/test_project_version.py` (11 testes, 43 casos), `tests/test_doctor.py::test_doctor_last_line_is_the_project_skills` (4 casos), `tests/test_hermetic.py` (`test_project_version.py`) |
| US5.1, US5.2, US7.2 / FR6.1–FR6.5 | T2 — `bob update` e `bob --version` | CT1, CT11, CT12, CT14 / ADR 0011, 0018, 0025 | #206 | `377b855` | `tests/test_update.py` (26 testes, 82 casos), `tests/test_usage_exit.py` (A1–A3), `tests/test_hermetic.py` (`test_update.py`) |
| US5.1, US5.2, US7.2 / FR6.1–FR6.5 | T3 — Harness: passos 10 e 11 (`bob update`) e `--version` no passo 2 | CT11, CT12, CT15 / ADR 0025, 0026, 0027 | #208 | `4d16033` | `tests/test_verify_install.py` (7 testes novos, 9 casos; total 46 passed); `scripts/verify-install.sh` passo 2 (`check_version`), passo 10 e passo 11 |

## Registro
- 23/10/2026 08:50:52 (UTC-3): o Emerson mergeou o #203 (T1 → `675d933188b09bb2f23b88257c40efc850cca632`).
- 23/10/2026 19:57:12 (UTC-3): o Emerson mergeou o #206 (T2 → `377b855daecb1f0354254c19f1ae62fb36800bab`).
- 24/10/2026 00:00:53 (UTC-3): o Emerson mergeou o #208 (T3 → `4d1603323ddc13714fa50b5e98487cb0957c7f20`).
- 24/10/2026 00:02:43 (UTC-3): fecharam `package / dist` (41 s) e `verify-install / linux-x64` (1m45s, 14 linhas `ok`) no push de `4d16033`.
- 24/10/2026 00:08 (UTC-3): `checkpoint.md` da U7 preparado e `traceability.json` atualizado (U7 T3 e PR #208 `merged` em `4d1603323ddc13714fa50b5e98487cb0957c7f20`).
