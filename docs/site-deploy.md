# Deploy the docs site

[Index](README.md) · [ADR 0007](adr/0007-gerador-do-site.md)

GitHub Actions publishes the Docusaurus site to GitHub Pages at `https://fazedordecodigo.github.io/bob/`. The workflow is [`.github/workflows/pages.yml`](https://github.com/fazedordecodigo/bob/blob/main/.github/workflows/pages.yml).

The site config stays `url: 'https://fazedordecodigo.github.io'` and `baseUrl: '/bob/'`. There is no CNAME, no custom domain, and no DNS record. The domain `bob.fazedordecodigo.com` is a later change ([#163](https://github.com/fazedordecodigo/bob/issues/163)).

## One-time setup

Pages is not enabled on this repository. `GET /repos/fazedordecodigo/bob/pages` returns 404. This workflow does not turn Pages on and it does not create a secret. Enabling Pages with `actions/configure-pages` would need a token other than `GITHUB_TOKEN`, and the workflow sets `enablement: false`.

Emerson saves this once, in the repository settings:

**Settings > Pages > Build and deployment > Source: GitHub Actions.**

Leave the custom domain empty. Do not add a CNAME file.

## Repo settings

Pages source is GitHub Actions, set in the step above. The recommended deployment branch rule for the `github-pages` environment is `main` only: **Settings > Environments > github-pages > Deployment branches and tags > Selected branches > `main`.** A workflow run from any other ref cannot deploy.

Until the Pages source is saved, a deploy run fails in `actions/configure-pages` or `actions/deploy-pages`. The live URLs do not return HTTP 200, so there is no curl evidence yet. The first green deploy, and the `curl -I` output below, come after this setting and after the workflow is on `main`.

## What a run does

The workflow runs in two cases.

- A push to `main` that changes `website/**` or `docs/**`. A commit that changes only the workflow file does not publish. Dispatch it from `main`.
- `workflow_dispatch` on `main`. The input `ref` is optional and only selects the tree to build. Empty builds the `main` commit the workflow runs on.

The build job has `contents: read`. Checkout uses `persist-credentials: false` and checks out `inputs.ref` when it is set, otherwise `github.sha`. It installs Node `22.18.0`, then runs `npm ci`, `npm run build`, and `npm test` in `website/`. The Pages artifact is `website/build`.

The deploy job needs the build job. Its token has `pages: write` and `id-token: write`, and nothing else. It runs in the `github-pages` environment. The steps are `actions/configure-pages` (`enablement: false`), `actions/deploy-pages`, then the health check. The three Pages actions are the official `actions/*` actions, pinned by commit SHA.

The concurrency group is `pages`. An in-progress deploy is not cancelled. A newer queued run replaces an older queued run.

## Health check

The deploy job fails unless both of these URLs return HTTP 200. It retries for a short propagation window: 10 attempts, 10 seconds apart, about two minutes.

```bash
curl --silent --show-error --head --output /dev/null --write-out '%{http_code}\n' --max-time 20 https://fazedordecodigo.github.io/bob/
curl --silent --show-error --head --output /dev/null --write-out '%{http_code}\n' --max-time 20 https://fazedordecodigo.github.io/bob/pt-BR/
```

Both lines must print `200`. The job sends that `HEAD` request with `--write-out '%{http_code}'`, no `-f`, and no redirect follow. The commands above add a newline after the code. A `301` or a `404` fails the job. The job repeats the request up to 10 times, 10 seconds apart.

`actions/deploy-pages` publishes the artifact before the check. A red health check means the new artifact is already public. Roll it back with one of the commands below. The check does not unpublish.

## Rollback

No secret is required. Only `main` can deploy once the `github-pages` environment is limited to that branch. Do not dispatch `pages.yml` from another branch or tag.

### Revert on `main`

This is the path that still works after GitHub's 30-day re-run window.

```bash
git fetch origin main
git checkout main
git revert --no-edit <bad-commit-sha>
git push origin main
```

Target: `main`. The revert commit has to change `website/**` or `docs/**`. That push is what starts `pages.yml`. If the bad commit did not touch those paths, dispatch from `main` instead.

Expected time: about 5 minutes from the push until the health check passes. The build is the same work as the pull request site build, about 3 minutes. The health check then allows about 2 minutes (10 attempts, 10 seconds apart). If both URLs need every attempt, the run takes about 7 minutes.

### Dispatch the workflow on `main`

```bash
gh workflow run pages.yml --repo fazedordecodigo/bob --ref main -f ref=<commit-sha>
```

Target: the workflow runs on `main`. `<commit-sha>` is only the tree to build, and it must still contain `website/` and `docs/`. Omit `-f ref=` to build the tip of `main`.

Expected time: about 5 minutes, or about 7 minutes when the health check uses every retry.

### Re-run a successful run from the last 30 days

GitHub accepts `gh run rerun` for 30 days after the run. After that window, revert on `main`.

```bash
gh run list --repo fazedordecodigo/bob --workflow pages.yml --status success --limit 20
gh run rerun <run-id> --repo fazedordecodigo/bob
```

The run being re-run must be one that already ran on `main`. Re-run uses that run's commit and workflow snapshot. The health check runs again. Expected time: about 5 minutes, the same as a dispatch on `main`.

## After the merge

Merging this change pushes `docs/`, so the workflow starts on `main`. That run stays red until Source is GitHub Actions. After the setting is saved, re-run the failed workflow (it already ran on `main`), or dispatch `pages.yml` from `main`. Then collect the evidence:

```bash
curl -I https://fazedordecodigo.github.io/bob/
curl -I https://fazedordecodigo.github.io/bob/pt-BR/
```

Expect `HTTP/2 200` on both. That output is not available from the pull request. Pages is still off, and the site is not served yet.
