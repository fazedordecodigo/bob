# CLI

[Index](../README.md) · [Installation](../getting-started/installation.md) · [Configuration schema](configuration.md) · [Gates and waivers](../guides/gates-and-waivers.md) · [Exit codes](../exit-codes.md) · [Reports](../guides/reports.md)

The command is `bob`. The parser is `build_parser` in `src/bob_quality/cli.py`. Help text and messages use the resolved output language. The strings live in `src/bob_quality/messages.py`.

```bash
bob check --base origin/main
bob crap --base origin/main
bob dry --base origin/main
bob deps --base origin/main
bob mutate --base origin/main
bob report
bob waive <file::function|Target> --reason "one line of text"
bob doctor
```

Every command accepts `--lang en|pt-BR` before or after the command name. See [Output language](#output-language).

Invalid command-line usage exits `4`. Stderr is argparse usage text, it does not mention baseline, and nothing is written under `.bob/`. Help (`-h`, `--help`) exits `0`. That `4` is not the baseline exit `2`. A value outside the rule for `--threshold` or `--max-workers` is also invalid usage. The last stderr line stays English even with `--lang pt-BR`, as in `bob crap: error: argument --threshold: invalid value: 'nan' (use a finite number greater than 0)`.

`--config` before the command name exits `4` and writes nothing. The last stderr line stays English. It shows the command with the flag after the name, as in `bob: error: --config goes after the command: bob check --config ci.yaml`. A path with a space is quoted, as in `bob crap --config 'my ci.yaml'`. `doctor`, `waive`, and `report` do not accept `--config`. The last line is `bob: error: doctor does not accept --config`, and the same shape for `waive` and `report`. `bob --help` does not list `--config`.

## bob check

Runs the requested gates and writes `.bob/` (or `--out`).

| Flag | Default | Effect |
|---|---|---|
| `--base` | `base` from `bob.yaml`, or `origin/main` | Ref of `git diff <base>...HEAD` |
| `--config` | `bob.yaml` in the working directory, if it exists | Another configuration file |
| `--out` | `.bob/` | Report directory |
| `--gates` | `crap,dry,deps` | Comma-separated list. The constant is `DEFAULT_GATES` in `src/bob_quality/check.py` |
| `--format` | `both` | `md`, `json`, or `both` |
| `--dry-fail` | off | Turns on DRY fail mode for this run, the same as `duplication.new_clones: fail` |
| `--max-new-clones` | `duplication.max_new_clones` | Ceiling of new clones in fail mode for this run. `0` is a real ceiling. A negative value exits `4` |
| `--lang` | see [Output language](#output-language) | `en` or `pt-BR` |

A `--config` path that is not a file exits `4`. English stderr names the path, as in `config file not found: <path>`. Nothing is written. The same applies to `crap`, `dry`, `deps`, and `mutate`. See [Exit 4](../exit-codes.md#exit-4).

A gate name the code does not handle becomes `not_run`, with the reason `gate not implemented in this slice` in English (`check.gate_not_implemented` in `messages.py`), and that gate contributes exit `0`. The implemented names are `crap`, `dry`, `deps`, `mutate`, `coverage`, `test_smells`, `cognitive`, `supply`, `security`, `typing`, `secrets`, and `dead_code`. The last eight run only through `--gates` on `bob check`.

`bob check` without `mutate` in the list does not run mutation. `bob check --gates mutate` and `bob mutate` do.

When more than one gate returns a code, the highest wins (`_worse` in `check.py`).

## Other measurement commands

`crap`, `dry`, `deps`, and `mutate` call the same `run_check`, each with one gate, and write both formats. They accept `--base`, `--config`, `--out`, and `--lang`.

| Command | Extra flags |
|---|---|
| `bob crap` | `--threshold` replaces `crap.max_per_function` for this run. It has to be a finite number greater than `0`. `--coverage-file` points at a coverage file that already exists |
| `bob dry` | `--dry-fail` and `--max-new-clones`, the same flags as `bob check` |
| `bob deps` | none beyond the shared flags |
| `bob mutate` | `--max-workers` becomes mutmut's `--max-children` (`src/bob_quality/mutmut_tool.py`). `--since-last-run` does not change the measurement: the help text says reusing the cache is already the default. The flag is added to the report's reproduce line only when it was passed |

`--max-workers` accepts an integer from 1 to 64. The ceiling is `_WORKER_CEILING` in `src/bob_quality/cli.py`. A value outside that range exits `4`. The last stderr line is `bob mutate: error: argument --max-workers: invalid value: '65' (use an integer from 1 to 64)` when the value is `65`.

## What each surface runs

| Surface | Gates | Where |
|---|---|---|
| `bob check` without `--gates` | `crap,dry,deps` | `DEFAULT_GATES` |
| Hook `pre-push` | `crap,dry,deps` | `src/bob_quality/hooks/pre-push` |
| GitHub Action, `gates` input omitted | `crap,dry,deps,mutate` | `.github/actions/bob/action.yml` |

The spec says the local hook runs `crap,dry,deps` and that in CI the check runs every gate. The hook script passes `crap,dry,deps`. The CLI default is the same three. CI asks for `mutate` through the Action input, not because the CLI default changed. The skill `skills/bob-check/SKILL.md` names those two commands. See [SPEC](../architecture/spec.md).

## bob doctor

Lists each pin in `src/bob_quality/doctor.py` with the expected version and the found version. It exits `0` when every pin is satisfied and `4` when one is missing or outside the pin, and it prints the install command. It does not write `.bob/report.md`. A `-rc` suffix on the found version is outside the pin, and doctor exits `4`.

Pins, in code order: lizard 1.24.1, deptry 0.25.1, coverage.py 7.16.2, node `>=22.18.0 <23`, c8 12.0.0, vitest 5.0.3, jscpd 5.4.1, eslint 9.39.5, eslint-plugin-sonarjs 2.0.4, mutmut 3.8.0, complexipy 8.0.1, import-linter 2.15, grimp 3.17, diff-cover 10.6.0, bandit 1.9.4, dependency-cruiser 18.5.0, gitleaks 8.30.1, vulture 2.16, knip 6.41.0, stryker 10.0.0, stryker-vitest-runner 10.0.0. The expected version of a Python tool comes from the installed `Requires-Dist` of `bob-quality`. Semgrep 1.180.0 is not in that list. The security gate calls `uvx --from semgrep==1.180.0`.

`bob doctor --install` runs `npm ci` in the installed package and then prints the same report. See [Installation](../getting-started/installation.md).

`doctor` also passes through the configuration preflight. An invalid `bob.yaml` or `.bob/waivers.yaml` in the working directory makes doctor exit `4` before the version report. See [Exit 4](../exit-codes.md#exit-4).

## bob waive

```bash
bob waive <file::function|Target> --reason "one line"
```

Writes or replaces one row in `.bob/waivers.yaml` and exits `0`. It does not write `report.md`. The fields are in [Configuration](../guides/configuration.md#bobwaiversyaml).

The target is `file::function`, which waives every survivor of the function, or the Target column of the last mutation report, which waives one survivor. The command reads survivors from `.bob/mutation-cache.json` and `.bob/stryker-mutants.json`. Run mutation first.

`--reason` is required in practice. A missing reason, an empty string, or a newline raises `WaiverError` and the process exits `4`. That message follows the resolved language. An empty target exits `4`. A target no survivor has, such as the mutant id or a bare function name, exits `4` and writes nothing.

A `.bob/waivers.yaml` that is already invalid is rejected first, in English on stderr, also with `4`, and the file is not rewritten.

## bob report

`build_parser` registers `report` next to `check`, `crap`, `dry`, `deps`, `mutate`, `waive`, and `doctor`. The interface matches the spec:

```text
bob report  [--in .bob/] [--out .bob/report.md]
```

`--in` is the directory that already contains `report.json`. The default is `.bob/`. `--out` is the Markdown file. The default is `.bob/report.md`. The command does not measure again. It reads the JSON and writes the Markdown in the output language chosen by `--lang`, by `BOB_LANG`, or by `language` in `bob.yaml`. The process exits with the `exit_code` stored in that JSON. The integer has to be 0, 1, 2, 3, or 4 (`_SAVED_EXIT_CODES` in `src/bob_quality/report.py`).

If the file is missing, the text is not JSON, or the shape is invalid, the command exits `4`. Stderr stays English. The command does not write `--out` and does not truncate a file that was already there. Invalid command-line usage also exits `4` and writes no report. The `bob.yaml` and `.bob/waivers.yaml` preflight is the same as the other commands.

`report.json` stays English. `--lang pt-BR` translates the headings the catalog knows. A gate reason, or a rule name, stays English when the JSON already stored it that way. To write both files during measurement, use `bob check --format md` or `--format both`.

## Output language

The first source that is set wins:

1. `--lang en` or `--lang pt-BR`, before or after the command.
2. The `BOB_LANG` environment variable.
3. `language` in `bob.yaml`, or in the `--config` file.
4. `en`.

The case matters. `pt-br` is invalid. An empty `--lang` or `BOB_LANG` exits `4`, prints `invalid language: "" (use en or pt-BR)` on stderr, and writes no report. An empty `language` key stays unset.

An invalid language, a `language` that is not a string, YAML that is not a mapping, a YAML syntax error, and a key with the wrong type also exit `4` in English on stderr, even when the intent was `pt-BR`, and they write no report. The same applies to `paths`, `languages`, `base`, `dependencies`, and the `include` and `exclude` lists, on `check`, `doctor`, `waive`, and the other commands. A `paths.include` entry that is not on disk follows the same path. Stderr names the file and each missing entry, as in `bob.yaml: paths.include does not exist: missing-root`. An omitted or empty `paths.include` stays `src` and is not checked.

An invalid `duplication` also exits `4`, in English on stderr, with no report. An unknown key follows the same path. See [Exit 4](../exit-codes.md#exit-4) and the [configuration schema](configuration.md).

What follows the output language: CLI messages, `--help` text, `bob doctor`, the hook (because it calls the CLI), `.bob/report.md`, the Action comment's truncation note, and that comment's own errors. `.bob/report.json` is the same file in both languages (`JSON_LANGUAGE = "en"` in `report.py`).
