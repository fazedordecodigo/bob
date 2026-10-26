# Checkpoint da U5 (u5-hook-pre-push) — B5
Preparado pelo Arquiteto em 22/10/2026 20:45 (UTC-3) para o checkpoint do Emerson. Base: `main` @ `22d461a60920ab13e7b09fd654fd0e4686ba14d0` (squash do #202, T3, pai `144b997`).
Formato: o mesmo de `construction/u4-bob-yaml/checkpoint.md`.
Fontes: só leituras remotas (cursor-github para PRs, check runs, workflow runs, compare e logs dos jobs; `raw.githubusercontent.com`; API pública). Sem clone.

## Confirmação do merge e da `main`
- PR #202: `merged: true`, `merge_commit_sha` `22d461a60920ab13e7b09fd654fd0e4686ba14d0`, `merged_at` 2026-10-22T22:42:55Z (**19:42:55 UTC-3**), `merged_by` fazedordecodigo (Emerson). Head `03e39e5`.
- `main` → `22d461a60920ab13e7b09fd654fd0e4686ba14d0`, pai único `144b997`, mensagem "ET-u5-hook-pre-push-T3: Harness: passos 6 e 12 e hook nos passos 7 e 8. (#202)", assinatura válida.
- Árvore: `compare 03e39e5...22d461a` mostra a mesma `tree` `c8e7dff1d5a66ce3f12e7927c2bf271d84f0adb8` no head do #202 e na `main`. Os checks que só rodam em PR (`bob / check`, `bob / cold`) valem para a `main`.

## Veredito: pronto para o checkpoint do Emerson
O Comando de Verificação passa na `main` `22d461a`. O pytest dá `4605 passed` em 3.10 e em 3.12. O `verify-install / linux-x64` tem 11 linhas `ok`: passo 6 em 1 s, passo 12 em 9 s e harness em cerca de 146 s. Os 4 checks do push estão verdes. A B5 e os 3 prontos da U5 atendem. Das 16 metas de NFR da U5, as 16 atendem. A U4-N14 continua Não verificado: a guarda da U5-N16 não roda os testes da U4. Os 3 PRs foram mergeados pelo Emerson. Nenhuma lacuna bloqueia o checkpoint.

## 1. Comando de Verificação aprovado na `main` `22d461a`
Comando (`verification-command.md`, aprovado no 2.9):
`python3 -m venv /tmp/dev && /tmp/dev/bin/pip install -e '.[dev]' && /tmp/dev/bin/pytest && sh scripts/verify-install.sh`

| Parte | Evidência remota | Resultado |
|---|---|---|
| `pip install -e '.[dev]'` + `pytest` | workflow `CI`, push em `22d461a`, run 39866937619. `pytest (3.10)`: `success` em 19m35s, `4605 passed, 3 warnings in 1096.16s`. `pytest (3.12)`: `success` em 14m01s, `4605 passed, 3 warnings in 778.39s`. 0 failed, 0 errors. Os 3 warnings são o `verify_requirements` de `tests/test_security_parse.py`, que já existia | Atende |
| `sh scripts/verify-install.sh` | workflow `verify-install`, run 39866937636 (job 120131364542), `success` em 2m50s. O log mostra `Run sh scripts/verify-install.sh` às 22:43:07 UTC e 11 linhas `ok`: 1, 2 (`tempo 40 s`), 3, 4, 5 (`tempo 5 s`), 6 (`tempo 1 s`), 7 (`tempo 0 s`), 8, 9a, 9b e 12 (`tempo 9 s`, `ok` às 22:45:33 UTC). Harness em cerca de **146 s** | Atende |
| Passos da U5 (6, 7, 8 parcial, 12) | mesmo log: `passo 6: tempo 1 s`, `passo 6: ok`; `passo 7: ok`; `passo 8: ok`; `passo 12: tempo 9 s`, `passo 12: ok` | Atende |
| Sem regressão nos passos que já existem (1, 2, 3, 4, 5, 9a, 9b) | mesmo log: todos `ok` | Atende |
| Pacote | workflow `package`, run 39866937693, `dist` `success` (1m24s) | Atende |
| Qualidade (`bob / check`, `bob / cold`) | Só rodam em PR. No head do #202 (`03e39e5`, mesma árvore): `bob / check` `success` em 11m55s e `bob / cold` `success` em 1m21s (`T3-verificacao.md`) | Atende |
| Docs (`website / build`) | Os PRs da U5 não tocam `website/`, e o check não rodou. O push em `22d461a` também não disparou o workflow `pages`: só rodaram `CI`, `package` e `verify-install` | Não se aplica |
| Passos 9c, 10, 11, 13, 14 | Ainda não existem no harness (U6, U7, U8, U9). Pelo bolt-plan, ficam fora do escopo da U5 (B5: passos 6, 7, 8 parcial, 12) | Não se aplica |
| Matriz (Linux arm64, macOS x64/arm64) | O CI só roda Linux x64. A matriz é da U9 | Não verificado (U9) |
| `VERIFY_REMOTE=1` | Só depois de uma release com a U5 (I44) | Não verificado (U9) |

### Checks no push da `main` `22d461a` (início 22/10 19:42 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| package / dist | package, 39866937693 | success | 1m24s |
| verify-install / linux-x64 | verify-install, 39866937636 | success, 11 `ok`, passo 6 em 1 s, passo 12 em 9 s, harness em cerca de 146 s | 2m50s |
| CI / pytest (3.10) | CI, 39866937619 | success, `4605 passed, 3 warnings` | 19m35s |
| CI / pytest (3.12) | CI, 39866937619 | success, `4605 passed, 3 warnings` | 14m01s |
| pages / build, pages / deploy | — | não rodaram neste push (ver L1) | — |

Cada um dos 4 check runs tem 1 annotation de nível `notice`: "The ubuntu-latest label will migrate to Ubuntu 26 beginning October 19, 2026" (ver L8).

## 2. Critérios da B5 (bolt-plan) e "Pronto quando" da U5 → evidência
| Critério | Evidência | Resultado |
|---|---|---|
| B5: o push dispara o hook | Passo 6 verde na `main` e no #202. O `git push` com `env -i HOME=… PATH=/usr/bin:/bin` sai 0, o remoto recebe o commit e o `.bob/report.md` tem `# bob report` e as linhas de `crap`, `dry` e `deps`. Também: e2e da T2 (`PUSH:0`, SHAs iguais) e `test_step_6_pushes_with_a_clean_env` | Atende |
| B5: `test_hook.py` < 60 s | Passo 12 na `main`: `7 passed` em 9 s, com o bob instalado. CI `pytest` 3.10 e 3.12 verde, com `test_pre_push_hook_runs_crap_gate_under_60s` e `test_pre_push_hook_blocks_when_changed_function_exceeds_crap_10`. No #200: 1.19 s e 1.15 s | Atende |
| B5: hook alheio e `core.hooksPath` preservados | Passo 8: sha igual, `  preserved: .git/hooks/pre-push (pre-push hook without the bob marker)` e o aviso com a linha. Também: `test_install_preserves_a_foreign_hook`, `test_install_never_follows_a_link_or_a_folder`, `test_install_respects_core_hooks_path` (T1); `test_hook_step_preserves_a_foreign_hook`, `test_hook_step_respects_core_hooks_path` (T2); e2e da T2 (`hookspath` sem `.git/hooks/pre-push` nem `.husky`) | Atende |
| Pronto 1: push para remoto bare com `env -i HOME=$HOME PATH=/usr/bin:/bin` dispara o hook e roda `bob check --gates crap,dry,deps` | Passo 6: `cmp` do hook com `expected_hook` (template do CT10), modo `-rwxr-xr-x`, push 0, commit no remoto e 3 gates no relatório | Atende |
| Pronto 2: `tests/test_hook.py` passa em < 60 s | Passo 12 (9 s no total, 7/7) e CI (3.10, 3.12) | Atende |
| Pronto 3: hook alheio com o mesmo hash e aviso no resumo; `core.hooksPath` sem nada gravado e aviso com a linha | Passo 8 (hook alheio). Para o `core.hooksPath`: testes da T1 e da T2 e o e2e da T2. O harness não tem caso de `core.hooksPath`; a ET não previa | Atende |
| Não verificado herdado do bolt-plan (l.40: "`test_hook.py` com o template novo") | Fechado. O `test_hook.py` instala por `install_hook` (T1, #200) e passa no CI e no passo 12 | Atende |
| DoD 1–6 (bolt-plan) | 1: prontos acima. 2: Comando de Verificação com saída 0 e sem regressão (item 1). 3: passos com `--only` no PR da T3 (`T3-verificacao.md`). 4: CT10, CT3 e CT15 implementados. 5: PRs citam unit, FR, US e CT, sem segredo (verificações). 6: merges pelo Emerson (item 3) | Atende |

**B5 atendida por inteiro.**

### Metas de NFR da U5 (`nfr-requirements.md`)
| ID | Alvo | Medido | Evidência | Resultado |
|---|---|---|---|---|
| U5-N1 | push `0`; commit no remoto; 3 de 3 linhas de gate | 0; sim; 3 de 3 | passo 6 verde (`main`, #202); e2e da T2 | Atende |
| U5-N2 | 0 bytes diferentes do CT10; `0755`; LF | 0; `0755`; LF | `test_render_hook_is_the_ct10_text`, `test_install_creates_the_hook`; passo 6 (`cmp` + modo); `test_harness_expects_the_ct10_text` (2 casos) | Atende |
| U5-N3 | < 60 s em cada uma das 2 medições; 7 de 7 | 1.19 s e 1.15 s (#200); 7/7 em 9 s (passo 12, `main`) | `tests/test_hook.py` no CI 3.10 e 3.12 (`main` verde); passo 12 | Atende |
| U5-N4 | 0 bytes e 0 de modo alterados; 1 linha `preserved:` e 1 aviso por item | 0; 1 e 1 | `test_install_preserves_a_foreign_hook` (5), `test_install_never_follows_a_link_or_a_folder`, `test_hook_step_preserves_a_foreign_hook`; passo 8 | Atende |
| U5-N5 | 0 arquivos criados; 1 aviso | 0; 1 | `test_install_respects_core_hooks_path` (2), `test_hook_step_respects_core_hooks_path`; e2e da T2 | Atende |
| U5-N6 | `unchanged`; bytes e `st_mtime_ns` iguais | `unchanged`; iguais | `test_install_is_unchanged_on_the_second_run`, `test_hook_step_second_run_is_unchanged`; passo 7 (`digest` + mtime do hook) | Atende |
| U5-N7 | `updated`; = CT10 e `0755` | `updated` | `test_install_updates_a_bob_hook_that_differs` (2), `test_hook_step_reports_updated` | Atende |
| U5-N8 | 0 `pre-push.tmp-*`; 0 `pre-push` depois de falha | 0; 0 | `test_write_error_leaves_no_temporary` (3), `test_temporary_is_next_to_the_hook` | Atende |
| U5-N9 | 0 chamadas ao git e 0 escritas com `BOB_BIN` inválido; 0 leituras em link ou pasta | 0; 0 | `test_bad_path_writes_nothing_and_calls_no_git`, `test_install_never_follows_a_link_or_a_folder` | Atende |
| U5-N10 | 100% (1 `git.*` + 8 `setup.*`, × 2 idiomas) | 18 de 18 | `test_git_command_failed_message_in_both_languages` (2); `test_setup_messages_exist_in_both_languages` (+16) | Atende |
| U5-N11 | passo 6 ≤ 60 s | 1 s (#202); **1 s** (`main`) | log do `verify-install / linux-x64` | Atende |
| U5-N12 | passo 12 ≤ 240 s | 14 s (#202); **9 s** (`main`) | log do `verify-install / linux-x64` | Atende |
| U5-N13 | harness ≤ 900 s | job 4m10s (#202); cerca de **146 s** (`main`, job 2m50s) | log do `verify-install / linux-x64` | Atende |
| U5-N14 | `sh -n` e `dash -n` com exit 0 | 0; 0 | `test_verify_install_is_posix` verde no CI da `main`. O `dash -n` só roda se houver `dash`; no `ubuntu-latest` há (o `/bin/sh` é dash) | Atende |
| U5-N15 | 0 failed + errors; CRAP < 10; 0 sobreviventes (0 waivers novos); linhas novas de `src/` 100% cobertas | 0; máx. 6.0 (`step_hook`); 0 (0 novos); 100% | CI `pytest` nos 3 PRs e na `main`; `bob check … crap,dry,deps,mutate,coverage` exit 0 nos corpos do #200 (cobertura do diff 100%), do #201 (100%) e do #202. A T3 não muda `src/` | Atende |
| U5-N16 | 0 linhas no log da guarda e pytest interno com saída 0; controle positivo ≥ 1 linha; `rg http` → exit 1 | 0; 0; ≥ 1; `RC:1` | `test_net_guard_catches_a_connection` e `test_u5_tests_open_no_network[tests/test_hook_install.py, tests/test_setup_cmd.py]` verdes no CI da `main` (3.10, 3.12); `rg -n "https?://" tests/test_hook_install.py` → `RC:1` (corpo do #200) | Atende |

**Contagem: 16 Atende, 0 Não atende, 0 Não verificado.**

**Hermeticidade e U4-N14:** a U5-N16 atende. Ela **não fecha a U4-N14**. Na `main`, o `_UNIT_ARGS` de `tests/test_hermetic.py` só tem `("tests/test_hook_install.py",)` e `("tests/test_setup_cmd.py", "-k", "hook")`. O `-k hook` não pega os testes `bob_yaml` do `test_setup_cmd.py`. Os testes novos da U4 (`test_init_config.py`, os testes `bob_yaml` do `test_setup_cmd.py`, os da T1b em `test_check_dispatch.py`/`test_check_report.py` e os de `test_verify_install.py`) não passam pela guarda. A U4-N14 segue **Não verificado**. O mecanismo para medi-la já existe; falta só acrescentar esses alvos ao `_UNIT_ARGS` (L3). No `traceability.json`, a U4-N14 não muda.

Metas herdadas sem rebaixamento: passo 2 ≤ 300 s (U3-N1): 40 s na `main`. Passo 5 ≤ 180 s (U4-N10): 5 s. Passo 7 ≤ 60 s (U1-N13/U3-N5): `tempo 0 s`. Harness ≤ 900 s (U1-N12/U3-N13/U4-N11): cerca de 146 s. Qualidade (U4-N13): igual à U5-N15.

## 3. PRs da U5
| PR | Tarefa (ET) | Head | Merge (SHA) | Merge (UTC-3) | Checks no head | pytest | Rodadas de correção |
|---|---|---|---|---|---|---|---|
| [#200](https://github.com/fazedordecodigo/bob/pull/200) | T1 (v2) | `7b97bc0` | `7f9ad593ca9d905b1c66cc03a8c30773c326af76` | 22/10 13:48:51 | 6/6 verdes (verify-install em 4m11s) | 4562 passed | 1. Lacuna da ET: na v1, os mutantes `partition` → `rpartition` (linhas 72 e 94) sobreviveram; a ET v2 incluiu os testes 22 e 23, que os matam. O código de produção não mudou |
| [#201](https://github.com/fazedordecodigo/bob/pull/201) | T2 (v1) | `fbd14d0` | `144b997079375d78a97530aaa10b506d89d42ab1` | 22/10 16:32:36 | 6/6 verdes (verify-install em 3m49s) | 4597 passed | 0 |
| [#202](https://github.com/fazedordecodigo/bob/pull/202) | T3 (v1) | `03e39e5` | `22d461a60920ab13e7b09fd654fd0e4686ba14d0` | 22/10 19:42:55 | 6/6 verdes (verify-install em 4m10s, 11 `ok`) | 4605 passed | 0 |

Os 3 foram mergeados por `fazedordecodigo` (Emerson), conferido por `GET pulls/<n>`. O merge da T2 em `144b997` às 16:32 está confirmado pela API.

Relatórios: `code-generation/tasks/T1-verificacao.md`, `T2-verificacao.md` e `T3-verificacao.md`.

Contagem do pytest: 4520 → 4562 (+42, T1) → 4597 (+35, T2) → 4605 (+8, T3).

## 4. Lacunas e pendências
| # | Lacuna | Estado (22/10, UTC-3) | Dono |
|---|---|---|---|
| L1 | GitHub Pages não habilitado (`has_pages: false`). O workflow `pages` não rodou no push de `22d461a`. Na U4 (L5), o `pages / deploy` falhava em "Get Pages site failed … Not Found". Não é check exigido | Registrada; continua como na U4 | Emerson (configuração do repo) |
| L2 | 28 vulnerabilidades high no `npm ci` do site (L4 da U4). Os PRs da U5 não tocam `website/` e o `website / build` não rodou, então não houve reverificação | Registrada; não reverificada | Emerson (issue ou unit futura) |
| L3 | U4-N14 continua Não verificado. Proposta para a 3.6: acrescentar ao `_UNIT_ARGS` de `tests/test_hermetic.py` os alvos `tests/test_init_config.py`, `tests/test_setup_cmd.py -k bob_yaml`, os testes da T1b e `tests/test_verify_install.py` | Não verificado | 3.6 / estratégia de testes |
| L4 | Os testes novos da T3 (`test_verify_install.py`) estão fora da guarda de rede. Pela definição, a U5-N16 cobre só a T1 e a T2. Esses testes rodam `sh` local | Registrada (entra na proposta da L3) | 3.6 |
| L5 | Herdados para a U9: matriz macOS/arm64 (U5-N1, N3, N11–N13 só medidos em Linux x64) e `VERIFY_REMOTE=1` só depois de uma release com a U5 (I44) | Não verificado (U9) | — |
| L6 | O `bob / check` do CI roda `crap,dry,deps,mutate`. A evidência do gate `coverage` dos 3 PRs só está nos corpos (exit 0, cobertura do diff 100%) | Registrada (vale desde a U3; L7 da U4) | — |
| L7 | No push do hook com `PATH=/usr/bin:/bin`, o `dry` fica ⏭️ (sem Node) e soma 0 (I43). O comportamento está previsto, mas um dev sem Node no PATH do terminal não roda o DRY no push | Registrada (observação, não reprovou) | Emerson decide se vira item de produto |
| L8 | Annotation `notice` nos 4 checks: o `ubuntu-latest` migra para Ubuntu 26 a partir de 19/10/2026. Pode mudar `dash`, `git` e Python do runner, e o U5-N14 depende do `dash` | Registrada; monitorar | Maestro |
| L9 | O corpo do #202 foi editado depois da minha verificação das 19:03. Acrescentou o CI com o passo 6 em 1 s e o passo 12 em 14 s. Conferi com os check runs: os números batem e o head (`03e39e5`) não mudou | Registrada (sem efeito) | — |
| L10 | Observações que não reprovaram. T2: `sed -n 1,6p` não mostrava as linhas dos gates; `SETUP:$?` pegava o exit do `grep`; o import da l.21 tinha 110 colunas na ET. T3: Decisões escritas como `## Decisões tomadas` seguido de "nenhuma" | Registrada | — |
| L11 | Lições para as próximas ETs: (a) o comando de evidência tem que mostrar o que o "esperado" pede; (b) `$?` só logo depois do comando medido, nunca depois de pipe ou `grep`; (c) conferir largura dos imports longos na própria ET; (d) fixar a forma literal do título de Decisões; (e) quando a ET usa `partition` ou `split` com limite, incluir o teste que mata o mutante `rpartition`/`rsplit` (lição da T1) | Para a 3.6 e as ETs da U6/U7 | Arquiteto |

## Registro
- 22/10/2026 19:42 (UTC-3): o Emerson mergeou o #202 (`22d461a`).
- 22/10/2026 20:02 (UTC-3): fechou o último check do push (`CI / pytest (3.10)`), e os 4 ficaram verdes.
- 22/10/2026 20:45 (UTC-3): checkpoint preparado. Atualizei o `traceability.json` (U5: T3 `merged`; PRs 200, 201 e 202 com merge; bloco `checkpoint` com aprovação pendente; status da unit sem mudança, `plan_approved`) e o `trace.md` da U5.
