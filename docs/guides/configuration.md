# Configuration

[Index](../README.md) · [Configuration schema](../reference/configuration.md) · [Gates and waivers](gates-and-waivers.md) · [Exit codes](../exit-codes.md)

Two files. `bob.yaml` at the repository root, or the path in `--config`, sets the base ref, the output language, the paths, and the limits. `.bob/waivers.yaml` holds waivers and is committed with the code.

## bob.yaml

If the file is missing and `--config` was not passed, `load_config` returns the defaults in `Config` (`src/bob_quality/config.py`) and detects languages from the tree. If `--config` points at a file that does not exist, `check`, `crap`, `dry`, `deps`, and `mutate` exit `4`. English stderr names the path (`config file not found: <path>`). Nothing is written. `doctor`, `waive`, and `report` do not accept `--config`.

A file that only sets what this repository sets (`base`, `languages`, `paths`, and `crap`) leaves every other key at the code default. The full key list, the types, and the values that exit `4` are in the [configuration schema](../reference/configuration.md).

```yaml
base: origin/main
languages: [python]
paths:
  include: [src]
  exclude: [tests, node_modules, dist]
crap:
  max_per_function: 10
  scope: changed
duplication:
  new_clones: warn
  max_new_clones: 0
```

`crap.scope` is `changed` or `all`. With `changed`, only changed functions can fail the CRAP gate. With `all`, every measured function can fail it. Any other string exits `4`. [ADR 0002](../adr/0002-o-diff-filtra-o-veredito.md) describes an earlier rule in which any other non-empty string counted every measured function. The loader on `main` accepts only `changed` and `all`.

`duplication.new_clones` is `warn` (the default) or `fail`. In `warn`, a new clone stays a warning and the exit stays `0`. In `fail`, the gate exits `1` when the counted new clones exceed `duplication.max_new_clones` (default `0`). `bob dry` and `bob check` accept `--dry-fail`, which turns on fail mode for that run, and `--max-new-clones N`, which replaces the ceiling for that run. `0` is a real ceiling. No flag forces warn mode.

## Output language

The first source that is set wins (`resolve_language` in `src/bob_quality/config.py`):

1. `--lang en` or `--lang pt-BR`, before or after the command name.
2. The `BOB_LANG` environment variable.
3. `language` in `bob.yaml`, or in the `--config` file.
4. `en`.

The case matters. `pt-br` is invalid. The accepted values are `en` and `pt-BR` (`LANGUAGES` in `src/bob_quality/messages.py`).

An empty `--lang` or `BOB_LANG` exits `4`, prints `invalid language: "" (use en or pt-BR)` on stderr, and writes nothing. An empty `language` key still counts as unset.

In CI, set `language: pt-BR` in `bob.yaml`, or `BOB_LANG: pt-BR` in the job `env`. The Action input `language` sets the same choice for `bob check` and for the pull request comment. An empty input leaves `BOB_LANG` and `bob.yaml` in charge. See [CI](ci.md).

`.bob/report.json` is the same bytes in both languages. `report.md` and the pull request comment follow the output language. See [report.json](../reference/report-json.md).

## .bob/waivers.yaml

The path is always `<cwd>/.bob/waivers.yaml`. `bob waive` creates the directory when it needs to. `write_waivers` is the only writer.

```bash
bob waive 'src/app/billing.py::charge::if total > limit: -> if total >= limit:' --reason "equivalent; the inclusive limit does not change the contract"
```

`bob waive` accepts only a target of a survivor from the last mutation run, read from `.bob/mutation-cache.json` (Python) and `.bob/stryker-mutants.json` (TypeScript). Run mutation first. The target is `file::function`, which waives every survivor of that function, or the Target column of the survivor table, which waives one survivor. The mutant id, a bare function name, and `file:function` exit `4` and write nothing.

The command writes these fields:

| Field | Source | Rule |
|---|---|---|
| `id` | The argument, stripped | Non-empty string |
| `reason` | `--reason`, one line, stripped | Empty, or a value containing `\n` or `\r`, is rejected |
| `author` | `git config user.name`, then `$USER`, then `unknown` | Non-empty string in the file |
| `date` | Today's UTC date, `YYYY-MM-DD` | Non-empty string |

A missing `--reason`, an empty reason, or a reason with a newline exits `4`. That message follows the output language. An id that already appears once is replaced and the command exits `0`. A file that already contains two rows with one id exits `4` and the bytes stay.

Hand-written ids for the other gates use the prefixes in [Gates and waivers](gates-and-waivers.md). `bob waive` itself only stores a mutation survivor target. The other ids are edited into the same file. `load_waivers` does not check that an id matches a survivor. An id that matches nothing leaves the finding unwaived.

A `waivers.yaml` that is valid YAML with the wrong shape exits `4`. English stderr names `.bob/waivers.yaml` and the field, as in `.bob/waivers.yaml: waivers[0].reason must be a string`. A YAML syntax error names the file and the parser error. A repeated key names the key and the line, as in `invalid YAML in .bob/waivers.yaml: found duplicate key 'id' on line 3`. The run writes no `report.md` and no `report.json`, and the file stays as it is. `check`, `doctor`, `waive`, and `report` share this preflight, including when `--lang` is `pt-BR`.

The agent writes the waiver. The human approves it in the pull request review. The skill `skills/harden/SKILL.md` says when to record a waiver instead of weakening production code. Every waiver appears in the report's `## Waivers` section when mutation ran or when a waiver already exists.
