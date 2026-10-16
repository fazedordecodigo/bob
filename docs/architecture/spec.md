# SPEC

[Index](../README.md) · [Technical overview](overview.md) · [ADRs](adrs.md)

The approved specification is [SPEC.md](../SPEC.md). It stays the record of what was decided, including behavior the CLI does not implement yet. These guides document the code. They do not edit the spec.

Read the spec for the problem statement, the user stories, the implementation decisions, and the MVP acceptance criteria. Read the guides when you need the command, the flag, the key, or the exit code the process actually uses.

## Where the code and the spec disagree

The notes below are the disagreements these pages rely on. The code is the behavior.

**CI does not run every gate from inside the CLI.** The spec says the check in CI runs every gate. `DEFAULT_GATES` in `src/bob_quality/check.py` is `crap`, `dry`, `deps`. The Action input `gates` defaults to `crap,dry,deps,mutate` (`.github/actions/bob/action.yml`). `coverage`, `test_smells`, `cognitive`, `supply`, `security`, `typing`, `secrets`, and `dead_code` run only when `--gates` names them. There is no CI detector in the CLI.

**CRAP coverage is the statement fraction, not branch coverage.** The spec's adapter list says coverage.py and c8 return line and branch coverage, including lcov. `line_coverage` in `src/bob_quality/core.py` is the fraction of executable lines in the function range. The formula in `src/bob_quality/crap.py` uses that fraction. The `coverage` gate is a separate measurement: diff-cover on coverage XML for Python and on c8 lcov for TypeScript.

**`crap.scope` accepts only `changed` and `all`.** [ADR 0002](../adr/0002-o-diff-filtra-o-veredito.md) says any other non-empty string counts every measured function. The loader rejects any other string with exit `4`. See [Configuration schema](../reference/configuration.md).

**Exit `4` during measurement writes the report.** The preflight writes nothing. `_fail_early` in `check.py` writes the report when git fails or a tool blocks the measurement. The [exit codes](../exit-codes.md#exit-4) page separates the two paths. A short README sentence that says exit `4` writes nothing describes the preflight.

**Stryker is in the tree.** [ADR 0001](../adr/0001-adaptadores-sobre-ferramentas-de-mercado.md) and [ADR 0000](../adr/0000-architecture-review.md) record a checkout with no Stryker adapter. `src/bob_quality/adapters/stryker.py` and the Stryker pins in `doctor.py` are on `main`. Those ADRs are the record of the earlier decision, not a claim about the current tree.

**The Markdown report leads with waivers.** The spec's report order starts with the header and the verdict. `to_markdown` emits `## Waivers` first when the section exists. See [Reports](../guides/reports.md).

**Relative churn is in the report.** [ADR 0005](../adr/0005-modelo-de-gate-das-analises-novas.md) describes churn as the commit count in the window. The code also writes a relative rate: changed lines divided by the file's line count. The commit count is still there. The rate is `null` when the file has no lines or cannot be read. The section still does not change the exit code.
