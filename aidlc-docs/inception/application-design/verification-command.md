# 2.6 Application Design — Proposta do Comando de Verificação

Status: proposta do Arquiteto. A aprovação é no 2.9 (campo "Comando de verificação aprovado" do `aidlc-state.md`).

## Comando
Numa máquina limpa (runner padrão, usuário sem `sudo`), na raiz de um checkout do bob:
```sh
python3 -m venv /tmp/dev && /tmp/dev/bin/pip install -e '.[dev]' && /tmp/dev/bin/pytest \
  && sh scripts/verify-install.sh
```
- `pytest`: suíte do repo, com os testes novos de paridade (ADR 0008, 0020) e do wheel (ADR 0010).
- `scripts/verify-install.sh` (novo, C11): prova os critérios do intent de ponta a ponta. Sai `0` só se todos os passos passam; senão `1`, com o número do passo.
- Modo pré-release (padrão): faz `python -m build`, gera `SHA256SUMS`, serve `dist/` e um `releases/latest` falso num servidor local (`python3 -m http.server`) e usa `BOB_RELEASES_URL`. Assim prova a release antes de publicá-la.
- Modo pós-release: `VERIFY_REMOTE=1 sh scripts/verify-install.sh` usa o GitHub de verdade.
- Matriz: Linux x64, Linux arm64, macOS x64, macOS arm64 (NFR3). Rótulos de runner a fixar no 3.7 (Não verificado agora).

Todo passo roda com `HOME` temporário e `PATH=/usr/bin:/bin:<node>:<python>` (sem venv do bob), para simular máquina limpa.

## Passos
| # | Passo | Verifica | Esperado |
|---|---|---|---|
| 1 | Node falso 20.0.0 na frente do `PATH`; rodar o comando único num projeto novo | US1.2; FR7.3; NFR9 | sai ≠ 0; stderr cita `node`, a versão achada e `>=22.18.0 <23`; hash dos arquivos do projeto igual ao de antes |
| 2 | Projeto novo (R-S8: `git init`, `src/app.py`, 1 commit); `time` do comando único | intent C1, C6; US1.1 crit. 1–3; NFR1; NFR2 | sai `0`; duração ≤ 300 s; última linha do resumo `bob doctor: 0`; `bob --version` = versão da release; nenhum `git clone` no log |
| 3 | `sudo` falso no `PATH` que só grava um log | NFR7; US1.1 crit. 4 | log do `sudo` vazio |
| 4 | Skills só em `.agents/skills`, uma cópia | intent C2; US2.1; FR3.1–3.3; ADR 0009 | `.agents/skills/{bob-check,harden,review-report}/SKILL.md` e `.bob-version` existem; nenhuma skill do bob em `.claude/skills`, `.github/skills`, `.cursor/skills`, `.devin/skills`; nenhum symlink para elas |
| 5 | `bob check --base HEAD --gates crap,dry,deps` em três projetos: com `src/`; com código só em `app/`; sem código | intent C3; US3.1; FR4.1–4.5 | código ≠ `4` nos três; `paths.include` = `[src]`, `[app]`, `["."]`; aviso "nenhuma pasta de código" só no terceiro; todas as outras chaves iguais ao README |
| 6 | Remoto bare local; commit novo; `git push` com `env -i HOME=$HOME PATH=/usr/bin:/bin` | intent C4; US4.1; FR5.1, FR5.2 | o push dispara o hook; a saída tem o relatório do `bob check`; sai `0` |
| 7 | Rodar o comando único de novo no mesmo projeto | NFR4; US1.1 crit. 6 | sai `0`; hash de todos os arquivos do projeto igual |
| 8 | Projeto com `bob.yaml`, hook próprio, `.bob/waivers.yaml`, `.agents/skills/outra/SKILL.md` e `package.json` com vitest 4.x e `node_modules` instalado | critério 7 dos requisitos; US3.2; US1.4; FR2.4, FR2.5, FR3.4 | sai `0`; os cinco itens com hash igual; resumo lista os preservados; `bob doctor` = `0` |
| 9 | `BOB_GITLEAKS_BASE_URL` apontando para um tar.gz adulterado, em `HOME` novo | US1.3; FR2.3; NFR6 | sai `4`; stderr cita `gitleaks` e "sha256"; `BOB_HOME/tools/gitleaks` não existe |
| 10 | Servidor com duas releases (v-antiga instalada; v-nova como `latest`; uma pré-release mais nova fora do `latest`) e `bob update` no projeto do passo 8 | intent C5; US5.1; US5.2; US7.2; FR6.1–6.4 | sai `0`; `bob --version` mostra v-nova nas duas linhas; `.bob-version` = v-nova; os itens preservados do passo 8 com hash igual; `bob doctor` = `0` |
| 11 | `bob update` de novo | FR6.5; US5.1 crit. 4; US7.2 crit. 2 | sai `0`; mensagem "já está na release mais nova"; hash dos arquivos igual |
| 12 | `pytest tests/test_hook.py` | NFR8 | passa (< 60 s) |
| 13 | Perfil do shell (Q1 A, ADR 0013). Cada caso em `HOME` novo, `PATH` sem `~/.local/bin`, rodando o comando único duas vezes seguidas: (a) `SHELL=/bin/zsh`, sem `.zshrc`; (b) `SHELL=/bin/bash`, `.bashrc` com conteúdo e sem quebra de linha no fim; (c) `SHELL=/bin/sh`, sem `.profile`; (d) `SHELL=/bin/bash` com `~/.local/bin` já no `PATH`; (e) `SHELL=/bin/bash` com `.bashrc` só leitura | FR1.1; NFR2; NFR4; NFR5; NFR9 | (a) `.zshrc` criado só com a linha; (b) conteúdo anterior byte a byte igual e a linha no fim, numa linha própria; (c) `.profile` criado só com a linha; em (a)–(c), `grep -c 'managed-by: bob-quality'` = `1` depois das duas execuções, a 1ª execução mostra no resumo `perfil do shell: acrescentei ... em <arquivo>` e a 2ª `<arquivo> já tem a linha do bob; nada mudou`; nenhum outro perfil criado; `env -i HOME=$HOME PATH=/usr/bin:/bin sh -c '. "<arquivo>"; command -v bob'` = `$HOME/.local/bin/bob` (em (a), com `bash` no lugar de `zsh` se o runner não tiver zsh: a linha é POSIX); (d) nenhum perfil criado ou alterado, resumo `já está no PATH`; (e) sai `0`, arquivo igual, aviso `install: perfil: não consegui gravar` com a linha para colar |

Código de saída do script: `0` se os 13 passam; `1` no primeiro que falha, com `verify-install: passo <n>: <motivo>`.

## O que fica fora da automação
- Ver as skills na interface de cada agente (intent C2, US2.1 crit. 1). O passo 4 prova a pasta; a leitura pelo agente vem das docs da ADR 0009 e da verificação manual abaixo.
- Comportamento real do `releases/latest` do GitHub com pré-release e rascunho (US7.2): garantido pela doc da API (ADR 0011); conferido no modo pós-release depois da P2.

## Verificação manual por release
Feita antes de marcar a release como pronta, no projeto do passo 2 (só `.agents/skills`). Evidência em `docs/release-checks/vX.Y.Z.md`, no PR da release: para cada item, data (UTC-3), versão do bob, versão do agente e a saída do terminal ou a captura de tela com as skills listadas.

| Agente | Doc confirma `.agents/skills`? | O que fazer | Passa se |
|---|---|---|---|
| Cursor | sim | abrir o projeto e listar as skills | `bob-check`, `harden`, `review-report` aparecem, uma vez cada |
| Claude Code | **não** (Risco 1 da ADR 0009) | abrir o projeto e listar as skills | idem |
| GitHub Copilot (CLI ou agente) | sim | abrir o projeto e listar as skills | idem |
| Devin CLI | sim | abrir o projeto no Devin CLI e listar as skills | idem |
| Devin web | sim | sessão no repositório de teste com o projeto do passo 2 e listar as skills | idem |

- No 3.6, o critério 2 do intent (e FR3.2, US2.1 crit. 1) para o **Claude Code** é avaliado por esta verificação manual, com a evidência em `docs/release-checks/vX.Y.Z.md`. Base: risco aceito pelo Emerson (ADR 0009, Risco 1; 18/10/2026 18:31 UTC-3: "Aceito o risco no Claude Code e mantenho .agents/skills."). O resultado é registrado como está, passe ou falhe.
- Para Cursor, Copilot, Devin CLI e Devin web a meta não muda: as três skills, uma vez cada; o passo 4 automático e esta verificação manual precisam passar.
- Gatilho: algum agente não lista uma das três skills, ou lista em duplicata.
- Resposta: registrar em `docs/release-checks/vX.Y.Z.md`, abrir issue e levar ao Emerson com a evidência. Não há plano B de duplicação; a pasta não muda sem decisão dele (ADR 0009).
