# U8 — Requisitos não funcionais (3.2, kind spec)

O kind spec só tem NFR de conteúdo, paridade e build. Desempenho e segurança entram só no passo 14 (harness).

| # | Requisito (origem) | Medida | Alvo | Prova | Pronto |
|---|---|---|---|---|---|
| U8-N1 | Comando único primeiro (FR8.1, CT17) | docs dos 8 cujo 1º bloco de shell é o comando único do idioma | 8 de 8 | `test_install_docs_start_with_the_one_liner[4]`, `test_agent_and_hook_docs_start_with_the_one_liner[4]` | 1 |
| U8-N2 | Pins dos docs (FR8.2) | versões citadas iguais às fontes (npm, Node, Python, gitleaks) | 100% | `test_docs_cite_only_the_pinned_versions[8]`, `test_install_docs_cite_the_pinned_requirements[4]` | 2 |
| U8-N3 | Atualizar e ver versão (FR8.3) | docs de instalação com `## Update`/`## Atualizar`, `bob update` e `bob --version` | 4 de 4 | `test_update_section_shows_update_and_version[4]` | 3 |
| U8-N4 | Ordem principal/alternativa (FR8.4, CT17) | título da alternativa 1 vez, depois do comando único, com link no idioma e arquivo existente | 4 de 4 | `test_alternative_comes_after_the_one_liner_once[4]`, `test_alternative_links_the_prompt_in_the_doc_language[4]` | 4 |
| U8-N5 | Paridade do prompt (FR1.6, FR1.8, FR8.5, CT18) | itens de paridade que passam | 11 de 11 | testes 1–13 da T1 (13 testes, 19 casos) | 5 |
| U8-N6 | Independência do `install.sh` (NFR11) | blocos com `install.sh` ou `sudo`; pedidos de `install.sh` na instalação B | 0; 0 | `test_prompt_blocks_never_use_install_sh_or_sudo`; passo 14 | 5, 6 |
| U8-N7 | Mesmo resultado (NFR10, FR1.7) | diferenças entre o manifesto A e o B; 2ª execução | 0; `~/.profile` igual, 2 linhas `reused`, doctor 0 | passo 14 | 6 |
| U8-N8 | `BOB_VERSION` fora do uso normal (FR1.4) | menções fora da nota marcada | 0 (prompt e 8 docs) | `test_bob_version_is_read_only_in_the_prompt[2]`, `test_bob_version_only_in_the_release_check_note[8]` | 5 |
| U8-N9 | Site publica sem link quebrado (CT17, ADR 0028) | check `website / build` (`npm run build` nos 2 locales e `npm test`) | verde | check do PR em T1, T2 e T3 | 4 |
| U8-N10 | Tempo do passo 14 | `verify-install: passo 14: tempo <s> s` | ≤ 360 s | job `verify-install / linux-x64` | 6 |
| U8-N11 | Harness inteiro | duração de `sh scripts/verify-install.sh` | ≤ 900 s (timeout do job 20 min) | job | U5-N13 |
| U8-N12 | Testes herméticos (U5-N16) | linhas no log da guarda em `pytest tests/test_docs_pins.py` | 0 | `test_u5_tests_open_no_network[tests/test_docs_pins.py]` | — |
| U8-N13 | Qualidade do diff | `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` | exit 0; 0 waivers novos | checks do PR | — |

## Não se aplica (ou só em parte)
- **Mutação e CRAP.** A U8 não muda `src/`. Os gates rodam e precisam sair 0, mas não há linha nova gateada.
- **Cobertura de `src/`.** Sem linha nova; a meta global (≥ 80,0) não muda.
- **Desempenho do `bob`.** Só o tempo do passo 14 (U8-N10).
