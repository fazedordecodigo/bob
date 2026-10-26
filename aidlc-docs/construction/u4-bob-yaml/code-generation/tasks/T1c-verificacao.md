# Verificação: ET-u4-bob-yaml-T1c (v1) × PR #199
Verificada em 22/10/2026 08:25 (UTC-3) contra `T1c.md` (v1, base `main` @ `bb08a2c`). Só leituras remotas, sem clone nem fetch: API pública do GitHub por curl, `raw.githubusercontent.com` (5 arquivos e `CHANGELOG.md` no head e na base) e cursor-github (check runs, workflow run e logs dos jobs).

PR: https://github.com/fazedordecodigo/bob/pull/199 | branch `aidlc/u4-bob-yaml/t1c-docs-no-code` → `main` | head `3a49309e2c53f16e393e516c3b32664da2bfdb92` | base `bb08a2c0fd2ceed93223c3f4cd052b86b7cce5de` | aberto, pronto para revisão (`draft: false`), não mergeado, `mergeable: true` (`mergeable_state: clean`) | 1 commit, +14/−0, 5 arquivos.
Commit: `3a49309` (22/10 06:59 UTC-3, pai `bb08a2c`); PR aberto em 22/10 07:53 (UTC-3). Agente: `bc-fcc12763-56b3-5f33-8e48-3b1c33793083`.

## Veredito: Aprovado para checkpoint
Os 10 critérios de aceite, R1–R3 e os textos D1–D7 atendem. Os 7 checks do head estão verdes. Nenhum desvio. 0 rodadas de correção. O merge é do Emerson.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u4-bob-yaml-T1c: Documentar o not_run "no code to measure" com exit 0`; `aidlc/u4-bob-yaml/t1c-docs-no-code` → `main`; `base.sha` = `bb08a2c…` (a da ET); pai do commit = `bb08a2c` | Atende |
| Passo 0 com as 3 linhas | corpo, "Passo 0", sobre `bb08a2c…`: `89:    "check.no_code": "no code to measure",`, `497:    "check.no_code": "nenhum código a medir",`, `47:_NEEDS_CODE = ("crap", "coverage")` | Atende |
| Exatamente 5 arquivos, só adições | `pulls/199/files`: `docs/exit-codes.md` +4/−0, `website/i18n/pt-BR/…/exit-codes.md` +4/−0, `docs/adr/0003-exit-codes.md` +2/−0, `README.md` +2/−0, `README.pt-BR.md` +2/−0; `diff` base × head dos 5 arquivos na box só com linhas `>`; o corpo traz o mesmo `numstat` | Atende |
| D1 | `docs/exit-codes.md`: âncora `An unknown gate name is \`not_run\` and contributes \`0\`.` na l.19; l.20 vazia; l.21 = D1; l.22 vazia | Atende |
| D2 | `docs/exit-codes.md`: âncora "A warning-only gate (`cognitive`, `test_smells`, `dead_code`) … in fail mode too." na l.100 (98 na base, +2 do D1); l.101 vazia; l.102 = D2; l.103 vazia | Atende |
| D3 | espelho pt-BR: âncora `Um nome de gate desconhecido é \`not_run\` e contribui com \`0\`.` na l.19; l.21 = D3, l.20 e l.22 vazias | Atende |
| D4 | espelho pt-BR: âncora "Um gate só de aviso (`cognitive`, …) … também no modo fail." na l.100; l.102 = D4, l.101 e l.103 vazias | Atende |
| D5 | `docs/adr/0003-exit-codes.md`: âncora `Um nome de gate desconhecido grava \`not_run\` e contribui 0. O processo pode sair 0.` na l.30; l.32 = D5, l.31 e l.33 vazias | Atende |
| D6 | `README.md`: âncora `When more than one gate fails, \`bob check\` exits with the highest code.` na l.154; l.156 = D6, l.155 e l.157 vazias | Atende |
| D7 | `README.pt-BR.md`: âncora `Quando mais de um gate falha, \`bob check\` sai com o código mais alto.` na l.154; l.156 = D7, l.155 e l.157 vazias | Atende |
| Texto byte a byte | script na box: cada D extraído da tabela da ET (sem as crases duplas de fora) comparado em bytes UTF-8 com a linha N+2 do arquivo do head: 7/7 iguais. O ⏭️ de D1, D3, D6 e D7 é `U+23ED U+FE0F`, com o seletor de variação, na ET e no arquivo. As crases simples internas são iguais. Cada parágrafo fica numa linha só | Atende |
| Nenhum título, link ou âncora novo ou mudado (R2) | script na box, base × head dos 5 arquivos: linhas que começam com `#` iguais; links `](…)`, `<a …>`, `{#…}` e URLs iguais. Os 7 parágrafos não têm link | Atende |
| `CHANGELOG.md` intocado (R3) | fora de `pulls/199/files`; `cmp` base × head: idêntico | Atende |
| Nenhum outro arquivo (proibidos) | nada em `src/`, `tests/`, `skills/`, `scripts/`, `website/` (fora do espelho) nem `aidlc-docs/` | Atende |
| Suíte inteira 0 failed, 0 errors; os 2 testes de docs sem edição | CI: `4520 passed, 3 warnings` em 3.10 (1124 s) e 3.12 (724 s), igual à `main` (o PR não toca teste); `test_gate_publications.py` e `test_skills_contract.py` sem hunk; corpo: `16 passed` nos dois e `4520 passed` na suíte | Atende |
| `website`: `npm ci`, `npm run build`, `npm test` exit 0 | job `website / build` (workflow `website`, `.github/workflows/website.yml`, `pull_request`, run 39766527969): `[SUCCESS] Generated static files in "build".` e `… "build/pt-BR".`; `# tests 14`, `# pass 14`, `# fail 0`, nenhum `not ok`, `[WARNING]` ou `[ERROR]` | Atende |
| `bob check … crap,dry,deps,mutate,coverage` → 0 | corpo: exit 0, 5 gates `passed`; comentário do `bob` (CI, `crap,dry,deps,mutate`, commit `3a49309`): 4 ✅, "No surviving mutants", "No mutants without tests"; os 16 waivers são de 2026-10-11 (nenhum novo) | Atende |
| 7 checks verdes no head | tabela abaixo: os 6 obrigatórios e `website / build` em `success` | Atende |
| Corpo do PR | Resumo, Passo 0, Arquivos, Textos (D1–D7 com N e linhas vazias), Comandos (com o fim do `npm`), `## Decisões tomadas: nenhuma`, `## Bloqueios` "Nenhum."; Referências: U4, T1b, "Q1 = A, Emerson, 2026-10-20 21:18 UTC-3", "Decisão de 21:42 (UTC-3): … com a T1c separada para a E4", CT1, CT7, ADR 0015, `docs/adr/0003-exit-codes.md` | Atende |
| Não mergeado pelo agente | `state: open`, `merged: false`, `merged_by: null` | Atende |

## Checks no head `3a49309` (início 22/10 07:53 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| bob / check | bob, run 39766527976 | success | 11m58s |
| bob / cold | bob, run 39766527976 | success | 1m17s |
| CI / pytest (3.10) | CI, run 39766528061 | success, `4520 passed, 3 warnings` | 20m03s |
| CI / pytest (3.12) | CI, run 39766528061 | success, `4520 passed, 3 warnings` | 12m55s |
| package / dist | package, run 39766528145 | success | 0m57s |
| verify-install / linux-x64 | verify-install, run 39766527997 | success, 9 linhas `ok`, passo 5 em 7 s | 3m51s |
| website / build | website, run 39766527969 | success, build en e pt-BR, 14/14 testes | 2m25s |
| Graphify Formal Verification | externo (graphify-labs) | neutral; não exigido | — |

## Observações (não reprovam)
- O `npm ci` do `website / build` mostra "28 high severity vulnerabilities". É o resultado do `npm audit` das dependências já existentes do site; o PR não toca `package.json` nem o lockfile.
- O corpo cita `32 subtests passed` nas corridas locais; o CI não mostra subtests. A contagem de casos (4520) é a mesma.
- `mergeable_state: clean`: sem conflito e sem bloqueio de proteção no momento da consulta.

## Registro
- 22/10/2026 08:25 (UTC-3): rodada 1 (head `3a49309`): aprovado para checkpoint, sem desvios. `traceability.json` (U4 T1c `verified`, PR 199 `open`) e `trace.md` atualizados. O merge é do Emerson.
