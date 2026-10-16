# Exit codes

[Index](README.md) · [CLI](reference/cli.md) · [Gates and waivers](guides/gates-and-waivers.md) · [Reports](guides/reports.md) · [SPEC](SPEC.md)

The codes are in `src/bob_quality/exit_codes.py`. The spec takes them from mutator. `bob check` keeps the highest code among the gates (`_worse` in `src/bob_quality/check.py`).

| Code | Name in code | When it exits |
|---|---|---|
| `0` | `PASSED` | Every gate that ran passed, or only warned |
| `1` | `GATE_FAILED` | A blocking finding in the diff: CRAP at or above the limit, a dependency violation, DRY fail mode over the ceiling, or, when that gate was requested, diff coverage under the floor, a blocking supply finding, a blocking security finding, a new type diagnostic or escape, or a new secret |
| `2` | `BASELINE_BROKEN` | The suite breaks before measurement |
| `3` | `UNWAIVED_SURVIVOR` | A `survived` mutant with no waiver on a changed line, or `no_coverage` on a changed function |
| `4` | `CONFIG_OR_TOOL` | Invalid configuration, invalid command-line usage, or a tool that blocks the requested measurement |

## Exit 0

Every requested gate that actually ran passed. A warning also ends at `0`: a new clone in warn mode or at the ceiling in fail mode, TypeScript skipped in a mixed repository when what was measured is within the limit, a security finding on the diff outside `security.fail_severities`, and a dead symbol in the diff. The same `0` applies when the `security` gate measured one language and the other was left out: the pass becomes `warn`. The gate verdict shows ⚠️. The exit stays `0`. `no_coverage` on a changed function is not a warning. It exits `3`.

An unknown gate name is `not_run` and contributes `0`.

`bob waive` with a valid reason and a target of a survivor from the last mutation report exits `0` and only writes `.bob/waivers.yaml`.

`bob doctor` exits `0` when every pin matches the found version.

`bob report` exits with the integer stored in the saved JSON, which can be `0`.

## Exit 1

`crap_verdict` returns `1` when a considered function has CRAP greater than or equal to `crap.max_per_function` (or `--threshold`). The reason lists names as `function@file:line`.

`deps_verdict` returns `1` when a violation is marked in the diff. The reason lists `origin → destination`.

DRY returns `1` only in fail mode (`duplication.new_clones: fail` or `--dry-fail`), when the counted new clones exceed `duplication.max_new_clones` or `--max-new-clones`. The reason names the key and the ceiling, as in `1 new clone exceeds duplication.max_new_clones 0`. In warn mode, the default, DRY does not return `1`.

When the gate was requested:

- `coverage` returns `1` when a measured language is below `coverage.min_percent`. A percent equal to the floor passes.
- `supply` returns `1` when a new package 404s, an import is undeclared, or an advisory severity is in `supply.osv_fail_severities`.
- `security` returns `1` when a finding in the diff has a severity in `security.fail_severities` and has no waiver. A finding off the diff, a waived finding, and a severity outside the list do not return `1`. If the other language did not measure, the failure stays `1`.
- `typing` returns `1` for a new diagnostic or a new escape on a diff line with no waiver.
- `secrets` returns `1` for a new secret on a diff line with no waiver.

Mutation does not return `1`. An unwaived survivor is `3`. `cognitive`, `test_smells`, and `dead_code` do not return `1`.

If CRAP fails (`1`) and mutation also fails (`3`), `check` exits `3`.

## Exit 2

The `crap` gate runs pytest (Python) or vitest (TypeScript) to measure coverage. In Python, a pytest code other than `0` and `5` is a broken baseline (`pytest_passed` in `exit_codes.py`). The comment in that module says `5` is "no tests collected" and also passes. In TypeScript, `vitest_code != 0` is exit `2`. A missing `coverage-final.json` after vitest exits `0` is exit `4`.

The `mutate` gate also requires the baseline. If `crap` ran earlier in the same run, the pytest code is reused. On its own, `bob mutate` calls the pytest exit. On failure the status is `not_run` and the exit is `2`.

The `coverage` gate exits `2` when the suite breaks before the coverage artifact exists.

[AGENTS.md](../AGENTS.md) records that exit `2` also comes from the default `bob check`, because the default includes `crap`.

## Exit 3

Only the `mutate` gate. The blocking list is mutants with status `survived`, an empty waiver, and a line on the new side of the diff. With no file, or with a line at or below zero, that survivor also blocks. One or more: exit `3` and status `failed`. The reason lists only those, as `function@file:line`. An unwaived survivor outside the diff stays in the table and does not change the exit.

A waiver matched by `file::function` or `file::function::<description>` removes the survivor from that list. The mutant id and a bare function name do not match. An id that matches nothing leaves the survivor on the list. In TypeScript, a line inserted above the mutant changes the description, and the old waiver stops matching. See [ADR 0006](adr/0006-chave-estavel-do-waiver.md). `killed` and `timeout` are not on the list. `no_coverage` on a changed function also exits `3`, and a waiver does not remove it. If a blocking survivor already exists, the exit reason stays the survivor's, and the `no_coverage` count goes in the report.

## Exit 4

There are two ways to reach `4`.

### Before measurement, nothing is written

`cli.main` returns `4` without writing `report.md` or `report.json`, and without changing `waivers.yaml`, in two different cases.

Invalid command-line usage (missing command, unknown command, illegal flag, a value outside the choices, a value outside the rule for `--threshold` or `--max-workers`) prints argparse usage on stderr. That text does not mention baseline. Help (`-h`, `--help`) exits `0`. This is not exit `2`. The rule for `--threshold` and `--max-workers` is in [Other measurement commands](reference/cli.md#other-measurement-commands). A negative `--max-new-clones` on `bob dry` or `bob check` also exits `4`, with `--max-new-clones must be at least 0` in English on stderr.

`--config` before the command is invalid usage. The last stderr line stays English even with `--lang pt-BR`, as in `bob: error: --config goes after the command: bob check --config ci.yaml`. `doctor` does not accept the flag. The last line is `bob: error: doctor does not accept --config`. `waive` does not accept it. The last line is `bob: error: waive does not accept --config`. `report` does not accept it either.

Invalid configuration prints English on stderr when:

- `--lang` or `BOB_LANG` is empty or is not `en` or `pt-BR`;
- `language` in the YAML is not a string or is not one of those two values;
- `bob.yaml` has a syntax error, repeats a key in the same mapping, or is not a mapping. A repeated key names the key and the line, as in `invalid YAML in bob.yaml: found duplicate key 'base' on line 2`;
- a key has the wrong type, including `base`, `languages`, `paths`, `include`, `exclude`, `crap`, `cognitive`, `duplication`, `coverage`, `dependencies`, `security`, and `dead_code`;
- `security.fail_severities` has a word outside the vocabulary, a repeated item, or an empty list;
- `.bob/waivers.yaml` exists and the YAML is invalid, repeats a key, or the shape is not the one in [Configuration](guides/configuration.md#bobwaiversyaml). The message names the path and the field. A repeated key names the key and the line, as in `invalid YAML in .bob/waivers.yaml: found duplicate key 'id' on line 3`.

A `--config` path that is not a file is in this barrier. The missing file raises `ConfigError`, and the preflight prints English on stderr (`config file not found: <path>`) and returns `4` without writing a report. The flag exists on `check`, `crap`, `dry`, `deps`, and `mutate`. `doctor` and `waive` do not accept it. A missing `bob.yaml`, with no `--config`, stays on the defaults.

An invalid `duplication` is in the same barrier as the other keys. English stderr, no report. The refusal covers a value that is not a mapping, a `min_tokens` that is not an integer greater than 0, and `new_clones`, `max_new_clones`, `min_similarity`, or `min_lines` with the wrong type or value. An unknown key, including `mutation`, `duplication.tool`, and `dependencies.violation`, takes the same path.

A `paths.include` entry that is not on disk is in the same barrier. English stderr names the file and each missing entry, as in `bob.yaml: paths.include does not exist: missing-root`. Nothing is written. An omitted or empty `paths.include` stays `src` and is not checked. `run_check` called directly, without the CLI, writes the early report with that reason and the same exit `4`.

A missing `--reason` on `bob waive` is also `4`, and that sentence follows the CLI language, because it happens inside the waive command after the file barrier. A target that no survivor in `.bob/mutation-cache.json` or `.bob/stryker-mutants.json` has also exits `4`, in the CLI language, and `waivers.yaml` does not change.

### During measurement, with a report

If the tool is missing in the middle of a gate that can exit `1` or `3` (lizard, mutmut, import-linter, dependency-cruiser, Node in a TypeScript-only repository, Bandit or Semgrep when no language of the `security` gate measured, git failing to compute the diff), the gate is `not_run` and the exit is `4`. The report is written. `write_report` writes `.bob/report.md` and `report.json` with that code. `GitError` in the open step uses the same early report.

`bob doctor` with a missing pin or a different version exits `4` on the doctor's own stdout, with no report under `.bob/`.

A warning-only gate (`cognitive`, `test_smells`, `dead_code`) treats a missing or broken tool as `not_run` and contributes `0`. jscpd does the same: DRY without Node is `not_run` with `0`, in fail mode too.

In a repository with Python and TypeScript, a missing Node does not use this code for CRAP or for deps. Python continues, TypeScript is attached as a warning, and the exit is whatever was measured (`0` or `1`). See [Python and TypeScript together](guides/gates-and-waivers.md#python-and-typescript-together).

The README summary that says exit `4` writes nothing describes the preflight path. It does not describe this measurement path. This page documents both.
