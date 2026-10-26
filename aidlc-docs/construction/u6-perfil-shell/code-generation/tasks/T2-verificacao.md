# Verificação: ET-u6-perfil-shell-T2 (v1) × PR #205
Verificada em 23/10/2026 01:22 (UTC-3) contra `T2.md` (v1; base original da ET `22d461a`, rebase mecânico sobre `main` @ `040d744` pedido pelo Emerson). Só leituras remotas, sem clone nem fetch: `gh`/API GitHub (PR, files, patches, check runs, logs), `raw.githubusercontent.com` e o corpo do PR.

PR: https://github.com/fazedordecodigo/bob/pull/205 | branch `aidlc/u6-perfil-shell/t2-setup-perfil` → `main` | head `f3f810660a0e215ea7fd4cb46cd4f382c28e9640` | base `040d744d17e306f27414e0804b7e4d3bb54984c9` | aberto, pronto para revisão (`draft: false`), não mergeado (`mergedAt: null`) | 1 commit (parent = `040d744`), +168/−2, 4 arquivos.
Agente: `bc-0e86d115-1c2a-52e6-986e-1f4634ea4b95`. `correction_round` 0 (só rebase mecânico; sem lacuna de ET).

## Veredito: Aprovado para checkpoint
Os critérios de aceite, R1–R6 e os 4 testes (21 casos) + 5 tuplas `_MESSAGES` (10 casos) da ET v1 atendem. Os 6 checks obrigatórios do head estão verdes. Nenhum desvio que reprove. O merge é do Emerson.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u6-perfil-shell-T2: Linha perfil do shell no resumo do bob setup`; `aidlc/u6-perfil-shell/t2-setup-perfil` → `main`; `baseRefOid`/`parent` = `040d744…` | Atende |
| Fora de rascunho; não mergeado pelo agente | `isDraft: false`, `state: OPEN`, `mergedAt: null` | Atende |
| Passo 0 colado e igual ao esperado | corpo: `0`; `0`; linha `("tests/test_setup_cmd.py", "-k", "hook"),`; `EXIT:0`; `169 passed`; `EXIT:5`; `166 deselected` | Atende |
| Exatamente 4 arquivos | `messages.py`, `setup_cmd.py`, `test_hermetic.py`, `test_setup_cmd.py`. Nenhum proibido (`CHANGELOG.md`, `scripts/**`, `doctor.py`, `cli.py`, `install_skills.py`, `docs/**`, `website/**`, `README*`, `.github/workflows/`, `pyproject.toml`, `tests/conftest.py`) | Atende |
| R1 `import os` | entre `importlib.metadata` e `platform` | Atende |
| R2 constantes | `_PROFILE_ENV`, `_PROFILE_LINE`, `_PROFILE_ON_PATH`, `_PROFILE_ON_PATH_KEY`, `_PROFILE_ADDED_KEY`, `_PROFILE_KINDS` logo depois de `_DOCTOR_NOT_RUN`, ordem e valores exatos | Atende |
| R3 `_profile_text` | assinatura `-> Text | None`; regras 1–5 (`None`, `already-on-path`, `partition` + `is_absolute`, path absoluto → added, senão `None`); sem `strip`/`startswith`/`split`/regex; `Text` já importado de `messages` | Atende |
| R4 `_summary` | `profile = _profile_text(os.environ.get(_PROFILE_ENV))` + `print` entre avisos e `_DOCTOR_LINE`; assinaturas de `_summary`/`_fail` intactas | Atende |
| R5 mensagens | 5 chaves depois de `setup.doctor_not_run` em en e pt-BR; textos iguais à tabela (`setup.profile` com 2 espaços; `profile_added` em parênteses por coluna) | Atende |
| R6 hermetic | `"-k", "hook"` → `"-k", "hook or profile"`; id do parâmetro continua `tests/test_setup_cmd.py`; sem linha `test_project_version` (U7 T1 paralela) | Atende |
| 4 testes + 5 tuplas | nomes exatos; 16+2+2+1 = 21 casos; `_MESSAGES` com as 5 chaves; `render` importado. Nenhum `skip`/`xfail`/`only` | Atende |
| Contagem | corpo: `210 passed` (197+3+10); `test_setup_cmd.py` `197 passed`; `-k "hook or profile"` `65 passed`; net guard 0; suíte pós-rebase `4651 passed, 3 warnings` (4620 + 31) | Atende |
| Colunas ≤ 100 | patch: 0 linhas novas com `len > 101` | Atende |
| `bob check … crap,dry,deps,mutate,coverage` → 0 | corpo pós-rebase: EXIT:0; `_profile_text` CRAP 6.0 / `_summary` 4.0; diff coverage 100%; 0 sobreviventes; 0 waivers novos. Comentário CI bob: crap/dry/deps/mutate ✅, "No surviving mutants" | Atende |
| 6 checks verdes | tabela abaixo; CI pytest 3.10 e 3.12: `4651 passed, 3 warnings`; verify-install: 11 linhas `ok` | Atende |
| Corpo do PR | Resumo, Passo 0, Arquivos, Testes (4 nomes + 5 tuplas + guarda), Comandos, Rebase, `## Decisões tomadas: nenhuma`, `## Bloqueios` / Nenhum; refs U6, CT1, CT3, CT6, ADR 0021, ADR 0023, FR7.1, US1.1 | Atende |

## Checks no head `f3f81066` (início 23/10 00:53 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| bob / check | bob, run 39897407461 | success | 25m27s |
| bob / cold | bob, run 39897407461 | success | 0m58s |
| CI / pytest (3.10) | CI, run 39897407422 | success, `4651 passed, 3 warnings` | 21m51s |
| CI / pytest (3.12) | CI, run 39897407422 | success, `4651 passed, 3 warnings` | 21m31s |
| package / dist | package, run 39897407622 | success | 1m28s |
| verify-install / linux-x64 | verify-install, run 39897407428 | success, 11 linhas `ok` (1–9b,12); passo 2 em 69 s, passo 6 em 1 s, passo 12 em 13 s | 4m17s |
| website / build | — | não se aplica (o PR não toca `docs/` nem `website/`) | — |

## Observações (não reprovam)
- R3 item 3: `if kind is not None: if Path(rest).is_absolute(): return …; return None` em duas linhas em vez do ternário da ET; equivalente.
- `setup.profile_added` (en/pt-BR) partido em parênteses adjacentes para caber em 100 colunas; texto gerado idêntico.
- `mergeStateStatus: BLOCKED` com checks verdes: proteção de branch, não falha de CI.
- O CI do `bob / check` roda `crap,dry,deps,mutate` (sem `coverage`); a evidência do `coverage` está no corpo do PR.
- Contagem do pytest: 4620 → 4651 (+31 = 21 casos novos + 10 de `_MESSAGES`).

## Registro
- 23/10/2026 01:22 (UTC-3): rodada contra a v1 (head `f3f81066`, base `040d744` pós-rebase mecânico): aprovado para checkpoint, sem desvios. `correction_round` 0. `traceability.json` (U6 T2 `verified`, PR 205 `open`) atualizado. Status da unit sem mudança (`plan_approved`). O merge é do Emerson.
