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

const englishHomeRoutes = [
  '/docs/why-bob',
  '/docs/getting-started/installation',
  '/docs/guides/configuration',
  '/docs/reference/cli',
  '/docs/architecture/overview',
  '/docs/contributing',
];

const temporaryPortugueseRoutes = [
  '/docs/visao-geral',
  '/docs/instalacao',
  '/docs/cli',
  '/docs/configuracao',
  '/docs/gates',
  '/docs/relatorios',
  '/docs/contribuicao',
];

const englishSidebar = {
  'Why bob': ['why-bob', 'README'],
  'Getting started': [
    'getting-started/installation',
    'getting-started/first-check',
    'getting-started/agents',
  ],
  Guides: [
    'guides/configuration',
    'guides/gates-and-waivers',
    'guides/pre-push',
    'guides/ci',
    'guides/reports',
  ],
  Reference: [
    'reference/cli',
    'reference/configuration',
    'exit-codes',
    'reference/report-json',
  ],
  Architecture: [
    'architecture/overview',
    'architecture/adrs',
    'architecture/spec',
    'adr/0000-architecture-review',
    'adr/0001-adaptadores-sobre-ferramentas-de-mercado',
    'adr/0002-o-diff-filtra-o-veredito',
    'adr/0003-exit-codes',
    'adr/0004-empacotamento-quatro-agentes',
    'adr/0005-modelo-de-gate-das-analises-novas',
    'adr/0006-chave-estavel-do-waiver',
    'adr/0007-gerador-do-site',
  ],
  'Contributing and changelog': ['contributing', 'changelog', 'publishing'],
};

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

function docIds(items) {
  const ids = [];
  for (const item of items) {
    if (typeof item === 'string') {
      ids.push(item);
    } else if (item.type === 'doc') {
      ids.push(item.id);
    } else if (item.type === 'category') {
      ids.push(...docIds(item.items));
    }
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

test('sidebar doc ids match the English docs files', async () => {
  const sidebars = (await import('../sidebars.js')).default;
  assert.deepEqual(
    sidebars.docs.map((category) => category.label),
    sidebarLabels,
  );
  for (const category of sidebars.docs) {
    assert.equal(category.type, 'category');
    const expected = englishSidebar[category.label];
    assert.deepEqual(docIds(category.items), expected, category.label);
    for (const id of expected) {
      assert.ok(sourceForDoc(id), `sidebar id ${id} has no file under docs/`);
    }
  }
});

test('footer links to the English pages and the temporary pt-BR guides stay reachable', async () => {
  const config = (await import('../docusaurus.config.js')).default;
  assert.equal(config.onBrokenAnchors, 'throw');
  const columns = config.themeConfig.footer.links;
  assert.deepEqual(
    columns[0].items.map((item) => item.to),
    englishHomeRoutes,
  );
  const temporary = columns.flatMap((column) => column.items.map((item) => item.to));
  for (const route of temporaryPortugueseRoutes) {
    assert.ok(temporary.includes(route), `footer is missing ${route}`);
    assert.ok(sourceForDoc(route.slice('/docs/'.length)), `missing docs file for ${route}`);
  }
});

function pageLinksTo(html, route) {
  return html.includes(`/bob${route}`) || html.includes(`/bob${route}/`);
}

function menuLinks(html) {
  return [...html.matchAll(/class="[^"]*menu__link[^"]*"[^>]*href="([^"]+)"/g)].map(
    (match) => match[1],
  );
}

test('the built home, footer, and sidebar link to the English pages', () => {
  const home = readBuild('index.html');
  const portugueseHome = readBuild('pt-BR/index.html');
  const docs = readBuild('docs/index.html');
  const sidebar = menuLinks(docs);
  for (const route of englishHomeRoutes) {
    assert.ok(pageLinksTo(home, route), `English home is missing ${route}`);
    assert.ok(pageLinksTo(portugueseHome, `/pt-BR${route}`), `pt-BR home is missing ${route}`);
    assert.ok(
      sidebar.some((href) => href === `/bob${route}` || href === `/bob${route}/`),
      `docs sidebar is missing ${route}`,
    );
  }
  assert.equal(
    sidebar.some((href) => href.includes('/docs/visao-geral')),
    false,
    'docs sidebar still points at the temporary pt-BR overview',
  );
  for (const route of temporaryPortugueseRoutes) {
    assert.ok(pageLinksTo(home, route), `footer is missing the temporary guide ${route}`);
    assert.ok(
      fs.existsSync(path.join(buildDir, `${route.slice(1)}/index.html`)),
      `temporary guide was not published: ${route}`,
    );
    assert.ok(
      fs.existsSync(path.join(buildDir, `pt-BR${route}/index.html`)),
      `temporary guide was not published for pt-BR: ${route}`,
    );
  }
});

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

test('a broken anchor fails the production build', () => {
  const probe = path.join(docsDir, 'zz-broken-anchor.md');
  fs.writeFileSync(probe, '# Probe\n\n[missing](#this-anchor-does-not-exist)\n', 'utf8');
  try {
    const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'bob-site-anchor-'));
    const result = runBuild({}, outDir);
    const output = `${result.stdout}\n${result.stderr}`;
    assert.notEqual(result.status, 0, output);
    assert.match(output, /broken anchor|this-anchor-does-not-exist/i);
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
