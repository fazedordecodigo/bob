import Link from '@docusaurus/Link';
import { translate } from '@docusaurus/Translate';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

export default function Home() {
  const tagline = translate({
    id: 'home.tagline',
    message: 'Deterministic quality gates for the code a coding agent changes.',
    description: 'The tagline on the home page',
  });
  const sections = [
    [
      '/docs/why-bob',
      translate({
        id: 'home.section.whyBob.title',
        message: 'Why bob',
        description: 'Home section title linking to why-bob',
      }),
      translate({
        id: 'home.section.whyBob.description',
        message: 'What bob measures, and why the gates exist.',
        description: 'Home section description linking to why-bob',
      }),
    ],
    [
      '/docs/getting-started/installation',
      translate({
        id: 'home.section.gettingStarted.title',
        message: 'Getting started',
        description: 'Home section title linking to installation',
      }),
      translate({
        id: 'home.section.gettingStarted.description',
        message: 'Install the package, run a first check, and use it from the coding agents.',
        description: 'Home section description linking to installation',
      }),
    ],
    [
      '/docs/guides/configuration',
      translate({
        id: 'home.section.guides.title',
        message: 'Guides',
        description: 'Home section title linking to configuration',
      }),
      translate({
        id: 'home.section.guides.description',
        message: 'Configuration, gates, waivers, the pre-push hook, CI, and reports.',
        description: 'Home section description linking to configuration',
      }),
    ],
    [
      '/docs/reference/cli',
      translate({
        id: 'home.section.reference.title',
        message: 'Reference',
        description: 'Home section title linking to the CLI reference',
      }),
      translate({
        id: 'home.section.reference.description',
        message: 'CLI, configuration schema, exit codes, and report.json.',
        description: 'Home section description linking to the CLI reference',
      }),
    ],
    [
      '/docs/architecture/overview',
      translate({
        id: 'home.section.architecture.title',
        message: 'Architecture',
        description: 'Home section title linking to the architecture overview',
      }),
      translate({
        id: 'home.section.architecture.description',
        message: 'Technical overview, ADRs, and the SPEC.',
        description: 'Home section description linking to the architecture overview',
      }),
    ],
    [
      '/docs/contributing',
      translate({
        id: 'home.section.contributing.title',
        message: 'Contributing',
        description: 'Home section title linking to contributing',
      }),
      translate({
        id: 'home.section.contributing.description',
        message: 'How to change bob.',
        description: 'Home section description linking to contributing',
      }),
    ],
    [
      '/docs/changelog',
      translate({
        id: 'home.section.changelog.title',
        message: 'Changelog',
        description: 'Home section title linking to the changelog',
      }),
      translate({
        id: 'home.section.changelog.description',
        message: 'The record of behavior changes.',
        description: 'Home section description linking to the changelog',
      }),
    ],
  ];
  return (
    <Layout title="bob" description={tagline}>
      <main className="home">
        <div className="container">
          <Heading as="h1">bob</Heading>
          <p className="home-lead">{tagline}</p>
          <ul className="home-sections">
            {sections.map(([to, title, text]) => (
              <li key={to}>
                <Heading as="h2">
                  <Link to={to}>{title}</Link>
                </Heading>
                <p>{text}</p>
              </li>
            ))}
          </ul>
        </div>
      </main>
    </Layout>
  );
}
