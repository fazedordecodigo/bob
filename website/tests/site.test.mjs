import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const websiteDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const repoRoot = path.resolve(websiteDir, '..');
const docsDir = path.join(repoRoot, 'docs');
const buildDir = path.join(websiteDir, 'build');

const sidebarLabels = [
  'Why bob',
  'Getting started',
  'Guides',
  'Reference',
  'Architecture',
  'Contributing and changelog',
];

const allowedDependencies = new Set([
  '@docusaurus/core',
  '@docusaurus/preset-classic',
  'react',
  'react-dom',
]);

function readBuild(relativePath) {
  const filePath = path.join(buildDir, relativePath);
  assert.ok(fs.existsSync(filePath), `missing build output ${relativePath}`);
  return fs.readFileSync(filePath, 'utf8');
}

function walk(directory) {
  if (!fs.existsSync(directory)) {
    return [];
  }
  const entries = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      entries.push(...walk(fullPath));
    } else if (entry.isFile()) {
      entries.push(fullPath);
    }
  }
  return entries;
}

function readText(filePath) {
  return fs.readFileSync(filePath);
}

function outputContains(directory, needle) {
  return walk(directory).some((filePath) => readText(filePath).includes(needle));
}

function htmlContains(directory, needle) {
  return walk(directory)
    .filter((filePath) => filePath.endsWith('.html'))
    .some((filePath) => fs.readFileSync(filePath, 'utf8').includes(needle));
}

function runBuild(env, outDir) {
  const args = ['--locale', 'en'];
  if (outDir) {
    args.push('--out-dir', outDir);
  }
  return spawnSync('npm', ['run', 'build', '--', ...args], {
    cwd: websiteDir,
    env: { ...process.env, ...env },
    encoding: 'utf8',
    timeout: 180000,
  });
}

function sidebarDocIds() {
  const source = fs.readFileSync(path.join(websiteDir, 'sidebars.js'), 'utf8');
  const ids = [];
  for (const match of source.matchAll(/\bid:\s*'([^']+)'/g)) {
    ids.push(match[1]);
  }
  for (const match of source.matchAll(/^\s+'([^']+)',?\s*$/gm)) {
    ids.push(match[1]);
  }
  return ids;
}

function sourceForDoc(id) {
  const candidates = [
    path.join(docsDir, `${id}.md`),
    path.join(docsDir, `${id}.mdx`),
    path.join(docsDir, id, 'index.md'),
    path.join(docsDir, id, 'index.mdx'),
  ];
  return candidates.find((candidate) => fs.existsSync(candidate));
}

test('website dependencies stay inside the Docusaurus set', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(websiteDir, 'package.json'), 'utf8'));
  const declared = [
    ...Object.keys(manifest.dependencies ?? {}),
    ...Object.keys(manifest.devDependencies ?? {}),
  ];
  const unexpected = declared.filter((name) => !allowedDependencies.has(name));
  assert.deepEqual(unexpected, []);
});

test('the production build emits English and pt-BR from docs/ without copying the markdown', () => {
  assert.equal(fs.existsSync(path.join(websiteDir, 'docs')), false);
  const ids = sidebarDocIds();
  assert.ok(ids.length > 0, 'sidebar has no doc ids');
  for (const id of ids) {
    assert.ok(sourceForDoc(id), `sidebar id ${id} has no file under docs/`);
  }

  const english = readBuild('index.html');
  const portuguese = readBuild('pt-BR/index.html');
  assert.match(english, /<html[^>]*\slang="en"/);
  assert.match(portuguese, /<html[^>]*\slang="pt-BR"/);
  assert.ok(fs.existsSync(path.join(buildDir, 'docs/index.html')));
  assert.ok(fs.existsSync(path.join(buildDir, 'pt-BR/docs/index.html')));
});

test('markdown stays CommonMark when the source contains braces', () => {
  const probe = path.join(docsDir, 'zz-commonmark.md');
  fs.writeFileSync(
    probe,
    '# Probe\n\nzz-commonmark-{notAComponent}\n\n`<caminho>`\n',
    'utf8',
  );
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'bob-site-commonmark-'));
  try {
    const result = runBuild({}, outDir);
    const output = `${result.stdout}\n${result.stderr}`;
    assert.equal(result.status, 0, output);
    const page = fs.readFileSync(path.join(outDir, 'docs/zz-commonmark/index.html'), 'utf8');
    assert.match(page, /notAComponent/);
    assert.match(page, /caminho/);
  } finally {
    fs.rmSync(probe, { force: true });
  }
});

test('the site targets GitHub Pages and offers both configured locales', () => {
  const home = readBuild('index.html');
  assert.match(home, /https:\/\/fazedordecodigo\.github\.io\/bob\//);
  assert.doesNotMatch(home, /bob\.fazedordecodigo\.com/);
  assert.match(home, /alt="bob"/);
  assert.match(home, /src="\/bob\/assets\/logo\.svg"/);
  assert.match(home, /Português \(Brasil\)/);
  assert.match(readBuild('pt-BR/index.html'), /English/);
});

function builtStylesheets() {
  return walk(buildDir).filter((filePath) => filePath.endsWith('.css'));
}

function rulesThatUnderline(selectorPattern, css) {
  const matched = [];
  for (const block of css.split('}')) {
    const splitAt = block.lastIndexOf('{');
    if (splitAt === -1) {
      continue;
    }
    const selector = block.slice(0, splitAt).trim();
    const body = block.slice(splitAt + 1);
    const hits = selector.split(',').some((part) => selectorPattern.test(part.trim()));
    if (hits && /text-decoration(?:-line)?\s*:\s*underline/.test(body)) {
      matched.push(selector);
    }
  }
  return matched;
}

test('the built stylesheet underlines docs and home prose links', () => {
  const css = builtStylesheets()
    .map((filePath) => fs.readFileSync(filePath, 'utf8'))
    .join('\n');
  assert.ok(css.length > 0, 'the production build has no stylesheet');
  const prose = rulesThatUnderline(/^(?:\.markdown a|\.home p a|\.home-lead a)(?:[:.\[]|$)/, css);
  assert.ok(
    prose.some((selector) => selector.includes('.markdown a')),
    'built CSS does not underline .markdown a',
  );
  assert.ok(
    prose.some((selector) => selector.includes('.home p a') || selector.includes('.home-lead a')),
    'built CSS does not underline home prose links',
  );
});

test('docs pages expose the six approved sidebar sections', () => {
  const page = readBuild('docs/index.html');
  for (const label of sidebarLabels) {
    assert.ok(page.includes(label), `sidebar is missing ${label}`);
  }
});

test('a link to a real file outside docs/ points at the repository and the site has no CNAME', () => {
  const probe = path.join(docsDir, 'zz-outside-link.md');
  fs.writeFileSync(probe, '# Probe\n\n[agents](../AGENTS.md)\n', 'utf8');
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'bob-site-outside-'));
  try {
    const result = runBuild({}, outDir);
    const output = `${result.stdout}\n${result.stderr}`;
    assert.equal(result.status, 0, output);
    const page = fs.readFileSync(path.join(outDir, 'docs/zz-outside-link/index.html'), 'utf8');
    assert.match(
      page,
      /href="https:\/\/github\.com\/fazedordecodigo\/bob\/blob\/main\/AGENTS\.md"/,
    );
  } finally {
    fs.rmSync(probe, { force: true });
  }
  assert.equal(fs.existsSync(path.join(buildDir, 'CNAME')), false);
  assert.equal(fs.existsSync(path.join(websiteDir, 'static/CNAME')), false);
});

test('Algolia is emitted only when app id, api key, and index name are all set', () => {
  assert.equal(outputContains(buildDir, 'bob-index-visible'), false);
  assert.equal(htmlContains(buildDir, 'DocSearch-Button'), false);

  const enabledDir = fs.mkdtempSync(path.join(os.tmpdir(), 'bob-site-algolia-'));
  const enabled = runBuild(
    {
      ALGOLIA_APP_ID: 'bob-app-id-visible',
      ALGOLIA_API_KEY: 'bob-search-key-visible',
      ALGOLIA_INDEX_NAME: 'bob-index-visible',
    },
    enabledDir,
  );
  assert.equal(
    enabled.status,
    0,
    `algolia build failed\n${enabled.stdout}\n${enabled.stderr}`,
  );
  assert.equal(outputContains(enabledDir, 'bob-app-id-visible'), true);
  assert.equal(outputContains(enabledDir, 'bob-search-key-visible'), true);
  assert.equal(outputContains(enabledDir, 'bob-index-visible'), true);
  assert.equal(htmlContains(enabledDir, 'DocSearch-Button'), true);

  const partialDir = fs.mkdtempSync(path.join(os.tmpdir(), 'bob-site-partial-'));
  const partial = runBuild({ ALGOLIA_APP_ID: 'bob-app-id-partial' }, partialDir);
  assert.equal(
    partial.status,
    0,
    `partial algolia build failed\n${partial.stdout}\n${partial.stderr}`,
  );
  assert.equal(outputContains(partialDir, 'bob-app-id-partial'), false);
  assert.equal(htmlContains(partialDir, 'DocSearch-Button'), false);
});

function docsSidebarHrefs(relativePage) {
  const html = readBuild(relativePage);
  const start = html.indexOf('aria-label="Docs sidebar"');
  assert.ok(start !== -1, `${relativePage} has no docs sidebar`);
  const end = html.indexOf('</nav>', start);
  const sidebar = html.slice(start, end);
  return [...sidebar.matchAll(/href="([^"]+)"/g)].map((match) => match[1]);
}

function assertSidebarHas(relativePage, hrefs) {
  const found = docsSidebarHrefs(relativePage);
  for (const href of hrefs) {
    assert.ok(found.includes(href), `${relativePage} sidebar is missing ${href}`);
  }
}

test('the English sidebar links to the pages from the English docs', () => {
  assertSidebarHas('docs/index.html', [
    '/bob/docs/why-bob',
    '/bob/docs/getting-started/installation',
    '/bob/docs/guides/configuration',
    '/bob/docs/reference/cli',
    '/bob/docs/architecture/overview',
    '/bob/docs/contributing',
  ]);
  assertSidebarHas('docs/getting-started/installation/index.html', [
    '/bob/docs/getting-started/installation',
    '/bob/docs/getting-started/first-check',
    '/bob/docs/getting-started/agents',
  ]);
  assertSidebarHas('docs/guides/configuration/index.html', [
    '/bob/docs/guides/configuration',
    '/bob/docs/guides/gates-and-waivers',
    '/bob/docs/guides/pre-push',
    '/bob/docs/guides/ci',
    '/bob/docs/guides/reports',
  ]);
  assertSidebarHas('docs/reference/cli/index.html', [
    '/bob/docs/reference/cli',
    '/bob/docs/reference/configuration',
    '/bob/docs/exit-codes',
    '/bob/docs/reference/report-json',
  ]);
  assertSidebarHas('docs/architecture/overview/index.html', [
    '/bob/docs/architecture/overview',
    '/bob/docs/architecture/adrs',
    '/bob/docs/architecture/spec',
    '/bob/docs/SPEC',
  ]);
  assertSidebarHas('docs/adr/0007-gerador-do-site/index.html', [
    '/bob/docs/adr/0000-architecture-review',
    '/bob/docs/adr/0001-adaptadores-sobre-ferramentas-de-mercado',
    '/bob/docs/adr/0002-o-diff-filtra-o-veredito',
    '/bob/docs/adr/0003-exit-codes',
    '/bob/docs/adr/0004-empacotamento-quatro-agentes',
    '/bob/docs/adr/0005-modelo-de-gate-das-analises-novas',
    '/bob/docs/adr/0006-chave-estavel-do-waiver',
    '/bob/docs/adr/0007-gerador-do-site',
  ]);
  assertSidebarHas('docs/contributing/index.html', [
    '/bob/docs/contributing',
    '/bob/docs/changelog',
    '/bob/docs/publishing',
  ]);
});

const temporaryGuideHrefs = [
  '/bob/docs/visao-geral',
  '/bob/docs/instalacao',
  '/bob/docs/cli',
  '/bob/docs/configuracao',
  '/bob/docs/gates',
  '/bob/docs/relatorios',
  '/bob/docs/contribuicao',
];

test('temporary pt-BR guides stay generated and linked from the sidebar', () => {
  assertSidebarHas('docs/visao-geral/index.html', temporaryGuideHrefs);
  for (const href of temporaryGuideHrefs) {
    const relative = href.replace('/bob/', '');
    assert.ok(
      fs.existsSync(path.join(buildDir, relative, 'index.html')),
      `missing generated page ${relative}`,
    );
    assert.ok(
      fs.existsSync(path.join(buildDir, 'pt-BR', relative, 'index.html')),
      `missing pt-BR generated page ${relative}`,
    );
  }
});

const englishSectionHrefs = [
  '/docs/why-bob',
  '/docs/getting-started/installation',
  '/docs/guides/configuration',
  '/docs/reference/cli',
  '/docs/architecture/overview',
  '/docs/contributing',
  '/docs/changelog',
];

function localizedHref(locale, href) {
  const prefix = locale === 'pt-BR' ? '/bob/pt-BR' : '/bob';
  return `${prefix}${href}`;
}

test('the home and the footer link to the English pages in both locales', () => {
  for (const locale of ['en', 'pt-BR']) {
    const relative = locale === 'pt-BR' ? 'pt-BR/index.html' : 'index.html';
    const home = readBuild(relative);
    const footerStart = home.indexOf('<footer');
    assert.ok(footerStart !== -1, `${relative} has no footer`);
    const main = home.slice(0, footerStart);
    const footer = home.slice(footerStart);
    for (const href of englishSectionHrefs) {
      const absolute = localizedHref(locale, href);
      assert.ok(main.includes(`href="${absolute}"`), `${relative} main is missing ${absolute}`);
      assert.ok(
        footer.includes(`href="${absolute}"`),
        `${relative} footer is missing ${absolute}`,
      );
    }
    for (const href of temporaryGuideHrefs) {
      const absolute = localizedHref(locale, href.slice('/bob'.length));
      assert.ok(
        footer.includes(`href="${absolute}"`),
        `${relative} footer is missing temporary guide ${absolute}`,
      );
    }
  }
});

test('a broken anchor fails the production build', () => {
  const probe = path.join(docsDir, 'zz-broken-anchor.md');
  fs.writeFileSync(probe, '# Probe\n\n[missing](#does-not-exist)\n', 'utf8');
  try {
    const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'bob-site-anchor-'));
    const result = runBuild({}, outDir);
    const output = `${result.stdout}\n${result.stderr}`;
    assert.notEqual(result.status, 0, output);
    assert.match(output, /does-not-exist/);
  } finally {
    fs.rmSync(probe, { force: true });
  }
});

test('a broken markdown link fails the production build', () => {
  const probe = path.join(docsDir, 'zz-broken-link.md');
  fs.writeFileSync(probe, '# Probe\n\n[missing](./does-not-exist.md)\n', 'utf8');
  try {
    const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'bob-site-broken-'));
    const result = runBuild({}, outDir);
    const output = `${result.stdout}\n${result.stderr}`;
    assert.notEqual(result.status, 0, output);
    assert.match(output, /broken|does-not-exist/i);
  } finally {
    fs.rmSync(probe, { force: true });
  }
});
