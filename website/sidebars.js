// @ts-check

/**
 * Six sections from issue #156. Each item is a file that exists under `docs/`.
 * The English pages are the ones added for the public site.
 * The pt-BR guides stay in the sidebar until issue #160 replaces them.
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
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'Contributing and changelog',
      items: ['contributing', 'changelog', 'publishing'],
    },
    {
      type: 'category',
      label: 'Português (temporário, até #160)',
      items: [
        'visao-geral',
        'instalacao',
        'cli',
        'configuracao',
        'gates',
        'relatorios',
        'contribuicao',
      ],
    },
  ],
};

export default sidebars;
