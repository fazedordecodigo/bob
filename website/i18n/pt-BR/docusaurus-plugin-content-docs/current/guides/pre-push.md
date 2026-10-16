# Hook pre-push

[Índice](../README.md) · [Primeiro check](../getting-started/first-check.md) · [CI](ci.md) · [Gates e waivers](gates-and-waivers.md)

O script `src/bob_quality/hooks/pre-push` roda os gates rápidos:

```bash
cp src/bob_quality/hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

O script é:

```sh
exec bob check --gates crap,dry,deps </dev/null
```

Ele retira `PYTEST_ADDOPTS` e `PYTEST_PLUGINS` do ambiente antes desse exec. Ele não passa nem `--dry-fail` nem `--max-new-clones`, então a duplicação segue o `bob.yaml`. Ele segue `BOB_LANG` e `language` no `bob.yaml` porque esses dois entram na resolução de idioma da CLI.

`tests/test_hook.py` confere que o hook termina em menos de 60 segundos no fixture.

A mutação não está neste comando. Tampouco `coverage`, `test_smells`, `cognitive`, `supply`, `security`, `typing`, `secrets` ou `dead_code`. Peça esses com `bob check --gates` quando quiser. A [Action de CI](ci.md) acrescenta `mutate` no pull request e ainda omite os gates opt-in, a menos que o workflow defina `gates`.
