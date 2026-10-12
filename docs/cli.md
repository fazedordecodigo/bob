# CLI

[Índice](README.md) · [Instalação](instalacao.md) · [Configuração](configuracao.md) · [Gates](gates.md) · [Exit codes](exit-codes.md) · [Relatórios](relatorios.md)

O comando é `bob`. O parser está em `src/bob_quality/cli.py`. A ajuda e as mensagens saem no idioma resolvido. Os textos ficam em `src/bob_quality/messages.py`.

```bash
bob check --base main
bob crap --base main
bob dry --base main
bob deps --base main
bob mutate --base main
bob waive <mutant-id|função> --reason "texto de uma linha"
bob doctor
```

Todo comando aceita `--lang en|pt-BR` antes ou depois do nome. Ver [Idioma](#idioma---lang).

Um uso inválido da linha de comando sai com `4`. O stderr é o texto de uso do argparse, não menciona baseline, e nada é gravado em `.bob/`. A ajuda (`-h`, `--help`) sai com `0`. Isso não é o exit `2` da suíte.

## bob check

Roda os gates pedidos e grava `.bob/` (ou `--out`).

| Flag | Padrão | Efeito |
|---|---|---|
| `--base` | `base` do `bob.yaml`, ou `origin/main` | Ref de `git diff <base>...HEAD` |
| `--config` | `bob.yaml` no diretório atual, se existir | Outro arquivo de configuração |
| `--out` | `.bob/` | Pasta do relatório |
| `--gates` | `crap,dry,deps` | Lista separada por vírgula. Constante `DEFAULT_GATES` em `src/bob_quality/check.py` |
| `--format` | `both` | `md`, `json` ou `both` |
| `--lang` | ver [Idioma](#idioma---lang) | `en` ou `pt-BR` |

Um nome de gate que o código não trata vira status `not_run`, com o motivo `gate não implementado nesta fatia` em `pt-BR`, e esse gate contribui exit `0` (`check.py`, ramo final de `_absorb`). Os quatro nomes implementados são `crap`, `dry`, `deps` e `mutate`.

`bob check` sem `mutate` na lista não roda mutação. `bob check --gates mutate` e `bob mutate` rodam.

Quando mais de um gate devolve código, fica o maior (`_worse` em `check.py`).

## Outros comandos de medição

`crap`, `dry`, `deps` e `mutate` chamam o mesmo `run_check`, cada um com um gate, e gravam os dois formatos (`fmt="both"` no `cli.py`). Eles aceitam `--base`, `--config`, `--out` e `--lang`.

| Comando | Flags a mais |
|---|---|
| `bob crap` | `--threshold` substitui `crap.max_per_function` nesta execução. `--coverage-file` aponta um arquivo de cobertura já gerado |
| `bob dry` | nenhuma além das compartilhadas |
| `bob deps` | nenhuma além das compartilhadas |
| `bob mutate` | `--max-workers` vira `--max-children` do mutmut (`src/bob_quality/mutmut_tool.py`). `--since-last-run` não muda a medição: a ajuda diz que reusar o cache já é o padrão. A flag só entra na linha `reproduce` do relatório quando foi passada |

## bob doctor

Lista cada pino de `src/bob_quality/doctor.py` com a versão esperada e a encontrada. Sai com `0` quando todas coincidem e com `4` quando alguma falta ou diverge, e imprime o comando de instalação. Não grava `.bob/report.md`.

Pinos, na ordem do código: lizard 1.24.1, coverage.py 7.16.2, node 22.14.0, c8 12.0.0, vitest 5.0.3, jscpd 5.4.1, mutmut 3.8.0, import-linter 2.15, dependency-cruiser 18.5.0.

`bob doctor --install` roda `npm ci` no pacote instalado e depois imprime o mesmo relatório. Ver [Instalação](instalacao.md#pacote-pip-bob-quality).

`doctor` também passa por `_blocked_config`: um `bob.yaml` ou um `.bob/waivers.yaml` inválido no diretório atual faz o doctor sair com `4` antes do relatório de versões. Ver [Exit codes](exit-codes.md#exit-4).

## bob waive

```bash
bob waive <id-ou-função> --reason "uma linha"
```

Grava ou substitui uma entrada em `.bob/waivers.yaml` e sai com `0`. Não gera `report.md`. Os campos e as regras de formato estão em [Waivers](configuracao.md#bobwaiversyaml).

`--reason` é obrigatório na prática: ausência, string vazia ou quebra de linha levantam `WaiverError` e o processo sai com `4`. Essa mensagem segue o idioma resolvido (`waiver sem motivo: informe --reason com uma linha` em `pt-BR`). Um alvo vazio sai com `4` e `waiver sem alvo`.

Um `.bob/waivers.yaml` que já está inválido é recusado antes, em inglês no stderr, também com `4`, e o arquivo não é reescrito. Ver [Exit codes](exit-codes.md#exit-4).

## Idioma (`--lang`)

Vale a primeira fonte definida (`resolve_language` em `src/bob_quality/config.py`, chamada a partir de `cli.py`):

1. `--lang en` ou `--lang pt-BR`, antes ou depois do comando.
2. A variável `BOB_LANG`.
3. A chave `language` no `bob.yaml` (ou no arquivo de `--config`).
4. `en`.

A caixa importa. `pt-br` é inválido. Os valores aceitos são os de `LANGUAGES` em `messages.py`: `en` e `pt-BR`.

Um `--lang` ou `BOB_LANG` vazio é inválido. A CLI sai com `4`, imprime `invalid language: "" (use en or pt-BR)` no stderr e não grava relatório. Uma chave `language` vazia no YAML conta como ausente (`_language` devolve `None`).

Idioma inválido, `language` que não é string, YAML que não é mapeamento, erro de sintaxe no `bob.yaml` e chave com tipo errado também saem com `4` em inglês no stderr, mesmo que se pretendesse `pt-BR`, e não gravam relatório. O mesmo vale para `paths`, `languages`, `base`, `dependencies`, `duplication` e as listas `include` e `exclude`, em `check`, `doctor`, `waive` e nos outros comandos. Uma chave desconhecida segue o mesmo caminho. Ver [Exit codes](exit-codes.md#exit-4).

O que muda com o idioma: mensagens da CLI, texto do `--help`, `bob doctor`, o hook (porque ele chama a CLI), `.bob/report.md` e a nota de truncamento do comentário da Action. O `.bob/report.json` é o mesmo arquivo nos dois idiomas (`JSON_LANGUAGE = "en"` em `report.py`). Detalhe em [Relatórios](relatorios.md#o-que-não-muda-com-o-idioma).

No CI, `language: pt-BR` no `bob.yaml` ou `BOB_LANG: pt-BR` no `env` do job. O input `language` da Action repassa a escolha ao `bob check` e ao comentário. Input vazio deixa `BOB_LANG` e o `bob.yaml`.

## O que cada superfície roda

| Superfície | Gates | Onde está |
|---|---|---|
| `bob check` sem `--gates` | `crap,dry,deps` | `DEFAULT_GATES` |
| Hook `pre-push` | `crap,dry,deps` | `src/bob_quality/hooks/pre-push` |
| GitHub Action, input `gates` omitido | `crap,dry,deps,mutate` | `.github/actions/bob/action.yml` |

O hook, a SPEC e o padrão da CLI usam `crap,dry,deps`. O CI pede `mutate` pelo input da Action, não porque o padrão da CLI tenha mudado. A skill `skills/bob-check/SKILL.md` também mostra a interface da spec, inclusive `bob report`.

## Comandos que a spec lista e a CLI ainda não tem

`build_parser` registra `check`, `crap`, `dry`, `deps`, `mutate`, `waive` e `doctor`. Não registra `report`. A interface citada na [SPEC](SPEC.md) e nas skills inclui:

```text
bob report  [--in .bob/] [--out .bob/report.md]
```

O [README.pt-BR.md](../README.pt-BR.md) marca esse comando como planejado. Quem precisa do Markdown gera com `bob check --format md` ou `--format both`.
