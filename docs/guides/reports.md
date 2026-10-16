# Reading the report

[Index](../README.md) · [report.json](../reference/report-json.md) · [Exit codes](../exit-codes.md) · [CI](ci.md)

`bob check` and the single-gate commands write `.bob/report.md` and `.bob/report.json` by default. `--out` changes the directory. `--format md`, `json`, or `both` (the default) chooses the file. `crap`, `dry`, `deps`, and `mutate` always write both, because `cli.py` calls `run_check` with `fmt="both"`.

`bob report` renders a saved `report.json` as Markdown. It does not measure again. See [CLI](../reference/cli.md#bob-report).

The schema is `src/bob_quality/schemas/report_v1.json`. `schema_version` is `1`.

## Markdown order

`to_markdown` in `src/bob_quality/report.py` emits the sections below in the output language. The headings here are the `en` ones.

1. Title `# bob report`.
2. `## Waivers`, only when waivers already exist or mutation ran. The heading `## Waivers` is the same string in both languages. The table columns are target, reason, author, and date. With no rows the text is `No waivers.`
3. A header with the commit, the base, the date, and the tool versions. The labels `Commit:` and `Base:` stay English.
4. `## Verdict`, one line per gate: ✅ passed, ⚠️ warning, ❌ failed, or ⏭️ not run. A reason, when there is one, is in parentheses.
5. `## Where to focus the review`. Changed files ordered by risk (highest CRAP, plus clones and, when mutation ran, an extra 100 of risk for each blocking survivor). A survivor with a waiver, or outside the diff, does not add risk and does not add a new file. A file with a clone gets the suffix `, clone`.
6. `## Top 5 functions by CRAP (diff)`. Function, file:line, CC, coverage as an integer percent, CRAP, and delta. A missing delta is `—`.
7. `## Information (old debt)`, only when a function outside the diff is at or above the limit. The item ends with `outside the diff; does not block`.
8. `## Dependency violations and cycles`, then `## Information (dependencies outside the diff)` when there are violations outside the diff.
9. `## New clones`. Each pair lists the files, the lines, the tokens, and the similarity.
10. `## Surviving mutants`, only when mutation ran. Columns: target, function, location, operator, waiver. The target is what `bob waive` accepts for that survivor, or `—` when another survivor of the function has the same description. An unwaived survivor that does not block carries `outside the diff; does not block` on the location.
11. `## Mutants without tests`, only when the mutation summary has `no_coverage`. The total line says it blocks.
12. `## Diff coverage`, only when the `coverage` gate is in the verdict. It lists each measured language percent and each uncovered line as `` `file:line` ``. If the gate ran and no language measured, the section shows the reason and no table.
13. `## Diff tests`, only when `test_smells` ran. The id is `tests:<file>:<line>:<rule>`.
14. `## New dependencies`, only when the supply gate measured.
15. `## Types`, only when the typing gate was requested.
16. `## Secrets`, only when the secrets gate measured. The target is `secret:<rule>:<file>:<line>`. The line `Outside the diff; does not block.` introduces findings that do not change the exit.
17. `## Cognitive complexity`, only when `cognitive` was requested, including `not_run`.
18. `## Dead code`, only when `dead_code` was requested, including `not_run`.
19. `## Security`, only when `security` ran, including `not_run`. Disposition in the Markdown is translated. The JSON keeps `fail`, `warn`, `waived`, and `off_diff`.
20. `## Churn`, always, including on an early failure and when the count cannot be read. The window is `churn.window_days` days ending on the commit's date. Diffusion is how many included files changed and how many parent directories they sit in. Relative churn is changed lines divided by the file's line count, shown to 4 decimal places, or `n/a` when the file has no lines or cannot be read. A changed function's hotspot is the commit count times its cyclomatic complexity. The section does not change the exit code. When the count cannot be read, the heading stays and the numbers do not.
21. `## How to reproduce`. The command, in a fence, including the `--lang` that produced the file.

Empty debt and mutation sections are omitted. Focus, the top 5, clones, the verdict, and churn are present even when empty. A truly empty churn says there is no included file. Unavailable churn does not show a zero.

The spec describes an order that starts with the header and the verdict, and places waivers next to the mutants. The code places `## Waivers` before the header when the section exists. This page documents the code.

## The pull request comment

The Action creates or updates one comment with the Markdown on a pull request. The body limit is `GITHUB_BODY_LIMIT = 65536` in `.github/actions/bob/upsert_comment.py`. Above that, the comment is truncated and the note uses the resolved output language. See [CI](ci.md).

## When there is no report file

- `bob doctor` prints on stdout. It does not write `.bob/report.md`.
- `bob waive` only edits `.bob/waivers.yaml`.
- Invalid configuration rejected in `cli.main` before `run_check` writes no report. Invalid command-line usage writes no report. A missing `--config` file on `check`, `crap`, `dry`, `deps`, or `mutate` writes no report. See [Exit 4](../exit-codes.md#exit-4).
- A missing tool during measurement does write the report, with the broken gate at `not_run`.
