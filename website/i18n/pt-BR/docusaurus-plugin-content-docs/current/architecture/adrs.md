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
| [0008](adr/0008-fonte-unica-das-versoes-npm.md) | Fonte única das versões npm: o `package.json` empacotado |
| [0009](adr/0009-skills-de-projeto-so-em-agents-skills.md) | Skills de projeto só em `.agents/skills` |
| [0010](adr/0010-skills-manifesto-e-license-no-wheel.md) | Skills, manifesto e LICENSE dentro do wheel |
| [0011](adr/0011-distribuicao-por-release-do-github.md) | Distribuição por release do GitHub com três assets: `install.sh`, o wheel e `SHA256SUMS` |
| [0012](adr/0012-comando-unico-install-sh-e-bob-setup.md) | Comando único: `install.sh` mais `bob setup` |
| [0013](adr/0013-instalacao-na-conta-do-usuario.md) | Instalação na conta do usuário com launcher estável |
| [0014](adr/0014-gitleaks-por-plataforma.md) | gitleaks 8.30.1 por plataforma, conferido por sha256 |
| [0015](adr/0015-geracao-do-bob-yaml.md) | Geração do `bob.yaml` e a regra de `paths.include` |
| [0016](adr/0016-hook-pre-push-gerenciado.md) | Hook pre-push gerenciado |
| [0017](adr/0017-preservacao-posse-e-idempotencia.md) | Preservação, posse e idempotência |
| [0018](adr/0018-atualizacao-e-versao-visivel.md) | Atualização e versão visível |
| [0019](adr/0019-doctor-so-ferramentas-do-bob.md) | O `bob doctor` confere só as ferramentas do bob |
| [0020](adr/0020-docs-com-teste-de-paridade.md) | Docs com teste de paridade de versões |
| [0021](adr/0021-bob-install-profile-already-marked.md) | `BOB_INSTALL_PROFILE` leva o arquivo também em `already-marked` |
| [0022](adr/0022-passo-perfil-do-install-sh.md) | O passo `perfil` do `install.sh`: escrita, aviso e resultado |
| [0023](adr/0023-linha-perfil-do-shell-no-setup.md) | Linha do perfil do shell no resumo do `bob setup` |
| [0024](adr/0024-versao-das-skills-do-projeto.md) | Versão das skills do projeto: o módulo `project_version` |
| [0025](adr/0025-bob-update-e-version.md) | `bob update` e `bob --version`: implementação |
| [0026](adr/0026-harness-passos-10-11-e-13.md) | Harness: passos 10, 11 e 13 e o passo 2 parcial |
| [0027](adr/0027-entrega-em-paralelo-e-changelog.md) | Entrega em paralelo: CHANGELOG por unit e rebase mecânico |
| [0028](adr/0028-docs-u8-arquivos-e-links.md) | Docs de instalação: lista de arquivos, links e paridade |
| [0029](adr/0029-u8-docs-paridade-e-passo-14.md) | Forma dos docs de instalação, o teste de paridade e o passo 14 |

O ADR 0007 foi aceito pelo Emerson em 15/10/2026. O gerador é o Docusaurus 3.x porque é a opção mais adotada e estável, com versionamento e i18n nativos. A busca é Algolia DocSearch. O idioma padrão é inglês. O segundo idioma é pt-BR. O endereço atual é `https://fazedordecodigo.github.io/bob/`. O domínio próprio `bob.fazedordecodigo.com` é o passo seguinte, [issue 163](https://github.com/fazedordecodigo/bob/issues/163). O site fica em `website/`, os arquivos `.md` existentes continuam Markdown puro, e o pacote Python permanece intocado. O MkDocs é recusado porque não teve release estável desde agosto de 2024. O Starlight é recusado porque ainda é pré-1.0.
