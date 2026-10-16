import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

const sections = [
  ['/docs/why-bob', 'Why bob', 'What bob measures, and why the gates exist.'],
  [
    '/docs/getting-started/installation',
    'Getting started',
    'Install the package, run the first check, and use it from the coding agents.',
  ],
  [
    '/docs/guides/configuration',
    'Guides',
    'Configuration, gates, waivers, the pre-push hook, CI, and how to read a report.',
  ],
  [
    '/docs/reference/cli',
    'Reference',
    'CLI, configuration schema, exit codes, and report.json.',
  ],
  [
    '/docs/architecture/overview',
    'Architecture',
    'Technical overview, ADRs, and the SPEC.',
  ],
  [
    '/docs/contributing',
    'Contributing and changelog',
    'How to change bob, and the changelog.',
  ],
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
        </div>
      </main>
    </Layout>
  );
}
