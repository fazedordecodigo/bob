# U8 — u8-docs — Plano de geração de código

Bolt: B8 (U8) | Base do desenho: `main` @ `22d461a60920ab13e7b09fd654fd0e4686ba14d0` | Profundidade: spec | Data: 2026-10-22 (UTC-3)
**Despacho só depois dos merges da U6 e da U7** (bolt-plan; aprovação do Emerson: "U6 e U7 em paralelo, com o desenho da U8 junto e o despacho dela depois dos merges da U6 e da U7"). Nada foi despachado.
Aprovação do plano: **aprovado pelo Emerson** (U8 Q1 = A; despacho autorizado após os merges da U6 T3 e da U7 T3). Base da T1 fixada em `4d1603323ddc13714fa50b5e98487cb0957c7f20` (#208 U7 T3 mergeada; T1 mergeada no #209 → `465b1056cf1324c00780df42f5659a44ba169358`). Base da T2 e da T4 fixada em `465b1056cf1324c00780df42f5659a44ba169358` (#210 U6 T4 → `3ced2ce30193ac90035d374ec62f38d86bd63f34` e #209 U8 T1 → `465b1056cf1324c00780df42f5659a44ba169358` mergeadas), com todas as âncoras reconferidas.
Desenho: `../functional-design.md` (P1–P4, D1–D9, passo 14), `../nfr-requirements.md` (U8-N1–N13), `../nfr-design.md`.
ADRs propostas: 0021, 0026, 0027, 0028 e 0029, em `../../u6-u7-decisions-proposta.md`. Ainda não estão no `decisions.md`.
**Pergunta de produto aberta:** `../functional-design-questions.md` Q1 (instruções de plugin nos docs de usuário). **A T3 só é despachada com Q1 = A** (recomendação). Outra resposta gera a T3 v2. A T1, a T2 e a T4 não dependem dela.

## Âncoras a reconferir antes do despacho
Lidas em `22d461a` (leitura remota, sem clone). O arquiteto reconfere na `main` pós-U6/U7, e o passo 0 de cada ET as prende com resultado numérico.
- `scripts/install.sh`: linhas 4-5 (`STEPS` com `perfil`, `PROFILE_LINE`; vêm da U6 T1); as 3 linhas com `BOB_VERSION`; `CURL_OPTS`/`PIP_OPTS` (linhas 8-9 depois da U6).
- `tests/test_hermetic.py`: `_UNIT_ARGS` na forma de R-HE (4 itens).
- `README.md`/`README.pt-BR.md`: `## Installation (development)` / `## Instalação (desenvolvimento)` na linha 60; linha 7 (`- CLI:`). A U6 e a U7 não tocam os READMEs.
- `scripts/verify-install.sh`: linhas 2 e 4 na forma de R-VI1 (`… 12 13`); `release_pair`, `run_oneliner` (com os argumentos 10 e 11 da U6), `run_bob` (U7), `step_13`, `run_selected`, `NEW_WHL=`, `      13) step_13 ;;`. A T4 cita tudo por conteúdo.
- `tests/test_verify_install.py`: 46 casos (R-TV); `_HELP`, `test_step_ids_are_the_known_steps`, os 2 parâmetros de `Passos:`, `test_run_oneliner_passes_shell_and_bob_home` (U6), `test_run_bob_builds_the_environment` (U7), `test_profile_line_comes_from_install_sh` (último da U6).
- `CHANGELOG.md`: `## Unreleased` no topo, com as entradas da U6 e da U7.

## Resumo
- **Constrói:**
  - o prompt de IA sem `install.sh` (CT18), em `docs/install-prompt.en.md` e `docs/install-prompt.pt-BR.md`;
  - os 8 docs a partir do comando único, com a alternativa e a seção de atualizar (CT17);
  - o teste de paridade e de pins `tests/test_docs_pins.py`;
  - o passo 14 do harness (CT15), com `pass_env`.
- **Toca:**
  - T1: os 2 prompts (novos, cópia do anexo `tasks/T1-anexo/docs/`), `tests/test_docs_pins.py` (novo), `tests/test_hermetic.py`;
  - T2: `README.md`, `README.pt-BR.md`, `docs/getting-started/installation.md`, `website/i18n/pt-BR/docusaurus-plugin-content-docs/current/getting-started/installation.md`, `tests/test_docs_pins.py`;
  - T3: `docs/getting-started/agents.md`, `docs/guides/pre-push.md`, as 2 traduções pt-BR deles, `README.md`, `README.pt-BR.md`, `tests/test_docs_pins.py`, `CHANGELOG.md`;
  - T4: `scripts/verify-install.sh`, `tests/test_verify_install.py`, `CHANGELOG.md`.
- **Testes:**
  - T1: 13 testes (19 casos); guarda +1 (`test_hermetic.py`: 5 → 6);
  - T2: 6 testes (28 casos), 19 → 47;
  - T3: 4 testes (22 casos), 47 → 69;
  - T4: 5 testes (8 casos) e 5 ajustes. `test_verify_install.py`: 46 → 54.
  - O arquiteto rodou os testes da T1, da T2 e da T3 contra os docs de `22d461a` com as mudanças das ETs aplicadas numa cópia local (não é clone; arquivos lidos por leitura remota): 19, 47 e 69 passed. Também rodou as funções `pass_env`, `prompt_blocks` e `manifest` da T4 contra os casos dela.
  - Harness: passo 14; 15 linhas `ok`.

## Decisões fechadas
| # | Decisão | Origem |
|---|---|---|
| D1 | Prompt = anexo da T1, cópia byte a byte (sha256 na ET). Blocos iguais em en e pt-BR. Só o `perfil` difere do CT18: `R="already-marked:$F"` (ADR 0021) e `S=${SHELL:-}` (bug com `set -u` e `SHELL` ausente; ADR 0029). | ADR 0021, 0029 |
| D2 | 8 docs, com a tradução pt-BR do site no lugar de `docs/instalacao.md`. Links: `docs/install-prompt.<lang>.md` nos READMEs, `../install-prompt.en.md` no en do site, `/install-prompt.pt-BR.md` no pt-BR do site. | ADR 0028 |
| D3 | "Bloco de shell" = info string `bash`, `sh`, `shell` ou `console`. Seção `## Update` / `## Atualizar` com `bob update` e `bob --version`. | ADR 0029 |
| D4 | `test_docs_pins.py` lê os pins pelas funções do pacote e o `install.sh` pelas linhas `NOME='…'`. Sem rede; entra na guarda. | ADR 0029, CT17 |
| D5 | Q1 = A (pendente): tirar as instruções de plugin dos docs de usuário; `docs/publishing.md` e os manifestos ficam. | Q1 |
| D6 | Passo 14: A (`run_oneliner`) × B (blocos do prompt en, filtrados pela plataforma), manifesto igual, B2 sem mudança. Sem `SHELL` nos dois (perfil em `~/.profile`). `npm_config_cache` compartilhado. "Não se aplica" com `VERIFY_REMOTE=1`. ≤ 360 s. | ADR 0026, 0028, 0029, CT15 |
| D7 | `pass_env` substitui os 2 laços de repasse (U6 `run_oneliner`, U7 `run_bob`) e serve ao `run_blocks`. | ADR 0028 |
| D8 | `CHANGELOG.md` só na T3 e na T4. A que entra depois põe os parágrafos dela no topo (R-CL). | ADR 0027, 0029 |
| D9 | Checks exigidos: os 6 (`bob / check`, `bob / cold`, `CI / pytest (3.10)`, `CI / pytest (3.12)`, `package / dist`, `verify-install / linux-x64`). Na T1, na T2 e na T3 entra também `website / build`, porque tocam `docs/**` ou `website/**`. | bolt-plan |

## Testing Contract
| Pronto / requisito | Prova automática | Onde |
|---|---|---|
| FR8.1 / CT17: comando único primeiro nos 8 docs | `test_install_docs_start_with_the_one_liner[4]`, `test_agent_and_hook_docs_start_with_the_one_liner[4]` | T2, T3 |
| FR8.2: requisitos e versões reais | `test_install_docs_cite_the_pinned_requirements[4]`, `test_docs_cite_only_the_pinned_versions[8]` | T2 |
| FR8.3: atualizar e ver a versão | `test_update_section_shows_update_and_version[4]` | T2 |
| FR8.4 / CT17: ordem principal → alternativa, link no idioma | `test_alternative_comes_after_the_one_liner_once[4]`, `test_alternative_links_the_prompt_in_the_doc_language[4]` | T2 |
| FR1.2, FR1.3: nada de clone nem plugin antes do comando | `test_no_clone_or_plugin_before_the_one_liner[8]`, `test_agents_doc_names_the_single_folder_and_ra1[2]` | T3 |
| FR3.2 / RA1: pasta única nos agentes | `test_agents_doc_names_the_single_folder_and_ra1[2]` | T3 |
| CT18 paridade (11 itens), FR1.6, FR1.8, FR8.5 | os 13 testes da T1 (19 casos) | T1 |
| NFR11: sem `install.sh` nem `sudo` | `test_prompt_blocks_never_use_install_sh_or_sudo`; passo 14 (pedidos exatos e `sudo.log`) | T1, T4 |
| NFR10, FR1.7: mesmo resultado | passo 14 (manifesto A = B; B2) | T4 |
| FR1.4: `BOB_VERSION` só na nota | `test_bob_version_is_read_only_in_the_prompt[2]`, `test_install_sh_mentions_bob_version_only_when_invalid`, `test_bob_version_only_in_the_release_check_note[8]` | T1, T3 |
| Site sem link quebrado | check `website / build` | T1–T3 |
| Hermeticidade | `test_u5_tests_open_no_network[tests/test_docs_pins.py]` | T1 |
| Qualidade | checks do PR + `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → 0 | T1–T4 |

## Passos
- [x] P1 — os 2 prompts, cópia do anexo (T1, #209 → `465b105`).
- [x] P2 — `tests/test_docs_pins.py` (paridade do CT18) e a guarda (T1, #209 → `465b105`).
- [ ] P3 — os 4 docs de instalação e os testes de ordem, link, atualizar e pins (T2).
- [ ] P4 — `agents.md` e `pre-push.md` (en e pt-BR), as 2 seções dos READMEs, os testes D2/D7/D8 e o `CHANGELOG.md` (T3; Q1 = A).
- [ ] P5 — `scripts/verify-install.sh`: `pass_env` e passo 14; `tests/test_verify_install.py`; `CHANGELOG.md` (T4).
- [ ] P6 — verificação da unit: harness inteiro verde (15 `ok`) e `website / build` verde na `main`; checkpoint da U8 com o Emerson.

## Tarefas
| Tarefa | ET | Passos | Base | Branch | Depende de |
|---|---|---|---|---|---|
| T1 — Prompt de IA sem install.sh e teste de paridade | `tasks/T1.md` (+ `tasks/T1-anexo/docs/`) | P1, P2 | `main` @ `4d1603323ddc13714fa50b5e98487cb0957c7f20` (#208) | `aidlc/u8-docs/t1-prompt` | U6 T1 (`perfil`, `PROFILE_LINE`); U7 inteira |
| T2 — Docs de instalação: comando único, alternativa e atualizar | `tasks/T2.md` | P3 | `main` @ `465b1056cf1324c00780df42f5659a44ba169358` (#209) | `aidlc/u8-docs/t2-install-docs` | T1 |
| T3 — Docs dos agentes e do hook a partir do comando único | `tasks/T3.md` | P4 | `main` depois do merge da T2 | `aidlc/u8-docs/t3-agents-hook-docs` | T2; Q1 = A |
| T4 — Harness: passo 14 (comando único × prompt de IA) e pass_env | `tasks/T4.md` | P5 | `main` @ `465b1056cf1324c00780df42f5659a44ba169358` (#209) | `aidlc/u8-docs/t4-step-14` | T1; U6 T3; U7 T3 |

**Paralelismo:**
- **T1 primeiro, sozinha.** As outras usam os prompts (T2, T3 linkam; T4 extrai os blocos) e o arquivo de teste (T2, T3).
- **T2 → T3 em sequência.** As duas mudam `tests/test_docs_pins.py` (cada uma acrescenta no fim) e os 2 READMEs.
- **T4 em paralelo com a T2 e com a T3.** Nenhum arquivo de código em comum. Só o `CHANGELOG.md` é comum com a T3, e a regra R-CL resolve: a que entra depois põe os parágrafos dela no topo.
- Ordem de merge sugerida: T1; depois T2 e T4 (qualquer ordem); depois T3.

## Ordem no CHANGELOG (fim da U8)
No topo de `## Unreleased`, de cima para baixo: a entrada de quem entrou por último entre a U8 T3 e a U8 T4; a outra; depois as da U7 T3 e da U6 T3 (na ordem de R-CL da U6/U7); depois a da U5 T3. Cada entrada tem 2 parágrafos (en, pt-BR).

## Mecanismo de entrega
Igual à U5, à U6 e à U7:
- O Maestro despacha cada ET, com o HEAD da base anotado, para um agente de código. A T1 vai com o anexo.
- O agente abre 1 PR para `main`.
- Eu verifico o PR contra a ET (`tasks/T<n>-verificacao.md`, escrito na hora da verificação).
- O Emerson faz o merge.

Antes de cada despacho eu fixo o SHA da base e reconfiro as âncoras da lista acima. Nada é despachado por este plano.

## Riscos
| # | Risco | Mitigação |
|---|---|---|
| R1 | Q1 sem resposta segura a T3. | Q1 vai ao Emerson com a Plan Approval. A T1, a T2 e a T4 seguem. Outra resposta gera a T3 v2 (textos de `agents.md`, `_NOT_BEFORE` e o teste 4). |
| R2 | O `install.sh` da `main` pós-U6 diverge do anexo (por exemplo, outra opção de `curl`). | O teste da T1 falha e o agente para (restrição da ET). O arquiteto ajusta o anexo; o CT2 manda. |
| R3 | Os manifestos A e B diferem no CI por um arquivo que o `install.sh` escreve e o prompt não. | É a falha que o passo 14 existe para achar. O agente para e cola `a.txt`/`b.txt`. O arquiteto decide se a correção vai no prompt (CT18 v2) ou no `install.sh`. |
| R4 | O `pip freeze` muda entre A e B por algo além da linha `bob-quality @`. | Mesmo Python, mesmo wheel e mesmo índice nas duas. Se divergir, cai no R3. |
| R5 | O passo 14 instala 2 vezes (pip e `npm ci`) e pode passar de 360 s. Os tetos por passo somam mais que 900 s (2: 300; 10: 300; 11: 30; 13: 180; 14: 360). | Cache npm compartilhado. Os tetos são de falha, não de soma: hoje o harness leva ~232 s. A ET manda parar e reportar se passar, sem subir limite. |
| R6 | Link do site pt-BR. | Conferido no código do Docusaurus (ADR 0028). O `website / build` com `onBrokenLinks: 'throw'` prova. |
| R7 | O `README.md` não é página do site; um link errado nele não quebra o build. | `test_alternative_links_the_prompt_in_the_doc_language` resolve o link a partir da pasta do arquivo. |
| R8 | `VERIFY_REMOTE=1` não prova o prompt contra o GitHub real. | O passo 14 diz "não se aplica". A prova real é a linha "Prompt de IA" do release-check (U9). |
| R9 | A T3 e a T4 encostam no topo do `CHANGELOG.md`. | Regra R-CL. |
| R10 | A T4 muda `run_oneliner` (U6) e `run_bob` (U7). | Os testes delas (A4, A5) mantêm a saída esperada: prova de que a ordem não mudou. |

## Autochecagem
- [x] P1–P4, D1–D9 e o passo 14 têm tarefa e teste.
- [x] Todo FR8.x, FR1.6–FR1.8 e o CT17/CT18 têm prova automática (Testing Contract).
- [x] Âncoras conferidas em `22d461a`; as que a U6/U7 mexem estão na lista "a reconferir" e no passo 0 de cada ET.
- [x] Cada ET tem passo 0 numérico, diz se toca o `CHANGELOG.md` (T3, T4) e se roda em paralelo.
- [x] Nenhuma meta rebaixada; nenhum waiver novo. `src/` não muda.
