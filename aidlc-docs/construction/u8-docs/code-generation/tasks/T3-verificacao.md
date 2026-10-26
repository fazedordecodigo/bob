# Verificação: ET-u8-docs-T3 (v1) × PR #213
Verificada em 24/10/2026 11:40 (UTC-3) contra `T3.md` (v1, 22/10/2026; base no despacho: `d30080723d5cc79e8868940effe619bda08c4863`, main após #211 U8 T4 e #212 U8 T2). Só leituras remotas pelo `gh` / GitHub API (PR, diff, commits, checks, logs de job, conteúdo na base e no head), sem clone. Evidência = corpo do PR + CI + arquivos lidos na base e no head e comparados no box contra os blocos da ET.

PR: https://github.com/fazedordecodigo/bob/pull/213 | branch `aidlc/u8-docs/t3-agents-hook-docs` → `main` | head `0f88870b4ec128f942d4ab7ed5aef92ebaf75466` | base `d30080723d5cc79e8868940effe619bda08c4863` | aberto, `isDraft: false`, `mergeable: MERGEABLE`, não mergeado | 1 commit (parent `d300807…`, 24/10/2026 10:48:56 UTC-3) | +111/−208, 8 arquivos.
Agente: `bc-dc052d84-17fe-5c43-b436-e983570bf8a2`. `correction_round` 0.

## Veredito: Aprovado para checkpoint
Todos os critérios, R1–R8 e os 4 testes (22 casos) atendem. 7/7 checks verdes. Nenhum desvio. O merge é do Emerson.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch, base | `ET-u8-docs-T3: Docs dos agentes e do hook a partir do comando único`; base `d300807…` (commit do squash da #212); commit único com parent na base | Atende |
| Fora de rascunho; não mergeado | `OPEN`, `isDraft: false`, `MERGEABLE` | Atende |
| Q1 = A citada com data | corpo: `Q1 = A (2026-10-22 / 2026-10-23)` | Atende |
| Passo 0 (11 itens) | `d300807…`; `EXIT:0`; `47 passed in 0.17s`; `79`; `79`; ``The script `src/bob_quality/ho`` e ```` ``` ````; ``O script `src/bob_quality/hook`` e ```` ``` ````; `99/139/346/355` en; `99/139/346/355` pt-BR; `README.md:1`, `README.pt-BR.md:1`; `# Changelog`, vazio, `## Unreleased`, vazio | Atende |
| Exatamente 8 arquivos; nenhum proibido | `CHANGELOG.md` +11/−0, `README.md` +2/−41, `README.pt-BR.md` +2/−41, `docs/getting-started/agents.md` +17/−60, `docs/guides/pre-push.md` +4/−3, `tests/test_docs_pins.py` +54/−0, `…/pt-BR/…/agents.md` +17/−60, `…/pt-BR/…/pre-push.md` +4/−3. Sem `docs/publishing.md`, `.claude-plugin/**`, `.cursor-plugin/**`, `docs/install-prompt.*`, `installation.md`, `docs/adr/**`, `src/**`, `scripts/**`, `website/*.js` | Atende |
| R1 / R2 | os 2 `agents.md` no head são byte a byte "Agents en" e "Agents pt-BR" (igualdade = True) | Atende |
| R3 / R4 | head = base linhas 1–4 + "Hook en/pt-BR" + base a partir da linha 11 (`The script is:` / `O script é:` em diante sem mudança): igualdade = True nos 2 | Atende |
| R5 / R6 | head = base com corpo entre os títulos trocado por linha em branco + "README agents" + linha em branco, e o bloco `cp` de 4 linhas de `## Pre-push hook` / `## Hook pre-push` trocado por "README hook": igualdade = True nos 2. Linha 7 (T2), `## Skills` e títulos preservados | Atende |
| R7 CHANGELOG | parágrafos en e pt-BR com texto exato, logo após `## Unreleased` + linha em branco, acima dos da T4 (R-CL); resto do arquivo idêntico à base; quebra gulosa recalculada no box = True; larguras 97/72/99/95/5 e 99/76/99/95 bytes | Atende |
| R8 | as 3 checagens de igualdade acima cobrem os arquivos inteiros: nenhuma outra linha mudou | Atende |
| Constantes | `_NOT_BEFORE`, `_AGENT_ROWS`, `_AGENTS` exatos, no fim do arquivo | Atende |
| 4 testes, 22 casos | `test_agent_and_hook_docs_start_with_the_one_liner` (4), `test_no_clone_or_plugin_before_the_one_liner` (8), `test_bob_version_only_in_the_release_check_note` (8), `test_agents_doc_names_the_single_folder_and_ra1` (2); asserções conforme a ET; 0 linhas removidas em testes; sem skip/xfail | Atende |
| `test_docs_pins.py` 69; +hermetic 75 | CI 3.10 e 3.12: 48 + 21 = 69 pontos; corpo `69 passed`, `75 passed in 2.48s` | Atende |
| Colunas | linhas `+` de `tests/` e `CHANGELOG.md` com `awk 'length > 101'` → `0` | Atende |
| Suíte inteira | CI 3.10 e 3.12: `4882 passed, 3 warnings` (4860 + 22); corpo `4882 passed`; 0 failed, 0 errors | Atende |
| `bob check`; 0 waivers novos | corpo `EXIT:0`, 5 gates passed, diff coverage 100%; `.bob/waivers.yaml` fora do diff; CI `bob / check` pass | Atende |
| 7 checks verdes | tabela abaixo | Atende |
| Corpo do PR | Resumo, Passo 0, Arquivos, Testes, Comandos, `## Decisões tomadas: nenhuma`, `## Bloqueios` (Nenhum); U8, CT17, ADR 0028, ADR 0029, FR1.2, FR1.3, FR3.2, RA1, Q1 = A | Atende |

## Checks no head `0f88870b4ec128f942d4ab7ed5aef92ebaf75466`
| Check | Run / job | Resultado | Duração |
|---|---|---|---|
| bob / check | 40101125467 / 120893311961 | pass | 13m29s |
| bob / cold | 40101125467 / 120893311865 | pass | 30s |
| CI / pytest (3.10) | 40101125451 / 120893311737 | pass, 4882 passed | 20m51s |
| CI / pytest (3.12) | 40101125451 / 120893311940 | pass, 4882 passed | 16m56s |
| package / dist | 40101125483 / 120893311861 | pass | 31s |
| verify-install / linux-x64 | 40101125555 / 120893312085 | pass | 2m08s |
| website / build | 40101125468 / 120893311667 | pass | 2m51s |

## Observações (não reprovam)
- O "Before" do `bob check` local falhou por ambiente (gitleaks em `BOB_HOME/bin`, sem `uvx`); o "After" e o CI estão verdes.
- `bob / check` no CI roda `crap,dry,deps,mutate`; `coverage` vem do corpo.

## Registro
- 24/10/2026 11:40 (UTC-3): 1ª rodada contra a ET v1: aprovado para checkpoint, sem desvios. `traceability.json` atualizado (U8 T3 `verified_awaiting_checkpoint`). O merge é do Emerson.
