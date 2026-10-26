# Verificação: ET-u6-perfil-shell-T1 (v2) × PR #204
Verificada em 23/10/2026 00:00 (UTC-3) contra `T1.md` (v2; v1 em `T1-v1.md`; base `main` @ `22d461a`). Só leituras remotas, sem clone nem fetch: cursor-github (PR, check runs, logs, arquivos/patch), `raw.githubusercontent.com` (`scripts/install.sh` no head) e o corpo do PR.

PR: https://github.com/fazedordecodigo/bob/pull/204 | branch `aidlc/u6-perfil-shell/t1-install-perfil` → `main` | head `a465b85dc655d652ebc4ca18542347bc75a5c445` | base `22d461a60920ab13e7b09fd654fd0e4686ba14d0` | aberto, pronto para revisão (`draft: false`), não mergeado (`merged: false`, `merged_by: null`) | 1 commit, +383/−3, 2 arquivos.
Commit: `a465b85` (pai `22d461a`). PR aberto em 22/10 23:26 (UTC-3). Agente: `bc-b7d54197-ae92-5825-b14d-3a683e13e7ff`. `correction_round` já 1 (lacuna das colunas `STEPS=` na ET; código não mudou na rodada; ET v2).

## Veredito: Aprovado para checkpoint
Os critérios de aceite, R1–R6, A1–A6 e os 8 testes (15 casos) da ET v2 atendem. Os 6 checks obrigatórios do head estão verdes. Nenhum desvio que reprove. A lacuna das 107 colunas em `STEPS=` é da ET v2, não do agente; conto 1 rodada de correção (já registrada no despacho). O merge é do Emerson.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u6-perfil-shell-T1: Passo perfil no install.sh`; `aidlc/u6-perfil-shell/t1-install-perfil` → `main`; `base.sha` = `22d461a…` (a da ET) | Atende |
| Fora de rascunho; não mergeado pelo agente | `draft: false`, `state: open`, `merged: false`, `merged_by: null` | Atende |
| Passo 0 colado e igual ao esperado | corpo, "Passo 0", sobre `22d461a…`: `STEPS=…launcher setup`; `DEFAULT_API=…`; `0`; `0`; `EXIT:0`; `64 passed in 25.36s`; `0` | Atende |
| Exatamente 2 arquivos | `list_pull_request_files`: `scripts/install.sh` +66/−2; `tests/test_install_sh.py` +317/−1. Nenhum proibido (`CHANGELOG.md`, `src/**`, `scripts/verify-install.sh`, `tests/test_verify_install.py`, `tests/test_hermetic.py`, `docs/**`, `website/**`, `README*`, `.github/workflows/`, `pyproject.toml`, `tests/conftest.py`) | Atende |
| R1 `STEPS` e `PROFILE_LINE` | l.4 `STEPS='…launcher perfil setup'` (107 colunas); l.5 `PROFILE_LINE='export PATH="$HOME/.local/bin:$PATH" # managed-by: bob-quality'`; `grep -c managed-by` → `1` (corpo); nada mais muda em 4–11 | Atende |
| R2 `step_perfil` depois de `step_launcher` | função entre o `}` de `step_launcher` e `step_setup`; R2a–R2g: `already-on-path`, escolha zsh/bash/`*`, marca `# managed-by: bob-quality`, append sem truncar, `chmod 0644` só no arquivo novo, `failed:` + `say profile_warning`, sempre `step_ok perfil` | Atende |
| R3 `profile_warning` e stdout | ids depois de `launcher_warning` em pt-BR e en; texto final igual ao da ET (`${PROFILE_LINE%% \#*}`); `if` com `launcher_warning \|\| profile_warning` no stdout | Atende |
| R4 `_run_step` | `perfil) step_perfil ;;` entre `launcher` e `setup` | Atende |
| R5 `step_setup` | `export BOB_INSTALL_PROFILE` entre `trap - EXIT INT TERM` e o `exec` | Atende |
| R6 utilitários; sem `sudo` | só `tail` e `chmod` novos em `_ALLOWED`; corpo: `grep -nE '\bsudo\b'` sem linha; sem `sed -i`/`mv`/`cp`/`env`/`>` sobre arquivo existente no caminho do perfil | Atende |
| A1–A6 | `tail`/`chmod` depois de `tr`; `PROFILE_LINE` em `_SOURCE_NAMES`/`_SOURCE`/`once`; `perfil` em `_CT2_STEPS` e `_assert_install_stdout`; `profile_warning` en/pt-BR; `FAKE_BOB_ENV` no `_fake_wheel`; `_run`/`_profile_run` com `umask` + `preexec_fn` | Atende |
| 8 testes com nome exato (15 casos) | patch: os 8 `def test_` na ordem da ET; ids `zsh,bash,sh,fish,empty,unset` / `newline,no-newline` / `en,pt-BR`; helpers `_PROFILE_LINE`, `_profile_run`, `_profile_env`, `_redirect_error`; `import stat`. Nenhum `skip`/`xfail`/`only` | Atende |
| `tests/test_install_sh.py`: 79 passed | corpo: `79 passed in 63.73s`, `EXIT:0` | Atende |
| Suíte inteira 0 failed | CI: `4620 passed, 3 warnings` em 3.10 (1244.68 s) e 3.12 (1259.27 s). 4605 da `main` + 15 novos. Warnings = `verify_requirements` já existente. Corpo: `4620 passed`, `EXIT:0`, `failed|error` → `0` | Atende |
| `sh -n` / `dash -n` | corpo: `RC:0` nos dois | Atende |
| Colunas ≤ 100, exceto `STEPS=` | script sobre os patches: 0 linhas novas com `len > 101` depois de excluir `+STEPS=`; `STEPS=` tem 107 (fonte única CT2, exceção da v2) | Atende |
| `bob check … crap,dry,deps,mutate,coverage` → 0 | corpo: `EXIT:0`, 5 gates ✅, 0 waivers novos. Comentário do `bob` no PR (CI, só `crap,dry,deps,mutate`): 4 ✅, "No surviving mutants", "No mutants without tests", "No changed file inside the include paths", waivers só de 2026-10-11 | Atende |
| 6 checks verdes; passo 2 com `bob doctor: 0` | tabela abaixo; log do `verify-install`: `passo 2: ok` (o harness só imprime `ok` se a última linha for `  bob doctor: 0`) | Atende |
| Corpo do PR | Resumo, Passo 0, Arquivos, Testes (8 nomes + A1–A6), Comandos, Evidence, `## Decisões tomadas: nenhuma`, `## Bloqueios` / Nenhum; referências U6, CT2, CT6, CT16, ADR 0013, ADR 0021, ADR 0022, FR1.1, NFR4, NFR5, NFR7, NFR9, US1.1 | Atende |

## Checks no head `a465b85` (início 22/10 23:27 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| bob / check | bob, run 39889627035 | success | 12m31s |
| bob / cold | bob, run 39889627035 | success | 1m17s |
| CI / pytest (3.10) | CI, run 39889627149 | success, `4620 passed, 3 warnings` | 22m20s |
| CI / pytest (3.12) | CI, run 39889627149 | success, `4620 passed, 3 warnings` | 22m25s |
| package / dist | package, run 39889627073 | success | 1m31s |
| verify-install / linux-x64 | verify-install, run 39889627026 | success, 11 linhas `ok` (1,2,3,4,5,6,7,8,9a,9b,12); passo 2 em 63 s, passo 6 em 1 s, passo 12 em 13 s | 4m03s |
| website / build | — | não se aplica (o PR não toca `docs/` nem `website/`) | — |

## Observações (não reprovam)
- R3: o `say` monta `profile_warning` em 3 concatenações em vez de um único `_msg=…`. O texto final é o da ET.
- A5: a linha do `handle.write('BOB_INSTALL_PROFILE=' + …)` foi partida em duas strings adjacentes para caber em 100 colunas. O conteúdo gerado é o mesmo.
- `step_perfil` usa o flag `_pok` em vez do fluxo literal R2d/R2e linha a linha. A ET libera o corpo da função shell desde que as regras e os testes passem.
- `mergeable_state: blocked` na consulta: checks verdes; o bloqueio típico é proteção de branch (review/aprovação), não falha de CI.
- O CI do `bob / check` roda `crap,dry,deps,mutate` (sem `coverage`); a evidência do `coverage` está no corpo do PR. `scripts/install.sh` e `tests/` ficam fora de `paths.include`, então o comentário do `bob` diz "No changed file inside the include paths".
- Contagem do pytest: 4605 → 4620 (+15 casos da T1).

## Registro
- 23/10/2026 00:00 (UTC-3): rodada contra a v2 (head `a465b85`): aprovado para checkpoint, sem desvios. `correction_round` 1 (lacuna `STEPS=` da ET; código sem mudança na rodada). `traceability.json` (U6 T1 `verified`, PR 204 `open`) atualizado. Status da unit sem mudança (`plan_approved`). O merge é do Emerson.
