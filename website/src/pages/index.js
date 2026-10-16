import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

const sections = [
  ['/docs/visao-geral', 'Why bob', 'What bob measures, and why the gates exist.'],
  ['/docs/instalacao', 'Getting started', 'Install the package and use it from the coding agents.'],
  ['/docs/configuracao', 'Guides', 'Configuration, gates, waivers, and how to read a report.'],
  ['/docs/cli', 'Reference', 'CLI commands and exit codes.'],
  ['/docs/adr/0000-architecture-review', 'Architecture', 'Technical overview, ADRs, and the SPEC.'],
  ['/docs/contribuicao', 'Contributing and changelog', 'How to change bob. The changelog lives in the repository.'],
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
