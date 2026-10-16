# Installation

[Index](../README.md) · [First check](first-check.md) · [Agents](agents.md) · [Contributing](../contributing.md)

There are two artifacts. The pip package `bob-quality` provides the `bob` command. The plugin `bob` provides the skills to agents. Nothing has been published to PyPI or to a marketplace. The steps below start from a clone of <https://github.com/fazedordecodigo/bob>.

## Requirements

- Python 3.10 or newer. CI (`.github/workflows/ci.yml`) runs 3.10 and 3.12. `requires-python` in `pyproject.toml` is `>=3.10`.
- Node `>=22.18.0 <23`. `bob doctor` accepts that range (`NODE` in `src/bob_quality/doctor.py`). Node 20, Node 24, and a `-rc` suffix make `doctor` exit `4`. A prerelease does not match the `X.Y.Z` pattern `_node_version` requires.
- For the npm tools, `npm ci` at the clone root, or `bob doctor --install` after the package is installed.

On a current Ubuntu the system Python refuses `pip install` under PEP 668. Use a venv. For Node, run `fnm install 22.18.0` or `nvm install 22.18.0`, or download the `.tar.gz` from <https://nodejs.org/dist/v22.18.0/>. [AGENTS.md](../../AGENTS.md) prefers the `.tar.gz` over the `.tar.xz` when the image has no `xz`.

The composite GitHub Action still installs Node `22.14.0` (`.github/actions/bob/action.yml`). That pin is the Action's setup step. It is not the range `bob doctor` accepts. See [CI](../guides/ci.md).

## The pip package

`pyproject.toml` declares the name `bob-quality`, version `0.1.0`, and the script:

```toml
[project.scripts]
bob = "bob_quality.cli:main"
```

Pinned Python dependencies in the package are `lizard==1.24.1`, `deptry==0.25.1`, `coverage==7.16.2`, `diff-cover==10.6.0`, `PyYAML==6.0.3`, `import-linter==2.15`, `grimp==3.17`, `mutmut==3.8.0`, `complexipy==8.0.1`, `bandit==1.9.4`, and `vulture==2.16`. The `dev` extra brings `pytest==9.1.1`, `jsonschema==4.26.0`, `build==1.6.1`, and `twine==7.0.0`. On Python older than 3.11 the extra also pins `tomli==2.5.0`. Semgrep 1.180.0 is not a dependency. The security gate runs `uvx --from semgrep==1.180.0`.

In a checkout, for development:

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -e '.[dev]'
npm ci
bob doctor
```

`pip install -e '.[dev]'` installs the `bob` command and the Python tools. `npm ci` installs, from the root `package.json` (`name`: `bob-quality-tools`), `c8@12.0.0`, `vitest@5.0.3`, `jscpd@5.4.1`, `dependency-cruiser@18.5.0`, `eslint@9.39.5`, `eslint-plugin-sonarjs@2.0.4`, `knip@6.41.0`, `@stryker-mutator/core@10.0.0`, and `@stryker-mutator/vitest-runner@10.0.0`. `bob doctor` lists each tool with the expected version and the found version and exits `0` only when every pin matches.

The pip-installed package carries `package.json`, `package-lock.json`, and `js/` (`tool.setuptools.package-data` in `pyproject.toml`). `bob doctor --install` runs `npm ci` in that package. If npm fails there with `EACCES`, `EPERM`, or `EROFS`, the install goes to `$XDG_CACHE_HOME/bob-quality` or `~/.cache/bob-quality` (`src/bob_quality/npm_tools.py`). Any other npm error exits `4` and prints the command. If the package directory is not writable, the doctor message asks for `bob doctor --install`.

The wheel does not include the skills. From a pip install, pass `--source` with the clone. See [Agents](agents.md).

On an editable checkout, `src/bob_quality/package.json` is a symlink to the root `package.json`. `bob doctor --install` installs at that root, the same place as `npm ci`. If `src/bob_quality/node_modules` already exists from an older `--install`, delete that directory before `pytest`. It breaks `tests/test_mutmut_dogfood.py`.

## Next

Run the [first check](first-check.md), or install the skills with [Agents](agents.md).
