# Configuration schema

[Index](../README.md) · [Configuration](../guides/configuration.md) · [CLI](cli.md) · [Exit codes](../exit-codes.md)

`load_config` in `src/bob_quality/config.py` reads `bob.yaml`, or the file `--config` names. The object is `Config`. Keys below are the ones `_SCHEMA` accepts. Any other key exits `4` with English stderr (`file.unknown_key`) and writes nothing.

## Defaults

These values apply when the key is omitted. `language: en` in prose is the result of resolution, not a key an empty file has to contain. Without the key, `resolve_language` returns `en`.

| Key | Type | Default | Use |
|---|---|---|---|
| `base` | string | `origin/main` | Diff ref when `--base` is omitted. Empty counts as unset. |
| `language` | `en` or `pt-BR`, or empty | unset, so `en` | Output language. Empty counts as unset. |
| `languages` | list of `python` and `typescript` | `[python]`, or detected | Which languages the gates measure. |
| `paths.include` | list of strings | `[src]` | Roots that are measured. |
| `paths.exclude` | list of strings | `[tests, node_modules, dist]` | Left out of measurement. |
| `crap.max_per_function` | finite number greater than 0 | `10` | A function at or above this CRAP fails. A bool is not a number. |
| `crap.scope` | `changed` or `all` | `changed` | `changed` considers changed functions. `all` considers every measured function. Any other string exits `4`. |
| `cognitive.max_per_function` | integer greater than 0 | `15` | A changed function at or above this score warns. The exit stays `0`. `null` is rejected. |
| `duplication.min_tokens` | integer greater than 0 | `50` | jscpd token minimum. `null` is rejected. |
| `duplication.new_clones` | `warn` or `fail` | `warn` | DRY mode. Empty counts as unset. |
| `duplication.max_new_clones` | integer ≥ 0 | `0` | Ceiling in fail mode. A bool is not an integer. |
| `duplication.min_similarity` | finite number from 0 to 100 | `0` | Minimum similarity, in percent, for a new clone to count. |
| `duplication.min_lines` | integer ≥ 0 | `0` | Minimum lines for a new clone to count. |
| `coverage.min_percent` | finite number from 0 to 100 | `80` | Floor for the diff-coverage gate. A percent equal to the floor passes. `null` is rejected. |
| `dependencies.python` | string | `.importlinter` | import-linter config path. |
| `dependencies.typescript` | string | `.dependency-cruiser.cjs` | dependency-cruiser config path. |
| `test_smells` | `true` only | `true` | The loader accepts `true`. The gate does not read the field. |
| `typing` | mapping with no children | unset | Accepted and ignored. It does not turn the typing gate on. |
| `secrets` | mapping with no children | unset | No threshold and no children. It does not turn the secrets gate on. |
| `churn.window_days` | integer greater than 0 | `90` | Churn window, ending on the commit's own date. |
| `supply.osv_fail_severities` | list of `HIGH` and `CRITICAL` | `[HIGH, CRITICAL]` | Advisory severities that block. `MODERATE` and `LOW` are not members of this list. |
| `supply.timeout_seconds` | integer greater than 0 | `30` | Timeout for each HTTP call and each process in the supply gate. |
| `security.fail_severities` | list of strings | `[HIGH, CRITICAL, ERROR]` | Severities that fail the security gate. |
| `dead_code.min_confidence` | integer from 0 to 100, or unset | unset | Vulture `--min-confidence`. Unset or null does not pass the flag. `0` does pass it. knip ignores the key. |

Opt-in gates are not turned on by the presence of their keys. The command is `bob check --gates <name>`. See [Gates and waivers](../guides/gates-and-waivers.md).

## Languages and paths

`languages` omitted or null is detected. The same detection runs when `bob.yaml` is missing and `--config` was not passed. The scan reads `paths.include`, skips `paths.exclude`, and does not follow symlinks. `.py` selects `python`. `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, and `.cjs` select `typescript`, in that order. If none of those files exist, the result is `[python]`. An explicit list is kept as written. An empty list, or a repeated item, exits `4`.

`paths.exclude` matches a path prefix or a path component. It is not a glob. `*.py` does not exclude `src/app.py`. `tests` excludes `tests/a.py` and `src/tests/a.py`.

Each `paths.include` entry is resolved from the current working directory. An entry that is not on disk exits `4`. English stderr names the file and each missing entry, as in `bob.yaml: paths.include does not exist: missing-root`. An omitted or empty list stays `[src]` and is not checked. A path that exists as a file, not a directory, passes this check.

## Values that exit 4

A wrong type exits `4`. English stderr names the file and the key, as in `bob.yaml: crap must be a mapping` or `bob.yaml: crap.max_per_function must be a number`. `check`, `doctor`, `waive`, `report`, and the other commands do this the same way. None of them writes a file in this case.

A repeated key in one mapping exits `4`. English stderr names the key and the line, as in `invalid YAML in bob.yaml: found duplicate key 'base' on line 2`. A key written in the mapping can still override a value merged with `<<`.

YAML that is not a mapping, and YAML with a syntax error, exit `4`. The syntax message names the file and the parser's first line.

`test_smells` omitted, `null`, or `true` stores `True`. `false`, a mapping, and any other value exit `4` with `bob.yaml: test_smells accepts only true`. The gate does not read the field.

`churn` omitted, `churn: null`, and `churn: {}` keep 90. `churn.window_days` set to `null`, a float, a bool, `0`, or a negative integer exits `4`. Any other `churn.*` key is an unknown key.

`secrets` omitted, `secrets:`, `secrets: null`, and `secrets: {}` are the same empty mapping. `secrets: true` and `secrets: {threshold: 1}` exit `4`.

`typing: {}`, `typing:`, and `typing: null` load and store no field on `Config`. A child key exits `4` with `bob.yaml: unknown key typing.threshold`. A non-mapping such as `typing: 1` exits `4` with `bob.yaml: typing must be a mapping`.

`security.fail_severities` members have to be in the scanner vocabulary: `CRITICAL`, `ERROR`, `HIGH`, `INFO`, `LOW`, `MEDIUM`, `UNDEFINED`, `WARNING` (`severity_vocabulary` in `src/bob_quality/security_scanners.py`). A word outside that list, a repeated item, an empty list, or a value that is not a list of strings exits `4`. An omitted or null list stays `HIGH`, `CRITICAL`, `ERROR`. `[]` does not return to the default. `ERROR` is not an alias of `HIGH`.

`supply.osv_fail_severities: [MODERATE]` exits with `bob.yaml: supply.osv_fail_severities[0] must be HIGH or CRITICAL`. An empty list, a repeated item, or a bare string also exits `4`. `supply.timeout_seconds: 0` exits with `bob.yaml: supply.timeout_seconds must be greater than 0`.

`dead_code.min_confidence` of `101`, `-1`, `true`, or `1.5` exits `4` on `check`, `doctor`, and `waive`. English stderr names `dead_code.min_confidence`. Nothing is written under `.bob/`.

`coverage.min_percent` below 0, above 100, non-finite, or a bool exits `4`.

## Keys the loader rejects

`_reject_unknown` refuses every key that is not in the table above. These three show up in older notes and are rejected:

- `mutation`, including `require_zero_unwaived_survivors`, `scope`, or `differential`. The error is `bob.yaml: unknown key mutation`.
- `duplication.tool`. The error is `bob.yaml: unknown key duplication.tool`.
- `dependencies.violation`. The error is `bob.yaml: unknown key dependencies.violation`.

An unwaived survivor still exits `3`, mutation still reuses `.bob/mutation-cache.json`, and a dependency violation in the diff still exits `1`. There is no key to turn those off. `tests/test_invalid_config.py` covers the refusal.

The spec's configuration sketch and the README example do not list every key in the table above. This page lists the keys the loader reads.
