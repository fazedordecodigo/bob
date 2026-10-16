# bob docs site

Static site for the guides in `../docs`. The markdown stays in that directory; this package does not copy it.

```bash
cd website
npm ci
npm run build
```

The build uses `onBrokenLinks: 'throw'` and CommonMark (`markdown.format: 'md'`). The site is set up for GitHub Pages at `https://fazedordecodigo.github.io/bob/`. English is the default locale. Brazilian Portuguese is available at `/bob/pt-BR/`; the translated pages are a later change.

Algolia DocSearch is included only when all three variables are set: `ALGOLIA_APP_ID`, `ALGOLIA_API_KEY`, and `ALGOLIA_INDEX_NAME`.

`npm test` checks the output of `npm run build`.
