import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

const sections = [
  ['/docs/why-bob', 'Why bob', 'What the gates add to running each tool on its own.'],
  [
    '/docs/getting-started/installation',
    'Getting started',
    'Install bob, run the first check, and use it from the coding agents.',
  ],
  [
    '/docs/guides/configuration',
    'Guides',
    'Configuration, gates and waivers, the pre-push hook, CI, and reports.',
  ],
  [
    '/docs/reference/cli',
    'Reference',
    'CLI, configuration schema, exit codes, and report.json.',
  ],
  ['/docs/architecture/overview', 'Architecture', 'Technical overview, ADRs, and the SPEC.'],
  ['/docs/contributing', 'Contributing and changelog', 'How to change bob.'],
];

const portugueseGuides = [
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
          <p>
            The <Link to="/docs/changelog">changelog</Link> records behavior changes. Portuguese
            guides stay available until the translation:{' '}
            {portugueseGuides.map(([to, title], index) => (
              <span key={to}>
                {index > 0 ? ', ' : null}
                <Link to={to}>{title}</Link>
              </span>
            ))}
            .
          </p>
        </div>
      </main>
    </Layout>
  );
}
