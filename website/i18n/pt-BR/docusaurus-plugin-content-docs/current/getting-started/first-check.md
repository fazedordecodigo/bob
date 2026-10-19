# Primeiro check

[Índice](../README.md) · [Instalação](installation.md) · [CLI](../reference/cli.md) · [Códigos de saída](../exit-codes.md)

Num checkout git que tem o código que você quer medir, com `bob` no `PATH`:

```bash
bob check --base origin/main
```

`--base` seleciona a ref de `git diff <base>...HEAD`. Quando a flag é omitida, o bob usa a chave `base` do `bob.yaml`, ou `origin/main` quando essa chave é omitida (`Config.base` em `src/bob_quality/config.py`).

Sem `--gates`, o comando roda `crap`, `dry` e `deps`. Ele não roda mutação. Para rodar mutação nas funções alteradas:

```bash
bob check --base origin/main --gates crap,dry,deps,mutate
```

A execução grava `.bob/report.md` e `.bob/report.json`, a menos que o preflight recuse a configuração. `--format md`, `--format json` ou `--format both` (o padrão) escolhe os arquivos. `--out` muda o diretório. O padrão é `.bob/`.

## O que o código de saída significa

| Código | Significado |
|---|---|
| `0` | Todo gate que rodou passou, ou só avisou. |
| `1` | Um gate que bloqueia falhou no diff. |
| `2` | Os testes da baseline falharam antes de o bob poder medir. |
| `3` | Um mutante sobrevivente numa linha alterada não tem waiver, ou uma função alterada tem um mutante `no_coverage`. |
| `4` | Configuração inválida, uso inválido da linha de comando, ou uma ferramenta ausente que bloqueia a medição pedida. |

Quando mais de um gate devolve um código, o processo fica com o mais alto (`_worse` em `src/bob_quality/check.py`). O catálogo completo está em [Códigos de saída](../exit-codes.md).

Abra `.bob/report.md` na seção Veredito. Um gate que não rodou é marcado como não executado, com um motivo. Ele nunca aparece como passado. [Relatórios](../guides/reports.md) percorre o resto da página.

Um `bob check` local não roda mutação, a menos que `mutate` esteja em `--gates`. O hook de pre-push usa os três gates rápidos. O input padrão da GitHub Action acrescenta `mutate`. Ver [Hook pre-push](../guides/pre-push.md) e [CI](../guides/ci.md).

## Um repositório sem bob.yaml

Se `bob.yaml` falta e `--config` não foi passado, o bob usa os padrões e detecta as linguagens a partir dos arquivos sob `paths.include`. Ver [Configuração](../guides/configuration.md). Se `--config` nomeia um arquivo que não está lá, `check`, `crap`, `dry`, `deps` e `mutate` saem com `4`, imprimem `config file not found: <path>` no stderr e não gravam nada.
