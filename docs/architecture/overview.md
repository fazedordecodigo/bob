# Technical overview

[Index](../README.md) · [ADRs](adrs.md) · [SPEC](spec.md) · [Exit codes](../exit-codes.md)

bob is the CLI of the pip package `bob-quality` and the marketplace plugin `bob`. Nothing has been published to PyPI or to a marketplace. A run measures a diff and returns one report plus one exit code. The skills `bob-check`, `harden`, and `review-report` are what Cursor, Claude Code, GitHub Copilot, and Devin load. Codex is named only as a reader of `.agents/skills`.

This page describes the code on `main`. [ADR 0000](../adr/0000-architecture-review.md) is the reading from 12/10/2026 at commit `246d2eb`. Later gates and the Stryker adapter are in the tree now. The ADR is unchanged.

## Four seams

1. `cli.py` resolves the output language and runs the preflight. `check`, `crap`, `dry`, `deps`, and `mutate` become `run_check`. `doctor`, `waive`, and `report` leave that path after the same preflight. `report` does not measure.
2. The gates start the pinned tools. Adapters parse text or JSON into the model in `models.py`. The core does not import an adapter.
3. `crap.py`, `core.py`, and `probe.py` join cyclomatic complexity and line coverage, apply the formula, and mark what the diff can block.
4. `check.py` builds the `Report`. `report.py` writes `.bob/report.md` and `.bob/report.json` with `schema_version` 1. The process exit is the highest code among the gates.

## What the diff filters

The tools measure the tree under `paths.include`. `changed_lines` in `diff.py` runs `git diff --unified=0 <base>...HEAD` and keeps the new side. A zero-length new hunk still records the anchor line. `function_is_changed` is an inclusive overlap of `[start, end]`.

Only a finding the diff selects can change the exit code. The rest can appear in the report. [ADR 0002](../adr/0002-o-diff-filtra-o-veredito.md) records that split. The loader's rule for `crap.scope` is narrower than one sentence in that ADR: only `changed` and `all` are accepted. See [Configuration schema](../reference/configuration.md).

## Gates

`DEFAULT_GATES` is `crap`, `dry`, `deps`. There is no CI detector inside the CLI. The Action passes `crap,dry,deps,mutate` unless the workflow sets `gates`.

`check.py` also runs `coverage`, `test_smells`, `cognitive`, `supply`, `security`, `typing`, `secrets`, and `dead_code` when `--gates` names them. An unknown name is `not_run` and contributes `0`. Churn is measured on every check and is not a gate.

Mutation is differential. Python uses mutmut and `.bob/mutation-cache.json`. TypeScript uses Stryker, `.bob/stryker-incremental.json`, and `.bob/stryker-mutants.json`. [ADR 0001](../adr/0001-adaptadores-sobre-ferramentas-de-mercado.md) recorded the absence of a Stryker adapter. `src/bob_quality/adapters/stryker.py` is in the tree now.

## Waivers and the report

Waivers are `.bob/waivers.yaml`, with `id`, a one-line `reason`, `author`, and `date`. Mutation ids are `file::function` or `file::function::<description>` ([ADR 0006](../adr/0006-chave-estavel-do-waiver.md)). The other gates use the prefixes in [Gates and waivers](../guides/gates-and-waivers.md).

`schema_version` stays 1. New sections are optional in `report_v1.json`. The JSON stays English. The Markdown translates headings. See [report.json](../reference/report-json.md).

## What this repository does not do

The `package` workflow builds an sdist and a wheel, runs `twine check`, and runs `bob doctor`. It does not publish. Marketplace publication stays on Emerson's approval. The public documentation site is [ADR 0007](../adr/0007-gerador-do-site.md): Docusaurus 3.x, Algolia DocSearch, English as the default language, pt-BR as the second, first at `https://fazedordecodigo.github.io/bob/`, isolated in `website/`. The custom domain is [issue 163](https://github.com/fazedordecodigo/bob/issues/163).
