# CLI

[Índice](README.md) · [Instalação](instalacao.md) · [Configuração](configuracao.md) · [Gates](gates.md) · [Exit codes](exit-codes.md) · [Relatórios](relatorios.md)

O comando é `bob`. O parser está em `src/bob_quality/cli.py`. A ajuda e as mensagens saem no idioma resolvido. Os textos ficam em `src/bob_quality/messages.py`.

```bash
bob check --base main
bob crap --base main
bob dry --base main
bob deps --base main
bob mutate --base main
bob waive <arquivo::função|Alvo> --reason "texto de uma linha"
bob doctor
```

Todo comando aceita `--lang en|pt-BR` antes ou depois do nome. Ver [Idioma](#idioma---lang).

Um uso inválido da linha de comando sai com `4`. O stderr é o texto de uso do argparse, não menciona baseline, e nada é gravado em `.bob/`. A ajuda (`-h`, `--help`) sai com `0`. Isso não é o exit `2` da suíte. Um valor fora da regra de `--threshold` ou de `--max-workers` também é uso inválido. A última linha do stderr fica em inglês, mesmo com `--lang pt-BR`, como `bob crap: error: argument --threshold: invalid value: 'nan' (use a finite number greater than 0)`.

`--config` antes do nome do comando também é uso inválido. Nada é gravado em `.bob/`. A última linha do stderr fica em inglês, mesmo com `--lang pt-BR`. Ela mostra o comando com a flag depois do nome, como `bob: error: --config goes after the command: bob check --config ci.yaml`. Um caminho com espaço sai entre aspas, como `bob crap --config 'my ci.yaml'`. `doctor` não aceita `--config`. A última linha é `bob: error: doctor does not accept --config`. `waive` também não aceita. A última linha é `bob: error: waive does not accept --config`. `bob --help` não lista `--config`.

## bob check

Roda os gates pedidos e grava `.bob/` (ou `--out`).

| Flag | Padrão | Efeito |
|---|---|---|
| `--base` | `base` do `bob.yaml`, ou `origin/main` | Ref de `git diff <base>...HEAD` |
| `--config` | `bob.yaml` no diretório atual, se existir | Outro arquivo de configuração |
| `--out` | `.bob/` | Pasta do relatório |
| `--gates` | `crap,dry,deps` | Lista separada por vírgula. Constante `DEFAULT_GATES` em `src/bob_quality/check.py` |
| `--format` | `both` | `md`, `json` ou `both` |
| `--dry-fail` | desligada | Liga o modo fail do DRY nesta execução, como `duplication.new_clones: fail`. Ver [Gates](gates.md#dry) |
| `--max-new-clones` | `duplication.max_new_clones` | Teto de clones novos no modo fail nesta execução. `0` é um teto de verdade. Negativo sai com `4` |
| `--lang` | ver [Idioma](#idioma---lang) | `en` ou `pt-BR` |

Um `--config` que aponta para um arquivo inexistente sai com `4`. O stderr fica em inglês e cita o caminho, como em `config file not found: <caminho>`. Nada é gravado. O mesmo vale para `crap`, `dry`, `deps` e `mutate`. Detalhe em [Exit 4](exit-codes.md#exit-4).

Um nome de gate que o código não trata vira status `not_run`, com o motivo `gate não implementado nesta fatia` em `pt-BR`, e esse gate contribui exit `0` (`check.py`, ramo final de `_absorb_remaining`). Os nomes implementados são `crap`, `dry`, `deps`, `mutate`, `coverage`, `test_smells`, `cognitive`, `supply`, `security`, `typing`, `secrets` e `dead_code`. `coverage`, `test_smells`, `cognitive`, `supply`, `security`, `typing`, `secrets` e `dead_code` entram só por `--gates` no `bob check`. Não há comando `bob coverage`, `bob test_smells`, `bob cognitive`, `bob supply`, `bob security`, `bob typing`, `bob secrets` nem `bob dead_code`.

`bob check` sem `mutate` na lista não roda mutação. `bob check --gates mutate` e `bob mutate` rodam.

Quando mais de um gate devolve código, fica o maior (`_worse` em `check.py`).

## Outros comandos de medição

`crap`, `dry`, `deps` e `mutate` chamam o mesmo `run_check`, cada um com um gate, e gravam os dois formatos (`fmt="both"` no `cli.py`). Eles aceitam `--base`, `--config`, `--out` e `--lang`.

| Comando | Flags a mais |
|---|---|
| `bob crap` | `--threshold` substitui `crap.max_per_function` nesta execução e segue a mesma regra, um número finito maior que `0`. `--coverage-file` aponta um arquivo de cobertura já gerado |
| `bob dry` | `--dry-fail` e `--max-new-clones`, as mesmas de `bob check` |
| `bob deps` | nenhuma além das compartilhadas |
| `bob mutate` | `--max-workers` vira `--max-children` do mutmut (`src/bob_quality/mutmut_tool.py`). `--since-last-run` não muda a medição: a ajuda diz que reusar o cache já é o padrão. A flag só entra na linha `reproduce` do relatório quando foi passada |

`--max-workers` aceita um inteiro de 1 a 64. O teto é `_WORKER_CEILING` em `src/bob_quality/cli.py`. O mutmut abre um pool com esse número de processos antes do primeiro mutante. Cada processo segura dois descritores de arquivo. Com 256 arquivos abertos, o limite padrão do macOS, 128 processos já falham. 64 é a maior potência de 2 que ainda abre ali.

## bob doctor

Lista cada pino de `src/bob_quality/doctor.py` com a versão esperada e a encontrada. Sai com `0` quando cada pino está satisfeito e com `4` quando algum falta ou fica fora do pino, e imprime o comando de instalação. Não grava `.bob/report.md`. Um sufixo `-rc` na versão encontrada fica de fora do pino e o doctor sai com `4`.

Pinos, na ordem do código: lizard 1.24.1, deptry 0.25.1, coverage.py 7.16.2, node `>=22.14.0 <23`, c8 12.0.0, vitest 5.0.3, jscpd 5.4.1, eslint 9.39.5, eslint-plugin-sonarjs 2.0.4, mutmut 3.8.0, complexipy 8.0.1, import-linter 2.15, grimp 3.17, diff-cover 10.6.0, bandit 1.9.4, dependency-cruiser 18.5.0, gitleaks 8.30.1, vulture 2.16, knip 6.41.0, stryker 10.0.0, stryker-vitest-runner 10.0.0. A versão esperada de uma ferramenta Python vem do Requires-Dist instalado do `bob-quality`. O Semgrep 1.180.0 não entra nessa lista. O gate de security chama `uvx --from semgrep==1.180.0`.

`bob doctor --install` roda `npm ci` no pacote instalado e depois imprime o mesmo relatório. Ver [Instalação](instalacao.md#pacote-pip-bob-quality).

`doctor` também passa por `_blocked_config`: um `bob.yaml` ou um `.bob/waivers.yaml` inválido no diretório atual faz o doctor sair com `4` antes do relatório de versões. Ver [Exit codes](exit-codes.md#exit-4).

## bob waive

```bash
bob waive <arquivo::função|Alvo> --reason "uma linha"
```

Grava ou substitui uma entrada em `.bob/waivers.yaml` e sai com `0`. Não gera `report.md`. Os campos e as regras de formato estão em [Waivers](configuracao.md#bobwaiversyaml).

O alvo é `arquivo::função`, que dispensa todo sobrevivente da função, ou o valor da coluna Alvo do último relatório de mutação, que dispensa um sobrevivente. O comando lê os sobreviventes de `.bob/mutation-cache.json` e `.bob/stryker-mutants.json`. Rode a mutação antes.

`--reason` é obrigatório na prática: ausência, string vazia ou quebra de linha levantam `WaiverError` e o processo sai com `4`. Essa mensagem segue o idioma resolvido (`waiver sem motivo: informe --reason com uma linha` em `pt-BR`). Um alvo vazio sai com `4` e `waiver sem alvo`. Um alvo que nenhum sobrevivente tem, como o id do mutante ou o nome nu da função, sai com `4` e `nenhum sobrevivente casa com <alvo>: copie arquivo::função ou um Alvo do último relatório de mutação`. Nos três casos nada é gravado.

Um `.bob/waivers.yaml` que já está inválido é recusado antes, em inglês no stderr, também com `4`, e o arquivo não é reescrito. Ver [Exit codes](exit-codes.md#exit-4).

## Idioma (`--lang`)

Vale a primeira fonte definida (`resolve_language` em `src/bob_quality/config.py`, chamada pela CLI e pelo comentário da Action):

1. `--lang en` ou `--lang pt-BR`, antes ou depois do comando.
2. A variável `BOB_LANG`.
3. A chave `language` no `bob.yaml` (ou no arquivo de `--config`).
4. `en`.

A caixa importa. `pt-br` é inválido. Os valores aceitos são os de `LANGUAGES` em `messages.py`: `en` e `pt-BR`.

Um `--lang` ou `BOB_LANG` vazio é inválido. A CLI sai com `4`, imprime `invalid language: "" (use en or pt-BR)` no stderr e não grava relatório. Uma chave `language` vazia no YAML continua ausente.

Idioma inválido, `language` que não é string, YAML que não é mapeamento, erro de sintaxe no `bob.yaml` e chave com tipo errado também saem com `4` em inglês no stderr, mesmo que se pretendesse `pt-BR`, e não gravam relatório. O mesmo vale para `paths`, `languages`, `base`, `dependencies` e as listas `include` e `exclude`, em `check`, `doctor`, `waive` e nos outros comandos. Uma entrada de `paths.include` que não existe no disco segue o mesmo caminho. O stderr cita o arquivo e cada entrada ausente, como `bob.yaml: paths.include does not exist: missing-root`. Um `paths.include` omitido ou vazio continua `src` e não é verificado.

Uma chave `duplication` inválida também sai com `4`, em inglês no stderr, sem gravar relatório. `reject_config_types` percorre o schema inteiro, inclusive `duplication`. O [CHANGELOG.md](../CHANGELOG.md) descreve esse caso. Uma chave desconhecida segue o mesmo caminho. Ver [Exit codes](exit-codes.md#exit-4).

O que muda com o idioma: mensagens da CLI, texto do `--help`, `bob doctor`, o hook (porque ele chama a CLI), `.bob/report.md`, a nota de truncamento do comentário da Action e os erros desse comentário (repo, pr ou token ausente, relatório ausente, lista de comentários inválida). O `.bob/report.json` é o mesmo arquivo nos dois idiomas (`JSON_LANGUAGE = "en"` em `report.py`). Detalhe em [Relatórios](relatorios.md#o-que-não-muda-com-o-idioma).

No CI, `language: pt-BR` no `bob.yaml` ou `BOB_LANG: pt-BR` no `env` do job. O input `language` da Action repassa a escolha ao `bob check` e ao comentário. Input vazio deixa `BOB_LANG` e o `bob.yaml`.

## O que cada superfície roda

| Superfície | Gates | Onde está |
|---|---|---|
| `bob check` sem `--gates` | `crap,dry,deps` | `DEFAULT_GATES` |
| Hook `pre-push` | `crap,dry,deps` | `src/bob_quality/hooks/pre-push` |
| GitHub Action, input `gates` omitido | `crap,dry,deps,mutate` | `.github/actions/bob/action.yml` |

A [SPEC](SPEC.md) diz que o hook local executa `crap,dry,deps` e que no CI o `check` executa todos. O script do hook passa `crap,dry,deps`. O padrão da CLI é o mesmo trio; o CI pede `mutate` pelo input da Action, não porque o padrão da CLI tenha mudado. A skill `skills/bob-check/SKILL.md` cita esses dois comandos.

## bob report

`build_parser` registra `report` junto de `check`, `crap`, `dry`, `deps`, `mutate`, `waive` e `doctor`. A interface é a da [SPEC](SPEC.md):

```text
bob report  [--in .bob/] [--out .bob/report.md]
```

`--in` é a pasta que já contém `report.json`. O padrão é `.bob/`. `--out` é o arquivo Markdown. O padrão é `.bob/report.md`. O comando não mede de novo. Ele lê o JSON e grava o Markdown no idioma da saída, escolhido por `--lang`, por `BOB_LANG` ou por `language` no `bob.yaml`. O processo sai com o `exit_code` gravado nesse JSON. O inteiro tem de ser 0, 1, 2, 3 ou 4.

Se o arquivo falta, se o texto não é JSON, ou se o formato é inválido, o comando sai com 4. O stderr fica em inglês. O comando não grava o `--out` e não trunca um arquivo que já estava lá. Um uso inválido da linha de comando também sai com 4 e não grava relatório. O preflight de `bob.yaml` e de `.bob/waivers.yaml` é o mesmo dos outros comandos.

O `report.json` fica em inglês. `--lang pt-BR` traduz os títulos que o catálogo conhece. Um motivo de gate, ou o nome de uma regra, permanece em inglês quando o JSON já o gravou assim. Para gerar os dois arquivos durante a medição, use `bob check --format md` ou `--format both`.
