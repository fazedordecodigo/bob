# CI com a GitHub Action

[Índice](../README.md) · [Hook pre-push](pre-push.md) · [Relatórios](reports.md) · [CLI](../reference/cli.md)

A action composta em `.github/actions/bob` instala o bob e roda `bob check`. Este repositório a chama a partir de `.github/workflows/bob.yml`.

## Entradas

De `.github/actions/bob/action.yml`:

| Input | Padrão | Efeito |
|---|---|---|
| `base` | vazio | Ref do diff. Vazio usa `origin/$GITHUB_BASE_REF` num pull request. Caso contrário o bob usa o `bob.yaml`. |
| `gates` | `crap,dry,deps,mutate` | Lista separada por vírgula. |
| `pip-spec` | vazio | Requisito pip explícito. Vazio instala o checkout quando ele é `bob-quality`. Caso contrário instala a fonte git da action. |
| `token` | vazio | Comentário e artefatos. Vazio usa o `GITHUB_TOKEN` do workflow. |
| `language` | vazio | `en` ou `pt-BR` para o `bob check` e para o comentário do pull request. Vazio deixa `BOB_LANG` e `language` no `bob.yaml` no controle. |

`bob-quality` não está no PyPI. Num checkout deste repositório a action roda `pip install -e ".[dev]"` (`install.sh`). Em outro repositório ela instala a fonte git da action. Publicação no GitHub Marketplace não faz parte desta action.

## O que o job instala

A action configura Python 3.12 e Node `22.14.0` (`actions/setup-node` pinado por SHA em `action.yml`). Em seguida instala o jscpd `5.4.1` para que o gate `dry` possa rodar quando quem chama não instalou Node e jscpd. Sem essa instalação, `dry` fica `not_run`.

O `bob doctor` aceita Node `>=22.18.0 <23`. Os workflows de CI `.github/workflows/ci.yml` e `.github/workflows/bob.yml` usam Node `22.18.0`. O próprio passo de setup da Action ainda é `22.14.0`. São dois pins na árvore. Esta página registra os dois.

## Cache e comentário

A action restaura `.bob/mutation-cache.json` e `.bob/stryker-incremental.json` do artefato `bob-mutation-cache`. Uma falha de restore não interrompe o check (`restore_cache.py || echo` na action). O upload usa `if: always()`, `retention-days: 7` e `if-no-files-found: ignore`. Um dos dois arquivos pode estar ausente.

Num pull request a action cria ou atualiza um comentário com `.bob/report.md`. O marcador e o limite de truncamento ficam em `.github/actions/bob/upsert_comment.py`. O limite do corpo é 65536 caracteres. Acima disso, o comentário é truncado e a nota usa o idioma de saída resolvido. Erros de comentário usam esse idioma também: repo, pr ou token ausente; relatório ausente; lista de comentários inválida. O código de saída do job é o código de saída do bob, inclusive `4` para uso inválido da linha de comando (`propagate_exit.sh`).

O comentário resolve o idioma com `resolve_language`. A ordem é o input `language` da Action, depois `BOB_LANG`, depois `language` no `bob.yaml`, depois `en`. Um input `language` vazio é pulado. `upsert_comment.py` lê `bob.yaml` do diretório de trabalho do processo.

## Gates que o input padrão não roda

O valor padrão de `gates` é `crap,dry,deps,mutate`. Estes nomes só rodam quando o workflow os acrescenta a `gates`: `coverage`, `test_smells`, `cognitive`, `supply`, `security`, `typing`, `secrets`, `dead_code`. Um nome desconhecido é `not_run` e contribui com exit `0`.

A spec diz que o check de CI roda todo gate. O código roda o input da Action. O input padrão são os quatro nomes acima. Ver [SPEC](../architecture/spec.md).
