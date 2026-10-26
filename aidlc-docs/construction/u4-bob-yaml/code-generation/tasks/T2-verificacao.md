# Verificação: ET-u4-bob-yaml-T2 (v3) × PR #196
Verificada em 21/10/2026 12:2x (UTC-3) contra `T2.md` (v3, base `main` @ `637ec39`, passo 0 com critério `EXIT:0`). Só leituras remotas (cursor-github: PR, commits, diff, compare, arquivos no head, check runs, logs dos jobs, comentário do `bob`), sem clone.
PR: https://github.com/fazedordecodigo/bob/pull/196 | branch `aidlc/u4-bob-yaml/t2-setup-step` → `main` | head `0990f841c93f8d4daeab9ef5becd5befdd6470b5` | base `637ec39dfe55db138553b827a6bb8a72905476f1` | aberto, pronto para revisão (`draft: false`), não mergeado, `mergeable: true` (`mergeable_state: blocked`, aguardando revisão) | 3 commits, +340/−1, 4 arquivos.
Commits: `d90c24d` (20/10 20:40 UTC-3, commit vazio do passo 0 bloqueado, pai `0d85510`), `88248c7` (21/10 10:45, merge de `origin/main`, pais `d90c24d` e `637ec39`), `0990f84` (21/10 11:12, entrega, pai `88248c7`). Agente: `bc-691329cf-9c32-599d-b0e2-34a6b6196ac0`, retomado em 21/10 10:47 (run `run-42340d21-0e04-4577-b9c9-a3cdd57990f9`).

## Veredito: Aprovado para checkpoint
Todos os critérios de aceite da v3, R1–R8, os 10 testes, os ajustes, o CHANGELOG, o passo 0, o e2e, o corpo e os 6 checks atendem. 0 rodadas de correção nesta retomada. O merge é do Emerson.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Retomada por merge, sem force-push | histórico do PR: `d90c24d` → `88248c7` (merge, pais `d90c24d` + `637ec39`) → `0990f84`; `compare 637ec39...0990f84`: `ahead 3`, `behind 0`; o corpo declara o merge `88248c7` sem rebase nem force-push | Atende |
| Passo 0 com `EXIT:0` e linha do anterior | corpo, "Passo 0": script igual ao da ET; `ConfigResult(state='created_no_code', include=('.',))`; `bob.yaml` com `  include: ["."]`; `EXIT:0`; `.bob/report.md` com ``- ⏭️ `crap`: not run (no code to measure)``; linha "Passo 0 anterior: `EXIT:4` em `0d85510`, resolvido pela T1b." | Atende |
| Exatamente 4 arquivos | `compare` contra `637ec39`: `CHANGELOG.md` +8, `messages.py` +20, `setup_cmd.py` +54, `tests/test_setup_cmd.py` +258/−1 (a remoção é a linha `from bob_quality import …` trocada); corpo traz o `git diff --name-only` com os 4 | Atende |
| R1 | `setup_cmd.py:201-212`: `def step_bob_yaml(ctx: SetupContext) -> StepResult:`, docstring idêntica (l.202), chamada `init_config.write_default_config(ctx.project)` por atributo (l.205) | Atende |
| Imports de `setup_cmd.py` | l.18 `from bob_quality import init_config` (linha própria, no estilo das l.16-21); l.22 `from bob_quality.config import ConfigError`; nenhum `ConfigResult` nem `write_default_config` importado pelo nome; `ToolError` já importado (l.27) | Atende |
| R2 | `STEPS` (l.215-222) termina em `(_BOB_YAML, step_bob_yaml)` depois de `("skills", step_skills)`; `_BOB_YAML = "bob.yaml"` (l.98), usado no `STEPS` e em `_failed_reason(_BOB_YAML, exc)` (l.209) | Atende |
| R3 | `_waivers_kept` (l.437-441): `ctx.project / ".bob" / "waivers.yaml"`, `exists() or is_symlink()` → `(msg(_PRESERVED_WAIVERS),)`, senão `()`; não lê nem escreve o arquivo | Atende |
| R4–R6 (estados) | `_config_result` (l.449-458) e `_no_code_warning` (l.461-464): `preserved` → `StepResult("preserved", preserved=(msg(_PRESERVED_BOB_YAML),) + W)`; `created` → `installed` com `installed=(msg(_ITEM_BOB_YAML),)`, `preserved=W`, `warnings=()`; `created_no_code` → o mesmo com `warnings=(msg(_WARN_NO_CODE),)` | Atende |
| R7 (exceções) | `ConfigError` → `StepResult(_FAILED, error=msg(_BOB_YAML_INVALID, detail=reason(exc)))`; `ToolError` → `_failed_reason(_BOB_YAML, exc)`; `OSError` → `_bob_yaml_write_failure` (l.444-446: `exc.strerror or type(exc).__name__`); nenhuma outra exceção capturada | Atende |
| R8 (6 chaves) | `messages.py` en l.446-455 e pt-BR l.860-869, logo depois de `setup.warn_duplicate` (l.442 e l.856), na ordem da ET, com os 12 textos idênticos à tabela; constantes `_ITEM_BOB_YAML` … `_BOB_YAML_WRITE` em `setup_cmd.py:107-112`, depois de `_WARN_DUPLICATE` | Atende |
| Teste 1 | `test_bob_yaml_step_reports_created` (`test_setup_cmd.py:1092`): `git_project`; `== StepResult("installed", installed=(msg("setup.item_bob_yaml"),))`; `"  include: [src]"` no `bob.yaml` | Atende |
| Teste 2 | `test_bob_yaml_step_warns_when_there_is_no_code` (l.1102): repo vazio em `tmp_path / "vazio"` (`init -q`, resolvido); `installed` + `warnings=(msg("setup.warn_no_code"),)` | Atende |
| Teste 3 | `test_bob_yaml_step_reports_preserved` (l.1114): `bob.yaml` = `"base: main\n"`; `StepResult("preserved", preserved=(msg("setup.preserved_bob_yaml"),))`; bytes iguais | Atende |
| Teste 4 (3 casos) | `test_bob_yaml_step_lists_existing_waivers` (l.1129), `parametrize("shape", ["file", "symlink", "directory"])`: (a) arquivo `"# w\n"` → `installed` + `preserved=(waivers,)`, bytes iguais; (b) `bob.yaml` + link quebrado → `preserved` com os 2 itens, `os.readlink` igual; (c) pasta → igual a (a), segue pasta | Atende |
| Teste 5 | `test_bob_yaml_step_invalid_config_fails` (l.1167): `ConfigError("quebrado")` → `setup.bob_yaml_invalid` com `detail="quebrado"` | Atende |
| Teste 6 | `test_bob_yaml_step_git_failure_fails` (l.1182): `ToolError(msg("git.ls_files_failed", detail="fatal: x"))` → `setup.step_reason` com `step="bob.yaml"` | Atende |
| Teste 7 (2 casos) | `test_bob_yaml_step_write_error_fails` (l.1206): `(PermissionError(13, "Permission denied"), "Permission denied")`, `(OSError(), "OSError")` → `setup.bob_yaml_write` | Atende |
| Teste 8 (2 casos) | `test_bob_yaml_step_failure_stops_setup` (l.1224), `lang` en/pt-BR: `STEPS` com `later` que levanta, `ConfigError("quebrado")`, `run_doctor` que levanta; `== 4`; linha `setup.error` no stderr; última linha do stdout `setup.doctor` com `setup.doctor_not_run` | Atende |
| Teste 9 | `test_bob_yaml_step_reaches_the_summary` (l.1265): passo real, `_pass_doctor(0)`, waivers `"# w\n"`; 1ª execução `0` com `bob setup: bob.yaml: ok`, `  installed: bob.yaml`, `  preserved: .bob/waivers.yaml (bob does not change it)`; 2ª `0`, `preserved: bob.yaml …` antes do waivers, bytes dos dois iguais | Atende |
| Teste 10 (2 casos) | `test_bob_yaml_step_no_code_warning_reaches_the_output` (l.1293), `lang` en/pt-BR: `== 0`; linhas `setup.warning_line` e `setup.warnings`; `  include: ["."]` | Atende |
| Ajustes em testes existentes | imports: `init_config` na linha `from bob_quality import …` (l.21), `from bob_quality.config import ConfigError` (l.22), `step_bob_yaml` no bloco de `setup_cmd`; `test_steps_follow_the_ct3_order` (l.324) com `"bob.yaml"` no fim e `assert dict(STEPS)["bob.yaml"] is step_bob_yaml`; `_MESSAGES` +6 tuplas no fim, na ordem da tabela; nenhum outro hunk em teste existente | Atende |
| Guarda intocada | `test_setup_does_not_touch_the_project_package_files` (l.937): nenhum hunk do diff passa por ela; passou no CI | Atende |
| Contagem do pytest | 4486 da `main` (`637ec39`) + 27 = 4513. Os 27: 15 casos dos 10 testes novos (1 + 1 + 1 + 3 + 1 + 1 + 2 + 2 + 1 + 2) e 12 de `test_setup_messages_exist_in_both_languages` (l.887-900, parametrizado por `_MESSAGES` × en/pt-BR: 6 tuplas × 2 idiomas). CI: `4513 passed, 3 warnings` em 3.10 e em 3.12 | Atende |
| CHANGELOG | topo de `## Unreleased`, en e pt-BR, cada um seguido de linha em branco, antes da entrada da T1b; juntando as quebras com espaço, texto idêntico ao da ET; linhas de 95, 98, 11 e 93, 98, 30 colunas, quebra só em espaço | Atende |
| ≤ 100 colunas | maior linha nova: 84 (`setup_cmd.py`), 86 (`messages.py`), 96 (`tests/test_setup_cmd.py`) | Atende |
| Sem skip/only | nenhum `skip`, `xfail`, `.only`, `noqa`, `pragma` nem assert comentado nas linhas novas | Atende |
| Nenhum waiver novo | tabela de waivers do comentário do `bob`: só entradas de 2026-10-11 | Atende |
| E2e | corpo, "E2e" (Node 22.23.3): `SETUP:0` nos três; `include` `[src]`, `[app]`, `["."]`; `bob setup: bob.yaml: warning: no code folder found; paths.include: ["."].` só em `sem-codigo`; 3 `EXIT:0`; reexecução com `  preserved: bob.yaml (already exists; not changed)` e `  preserved: .bob/waivers.yaml (bob does not change it)`, `SETUP:0`; sha256 do `bob.yaml` (`f5fe5a1a…`) e do waivers (`a6d1bad9…`) iguais antes e depois | Atende |
| `bob check … crap,dry,deps,mutate,coverage` → 0 | corpo: exit 0, 5 gates `passed`, 0 sobreviventes, cobertura do diff 100%; comentário do `bob` (CI, `crap,dry,deps,mutate`, commit `0990f84`): 4 ✅, CRAP máx. 4.0 (`step_bob_yaml`), "No surviving mutants", "No mutants without tests" | Atende |
| 6 checks verdes no head | tabela abaixo, todos `success` em `0990f84` | Atende |
| Corpo do PR | U4, CT3, CT7, ADR 0015, ADR 0017, US3.1, US3.2, FR4.1–FR4.6, NFR4, NFR5; `## Decisões tomadas: nenhuma`; `## Bloqueios` com "Nenhum."; comandos com saída (`178 passed`, `4513 passed`, `bob check` exit 0, `git diff` com 4 arquivos) | Atende |
| Pronto para revisão, não mergeado | `draft: false`, `merged: false`, `state: open` | Atende |

## Checks no head `0990f84` (início 21/10 11:45 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| bob / check | bob, run 39619572886 | success | 24m02s |
| bob / cold | bob, run 39619572886 | success | 1m19s |
| CI / pytest (3.10) | CI, run 39619572903 | success, `4513 passed, 3 warnings` | 20m34s |
| CI / pytest (3.12) | CI, run 39619572903 | success, `4513 passed, 3 warnings` | 15m12s |
| package / dist | package, run 39619572876 | success | 1m25s |
| verify-install / linux-x64 | verify-install, run 39619573074 | success, 8 linhas `ok` (1, 2, 3, 4, 7, 8, 9a, 9b) | 3m33s |

## Observações (não reprovam)
- `tests/test_setup_cmd.py` ganhou `import os` (l.7), que não está na lista de ajustes de import. É necessário para o `os.readlink` que o teste 4 (b) exige, como o `import json` que a T1 precisou para o teste 24.
- `_empty_repo(tmp_path)` (l.1085-1089) é um ajudante que monta o `empty_repo` da ET (`tmp_path / "vazio"`, `init -q`, sem arquivos, resolvido). É chamado dentro dos testes 2 e 10, e a T2 não proíbe ajudante (a T1b proibia).
- O caso `preserved` usa o literal `"preserved"` e o `installed`, a constante `_INSTALLED`; os dois produzem o mesmo `Status`.
- `mergeable_state: blocked` é a proteção da branch esperando revisão; não é conflito.

## Registro
- 21/10/2026 12:2x (UTC-3): rodada 1 da v3 (head `0990f84`): aprovado para checkpoint. `traceability.json` (U4 T2 `verified`, PR 196), `trace.md`, `code-generation-plan.md` e `T3.md` (v2, base "main após o merge da T2 (SHA a fixar)", números conferidos em `0990f84`) atualizados. O merge é do Emerson.
