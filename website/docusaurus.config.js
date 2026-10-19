// @ts-check

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const siteDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(siteDir, '..');
const docsDir = path.join(repoRoot, 'docs');

/**
 * Links that point at a real file outside `docs/` cannot be site routes.
 * Send them to the file in the repository so the current guides stay usable.
 * Any other unresolved markdown link fails the build.
 *
 * @param {{ sourceFilePath: string, url: string }} params
 * @returns {string | undefined}
 */
function onBrokenMarkdownLinks({ sourceFilePath, url }) {
  const rewritten = repositoryUrl(sourceFilePath, url);
  if (rewritten) {
    return rewritten;
  }
  throw new Error(`Broken markdown link in ${sourceFilePath}: ${url}`);
}

/**
 * @param {string} sourceFilePath
 * @param {string} url
 * @returns {string | undefined}
 */
function repositoryUrl(sourceFilePath, url) {
  const hashIndex = url.indexOf('#');
  const withoutHash = hashIndex === -1 ? url : url.slice(0, hashIndex);
  const hash = hashIndex === -1 ? '' : url.slice(hashIndex);
  if (!withoutHash.startsWith('.')) {
    return undefined;
  }
  const sourcePath = path.resolve(process.cwd(), sourceFilePath);
  const target = path.resolve(path.dirname(sourcePath), withoutHash);
  const insideDocs = target === docsDir || target.startsWith(`${docsDir}${path.sep}`);
  const insideRepo = target === repoRoot || target.startsWith(`${repoRoot}${path.sep}`);
  if (!insideRepo || insideDocs || !fs.existsSync(target) || !fs.statSync(target).isFile()) {
    return undefined;
  }
  const relative = path.relative(repoRoot, target).split(path.sep).join('/');
  return `https://github.com/fazedordecodigo/bob/blob/main/${relative}${hash}`;
}

/**
 * Search stays off unless every Algolia value is present. Nothing is hardcoded.
 *
 * @param {NodeJS.ProcessEnv} env
 */
function algoliaFromEnv(env) {
  const appId = env.ALGOLIA_APP_ID?.trim() ?? '';
  const apiKey = env.ALGOLIA_API_KEY?.trim() ?? '';
  const indexName = env.ALGOLIA_INDEX_NAME?.trim() ?? '';
  if (!appId || !apiKey || !indexName) {
    return undefined;
  }
  return {
    appId,
    apiKey,
    indexName,
    contextualSearch: true,
  };
}

const algolia = algoliaFromEnv(process.env);

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'bob',
  tagline: 'Deterministic quality gates for the code a coding agent changes.',
  url: 'https://fazedordecodigo.github.io',
  baseUrl: '/bob/',
  favicon: 'assets/logo.svg',
  onBrokenLinks: 'throw',
  onBrokenAnchors: 'throw',
  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'pt-BR'],
    localeConfigs: {
      en: {
        label: 'English',
        htmlLang: 'en',
      },
      'pt-BR': {
        label: 'Português (Brasil)',
        htmlLang: 'pt-BR',
      },
    },
  },
  markdown: {
    format: 'md',
    hooks: {
      onBrokenMarkdownLinks,
    },
  },
  presets: [
    [
      'classic',
      {
        docs: {
          path: '../docs',
          routeBasePath: 'docs',
          sidebarPath: './sidebars.js',
          // ADR filenames start with 0000-. Keep that prefix in the id and the URL.
          numberPrefixParser: false,
          editUrl: 'https://github.com/fazedordecodigo/bob/edit/main/docs/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      },
    ],
  ],
  themeConfig: {
    navbar: {
      title: 'bob',
      logo: {
        alt: 'bob',
        src: 'assets/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docs',
          position: 'left',
          label: 'Docs',
        },
        {
          href: 'https://github.com/fazedordecodigo/bob',
          label: 'GitHub',
          position: 'right',
        },
        {
          type: 'localeDropdown',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            { label: 'Why bob', to: '/docs/why-bob' },
            { label: 'Getting started', to: '/docs/getting-started/installation' },
            { label: 'Guides', to: '/docs/guides/configuration' },
            { label: 'Reference', to: '/docs/reference/cli' },
            { label: 'Architecture', to: '/docs/architecture/overview' },
            { label: 'Contributing', to: '/docs/contributing' },
            { label: 'Changelog', to: '/docs/changelog' },
          ],
        },
      ],
      copyright: 'MIT License © 2026 Emerson Delatorre',
    },
    colorMode: {
      respectPrefersColorScheme: true,
    },
    ...(algolia ? { algolia } : {}),
  },
};

export default config;
