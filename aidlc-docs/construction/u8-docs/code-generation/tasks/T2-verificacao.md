# Verificação: ET-u8-docs-T2 (v1) × PR #212
Verificada em 24/10/2026 09:20 (UTC-3) contra `T2.md` (v1, 22/10/2026; SHA base fixado no despacho em 24/10/2026: `465b1056cf1324c00780df42f5659a44ba169358`). Só leituras remotas pelo `gh` / GitHub API (PR, diff, commit, checks, logs de job, conteúdo na ref do head), sem clone nem fetch. Transcript do agente indisponível no box; evidência = corpo do PR + CI + arquivos lidos na ref do head.

PR: https://github.com/fazedordecodigo/bob/pull/212 | branch `aidlc/u8-docs/t2-install-docs` → `main` | head `cb166448d7c943182e5812b97286fde452ecc458` | base `465b1056cf1324c00780df42f5659a44ba169358` | aberto, pronto para revisão (`isDraft: false`, `mergeable: MERGEABLE`), não mergeado | 1 commit (parent `465b105…`, 24/10/2026 07:36:11 UTC-3) | +265/−3, 5 arquivos.
Agente: `bc-4e4a7cab-c610-5478-ab17-30f0e558d956`. `correction_round` 0 (aprovado na 1ª rodada contra a ET v1).

## Veredito: Aprovado para checkpoint
Todos os critérios de aceite, R1–R5 e os 6 testes (28 casos) atendem. Os 7 checks do head estão verdes. Nenhum desvio. O merge é do Emerson.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u8-docs-T2: Docs de instalação: comando único, alternativa e atualizar`; `aidlc/u8-docs/t2-install-docs` → `main`; commit único `cb16644…` com parent `465b1056…` | Atende |
| Fora de rascunho; não mergeado | `state: OPEN`, `isDraft: false`, `mergeable: MERGEABLE` | Atende |
| Passo 0 (12 itens) | corpo: `465b1056…`; `13`; `EXIT:0`; `19 passed in 0.13s`; `60:## Installation (development)`; `60:## Instalação (desenvolvimento)`; `README.md:1`, `README.pt-BR.md:1`; `There are two artifacts. The pip package`; ``Há dois artefatos. O pacote pip `bob-qu``; `7:## Requirements`; `7:## Requisitos`; 4 × `:0` (exit 1 esperado) | Atende |
| Exatamente 5 arquivos; nenhum proibido | `README.md` (+28/−1), `README.pt-BR.md` (+28/−1), `docs/getting-started/installation.md` (+32/−1), `website/i18n/pt-BR/…/getting-started/installation.md` (+32/−1), `tests/test_docs_pins.py` (+145/−0). Sem `docs/install-prompt.*`, `agents.md`, `pre-push.md`, `website/*.js`, `scripts/**`, `src/**`, `CHANGELOG.md` | Atende |
| R1 + R2 blocos e links | conferido no box contra a ET: o texto `Bloco en`/`Bloco pt-BR` (com `{link}` trocado) + linha em branco aparece byte a byte logo antes de `## Installation (development)` (README, link `docs/install-prompt.en.md`), `## Instalação (desenvolvimento)` (README.pt-BR, `docs/install-prompt.pt-BR.md`), `## Requirements` (installation en, `../install-prompt.en.md`, seguido de "Dev en") e `## Requisitos` (installation pt-BR, `/install-prompt.pt-BR.md`, seguido de "Dev pt-BR") | Atende |
| R3 linha 7 dos READMEs | única linha `-` = linha CLI antiga; linha 7 no head = `… doctor \| setup \| update`)` | Atende |
| R4 linha 5 + Dev | linha 5 dos 2 `installation.md` = texto exato da ET; única linha `-` = linha 5 antiga; "Dev en"/"Dev pt-BR" + linha em branco antes do título de requisitos | Atende |
| R5 nada mais muda | linhas `+` de cada doc = exatamente bloco (+ Dev) + linha nova (comparação de multiconjunto = True); linhas `-` = 1 por doc | Atende |
| Helpers/constantes | no fim de `tests/test_docs_pins.py`, na ordem: `_ONE_LINER` (2 literais), `_I18N`, `_INSTALL_DOCS` (4, na ordem), `_OTHER_DOCS` (4), `_ALL_DOCS`, `_FENCE`, `_SHELL`, `_HEADS`, `_ALT` (texto exato quebrado), `_PYTHON_FLOOR`, `_doc_lang`, `_doc_text`, `_one_liner`, `_shell_blocks`, `_line_at`, `_requires_python` | Atende |
| 6 testes, nomes exatos, 28 casos | `test_install_docs_start_with_the_one_liner`, `test_alternative_comes_after_the_one_liner_once`, `test_alternative_links_the_prompt_in_the_doc_language`, `test_update_section_shows_update_and_version`, `test_install_docs_cite_the_pinned_requirements` (4 casos cada, ids = caminho) e `test_docs_cite_only_the_pinned_versions` (8). Asserções conforme a tabela da ET | Atende |
| Testes existentes intactos; sem skip | 0 linhas `-` em `tests/`; sem skip/only/xfail | Atende |
| `test_docs_pins.py`: 47 passed; +hermetic 53 | CI pytest 3.10 e 3.12: 47 pontos em `tests/test_docs_pins.py`; corpo `53 passed in 2.38s` | Atende |
| Colunas | `grep '^+[^+]' \| awk 'length > 101'` em `tests/` do diff → `0` | Atende |
| Suíte inteira | CI 3.10 `4852 passed, 3 warnings` (19m43s) e 3.12 `4852 passed, 3 warnings` (13m59s) = 4824 + 28; 0 failed, 0 errors | Atende |
| `bob check` exit 0; 0 waivers novos | corpo: `EXIT:0`, crap/dry/deps/mutate/coverage, diff coverage 100%, 0 waivers; CI `bob / check` pass | Atende |
| `website / build` (link `/install-prompt.pt-BR.md`) | corpo `EXIT:0`, 14 testes; CI `website / build` pass 2m48s | Atende |
| 7 checks verdes | tabela abaixo | Atende |
| Corpo do PR | Resumo, Passo 0, Arquivos, Testes, Comandos, `## Decisões tomadas: nenhuma`, `## Bloqueios`; referências U8, CT2, CT17, CT18, ADR 0028, ADR 0029, FR8.1–FR8.5 | Atende |

## Checks no head `cb166448d7c943182e5812b97286fde452ecc458`
| Check | Run / job | Resultado | Duração |
|---|---|---|---|
| bob / check | 40091125379 / 120863838939 | pass | 12m27s |
| bob / cold | 40091125379 / 120863838739 | pass | 38s |
| CI / pytest (3.10) | 40091125351 / 120863838757 | pass, 4852 passed | 20m18s |
| CI / pytest (3.12) | 40091125351 / 120863838949 | pass, 4852 passed | 14m29s |
| package / dist | 40091125363 / 120863838816 | pass | 39s |
| verify-install / linux-x64 | 40091125354 / 120863838707 | pass | 2m17s |
| website / build | 40091125346 / 120863838645 | pass | 2m48s |

## Observações (não reprovam)
- Em "Bloqueios" o corpo diz "Nenhum no código" e que a suíte local (`python -m pytest -q`) seria colada depois; a 1ª corrida local deu 12 falhas por falta de `uv`/gitleaks no ambiente do agente. A evidência que vale é o CI (skill, passo 8): 4852 passed em 3.10 e 3.12.
- `bob / check` no CI roda `crap,dry,deps,mutate`; `coverage` vem do corpo.
- Pytest local não rodou no box (sem pytest).

## Registro
- 24/10/2026 09:20 (UTC-3): 1ª rodada contra a ET v1 (head `cb16644…`, base `465b105…`): aprovado para checkpoint, sem desvios (`correction_round` 0). `traceability.json` atualizado (U8 T2 `verified_awaiting_checkpoint`). O merge é do Emerson.
