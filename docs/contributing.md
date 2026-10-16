# Contributing

[Index](README.md) · [Installation](getting-started/installation.md) · [SPEC](architecture/spec.md) · [Changelog](changelog.md)

There is no `CONTRIBUTING.md` in this repository. What follows is what [AGENTS.md](https://github.com/fazedordecodigo/bob/blob/main/AGENTS.md), the workflows, and [SPEC.md](SPEC.md) already ask of someone changing the code. The license is MIT (`LICENSE`, copyright 2026 Emerson Delatorre).

The spec says merge and marketplace publication depend on Emerson's approval. Publication to PyPI and to the marketplaces is outside what `main` does today. The `package` workflow builds an sdist and a wheel, runs `twine check --strict dist/*`, and runs `bob doctor`. It does not publish.

## Environment

The steps in [AGENTS.md](https://github.com/fazedordecodigo/bob/blob/main/AGENTS.md), aligned with `.github/workflows/ci.yml` and `.github/workflows/bob.yml`:

1. Python 3.10 or newer. CI runs 3.10 and 3.12. The image needs `python3-venv`.
2. Node `>=22.18.0 <23`, the range `bob doctor` accepts. Node 20, Node 24, and a `-rc` suffix exit `4`. CI installs 22.18.0.
3. `python3 -m venv .venv && . .venv/bin/activate`.
4. `python -m pip install -e '.[dev]'`.
5. `npm ci` at the root.
6. `bob doctor`. It exits `0` only when every tool matches its pin. On an editable checkout, `bob doctor --install` installs at the root, the same place as `npm ci`. Delete `src/bob_quality/node_modules` if an older `--install` created it. That directory breaks `tests/test_mutmut_dogfood.py`.
7. `python -m pytest`. The suite takes several minutes. The mutmut dogfood generates `mutants/`.
8. `bob check --base origin/main --gates crap,dry,deps,mutate`, as CI does. Without `--gates`, the default is `crap,dry,deps`. The report is `.bob/report.md` and `.bob/report.json`.

## What the tests cover

The spec asks for tests through external behavior. The suite is `tests/`.

- `tests/test_cli.py`, `test_ts_cli.py`, `test_mixed_cli.py`, `test_deps_cli.py`, `test_language_cli.py`, `test_invalid_config.py`: the CLI on fixtures and on invalid config.
- `tests/fixtures/python_app`, `ts_app`, and `mixed_app`: minimal repositories. `tests/fixtures/raw` stores output from the pinned tools.
- `tests/test_crap.py` and the core: formula, limit, delta.
- `tests/test_adapters.py` and the deps tests: adapters against a recorded fixture.
- `tests/test_mutate.py`, `test_no_coverage.py`, `test_mutmut_dogfood.py`: mutation, the `no_coverage` failure, and the package under mutmut.
- `tests/test_skills_contract.py`: the skills listed in both manifests.
- `tests/test_hook.py`: the pre-push hook finishes in under 60 seconds on the fixture.

The spec says the plugin implementation is done with TDD. A parity test on `messages.py` requires the same keys and the same placeholders in `en` and `pt-BR`.

## Skills the repository asks the agent to follow

[AGENTS.md](https://github.com/fazedordecodigo/bob/blob/main/AGENTS.md) points at three skills:

- `skills/bob-check/SKILL.md`: run `bob check`, read the JSON, iterate until exit `0`.
- `skills/harden/SKILL.md`: kill a surviving mutant or record a waiver. Do not weaken production code to kill a mutant.
- `skills/review-report/SKILL.md`: summarize the report in the pull request body, in the shape Summary / Evidence / Merge Danger.

`bob report` is implemented. The interface is in [CLI](reference/cli.md#bob-report). The skills still point at `docs/exit-codes.md#exit-4` for invalid CLI usage.

## Where to change things

| Change | Place |
|---|---|
| Formula, limit, verdict | `src/bob_quality/core.py`, `crap.py` |
| One gate | the matching `*_gate.py`, or `mutate.py` |
| An external tool | `src/bob_quality/adapters/` |
| Text for humans | `src/bob_quality/messages.py` (both languages) |
| Config and waivers | `config.py`, `waivers.py` |
| Report | `report.py`, `schemas/report_v1.json` |
| Exit codes | `exit_codes.py` |
| Plugin skills | `skills/*/SKILL.md` and the list in `.claude-plugin/plugin.json` and `.cursor-plugin/plugin.json` |

The spec asks that a new language enter through an adapter, without changing the core. The concrete probes today are `python_probe.py` and `typescript_probe.py`. An explicit `languages` list is kept as written. An omitted or null key is detected. See [Configuration schema](reference/configuration.md#languages-and-paths).

## Documentation

The guides in this directory describe behavior checked against the code. [SPEC.md](SPEC.md) remains the approved spec. When behavior changes, update the matching guide and, when the change is product behavior, both READMEs and [CHANGELOG.md](https://github.com/fazedordecodigo/bob/blob/main/CHANGELOG.md). Each changelog note is in English and in Portuguese. Do not change the decision text of an existing ADR, and do not edit `SPEC.md`, without Emerson's approval.
