import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const websiteDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const repoRoot = path.resolve(websiteDir, '..');
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

test('website dependencies stay inside the Docusaurus set', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(websiteDir, 'package.json'), 'utf8'));
  const declared = [
    ...Object.keys(manifest.dependencies ?? {}),
    ...Object.keys(manifest.devDependencies ?? {}),
  ];
  const unexpected = declared.filter((name) => !allowedDependencies.has(name));
  assert.deepEqual(unexpected, []);
});

test('the site is generated from docs/ without a second copy of the markdown', () => {
  assert.equal(fs.existsSync(path.join(websiteDir, 'docs')), false);
  const source = fs.readFileSync(path.join(repoRoot, 'docs/visao-geral.md'), 'utf8');
  const sentence = 'O bob mede o diff que um agente de código acabou de produzir.';
  assert.ok(source.includes(sentence));
  const page = readBuild('docs/visao-geral/index.html');
  assert.ok(page.includes(sentence), 'current docs/visao-geral.md was not rendered');
});

test('existing markdown renders braces and angle-bracket text', () => {
  const specification = readBuild('docs/SPEC/index.html');
  assert.match(specification, /mutatorName/);
  const exitCodes = readBuild('docs/exit-codes/index.html');
  assert.match(exitCodes, /config file not found: (?:<|&lt;)caminho(?:>|&gt;)/);
});

test('default locale is English and pt-BR is a configured locale', () => {
  const home = readBuild('index.html');
  assert.match(home, /<html[^>]*\slang="en"/);
  assert.match(home, /https:\/\/fazedordecodigo\.github\.io\/bob\//);
  assert.doesNotMatch(home, /bob\.fazedordecodigo\.com/);
  assert.match(home, /alt="bob"/);
  assert.match(home, /src="\/bob\/assets\/logo\.svg"/);
  assert.match(home, /Português \(Brasil\)/);

  const portuguese = readBuild('pt-BR/index.html');
  assert.match(portuguese, /<html[^>]*\slang="pt-BR"/);
  assert.match(portuguese, /English/);
});

test('docs pages expose the six approved sidebar sections', () => {
  const page = readBuild('docs/visao-geral/index.html');
  for (const label of sidebarLabels) {
    assert.ok(page.includes(label), `sidebar is missing ${label}`);
  }
});

test('links that leave docs/ point at the repository and the site has no custom-domain CNAME', () => {
  const index = readBuild('docs/index.html');
  assert.match(
    index,
    /href="https:\/\/github\.com\/fazedordecodigo\/bob\/blob\/main\/README\.pt-BR\.md"/,
  );
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

test('a broken markdown link fails the production build', () => {
  const probe = path.join(repoRoot, 'docs/zz-broken-link.md');
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
