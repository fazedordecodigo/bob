# Why bob

[Index](README.md) · [Installation](getting-started/installation.md) · [Gates and waivers](guides/gates-and-waivers.md) · [SPEC](SPEC.md)

An agent can change a lot of code before a person reviews it. Coverage, complexity, clones, dependency cycles, and mutation each answer a different question, and each tool exits with its own code and its own file. A reviewer then has to open every file and decide which finding is in the diff.

bob runs those measurements as gates on the diff. One command writes one report and exits with one code. The agent can loop on that code. The person reviewing the pull request gets one page that says where to look first.

## What one command adds

Each market tool stays behind an adapter. bob does not copy their code. The formula, the limits, the diff scope, differential mutation, and waivers stay in the Python package `bob-quality`.

Running lizard, jscpd, import-linter, and mutmut yourself still produces their raw output. A bob gate adds four things those runs do not share:

- The diff chooses what can block. Old debt stays in the report and does not change the exit code. See [ADR 0002](adr/0002-o-diff-filtra-o-veredito.md).
- The exit code is one of `0`, `1`, `2`, `3`, or `4`. When more than one gate returns a code, the process keeps the highest. See [Exit codes](exit-codes.md).
- `.bob/report.md` is one page for the reviewer. `.bob/report.json` is the same run in schema v1, in English. See [Reports](guides/reports.md).
- A waiver is a one-line reason in `.bob/waivers.yaml`, committed with the code, for a finding the team accepts. The human approves it in review.

`bob check` without `--gates` runs `crap`, `dry`, and `deps` (`DEFAULT_GATES` in `src/bob_quality/check.py`). Mutation and the other gates run when the command names them. The [gates guide](guides/gates-and-waivers.md) lists each one.

## Who it is for

The skills `bob-check`, `harden`, and `review-report` tell Cursor, Claude Code, GitHub Copilot, and Devin when to run the CLI, how to treat a surviving mutant, and how to carry the report into the pull request. Codex reads the same project skills folder as the `agents` installer target. See [Agents](getting-started/agents.md). The repository index for agents is [AGENTS.md](../AGENTS.md).

## Words

These pages use one word for each of these:

| Word | Meaning |
|---|---|
| gate | A named check (`crap`, `dry`, `deps`, `mutate`, and the opt-in names) |
| diff | The new side of `git diff <base>...HEAD` |
| changed function | A function whose line range overlaps the diff |
| baseline | The test suite run before a measurement that needs it |
| mutant | A small change mutation testing makes |
| survivor | A mutant the tests did not kill |
| waiver | One committed row in `.bob/waivers.yaml` with a one-line reason |
| clone | A duplicated block the `dry` gate reports |
| pin | The tool version `bob doctor` expects |
| report | `.bob/report.md` and `.bob/report.json` from one run |
| exit code | The process status `0`, `1`, `2`, `3`, or `4` |

Output language (`en` or `pt-BR`) is the language of CLI text and `report.md`. It is separate from the language of this site.
