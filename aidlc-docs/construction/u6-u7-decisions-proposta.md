# U6, U7 e U8 — Proposta de ADRs e deltas de contrato

Data: 2026-10-22 (UTC-3) | Base conferida: `main` @ `22d461a60920ab13e7b09fd654fd0e4686ba14d0` (merge do #202, U5 T3).
Estado: **promovido 2026-10-22 22:17 UTC-3 (Plan Approval Emerson)**.
ADRs 0021–0029 → `inception/application-design/decisions.md`.
Deltas CT2, CT3, CT4, CT6 (v2), CT8, CT11, CT15, CT16 (v2), CT17, CT18 → `inception/contracts/contract-summary.md`.
Quote: "Aprovo o plano da U6 e da U7, as ETs e o CT6/CT16 v2. U7 Q1: A, mixed (0.1.0, not installed). U8 Q1: A, tirar as instruções de plugin. Pode despachar a U6 T1, a U6 T2 e a U7 T1 sobre a main 22d461a."
Origem: Arquiteto Técnico AI-DLC, 2.10 de construção da U6, U7 e U8. A mudança do bolt-plan foi aprovada às 19:47 UTC-3: "Aprovo a mudança no bolt-plan: U6 e U7 em paralelo, com o desenho da U8 junto e o despacho dela depois dos merges da U6 e da U7."

Todas as decisões abaixo são técnicas e reversíveis. As que mudam comportamento visível e não estão nos requisitos viraram pergunta (`u7-update-versao/functional-design-questions.md`, Q1). A U6 e a U8 não têm pergunta aberta.

## ADRs novas

### ADR 0021 — `BOB_INSTALL_PROFILE` leva o arquivo também em `already-marked`
**Contexto.** O CT6 e o CT16 dão os valores `<arquivo>`, `already-on-path`, `already-marked` e `failed:<arquivo>`. Mas o texto aprovado do resumo (CT3) e o passo 13 do Comando de Verificação pedem `<arquivo> já tem a linha do bob; nada mudou`. Com `already-marked` sozinho, o `bob setup` não sabe qual arquivo citar. A outra saída seria o Python refazer a regra de `$SHELL`/`ZDOTDIR`, o que duplica a ADR 0013 em duas linguagens.
**Decisão.** O valor passa a ser `already-marked:<arquivo absoluto>`. Os outros três ficam iguais. O `bob setup` aceita só estes 4 formatos. Qualquer outro, inclusive `already-marked` sem arquivo, é ignorado (sem linha).
**Consequências.** É mudança de formato numa variável lida por máquina, então é incompatível: CT6 (linha `BOB_INSTALL_PROFILE`) e CT16 sobem para v2. Não há v1 a manter, porque nenhuma consumidora implementou o valor ainda. O bloco `perfil` do prompt (CT18, U8) grava `R="already-marked:$F"` (ver ADR 0028). **Aviso ao Maestro antes da ET**, porque o CT6 e o CT16 estão aprovados.

### ADR 0022 — Passo `perfil` do `install.sh`: forma da escrita, do aviso e da passagem do resultado
**Decisão.**
- `PROFILE_LINE` é a 2ª fonte única do topo (linha 5, logo depois de `STEPS`). A marca (`# managed-by: bob-quality`) e a linha para colar (`export PATH="$HOME/.local/bin:$PATH"`) saem dela por expansão (`"#${PROFILE_LINE#* #}"` e `${PROFILE_LINE%% #*}`). O literal da marca não se repete no script.
- O aviso de falha vai para o stdout (como o `launcher_warning`), em en e pt-BR. O `<erro>` do CT16 é o texto depois do último `": "` da 1ª linha do stderr do shell ao abrir ou criar o arquivo. Exemplos: `Permission denied` (dash e bash) e `Directory nonexistent` (dash). Sem texto, vira `unknown error` / `erro desconhecido`, como no `launcher_try`.
- Falha ao criar, ao fazer `chmod 0644` ou ao acrescentar: todas dão `failed:<arquivo>`. O passo nunca chama `fail` e sempre imprime `install: perfil: ok`.
- O resultado vai para o filho por `export BOB_INSTALL_PROFILE="$profile_result"` e depois `exec "$bob_root/bin/bob" setup --lang "$bob_lang" </dev/null`. Não usa `exec env …`: o efeito é o mesmo e não traz o binário `env` para a lista de ferramentas.
- `tail` e `chmod` entram na lista de utilitários usados (POSIX base). O passo `ferramentas` não os confere, como não confere `mkdir`, `ln` e `awk`.
**Consequências.** O CT2 ganha um esclarecimento compatível na linha `setup`. Root escreve em arquivo só leitura, então o caso (e) do passo 13 não reproduz como root. O harness recusa rodar como root no passo 13 (ADR 0026).

### ADR 0023 — Linha `perfil do shell` no resumo do `bob setup`
**Decisão.** A função privada `setup_cmd._profile_text(value)` mapeia o valor de `BOB_INSTALL_PROFILE`:
- `already-on-path` → `setup.profile_on_path`;
- `already-marked:/…` → `setup.profile_marked`;
- `failed:/…` → `setup.profile_failed`;
- `/…` → `setup.profile_added`;
- vazio, ausente, relativo ou outro valor → nada.

A linha (`setup.profile`) sai em `_summary`, antes de `  bob doctor:`, também no resumo parcial (`_fail`). Lê `os.environ` dentro de `_summary`. As chaves novas entram em `messages.py` logo depois de `setup.doctor_not_run` (en e pt-BR).
**Consequências.** Nada muda sem a variável: os testes atuais do resumo seguem iguais. Os textos en são tradução dos pt aprovados no CT3.

### ADR 0024 — Versão das skills do projeto: módulo `project_version`
**Decisão.**
- Módulo novo `src/bob_quality/project_version.py` (parte de C10). Lê `<projeto>/.agents/skills/<nome>/.bob-version` só para os nomes do manifesto empacotado.
- Função pública nova `install_skills.manifest_skill_names(source=None) -> tuple[str, ...]`. É um acréscimo compatível ao CT4.
- Um arquivo vale só se é regular (não symlink) e o conteúdo casa exatamente `\d+\.\d+\.\d+\n`. Erro de leitura, symlink ou conteúdo fora disso contam como ausente.
- Estados: `installed` (todas as skills com a mesma versão); `not_installed` (nenhuma válida, manifesto ilegível ou lista vazia); `mixed` (versões diferentes, ordenadas como tupla numérica, sem repetição). Uma parte ausente e outra válida também é `mixed`, com o marcador `missing` (recomendação A da Q1 da U7).
- O `bob doctor` acrescenta a linha `project skills:` no fim da saída normal, dentro de `_report_pins`, com o `cwd`. Ela não muda o código de saída. Sai só quando os pins foram lidos (no erro do `package.json` continua 0 linhas no stdout).
- O módulo fica separado de `update.py` para evitar o ciclo `doctor → update → setup_cmd → doctor`.
**Consequências.** O `bob --version` e o doctor usam a mesma linha (CT8 = CT11). Q1 pendente: se a resposta não for A, só os textos de `mixed` mudam (ET v2 da U7 T1).

### ADR 0025 — `bob update` e `bob --version`: implementação
**Decisão.**
- Rede (CT14): `urllib.request.urlopen(Request(url, headers=…), timeout=30)`. `Accept: application/vnd.github+json` só na chamada da API.
  - 3 tentativas, com 1 s de pausa (`time.sleep(1.0)`), como em `gitleaks.py`.
  - Repete só em erro de rede, timeout ou `5xx`. `4xx`, inclusive `429`, não repete.
  - Status no texto: `HTTP <código>`, senão o nome do tipo do `reason` (igual a `gitleaks._status`).
- `BOB_RELEASES_URL`: tira uma `/` final e valida com a mesma regex de `gitleaks._ALLOWED_URL`. Fora → `versão: BOB_RELEASES_URL=<v> …`, saída `4`.
- `tag_name` precisa casar `v\d+\.\d+\.\d+`. Senão → `versão: … (invalid response)`, saída `4`.
- Projeto: `setup_cmd.step_projeto(SetupContext(...))`. A mensagem é a do `bob setup`, com o prefixo `bob update:`. `BOB_HOME` relativo → `setup.bob_home_relative`, saída `4`.
- Comparação:
  - "pacote atual" = a tupla de `importlib.metadata.version("bob-quality")` ≥ a tupla da última. Versão local fora de `X.Y.Z` conta como mais velha.
  - "projeto atual" = estado `installed` com versão ≥ a última. `mixed` e `not_installed` nunca são atuais.
- Download: `install.sh`, depois `SHA256SUMS`, num `tempfile.mkdtemp(prefix="bob-update.")` que sai em `finally`.
  - `404` → "release incompleta"; outro erro → "download … falhou".
  - O `SHA256SUMS` é lido em bytes, por `line.partition(b"  ")`. Linha ausente ou hash diferente → `integridade`, `4`.
- Instalar: `subprocess.run(["sh", <script>, "--lang", <l>], cwd=<projeto>, env={**os.environ, "BOB_VERSION": <tag>}, check=False)`. Devolve o código do filho. `OSError` → `instalar: …`, `4`.
- `bob --version`: uma `argparse.Action` própria (`nargs=0`) no parser de topo. Imprime as 2 linhas e chama `parser.exit()`, que no `_Parser` vira `Help` e sai `0` antes da exigência de subcomando. O idioma vem de `_language` (`--lang`, `BOB_LANG`, `bob.yaml`).
**Consequências.** São ~12 linhas parecidas com o `_fetch` do `gitleaks.py`. O gate `dry` só reporta, não bloqueia. Juntar as duas cópias fica para depois (fora da U7).

### ADR 0026 — Harness: passos 10, 11 e 13 e o passo 2 parcial
**Decisão.**
- **Dependências dentro do passo, não em `run_selected`.** O `step_13` chama `ensure_2` na 1ª linha. O `step_10` chama `ensure_8`, e o `step_11` chama `ensure_10`. A linha `3|4|5|6|7|12) ensure_2 ;;` não muda (uma linha a menos em comum entre a U6 e a U7).
- **Passo 13 (U6).**
  - 5 casos, cada um com `HOME` e projeto novos em `$T/s13/<a..e>`, 2 execuções do comando único.
  - `BOB_HOME` compartilhado com o do passo 2 (`$S2_HOME/.local/share/bob-quality`): o pacote é reusado e o passo fica em segundos.
  - `run_oneliner` ganha dois argumentos opcionais, `${10}` (`SHELL`) e `${11}` (`BOB_HOME`).
  - A checagem "bob já está no PATH" aceita só o `$HOME/.local/bin/bob` do próprio caso. Sem isso, o caso (d) não roda a 2ª vez. Nos outros passos o `PATH` nunca tem `~/.local/bin`, então nada muda neles.
  - Root → `die_passo 13`.
  - Alvo ≤ 180 s.
- **Passos 10 e 11 (U7).**
  - Subárvore própria do espelho, `$T/mirror/upd/` (como `bad/`):
    - `api/releases/latest` = `v<X.Y.Z+1>`;
    - `download/v<X>` e `download/v<X.Y.Z+1>`;
    - `latest/download/install.sh`;
    - pré-release `v99.1.0` (fora do `latest`, com `prerelease.json`) e rascunho `drafts/v99.1.1`.
  - O wheel novo é o wheel do build com a versão trocada (`rebrand_wheel`: renomeia o `dist-info`, troca `Version:` no `METADATA` e refaz o `RECORD`). Não dá para copiar `src/` e buildar de novo, por causa dos symlinks de `package.json`, `plugin/…` e outros.
  - O `bob update` roda no projeto e no `HOME` do passo 8, por `run_bob`, com `env -i` e a mesma lista de variáveis de proxy e índice do `run_oneliner` (cópia; a U8 T4 junta as duas em `pass_env`).
  - Conferências do passo 10:
    - o comando único num projeto novo, no mesmo `HOME`, instala a `latest` e não a pré-release (US7.2 crit. 1);
    - `bob --version`;
    - `.bob-version`;
    - `current`;
    - hashes;
    - linhas `preserved:`.
  - O passo 11 confere: 1 linha "já está…", 1 pedido (`api`), `digest` do projeto igual.
  - `VERIFY_REMOTE=1` → "não se aplica" nos dois.
  - Alvos: o `bob update` do passo 10 ≤ 300 s; o passo 11 ≤ 30 s.
- **Passo 2 parcial (U7).** Depois de `check_gitleaks_install 2`, só no modo espelho: `bob --version` no projeto do passo 2 = `bob $X` e `project skills: $X (.agents/skills)`.
- **Ids finais** (depois das duas units): `STEP_IDS='1 2 3 4 5 6 7 8 9a 9b 10 11 12 13'`.
**Consequências.** O harness projetado fica em cerca de 232 + 150 (passos 10 e 11) + 60 (passo 13) ≈ 450 s no CI, abaixo de 900 s.

### ADR 0027 — Entrega em paralelo: CHANGELOG por unit e rebase mecânico
**Decisão.**
- **CHANGELOG.** Cada unit escreve no `CHANGELOG.md` só na ET que fecha a unit. Na U6 e na U7 é a T3; na U8, a T3 (docs) e a T4 (harness). Assim a U6 T1 e a U6 T2 não têm arquivo em comum e rodam em paralelo.
- **Âncoras fixas.** Pontos de inserção diferentes por unit, separados por pelo menos 1 linha que nenhuma das duas muda. Regras exatas de rebase em `u6-perfil-shell/shared-files-u6-u7.md`.
- **Ordem sugerida de merge.** U6 T1 e T2 (qualquer ordem), U7 T1, U7 T2, U6 T3, U7 T3 por último, com rebase.
**Consequências.** Entre os merges, a `main` fica algumas horas sem entrada no CHANGELOG para a T1 e a T2. A seção é `## Unreleased`, então isso não afeta release.

### ADR 0028 — Docs (U8): lista de arquivos, links e paridade
**Decisão.**
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
**Consequências.** A lista do CT17 sobe de 6 para 8 arquivos. É correção compatível: o doc pt-BR mudou de lugar no #174, e nenhuma consumidora implementou o teste. Os requisitos (FR8.4, US1.5 crit. 6) citam `docs/instalacao.md`. O plano registra o mapeamento e não edita o 2.3.

### ADR 0029 — U8: forma dos docs, do teste de paridade e do passo 14
**Decisão.**
- **Prompt.** O texto exato dos 2 arquivos fica num anexo da ET (`u8-docs/code-generation/tasks/T1-anexo/docs/`), gerado a partir do CT18. Só o bloco `perfil` muda, em 2 pontos: a troca da ADR 0021 e `S=${SHELL:-}` / `case "${S##*/}" in` no lugar de `case "${SHELL##*/}" in`. Com `set -u`, um `SHELL` ausente derrubava o bloco: conferido em `sh` e `dash`, 2026-10-22. O agente copia byte a byte (sha256 na ET).
- **"Bloco de shell"** (CT17, "primeiro bloco de código de instalação") = bloco cercado com info string `bash`, `sh`, `shell` ou `console`. Fica de fora o `mermaid` do README, que vem antes da instalação. Nos docs pt-BR, o comando único é a forma `… | sh -s -- --lang pt-BR` do CT2.
- **Seção `## Update` / `## Atualizar`** nos 4 docs de instalação, com `bob update` e `bob --version` (FR8.3), logo depois da alternativa.
- **Teste.** `tests/test_docs_pins.py` lê os pins pelas funções do pacote e o `install.sh` pelas fontes únicas. Entra na guarda de rede (`_UNIT_ARGS`).
- **Passo 14.**
  - `prompt_blocks` extrai os blocos com a mesma regex do CT18 para arquivos numerados.
  - `box_platform` usa a tabela do bloco `plataforma`.
  - `manifest` é um `python3 -c`.
  - O `pip freeze` é normalizado na linha `bob-quality @`.
  - `VERIFY_REMOTE=1` → "não se aplica".
  - Alvo ≤ 360 s.
- **Ordem.** T1 → T2 → T3 em sequência (mesmo arquivo de teste). A T4 roda depois da T1, em paralelo com a T2 e a T3. A T3 e a T4 escrevem no `CHANGELOG.md`: a que entra depois põe o parágrafo dela no topo (regra R-CL).
**Consequências.** O CT17 ganha a seção de atualizar e a definição de bloco de shell (esclarecimento compatível). O teste falha se o CT2 mudar uma fonte única sem o prompt acompanhar (FR8.5).

## Deltas de contrato (aprovados e aplicados em 2026-10-22 22:17 UTC-3)
| Contrato | Hoje | Proposta | Tipo | ADR |
|---|---|---|---|---|
| CT6, linha `BOB_INSTALL_PROFILE` | valores `<arquivo absoluto>`, `already-on-path`, `already-marked`, `failed:<arquivo>` | `already-marked` → `already-marked:<arquivo absoluto>`; `<arquivo>`, `already-marked:` e `failed:` exigem caminho que começa com `/`; resto ignorado | incompatível → v2 (sem v1 a manter) | 0021 |
| CT16 | "Arquivo já tem a marca → `already-marked`" | `already-marked:<arquivo>`; `<erro>` = texto depois do último `": "` da 1ª linha do stderr do shell, ou `unknown error`/`erro desconhecido`; en: `install: perfil: warning: could not write <arquivo> (<erro>). To use the bob command, add to your profile: export PATH="$HOME/.local/bin:$PATH".` | incompatível → v2 | 0021, 0022 |
| CT3, resumo | `already-marked` → `<arquivo> já tem…` | `already-marked:<arquivo>` → `<arquivo> já tem…`; textos en: `added ~/.local/bin to PATH in <arquivo>. Open a new terminal or run: . <arquivo>`, `~/.local/bin is already on PATH; nothing changed`, `<arquivo> already has the bob line; nothing changed`, `could not write <arquivo>; see the warning above`; linha também no resumo parcial | compatível (acompanha CT6 v2) | 0021, 0023 |
| CT2, linha `setup` | `exec env BOB_INSTALL_PROFILE=<r> "$BOB_HOME/bin/bob" setup --lang <l>` | `export BOB_INSTALL_PROFILE=<r>` + `exec "$BOB_HOME/bin/bob" setup --lang <l> </dev/null` | esclarecimento compatível | 0022 |
| CT4 | — | `manifest_skill_names(source: Path \| None = None) -> tuple[str, ...]`, `SourceError` se o manifesto é inválido | acréscimo compatível | 0024 |
| CT8, linha 3 | `project skills: <v> (.agents/skills)` / `not installed` / `mixed (<v1>, <v2>)` | mais `mixed (<v…>, not installed)` / `misturadas (<v…>, não instaladas)` quando uma parte falta (Q1 da U7, recomendação A); versões em ordem numérica | compatível (pendente da Q1) | 0024 |
| CT11 | erros de `download`/`integridade` sem texto; `--version` "antes da exigência de subcomando" | textos en/pt de `update.*` (tabela no `functional-design.md` da U7); `Accept` só na API; `--version` por `argparse.Action` + `Help`; versão do pacote por `importlib.metadata` | esclarecimento compatível | 0025 |
| CT15 | passos 10, 11 e 13 sem forma | `ensure_8`, `ensure_10`; `run_oneliner` com `${10}`/`${11}`; espelho `$T/mirror/upd/`; passo 2 com `bob --version`; mensagens `verify-install: passo <n>: …` (tabelas das ETs) | acréscimo compatível | 0026 |
| CT17 | 6 arquivos com `docs/instalacao.md` | 8 arquivos (ADR 0028); link por arquivo (`/install-prompt.pt-BR.md` na página pt-BR do site); regra de resolução do link no teste; seção `## Update` / `## Atualizar` nos 4 docs de instalação | correção compatível | 0028 |
| CT18, bloco `perfil` | `R=already-marked`; `case "${SHELL##*/}" in` | `R="already-marked:$F"`; `S=${SHELL:-}` + `case "${S##*/}" in` | acompanha CT6 v2; correção de bug (`set -u` com `SHELL` ausente) (CT18 v1 ainda não implementado) | 0021, 0028, 0029 |
| CT15, passo 14 | proposto, sem forma | `pass_env`, `box_platform`, `prompt_blocks`, `manifest`, `step_14`; `npm_config_cache=$T/npm-cache`; "não se aplica" com `VERIFY_REMOTE=1`; ≤ 360 s | acréscimo compatível | 0028, 0029 |

## Registro
- 2026-10-22 (UTC-3): proposta criada no 2.10 da U6/U7/U8, sobre `22d461a`.
- 2026-10-22 20:45 (UTC-3): ADR 0028 corrigida (link da página pt-BR com `/`, conferido no código do Docusaurus). ADR 0029 acrescentada (U8: estrutura dos docs, teste e passo 14). Pendente: Plan Approval conjunta da U6 e da U7; aviso ao Maestro sobre CT6/CT16 v2 antes do despacho da U6 T1 e T2.
- 2026-10-22 21:06 (UTC-3): U8 escrita (desenho, NFR, plano, ETs T1–T4, anexo do prompt). O anexo corrige o bloco `perfil` do CT18: com `set -u`, um `SHELL` ausente derrubava o bloco (`S=${SHELL:-}`, ADR 0029, delta CT18). Os testes da T1, da T2 e da T3 rodaram numa cópia local dos arquivos de `22d461a` (19, 47 e 69 passed). O passo 14 passa a ser sem `SHELL` (perfil em `~/.profile`). Delta CT15 (passo 14) acrescentado.
- 2026-10-22 22:19 (UTC-3): Plan Approval da U6 e da U7 aprovado (Emerson via Maestro). U7 Q1=A, U8 Q1=A. Despacho autorizado: U6 T1, U6 T2, U7 T1 sobre 22d461a. Pacotes em /workspace/dispatch/u6-t1, u6-t2, u7-t1. Pendente: promover ADRs 0021–0029 e deltas CT15/17/18 para decisions.md e contract-summary.md; despachar as 3 ETs.
- 2026-10-22 22:20 (UTC-3): ADRs 0021–0029 e deltas promovidos para `application-design/decisions.md` e `contracts/contract-summary.md`. Pacotes u6-t1, u6-t2, u7-t1 atualizados.
