# bob documentation

English guides for [bob](https://github.com/fazedordecodigo/bob/blob/main/README.md). They describe what the code on `main` does. The approved spec stays in [SPEC.md](SPEC.md). Where the spec and the code disagree, the page documents the code and says so.

The pip package is `bob-quality`. The command is `bob`. Marketplace listings use the name `bob`. The license is MIT (`LICENSE`).

The pt-BR pages of the public site are a separate change. These files are the English source.

## Português (temporário, até #160)

- [Visão geral](visao-geral.md)
- [Instalação](instalacao.md)
- [CLI](cli.md)
- [Configuração](configuracao.md)
- [Gates](gates.md)
- [Relatórios](relatorios.md)
- [Contribuição](contribuicao.md)

## Why bob

[Why bob](why-bob.md) states the problem the gates solve and what one command adds to running each tool on its own.

## Getting started

| Page | What it answers |
|---|---|
| [Installation](getting-started/installation.md) | Python, Node, the `bob-quality` package, and `bob doctor` |
| [First check](getting-started/first-check.md) | The first `bob check` and how to read the exit code |
| [Agents](getting-started/agents.md) | Cursor, Claude Code, Codex, Devin, and GitHub Copilot |

## Guides

| Page | What it answers |
|---|---|
| [Configuration](guides/configuration.md) | `bob.yaml`, output language, and `.bob/waivers.yaml` |
| [Gates and waivers](guides/gates-and-waivers.md) | What each gate measures, when it blocks, and the waiver id |
| [Pre-push hook](guides/pre-push.md) | The local hook and the gates it runs |
| [CI](guides/ci.md) | The GitHub Action, its inputs, and the pull request comment |
| [Reports](guides/reports.md) | How to read `.bob/report.md` |

## Reference

| Page | What it answers |
|---|---|
| [CLI](reference/cli.md) | Commands, flags, and output language |
| [Configuration schema](reference/configuration.md) | Every key the loader accepts, and the keys it rejects |
| [Exit codes](exit-codes.md) | Codes `0` through `4` |
| [report.json](reference/report-json.md) | Schema v1 fields |

## Architecture

| Page | What it answers |
|---|---|
| [Technical overview](architecture/overview.md) | How a run moves from the CLI to the report |
| [ADRs](architecture/adrs.md) | The decision records, including [ADR 0007](adr/0007-gerador-do-site.md) |
| [SPEC](architecture/spec.md) | Where to read the spec, and where the code differs |

## Contributing and changelog

- [Contributing](contributing.md)
- [Changelog](changelog.md)
- [Publishing the Cursor plugin](publishing.md)

## Where to start

- Install and compare versions: [Installation](getting-started/installation.md) and [`bob doctor`](reference/cli.md#bob-doctor).
- Measure a diff: [First check](getting-started/first-check.md) and [Exit codes](exit-codes.md).
- Change a limit or the output language: [Configuration](guides/configuration.md).
- Read the result: [Reports](guides/reports.md).
- Understand a verdict: [Gates and waivers](guides/gates-and-waivers.md).
