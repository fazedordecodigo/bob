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
- `include: ["."]` com o resto do padrão: aceito por `load_config`. Medido em 2026-10-20 (passo 0 da T2, PR #196, `main` @ `0d85510`): sem código, `crap` e `coverage` saíam `4` (`coverage.py: No data to report.`); `dry` e `deps` saem `0`. Decisão do Emerson (Q1 = A, 2026-10-20 21:18 UTC-3): sem código a medir, `crap` e `coverage` ficam ⏭️ `not_run` com o motivo "no code to measure" / "nenhum código a medir" e contribuem `0` (T1b). "Sem código" = `config.detect_languages(cwd, include, exclude)` vazio (mesmos sufixos e exclusão desta ADR, sem seguir symlink). Com código, erro de coverage segue `4`.
  - Emenda E1 (T1b), aprovada pelo Emerson em 2026-10-20 21:42 UTC-3 ("Aprovo a T1b e as emendas E1 a E3, com a T1c separada para a E4."); origem: Q1 = A e `construction/u4-bob-yaml/code-generation/tasks/T1b-emenda.md`.
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

**Complemento (U5, 3.5, 2026-10-22, UTC-3).** Refinamento compatível, decidido pelo Arquiteto no plano da U5 (`construction/u5-hook-pre-push/code-generation/code-generation-plan.md`, D1–D9); nada acima muda.
- Ordem: confere o caminho → `git config --get core.hooksPath` (saída `0` preserva; `1` segue; outra é erro de ferramenta) → `git rev-parse --git-path hooks` → decide → grava.
- Caminho do launcher: absoluto e sem `"`, `$`, `` ` ``, `\` ou quebra de linha (o que o `sh` não lê literal entre aspas duplas). Senão, o passo `hook` falha com saída `4` e nada é gravado.
- Link (mesmo para um hook do bob) e pasta no lugar de `pre-push`: preservados sem leitura, com aviso (ADR 0017).
- "Difere" inclui o modo: hook do bob com os mesmos bytes e modo ≠ `0755` é regravado.
- Gravação por `pre-push.tmp-<pid>` na mesma pasta + `os.replace`; o temporário é apagado em qualquer falha.
- Hook preservado e `core.hooksPath` aparecem na linha `preservado:` **e** como aviso com a linha a acrescentar (FR5.3).
- O hook estático `src/bob_quality/hooks/pre-push` fica (caminho manual dos docs, que a U8 atualiza); um teste prende o comando dele ao do template.

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

## ADR 0021 — `BOB_INSTALL_PROFILE` leva o arquivo também em `already-marked`
**Contexto.** O CT6 e o CT16 dão os valores `<arquivo>`, `already-on-path`, `already-marked` e `failed:<arquivo>`. Mas o texto aprovado do resumo (CT3) e o passo 13 do Comando de Verificação pedem `<arquivo> já tem a linha do bob; nada mudou`. Com `already-marked` sozinho, o `bob setup` não sabe qual arquivo citar. A outra saída seria o Python refazer a regra de `$SHELL`/`ZDOTDIR`, o que duplica a ADR 0013 em duas linguagens.
**Decisão.** O valor passa a ser `already-marked:<arquivo absoluto>`. Os outros três ficam iguais. O `bob setup` aceita só estes 4 formatos. Qualquer outro, inclusive `already-marked` sem arquivo, é ignorado (sem linha).
**Consequências.** É mudança de formato numa variável lida por máquina, então é incompatível: CT6 (linha `BOB_INSTALL_PROFILE`) e CT16 sobem para v2. Não há v1 a manter, porque nenhuma consumidora implementou o valor ainda. O bloco `perfil` do prompt (CT18, U8) grava `R="already-marked:$F"` (ver ADR 0028). **Aviso ao Maestro antes da ET**, porque o CT6 e o CT16 estão aprovados.

## ADR 0022 — Passo `perfil` do `install.sh`: forma da escrita, do aviso e da passagem do resultado
**Decisão.**
- `PROFILE_LINE` é a 2ª fonte única do topo (linha 5, logo depois de `STEPS`). A marca (`# managed-by: bob-quality`) e a linha para colar (`export PATH="$HOME/.local/bin:$PATH"`) saem dela por expansão (`"#${PROFILE_LINE#* #}"` e `${PROFILE_LINE%% #*}`). O literal da marca não se repete no script.
- O aviso de falha vai para o stdout (como o `launcher_warning`), em en e pt-BR. O `<erro>` do CT16 é o texto depois do último `": "` da 1ª linha do stderr do shell ao abrir ou criar o arquivo. Exemplos: `Permission denied` (dash e bash) e `Directory nonexistent` (dash). Sem texto, vira `unknown error` / `erro desconhecido`, como no `launcher_try`.
- Falha ao criar, ao fazer `chmod 0644` ou ao acrescentar: todas dão `failed:<arquivo>`. O passo nunca chama `fail` e sempre imprime `install: perfil: ok`.
- O resultado vai para o filho por `export BOB_INSTALL_PROFILE="$profile_result"` e depois `exec "$bob_root/bin/bob" setup --lang "$bob_lang" </dev/null`. Não usa `exec env …`: o efeito é o mesmo e não traz o binário `env` para a lista de ferramentas.
- `tail` e `chmod` entram na lista de utilitários usados (POSIX base). O passo `ferramentas` não os confere, como não confere `mkdir`, `ln` e `awk`.
**Consequências.** O CT2 ganha um esclarecimento compatível na linha `setup`. Root escreve em arquivo só leitura, então o caso (e) do passo 13 não reproduz como root. O harness recusa rodar como root no passo 13 (ADR 0026).

## ADR 0023 — Linha `perfil do shell` no resumo do `bob setup`
**Decisão.** A função privada `setup_cmd._profile_text(value)` mapeia o valor de `BOB_INSTALL_PROFILE`:
- `already-on-path` → `setup.profile_on_path`;
- `already-marked:/…` → `setup.profile_marked`;
- `failed:/…` → `setup.profile_failed`;
- `/…` → `setup.profile_added`;
- vazio, ausente, relativo ou outro valor → nada.

A linha (`setup.profile`) sai em `_summary`, antes de `  bob doctor:`, também no resumo parcial (`_fail`). Lê `os.environ` dentro de `_summary`. As chaves novas entram em `messages.py` logo depois de `setup.doctor_not_run` (en e pt-BR).
**Consequências.** Nada muda sem a variável: os testes atuais do resumo seguem iguais. Os textos en são tradução dos pt aprovados no CT3.

## ADR 0024 — Versão das skills do projeto: módulo `project_version`
**Decisão.**
- Módulo novo `src/bob_quality/project_version.py` (parte de C10). Lê `<projeto>/.agents/skills/<nome>/.bob-version` só para os nomes do manifesto empacotado.
- Função pública nova `install_skills.manifest_skill_names(source=None) -> tuple[str, ...]`. É um acréscimo compatível ao CT4.
- Um arquivo vale só se é regular (não symlink) e o conteúdo casa exatamente `\d+\.\d+\.\d+\n`. Erro de leitura, symlink ou conteúdo fora disso contam como ausente.
- Estados: `installed` (todas as skills com a mesma versão); `not_installed` (nenhuma válida, manifesto ilegível ou lista vazia); `mixed` (versões diferentes, ordenadas como tupla numérica, sem repetição). Uma parte ausente e outra válida também é `mixed`, com o marcador `missing` (recomendação A da Q1 da U7).
- O `bob doctor` acrescenta a linha `project skills:` no fim da saída normal, dentro de `_report_pins`, com o `cwd`. Ela não muda o código de saída. Sai só quando os pins foram lidos (no erro do `package.json` continua 0 linhas no stdout).
- O módulo fica separado de `update.py` para evitar o ciclo `doctor → update → setup_cmd → doctor`.
**Consequências.** O `bob --version` e o doctor usam a mesma linha (CT8 = CT11). Q1 pendente: se a resposta não for A, só os textos de `mixed` mudam (ET v2 da U7 T1).

## ADR 0025 — `bob update` e `bob --version`: implementação
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

## ADR 0026 — Harness: passos 10, 11 e 13 e o passo 2 parcial
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

## ADR 0027 — Entrega em paralelo: CHANGELOG por unit e rebase mecânico
**Decisão.**
- **CHANGELOG.** Cada unit escreve no `CHANGELOG.md` só na ET que fecha a unit. Na U6 e na U7 é a T3; na U8, a T3 (docs) e a T4 (harness). Assim a U6 T1 e a U6 T2 não têm arquivo em comum e rodam em paralelo.
- **Âncoras fixas.** Pontos de inserção diferentes por unit, separados por pelo menos 1 linha que nenhuma das duas muda. Regras exatas de rebase em `u6-perfil-shell/shared-files-u6-u7.md`.
- **Ordem sugerida de merge.** U6 T1 e T2 (qualquer ordem), U7 T1, U7 T2, U6 T3, U7 T3 por último, com rebase.
**Consequências.** Entre os merges, a `main` fica algumas horas sem entrada no CHANGELOG para a T1 e a T2. A seção é `## Unreleased`, então isso não afeta release.

## ADR 0028 — Docs (U8): lista de arquivos, links e paridade
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

## ADR 0029 — U8: forma dos docs, do teste de paridade e do passo 14
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

## ADR 0030 — `VERIFY_DIST` no harness `scripts/verify-install.sh` (U9)
**Contexto.** O CT13 exige que o job `verify` do `.github/workflows/release.yml` rode o Comando de Verificação (CT15) nas 4 plataformas "com os assets do run" gerados pelo job `check`. Em `scripts/verify-install.sh`, `build_wheel()` constrói um wheel novo em `$T/build-venv`. Sem aceitar um diretório externo, cada runner do `verify` construiria outro wheel em vez de testar o artefato exato que `publish` anexará à release.
**Decisão.** Adição retrocompatível ao CT15 (`v1.1`). Em `build_wheel()`, logo após `WHL="bob_quality-$X-py3-none-any.whl"`: se `VERIFY_DIST` não estiver vazio (`[ -n "${VERIFY_DIST:-}" ]`), o harness exige `[ -f "$VERIFY_DIST/$WHL" ]` (senão `die_preparo "VERIFY_DIST sem $WHL"`), cria `$T/dist`, copia `$VERIFY_DIST/$WHL` para `$T/dist/$WHL` e retorna `0` sem criar `build-venv`. Quando `VERIFY_DIST` está vazio ou ausente, o comportamento padrão não muda.
**Alternativas consideradas.** (a) Reconstruir o wheel em cada runner do `verify`: não garante reprodutibilidade byte a byte nem testa o artefato real do job `check`. (b) Usar `VERIFY_REMOTE=1`: exige release já publicada e pula os passos de espelho (9a, 9b, 10, 11, 14).
**Consequências.** CT15 passa para `v1.1` (adição compatível). Aprovada pelo Emerson em 24/10/2026 12:41 (UTC-3) na Plan Approval da U9.
