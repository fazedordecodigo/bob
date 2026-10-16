# Gerador do site de documentação

Status: aceita pelo Emerson em 15/10/2026. Registrada em 15/10/2026.

## Contexto

A issue [#156](https://github.com/fazedordecodigo/bob/issues/156) pede um site público com o conteúdo de `docs/`: por que usar o bob, como começar, guias, referência, arquitetura, contribuição e changelog.

Em 15/10/2026 a release estável do MkDocs no PyPI era a 1.6.1, publicada em 30/08/2024. Não houve release estável desde agosto de 2024. O `@astrojs/starlight` estava em 0.42.6, anterior a 1.0. O `@docusaurus/core` estava em 3.10.2.

## Decisão

O gerador é o Docusaurus 3.x. É a opção mais adotada e estável, com versionamento e i18n nativos.

A busca é o Algolia DocSearch.

O inglês é o idioma padrão. O pt-BR é o segundo idioma, pelo i18n nativo.

O endereço atual é `https://fazedordecodigo.github.io/bob/`, o endereço padrão do GitHub Pages. O domínio `bob.fazedordecodigo.com` entra depois, na issue [#163](https://github.com/fazedordecodigo/bob/issues/163).

O site fica isolado em `website/`. Os arquivos `.md` entram em Markdown puro, não MDX. Essa escolha não altera o pacote Python.

MkDocs fica de fora: sem release estável desde agosto de 2024. Starlight fica de fora: ainda anterior a 1.0.

## Consequências

O esqueleto em `website/`, o deploy no GitHub Pages e as chaves do Algolia são issues próprias. Esta ADR não acrescenta tema de terceiro nem dependência além do Docusaurus e dos plugins oficiais. O conteúdo em inglês fica em `docs/`. A tradução pt-BR e o snapshot da versão `v0.1.0` são issues seguintes. A troca para o domínio customizado é a [#163](https://github.com/fazedordecodigo/bob/issues/163).
