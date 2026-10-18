# CI with the GitHub Action

[Index](../README.md) · [Pre-push hook](pre-push.md) · [Reports](reports.md) · [CLI](../reference/cli.md)

The composite action in `.github/actions/bob` installs bob and runs `bob check`. This repository calls it from `.github/workflows/bob.yml`.

## Inputs

From `.github/actions/bob/action.yml`:

| Input | Default | Effect |
|---|---|---|
| `base` | empty | Diff ref. Empty uses `origin/$GITHUB_BASE_REF` on a pull request. Otherwise bob uses `bob.yaml`. |
| `gates` | `crap,dry,deps,mutate` | Comma-separated list. |
| `pip-spec` | empty | Explicit pip requirement. Empty installs the checkout when it is `bob-quality`. Otherwise it installs the action's git source. |
| `token` | empty | Comment and artifacts. Empty uses the workflow `GITHUB_TOKEN`. |
| `language` | empty | `en` or `pt-BR` for `bob check` and for the pull request comment. Empty leaves `BOB_LANG` and `language` in `bob.yaml` in charge. |

`bob-quality` is not on PyPI. In a checkout of this repository the action runs `pip install -e ".[dev]"` (`install.sh`). In another repository it installs the action's git source. Publication on the GitHub Marketplace is not part of this action.

## What the job installs

The action sets up Python 3.12 and Node `22.18.0` (`actions/setup-node` pinned by SHA in `action.yml`). It then installs jscpd `5.4.1` so the `dry` gate can run when the caller did not install Node and jscpd. Without that install, `dry` stays `not_run`.

`bob doctor` accepts Node `>=22.18.0 <23`. CI workflows `.github/workflows/ci.yml` and `.github/workflows/bob.yml` use Node `22.18.0`. The Action's setup step uses that same `22.18.0`.

## Cache and comment

The action restores `.bob/mutation-cache.json` and `.bob/stryker-incremental.json` from the `bob-mutation-cache` artifact. A restore failure does not stop the check (`restore_cache.py || echo` in the action). The upload uses `if: always()`, `retention-days: 7`, and `if-no-files-found: ignore`. One of the two files may be absent.

On a pull request the action creates or updates one comment with `.bob/report.md`. The marker and the truncation limit live in `.github/actions/bob/upsert_comment.py`. The body limit is 65536 characters. Above that, the comment is truncated and the note uses the resolved output language. Comment errors use that language too: missing repo, pr, or token; missing report; invalid comment list. The job exit code is bob's exit code, including `4` for invalid command-line usage (`propagate_exit.sh`).

The comment resolves language with `resolve_language`. The order is the Action `language` input, then `BOB_LANG`, then `language` in `bob.yaml`, then `en`. An empty `language` input is skipped. `upsert_comment.py` reads `bob.yaml` from the process working directory.

## Gates the default input does not run

The default `gates` value is `crap,dry,deps,mutate`. These names run only when the workflow adds them to `gates`: `coverage`, `test_smells`, `cognitive`, `supply`, `security`, `typing`, `secrets`, `dead_code`. An unknown name is `not_run` and contributes exit `0`.

The spec says the CI check runs every gate. The code runs the Action input. The default input is the four names above. See [SPEC](../architecture/spec.md).
