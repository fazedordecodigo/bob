# Verificação: ET-u7-update-versao-T1 (v2) × PR #203
Verificada em 23/10/2026 01:22 (UTC-3) contra `T1.md` (v2; v1 em `T1-v1.md`; CORRECAO-v2.md; base original da ET `22d461a`, rebase pedido pelo Emerson sobre `main` @ `040d744`). Só leituras remotas, sem clone nem fetch: `gh`/API GitHub (PR, files, patches, check runs, logs, compare), `raw.githubusercontent.com` e o corpo do PR.

PR: https://github.com/fazedordecodigo/bob/pull/203 | branch `aidlc/u7-update-versao/t1-project-version` → `main` | head `6d0d2329a8caf56e676859707dd9062bd1801c4c` | base `040d744d17e306f27414e0804b7e4d3bb54984c9` | aberto, pronto para revisão (`draft: false`), não mergeado (`mergedAt: null`) | 2 commits (ahead 2; pai intermediário `1b31c9a` = bloqueio Passo 0 da rodada 1; merge_base = `040d744`), +386/−1, 7 arquivos.
Agente: `bc-b1261427-a288-5375-9a66-bd4e5620acca`. `correction_round` já 1 (lacuna Passo 0: 116 vs 104 na v1; ET v2).

## Veredito: Aprovado para checkpoint
Os critérios de aceite, R1–R10, A1 e os 12 testes (43 + 4 casos) da ET v2 atendem. Os 6 checks obrigatórios do head estão verdes. Nenhum desvio que reprove. A lacuna do Passo 0 é da ET (já fechada na v2); conto a rodada 1 já registrada. O merge é do Emerson.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u7-update-versao-T1: Versão das skills do projeto (project_version) e linha no bob doctor`; `aidlc/u7-update-versao/t1-project-version` → `main`; `baseRefOid` = `040d744…` (aceite pós-rebase; âncora original da ET era `22d461a`) | Atende |
| Fora de rascunho; não mergeado pelo agente | `isDraft: false`, `state: OPEN`, `mergedAt: null` | Atende |
| Q1 = A antes do despacho | corpo: Q1 = **A** (`mixed (0.1.0, not installed)`), Emerson 22/10 22:17 (UTC-3); `traceability` U7 `product_questions.Q1.answer` = `A` | Atende |
| Passo 0 colado e igual ao esperado (v2) | corpo, "Passo 0": `RC:2`; `0`; `0`; `EXIT:0`; `116 passed in 7.68s`; `['./skills/bob-check', './skills/harden', './skills/review-report']` | Atende |
| Exatamente 7 arquivos | compare `040d744...6d0d232`: `doctor.py`, `install_skills.py`, `messages.py`, `project_version.py` (added), `test_doctor.py`, `test_hermetic.py`, `test_project_version.py` (added). Nenhum proibido (`CHANGELOG.md`, `cli.py`, `update.py`, `setup_cmd.py`, `scripts/**`, `test_project_skills.py`, `test_setup_cmd.py`, `docs/**`, `website/**`, `README*`, `.github/workflows/`, `pyproject.toml`, `plugin/**`) | Atende |
| R1 `manifest_skill_names` | patch: depois de `default_source`, antes de `main`; assinatura e corpo exatos; docstring em duas literais adjacentes cujo `__doc__` concatenado = o texto de R1 | Atende |
| R2–R7 `project_version.py` | raw/patch: docstring CT8/CT11/ADR 0024; só stdlib + `install_skills` + `messages`; `SkillsState`, `ProjectSkills`, `read_project_skills`, `skills_text`, `skills_line`; `_SKILLS_DIR`/`_VERSION_RE`/`_SEP`/`_DOT`; `_read_version` com `is_symlink`/`is_file`/`OSError`/`fullmatch`/`raw[:-1].decode()`; R5a–R5c; `skills_text`/`skills_line` | Atende |
| R8 `doctor.py` | import `project_version` entre `gitleaks` e `user_dirs`; `print(render(project_version.skills_line(Path.cwd()), lang))` entre o `print` dos pins e `return _verdict` | Atende |
| R9 mensagens | 5 chaves `version.*` logo depois de `doctor.bob_home_relative` em en e pt-BR, textos iguais à tabela | Atende |
| R10 hermetic | `("tests/test_project_version.py",),` entre `_UNIT_ARGS = (` e `test_hook_install.py`; a linha `hook` da U6 T2 ainda não entra (PRs paralelos) | Atende |
| A1 `test_doctor.py` | `_expected_versions` usa `splitlines()[:-1]`; `test_doctor_expected_versions_match_pip_and_npm_pins` exige última linha `project skills: not installed` | Atende |
| 12 testes com nome exato (43+4 casos) | patch: os 11 `def test_` em `test_project_version.py` + `test_doctor_last_line_is_the_project_skills`; ids e parâmetros da ET. Nenhum `skip`/`xfail`/`only` | Atende |
| Contagem pytest local (corpo) | `174 passed` (43+20+97+4+10); pós-rebase `174 passed`; suíte `4668 passed, 3 warnings` (4620 da main com U6 T1 + 48) | Atende |
| Rede / doctor / colunas | net guard log 0; última linha `project skills: not installed`; `git diff` 7 arquivos; linhas novas >101 → `0` | Atende |
| `bob check … crap,dry,deps,mutate,coverage` → 0 | corpo pós-rebase: EXIT:0, 5 gates ✅, diff coverage 100%, CRAP máx `read_project_skills` 9.0, 0 waivers novos. Comentário CI bob: crap/dry/deps/mutate ✅; sobrevivente só fora do diff (`_report_pins` `"\n".join` → `"XX\nXX".join`, não bloqueia) | Atende |
| 6 checks verdes | tabela abaixo; CI pytest 3.10 e 3.12: `4668 passed, 3 warnings`; verify-install: 11 linhas `ok` (1,2,3,4,5,6,7,8,9a,9b,12) | Atende |
| Corpo do PR | Resumo, Passo 0, Arquivos, Testes (12 nomes + A1 + R10), Comandos, Rebase, Evidence, `## Decisões tomadas: nenhuma`, `## Bloqueios` / Nenhum; refs U7, CT4, CT8, CT11, ADR 0018, ADR 0024, Q1, FR6.1, US5.1 | Atende |

## Checks no head `6d0d232` (início 23/10 00:51 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| bob / check | bob, run 39897237295 | success | 16m19s |
| bob / cold | bob, run 39897237295 | success | 0m53s |
| CI / pytest (3.10) | CI, run 39897237293 | success, `4668 passed, 3 warnings` | 15m09s |
| CI / pytest (3.12) | CI, run 39897237293 | success, `4668 passed, 3 warnings` | 19m50s |
| package / dist | package, run 39897237384 | success | 1m14s |
| verify-install / linux-x64 | verify-install, run 39897237422 | success, 11 linhas `ok` (1–9b,12); passo 2 em 38 s, passo 12 em 9 s | 2m46s |
| website / build | — | não se aplica (o PR não toca `docs/` nem `website/`) | — |

## Observações (não reprovam)
- R1: a docstring de `manifest_skill_names` está em duas literais concatenadas com `\`; o texto de `__doc__` é o de R1.
- `distinct = tuple(sorted({value for value in found if value is not None}, key=_numeric))` usa o nome `value` em vez de `v` de R5b; semântica idêntica.
- Commit intermediário `1b31c9a` documenta o bloqueio Passo 0 da rodada 1 (antes da ET v2); o head útil é `6d0d232`.
- `mergeStateStatus: BLOCKED` com checks verdes: proteção de branch (review), não falha de CI.
- O CI do `bob / check` roda `crap,dry,deps,mutate` (sem `coverage`); a evidência do `coverage` está no corpo do PR.
- Contagem do pytest: 4620 → 4668 (+48 = 43 + 4 + 1 hermetic).

## Registro
- 23/10/2026 01:22 (UTC-3): rodada contra a v2 (head `6d0d232`, base `040d744` pós-rebase): aprovado para checkpoint, sem desvios. `correction_round` 1 (lacuna Passo 0 da ET; fechada na v2). `traceability.json` (U7 T1 `verified`, PR 203 `open`) atualizado. Status da unit sem mudança (`plan_approved`). O merge é do Emerson.
