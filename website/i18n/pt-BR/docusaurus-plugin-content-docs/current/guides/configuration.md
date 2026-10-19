# Configuração

[Índice](../README.md) · [Schema de configuração](../reference/configuration.md) · [Gates e waivers](gates-and-waivers.md) · [Códigos de saída](../exit-codes.md)

Dois arquivos. `bob.yaml` na raiz do repositório, ou o caminho em `--config`, define a ref base, o idioma da saída, os caminhos e os limites. `.bob/waivers.yaml` guarda os waivers e é versionado com o código.

## bob.yaml

Se o arquivo falta e `--config` não foi passado, `load_config` devolve os padrões de `Config` (`src/bob_quality/config.py`) e detecta as linguagens a partir da árvore. Se `--config` aponta para um arquivo que não existe, `check`, `crap`, `dry`, `deps` e `mutate` saem com `4`. O stderr em inglês nomeia o caminho (`config file not found: <path>`). Nada é gravado. `doctor`, `waive` e `report` não aceitam `--config`.

Um arquivo que só define o que este repositório define (`base`, `languages`, `paths` e `crap`) deixa toda outra chave no padrão do código. A lista completa de chaves, os tipos e os valores que saem com `4` estão no [schema de configuração](../reference/configuration.md).

```yaml
base: origin/main
languages: [python]
paths:
  include: [src]
  exclude: [tests, node_modules, dist]
crap:
  max_per_function: 10
  scope: changed
duplication:
  new_clones: warn
  max_new_clones: 0
```

`crap.scope` é `changed` ou `all`. Com `changed`, só funções alteradas podem falhar o gate de CRAP. Com `all`, toda função medida pode falhá-lo. Qualquer outra string sai com `4`. O [ADR 0002](adr/0002-o-diff-filtra-o-veredito.md) descreve uma regra anterior na qual qualquer outra string não vazia contava toda função medida. O loader na `main` aceita só `changed` e `all`.

`duplication.new_clones` é `warn` (o padrão) ou `fail`. Em `warn`, um clone novo permanece um aviso e o exit permanece `0`. Em `fail`, o gate sai com `1` quando os clones novos contados passam de `duplication.max_new_clones` (padrão `0`). `bob dry` e `bob check` aceitam `--dry-fail`, que liga o modo fail nessa execução, e `--max-new-clones N`, que substitui o teto nessa execução. `0` é um teto de verdade. Nenhuma flag força o modo warn.

## Idioma da saída

A primeira fonte que está definida vence (`resolve_language` em `src/bob_quality/config.py`):

1. `--lang en` ou `--lang pt-BR`, antes ou depois do nome do comando.
2. A variável de ambiente `BOB_LANG`.
3. `language` no `bob.yaml`, ou no arquivo de `--config`.
4. `en`.

A caixa importa. `pt-br` é inválido. Os valores aceitos são `en` e `pt-BR` (`LANGUAGES` em `src/bob_quality/messages.py`).

Um `--lang` ou `BOB_LANG` vazio sai com `4`, imprime `invalid language: "" (use en or pt-BR)` no stderr e não grava nada. Uma chave `language` vazia ainda conta como não definida.

No CI, defina `language: pt-BR` no `bob.yaml`, ou `BOB_LANG: pt-BR` no `env` do job. O input `language` da Action define a mesma escolha para `bob check` e para o comentário do pull request. Um input vazio deixa `BOB_LANG` e `bob.yaml` no controle. Ver [CI](ci.md).

`.bob/report.json` tem os mesmos bytes nos dois idiomas. `report.md` e o comentário do pull request seguem o idioma da saída. Ver [report.json](../reference/report-json.md).

## .bob/waivers.yaml

O caminho é sempre `<cwd>/.bob/waivers.yaml`. `bob waive` cria o diretório quando precisa. `write_waivers` é o único escritor.

```bash
bob waive 'src/app/billing.py::charge::if total > limit: -> if total >= limit:' --reason "equivalent; the inclusive limit does not change the contract"
```

`bob waive` aceita só um alvo de um sobrevivente da última execução de mutação, lido de `.bob/mutation-cache.json` (Python) e `.bob/stryker-mutants.json` (TypeScript). Rode a mutação primeiro. O alvo é `file::function`, que dispensa todo sobrevivente dessa função, ou a coluna Target da tabela de sobreviventes, que dispensa um sobrevivente. O id do mutante, um nome de função nu e `file:function` saem com `4` e não gravam nada.

O comando grava estes campos:

| Campo | Fonte | Regra |
|---|---|---|
| `id` | O argumento, sem espaços nas pontas | String não vazia |
| `reason` | `--reason`, uma linha, sem espaços nas pontas | Vazio, ou um valor que contém `\n` ou `\r`, é recusado |
| `author` | `git config user.name`, depois `$USER`, depois `unknown` | String não vazia no arquivo |
| `date` | A data UTC de hoje, `YYYY-MM-DD` | String não vazia |

Um `--reason` ausente, um motivo vazio ou um motivo com quebra de linha sai com `4`. Essa mensagem segue o idioma da saída. Um id que já aparece uma vez é substituído e o comando sai com `0`. Um arquivo que já contém duas linhas com um id sai com `4` e os bytes permanecem.

Ids escritos à mão para os outros gates usam os prefixos de [Gates e waivers](gates-and-waivers.md). O próprio `bob waive` só guarda um alvo de sobrevivente de mutação. Os outros ids são editados no mesmo arquivo. `load_waivers` não confere que um id casa com um sobrevivente. Um id que não casa com nada deixa o achado sem waiver.

Um `waivers.yaml` que é YAML válido com o formato errado sai com `4`. O stderr em inglês nomeia `.bob/waivers.yaml` e o campo, como em `.bob/waivers.yaml: waivers[0].reason must be a string`. Um erro de sintaxe YAML nomeia o arquivo e o erro do parser. Uma chave repetida nomeia a chave e a linha, como em `invalid YAML in .bob/waivers.yaml: found duplicate key 'id' on line 3`. A execução não grava `report.md` nem `report.json`, e o arquivo permanece como está. `check`, `doctor`, `waive` e `report` compartilham este preflight, inclusive quando `--lang` é `pt-BR`.

O agente escreve o waiver. O humano aprova no review do pull request. A skill `skills/harden/SKILL.md` diz quando registrar um waiver em vez de enfraquecer código de produção. Todo waiver aparece na seção `## Waivers` do relatório quando a mutação rodou ou quando um waiver já existe.
