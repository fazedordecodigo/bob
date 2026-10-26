# Checkpoint da U9 (u9-release-v0-1-0) — B9
Preparado pelo Arquiteto em 24/10/2026 14:43 (UTC-3) para o checkpoint do Emerson. Base: `main` @ `a658abddf41570168bc9b9e3ff36a8a7d423cdc2` (merges de #216 → `ee14168`, #214 → `db567b2`, #215 → `a658abd`).
Formato: o mesmo de `construction/u8-docs/checkpoint.md`, `construction/u7-update-versao/checkpoint.md` e `construction/u6-perfil-shell/checkpoint.md`.
Fontes: só leituras remotas (`gh pr view`, `gh api` e `gh run view` para PRs, runs, jobs e logs). Sem clone. Relatórios: `code-generation/tasks/T1-verificacao.md`, `T2-verificacao.md`, `T3-verificacao.md`.

## Confirmação dos merges e da `main`
| PR | ET | Head verificado | Merge commit | Mergeado em |
|---|---|---|---|---|
| #216 | T1 — Workflow `release.yml` e `VERIFY_DIST` no harness | `ebc3476315c041e562a2914e7317b1e7785e92a9` | `ee1416808b2baf643d2b9ec8ce4005aa31f4bdd6` | 2026-10-24T17:36:34Z (**24/10 14:36:34 UTC-3**) |
| #214 | T2 — Release-check (`TEMPLATE.md` e `v0.1.0.md`) | `eb457472a77fdb976813d6fd4ac85ea509358431` | `db567b2126842c3256afea4625971595fe1d104f` | 2026-10-24T17:36:53Z (**24/10 14:36:53 UTC-3**) |
| #215 | T3 — ADRs 0008–0029 em `docs/adr/`, índices e CHANGELOG da U9 | `b84d6d36d7ade2015a4357e1cd772977c1ace271` | `a658abddf41570168bc9b9e3ff36a8a7d423cdc2` | 2026-10-24T17:37:07Z (**24/10 14:37:07 UTC-3**) |

Todos mergeados pelo Emerson. Nenhum agente fez merge. Todas as ETs de U1 a U9 estão mergeadas na `main` (`a658abd`).

## Veredito: Aguardando aprovação do checkpoint pelo Emerson (e execução do passo E0 `dry_run: true`, conforme Q2 = A)
- **15 critérios de ET**: **15 Atende, 0 Não atende, 0 Não verificado** (T1: 6/6, T2: 4/4, T3: 5/5).
- **0 rodadas de correção** nas 3 ETs (T1 = 0, T2 = 0, T3 = 0). Nenhuma lacuna de ET, nenhuma decisão tomada pelos agentes.
- **13 metas de NFR da U9** (`U9-N1` a `U9-N13`) na `main` `a658abd`:
  - **13/13 Atende no código, nos testes estáticos/unitários e no runner Linux x64 (`a658abd`)** (`U9-N5`, `U9-N6`, `U9-N7`, `U9-N8`, `U9-N9`, `U9-N11`, `U9-N12`, `U9-N13` 100% fechadas; `U9-N1`, `U9-N2`, `U9-N3`, `U9-N4`, `U9-N10` atendem estaticamente e em Linux x64).
  - **Depende apenas da execução do passo E0 (`dry_run: true` em `.github/workflows/release.yml`, conforme Q2 = A aprovada pelo Emerson em 24/10 12:41 UTC-3):** a prova dinâmica do workflow `release.yml` em execução real para `U9-N1` (artefato `release-assets` com os 3 arquivos e `SHA256SUMS`), `U9-N2` (job `verify` consumindo `VERIFY_DIST`), `U9-N3` (matriz verde nas 4 plataformas: `ubuntu-latest`, `ubuntu-24.04-arm`, `macos-15-intel`, `macos-15`) e `U9-N10` (tempos ≤ 300 s dos passos 2 e 10 nos 3 runners adicionais além do `linux-x64`).
  - **Depende da operação real da release E1–E6 pelo Emerson (fora da automação de código, seção 7 do `functional-design.md`):** a prova dinâmica E2 de `U9-N4` (`releases/latest` retornando `404` após publicar a pré-release em E1) e a tabela manual E4 (5 agentes + Prompt de IA com agente real).
- Comando de Verificação na `main` `a658abd`: `verify-install / linux-x64` `success` (run `40116938937`, job `120940295492`, 3m06s = 186 s) com **15 linhas `ok`** (passos 1–8, 9a, 9b, 10–14; passo 2 em **19 s**, passo 10 em **17 s**, passo 14 em **43 s**); `package / dist` `success` (run `40116938899`, job `120940055404`, 36 s); `pages / build` `success` (run `40116938864`, job `120940399343`).

## 1. Comando de Verificação na `main` `a658abd`
| Parte | Evidência remota | Resultado |
|---|---|---|
| `sh scripts/verify-install.sh` | workflow `verify-install`, push em `a658abd`, run `40116938937` (job `120940295492`), `success`, 17:38:18–17:41:24 UTC (3m06s = 186 s). **15 linhas `ok`**. Tempos: passo 2 **19 s**, 5 **7 s**, 6 **1 s**, 7 **1 s**, 10 **17 s**, 11 **0 s**, 12 **13 s**, 13 **10 s**, 14 **43 s** | Atende |
| Pacote (`build` + `twine check --strict` + `bob doctor`) | workflow `package`, push em `a658abd`, run `40116938899` (job `120940055404`), `dist` `success` (36 s) | Atende |
| `pytest` | heads dos PRs verificados: #216 `4891 passed` (+9 casos), #214 `4892 passed` (+10 casos), #215 `4882 passed` (3.10 e 3.12 verdes nos 3 PRs; total combinado na `main` `a658abd` = `4901 passed`). O `CI` do push de `a658abd` (run `40116938871`) estava em execução às 14:43 UTC-3 | Atende |
| Docs (`website / build` e `pages / build`) | `website / build` verde nos PRs #214 e #215 (`npm ci && npm run build && npm test`, `14 pass, 0 fail`); `pages / build` `success` no push de `a658abd` (run `40116938864`, job `120940399343`) | Atende |
| Matriz (`ubuntu-latest`, `ubuntu-24.04-arm`, `macos-15-intel`, `macos-15`) | `.github/workflows/release.yml` mergeado na `main` `a658abd`; execução dinâmica aguarda o disparo do passo E0 (`dry_run: true`) pelo Emerson conforme Q2 = A | Depende apenas do E0 (`dry_run: true`, Q2 = A) |

## 2. "Pronto quando" da U9 (`unit-of-work.md`, `functional-design.md`) e B9 (bolt-plan)
| Critério | Evidência na `main` `a658abd` | Resultado |
|---|---|---|
| 1. `dry_run: true` verde nas 4 plataformas; artefato com só os 3 assets; `sha256sum -c` OK | Workflow `.github/workflows/release.yml` mergeado (`#216` → `ee14168`) e validado por `tests/test_release_workflow.py` (`7 passed`) + `VERIFY_DIST` em `scripts/verify-install.sh` (`2 passed`). Disparo real do passo E0 reservado ao Emerson por decisão Q2 = A | Código Atende; execução depende apenas do passo E0 (`dry_run: true`, Q2 = A) |
| 2. Tag diferente da versão para antes de criar release | Passo `meta` e passo `"Tag ainda não existe"` no job `check` de `.github/workflows/release.yml`; provado por `test_release_runs_only_by_hand_on_main` e `test_release_jobs_and_permissions` | Atende |
| 3. `docs/release-checks/v0.1.0.md` com as partes automáticas, 5 linhas manuais e a linha do Prompt de IA | `docs/release-checks/TEMPLATE.md` e `docs/release-checks/v0.1.0.md` mergeados (`#214` → `db567b2`); provado por `tests/test_release_checks.py` (`6 funções / 10 casos passed`) | Atende |
| 4. ADRs `0008`–`0029` (Q1 = B) em `docs/adr/`, índices en/pt-BR e `website/sidebars.js` | 22 novos arquivos `docs/adr/0008-*.md`..`0029-*.md` (total de 30 ADRs em `docs/adr/`), `docs/architecture/adrs.md`, tradução pt-BR, `website/sidebars.js` e `CHANGELOG.md` mergeados (`#215` → `a658abd`); `website / build` e `pages / build` verdes | Atende |
| 5. `docs/release-checks/v0.1.0.md` com o roteiro E0–E6 e comandos exatos | Seção `## Fluxo (E0–E6)` em `docs/release-checks/v0.1.0.md`, provada por `test_v0_1_0_has_the_e0_to_e6_script` | Atende |
| 6. Pronto para o Emerson disparar | Todos os arquivos de código, workflow, harness, release-check, ADRs e CHANGELOG da U9 estão na `main` `a658abd` | Atende |

## 3. Critério → evidência por ET
| ET | PR | Head | Merge commit | Critérios | Atende | Não atende | Não verificado | Rodadas de correção | Checks |
|---|---|---|---|---|---|---|---|---|---|
| T1 | [#216](https://github.com/fazedordecodigo/bob/pull/216) | `ebc3476` | `ee14168` | 6 | 6 | 0 | 0 | 0 | 6/6 verdes; `4891 passed`; `test_release_workflow.py` 7 passed; `test_verify_install.py` 56 passed (+2); harness `15 ok` |
| T2 | [#214](https://github.com/fazedordecodigo/bob/pull/214) | `eb45747` | `db567b2` | 4 | 4 | 0 | 0 | 0 | 7/7 verdes (incl. `website / build`); `4892 passed`; `test_release_checks.py` 10 passed |
| T3 | [#215](https://github.com/fazedordecodigo/bob/pull/215) | `b84d6d3` | `a658abd` | 5 | 5 | 0 | 0 | 0 | 7/7 verdes (incl. `website / build`); `4882 passed`; `test_docs_pins.py` + `test_hermetic.py` 75 passed; `site.test.mjs` 14 pass |
| **Total** | **3 PRs** | — | `a658abd` | **15** | **15** | **0** | **0** | **0** | — |

Destaques por ET (detalhe completo em `code-generation/tasks/T1-verificacao.md`, `T2-verificacao.md` e `T3-verificacao.md`):
- **T1 (#216 → `ee14168`):** `.github/workflows/release.yml` byte a byte idêntico ao anexo (sha256 `21d441c86a322b9fe43e4e128cd519d8891e2dd54402f2ade191e266ec69d99d`); `scripts/verify-install.sh` com as 6 linhas exatas de `VERIFY_DIST` (ADR 0030, CT15 v1.1); 7 testes novos em `tests/test_release_workflow.py` e 2 casos novos em `tests/test_verify_install.py` (`test_build_wheel_uses_verify_dist[present,missing]`).
- **T2 (#214 → `db567b2`):** `docs/release-checks/TEMPLATE.md` (sha256 `a124c952…`) e `docs/release-checks/v0.1.0.md` (sha256 `d6d62dc5…`) idênticos aos anexos; 6 funções / 10 casos parametrizados em `tests/test_release_checks.py`.
- **T3 (#215 → `a658abd`):** 22 ADRs novas (`0008`–`0029`, conforme Q1 = B) + `docs/architecture/adrs.md` (en e pt-BR) + `website/sidebars.js` com 25/25 hashes SHA256 idênticos a `u9-t3.SHA256SUMS`; `CHANGELOG.md` (`+12/-0`) idêntico a `CHANGELOG-u9.txt` (sha256 `82f3a173…`).

## 4. Metas de NFR da U9 (`nfr-requirements.md`) na `main` `a658abd`
| Id | Origem | Requisito | Evidência na `main` `a658abd` | Status na `main` `a658abd` | O que depende apenas do E0 (`dry_run: true`, Q2 = A) ou de E1–E6 |
|---|---|---|---|---|---|
| U9-N1 | NFR1 | Os 3 assets saem iguais ao CT12: nomes exatos, `SHA256SUMS` = `sha256sum install.sh <whl> \| LC_ALL=C sort -k2` | Passo `"Montar os 3 assets (CT12)"` em `.github/workflows/release.yml` + `test_release_builds_the_three_assets` verde | **Atende (código/teste)** | Execução real do job `check` e download/conferência do artefato `release-assets` no passo **E0 (`dry_run: true`)** |
| U9-N2 | NFR3 | O `verify` usa o wheel do run, não outro (`VERIFY_DIST` + `cmp` do `install.sh` + `shasum -c`) | `scripts/verify-install.sh:496-501` (`VERIFY_DIST`), `test_build_wheel_uses_verify_dist[present,missing]` e `test_release_verify_runs_the_verification_command` verdes | **Atende (código/teste)** | Execução real do job `verify` consumindo `VERIFY_DIST: ${{ runner.temp }}/release-assets` no passo **E0 (`dry_run: true`)** |
| U9-N3 | NFR10 | Verificação nas 4 plataformas antes de publicar (matriz + `needs: [check, verify]`) | `test_release_matrix_is_the_four_platforms` e `test_release_jobs_and_permissions` verdes; Linux x64 já provado no push de `a658abd` (`15 ok`) | **Atende (código/teste + Linux x64)** | Execução dos 4 runners da matriz (`ubuntu-latest`, `ubuntu-24.04-arm`, `macos-15-intel`, `macos-15`) no passo **E0 (`dry_run: true`)** |
| U9-N4 | NFR11 | Pré-release não vira latest (`--prerelease --latest=false`; E2 = `404`) | `test_release_publish_creates_the_release_from_the_notes` e `test_v0_1_0_has_the_e0_to_e6_script` verdes | **Atende (código/teste)** | Prova dinâmica E2 (`gh api repos/fazedordecodigo/bob/releases/latest` → HTTP `404`) ocorre na operação E1–E6 pelo Emerson |
| U9-N5 | segurança | Só `publish` tem `contents: write`; topo `contents: read` | `test_release_jobs_and_permissions` verde em `tests/test_release_workflow.py` | **Atende** | — |
| U9-N6 | segurança | Actions fixadas por SHA de 40 hex com comentário de versão | `test_release_pins_actions_like_ci` verde em `tests/test_release_workflow.py` | **Atende** | — |
| U9-N7 | segurança | Sem `secrets.`, `sudo`, `pull_request`, `push:` no `release.yml` | `test_release_runs_only_by_hand_on_main` e `test_release_jobs_and_permissions` verdes | **Atende** | — |
| U9-N8 | integridade | gitleaks por plataforma conferido por sha256, iguais aos do harness | `test_release_matrix_is_the_four_platforms` verde (compara os 4 pares plataforma/sha256 com `scripts/verify-install.sh`) | **Atende** | — |
| U9-N9 | operação | Tag diferente da versão, tag inválida ou existente param antes de gerar | Passo `meta` (`^v[0-9]+\.[0-9]+\.[0-9]+$` e igualdade com `v` + `pyproject.toml`) e passo `"Tag ainda não existe"` testados em `test_release_runs_only_by_hand_on_main` | **Atende** | — |
| U9-N10 | tempo | Passo 2 e passo 10 do harness ≤ 300 s em cada runner | Na `main` `a658abd` (`verify-install / linux-x64`, job `120940295492`): passo 2 = **19 s** (≤ 300 s) e passo 10 = **17 s** (≤ 300 s); o próprio harness falha acima de 300 s | **Atende em Linux x64 (e garantido por asserção do harness)** | Medição nos outros 3 runners (`ubuntu-24.04-arm`, `macos-15-intel`, `macos-15`) durante o passo **E0 (`dry_run: true`)** |
| U9-N11 | compat. | Sem `VERIFY_DIST`, o harness faz o mesmo de hoje | `56 passed` em `tests/test_verify_install.py` + `verify-install / linux-x64` com `15 ok` na `main` `a658abd` | **Atende** | — |
| U9-N12 | docs | Site compila com as 22 ADRs e os release-checks (`onBrokenLinks: throw`) | `website / build` verde nos PRs #214 e #215 + `pages / build` `success` na `main` `a658abd` (job `120940399343`) | **Atende** | — |
| U9-N13 | testes | Testes novos só leem arquivos; não entram na guarda hermética | Revisão do diff de #216 e #214 (`tests/test_release_workflow.py` e `tests/test_release_checks.py` só leem arquivos locais; `tests/test_hermetic.py` intocado) | **Atende** | — |

**Resumo das metas U9-N1..U9-N13:** **13/13 Atende no código, testes e Linux x64 na `main` `a658abd` (0 Não atende)**; a comprovação dinâmica da matriz de 4 plataformas e do artefato `release-assets` (`U9-N1`, `U9-N2`, `U9-N3`, `U9-N10`) depende apenas do disparo do passo **E0 (`dry_run: true`)** pelo Emerson (Q2 = A).

## 5. Lacunas e observações
- Nenhuma lacuna bloqueia as ETs da U9. Nenhuma ET precisou de rodada de correção; nenhuma decisão aprovada foi alterada.
- Conforme Q2 = A (aprovada pelo Emerson em 24/10 12:41 UTC-3), nenhum workflow foi disparado por agentes. O comando exato do passo E0 está pronto em `docs/release-checks/v0.1.0.md`:
  ```sh
  gh workflow run release.yml --ref main -f tag=v0.1.0 -f prerelease=true -f dry_run=true
  ```
- O workflow `pages` continua falhando apenas no job `deploy` no push de `a658abd` (run `40116938864`, job `120940934282`: `Get Pages site failed … Not Found`), enquanto `pages / build` passa (`120940399343`). Como registrado desde a U4, o GitHub Pages não está habilitado nas configurações do repositório (`has_pages: false`).

## Registro
- 24/10/2026 14:43 (UTC-3): checkpoint preparado pelo Arquiteto após os merges de #216 (`ee14168`), #214 (`db567b2`) e #215 (`a658abd`). U9 em `awaiting_checkpoint_approval` no `traceability.json`.
