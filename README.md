# bob

English | [Português](README.pt-BR.md)

bob gives coding agents (Cursor, Claude Code, GitHub Copilot, Devin) deterministic quality gates for the code they change, plus skills that tell the agent when to run them. The gates measure CRAP, duplication, mutation, and dependencies, only for the functions in the diff. Each run exits with a code the agent can act on and writes a one-page report that tells the human reviewer where to look first. The gates follow Uncle Bob's workflow, and the spec skills come from Matt Pocock (see [Credits](#credits)).

- CLI: `bob` (`bob check | crap | dry | deps | mutate | waive | doctor`)
- PyPI package: `bob-quality` (sdist and wheel ready, not published yet)
- Marketplace name: `bob` (not published yet)
- Configuration: `bob.yaml`
- Reports: `.bob/report.md` and `.bob/report.json` (schema v1)
- Output language: English (`en`, the default) or Brazilian Portuguese (`pt-BR`)

License: MIT.

## Status

These parts work on `main`:

- CRAP for Python and TypeScript.
- Duplication with jscpd, as a warning only.
- The dependency gate, with the rule that forbids cycles.
- Differential mutation testing for Python, and `bob waive`.
- The GitHub Action that comments the report on the pull request.
- `bob doctor`, and the `bob-quality` package ready to distribute. Nothing has been sent to PyPI.

These parts are planned:

- Mutation testing for TypeScript with StrykerJS ([#8](https://github.com/fazedordecodigo/bob/issues/8)).
- Packaging for Claude Code, Cursor, Copilot, and Devin ([#10](https://github.com/fazedordecodigo/bob/issues/10)).
- A warning for `no_coverage` mutants in the report ([#31](https://github.com/fazedordecodigo/bob/issues/31)).
- The `bob report` command that `docs/SPEC.md` lists. The CLI does not have it yet.
- Publication on PyPI and on the agent marketplaces.

## Flow

The agent changes the code. The pre-push hook runs the fast gates on the developer's machine, and the GitHub Action runs all four gates on the pull request. Both measure only the functions in the diff, write the same report, and exit with the same codes.

```mermaid
flowchart TD
    agent["Agent changes the code"]
    agent --> hook["pre-push hook<br/>bob check --gates crap,deps"]
    agent --> pr["Pull request"]
    pr --> action["GitHub Action<br/>bob check --gates crap,dry,deps,mutate"]
    hook --> diff["Gates measure only the functions in the diff"]
    action --> diff
    diff --> report[".bob/report.md<br/>.bob/report.json"]
    report --> code{"Exit code"}
    code -->|"0 passed"| done["Push or merge check passes"]
    code -->|"1 gate failed"| agent
    code -->|"2 baseline tests failed"| agent
    code -->|"3 survivor without waiver"| choice{"Kill or waive?"}
    code -->|"4 config or tool"| doctor["bob doctor"]
    choice -->|"stronger test"| agent
    choice -->|"bob waive"| waivers[".bob/waivers.yaml"]
    waivers -->|"committed with the code"| agent
    report --> comment["Action creates or updates one PR comment"]
    comment --> human["Human reviews the report and the waivers"]
```

## Installation (development)

You need Python 3.10 or later and Node 22.14.0, the versions the CI uses. The system Python of a current Ubuntu refuses `pip install` under PEP 668, so install inside a venv. To get Node 22.14.0, run `fnm install 22.14.0` or `nvm install 22.14.0`, or download the `.tar.gz` from <https://nodejs.org/dist/v22.14.0/>. Choose the `.tar.gz` over the `.tar.xz`, because the image may not have `xz`.

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -e ".[dev]"
npm ci
```

These commands install the `bob` command, the Python tools pinned in `pyproject.toml` (`lizard`, `coverage`, `mutmut`, `import-linter`), and the npm tools pinned in `package.json` (`c8`, `vitest`, `jscpd`, `dependency-cruiser`). `bob doctor` shows the expected and the found version of each tool.

## Usage

In a Python repository with `bob.yaml` and pytest:

```bash
bob check --base main
bob crap --base main
bob dry --base main
bob deps --base main
bob mutate --base main
bob waive <mutant-id|function> --reason "texto de uma linha"
bob doctor
```

Each command accepts these flags:

| Command | Flags |
|---|---|
| `bob check` | `--base`, `--config`, `--out` (default `.bob/`), `--gates` (default `crap,dry,deps`), `--format` (`md`, `json`, or `both`, default `both`) |
| `bob crap` | `--base`, `--config`, `--out`, `--threshold`, `--coverage-file` |
| `bob dry` | `--base`, `--config`, `--out` |
| `bob deps` | `--base`, `--config`, `--out` |
| `bob mutate` | `--base`, `--config`, `--out`, `--max-workers`, `--since-last-run` (reuses the cache, which is already the default) |
| `bob waive` | the mutant id or function name, `--reason` |
| `bob doctor` | `--install` |

Every command also accepts `--lang en|pt-BR`, before or after the command name. See [Output language](#output-language).

The commands write `.bob/report.md` and `.bob/report.json`. The exit codes are:

| Code | Meaning |
|---|---|
| `0` | Every gate that ran passed. |
| `1` | A gate failed. A changed function has CRAP at or above the limit, or the diff has a dependency violation. |
| `2` | The baseline tests failed before bob could measure. The `crap` gate runs them in the default `bob check` too. |
| `3` | A surviving mutant has no waiver. |
| `4` | Missing or different tool, or a configuration error that bob catches. A YAML syntax error or a key with the wrong type still gives a traceback and exit `1` ([#39](https://github.com/fazedordecodigo/bob/issues/39)). |

When more than one gate fails, `bob check` exits with the highest code.

A local `bob check` does not run mutation. `bob check --gates mutate` and `bob mutate` run it, only on the changed functions and on the functions that still have survivors.

## How it works

### Only the diff blocks

bob runs `git diff <base>...HEAD` and maps the changed lines to functions. A function counts as changed when the diff touches one of its lines. Only changed functions, and dependency violations that touch changed files, can fail a gate. Old debt goes to the informational sections of the report, marked `outside the diff; does not block`, and does not change the exit code. `--base` overrides the `base` key in `bob.yaml`.

### Pinned tools per language

bob wraps each tool in its own adapter and copies no code from them. The versions are pinned in `pyproject.toml` and `package.json`.

| Gate | Python | TypeScript |
|---|---|---|
| CRAP | `lizard` 1.24.1 for complexity, `coverage` 7.16.2 running pytest | `lizard` 1.24.1 for complexity, `c8` 12.0.0 running `vitest` 5.0.3 |
| Duplication | `jscpd` 5.4.1 | `jscpd` 5.4.1 |
| Mutation | `mutmut` 3.8.0 | planned ([#8](https://github.com/fazedordecodigo/bob/issues/8)) |
| Dependencies | `import-linter` 2.15 | `dependency-cruiser` 18.5.0 |

The npm tools need Node, and jscpd needs it in a Python-only repository too. In a repository with Python and TypeScript, a missing Node is not exit `4`. bob still measures Python and reports TypeScript as skipped, with a warning. Exit `4` stays when the missing tool blocks the requested measurement, as in a TypeScript-only repository without Node.

### `bob.yaml`

bob reads these keys. The values below are the defaults that apply when `bob.yaml` does not exist:

```yaml
base: origin/main
language: en
languages: [python]
paths:
  include: [src]
  exclude: [tests, node_modules, dist]
crap:
  max_per_function: 10
  scope: changed
duplication:
  min_tokens: 50
dependencies:
  python: .importlinter
  typescript: .dependency-cruiser.cjs
```

With `crap.scope: changed`, only changed functions block. Any other value makes every measured function count. If `--config` points to a file that does not exist, or the YAML is not a mapping, the run exits with `4`. A YAML syntax error, or a key with the wrong type such as `crap: 5` or `max_per_function: abc`, gives a traceback and exit `1` without a report ([#39](https://github.com/fazedordecodigo/bob/issues/39)).

### Output language

bob writes its text for humans in English (`en`) or Brazilian Portuguese (`pt-BR`). That covers the CLI messages, the `--help` text, `bob doctor`, the pre-push hook, and `.bob/report.md`. The first source that is set wins:

1. `--lang en|pt-BR`, before or after the command name.
2. The `BOB_LANG` environment variable.
3. `language` in `bob.yaml`.
4. `en`.

An empty value counts as unset, and the case matters (`pt-br` is invalid). When an invalid `--lang` or `BOB_LANG` decides the language, the run exits with `4`, prints `invalid language: <value> (use en or pt-BR)` to stderr, and writes no report. An invalid `language` in `bob.yaml` is a configuration error like any other. `bob check` exits with `4` and writes the report in the language from the flag, from the environment, or in English.

`.bob/report.json` does not depend on the language. Its keys stay the same and its `reason` texts are always in English, so the same input gives the same bytes in both languages. Tool output and rule names, such as `Proibido ciclo de dependência`, pass through unchanged.

In CI, set `language: pt-BR` in `bob.yaml`, or `BOB_LANG: pt-BR` in the job `env`. The GitHub Action comments `.bob/report.md`, so the comment follows the same choice.

### `bob doctor` and `--install`

`bob doctor` lists each tool with the pinned and the found version. It exits with `0` when all match, and with `4` when a tool is missing or differs, together with the install command. The versions must match exactly, so Node 20, or any Node other than 22.14.0, gives `4`. If the package directory is not writable, the message asks for `bob doctor --install`.

`bob doctor --install` runs `npm ci` in the installed package. When npm fails there with `EACCES`, `EPERM` or `EROFS`, it installs into a user cache (`$XDG_CACHE_HOME/bob-quality`, or `~/.cache/bob-quality`). Other npm errors exit with `4` and the exact command. Then it prints the same report.

### Waivers

Waivers live in `.bob/waivers.yaml`, which you commit with the code. `bob waive` writes one entry with these fields:

- `id`, the mutant id or the function name.
- `reason`, one line of text.
- `author`, from `git config user.name`, or `$USER`.
- `date`, the UTC date.

A waiver without a one-line reason is rejected with exit `4`. A new waiver with the same `id` replaces the old one. A waiver matches a mutant by the mutant id, the function name, `file:function`, or `file::function`. A `waivers.yaml` with the wrong structure makes the run exit with `4`. A YAML syntax error in it gives a traceback and exit `1`. The agent writes the waiver, and the human approves it in the pull request review. Every waiver appears at the top of the report.

### The report

`.bob/report.md` is one page for the reviewer. `.bob/report.json` has the same data and follows the schema in `src/bob_quality/schemas/report_v1.json` (`schema_version: 1`). `--format` picks one file or both. The Markdown report has these parts, with the headings in the output language. The names below are the `en` ones, and `README.pt-BR.md` lists the `pt-BR` ones:

1. `Waivers`, when there are waivers or mutation ran.
2. A header with the commit, the base, the date, and the tool versions.
3. `Verdict`, one line per gate: ✅ passed, ⚠️ warning, ❌ failed, or ⏭️ not run with the reason. A gate that did not run never shows as ✅.
4. `Where to focus the review`, the changed files ordered by risk (highest CRAP, plus clones and survivors).
5. `Top 5 functions by CRAP (diff)`.
6. `Information (old debt)`, functions outside the diff at or above the limit.
7. `Dependency violations and cycles`, and `Information (dependencies outside the diff)`.
8. `New clones`.
9. `Surviving mutants`.
10. `How to reproduce`, the exact command to run locally.

## Concepts

### CRAP

CRAP combines the complexity of a function with how much of it the tests run. A complex function with few tests is where a change is most likely to break something nobody sees, so the reviewer looks there first.

```text
CRAP = CC² × (1 − cov)³ + CC
```

`CC` is the cyclomatic complexity from lizard. `cov` is the fraction of the function's executable lines that the tests ran, from coverage.py or c8. A function with no executable lines counts as fully covered.

| CC | Coverage | CRAP | Result |
|---|---|---|---|
| 4 | 50% | 16 × 0.125 + 4 = 6 | passes |
| 5 | 0% | 25 × 1 + 5 = 30 | fails |
| 10 | 100% | 0 + 10 = 10 | fails |

The limit is CRAP < 10 per changed function. A function with CRAP of 10 or more fails the gate with exit `1`. The gate runs the tests to measure coverage, so a broken baseline gives exit `2`, in the default `bob check` too. Because CRAP is never below CC, a changed function with CC 10 or more fails at the default limit even with full coverage. Change the limit with `crap.max_per_function` in `bob.yaml` or with `bob crap --threshold`.

### Duplication (DRY)

A clone is a block of code that repeats another block. New clones show where the agent copied code instead of reusing it.

bob runs jscpd and keeps only the clones where at least one side touches a changed line. For example, if the diff adds a block of at least 50 tokens that matches existing code, the report lists the pair under `New clones` and the verdict shows ⚠️. The exit code stays `0`.

The limit is `duplication.min_tokens` (default 50). Duplication is a warning only and never changes the exit code. Without Node, the gate shows as ⏭️.

### Mutation testing

Coverage shows that a line ran. It does not show that a test checks the result. Mutation testing makes a small change to the code, called a mutant, and runs the tests again. If a test fails, the mutant is killed. If every test still passes, the mutant survived, and that line is not really tested.

- `killed`, `survived`, `timeout`, and `no_coverage` are the mutant states. `no_coverage` means no test ran the mutant.
- An equivalent mutant changes the code without changing its behavior, so no test can kill it. bob has no separate state for it. Record a waiver instead, as the `harden` skill describes.
- A waiver is a one-line reason, approved by the human in review, for a survivor that should not be killed.

For example, a mutant changes `if total > limit:` to `if total >= limit:`. If no test uses `total == limit`, the mutant survives. Write that test, or run `bob waive` with a reason.

bob mutates Python with mutmut. It runs the baseline tests first and exits with `2` if they fail. It mutates the changed functions, plus the functions that still have survivors without a waiver. The cache `.bob/mutation-cache.json` stores a hash of each function's text, so bob reuses the results of functions that did not change. The GitHub Action restores and publishes the cache as the `bob-mutation-cache` artifact.

The limit is zero survivors without a waiver. Any such survivor fails the gate with exit `3`. The report lists only survivors. Mutants with `killed`, `timeout`, and `no_coverage` do not block. A warning for `no_coverage` mutants is planned ([#31](https://github.com/fazedordecodigo/bob/issues/31)), and so is TypeScript mutation ([#8](https://github.com/fazedordecodigo/bob/issues/8)).

### Dependencies

Dependency rules and cycles show architecture erosion. When module A imports B and B imports A, neither can change alone.

bob runs the rules the repository already declares, in `.importlinter` for Python (import-linter) and in `.dependency-cruiser.cjs` for TypeScript (dependency-cruiser). It adds one rule that is always on, `Proibido ciclo de dependência`, which forbids dependency cycles. For example, if `app.a` imports `app.b` and the diff makes `app.b` import `app.a`, the gate shows ❌ and exits with `1`.

The limit is zero violations in the diff. A violation blocks only when its origin, its destination, or another module in the same cycle (strongly connected component) changed in the diff. Older violations appear as `outside the diff; does not block`.

## Pre-push hook

The script `src/bob_quality/hooks/pre-push` runs `bob check --gates crap,deps`, the fast gates. It follows `BOB_LANG` and `language` in `bob.yaml`. `tests/test_hook.py` checks that it finishes in under 60 s on the fixture.

```bash
cp src/bob_quality/hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## Tests

```bash
pytest
```

The repository fixtures are in `tests/fixtures`: `python_app` (a passing case and a case that fails with CRAP ≥ 10), `ts_app`, and `mixed_app`. `tests/fixtures/raw` has recorded output from the pinned tools.

The CI (`.github/workflows/ci.yml`) runs this suite on Python 3.10 and 3.12 with Node 22.14.0, on pull requests and on pushes to `main`.

## GitHub Action

The composite action in `.github/actions/bob` installs `bob` and runs `bob check` with `crap,dry,deps,mutate`. It restores and publishes the `bob-mutation-cache` artifact (`.bob/mutation-cache.json`), and it creates or updates a single pull request comment with `.bob/report.md`. The job exit code is the one from `bob`.

The action accepts the inputs `base`, `gates`, `pip-spec`, and `token`. This repository uses it in `.github/workflows/bob.yml`. `bob-quality` is not on PyPI yet, so in a checkout of this repository the action runs `pip install -e ".[dev]"`, and in another repository it installs the action's git source. Publication on the GitHub Marketplace is not part of this slice.

## Skills

- Matt Pocock's spec flow (MIT, attributed), in `skills/vendor/mattpocock/`: `grill-me` → `to-spec` → `to-tickets` → `implement-spec` / `tdd` → `code-review`.
- `skills/bob-check/` says when and how to run `bob check`.
- `skills/harden/` says how to kill a surviving mutant or record a waiver.
- `skills/review-report/` summarizes `.bob/report.md` in the pull request.
- `AGENTS.md` is the index for agents.

## Credits

The gates follow Uncle Bob's workflow. The READMEs and the output of his tools [crapper](https://github.com/unclebob/crapper) and [mutator](https://github.com/unclebob/mutator) (0BSD) are the behavior reference, and bob reuses none of their code. The exit codes take after mutator. The duplication gate uses jscpd. A structural dryer of bob's own, in the line of his [dryer](https://github.com/unclebob/dryer) (0BSD), is out of scope for the MVP. The limits come from his recent posts, CRAP < 10 for agents ([post on X](https://x.com/unclebobmartin/status/2108946115169030596)) and kill mutants within reason ([Aviator podcast](https://www.aviator.co/podcast/uncle-bob-martin-ai-clean-code)).

The spec skills are a verbatim copy of [mattpocock/skills](https://github.com/mattpocock/skills) at commit `49dd158d1076134a641b33efb035946536778336`, under the MIT license. See `skills/vendor/mattpocock/LICENSE` and `skills/vendor/mattpocock/NOTICE`.

The market tools (lizard, coverage.py, c8, vitest, mutmut, jscpd, import-linter, dependency-cruiser) are pinned dependencies, and bob copies no code from them.

## License

MIT. See `LICENSE`.
