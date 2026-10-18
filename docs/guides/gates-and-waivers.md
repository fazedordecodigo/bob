# Gates and waivers

[Index](../README.md) · [Configuration](configuration.md) · [Exit codes](../exit-codes.md) · [Reports](reports.md) · [SPEC](../SPEC.md)

Twelve gate names. Each returns `passed`, `warn`, `failed`, or `not_run`. In `report.md` those are passed, warning, failed, and not run, with ✅ ⚠️ ❌ ⏭️ (`GATE_MARK` in `src/bob_quality/report.py`). A gate that did not run shows the reason. It never shows as passed.

`bob check` without `--gates` runs `crap,dry,deps` (`DEFAULT_GATES` in `src/bob_quality/check.py`). The pre-push hook runs the same three. The GitHub Action's default input is `crap,dry,deps,mutate`. The other eight names run only when `--gates` lists them. There is no `bob coverage`, `bob security`, or other subcommand for them. Churn is not a gate. It is a report section on every check, and it has no verdict line.

The process exit code is the highest code among the gates. A warning contributes `0`.

| Gate | Tools | What blocks | Exit when it blocks |
|---|---|---|---|
| `crap` | lizard, plus coverage.py or c8/vitest | a function in scope with CRAP at or above the limit | `1` |
| `dry` | jscpd | in fail mode, more counted new clones than the ceiling. Warn mode blocks nothing | `1` in fail mode, `0` in warn mode |
| `cognitive` | complexipy, or eslint with eslint-plugin-sonarjs | nothing. A changed function at the limit warns | `0` |
| `mutate` | mutmut (Python), Stryker (TypeScript) | an unwaived survivor on a changed line, or `no_coverage` on a changed function | `3` |
| `deps` | import-linter, grimp, dependency-cruiser, plus the cycle rule | a violation whose origin, destination, or another module in the cycle is in the diff | `1` |
| `coverage` | diff-cover 10.6.0 on `coverage.xml` or c8 lcov | a language percent below the floor | `1` |
| `test_smells` | Python AST, and the repository's eslint when a Jest or Vitest plugin is configured | nothing. A smell on a changed test warns | `0` |
| `supply` | deptry, knip, PyPI, npm, OSV | a new package that 404s, an undeclared import, or a `HIGH`/`CRITICAL` advisory on a line the diff added | `1` |
| `security` | Bandit (Python), Semgrep (TypeScript) | a new finding whose severity is in `security.fail_severities`, with no waiver | `1` |
| `typing` | the repository's mypy, pyright, or tsc | a diagnostic or an escape on a new diff line, with no waiver | `1` |
| `secrets` | gitleaks 8.30.1 | a new secret in the diff | `1` |
| `dead_code` | vulture and knip | nothing. An unused symbol whose definition is in the diff warns | `0` |

Pinned versions, from `pyproject.toml`, `package.json`, and `PINS` in `src/bob_quality/doctor.py`: lizard 1.24.1, deptry 0.25.1, coverage 7.16.2, diff-cover 10.6.0, c8 12.0.0, vitest 5.0.5, jscpd 5.4.1, mutmut 3.8.0, complexipy 8.0.1, `@stryker-mutator/core` 10.0.0, `@stryker-mutator/vitest-runner` 10.0.0, import-linter 2.15, grimp 3.17, dependency-cruiser 18.6.0, eslint 9.39.5, eslint-plugin-sonarjs 2.0.4, bandit 1.9.4, gitleaks 8.30.1, vulture 2.16, knip 6.41.0. Node for `bob doctor` is `>=22.18.0 <23`. mypy, pyright, and tsc are the repository's executables. Doctor does not pin them. Semgrep 1.180.0 is not in `PINS`. The security gate runs `uvx --from semgrep==1.180.0`.

A waiver lives in `.bob/waivers.yaml`. The file format is in [Configuration](configuration.md). Each gate reads ids with its own prefix. Mutation matching ignores those prefixes: a secret waiver or a typing waiver does not match a mutant unless the whole id is already one of the mutant's keys.

## CRAP

CRAP combines cyclomatic complexity with the fraction of the function's executable lines the tests ran.

```text
CRAP = CC² × (1 − cov)³ + CC
```

`CC` comes from lizard, for Python and TypeScript. `cov` is a fraction from 0 to 1 (`calculate_crap` in `src/bob_quality/crap.py`). A function with no executable lines in its range counts as fully covered. A file with no coverage data counts as 0 (`line_coverage` in `src/bob_quality/core.py`).

| CC | Coverage | CRAP | At the default limit of 10 |
|---|---|---|---|
| 4 | 50% | 16 × 0.125 + 4 = 6 | passes |
| 5 | 0% | 25 + 5 = 30 | fails |
| 10 | 100% | 0 + 10 = 10 | fails |

The comparison is `crap >= max_crap`. A function at 10 fails the default limit. Because CRAP is never below CC, CC 10 with full coverage also fails that limit. Change the limit with `crap.max_per_function` or with `bob crap --threshold`.

With `crap.scope: changed` (the default), only changed functions are considered. `all` considers every measured function. Any other string exits `4` before the run. [ADR 0002](../adr/0002-o-diff-filtra-o-veredito.md) recorded a wider rule. The code does not.

The gate runs the tests to measure coverage. A broken baseline exits `2`. Pytest `0` and `5` count as a good suite (`pytest_passed` in `src/bob_quality/exit_codes.py`). The comment in that module says `5` means no tests were collected. Vitest accepts only `0`. This applies to the default `bob check`, because that command includes `crap`.

Python runs coverage.py around pytest. TypeScript runs c8 around vitest. The spec still mentions branch coverage and lcov in the adapter list that feeds the core. The CRAP fraction is statement lines in the function range. The `coverage` gate is the one that reads diff-cover. See [SPEC](../architecture/spec.md).

## DRY

A clone is a block that repeats another block. The gate runs jscpd with `duplication.min_tokens` (default 50) and keeps clones where at least one side touches a changed line.

Two filters then choose which new clones count, in both modes. A clone counts when it has at least `duplication.min_lines` lines (default 0) and at least `duplication.min_similarity` percent similarity (default 0). A clone without a percentage counts as 100. jscpd already drops clones under 5 lines, its own default, so a `min_lines` below 5 does not bring them back. A clone that does not count stays out of the report.

In `warn` mode, the default, one or more counted clones leave the gate at `warn` and the exit at `0`. In `fail` mode the gate is `failed` and the exit is `1` when the count is above `duplication.max_new_clones` (default 0). The reason names the key and the ceiling, as in `1 new clone exceeds duplication.max_new_clones 0`. At or under the ceiling, fail mode stays `warn`. With no counted clones, the status is `passed`.

Fail mode comes from `duplication.new_clones: fail` or from `--dry-fail`. `--max-new-clones N` replaces the ceiling for that run. A negative `--max-new-clones` exits `4` before any report, with `--max-new-clones must be at least 0` on stderr.

Without Node, or without jscpd, the status is `not_run` and the exit stays `0`, in fail mode too. jscpd needs Node in a Python-only repository as well, when `dry` is in the list.

## Cognitive complexity

`bob check --gates cognitive`. A changed function with a score greater than or equal to `cognitive.max_per_function` (default 15) leaves the gate at `warn`. The exit stays `0` on a warning, on a pass, and when the tool is missing.

The waiver id is `cognitive:<file>:<name>`. complexipy names a Python method `Class::method`. TypeScript uses the same `::`. A function with no name is `anonymous@<line>`. The waiver `save` does not cover `Foo::save`.

Python measures with complexipy 8.0.1. TypeScript measures with ESLint 9.39.5 and eslint-plugin-sonarjs 2.0.4, rule `sonarjs/cognitive-complexity`. The number passed to the rule is `limit - 1`, because the rule reports only above its threshold. bob keeps the function when the score it reads is still `>= limit`. If every configured language fails, the status is `not_run` and the exit is `0`.

## Mutation

Coverage shows that a line ran. It does not show that a test checked the result. Mutation testing changes the code and runs the tests again. If a test fails, the mutant is `killed`. If the suite passes, it `survived`. The other statuses in the model are `timeout` and `no_coverage`. `no_coverage` means no test ran the mutant. The mutmut 3.8 adapter maps "no tests", "skipped", "not checked", and "check was interrupted by user" to `no_coverage`.

There is no separate status for an equivalent mutant. Record a waiver, as `skills/harden/SKILL.md` describes.

bob mutates Python with mutmut and TypeScript with Stryker. mutmut runs in `<--out>/mutmut/`, a directory of symlinks to the repository's top-level entries, and never writes the repository's `setup.cfg` or `mutants/`. Stryker's incremental file is `.bob/stryker-incremental.json` (or `<--out>/stryker-incremental.json`). The last Stryker mutants are written to `<--out>/stryker-mutants.json` for `bob waive`. [ADR 0001](../adr/0001-adaptadores-sobre-ferramentas-de-mercado.md) recorded a tree that had no Stryker adapter. The code on `main` has `src/bob_quality/adapters/stryker.py` and the pins above.

The baseline runs first. If `crap` already measured pytest in the same run, that code is reused. A broken baseline leaves the gate `not_run` and exits `2`.

The run mutates changed functions and cached functions that still have an unwaived survivor. The cache is `.bob/mutation-cache.json`. Each function stores a sha256 of its text, the mutmut version, and the suite fingerprint. If the mutmut version or the suite fingerprint differs from the file's key, the cache is not reused. `--since-last-run` does not change this. Reuse is already the default. The flag only appears on the report's reproduce line when it was passed.

A survivor blocks when it is `survived`, has no waiver, and its line is on the new side of the diff. A survivor with no file, or with a line at or below zero, also blocks. Either case exits `3`. An unwaived survivor on a line the diff did not change stays in the table, marked outside the diff, and does not change the exit. `killed` and `timeout` do not block. A waiver does not cover `no_coverage`. `no_coverage` on a changed function also exits `3`.

The waiver id is `file::function` for every survivor of that function, or `file::function::<description>` for one survivor. The description is the mutant's operator with the outer spaces stripped. For Python it is the `mutmut show` diff. For TypeScript it is `{mutatorName}@{line}:{column}-{line}:{column}`, plus ` -> {replacement}` when Stryker reports one. The exact form exists only when no other survivor of the function has the same description. See [ADR 0006](../adr/0006-chave-estavel-do-waiver.md).

## Dependencies

The gate runs the rules the repository already declares and adds one rule that is always on and forbids cycles.

- Python, when `python` is in `languages`: import-linter with `dependencies.python` (default `.importlinter`), plus cycles from the grimp graph.
- TypeScript, when `typescript` is in `languages`: dependency-cruiser with `dependencies.typescript` (default `.dependency-cruiser.cjs`).

The cycle rule name in JSON is `Forbidden dependency cycle`. In `pt-BR` `report.md` it is `Proibido ciclo de dependência`. A dependency-cruiser rule with no name is `dependency` in JSON and `dependência` in the Markdown.

A violation blocks when its origin, its destination, or another module in the same strongly connected component is in the diff. The others appear as information and do not change the exit code. Zero violations in the diff is `passed` and exit `0`. One in the diff is `failed` and exit `1`.

A missing tool that blocks the requested measurement leaves the gate `not_run` and exits `4`. The same `4` applies when dependency-cruiser JSON is not an object or has no `violations` list, and when import-linter exits 0 but its last `Contracts:` line is not `N kept, 0 broken.`

## Diff coverage

`bob check --gates coverage`. The floor is `coverage.min_percent`, default 80. A percent below the floor fails. A percent equal to the floor passes. That cut is the opposite of CRAP, which fails when the number equals the limit.

Each language in `languages` has its own percent. A language with no coverable new line counts as 100 and passes. Python reads coverage XML. TypeScript reads c8 lcov. Each language calls diff-cover 10.6.0 in its own process.

The line waiver is `coverage:<file>:<line>`. It removes the line from the numerator and the denominator. The file waiver is `coverage:<file>` and removes the whole file. The gate reads only ids with the prefix `coverage:`.

A suite that breaks before the artifact exists exits `2`. The JSON then has no `diff_coverage`. A good suite with a missing artifact, and no other language measured, exits `4`. A missing diff-cover exits `4` before this gate asks for the suite. A `crap` gate in the same list still measures.

If one language measures and the other has no tool, the verdict is the measured percent. The reason names the language that was left out.

## Test smells

`bob check --gates test_smells`. The exit contribution is always `0`. The status is `passed`, `warn`, or `not_run`.

The gate ignores `paths.include` and `paths.exclude`. A file under `tests/` is eligible even when `tests` is in the exclude list.

Python runs when `python` is in `languages`. The file name is `test_*.py` or `*_test.py`. `conftest.py` and `__init__.py` are left out. A test is a `test_*` function in the module body, or a `test_*` method on a module-level class whose name starts with `Test`.

| Rule | When it appears |
|---|---|
| `empty-test` | The body is only a docstring, `pass`, and `...` |
| `missing-assert` | The body has no assertion. An empty body is only `empty-test` |
| `disabled-test` | A changed line disables the test with `skip`, `skipif`, `skipIf`, `skipUnless`, `xfail`, or `importorskip`. A skip the diff did not touch does not count. A disabled test does not also emit `empty-test` or `missing-assert` |
| `sleep` | A call named `sleep` on a changed line inside the test. `time.sleep`, `asyncio.sleep`, and `trio.sleep` count. `sleeping` does not. A function outside the test does not |

A file that does not parse produces no row. Python stays measured.

TypeScript runs when `typescript` is in `languages`. The name ends in `.test.ts`, `.test.tsx`, `.test.js`, `.test.jsx`, `.test.mjs`, `.test.cjs`, or the same with `.spec` instead of `.test`. A file under `__tests__` also counts for those suffixes. `*.d.ts` is left out.

The gate looks for `eslint-plugin-jest`, `eslint-plugin-vitest`, `plugin:jest/`, or `plugin:vitest/` in the configuration text. The search skips `node_modules`, `dist`, `.git`, and `.bob`. In `package.json` only the `eslintConfig` value counts. Without a marker, TypeScript is skipped and eslint does not start. The binary is `node_modules/.bin/eslint`, with `--format json` and the changed paths. Exit `0` or `1` with a JSON list is a measurement. Any other exit, or output that is not that list, leaves TypeScript unmeasured. If no language measured, the status is `not_run` and the process exit stays `0`. A broken TypeScript half does not change the status of what was already measured. `bob doctor` does not pin that eslint.

The waiver id is `tests:<file>:<line>:<rule>`. A waived row keeps the line in the table and copies the reason. The status is passed when no unwaived row remains.

`test_smells: false` exits `4` before the gate, with `bob.yaml: test_smells accepts only true`, and writes no report. Omitting the key, `null`, and `true` are the same. The gate does not read the field.

## New dependencies

`bob check --gates supply`. It looks at what the diff adds.

A direct name counts when the manifest at `HEAD` declares it, the same manifest at the base does not, and the declaration's line is on the new side. A version bump of a name the base already has does not count. Undeclared imports are looked up under `paths.include`. The direct pin stays in the root manifest (`pyproject.toml`, `requirements*.txt`, `package.json`), even when that root is outside `paths.include`. A lockfile does not add a name.

Python uses deptry 0.25.1. `DEP001` and `DEP003` are undeclared imports. `DEP002`, `DEP004`, and `DEP005` are left out. TypeScript uses knip 6.41.0, findings `unlisted` and `unresolved`. A specifier that starts with `.` or `/` does not count.

The advisory id comes from `POST https://api.osv.dev/v1/querybatch`. The severity comes from `GET https://api.osv.dev/v1/vulns/{id}`, with the same `supply.timeout_seconds`. A failure of that GET, or a document with no published severity, warns and stays unverified. osv-scanner is not executed.

- A 404 from PyPI or npm blocks.
- An undeclared import blocks, including when the network is down.
- An advisory whose severity is in `supply.osv_fail_severities` blocks. The default is `HIGH` and `CRITICAL`. `MODERATE` and `LOW` warn.
- Timeout, DNS failure, or a response that does not decide warns and stays unverified. That warning is not exit `4`.

Waiver ids are `supply:missing:<index>:<name>`, `supply:undeclared:<file>:<module>`, and `supply:osv:<advisory>`. The index is `pypi` or `npm`. The id has to be equal. An unverified finding has no waiver.

Any blocking row leaves the gate `failed` and the exit `1`. With no blocking row, a warning is `warn` and exit `0`. If one configured language measures and the other does not, the verdict is the one that measured. Exit `4`, with a report, happens only when no configured language measured.

## Security

`bob check --gates security`. It is not in the default check, the hook, or the Action default.

Python runs Bandit (`python -m bandit`). TypeScript runs Semgrep 1.180.0 with `uvx --from semgrep==1.180.0 semgrep scan`. The bob package does not install Semgrep. Without `uvx` on `PATH`, that language is unmeasured and the reason is `semgrep runner missing: uvx`. A language that is not in `languages` does not run and does not count as a missing tool.

A finding fails when its line range overlaps the diff, the severity is in `security.fail_severities`, and no waiver matches. The default list is `HIGH`, `CRITICAL`, and `ERROR`. `ERROR` is the word older Semgrep rules emit. It is not rewritten to `HIGH`. Anything else on the diff is `warn` and the exit stays `0`. A finding off the diff is `off_diff` and does not change the exit. Bandit confidence does not filter.

The waiver id `sast:<tool>:<rule>` covers that rule on the whole diff. The id `sast:<tool>:<rule>:<file>:<line>` covers the finding's primary line. Comparison is equality of the two strings.

Semgrep receives `--baseline-commit` with the SHA of `git merge-base <base> HEAD`. The scan runs in a detached worktree of `HEAD`, deleted at the end. A dirty tree does not abort the gate. Rules are the committed `.semgrep/` directory at the root. Without a `.yml` or `.yaml` there, Semgrep does not start and the reason is `missing rules directory: .semgrep`. There is no registry id and no rule download. `uvx` downloads only the pinned Semgrep wheel.

Bandit scans the working directory. A project `.bandit` file does not choose the severity. bob passes `--ini` pointing at an empty file. `# nosec` and `nosem` stay visible for the waiver (`--ignore-nosec` and `--disable-nosem`).

If one language measures and the other does not, a pass becomes `warn` with exit `0`. A failure stays `failed` with exit `1`. If every requested language is unmeasured, the gate is `not_run`, the exit is `4`, and the report is written. A tool exit outside `0` and `1`, JSON that does not parse, or a missing binary counts as unmeasured. bob does not copy the tool's integer.

## Typing

`bob check --gates typing`. mypy, pyright, and tsc are the repository's executables. bob does not pin them, does not install them, and does not call them with `python -m` or `npx`.

There is no type-coverage threshold. The `typing` key has no children and does not turn the gate on. [ADR 0005](../adr/0005-modelo-de-gate-das-analises-novas.md) records that decision.

A checker diagnostic or an escape on a new diff line, with no waiver, is `failed` and exit `1`. The id is `typing:<file>:<line>:<code>`, compared as the whole string. The Python ignore code stored on the finding is `type: ignore`, including for `# type: ignore[arg-type]` and `# type:ignore`, so that id is quoted in YAML. A finding off the diff is `off_diff` and does not change the exit.

The escapes are `Any` and `type: ignore` in `.py` and `.pyi`, and `as any`, `@ts-ignore`, and `@ts-expect-error` in `.ts` and `.tsx`. `.js` is not scanned for escapes. `@ts-ignore` inside a string does not count.

Without a checker config, the language is `not_run`, contributes `0`, and the reason is `no checker config`.

- mypy runs when `mypy.ini`, `.mypy.ini`, `[mypy]` in `setup.cfg`, or `[tool.mypy]` in `pyproject.toml` exists.
- pyright runs when `pyrightconfig.json` or `[tool.pyright]` exists.
- If both exist, both run.
- tsc runs when the root `tsconfig.json` is a file. A nested `tsconfig` does not count. Without the root file, TypeScript is `not_run` and contributes `0`.

Config present and executable missing leaves that checker unmeasured. Exit `4` happens only when the gate was requested and no checker measured. If one measured and the other did not, the exit is the measured result.

Measured exits are mypy `0` and `1`, pyright `0` and `1`, and tsc `0`, `1`, and `2`. mypy `2`, pyright `2`, `3`, and `4`, and tsc `3` and `4` are outside measurement. Exit `0` with an error line, or an error exit with no diagnostic line, is unparseable. A tsc line with no file is ignored.

## Secrets

`bob check --gates secrets`. It runs `gitleaks detect --no-git` with gitleaks 8.30.1 on the `paths.include` roots.

A secret on a new diff line, with no waiver, leaves the gate `failed` and exits `1`. The waiver id is the whole string `secret:<rule>:<file>:<line>`. The id does not carry the secret value. The report lists the file, the line, and the rule id. It does not print the secret. Raw gitleaks output stays outside `.bob/`.

A finding off the diff appears in the Markdown and does not change the exit. A waived finding is in neither list.

The `secrets` key is an empty mapping. It does not turn the gate on. A `.gitleaksignore` file under an include root leaves the gate `not_run` and exits `4`, before the binary is called. Those entries belong in `.bob/waivers.yaml`.

## Dead code

`bob check --gates dead_code`. The gate warns and does not change the exit code. Python runs `python -m vulture` with vulture 2.16. TypeScript runs knip 6.41.0. knip does not receive `dead_code.min_confidence`.

A symbol counts when its definition line is on the new side of the diff. An edit that touches only the body, and not that line, does not warn. A symbol outside `paths.include`, or with a `paths.exclude` component in its path, is left out.

The waiver id is `dead:<file>:<line>:<name>`. The same id does not waive a mutant.

When `dead_code.min_confidence` is unset or null, bob does not pass `--min-confidence`. Vulture uses its own default, including `[tool.vulture]` in the repository. In the pinned vulture, `DEFAULTS` uses 0. The value `0`, when the key is present, passes `--min-confidence 0` and overrides `pyproject.toml`. The key is an integer from 0 to 100.

If one language measured and the other did not, the status follows the measured ledger. A clean ledger is `passed`. A symbol in the diff without a waiver is `warn`. The missing language stays in the gate reason. That does not force `warn` and does not use exit `4`. With no measurement, the status is `not_run` and the exit stays `0`. The report is written in both cases.

## Python and TypeScript together

When both languages are configured, a missing Node is not exit `4` for CRAP or for deps. Python is still measured. The TypeScript reason is appended. If the Python verdict was `passed`, the gate becomes `warn`. If it was already a failure, the failure stays and the reason names both. This is decision 10 in the spec, implemented in `crap_gate.py` and `deps_gate.py`.

A TypeScript-only repository without Node exits `4`, because the missing tool blocks the requested measurement.

DRY on its own treats a missing Node as `not_run` with exit `0`, including in a Python-only repository and including in fail mode.

The security gate uses the same split. A missing Semgrep in a repository that also measured Python does not exit `4`. Both languages unmeasured exits `4`.
