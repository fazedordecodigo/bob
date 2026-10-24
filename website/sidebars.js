// @ts-check

/**
 * Six sections from issue #156. Each item is a file that exists under `docs/`.
 * The English pages are the source. pt-BR is the Docusaurus locale in
 * `website/i18n/pt-BR`, not a second sidebar.
 *
 * @type {import('@docusaurus/plugin-content-docs').SidebarsConfig}
 */
const sidebars = {
  docs: [
    { type: 'doc', id: 'README', label: 'Documentation index' },
    { type: 'doc', id: 'why-bob', label: 'Why bob' },
    {
      type: 'category',
      label: 'Getting started',
      items: [
        'getting-started/installation',
        'getting-started/first-check',
        'getting-started/agents',
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      items: [
        'guides/configuration',
        'guides/gates-and-waivers',
        'guides/pre-push',
        'guides/ci',
        'guides/reports',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        'reference/cli',
        'reference/configuration',
        'exit-codes',
        'reference/report-json',
      ],
    },
    {
      type: 'category',
      label: 'Architecture',
      items: [
        'architecture/overview',
        'architecture/adrs',
        'architecture/spec',
        'SPEC',
        {
          type: 'category',
          label: 'ADRs',
          items: [
            'adr/0000-architecture-review',
            'adr/0001-adaptadores-sobre-ferramentas-de-mercado',
            'adr/0002-o-diff-filtra-o-veredito',
            'adr/0003-exit-codes',
            'adr/0004-empacotamento-quatro-agentes',
            'adr/0005-modelo-de-gate-das-analises-novas',
            'adr/0006-chave-estavel-do-waiver',
            'adr/0007-gerador-do-site',
            'adr/0008-fonte-unica-das-versoes-npm',
            'adr/0009-skills-de-projeto-so-em-agents-skills',
            'adr/0010-skills-manifesto-e-license-no-wheel',
            'adr/0011-distribuicao-por-release-do-github',
            'adr/0012-comando-unico-install-sh-e-bob-setup',
            'adr/0013-instalacao-na-conta-do-usuario',
            'adr/0014-gitleaks-por-plataforma',
            'adr/0015-geracao-do-bob-yaml',
            'adr/0016-hook-pre-push-gerenciado',
            'adr/0017-preservacao-posse-e-idempotencia',
            'adr/0018-atualizacao-e-versao-visivel',
            'adr/0019-doctor-so-ferramentas-do-bob',
            'adr/0020-docs-com-teste-de-paridade',
            'adr/0021-bob-install-profile-already-marked',
            'adr/0022-passo-perfil-do-install-sh',
            'adr/0023-linha-perfil-do-shell-no-setup',
            'adr/0024-versao-das-skills-do-projeto',
            'adr/0025-bob-update-e-version',
            'adr/0026-harness-passos-10-11-e-13',
            'adr/0027-entrega-em-paralelo-e-changelog',
            'adr/0028-docs-u8-arquivos-e-links',
            'adr/0029-u8-docs-paridade-e-passo-14',
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'Contributing and changelog',
      items: ['contributing', 'changelog', 'publishing'],
    },
  ],
};

export default sidebars;
