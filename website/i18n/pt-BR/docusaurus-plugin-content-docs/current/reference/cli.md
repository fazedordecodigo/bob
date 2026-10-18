# CLI

[Índice](../README.md) · [Instalação](../getting-started/installation.md) · [Schema de configuração](configuration.md) · [Gates e waivers](../guides/gates-and-waivers.md) · [Códigos de saída](../exit-codes.md) · [Relatórios](../guides/reports.md)

O comando é `bob`. O parser é `build_parser` em `src/bob_quality/cli.py`. O texto de ajuda e as mensagens usam o idioma de saída resolvido. As strings ficam em `src/bob_quality/messages.py`.

```bash
bob check --base origin/main
bob crap --base origin/main
bob dry --base origin/main
bob deps --base origin/main
bob mutate --base origin/main
bob report
bob waive <file::function|Target> --reason "one line of text"
bob doctor
```

Todo comando aceita `--lang en|pt-BR` antes ou depois do nome do comando. Ver [Idioma da saída](#idioma-da-saída).

Um uso inválido da linha de comando sai com `4`. O stderr é o texto de uso do argparse, não menciona baseline, e nada é gravado em `.bob/`. A ajuda (`-h`, `--help`) sai com `0`. Esse `4` não é o exit `2` da baseline. Um valor fora da regra de `--threshold` ou de `--max-workers` também é uso inválido. A última linha do stderr permanece em inglês mesmo com `--lang pt-BR`, como em `bob crap: error: argument --threshold: invalid value: 'nan' (use a finite number greater than 0)`.

`--config` antes do nome do comando sai com `4` e não grava nada. A última linha do stderr permanece em inglês. Ela mostra o comando com a flag depois do nome, como em `bob: error: --config goes after the command: bob check --config ci.yaml`. Um caminho com espaço sai entre aspas, como em `bob crap --config 'my ci.yaml'`. `doctor`, `waive` e `report` não aceitam `--config`. A última linha é `bob: error: doctor does not accept --config`, e a mesma forma para `waive` e `report`. `bob --help` não lista `--config`.

## bob check

Roda os gates pedidos e grava `.bob/` (ou `--out`).

| Flag | Padrão | Efeito |
|---|---|---|
| `--base` | `base` do `bob.yaml`, ou `origin/main` | Ref de `git diff <base>...HEAD` |
| `--config` | `bob.yaml` no diretório de trabalho, se existir | Outro arquivo de configuração |
| `--out` | `.bob/` | Diretório do relatório |
| `--gates` | `crap,dry,deps` | Lista separada por vírgula. A constante é `DEFAULT_GATES` em `src/bob_quality/check.py` |
| `--format` | `both` | `md`, `json` ou `both` |
| `--dry-fail` | desligada | Liga o modo fail do DRY nesta execução, o mesmo que `duplication.new_clones: fail` |
| `--max-new-clones` | `duplication.max_new_clones` | Teto de clones novos no modo fail nesta execução. `0` é um teto de verdade. Um valor negativo sai com `4` |
| `--lang` | ver [Idioma da saída](#idioma-da-saída) | `en` ou `pt-BR` |

Um caminho de `--config` que não é um arquivo sai com `4`. O stderr em inglês nomeia o caminho, como em `config file not found: <path>`. Nada é gravado. O mesmo vale para `crap`, `dry`, `deps` e `mutate`. Ver [Saída 4](../exit-codes.md#saída-4).

Um nome de gate que o código não trata vira `not_run`, com o motivo `gate not implemented in this slice` em inglês (`check.gate_not_implemented` em `messages.py`), e esse gate contribui com exit `0`. Os nomes implementados são `crap`, `dry`, `deps`, `mutate`, `coverage`, `test_smells`, `cognitive`, `supply`, `security`, `typing`, `secrets` e `dead_code`. Os últimos oito só rodam por `--gates` no `bob check`.

`bob check` sem `mutate` na lista não roda mutação. `bob check --gates mutate` e `bob mutate` rodam.

Quando mais de um gate devolve um código, o mais alto vence (`_worse` em `check.py`).

## Outros comandos de medição

`crap`, `dry`, `deps` e `mutate` chamam o mesmo `run_check`, cada um com um gate, e gravam os dois formatos. Eles aceitam `--base`, `--config`, `--out` e `--lang`.

| Comando | Flags extras |
|---|---|
| `bob crap` | `--threshold` substitui `crap.max_per_function` nesta execução. Tem de ser um número finito maior que `0`. `--coverage-file` aponta para um arquivo de cobertura que já existe |
| `bob dry` | `--dry-fail` e `--max-new-clones`, as mesmas flags de `bob check` |
| `bob deps` | nenhuma além das flags compartilhadas |
| `bob mutate` | `--max-workers` vira `--max-children` do mutmut (`src/bob_quality/mutmut_tool.py`). `--since-last-run` não muda a medição: o texto de ajuda diz que reusar o cache já é o padrão. A flag só entra na linha de reprodução do relatório quando foi passada |

`--max-workers` aceita um inteiro de 1 a 64. O teto é `_WORKER_CEILING` em `src/bob_quality/cli.py`. Um valor fora dessa faixa sai com `4`. A última linha do stderr é `bob mutate: error: argument --max-workers: invalid value: '65' (use an integer from 1 to 64)` quando o valor é `65`.

## O que cada superfície roda

| Superfície | Gates | Onde |
|---|---|---|
| `bob check` sem `--gates` | `crap,dry,deps` | `DEFAULT_GATES` |
| Hook `pre-push` | `crap,dry,deps` | `src/bob_quality/hooks/pre-push` |
| GitHub Action, input `gates` omitido | `crap,dry,deps,mutate` | `.github/actions/bob/action.yml` |

A spec diz que o hook local roda `crap,dry,deps` e que no CI o check roda todo gate. O script do hook passa `crap,dry,deps`. O padrão da CLI são os mesmos três. O CI pede `mutate` pelo input da Action, não porque o padrão da CLI mudou. A skill `skills/bob-check/SKILL.md` nomeia esses dois comandos. Ver [SPEC](../architecture/spec.md).

## bob doctor

Lista cada pin de `src/bob_quality/doctor.py` com a versão esperada e a versão encontrada. Sai com `0` quando todo pin está satisfeito e com `4` quando um falta ou está fora do pin, e imprime o comando de instalação. Não grava `.bob/report.md`. Um sufixo `-rc` na versão encontrada está fora do pin, e o doctor sai com `4`.

Pins, na ordem do código: lizard 1.24.1, deptry 0.25.1, coverage.py 7.16.2, node `>=22.18.0 <23`, c8 12.0.0, vitest 5.0.4, jscpd 5.4.1, eslint 9.39.5, eslint-plugin-sonarjs 2.0.4, mutmut 3.8.0, complexipy 8.0.1, import-linter 2.15, grimp 3.17, diff-cover 10.6.0, bandit 1.9.4, dependency-cruiser 18.6.0, gitleaks 8.30.1, vulture 2.16, knip 6.41.0, stryker 10.0.0, stryker-vitest-runner 10.0.0. A versão esperada de uma ferramenta Python vem do `Requires-Dist` instalado de `bob-quality`. O Semgrep 1.180.0 não está nessa lista. O gate de segurança chama `uvx --from semgrep==1.180.0`.

`bob doctor --install` roda `npm ci` no pacote instalado e depois imprime o mesmo relatório. Ver [Instalação](../getting-started/installation.md).

`doctor` também passa pelo preflight de configuração. Um `bob.yaml` ou `.bob/waivers.yaml` inválido no diretório de trabalho faz o doctor sair com `4` antes do relatório de versões. Ver [Saída 4](../exit-codes.md#saída-4).

## bob waive

```bash
bob waive <file::function|Target> --reason "one line"
```

Grava ou substitui uma linha em `.bob/waivers.yaml` e sai com `0`. Não grava `report.md`. Os campos estão em [Configuração](../guides/configuration.md#bobwaiversyaml).

O alvo é `file::function`, que dispensa todo sobrevivente da função, ou a coluna Target do último relatório de mutação, que dispensa um sobrevivente. O comando lê sobreviventes de `.bob/mutation-cache.json` e `.bob/stryker-mutants.json`. Rode a mutação primeiro.

`--reason` é obrigatório na prática. Um motivo ausente, uma string vazia ou uma quebra de linha levanta `WaiverError` e o processo sai com `4`. Essa mensagem segue o idioma resolvido. Um alvo vazio sai com `4`. Um alvo que nenhum sobrevivente tem, como o id do mutante ou um nome de função nu, sai com `4` e não grava nada.

Um `.bob/waivers.yaml` que já está inválido é recusado primeiro, em inglês no stderr, também com `4`, e o arquivo não é reescrito.

## bob report

`build_parser` registra `report` ao lado de `check`, `crap`, `dry`, `deps`, `mutate`, `waive` e `doctor`. A interface casa com a spec:

```text
bob report  [--in .bob/] [--out .bob/report.md]
```

`--in` é o diretório que já contém `report.json`. O padrão é `.bob/`. `--out` é o arquivo Markdown. O padrão é `.bob/report.md`. O comando não mede de novo. Ele lê o JSON e grava o Markdown no idioma de saída escolhido por `--lang`, por `BOB_LANG` ou por `language` no `bob.yaml`. O processo sai com o `exit_code` guardado nesse JSON. O inteiro tem de ser 0, 1, 2, 3 ou 4 (`_SAVED_EXIT_CODES` em `src/bob_quality/report.py`).

Se o arquivo falta, o texto não é JSON, ou a forma é inválida, o comando sai com `4`. O stderr permanece em inglês. O comando não grava `--out` e não trunca um arquivo que já estava lá. Uso inválido da linha de comando também sai com `4` e não grava relatório. O preflight de `bob.yaml` e `.bob/waivers.yaml` é o mesmo dos outros comandos.

`report.json` permanece em inglês. `--lang pt-BR` traduz os títulos que o catálogo conhece. Um motivo de gate, ou um nome de regra, permanece em inglês quando o JSON já o guardou assim. Durante a medição, `--format md` grava só `report.md`. `--format json` grava só `report.json`. `--format both` grava os dois. `write_report` em `src/bob_quality/report.py` é essa divisão.

## Idioma da saída

A primeira fonte que está definida vence:

1. `--lang en` ou `--lang pt-BR`, antes ou depois do comando.
2. A variável de ambiente `BOB_LANG`.
3. `language` no `bob.yaml`, ou no arquivo de `--config`.
4. `en`.

A caixa importa. `pt-br` é inválido. Um `--lang` ou `BOB_LANG` vazio sai com `4`, imprime `invalid language: "" (use en or pt-BR)` no stderr e não grava relatório. Uma chave `language` vazia permanece não definida.

Um idioma inválido, um `language` que não é string, um YAML que não é um mapeamento, um erro de sintaxe YAML e uma chave com o tipo errado também saem com `4` em inglês no stderr, mesmo quando a intenção era `pt-BR`, e não gravam relatório. O mesmo vale para `paths`, `languages`, `base`, `dependencies` e as listas `include` e `exclude`, em `check`, `doctor`, `waive` e os outros comandos. Uma entrada de `paths.include` que não está no disco segue o mesmo caminho. O stderr nomeia o arquivo e cada entrada ausente, como em `bob.yaml: paths.include does not exist: missing-root`. Um `paths.include` omitido ou vazio permanece `src` e não é conferido.

Um `duplication` inválido também sai com `4`, em inglês no stderr, sem relatório. Uma chave desconhecida segue o mesmo caminho. Ver [Saída 4](../exit-codes.md#saída-4) e o [schema de configuração](configuration.md).

O que segue o idioma da saída: mensagens da CLI, texto do `--help`, `bob doctor`, o hook (porque ele chama a CLI), `.bob/report.md`, a nota de truncamento do comentário da Action e os erros próprios desse comentário. `.bob/report.json` é o mesmo arquivo nos dois idiomas (`JSON_LANGUAGE = "en"` em `report.py`).
