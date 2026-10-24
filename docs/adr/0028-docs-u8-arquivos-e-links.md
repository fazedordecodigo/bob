# Docs (U8): lista de arquivos, links e paridade

Status: aceita pelo Emerson em 22/10/2026, no Plan Approval da U6, da U7 e da U8. Publicada em `docs/adr/` na U9.

## Decisão

- **`docs/instalacao.md` não existe desde o #174** (`752d235`, 2026-10-19, "docs: translate the public site pages into pt-BR"). A versão pt-BR da página de instalação agora é `website/i18n/pt-BR/docusaurus-plugin-content-docs/current/getting-started/installation.md`.
  - No CT17, `docs/instalacao.md` passa a ser esse arquivo.
  - Pela mesma regra entram as traduções pt-BR de `agents.md` e de `pre-push.md`: 8 docs no total, 4 de instalação.
- **Links para o prompt.**
  - `README.md` → `docs/install-prompt.en.md`.
  - `README.pt-BR.md` → `docs/install-prompt.pt-BR.md`.
  - `docs/getting-started/installation.md` → `../install-prompt.en.md`.
  - Página pt-BR do site → `/install-prompt.pt-BR.md` (com `/` no início). Conferido no código do Docusaurus (`packages/docusaurus-utils/src/markdownLinks.ts`, `resolveMarkdownLinkPathname`, branch `main`, lido em 2026-10-22): link `./` ou `../` só é resolvido a partir da pasta do próprio arquivo, que no pt-BR é `website/i18n/…`, onde o prompt não existe. Já o link com `/` é resolvido nos content paths, primeiro o traduzido e depois `docs/`. A redação anterior desta ADR (`../install-prompt.pt-BR.md`) quebraria o build.
  - O teste resolve o link: com `/`, a partir de `docs/`; sem `/`, a partir da pasta do arquivo (o `README*` na raiz do repo).
- **Bloco `perfil` do prompt.** Grava `R="already-marked:$F"` (ADR 0021). É o único bloco que muda em relação ao texto do CT18 v1.
- **Passo 14.** As instalações A e B usam `npm_config_cache=$T/npm-cache`, fora do `HOME`, para não baixar duas vezes. A U8 T4 junta a lista de variáveis repassadas (`run_oneliner`, `run_bob` e passo 14) numa função `pass_env`.

## Consequências

A lista do CT17 sobe de 6 para 8 arquivos. É correção compatível: o doc pt-BR mudou de lugar no #174, e nenhuma consumidora implementou o teste. Os requisitos (FR8.4, US1.5 crit. 6) citam `docs/instalacao.md`. O plano registra o mapeamento e não edita o 2.3.
