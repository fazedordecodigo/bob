# U8 — u8-docs — Desenho funcional (3.1, kind spec)

Base: `main` @ `22d461a60920ab13e7b09fd654fd0e4686ba14d0`. Data: 2026-10-22 (UTC-3).
**Despacho só depois dos merges da U6 e da U7** (bolt-plan, aprovação do Emerson: "U6 e U7 em paralelo, com o desenho da U8 junto e o despacho dela depois dos merges da U6 e da U7").
Todas as âncoras deste desenho e das ETs foram lidas em `22d461a`. **Reconferir na `main` pós-U6/U7** antes do despacho.
ADRs: 0020 (aprovada), 0021, 0026, 0027 e 0028 (propostas), 0029 (nova, proposta). Todas em `../u6-u7-decisions-proposta.md`.
Pergunta de produto aberta: `functional-design-questions.md` Q1 (instruções de plugin nos docs). Bloqueia só a T3.

## O que passa a existir
- `docs/install-prompt.en.md` e `docs/install-prompt.pt-BR.md` (CT18): 14 passos, 19 blocos `sh bob-step=<id> platform=<p>`, iguais byte a byte nos dois idiomas. O texto exato está em `code-generation/tasks/T1-anexo/docs/`.
- Nos 4 docs de instalação (`README.md`, `README.pt-BR.md`, `docs/getting-started/installation.md` e `website/i18n/pt-BR/docusaurus-plugin-content-docs/current/getting-started/installation.md`):
  - seção `## Install` / `## Instalar` com o comando único como 1º bloco de shell do arquivo;
  - requisitos reais e o que o comando faz;
  - `### Alternative: ask your AI agent` / `### Alternativa: pedir ao seu agente de IA`, com o link do prompt no idioma do doc;
  - `## Update` / `## Atualizar` com `bob update` e `bob --version` (CT17, FR8.1–FR8.4).
- `docs/getting-started/agents.md` e `guides/pre-push.md` (en e pt-BR) partem do comando único:
  - pasta única `.agents/skills`, com o Claude Code sob RA1;
  - hook escrito pelo `bob setup`;
  - as seções "Installing in the agents" e "Pre-push hook" dos 2 READMEs seguem o mesmo texto.
- `tests/test_docs_pins.py` (CT17): os 11 itens de paridade do CT18, as fontes únicas e a ordem dos docs.
- Passo 14 do `scripts/verify-install.sh` (CT15): instalação A (`install.sh`) × instalação B (blocos do prompt), manifesto igual e 2ª execução B2 sem mudança.

## Estado atual do repo (conferido @ 22d461a)
- Nenhum dos 8 docs mostra o comando único. Os 4 de instalação partem de um clone. `agents.md` e os READMEs ensinam plugins (`claude plugin install`, `copilot plugin install`, `git clone` para `~/.cursor/plugins/local/bob`).
- `docs/instalacao.md` não existe desde o #174. A página pt-BR é a tradução do Docusaurus (ADR 0028).
- O site (Docusaurus, `markdown.format: 'md'`, `onBrokenLinks: 'throw'`) monta `docs/` inteiro. Um `.md` novo em `docs/` vira página, mesmo fora do sidebar. O check `website / build` roda em PR que toca `docs/**` ou `website/**`.
- Pins atuais: `package.json` com `engines.node = ">=22.18.0 <23"` e 9 dependências exatas (`vitest` 5.0.5); `requires-python = ">=3.10"`; `gitleaks.VERSION = "8.30.1"`. As versões npm citadas hoje nos docs batem com os pins.
- `scripts/install.sh` (depois da U6): `STEPS` com `perfil`, `PROFILE_LINE` na linha 5, `DEFAULT_API`, `DEFAULT_DOWNLOAD`, `CURL_OPTS` e `PIP_OPTS`. `BOB_VERSION` aparece em 3 linhas: a leitura `_pinned=${BOB_VERSION:-}` e as 2 mensagens de valor inválido.

## Regras — prompt (CT18; ADR 0021, 0028; T1)
| # | Regra |
|---|---|
| P1 | Moldura do arquivo, nesta ordem: título; aviso de alternativa (citação `>`); 1 frase para colar o arquivo no agente; `## Rules` / `## Regras` com o bloco `text` das 8 regras (pt-BR exato do CT18; en com o mesmo conteúdo); `## <n>. <id>` para cada passo de 1 a 14, com os blocos; a nota `> Tests/release-check only:` / `> Somente testes/release-check:` como última linha. |
| P2 | Cada bloco é o preâmbulo do CT18 (6 linhas) seguido do corpo do CT18. Só o `perfil` muda, em 2 pontos: `R=already-marked` vira `R="already-marked:$F"` (ADR 0021); `case "${SHELL##*/}" in` vira `S=${SHELL:-}` e `case "${S##*/}" in`, porque com `set -u` um `SHELL` ausente derrubava o bloco (ADR 0029; é a mesma forma do `install.sh` da U6, R2b). |
| P3 | Blocos byte a byte iguais entre en e pt-BR. Só a prosa muda. |
| P4 | Nenhum bloco cita `install.sh` nem `sudo`. Todos passam em `sh -n` e em `dash -n`. |

## Regras — docs (CT17; ADR 0028, 0029; T2, T3)
| # | Regra |
|---|---|
| D1 | "Bloco de shell" = bloco cercado cuja 1ª palavra da info string é `bash`, `sh`, `shell` ou `console`. Nos 8 docs, o 1º bloco de shell é o comando único. Em en: `curl -fsSL https://github.com/fazedordecodigo/bob/releases/latest/download/install.sh \| sh`. Em pt-BR: a mesma linha seguida de ` -s -- --lang pt-BR` (CT2, linha 62 do contract-summary). |
| D2 | Nenhum `git clone` nem `plugin install` antes do comando único (posição no texto). |
| D3 | Nos 4 docs de instalação, o título da alternativa aparece 1 vez, depois do comando único. A seção dele traz o parágrafo fixo e o link (ADR 0028): `README.md` → `docs/install-prompt.en.md`; `README.pt-BR.md` → `docs/install-prompt.pt-BR.md`; `docs/getting-started/installation.md` → `../install-prompt.en.md`; página pt-BR do site → `/install-prompt.pt-BR.md`. |
| D4 | Nos 4 docs de instalação: `## Update` / `## Atualizar` 1 vez, depois da alternativa, com um bloco `bash` de exatamente 2 linhas (`bob update` e `bob --version`) (FR8.3). |
| D5 | Os requisitos citam, nos 4 docs de instalação: a faixa do Node = `str(node_range())`; o piso do Python = `requires-python` (forma `Python 3.10 or newer` / `Python 3.10 ou mais novo`); gitleaks `` `8.30.1` `` = `gitleaks.VERSION` (FR8.2). |
| D6 | Nos 8 docs, toda menção `<nome npm>@X.Y.Z` de um nome de `pinned_npm_versions()` é igual ao pin; toda faixa `>=A.B.C <N` é igual a `str(node_range())`; toda menção `Python X.Y or newer\|or later\|ou mais novo\|ou posterior` é igual ao piso; toda menção `gitleaks X.Y.Z` (com ou sem crase ou `v`) é igual a `gitleaks.VERSION`. |
| D7 | `BOB_VERSION` nos 8 docs: só numa linha que começa com `> Somente testes/release-check:` ou `> Tests/release-check only:`. Hoje nenhum dos 8 a cita, e a U8 não acrescenta. |
| D8 | `agents.md` (en e pt-BR): pasta única `.agents/skills`; tabela dos 4 agentes; o Claude Code sob RA1; nenhum `plugin install` nem `git clone` (sujeito à Q1). |
| D9 | `pre-push.md` (en e pt-BR): o comando único escreve o hook; um hook alheio fica preservado e o `bob setup` diz a linha a acrescentar (U5); o resto do guia não muda. |

## Regras — teste de paridade (CT17/CT18; T1–T3)
`tests/test_docs_pins.py` lê o `install.sh` com `^NOME='(.*)'$` e os blocos com a regex do CT18. Os itens 1–11 do CT18 viram os testes da T1. As regras D1–D7 viram os da T2 e da T3. Sem rede: o único processo é `sh`/`dash` local.

## Passo 14 (CT15; ADR 0026, 0028, 0029; T4)
- **Instalação A.** `HOME=$T/s14/h`, projeto `$T/s14/p`, `PATH=$(tool_path)`, `npm_config_cache=$T/npm-cache`, sem `SHELL` (como no `run_oneliner`; o perfil vai para `~/.profile` nas duas instalações). Roda `run_oneliner 14 …` contra o espelho. Grava o manifesto A.
- **Recriação.** Apaga `h` e `p` e recria nos mesmos caminhos.
- **Instalação B.** `prompt_blocks` extrai os blocos de `docs/install-prompt.en.md` filtrados pela plataforma do box. Cada bloco roda num `sh` separado (`env -i`, mesmo ambiente), na raiz do projeto, e o passo para no 1º ≠ 0. Depois:
  - 0 pedidos de `install.sh` no log do espelho durante B;
  - grava o manifesto B.
- **Manifesto.** Linhas ordenadas `caminho, tipo, modo, alvo ou sha256` de:
  - `$BOB_HOME`, sem o conteúdo de `versions/*/venv/`. No lugar dele vai 1 linha com o sha256 do `pip freeze --all` normalizado: a linha `bob-quality @ …` vira `bob-quality @ <wheel>`;
  - `~/.local/bin/bob`, `~/.profile`, `.agents/skills/**`, `bob.yaml`, `.git/hooks/pre-push`;
  - mais o código do `bob doctor` e as 2 linhas do `bob --version`.
- **A = B.** Diferença → `verify-install: passo 14: manifestos diferem: <1ª diferença>`.
- **B2.** Os blocos de novo. `~/.profile` fica com o mesmo sha256; `bob-prompt: pacote: ok (reused)` e `bob-prompt: gitleaks: ok (reused)` aparecem 1 vez cada; o `verificação` passa.
- `VERIFY_REMOTE=1` → "não se aplica" (como 9a, 9b, 10 e 11). Alvo ≤ 360 s. Harness inteiro ≤ 900 s.
- A lista de variáveis repassadas vira a função `pass_env`, usada por `run_oneliner`, `run_bob` e pelo passo 14 (ADR 0028).

## Fora do desenho
- Traduzir outras páginas do site.
- Publicar o prompt como asset (CT12 continua com 3 assets).
- Rodar o prompt num agente real (release-check da U9, CT13).
- `docs/reference/cli.md` (`bob update`, `bob --version`): fora da lista do CT17. Vai como sugestão de backlog.
