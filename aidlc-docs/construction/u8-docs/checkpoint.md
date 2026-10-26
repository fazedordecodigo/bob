# Checkpoint da U8 (u8-docs) — B8
Preparado pelo Arquiteto em 24/10/2026 12:05 (UTC-3) para o checkpoint do Emerson. Base: `main` @ `1b107922bf6553660231f598d758258b96fc091c` (merge do #213, T3).
Formato: o mesmo de `construction/u7-update-versao/checkpoint.md` e `construction/u6-perfil-shell/checkpoint.md`.
Fontes: só leituras remotas (`gh pr view`, `gh api` para PRs, runs, jobs e logs). Sem clone. Relatórios: `code-generation/tasks/T1-verificacao.md`, `T2-verificacao.md`, `T3-verificacao.md`, `T4-verificacao.md`.

## Confirmação dos merges e da `main`
| PR | ET | Head verificado | Merge commit | Mergeado em |
|---|---|---|---|---|
| #209 | T1 — Prompt de IA sem install.sh e teste de paridade | `72497ec437b174d8fbaf7a00e23e17e05558967a` | `465b1056cf1324c00780df42f5659a44ba169358` | 2026-10-24T10:14:31Z (**24/10 07:14:31 UTC-3**) |
| #211 | T4 — Harness: passo 14 e `pass_env` | `22fc38485e11f62cb9e114ab828174bb31c985cf` | `9c8c4f5c5629bafaf8780c877caebe88c99e8ced` | 2026-10-24T13:06:14Z (**24/10 10:06:14 UTC-3**) |
| #212 | T2 — Docs de instalação: comando único, alternativa e atualizar | `cb166448d7c943182e5812b97286fde452ecc458` | `d30080723d5cc79e8868940effe619bda08c4863` | 2026-10-24T13:07:14Z (**24/10 10:07:14 UTC-3**) |
| #213 | T3 — Docs dos agentes e do hook a partir do comando único | `0f88870b4ec128f942d4ab7ed5aef92ebaf75466` | `1b107922bf6553660231f598d758258b96fc091c` | 2026-10-24T14:51:50Z (**24/10 11:51:50 UTC-3**) |

Todos mergeados pelo Emerson. Nenhum agente fez merge.

## Veredito: Concluída — checkpoint aprovado pelo Emerson em 24/10/2026 12:41 (UTC-3): "Aprovo o checkpoint da U8 e o plano/ETs T1 a T3 da U9 com a ADR 0030. U9 Q1: B (publicar ADRs 0008 a 0029). U9 Q2: A (eu disparo ou autorizo o dry_run depois dos merges). Pode despachar a U9 T1, T2 e T3 em paralelo sobre 1b10792."
- **82 critérios de ET**: 82 Atende, 0 Não atende, 0 Não verificado (T1: 17, T2: 18, T3: 18, T4: 29).
- **0 rodadas de correção** nas 4 ETs (T1 = 0, T2 = 0, T3 = 0, T4 = 0). Nenhuma lacuna de ET, nenhuma decisão tomada pelos agentes.
- **13 metas de NFR da U8** (`U8-N1` a `U8-N13`): 13 Atende, 0 Não atende, 0 Não verificado.
- Comando de Verificação na `main` `1b10792`: `verify-install / linux-x64` `success` com **15 linhas `ok`** (passos 1–8, 9a, 9b, 10–14), passo 14 em **34 s**; `package / dist` `success`.
- Fica para a U9 (não é meta da U8): passo 14 na matriz Linux/macOS × x64/arm64 e o item "Prompt de IA" com agente real no release-check (NFR10/NFR11 por release, US1.5 crit. 7).

## 1. Comando de Verificação na `main` `1b10792`
| Parte | Evidência remota | Resultado |
|---|---|---|
| `sh scripts/verify-install.sh` | workflow `verify-install`, push em `1b10792`, run `40104391267` (job `120902948474`), `success`, 14:51:55–14:54:41 UTC (2m46s). **15 linhas `ok`**. Tempos: passo 2 16 s, 5 6 s, 6 1 s, 7 1 s, 10 13 s, 11 0 s, 12 11 s, 13 8 s, **14 34 s** | Atende |
| Pacote | workflow `package`, run `40104391280`, `dist` `success` | Atende |
| `pytest` | heads dos PRs: #213 `4882 passed, 3 warnings` (3.10 e 3.12); a árvore de `1b10792` é a do head `0f88870` sobre `d300807`. O `CI` do push de `1b10792` (run `40104391305`) estava em execução às 11:55 UTC-3 | Atende |
| Docs (`website / build`) | verde nos PRs #209, #212 e #213 (build en + pt-BR, `npm test`) | Atende |
| Matriz (Linux arm64, macOS x64/arm64) | o CI só roda Linux x64; a matriz é da U9 | Não verificado (U9) |

## 2. "Pronto quando" da U8 (`unit-of-work.md`) e B8 (bolt-plan)
| Critério | Evidência | Resultado |
|---|---|---|
| 1–3. Comando único primeiro nos docs; pins; gitleaks pelo comando; `bob update` e `bob --version` | T2 (#212) e T3 (#213): testes `test_install_docs_start_with_the_one_liner[4]`, `test_agent_and_hook_docs_start_with_the_one_liner[4]`, `test_docs_cite_only_the_pinned_versions[8]`, `test_install_docs_cite_the_pinned_requirements[4]`, `test_update_section_shows_update_and_version[4]` | Atende |
| 4. Comando único antes da "Alternativa", 1 vez, com link no idioma (CT17, FR8.4) | `test_alternative_comes_after_the_one_liner_once[4]`, `test_alternative_links_the_prompt_in_the_doc_language[4]`; `website / build` verde | Atende |
| 5. `install-prompt.en.md` e `.pt-BR.md`, blocos iguais, 11 itens do CT18 (FR1.6, FR1.8, FR8.5, NFR11) | T1 (#209): 13 testes, 19 casos em `tests/test_docs_pins.py`; `test_prompt_blocks_never_use_install_sh_or_sudo` | Atende |
| 6. Passo 14: manifesto A = B, doctor 0, 0 pedidos de `install.sh`, 2ª execução sem mudança (FR1.7, NFR10, NFR11) | T4 (#211) e `main` `1b10792`: passo 14 `ok` (42 s no PR, 34 s na `main`) | Atende |
| Q1 = A (sem instruções de plugin nos docs de usuário) | T3 (#213): `test_no_clone_or_plugin_before_the_one_liner[8]`, `test_agents_doc_names_the_single_folder_and_ra1[2]` | Atende |
| CHANGELOG (ADR 0027, R-CL) | topo de `## Unreleased` em `1b10792`: T3 (en, pt-BR), depois T4 (en, pt-BR), depois U7 | Atende |

**B8 atendida.**

## 3. Critério → evidência por ET
| ET | PR | Head | Critérios | Atende | Não atende | Não verificado | Rodadas de correção | Checks |
|---|---|---|---|---|---|---|---|---|
| T1 | #209 | `72497ec` | 17 | 17 | 0 | 0 | 0 | 7/7 verdes; `4819 passed`; `test_docs_pins.py` 19 passed; `test_hermetic.py` 6 |
| T2 | #212 | `cb16644` | 18 | 18 | 0 | 0 | 0 | 7/7 verdes; `4852 passed`; `test_docs_pins.py` 47 passed (+28) |
| T3 | #213 | `0f88870` | 18 | 18 | 0 | 0 | 0 | 7/7 verdes; `4882 passed`; `test_docs_pins.py` 69 passed (+22); 75 com hermetic |
| T4 | #211 | `22fc384` | 29 | 29 | 0 | 0 | 0 | 6/6 verdes; `4832 passed`; `test_verify_install.py` 54 passed (+8); 15 `ok`, passo 14 em 42 s, harness 192 s |
| **Total** | 4 | — | **82** | **82** | **0** | **0** | **0** | — |

Destaques por ET (detalhe completo nos relatórios):
- **T1:** prompts en e pt-BR byte a byte iguais aos anexos (sha256 `99e5e5b1…` e `ad4570c9…`); R1–R5; 13 testes/19 casos; guarda de rede com 0 bytes no log.
- **T2:** 4 blocos novos byte a byte iguais à ET, com os links da ADR 0028; linha 7 dos READMEs; linha 5 dos `installation.md`; 6 testes/28 casos; 0 testes existentes alterados.
- **T3:** Q1 = A citada; `agents.md` en/pt-BR iguais à ET; `pre-push.md` e READMEs com igualdade exata no arquivo inteiro; CHANGELOG acima do da T4, com quebra gulosa; 4 testes/22 casos.
- **T4:** `STEP_IDS` com 14; `PASS_ENV`/`BLOCK_FAILED`; `pass_env` única (3 `eval`); `box_platform`, `prompt_blocks`, `manifest`, `run_blocks`, `install_state`, `step_14` (R6a–R6j com as mensagens exatas); A1–A5; 5 testes/8 casos.

## 4. Metas de NFR da U8 (`nfr-requirements.md`)
| # | Meta | Alvo | Evidência | Resultado |
|---|---|---|---|---|
| U8-N1 | Comando único primeiro (FR8.1, CT17) | 8 de 8 | `test_install_docs_start_with_the_one_liner[4]` (T2) + `test_agent_and_hook_docs_start_with_the_one_liner[4]` (T3) = 8 casos passando | Atende |
| U8-N2 | Pins dos docs (FR8.2) | 100% | `test_docs_cite_only_the_pinned_versions[8]`, `test_install_docs_cite_the_pinned_requirements[4]`; pins lidos de `npm_tools`, `gitleaks.VERSION` e `pyproject.toml` | Atende |
| U8-N3 | Atualizar e ver versão (FR8.3) | 4 de 4 | `test_update_section_shows_update_and_version[4]` | Atende |
| U8-N4 | Ordem principal/alternativa (FR8.4) | 4 de 4 | `test_alternative_comes_after_the_one_liner_once[4]`, `test_alternative_links_the_prompt_in_the_doc_language[4]` | Atende |
| U8-N5 | Paridade do prompt (FR1.6, FR1.8, FR8.5, CT18) | 11 de 11 | 13 testes / 19 casos da T1 passando (CI 3.10 e 3.12) | Atende |
| U8-N6 | Independência do `install.sh` (NFR11) | 0; 0 | `test_prompt_blocks_never_use_install_sh_or_sudo`; passo 14 confere a lista exata de 4 pedidos ao espelho na instalação B (sem `install.sh`) e `sudo.log` vazio | Atende |
| U8-N7 | Mesmo resultado (NFR10, FR1.7) | 0 diferenças; `.profile` igual, 2 `reused`, doctor 0 | passo 14 `ok` (`cmp -s a.txt b.txt`, B2 com `.profile` igual e 2 linhas `reused`) no #211 e na `main` `1b10792` | Atende |
| U8-N8 | `BOB_VERSION` fora do uso normal (FR1.4) | 0 | `test_bob_version_is_read_only_in_the_prompt[2]`, `test_bob_version_only_in_the_release_check_note[8]` | Atende |
| U8-N9 | Site sem link quebrado (CT17, ADR 0028) | verde | `website / build` verde em #209, #212 e #213 | Atende |
| U8-N10 | Tempo do passo 14 | ≤ 360 s | 42 s (#211), 34 s (`main` `1b10792`) | Atende |
| U8-N11 | Harness inteiro | ≤ 900 s | 192 s (#211); 2m46s = 166 s (`main` `1b10792`) | Atende |
| U8-N12 | Testes herméticos (U5-N16) | 0 linhas no log da guarda | `test_u5_tests_open_no_network[tests/test_docs_pins.py]` (T1); execução sob `BOB_NET_GUARD_LOG` com 0 bytes | Atende |
| U8-N13 | Qualidade do diff | exit 0; 0 waivers novos | `bob / check` verde nos 4 PRs; corpos com `bob check … crap,dry,deps,mutate,coverage` exit 0; `.bob/waivers.yaml` fora dos 4 diffs | Atende |

**13 Atende, 0 Não atende, 0 Não verificado.**

Fora das metas da U8 (dependem da U9, não reprovam este checkpoint):
- Passo 14 e passos 1–13 na matriz Linux/macOS × x64/arm64 (NFR3, NFR10 na matriz): job da U9.
- Item "Prompt de IA" com agente de IA real por release (US1.5 crit. 7, CT13): release-check manual da U9 (E4).

## 5. Lacunas e observações
- Nenhuma lacuna bloqueia o checkpoint. Nenhuma ET mudou de versão; nenhuma decisão aprovada foi alterada.
- O workflow `pages` falha no job `deploy` no push de `1b10792` (run `40104391275`): `Get Pages site failed … Not Found`. O `build` passa. A falha é antiga (mesmo erro em `d300807`, `465b105`, `b142631`, `752d235`, `410175e`): o GitHub Pages não está habilitado no repo. Não é da U8. Habilitar o Pages é decisão do Emerson.
- Nos PRs #211, #212 e #213, o "Before" do `bob check` local falhou por ambiente do agente (`uv`/gitleaks); o "After" e o CI estão verdes.
- O `bob / check` no CI roda `crap,dry,deps,mutate`; o `coverage` vem do corpo dos PRs, como nas units anteriores.
- O `CI` do push de `1b10792` estava em execução quando este documento foi escrito; a mesma árvore passou no head `0f88870` do #213.

## Registro
- 24/10/2026 12:05 (UTC-3): checkpoint preparado pelo Arquiteto depois do merge do #213 (`1b10792`). U8 em `awaiting_checkpoint_approval` no `traceability.json`. Falta a aprovação do Emerson.
