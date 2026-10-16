# Por que usar o bob

[Índice](README.md) · [Instalação](getting-started/installation.md) · [Gates e waivers](guides/gates-and-waivers.md) · [SPEC](SPEC.md)

Um agente pode alterar muito código antes de uma pessoa revisar. Cobertura, complexidade, clones, ciclos de dependência e mutação respondem cada um a uma pergunta diferente, e cada ferramenta sai com o próprio código e o próprio arquivo. Quem revisa então precisa abrir cada arquivo e decidir qual achado está no diff.

O bob roda essas medições como gates sobre o diff. Um comando grava um relatório e sai com um código. O agente pode iterar sobre esse código. A pessoa que revisa o pull request recebe uma página que diz onde olhar primeiro.

## O que um comando acrescenta

Cada ferramenta de mercado fica atrás de um adaptador. O bob não copia o código delas. A fórmula, os limites, o escopo do diff, a mutação diferencial e os waivers ficam no pacote Python `bob-quality`.

Rodar lizard, jscpd, import-linter e mutmut por conta própria ainda produz a saída bruta delas. Um gate do bob acrescenta quatro coisas que essas execuções não compartilham:

- O diff escolhe o que pode bloquear. A dívida antiga fica no relatório e não muda o código de saída. Ver [ADR 0002](adr/0002-o-diff-filtra-o-veredito.md).
- O código de saída é um de `0`, `1`, `2`, `3` ou `4`. Quando mais de um gate devolve um código, o processo fica com o mais alto. Ver [Códigos de saída](exit-codes.md).
- `.bob/report.md` é uma página para quem revisa. `.bob/report.json` é a mesma execução no schema v1, em inglês. Ver [Relatórios](guides/reports.md).
- Um waiver é um motivo de uma linha em `.bob/waivers.yaml`, versionado com o código, para um achado que o time aceita. O humano aprova no review.

`bob check` sem `--gates` roda `crap`, `dry` e `deps` (`DEFAULT_GATES` em `src/bob_quality/check.py`). A mutação e os outros gates rodam quando o comando os nomeia. O [guia de gates](guides/gates-and-waivers.md) lista cada um.

## Para quem é

As skills `bob-check`, `harden` e `review-report` dizem ao Cursor, ao Claude Code, ao GitHub Copilot e ao Devin quando rodar a CLI, como tratar um mutante sobrevivente e como levar o relatório ao pull request. O Codex lê a mesma pasta de skills do projeto que o alvo `agents` do instalador. Ver [Agentes](getting-started/agents.md). O índice do repositório para agentes é [AGENTS.md](https://github.com/fazedordecodigo/bob/blob/main/AGENTS.md).

## Palavras

Estas páginas usam uma palavra para cada um destes:

| Palavra | Significado |
|---|---|
| gate | Um check nomeado (`crap`, `dry`, `deps`, `mutate` e os nomes opt-in) |
| diff | O lado novo de `git diff <base>...HEAD` |
| função alterada | Uma função cujo intervalo de linhas sobrepõe o diff |
| baseline | A execução da suíte de testes antes de uma medição que precisa dela |
| mutante | Uma pequena mudança que o teste de mutação faz |
| sobrevivente | Um mutante que os testes não mataram |
| waiver | Uma linha versionada em `.bob/waivers.yaml` com um motivo de uma linha |
| clone | Um bloco duplicado que o gate `dry` reporta |
| pin | A versão da ferramenta que o `bob doctor` espera |
| relatório | `.bob/report.md` e `.bob/report.json` de uma execução |
| código de saída | O status do processo `0`, `1`, `2`, `3` ou `4` |

O idioma da saída (`en` ou `pt-BR`) é o idioma do texto da CLI e do `report.md`. Ele é separado do idioma deste site.
