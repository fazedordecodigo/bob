// @ts-check

/**
 * Six sections approved in issue #156. Items are the current files in `docs/`.
 * Pages that do not exist yet are not invented here; issue #159 writes them.
 *
 * @type {import('@docusaurus/plugin-content-docs').SidebarsConfig}
 */
const sidebars = {
  docs: [
    {
      type: 'category',
      label: 'Why bob',
      items: [
        { type: 'doc', id: 'visao-geral', label: 'Why bob' },
        { type: 'doc', id: 'README', label: 'Documentation index' },
      ],
    },
    {
      type: 'category',
      label: 'Getting started',
      items: [{ type: 'doc', id: 'instalacao', label: 'Installation and agents' }],
    },
    {
      type: 'category',
      label: 'Guides',
      items: [
        { type: 'doc', id: 'configuracao', label: 'Configuration and waivers' },
        { type: 'doc', id: 'gates', label: 'Gates' },
        { type: 'doc', id: 'relatorios', label: 'Reading reports' },
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        { type: 'doc', id: 'cli', label: 'CLI' },
        { type: 'doc', id: 'exit-codes', label: 'Exit codes' },
      ],
    },
    {
      type: 'category',
      label: 'Architecture',
      items: [
        { type: 'doc', id: 'adr/0000-architecture-review', label: 'Technical overview' },
        { type: 'doc', id: 'SPEC', label: 'SPEC' },
        {
          type: 'category',
          label: 'ADRs',
          items: [
            'adr/0001-adaptadores-sobre-ferramentas-de-mercado',
            'adr/0002-o-diff-filtra-o-veredito',
            'adr/0003-exit-codes',
            'adr/0004-empacotamento-quatro-agentes',
            'adr/0005-modelo-de-gate-das-analises-novas',
            'adr/0006-chave-estavel-do-waiver',
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'Contributing and changelog',
      items: [
        { type: 'doc', id: 'contribuicao', label: 'Contributing' },
        {
          type: 'link',
          label: 'Changelog',
          href: 'https://github.com/fazedordecodigo/bob/blob/main/CHANGELOG.md',
        },
      ],
    },
  ],
};

export default sidebars;
