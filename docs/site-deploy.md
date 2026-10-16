# Deploy the docs site

[Index](README.md) · [ADR 0007](adr/0007-gerador-do-site.md)

GitHub Actions publishes the Docusaurus site to GitHub Pages at `https://fazedordecodigo.github.io/bob/`. The workflow is [`.github/workflows/pages.yml`](https://github.com/fazedordecodigo/bob/blob/main/.github/workflows/pages.yml).

The site config stays `url: 'https://fazedordecodigo.github.io'` and `baseUrl: '/bob/'`. There is no CNAME, no custom domain, and no DNS record. The domain `bob.fazedordecodigo.com` is a later change ([#163](https://github.com/fazedordecodigo/bob/issues/163)).

## One-time setup

Pages is not enabled on this repository. `GET /repos/fazedordecodigo/bob/pages` returns 404. This workflow does not turn Pages on and it does not create a secret. Enabling Pages with `actions/configure-pages` would need a token other than `GITHUB_TOKEN`, and the workflow sets `enablement: false`.

Emerson saves this once, in the repository settings:

**Settings > Pages > Build and deployment > Source: GitHub Actions.**

Leave the custom domain empty. Do not add a CNAME file.

Until that source is saved, a deploy run fails in `actions/configure-pages` or `actions/deploy-pages`. The live URLs do not return HTTP 200, so there is no curl evidence yet. The first green deploy, and the `curl -I` output below, come after this setting and after the workflow is on `main`.

## What a run does

The workflow runs in two cases.

- A push to `main` that changes `website/**` or `docs/**`. A commit that changes only the workflow file does not publish. Dispatch it.
- `workflow_dispatch`. The input `ref` is optional. Empty uses the commit selected as the workflow ref.

The build job has `contents: read`. Checkout uses `persist-credentials: false` and checks out `inputs.ref` when it is set, otherwise `github.sha`. It installs Node `22.18.0`, then runs `npm ci`, `npm run build`, and `npm test` in `website/`. The Pages artifact is `website/build`.

The deploy job needs the build job. Its token has `pages: write` and `id-token: write`, and nothing else. It runs in the `github-pages` environment. The steps are `actions/configure-pages` (`enablement: false`), `actions/deploy-pages`, then the health check. The three Pages actions are the official `actions/*` actions, pinned by commit SHA.

The concurrency group is `pages`. An in-progress deploy is not cancelled. A newer queued run replaces an older queued run.

## Health check

The deploy job fails unless both of these URLs return HTTP 200. It retries for a short propagation window: 10 attempts, 10 seconds apart, about two minutes.

```bash
curl -fsS -o /dev/null -w "%{http_code}\n" --max-time 20 https://fazedordecodigo.github.io/bob/
curl -fsS -o /dev/null -w "%{http_code}\n" --max-time 20 https://fazedordecodigo.github.io/bob/pt-BR/
```

Both lines must print `200`. The same request is what the job runs (`curl --head`). A 301 or a 404 fails the job. The check does not follow redirects.

`actions/deploy-pages` publishes the artifact before the check. A red health check means the new artifact is already public. Roll it back with one of the commands below. The check does not unpublish.

## Rollback

No secret is required. Pick one of the two.

### Dispatch the workflow on a previous commit

This uses the workflow file on `main` and builds the tree at `<commit-sha>`:

```bash
gh workflow run pages.yml \
  --repo fazedordecodigo/bob \
  --ref main \
  -f ref=<commit-sha>
```

`<commit-sha>` can also be a branch or a tag. Use a ref that still contains `website/` and `docs/`.

To run the workflow file that already exists on a branch or tag, omit the input. Checkout then uses that ref:

```bash
gh workflow run pages.yml --repo fazedordecodigo/bob --ref <branch-or-tag>
```

`--ref` has to be a branch or a tag. A bare commit that does not contain `pages.yml` cannot be selected that way. Pass it as `-f ref=` instead, or re-run an older successful run.

### Re-run an older successful run

```bash
gh run list --repo fazedordecodigo/bob --workflow pages.yml --status success --limit 20
gh run rerun <run-id> --repo fazedordecodigo/bob
```

Re-run uses the same commit and the same workflow snapshot as that run. The health check runs again.

## After the merge

Merging this change pushes `docs/`, so the workflow starts on `main`. That run stays red until Source is GitHub Actions. After the setting is saved, re-run the failed workflow, or dispatch `pages.yml`. Then collect the evidence:

```bash
curl -I https://fazedordecodigo.github.io/bob/
curl -I https://fazedordecodigo.github.io/bob/pt-BR/
```

Expect `HTTP/2 200` on both. That output is not available from the pull request. Pages is still off, and the site is not served yet.
