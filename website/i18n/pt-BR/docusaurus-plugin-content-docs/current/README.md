# Documentação do bob

Guias em inglês de [bob](https://github.com/fazedordecodigo/bob/blob/main/README.md). Eles descrevem o que o código na `main` faz. A spec aprovada permanece em [SPEC.md](SPEC.md). Onde a spec e o código divergem, a página documenta o código e diz isso.

O pacote pip é `bob-quality`. O comando é `bob`. As listagens de marketplace usam o nome `bob`. A licença é MIT (`LICENSE`).

As páginas pt-BR do site público são uma mudança separada. Estes arquivos são a fonte em inglês.

## Por que usar o bob

[Por que usar o bob](why-bob.md) expõe o problema que os gates resolvem e o que um comando acrescenta a rodar cada ferramenta por conta própria.

## Primeiros passos

| Página | O que ela responde |
|---|---|
| [Instalação](getting-started/installation.md) | Python, Node, o pacote `bob-quality` e o `bob doctor` |
| [Primeiro check](getting-started/first-check.md) | O primeiro `bob check` e como ler o código de saída |
| [Agentes](getting-started/agents.md) | Cursor, Claude Code, Codex, Devin e GitHub Copilot |

## Guias

| Página | O que ela responde |
|---|---|
| [Configuração](guides/configuration.md) | `bob.yaml`, idioma da saída e `.bob/waivers.yaml` |
| [Gates e waivers](guides/gates-and-waivers.md) | O que cada gate mede, quando bloqueia e o id do waiver |
| [Hook pre-push](guides/pre-push.md) | O hook local e os gates que ele roda |
| [CI](guides/ci.md) | A GitHub Action, os inputs dela e o comentário do pull request |
| [Relatórios](guides/reports.md) | Como ler o `.bob/report.md` |

## Referência

| Página | O que ela responde |
|---|---|
| [CLI](reference/cli.md) | Comandos, flags e idioma da saída |
| [Schema de configuração](reference/configuration.md) | Cada chave que o loader aceita, e as chaves que ele recusa |
| [Códigos de saída](exit-codes.md) | Os códigos `0` a `4` |
| [report.json](reference/report-json.md) | Os campos do schema v1 |

## Arquitetura

| Página | O que ela responde |
|---|---|
| [Visão técnica](architecture/overview.md) | Como uma execução vai da CLI ao relatório |
| [ADRs](architecture/adrs.md) | Os registros de decisão, inclusive o [ADR 0007](adr/0007-gerador-do-site.md) |
| [SPEC](architecture/spec.md) | Onde ler a spec, e onde o código difere |

## Contribuição e changelog

- [Contribuição](contributing.md)
- [Changelog](changelog.md)
- [Publicação do plugin do Cursor](publishing.md)
- [Publicar o site de documentação](site-deploy.md)

## Por onde começar

- Instalar e comparar versões: [Instalação](getting-started/installation.md) e [`bob doctor`](reference/cli.md#bob-doctor).
- Medir um diff: [Primeiro check](getting-started/first-check.md) e [Códigos de saída](exit-codes.md).
- Mudar um limite ou o idioma da saída: [Configuração](guides/configuration.md).
- Ler o resultado: [Relatórios](guides/reports.md).
- Entender um veredito: [Gates e waivers](guides/gates-and-waivers.md).
