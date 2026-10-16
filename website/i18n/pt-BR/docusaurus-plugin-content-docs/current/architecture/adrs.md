# ADRs

[Índice](../README.md) · [Visão técnica](overview.md) · [SPEC](spec.md)

Estes registros guardam decisões que a spec ou um pull request já tomou. As páginas não reescrevem uma decisão. Onde o código posterior é mais estreito ou foi mais longe, a [visão técnica](overview.md) e os guias documentam o código e apontam para o ADR.

| ADR | Decisão |
|---|---|
| [0000](adr/0000-architecture-review.md) | Leitura da arquitetura em 12/10/2026, no commit `246d2eb` |
| [0001](adr/0001-adaptadores-sobre-ferramentas-de-mercado.md) | Ferramentas de mercado atrás de adaptadores. O núcleo não as importa |
| [0002](adr/0002-o-diff-filtra-o-veredito.md) | As ferramentas medem a árvore de include. O diff escolhe o que pode bloquear |
| [0003](adr/0003-exit-codes.md) | Códigos de saída `0`, `1`, `2`, `3` e `4`, e as exceções já aprovadas |
| [0004](adr/0004-empacotamento-quatro-agentes.md) | Pacote `bob-quality`, comando `bob`, nome do plugin `bob`, quatro agentes, uma lista de skills |
| [0005](adr/0005-modelo-de-gate-das-analises-novas.md) | Veredito, waiver, chave do `bob.yaml` e seção do relatório para as análises posteriores |
| [0006](adr/0006-chave-estavel-do-waiver.md) | Um id de waiver de mutação é o arquivo, a função e a descrição |
| [0007](adr/0007-gerador-do-site.md) | Docusaurus 3.x, Algolia DocSearch, inglês como padrão, pt-BR como segundo, endereço do GitHub Pages agora, domínio próprio na #163 |

O ADR 0007 foi aceito pelo Emerson em 15/10/2026. O gerador é o Docusaurus 3.x porque é a opção mais adotada e estável, com versionamento e i18n nativos. A busca é Algolia DocSearch. O idioma padrão é inglês. O segundo idioma é pt-BR. O endereço atual é `https://fazedordecodigo.github.io/bob/`. O domínio próprio `bob.fazedordecodigo.com` é o passo seguinte, [issue 163](https://github.com/fazedordecodigo/bob/issues/163). O site fica em `website/`, os arquivos `.md` existentes continuam Markdown puro, e o pacote Python permanece intocado. O MkDocs é recusado porque não teve release estável desde agosto de 2024. O Starlight é recusado porque ainda é pré-1.0.
