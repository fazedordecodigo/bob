# Verificação: ET-u6-perfil-shell-T4 (v1) × PR #210
Verificada em 24/10/2026 01:48 (UTC-3) contra `T4.md` (v1, 23/10/2026 22:30 UTC-3; SHA base fixado no despacho em 24/10/2026: `4d1603323ddc13714fa50b5e98487cb0957c7f20`). Só leituras remotas pelo `gh` / GitHub API (PR, diff, commit, check runs, logs de job, comentários), sem clone nem fetch. Transcript do agente indisponível no box; evidência = corpo do PR + CI.

PR: https://github.com/fazedordecodigo/bob/pull/210 | branch `aidlc/u6-perfil-shell/t4-fora-do-home` → `main` | head `f8c9f523e1cf463755b9b2a8092e5935184dd6c7` | base `4d1603323ddc13714fa50b5e98487cb0957c7f20` | aberto, pronto para revisão (`isDraft: false`, `mergeable: MERGEABLE`, `merged: false`), não mergeado | 1 commit (`f8c9f523e1cf463755b9b2a8092e5935184dd6c7` sobre `4d1603323ddc13714fa50b5e98487cb0957c7f20`, 24/10/2026 00:24:07 UTC-3) | +122/−0, 1 arquivo (`tests/test_install_sh.py`).
Agente: `bc-d688f05c-76b1-51a3-9fb0-4daf1348f34c`. `correction_round` 0 (aprovado na 1ª rodada contra a ET v1).

## Veredito: Aprovado para checkpoint
Todos os critérios de aceite, os 3 helpers (`_tree`, `_tree_diff`, `_outside_run`), os 2 testes novos (5 casos) e as 2 provas de sensibilidade da ET v1 atendem. Os 6 checks obrigatórios do head (`bob / check`, `bob / cold`, `CI / pytest (3.10)`, `CI / pytest (3.12)`, `package / dist`, `verify-install / linux-x64`) estão verdes. Nenhum desvio. O merge é do Emerson.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u6-perfil-shell-T4: Teste: a instalação não escreve fora do HOME`; `aidlc/u6-perfil-shell/t4-fora-do-home` → `main`; base `4d1603323ddc13714fa50b5e98487cb0957c7f20` (#208 U7 T3 mergeada); commit único `f8c9f523e1cf463755b9b2a8092e5935184dd6c7` com parent `4d1603323ddc13714fa50b5e98487cb0957c7f20` | Atende |
| Fora de rascunho; não mergeado pelo agente | `state: OPEN`, `isDraft: false`, `mergeable: MERGEABLE`, `merged: false` | Atende |
| Passo 0 colado no PR e igual ao esperado | corpo do PR: checkout em `4d1603323ddc13714fa50b5e98487cb0957c7f20`; `STEP_IDS='1 2 3 4 5 6 7 8 9a 9b 10 11 12 13'`; `3`; `PROFILE_LINE='export PATH="$HOME/.local/bin:$PATH" # managed-by: bob-quality'`; `1`; `1`; `1`; `0`; `3`; `    assert result.stdout == "/h/.local/bin:/usr/bin:/bin"`; `EXIT:0`; `79 passed in 62.20s (0:01:02)`; `0` | Atende |
| Exatamente 1 arquivo, só acréscimos | `tests/test_install_sh.py` (+122/−0); `git diff -U0 origin/main...HEAD \| grep -c '^-[^-]'` = `0`; 0 arquivos proibidos (`scripts/install.sh`, `scripts/verify-install.sh`, `tests/test_verify_install.py`, `CHANGELOG.md`, `docs/**`, `website/**`, `src/**`) | Atende |
| `_tree`, `_tree_diff` e `_outside_run` idênticos à ET | `tests/test_install_sh.py:1555-1600`: `_tree(root: Path)` (1555-1573), `_tree_diff(before, after)` (1576-1584) e `_outside_run(git_project, base, tmp_path, home, extra)` (1587-1600) logo após `test_profile_line_sources_in_sh` (separados por 2 linhas em branco), idênticos linha por linha ao bloco da ET | Atende |
| Os 2 testes novos com nomes e ids exatos (5 casos); `84 passed` | `tests/test_install_sh.py:1603-1674`: `test_install_writes_nothing_outside_home` (1612, parametrizado `("shell", "name")`, ids `["bash", "sh", "zsh"]`) e `test_zdotdir_outside_home_is_the_only_outside_write` (1639, parametrizado `"before"`, ids `["new", "existing"]`). Corpo: `84 passed in 74.96s`, `EXIT:0`; `-k outside`: `5 passed, 79 deselected in 13.12s`, `EXIT:0`. CI `pytest (3.10)` e `pytest (3.12)`: 84 pontos em `tests/test_install_sh.py` | Atende |
| Colunas ≤ 100 nas linhas novas; sem skip/only/xfail/waiver | diff: 122 linhas adicionadas, máx. 78 colunas (`git diff -U0 origin/main...HEAD \| grep '^+[^+]' \| awk 'length > 101' \| wc -l` = `0`); 0 ocorrências de `skip`, `only`, `xfail`, `xit`, `@Ignore` ou asserts comentados; 0 waivers novos | Atende |
| Provas de sensibilidade 1 e 2 + restauração de `scripts/install.sh` | corpo do PR: Prova 1 (`: > .bob-mark` em `step_ok projeto`) → `EXIT:1`, `5 failed, 79 deselected in 13.48s`; Prova 2 (`: > "$ZDOTDIR/.zcompdump-bob"` em `step_ok perfil`) → `EXIT:1`, `2 failed, 3 passed, 79 deselected in 13.56s`; `git checkout -- scripts/install.sh` após cada uma; `git status --porcelain scripts/` vazio; `scripts/install.sh` ausente do diff | Atende |
| Suíte inteira: 0 failed, 0 errors | CI `pytest (3.10)` (804.60s) e `pytest (3.12)` (961.95s): `4804 passed, 3 warnings` (4799 base + 5 novos), 0 failed, 0 errors; corpo: `4804 passed, 3 warnings, 32 subtests passed in 1072.64s`, `EXIT:0` | Atende |
| `bob check … crap,dry,deps,mutate,coverage` exit 0; 0 waivers novos | corpo: `EXIT:0`, `crap`, `dry`, `deps`, `mutate` e `coverage` passed (cobertura do diff Python 100.00%, 0 waivers novos); CI `bob / check` (run 40061330256, job 120775278655) `success`, comentário `bob-report` no commit `f8c9f52`: crap ✅, dry ✅, deps ✅, mutate ✅ ("No surviving mutants", "No mutants without tests", "No new clones in the diff") | Atende |
| 6 checks verdes no head | tabela abaixo (`bob / check`, `bob / cold`, `CI / pytest (3.10)`, `CI / pytest (3.12)`, `package / dist`, `verify-install / linux-x64`) | Atende |
| Corpo do PR | seções Resumo, Passo 0, Arquivos, Testes, Comandos (com as 2 provas de sensibilidade), `## Decisões tomadas: nenhuma`, `## Bloqueios` vazio e referências `U6, U6-N5, NFR7, CT2, CT16, ADR 0013, US1.1.` | Atende |

## Checks no head `f8c9f523e1cf463755b9b2a8092e5935184dd6c7` (início 24/10/2026 01:11:03 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| bob / check | bob, run 40061330256 (job 120775278655) | success; crap/dry/deps/mutate ✅ | 12m09s |
| bob / cold | bob, run 40061330256 (job 120775278762) | success | 0m38s |
| CI / pytest (3.10) | CI, run 40061330386 (job 120775279156) | success, `4804 passed, 3 warnings` | 13m55s |
| CI / pytest (3.12) | CI, run 40061330386 (job 120775279416) | success, `4804 passed, 3 warnings` | 16m36s |
| package / dist | package, run 40061330316 (job 120775278769) | success | 0m34s |
| verify-install / linux-x64 | verify-install, run 40061330482 (job 120775279823) | success, 14 linhas `ok` (passos 1..8, 9a, 9b, 10..13; passo 2 24 s, passo 10 18 s, passo 11 0 s, passo 12 14 s, passo 13 11 s) | 2m47s |
| website / build | — | não se aplica (o PR não toca `docs/` nem `website/`) | — |

## Observações (não reprovam)
- `mergeable_state: blocked` com `mergeable: MERGEABLE` e todos os 6 checks verdes: proteção de branch (merge humano), não falha de CI.
- Na 1ª execução local do `bob check`, a baseline saiu `2` porque `uvx` não estava no ambiente do agente; após instalar `uv==0.13.0` no venv (mesmo pin do CI), `bob check --base origin/main --gates crap,dry,deps,mutate,coverage --format both` saiu `0` com todos os 5 gates verdes.
- O CI do `bob / check` roda `crap,dry,deps,mutate` (sem `coverage`); a evidência do `coverage` está no corpo do PR (100.00% no diff Python), mesmo padrão das ETs anteriores.
- Transcript do agente não disponível no box.

## Registro
- 24/10/2026 01:48 (UTC-3): 1ª rodada contra a ET v1 (head `f8c9f523e1cf463755b9b2a8092e5935184dd6c7`, base `4d1603323ddc13714fa50b5e98487cb0957c7f20`): aprovado para checkpoint, sem desvios (`correction_round` 0). `traceability.json` atualizado (U6 T4 `verified_awaiting_checkpoint`, PR 210 `open` / `draft: false`). O merge é do Emerson.
