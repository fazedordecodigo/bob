# report.json

[Index](../README.md) · [Reports](../guides/reports.md) · [Exit codes](../exit-codes.md)

`.bob/report.json` follows `src/bob_quality/schemas/report_v1.json`. `schema_version` is the constant `1`. The file is English in both output languages (`JSON_LANGUAGE = "en"` in `src/bob_quality/report.py`).

## Required fields

The schema requires `schema_version`, `commit`, `base`, `generated_at`, `tool_versions`, `gates`, `focus`, `top_crap`, `reproduce`, and `exit_code`.

`gates[]` requires `name` and `status`. `status` is `passed`, `warn`, `failed`, or `not_run`. `reason` is a string or null, and it is rendered in English.

`reproduce` in the JSON omits `--lang`. The reproduce line in `report.md` includes the `--lang` that produced it.

## Fields the renderer writes

The renderer also writes `old_debt`, `dependencies`, `old_dependencies`, `clones`, `waivers`, `survivors`, and `mutation`. Those are not all in `required`.

`survivors[].target` is the exact waiver target, or `null` when that form does not exist. `survivors[].blocking` is a boolean. The mutation cache does not store `blocking`.

`mutation.no_coverage` has `total` and `functions`. Each function row has `file`, `function`, and `count`.

Optional fields, omitted when that gate did not produce them:

| Field | When it is present | Shape |
|---|---|---|
| `test_smells` | the gate ran | list of `file`, `line`, `rule`, `waiver` |
| `supply` | the gate measured | `measured`, `skipped`, `findings` |
| `diff_coverage` | at least one language measured | per-language percents and `uncovered` rows of `file` and `line` |
| `typing` | the gate was requested | `absent`, `checkers`, `findings` |
| `secrets` | the gate measured | blocking findings, each with `file`, `line`, and `rule_id` |
| `cognitive` | the gate was requested | `file`, `name`, `start_line`, `end_line`, `score`, `language`, `waiver_id` |
| `dead_code` | the gate was requested | `symbols`, each with `file`, `line`, `name`, `kind`, `language`, `confidence`, `waiver`. `kind` stays English |
| `security` | the gate was requested | `findings` and `unmeasured`. A finding has `tool`, `rule`, `file`, `line`, `end_line`, `severity`, `disposition`, and `waiver`. Disposition is `fail`, `warn`, `waived`, or `off_diff` |
| `churn` | always | measured, or `{"kind": "unavailable"}` when the count cannot be read |

`churn` is optional in the schema and is always written. A measured object has `kind`, `window_days`, `ends_on`, `files`, `hotspots`, and `diffusion`. Each file has `path`, `commits`, and `relative`. `relative` is the rate, or `null`.

After `mutation`, the render order is `test_smells` when that gate ran, `supply` when it measured, `diff_coverage` when at least one language measured, `typing` when it was requested, `secrets` when it measured, `cognitive` when it was requested, `dead_code` when it was requested, and `security` when it was requested. `churn` comes next, before `reproduce` and `exit_code`. A check that did not run a gate omits that key. `schema_version` stays `1`.

## What does not change with the output language

The JSON bytes are the same in `en` and `pt-BR`:

- every gate `reason`;
- the cycle rule name (`Forbidden dependency cycle`);
- `reproduce`, which does not include `--lang`.

`report.md` and the pull request comment translate the cycle rule and the unnamed dependency-cruiser fallback, and the reproduce line includes `--lang`.

## bob report

`bob report --in <dir> --out <file>` reads `<dir>/report.json` and writes Markdown. It exits with the stored `exit_code`. The integer has to be `0`, `1`, `2`, `3`, or `4`. A missing file, text that is not JSON, or an invalid shape exits `4`, prints English on stderr, and does not write the output file. See [CLI](cli.md#bob-report).
