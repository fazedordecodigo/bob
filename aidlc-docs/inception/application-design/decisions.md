# 2.6 Application Design — Decisões (ADRs)

Projeto: bob. Profundidade: Minimal. Data: 2026-10-18 (UTC-3).
Numeração continua a do repo (`docs/adr/0000` a `0007` existem). Na construção, cada ADR vira `docs/adr/00NN-*.md`.
Evidência do repo: `fazedordecodigo/bob` `main` @ `d2e26bd`. Fontes externas com data de acesso.

| ADR | Título | Resolve |
|---|---|---|
| 0008 | Fonte única das versões npm | P1; gap 5 |
| 0009 | Skills de projeto só em `.agents/skills` (pedido do Emerson, 18/10 18:25) | P3; gap 4 |
| 0010 | Skills, manifesto e LICENSE dentro do wheel | issue #45; gap 2 |
| 0011 | Distribuição por release do GitHub com assets | FR1.2, FR1.4; gap 1, 9 |
| 0012 | Comando único: `install.sh` + `bob setup` | FR1.1; gap 3 |
| 0013 | Instalação na conta do usuário e launcher estável | NFR7, FR5.2, FR1.1 (PATH, Q1 A); gap 1, 6 |
| 0014 | gitleaks 8.30.1 por plataforma | FR2.2, FR2.3; gap 8 |
| 0015 | Geração do `bob.yaml` e regra de `paths.include` | FR4.*; gap 11 |
| 0016 | Hook pre-push gerenciado | FR5.*; gap 6 |
| 0017 | Preservação, posse e idempotência | FR3.4, FR4.6, FR5.3, FR6.3, NFR4, NFR5; gap 7 |
| 0018 | Atualização e versão visível | FR6.*; gap 9 |
| 0019 | `bob doctor` confere só as ferramentas do bob | FR2.5, FR1.5 |
| 0020 | Docs com teste de paridade de versões | FR8.*; gap 10 |

---

## ADR 0008 — Fonte única das versões npm (P1)
**Contexto.**
- Hoje a versão do vitest está em três lugares: `package.json:15` (5.0.5), `src/bob_quality/doctor.py:70` (5.0.4) e `tests/test_npm_pin.py:30` (5.0.4).
- O bump do Dependabot (#180, `d2e26bd`) mudou só o `package.json` e o lock. O `bob doctor` saiu `4` no workflow `package` (run 39159800688, 2026-10-18 16:41 UTC-3).
- A faixa do Node também se repete: `package.json:6` e `doctor.py:62`.

**Decisão.**
- O `package.json` empacotado é a fonte única das versões npm e da faixa do Node.
- O doctor lê `dependencies` (exigindo `x.y.z`) e `engines.node` (exigindo `>=A.B.C <N`) do `package.json` do prefixo do plugin (`npm_prefix()`).
- `PINS` do doctor guarda só nome exibido, executável e pacote npm. Sem versão.
- `tests/test_npm_pin.py` deixa de ter a lista fixa. Confere: todo spec é `x.y.z`; o lock (`packages["node_modules/<n>"].version`) bate com o spec; o `package.json` da raiz e o do pacote são o mesmo.
- O `install.sh` repete as faixas de Python e Node (é shell, não lê o pacote antes de instalar). Um teste confere paridade com `pyproject.toml` e `package.json`.
- Correção imediata de P1: com a ADR, o doctor passa a esperar 5.0.5 sem editar número nenhum.

**Alternativas.**
- Doctor ler o `package-lock.json`: o lock tem a versão resolvida, mas mistura dependências transitivas. O `package.json` exato basta e o teste garante o lock igual.
- Só alinhar o número no doctor: resolve hoje e quebra no próximo bump.
- Gerar `doctor.py` no build: mais peças, sem ganho.

**Consequências.**
- Um bump do Dependabot passa a exigir só `package.json` e lock. O teste de paridade pega lock divergente.
- Erro de leitura do `package.json` vira `4` com mensagem que cita o arquivo.

## ADR 0009 — Skills de projeto só em `.agents/skills` (P3)
**Origem.** Pedido de mudança do Emerson no portão do 2.6, rodada 1, literal via Maestro (18/10/2026 18:25 UTC-3): "As skills devem ir para .agents/skills essa pasta é padrão para todos os agentes. Não precisa duplicar em várias pastas." Substitui a versão anterior desta ADR (`.claude/skills`).

**Contexto.** Fontes oficiais, todas reconferidas em 18/10/2026 (UTC-3):

| Agente | Pastas de projeto que a doc cita | Confirma `.agents/skills`? | Fonte oficial |
|---|---|---|---|
| Cursor | `.agents/skills/`, `.cursor/skills/`; e, "for compatibility", `.claude/skills/` e `.codex/skills/` | **Sim** | https://cursor.com/docs/skills |
| Claude Code | `.claude/skills/<skill>/SKILL.md` (projeto), `~/.claude/skills/` (pessoal), `<subdir>/.claude/skills/` | **Não**. A página não cita `.agents` em nenhum ponto (busca por `.agents` e `agents/skills`: 0 ocorrências) | https://code.claude.com/docs/en/skills |
| GitHub Copilot | `.github/skills`, `.claude/skills` ou `.agents/skills` | **Sim** | https://docs.github.com/en/copilot/concepts/agents/about-agent-skills ; https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills |
| Devin CLI | `.agents/skills/<name>/SKILL.md`, `.devin/skills`, `.windsurf/skills` (projeto) | **Sim** | https://docs.devin.ai/cli/extensibility/skills/overview |
| Devin web | `.agents/skills` (recomendada), `.devin`, `.github`, `.claude`, `.cognition`, `.windsurf`; "All six paths are scanned in every repo" | **Sim** | https://docs.devin.ai/product-guides/skills |

- `.agents/skills` é confirmada por 4 dos 5 alvos. O Claude Code é a exceção.
- Gravar em mais de uma pasta faz Cursor, Copilot e Devin acharem cada skill duas vezes (FR3.3). O Emerson pediu pasta única.

**Decisão.**
- O `bob setup` grava as skills só em `.agents/skills/<nome>/`.
- Usa o alvo `agents` que já existe no instalador (`src/bob_quality/install_skills.py:17-21`). Nenhum alvo novo. Os alvos `copilot` e `devin` ficam para uso manual (`devin` aponta para a mesma pasta).
- Sem `.claude/skills`, sem `.devin/skills`, sem symlink e sem cópia extra. Não há plano B de duplicação.
- `bob setup` avisa quando acha cópia do bob em `.claude/skills` ou `.github/skills` (duplicata provável, ex.: instalação antiga ou manual). Não apaga (FR3.4).
- Se um risco abaixo se confirmar, a saída é levar ao Emerson. A pasta não muda sem nova decisão dele.

**Alternativas.**
- Só `.claude/skills` (versão anterior desta ADR): citada por 4 dos 5 docs (falta o Devin CLI), e o Cursor a lê só "for compatibility". Cobriria o Claude Code pela doc. Rejeitada pelo Emerson.
- `.agents/skills` + `.claude/skills` (cópia ou symlink): cobre o Claude Code pela doc, mas duplica em Cursor, Copilot e Devin web. Rejeitada pelo Emerson ("Não precisa duplicar").
- `.agents/skills` + `.devin/skills`: duplica no Devin web. Rejeitada.

**Consequências e riscos.**
- A fala do Emerson diz que `.agents/skills` "é padrão para todos os agentes". As docs confirmam para 4 dos 5; para o Claude Code, não (Risco 1).
- Fica alinhada à ADR 0004 do repo (alvos `agents`/`devin`, "Claude Code não tem alvo").
- **Risco 1 (Claude Code), alto — ACEITO pelo Emerson** em 18/10/2026 18:31 UTC-3, literal via Maestro: "Aceito o risco no Claude Code e mantenho .agents/skills." A doc oficial do Claude Code só cita `.claude/skills`. Pela doc, o Claude Code **não** acharia as skills do bob em `.agents/skills`. Situação real: **Não verificado**. Em tensão com FR3.2, US2.1 crit. 1 e o critério 2 do intent (ver `traceability.md`, "Impacto da ADR 0009"). A pasta continua `.agents/skills`; a verificação manual por release continua valendo para o Claude Code.
- **Risco 2 (Cursor, Copilot, Devin CLI, Devin web), baixo.** As docs confirmam `.agents/skills`. Falta ver na prática.
- Verificação: manual a cada release, nos 5 agentes (`verification-command.md`, "Verificação manual por release"). No projeto do passo 2, listar as skills em cada agente. Evidência (data UTC-3, versão do bob, versão do agente, saída do terminal ou captura de tela) em `docs/release-checks/vX.Y.Z.md`, no PR da release.
- Gatilho: algum dos 5 agentes não lista uma ou mais das três skills (`bob-check`, `harden`, `review-report`), ou lista em duplicata.
- Resposta ao gatilho: registrar em `docs/release-checks/vX.Y.Z.md` e levar ao Emerson, com a evidência. Sem mudar a pasta e sem duplicar por conta própria.
- `bob --version` e `bob doctor` mostram a versão das skills lida de `.agents/skills/<skill>/.bob-version`.

## ADR 0010 — Skills, manifesto e LICENSE dentro do wheel (issue #45)
**Contexto.** O wheel não leva `skills/` nem `.claude-plugin/` (`pyproject.toml:42-43`; log do run 39159800688). O instalador fora de clone sai `4` e pede `--source` (`install_skills.py:147-150`).

**Decisão.**
- Pasta `src/bob_quality/plugin/` com três symlinks no git: `.claude-plugin` → `../../../.claude-plugin`, `skills` → `../../../skills`, `LICENSE` → `../../../LICENSE`.
- `package-data` acrescenta `plugin/.claude-plugin/plugin.json`, `plugin/skills/**/*` e `plugin/LICENSE`.
- `install_skills` resolve a fonte: `--source`; senão `parents[2]` se tiver manifesto (clone); senão `bob_quality/plugin/` (pacote).
- Teste de empacotamento abre o wheel e confere as três `SKILL.md`, o `plugin.json` e o `LICENSE`.
- Fecha a issue #45 (o texto dela sobre NOTICE do Pocock está superado pela ADR 0004).

**Alternativas.** Copiar as skills para `src/` (duas cópias no repo); hook de build customizado (mais código); baixar as skills do GitHub na instalação (mais rede e outra conferência).

**Consequências.**
- Symlink de arquivo já funciona no build (`package.json`). Symlink de **diretório** em `package-data`: **Não verificado**. O teste do wheel pega a falha. Plano B: trocar o symlink `skills` por symlinks por arquivo.

## ADR 0011 — Distribuição por release do GitHub com assets
**Contexto.**
- FR1.2: direto do GitHub, sem PyPI. FR1.4 e G-2.3: só release publicada conta.
- A API `GET /repos/{owner}/{repo}/releases/latest` devolve "the most recent non-prerelease, non-draft release" (https://docs.github.com/en/rest/releases/releases, acessada em 2026-10-18).
- O link `/releases/latest/download/<asset>` baixa o asset da última release (https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases, acessada em 2026-10-18).
- O repo não tem tags nem releases (2.1).

**Decisão.**
- Cada release leva três assets: `install.sh`, `bob_quality-<v>-py3-none-any.whl` e `SHA256SUMS` (dos outros dois).
- Comando do dev: `curl -fsSL https://github.com/fazedordecodigo/bob/releases/latest/download/install.sh | sh`.
- O `install.sh` acha a versão pela API `releases/latest` (ou `BOB_VERSION`) e baixa o wheel e o `SHA256SUMS` dessa tag.
- Tag no formato `vX.Y.Z`. A versão do wheel é a da tag (o workflow confere `pyproject.toml` = tag).
- `BOB_RELEASES_URL` troca a base de API e downloads. Uso: testes e espelho. Padrão: GitHub.
- O workflow `release` (C11) cria a release com os assets, depois do `bob doctor` e do `verify-install.sh`. Disparo manual pelo Emerson (P2).

**Alternativas.** `pip install git+https://...@tag` direto (sem `install.sh` não há como conferir Python/Node antes nem criar launcher); pipx/uv (não são pré-requisitos); script em `raw.githubusercontent.com/.../main` (a `main` pode estar quebrada, como hoje).

**Consequências.**
- A API sem token tem limite por IP (Não verificado o número atual). Erro 403/429 vira `4` com ação "tente de novo ou defina `BOB_VERSION`".
- Release sem os três assets quebra a instalação. O workflow é o único caminho de criar release.

## ADR 0012 — Comando único: `install.sh` + `bob setup`
**Contexto.** Não há comando único (2.1). A ADR 0004 diz que o instalador de skills não é subcomando de `bob` (`docs/adr/0004-empacotamento-quatro-agentes.md:23`).

**Decisão.**
- `install.sh` cuida só do que precede o pacote: SO, arquitetura, Python, Node, versão, wheel, venv, launcher.
- `bob setup` (subcomando novo) cuida do projeto, na ordem fixa de C02.
- `install.sh` termina com `exec bob setup`. O dev vê um comando só.
- `python -m bob_quality.install_skills` continua existindo. `bob setup` o chama como biblioteca.
- Supera a ADR 0004 só no ponto "não é subcomando": a instalação do projeto passa a ser subcomando.

**Alternativas.** Tudo em shell (difícil testar, duplica lógica do doctor); tudo em Python sem bootstrap (sem como conferir Node e criar venv antes).

**Consequências.** `bob setup` também serve para configurar outro projeto já com o bob instalado.

## ADR 0013 — Instalação na conta do usuário e launcher estável
**Contexto.** NFR7: sem `sudo`. FR2.4: não mexer nas dependências do projeto. FR5.2: hook sem ativar ambiente. O hook atual chama `bob` pelo `PATH` (`src/bob_quality/hooks/pre-push:5`).

**Decisão.**
- `BOB_HOME` = `$BOB_HOME` ou `${XDG_DATA_HOME:-$HOME/.local/share}/bob-quality`.
- `BOB_HOME/versions/<v>/venv`: um venv por versão. As ferramentas npm vão para o pacote dentro desse venv (`bob doctor --install`, como hoje).
- `BOB_HOME/current` → `versions/<v>`, trocado por rename atômico só depois do venv pronto.
- `BOB_HOME/bin/bob` → `current/venv/bin/bob`. Caminho estável usado pelo hook.
- `~/.local/bin/bob` → `BOB_HOME/bin/bob`.
- `PATH` do shell (Q1 A, `application-design-questions.md`). Quem faz: `install.sh` (C01), depois do passo `pacote` e antes do `bob setup`.
  - Precisa? Só se `:$PATH:` não contém `:$HOME/.local/bin:`. Se contém, não toca em nada.
  - Shell: nome base de `$SHELL` (shell de login do usuário). Não usa o shell que roda o `install.sh`, porque o one-liner roda em `sh`.
    - `zsh` → `${ZDOTDIR:-$HOME}/.zshrc`.
    - `bash` → `~/.bashrc`.
    - qualquer outro ou `$SHELL` vazio → `~/.profile`.
  - Linha (uma só, com a marca no fim):
    `export PATH="$HOME/.local/bin:$PATH" # managed-by: bob-quality`
  - Idempotência: se o arquivo já tem `# managed-by: bob-quality`, não escreve. Repetir não duplica a linha.
  - Perfil não existe: cria o arquivo só com a linha (modo `0644`). Não cria o perfil de outro shell.
  - Perfil existe: acrescenta no fim. Se o arquivo não termina em quebra de linha, põe uma antes. O conteúdo anterior fica byte a byte igual.
  - Perfil é symlink (gerenciador de dotfiles): escreve no destino, como o shell leria.
  - Não consegue gravar (permissão ou disco): não falha a instalação. Avisa e mostra a linha para colar. Código de saída segue o do `bob setup`. O hook e o `bob setup` não dependem do `PATH` (usam `BOB_HOME/bin/bob`).
  - Resumo: o `install.sh` passa o resultado ao `bob setup` pela variável interna `BOB_INSTALL_PROFILE` (`<arquivo>`, `already-on-path`, `already-marked` ou `failed:<arquivo>`). O resumo ganha a linha `perfil do shell:` (texto em `component-interfaces.md`).
  - `bob update` não mexe no perfil: o caminho do launcher não muda.
- Versões antigas: ficam. Desinstalar está fora de escopo.

**Alternativas.** Venv no projeto (`.venv` do dev: fere FR2.4); `pip install --user` (mistura com o Python do sistema; PEP 668 bloqueia).

**Consequências.**
- Ubuntu sem `python3-venv` faz `python3 -m venv` falhar. O `install.sh` confere antes e cita o pacote do SO a instalar (fora do comando, é pré-requisito I-S1).
- O `PATH` só vale num terminal novo ou depois de `. <arquivo>`. O resumo diz isso.
- Risco aceito: no macOS, bash de login lê `~/.bash_profile`, não `~/.bashrc`. O shell padrão do macOS é zsh, e o caso bash no macOS não é coberto. O aviso do resumo mostra a linha e o arquivo, para o dev ajustar.
- Shells com outra sintaxe (ex.: fish) caem em `~/.profile`, que eles não leem. Mesma mitigação: o resumo mostra a linha.

## ADR 0014 — gitleaks 8.30.1 por plataforma
**Contexto.** RE-Q1 A, FR2.2, FR2.3. O doctor só conhece `linux_x64` (`doctor.py:91-97`).
Fonte: release oficial https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1 e o arquivo https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_checksums.txt, baixado no box em 2026-10-18. Os quatro valores abaixo batem com o campo `digest` da API de releases do GitHub para o mesmo asset. A release é publicada (não pré-release, não rascunho), de 2026-03-20 23:17 UTC-3.

| Plataforma (`uname -s`/`uname -m`) | Asset | sha256 |
|---|---|---|
| Linux / `x86_64` | `gitleaks_8.30.1_linux_x64.tar.gz` | `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb` |
| Linux / `aarch64`, `arm64` | `gitleaks_8.30.1_linux_arm64.tar.gz` | `e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080` |
| Darwin / `x86_64` | `gitleaks_8.30.1_darwin_x64.tar.gz` | `dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709` |
| Darwin / `arm64` | `gitleaks_8.30.1_darwin_arm64.tar.gz` | `b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5` |

URL de cada um: `https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/<asset>`. O valor de Linux x64 é o mesmo de `doctor.py:96`.

**Decisão.**
- A tabela acima vive só em `src/bob_quality/gitleaks.py`. Doctor e setup importam dela.
- O sha256 fica no código do bob. Não se baixa o `checksums.txt` na instalação (ele viria da mesma origem do binário).
- Fluxo: baixar para temporário → conferir sha256 → extrair só o membro `gitleaks` (sem caminho, sem link) → `chmod 0755` → mover para `BOB_HOME/tools/gitleaks/8.30.1/gitleaks` → ligar `BOB_HOME/bin/gitleaks`.
- Plataforma fora da tabela: `4`, com a lista suportada.
- `BOB_GITLEAKS_BASE_URL` troca a base de download (espelho e teste do caminho de falha).

**Alternativas.** Pedir ao dev (rejeitado por RE-Q1 A); `brew`/gerenciador do SO (não existe em toda máquina; pode pedir `sudo`); `go install` (exige Go).

**Consequências.** Trocar a versão do gitleaks exige editar só a tabela e os 4 sha256.

## ADR 0015 — Geração do `bob.yaml` e regra de `paths.include`
**Contexto.** FR4.1–FR4.5, RE-Q2 B. O padrão `include: [src]` sai `4` num projeto sem `src/` (`config.py:428-434`). A detecção de linguagem existente usa os sufixos de `_SUFFIX_LANGUAGE` e `_excluded` (`config.py:320-326`, `:387-425`).

**Decisão — conteúdo.**
- Chaves e valores do README (`README.pt-BR.md:182-203`): `base: origin/main`, `language: en`, `paths.exclude: [tests, node_modules, dist]`, `crap`, `duplication`, `coverage`, `dependencies`.
- A chave `languages` não é gravada. Omitida, ela é detectada, que é o padrão documentado (`README.pt-BR.md:180`).
- `paths.include`: regra abaixo.

**Decisão — regra exata de `paths.include`.**
1. Arquivos candidatos: saída de `git ls-files --cached --others --exclude-standard` (rastreados e não ignorados). Assim `node_modules`, `.venv` e afins ignorados pelo `.gitignore` ficam fora.
2. Arquivo de código: sufixo em `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs` (os mesmos de `_SUFFIX_LANGUAGE`). Symlinks não contam.
3. Descarta todo arquivo cujo caminho casa com `paths.exclude` padrão, pela mesma função `_excluded` (prefixo ou componente).
4. Pastas candidatas: o primeiro componente do caminho de cada arquivo que sobrou. Pastas que começam com `.` não contam.
5. Se `src` está entre as candidatas: `include: [src]` (o padrão do README).
6. Senão, se há candidatas: todas, em ordem alfabética.
7. Senão, se há arquivo de código na raiz: `include: ["."]`.
8. Senão (nenhum código): `include: ["."]` e aviso "nenhuma pasta de código encontrada" no resumo (FR4.5).

**Decisão — validação.**
- Gera o texto, grava num temporário no projeto, chama `load_config(temp, cwd)`. Passa por `config.py:428-434` porque toda pasta listada veio de arquivos que existem, e `.` sempre existe.
- `ConfigError` aqui é bug: não grava `bob.yaml`, sai `4` com a mensagem do erro.
- Só então rename atômico para `bob.yaml`.

**Alternativas.** Listar todas as pastas com código mesmo com `src/` (aumenta o escopo do gate em relação ao padrão); varrer o disco sem `git` (pega `node_modules` e `.venv` não excluídos).

**Consequências.**
- `include: ["."]` com o resto do padrão: aceito por `load_config` pela leitura do código; **Não verificado** em execução nos gates. O 3.6 testa `bob check` nesse caso.
- `base: origin/main` não é adaptado. Projeto com outra branch padrão mantém o padrão do README (FR4.2).

## ADR 0016 — Hook pre-push gerenciado
**Contexto.** FR5.1–FR5.3. Hoje é `cp` manual e o hook chama `bob` pelo `PATH`.

**Decisão.**
- Destino: `$(git rev-parse --git-path hooks)/pre-push`.
- `git config --get core.hooksPath` definido: não escreve. Aviso com a linha a pôr no gerenciador de hooks do projeto. Conta como "hook preservado".
- Arquivo existente sem a linha `# managed-by: bob-quality`: preservado, com aviso (FR5.3).
- Arquivo com a linha: reescrito só se o conteúdo difere.
- Template:
  ```sh
  #!/bin/sh
  # managed-by: bob-quality
  set -e
  unset PYTEST_ADDOPTS
  unset PYTEST_PLUGINS
  BOB="<BOB_HOME absoluto>/bin/bob"
  [ -x "$BOB" ] || BOB=bob
  exec "$BOB" check --gates crap,dry,deps </dev/null
  ```
- O caminho é o launcher estável (ADR 0013). Atualizar não muda o hook.

**Alternativas.** `core.hooksPath` próprio (muda config do repo e quebra outros hooks); hook versionado no projeto (exige editar arquivos do dev).

**Consequências.** O hook do bob roda o mesmo comando de hoje. O alvo de NFR8 (< 60 s, `tests/test_hook.py`) segue válido.

## ADR 0017 — Preservação, posse e idempotência
**Contexto.** I-S2, R-S3 (preservar e avisar, sem perguntar), FR3.4, FR6.3, NFR4, NFR5.

**Decisão.**
- O bob só escreve no que é dele: pasta de skill com `.bob-version`, hook com `# managed-by: bob-quality`, `bob.yaml` que ele cria quando não existe.
- Nunca escreve em `bob.yaml` existente, `.bob/waivers.yaml`, hook alheio, skill sem marcador, manifestos e lockfiles do projeto.
- Toda escrita compara antes. Igual: não escreve. Segunda execução seguida: 0 arquivos alterados.
- Todo item preservado entra no resumo, com o motivo.
- Escritas por arquivo temporário + rename.

**Alternativas.** Manifesto de instalação único em `.bob/` (mais um arquivo e estado a reconciliar); comparar com hash de versões conhecidas (exige tabela de hashes por release).

**Consequências.** Uma skill do bob editada à mão pelo dev (com marcador) é sobrescrita na atualização. O resumo avisa. A marca está documentada.

## ADR 0018 — Atualização e versão visível
**Contexto.** FR6.1–FR6.5, US5.1, US5.2, US7.2.

**Decisão.**
- `bob update`: lê a última release publicada (ADR 0011). Compara `vX.Y.Z` como tupla de inteiros com a versão do pacote (`importlib.metadata`).
- Igual: "já está na release mais nova", 0 arquivos alterados, sai `0`.
- Mais velha que a instalada: mesma mensagem, sai `0`.
- Mais nova: baixa `install.sh` e `SHA256SUMS` dessa tag, confere, roda com `BOB_VERSION=<tag>` na pasta atual. O `bob setup` da versão nova atualiza as skills com marcador e preserva o resto.
- `bob --version`: duas linhas: versão do pacote; versão das skills em `.agents/skills` (lida de `.bob-version`) ou "skills não instaladas neste projeto".
- O mesmo `curl ... | sh` também atualiza (pega a última). `bob update` é o atalho documentado.

**Alternativas.** Atualizar só o pacote com pip (não atualiza skills); seguir a `main` (rejeitado em RQ-Q1 A).

**Consequências.** "Projeto na release antiga" = `.bob-version` antigo nas skills. Pacote novo e skills velhas num projeto não reconfigurado: o `bob --version` mostra a diferença.

## ADR 0019 — `bob doctor` confere só as ferramentas do bob
**Contexto.** O doctor procura npm primeiro em `Path.cwd()/node_modules` (`doctor.py:358-360`) e binários em `Path.cwd()/node_modules/.bin` (`doctor.py:437-441`). Num projeto com vitest próprio, ele compara a versão do projeto (FR2.5).

**Decisão.**
- npm: só o prefixo do plugin (`npm_prefix()`), por `package.json` do pacote em `node_modules/<nome>`. Sem `cwd` e sem executável no `PATH`.
- Binários (gitleaks): `BOB_HOME/bin`, depois `PATH`.
- Python: sem mudança (lê do próprio venv).
- `--install`: npm e gitleaks.

**Alternativas.** Manter o `cwd` como fallback (é a causa do problema).

**Consequências.** Quem rodava o bob num clone com `npm ci` na raiz segue funcionando: no checkout editável o prefixo é a raiz (`docs/instalacao.md:43`).

## ADR 0020 — Docs com teste de paridade de versões
**Contexto.** Divergências 2 a 7 do 2.1 (`technology-stack.md`). FR8.1–FR8.3.

**Decisão.**
- Caminho principal nos READMEs e docs: o `curl ... | sh`, depois `bob update` e `bob --version`. O caminho com clone vira seção "Desenvolvimento".
- Requisitos: Python e Node com as faixas reais; gitleaks vem pelo comando; `python3-venv` no Ubuntu.
- `tests/test_docs_pins.py`: toda ocorrência `nome==x` ou `nome@x` ou "nome x.y.z" de uma ferramenta pinada nos docs listados em C12 bate com `pyproject.toml`/`package.json`. Também confere que a lista de ferramentas nos docs é completa.

**Alternativas.** Gerar os trechos de docs (mais tooling); revisão manual (é como divergiu).

**Consequências.** Bump de dependência passa a exigir doc certa, ou o teste falha.
