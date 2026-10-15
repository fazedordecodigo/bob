# Documentação do bob

Guias do [bob](../README.pt-BR.md) em português. A spec aprovada permanece em [SPEC.md](SPEC.md); estes guias descrevem o que o código faz hoje e apontam, em nota, onde a spec ou o README ainda dizem outra coisa.

O pacote pip se chama `bob-quality`. O comando é `bob`. Os marketplaces usam o nome `bob`. A licença é MIT (`LICENSE`).

## Índice

| Guia | O que responde |
|---|---|
| [Visão geral](visao-geral.md) | Para que serve, o que já roda e o fluxo do diff até o relatório |
| [Instalação](instalacao.md) | Pacote `bob-quality` e plugin no Cursor, Claude Code, Copilot e Devin |
| [CLI](cli.md) | `check`, `doctor`, `waive`, `--lang` e os outros comandos |
| [Configuração](configuracao.md) | `bob.yaml` e `.bob/waivers.yaml` |
| [Gates](gates.md) | CRAP, DRY, mutação e dependências |
| [Exit codes](exit-codes.md) | Códigos `0` a `4` |
| [Relatórios](relatorios.md) | `.bob/report.md`, `.bob/report.json` e o comentário no pull request |
| [Contribuição](contribuicao.md) | Ambiente, testes e o que o CI exige |
| [Publicação](publishing.md) | Workflow do plugin Cursor, o formulário manual e a ausência de segredos |

## Por onde começar

- Instalar e ver as versões: [Instalação](instalacao.md) e [`bob doctor`](cli.md#bob-doctor).
- Medir um diff: [`bob check`](cli.md#bob-check) e [Exit codes](exit-codes.md).
- Ajustar limite ou idioma: [Configuração](configuracao.md).
- Ler o resultado: [Relatórios](relatorios.md).
- Entender um veredito: [Gates](gates.md).

## Fontes

O texto destes guias foi conferido nestas fontes, nesta ordem quando elas discordam: o código em `src/bob_quality/`, [SPEC.md](SPEC.md), [README.pt-BR.md](../README.pt-BR.md), [README.md](../README.md) e [CHANGELOG.md](../CHANGELOG.md). Onde a spec descreve uma chave ou um comando que o código ainda não lê, o guia diz isso na seção.

## Notas que atravessam os guias

- A CLI ainda não tem o comando `bob report` que a [SPEC](SPEC.md) lista. Ver [CLI](cli.md#comandos-que-a-spec-lista-e-a-cli-ainda-não-tem).
- Mutação em TypeScript (StrykerJS) não aparece no código. Ver [Gates](gates.md#mutação).
