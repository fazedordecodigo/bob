// @ts-check

/**
 * Six sections approved in issue #156. Items are the English pages from #165.
 * Temporary pt-BR guides stay linked from the home and the footer until #160.
 *
 * @type {import('@docusaurus/plugin-content-docs').SidebarsConfig}
 */
const sidebars = {
  docs: [
    {
      type: 'category',
      label: 'Why bob',
      collapsed: false,
      items: [
        { type: 'doc', id: 'README', label: 'Documentation index' },
        'why-bob',
      ],
    },
    {
      type: 'category',
      label: 'Getting started',
      collapsed: false,
      items: [
        'getting-started/installation',
        'getting-started/first-check',
        'getting-started/agents',
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      collapsed: false,
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
      collapsed: false,
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
      collapsed: false,
      items: ['architecture/overview', 'architecture/adrs', 'architecture/spec'],
    },
    {
      type: 'category',
      label: 'Contributing and changelog',
      collapsed: false,
      items: ['contributing', 'changelog', 'publishing'],
    },
  ],
};

export default sidebars;
