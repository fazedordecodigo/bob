# Agentes

[Índice](../README.md) · [Instalação](installation.md) · [Hook pre-push](../guides/pre-push.md)

O plugin entrega três skills, listadas em `.claude-plugin/plugin.json` e repetidas em `.cursor-plugin/plugin.json`:

- `./skills/bob-check`
- `./skills/harden`
- `./skills/review-report`

Nada está publicado num marketplace. Os comandos abaixo partem de um clone. O [ADR 0004](adr/0004-empacotamento-quatro-agentes.md) registra a decisão de empacotamento para Claude Code, Cursor, GitHub Copilot e Devin.

## Cursor

O Cursor lê `.cursor-plugin/`. Copie o clone para `~/.cursor/plugins/local/bob` como um diretório real. O Cursor ignora um symlink cujo alvo está fora dessa pasta. Depois rode **Developer: Reload Window**.

```bash
rm -rf ~/.cursor/plugins/local/bob
mkdir -p ~/.cursor/plugins/local/bob
git archive HEAD | tar -x -C ~/.cursor/plugins/local/bob
```

`git clone` nesse caminho é o mesmo requisito: o resultado tem de ser um diretório real. Skills achatadas dentro de um projeto vão para `.agents/skills` (o alvo `agents` do instalador). O plugin em `~/.cursor/plugins/local/bob` e as skills copiadas para um projeto são instalações diferentes.

Publicar o plugin no marketplace do Cursor é um formulário manual. O workflow que valida a árvore é [Publicação do plugin do Cursor](../publishing.md).

## Claude Code

O Claude Code lê `.claude-plugin/`. A partir do clone:

```bash
claude plugin marketplace add <clone path>
claude plugin install bob@bob
```

Para uma sessão, rode `claude --plugin-dir <clone path>`.

O instalador não tem alvo de Claude Code. As skills ficam no clone, em `skills/<name>/SKILL.md`.

## Codex

O repositório não entrega um manifesto do Codex nem um alvo `codex` do instalador. `src/bob_quality/install_skills.py` diz que `.agents/skills` é lido por Cursor, Copilot, Devin e Codex. O alvo `agents` grava essa pasta:

```bash
python3 <clone path>/src/bob_quality/install_skills.py --project <project> agents
```

O mesmo módulo roda como `python -m bob_quality.install_skills`. Um `bob-quality` instalado pelo pip não carrega as skills, então passe `--source <clone path>`.

## Devin

O Devin lê `.agents/skills` e `.github/skills`. Os alvos do instalador são:

| Alvo | Pasta | Leitores nomeados no instalador |
|---|---|---|
| `agents` | `.agents/skills` | Cursor, Copilot, Devin, Codex |
| `devin` | `.agents/skills` | Devin (o mesmo diretório que `agents`) |
| `copilot` | `.github/skills` | Copilot e Devin |

`devin` e `agents` gravam o mesmo diretório. Instalar `copilot` e `devin` num projeto coloca cada skill nas duas pastas. O Devin então carrega cada skill duas vezes, então escolha um alvo.

## GitHub Copilot

A CLI do Copilot lê `.claude-plugin/`, com os mesmos comandos do Claude Code:

```bash
copilot plugin marketplace add <clone path>
copilot plugin install bob@bob
```

Skills de repositório para o Copilot vão para `.github/skills` (alvo `copilot`). Não há diretório `.plugin/`. O [ADR 0004](adr/0004-empacotamento-quatro-agentes.md) registra por que um segundo manifesto divergiria.

## O que o instalador faz

`install_skills.py` lê a lista de skills de `.claude-plugin/plugin.json` e copia cada pasta, achatada pelo nome, com o `LICENSE` mais próximo, da pasta da skill até a raiz do plugin. Ele não copia `NOTICE`.

Sem um manifesto, o instalador imprime o caminho que leu e sai com `4`. Quando uma skill não tem `LICENSE` da pasta dela até a raiz do plugin, o instalador avisa no stderr e ainda assim instala a skill.

Rodar o instalador de novo substitui as skills nomeadas no manifesto. Uma pasta da lista fixa de skills que o plugin não entrega mais só é apagada quando o `NOTICE` dessa pasta é um arquivo regular com o texto que o instalador antigo escreveu. Um arquivo, um symlink, um `NOTICE` que é symlink, ou uma pasta sem esse texto, permanece, e o instalador avisa no stderr. Toda outra pasta permanece.
