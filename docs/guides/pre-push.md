# Pre-push hook

[Index](../README.md) · [First check](../getting-started/first-check.md) · [CI](ci.md) · [Gates and waivers](gates-and-waivers.md)

The one-line install writes the hook to `.git/hooks/pre-push` (it runs `bob setup`, which installs the hook):

```bash
curl -fsSL https://github.com/fazedordecodigo/bob/releases/latest/download/install.sh | sh
```

If the project already has a pre-push hook that bob did not write, `bob setup` keeps it and prints the line to add to it.

The script is:

```sh
exec bob check --gates crap,dry,deps </dev/null
```

It unsets `PYTEST_ADDOPTS` and `PYTEST_PLUGINS` before that exec. It passes neither `--dry-fail` nor `--max-new-clones`, so duplication follows `bob.yaml`. It follows `BOB_LANG` and `language` in `bob.yaml` because those enter the CLI language resolution.

`tests/test_hook.py` checks that the hook finishes in under 60 seconds on the fixture.

Mutation is not in this command. Neither are `coverage`, `test_smells`, `cognitive`, `supply`, `security`, `typing`, `secrets`, or `dead_code`. Ask for those with `bob check --gates` when you want them. The [CI Action](ci.md) adds `mutate` on the pull request and still omits the opt-in gates unless the workflow sets `gates`.
