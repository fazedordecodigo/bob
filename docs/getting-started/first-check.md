# First check

[Index](../README.md) · [Installation](installation.md) · [CLI](../reference/cli.md) · [Exit codes](../exit-codes.md)

In a git checkout that has the code you want to measure, with `bob` on `PATH`:

```bash
bob check --base origin/main
```

`--base` selects the ref of `git diff <base>...HEAD`. When the flag is omitted, bob uses the `base` key in `bob.yaml`, or `origin/main` when that key is omitted (`Config.base` in `src/bob_quality/config.py`).

Without `--gates`, the command runs `crap`, `dry`, and `deps`. It does not run mutation. To run mutation on the changed functions:

```bash
bob check --base origin/main --gates crap,dry,deps,mutate
```

The run writes `.bob/report.md` and `.bob/report.json` unless the preflight rejects the configuration. `--format md`, `--format json`, or `--format both` (the default) chooses the files. `--out` changes the directory. The default is `.bob/`.

## What the exit code means

| Code | Meaning |
|---|---|
| `0` | Every gate that ran passed, or only warned. |
| `1` | A blocking gate failed on the diff. |
| `2` | The baseline tests failed before bob could measure. |
| `3` | A surviving mutant on a changed line has no waiver, or a changed function has a `no_coverage` mutant. |
| `4` | Invalid configuration, invalid command-line usage, or a missing tool that blocks the requested measurement. |

When more than one gate returns a code, the process keeps the highest (`_worse` in `src/bob_quality/check.py`). The full catalog is [Exit codes](../exit-codes.md).

Open `.bob/report.md` at the Verdict section. A gate that did not run is marked not run, with a reason. It is never shown as passed. [Reports](../guides/reports.md) walks the rest of the page.

A local `bob check` does not run mutation unless `mutate` is in `--gates`. The pre-push hook uses the three fast gates. The GitHub Action's default input adds `mutate`. See [Pre-push hook](../guides/pre-push.md) and [CI](../guides/ci.md).

## A repository without bob.yaml

If `bob.yaml` is missing and `--config` was not passed, bob uses the defaults and detects languages from files under `paths.include`. See [Configuration](../guides/configuration.md). If `--config` names a file that is not there, `check`, `crap`, `dry`, `deps`, and `mutate` exit `4`, print `config file not found: <path>` on stderr, and write nothing.
