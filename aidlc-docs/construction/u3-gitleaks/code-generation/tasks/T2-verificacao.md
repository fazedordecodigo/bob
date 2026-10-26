# Verificação: ET-u3-gitleaks-T2 (v2) × PR #192
Verificado em 20/10/2026 11:19 (UTC-3), contra a ET v2, só com leituras remotas (cursor-github), sem clone.
PR: https://github.com/fazedordecodigo/bob/pull/192 | branch `aidlc/u3-gitleaks/t2-setup-doctor` → `main` | head `6c5b3d12a98d8dcfbca26a3ad48f605b8f7e7ece` | base `f8b4068` (main com a T1 mergeada) | aberto, **não draft**, não mergeado, `mergeable: true` (`mergeable_state: blocked`, aguardando review) | 2 commits, +424/−10.

## Veredito: Aprovado para checkpoint (contra a ET v2)
Rodada 1 (head `6758783`): bloqueio relatado pelo agente (sobrevivente `setup_cmd.py:170`, `installed_version(ctx.home)` → `installed_version(None)`). A lacuna era da ET e foi corrigida na v2 (20/10 10:35), que incluiu `test_gitleaks_step_passes_ctx_home_to_installed_version` (19 testes). Rodada 2 (head `6c5b3d1`): 1 commit, que só acrescenta esse teste. Todos os critérios atendem. 1 rodada de correção.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Exatamente 8 arquivos | `list_pull_request_files`: `CHANGELOG.md` (+4), `doctor.py` (+22/−4), `messages.py` (+4), `setup_cmd.py` (+19), `user_dirs.py` (+13), `test_doctor.py` (+149/−1), `test_setup_cmd.py` (+134/−3), `test_user_dirs.py` (+79/−2); `changed_files: 8`; nenhum proibido (`gitleaks.py`, `secrets_gate.py`, `npm_tools.py`, `scripts/*`, workflows, `test_verify_install.py` fora) | Atende |
| R1 + assinatura/docstring de `locate_binary` | `user_dirs.py` +188–197: assinatura e docstring exatas; `ValueError` → `shutil.which(name)`; `is_file()` e `os.access(…, X_OK)` → `str(candidate)` sem `resolve()`; senão `shutil.which(name)` | Atende |
| `shutil.which` com 1 argumento | as 2 chamadas novas são `shutil.which(name)`; `test_doctor_runs_only_node_and_gitleaks` não mudou e passa | Atende |
| R2 | `doctor._locate` → `return user_dirs.locate_binary(executable)`; `_cli_version` sem mudança | Atende |
| R3 + `doctor.py` sem sha256/URL literal | `_GITLEAKS_REFERENCE = ("linux", "x64")` com o comentário exato; `BinaryPin("gitleaks", gitleaks.VERSION, "gitleaks", gitleaks.asset_url(_GITLEAKS_REFERENCE), gitleaks.ASSETS[_GITLEAKS_REFERENCE][1])`; `doctor.py@6c5b3d1` sem nenhum hex de 64, sem `releases/download` e sem `https://github.com/gitleaks`; `rg` do corpo → só `gitleaks.py` | Atende |
| R4 | `_install_then_report`: npm → `bob_home()` (`ValueError` → `doctor.error` + `doctor.bob_home_relative`, `CONFIG_OR_TOOL`) → `ensure_gitleaks` (`GitleaksError` → `doctor.error` + `reason`, `CONFIG_OR_TOOL`) → `_report_pins` | Atende |
| R5 + assinatura/docstring de `step_gitleaks` | `setup_cmd.py` +145–156: assinatura e docstring exatas; `unchanged` sem `ensure`; `failed` com `reason(exc)`; `installed` com `msg(_ITEM_GITLEAKS, version=gitleaks.VERSION)`; chamadas pelo módulo; `_GITLEAKS` e `_ITEM_GITLEAKS` | Atende |
| R6 `STEPS` na ordem | `projeto, runtimes, npm, (_GITLEAKS = "gitleaks"), skills` | Atende |
| R7 imports | `setup_cmd.py`: `from bob_quality import gitleaks` + `GitleaksError`; `doctor.py`: `gitleaks`, `user_dirs`, `GitleaksError`; `user_dirs.py`: só `import shutil` | Atende |
| R8 | nenhuma linha `-` em `messages.py`; `cli.setup` intocado | Atende |
| Mensagens en/pt-BR exatas, no lugar | `doctor.bob_home_relative` logo depois de `doctor.error` (en e pt-BR); `setup.item_gitleaks` logo depois de `setup.item_npm` (en e pt-BR); 4 textos iguais à tabela (comparação literal) | Atende |
| CHANGELOG | os 2 parágrafos exatos no topo de `## Unreleased` | Atende |
| Linhas novas `.py` ≤ 100 | nenhuma linha `+` com mais de 100 colunas nos `.py` | Atende |
| Ajustes da lista fechada | `test_steps_are_the_u1_steps_in_order` → `test_steps_follow_the_ct3_order` (lista + `is step_gitleaks`); `monkeypatch` de `installed_version` em `test_setup_does_not_touch_the_project_package_files` antes do `run_setup`; `_MESSAGES` + `setup.item_gitleaks`; `_SAMPLES` + `"version": "versão"`; imports `gitleaks`, `step_gitleaks`; fixture autouse `_empty_bob_home` | Atende |
| Nenhum outro teste existente alterado | linhas `-` do diff de testes: só os imports, o teste renomeado e a docstring de módulo de `test_user_dirs.py` (ver observação 1) | Atende |
| `test_verify_install.py` intocado | fora da lista de arquivos; está no comando escopado (321 passed) | Atende |
| 19 testes, nomes exatos, nem mais nem menos | 20 `+def test_` = os 19 da v2 (5 `test_user_dirs`, 9 `test_doctor`, 5 `test_setup_cmd`) + o renomeado `test_steps_follow_the_ct3_order` (ajuste); diferença de conjunto = só esse | Atende |
| Sem skip/xfail/only/noqa/pragma | grep no diff: nada | Atende |
| Suíte e `BOB_HOME=/nao/existe` | CI: `4423 passed, 3 warnings` (3.12 e 3.10); corpo: `321 passed` (escopado), `93 passed` × `93 passed` | Atende |
| E2e manual | corpo: `bob setup: gitleaks: ok`, `installed: gitleaks 8.30.1 in BOB_HOME/bin, …`, `gitleaks expected 8.30.1 found 8.30.1`, `  bob doctor: 0` (sem gitleaks no `PATH`); 2ª execução `installed: nothing`; `bob doctor --install` EXIT 0. É da rodada 1 e vale: `compare 6758783...6c5b3d1` = 1 commit, só `tests/test_setup_cmd.py` (+21/−0) | Atende |
| `bob check` com `mutate` | job `check` success: `run_check.sh` grava o exit do `bob check --gates crap,dry,deps,mutate --base origin/main` e `propagate_exit.sh` sai com ele, então o exit foi 0. Sobrevivente sem waiver daria 3, como na rodada 1. O PR não toca em `.bob/waivers.yaml`. A contagem literal "0 sobreviventes" está só no corpo e no comentário do bot (não lido; fora das ferramentas permitidas) | Atende |
| 6 checks verdes no head | ver tabela abaixo | Atende |
| Corpo cita U3, CT3, CT8, CT9, ADR 0014, ADR 0019, FR2.1, FR2.2, FR2.3, US1.3, US1.1 crit. 5, "Decisões tomadas: nenhuma" | todos presentes ("US1.1 critério 5"; Decisões tomadas = "nenhuma"; Bloqueios = "nenhum") | Atende |
| Sem merge, fora de rascunho | `merged: false`, `draft: false`, `state: open` | Atende |

## Checks no head `6c5b3d1` (início 20/10 10:51:02 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| check | bob / 39433971920 | success | 24m29s |
| pytest (3.10) | CI / 39433972184 | success | 19m54s |
| pytest (3.12) | CI / 39433972184 | success | 13m43s |
| verify-install / linux-x64 | verify-install / 39433971937 | success | 2m35s |
| cold | bob / 39433971920 | success | 1m20s |
| dist | package / 39433971912 | success | 57s |

Linha final do pytest no log: 3.12 `4423 passed, 3 warnings in 761.96s (0:12:41)`; 3.10 `4423 passed, 3 warnings in 1109.46s (0:18:29)`.

## Observações (não reprovam)
1. `tests/test_user_dirs.py`: a docstring do módulo passou de `bob_home (CT5, CT6).` para `bob_home (CT5, CT6) e locate_binary (CT8, ADR 0019).`. Não é teste. O arquivo está na lista com "testes novos".
2. `doctor.py` mantém `import shutil` sem uso direto. É necessário porque `test_doctor_runs_only_node_and_gitleaks` troca `doctor.shutil.which` e tem que passar sem edição.
3. O job `check` tem 1 anotação (não lida).

## Registro
- 20/10/2026 11:19 (UTC-3): aprovado contra a ET v2; `traceability.json` (U3 T2: `verified`, PR 192, `et_version` v2, `correction_rounds` 1) e `trace.md` atualizados. Entregue ao Maestro. Merge é do Emerson.
