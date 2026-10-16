// @ts-check

/**
 * Six sections approved in issue #156. Items are the English pages from #165.
 * The temporary pt-BR guides stay on disk until #160 and are linked from the
 * docs index and the footer. This file does not invent pages.
 *
 * @type {import('@docusaurus/plugin-content-docs').SidebarsConfig}
 */
const sidebars = {
  docs: [
    {
      type: 'category',
      label: 'Why bob',
      items: [
        { type: 'doc', id: 'why-bob', label: 'Why bob' },
        { type: 'doc', id: 'README', label: 'Documentation index' },
      ],
    },
    {
      type: 'category',
      label: 'Getting started',
      items: [
        { type: 'doc', id: 'getting-started/installation', label: 'Installation' },
        { type: 'doc', id: 'getting-started/first-check', label: 'First check' },
        { type: 'doc', id: 'getting-started/agents', label: 'Agents' },
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      items: [
        { type: 'doc', id: 'guides/configuration', label: 'Configuration' },
        { type: 'doc', id: 'guides/gates-and-waivers', label: 'Gates and waivers' },
        { type: 'doc', id: 'guides/pre-push', label: 'Pre-push hook' },
        { type: 'doc', id: 'guides/ci', label: 'CI' },
        { type: 'doc', id: 'guides/reports', label: 'Reading the report' },
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        { type: 'doc', id: 'reference/cli', label: 'CLI' },
        { type: 'doc', id: 'reference/configuration', label: 'Configuration schema' },
        { type: 'doc', id: 'exit-codes', label: 'Exit codes' },
        { type: 'doc', id: 'reference/report-json', label: 'report.json' },
      ],
    },
    {
      type: 'category',
      label: 'Architecture',
      items: [
        { type: 'doc', id: 'architecture/overview', label: 'Technical overview' },
        { type: 'doc', id: 'architecture/adrs', label: 'ADRs' },
        { type: 'doc', id: 'architecture/spec', label: 'SPEC' },
        {
          type: 'category',
          label: 'ADR records',
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
      items: [
        { type: 'doc', id: 'contributing', label: 'Contributing' },
        { type: 'doc', id: 'changelog', label: 'Changelog' },
        { type: 'doc', id: 'publishing', label: 'Publishing the Cursor plugin' },
      ],
    },
  ],
};

export default sidebars;
