import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

const sections = [
  ['/docs/why-bob', 'Why bob', 'What bob measures, and why the gates exist.'],
  [
    '/docs/getting-started/installation',
    'Getting started',
    'Install the package, run a first check, and use it from the coding agents.',
  ],
  [
    '/docs/guides/configuration',
    'Guides',
    'Configuration, gates, waivers, the pre-push hook, CI, and reports.',
  ],
  [
    '/docs/reference/cli',
    'Reference',
    'CLI, configuration schema, exit codes, and report.json.',
  ],
  ['/docs/architecture/overview', 'Architecture', 'Technical overview, ADRs, and the SPEC.'],
  ['/docs/contributing', 'Contributing', 'How to change bob.'],
  ['/docs/changelog', 'Changelog', 'The record of behavior changes.'],
];

const temporaryGuides = [
  ['/docs/visao-geral', 'Visão geral'],
  ['/docs/instalacao', 'Instalação'],
  ['/docs/cli', 'CLI'],
  ['/docs/configuracao', 'Configuração'],
  ['/docs/gates', 'Gates'],
  ['/docs/relatorios', 'Relatórios'],
  ['/docs/contribuicao', 'Contribuição'],
];

export default function Home() {
  const { siteConfig } = useDocusaurusContext();
  return (
    <Layout title="bob" description={siteConfig.tagline}>
      <main className="home">
        <div className="container">
          <Heading as="h1">bob</Heading>
          <p className="home-lead">{siteConfig.tagline}</p>
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
          <Heading as="h2">Português (temporário, até #160)</Heading>
          <ul className="home-sections">
            {temporaryGuides.map(([to, title]) => (
              <li key={to}>
                <Heading as="h3">
                  <Link to={to}>{title}</Link>
                </Heading>
              </li>
            ))}
          </ul>
        </div>
      </main>
    </Layout>
  );
}
