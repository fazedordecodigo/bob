# Configuração

[Índice](README.md) · [CLI](cli.md) · [Gates](gates.md) · [Relatórios](relatorios.md) · [SPEC](SPEC.md)

Dois arquivos. `bob.yaml` na raiz do repositório (ou o caminho de `--config`) define base, idiomas, caminhos e limiares. `.bob/waivers.yaml` guarda os waivers de mutação e entra no git junto com o código.

## bob.yaml

Se o arquivo não existe e `--config` não foi passado, `load_config` devolve os padrões de `Config` em `src/bob_quality/config.py`. Se `--config` aponta para um arquivo que não existe, `check`, `crap`, `dry`, `deps` e `mutate` saem com `4`, gravam `.bob/report.md` e `.bob/report.json`, e deixam o stdout e o stderr vazios. Cada gate pedido fica `not_run`. O `reason` do JSON é `config file not found: <caminho>`, com o caminho que `load_config` recebeu. O `report.md` segue o idioma da saída. `doctor` e `waive` não aceitam `--config`.

Padrões quando não há `bob.yaml`:

```yaml
base: origin/main
language: en          # ausente no objeto até alguém definir; o efetivo é en
languages: [python]
paths:
  include: [src]
  exclude: [tests, node_modules, dist]
crap:
  max_per_function: 10
  scope: changed
duplication:
  min_tokens: 50
dependencies:
  python: .importlinter
  typescript: .dependency-cruiser.cjs
```

`language: en` no bloco acima é o resultado da resolução, não uma chave que o arquivo vazio precise ter. Sem chave, `configured_language` devolve `None` e a CLI usa `en`.

O `bob.yaml` deste repositório é mais curto: `base`, `languages: [python]`, `paths.include: [src]`, `paths.exclude: [tests]`, `crap.max_per_function: 10`, `crap.scope: changed`. O que falta continua no padrão do código.

### Chaves que o código lê

| Chave | Tipo | Padrão | Uso |
|---|---|---|---|
| `base` | string | `origin/main` | Ref do diff, se `--base` não vier |
| `language` | `en` ou `pt-BR`, ou vazio | ausente → `en` | Idioma. Ver [CLI](cli.md#idioma---lang) |
| `languages` | lista de strings | `[python]` | Quais probes rodam |
| `paths.include` | lista de strings | `[src]` | Raízes medidas |
| `paths.exclude` | lista de strings | `[tests, node_modules, dist]` | Fora da medição |
| `crap.max_per_function` | número (bool não vale) | `10` | Limite. CRAP maior ou igual reprova |
| `crap.scope` | string | `changed` | Só `changed` ou `all`. Outro texto sai com `4` |
| `duplication.min_tokens` | inteiro maior que 0 | `50` | Mínimo de tokens do jscpd |
| `dependencies.python` | string | `.importlinter` | Config do import-linter |
| `dependencies.typescript` | string | `.dependency-cruiser.cjs` | Config do dependency-cruiser |
| `test_smells` | `true` | `true` | Aceito pelo loader. O gate não lê o campo |
| `secrets` | mapeamento vazio | ausente | Não liga o gate e não tem filhos |
| `dead_code.min_confidence` | inteiro de 0 a 100, ou ausente | ausente | Confiança mínima do vulture. Ausente ou nulo não passa `--min-confidence`. `0` passa a flag. O knip ignora a chave |

Um tipo errado sai com `4`. A mensagem em inglês no stderr cita o arquivo e a chave, por exemplo `bob.yaml: crap must be a mapping` ou `bob.yaml: crap.max_per_function must be a number`. Isso vale para `check`, `doctor`, `waive` e os outros comandos, e nenhum deles grava arquivo nesse caso. Ver [Exit 4](exit-codes.md#exit-4).

Uma chave repetida no mesmo mapeamento sai com `4`. O stderr fica em inglês e cita a chave e a linha, como `invalid YAML in bob.yaml: found duplicate key 'scope' on line 3`. Uma chave escrita nesse mapeamento ainda pode substituir um valor mesclado com `<<`.

`duplication` que não é mapeamento, ou `min_tokens` que não é um inteiro maior que 0, sai com `4`. A mensagem em inglês no stderr cita o arquivo e a chave, e nada é gravado. O [CHANGELOG](../CHANGELOG.md) descreve esse caso.

`test_smells` omitido, `null` ou `true` guarda `True`. `false`, um mapeamento (`{}` ou com filhos) e qualquer outro valor saem com `4`. O stderr é `bob.yaml: test_smells accepts only true`. Nada é gravado. O gate `test_smells` não consulta o campo.

### languages

`languages` omitido ou nulo (`languages:` ou `languages: null`) vira `["python"]`, o padrão de `Config`. Não há autodetecção. O mesmo vale quando o arquivo `bob.yaml` não existe e `--config` não foi passado. Para medir TypeScript é preciso listar `typescript` (e `python` também, num monorepo misto).

Uma lista vazia ou um item repetido sai com 4. Uma chave ausente ou nula continua `[python]`.

O gate DRY mapeia `typescript` para os formatos `typescript` e `javascript` do jscpd (`dry_gate.py`).

### Chaves que o loader recusa

O `_SCHEMA` em `src/bob_quality/config.py` aceita `base`, `language`, `languages`, `paths.include`, `paths.exclude`, `crap.max_per_function`, `crap.scope`, `duplication.min_tokens`, `dependencies.python`, `dependencies.typescript`, `test_smells`, `secrets` e `dead_code.min_confidence`. `_reject_unknown` recusa qualquer outra chave: exit `4`, mensagem em inglês no stderr, nenhum arquivo gravado.

`secrets` ausente, `secrets:`, `secrets: null` e `secrets: {}` são o mesmo mapeamento vazio. A chave não tem limiar nem filhos e não liga o gate. O gate só roda com `--gates secrets`. `secrets: true` e `secrets: {threshold: 1}` saem com `4`, em inglês no stderr, e nada é gravado.

`dead_code.min_confidence` ausente, nulo, ou o bloco `dead_code` vazio deixam o campo sem valor. `0` e `100` são valores presentes. `101`, `-1`, `true` e `1.5` saem com `4` em `check`, `doctor` e `waive`. A mensagem em inglês cita `bob.yaml` e `dead_code.min_confidence`. Nada é gravado em `.bob/`.

Estas não entram no schema:

- `mutation`. O erro é `bob.yaml: unknown key mutation`, também quando o bloco traz `require_zero_unwaived_survivors`, `scope` ou `differential`.
- `duplication.tool`. O erro é `bob.yaml: unknown key duplication.tool`.
- `duplication.new_clones`. O erro é `bob.yaml: unknown key duplication.new_clones`.
- `dependencies.violation`. O erro é `bob.yaml: unknown key dependencies.violation`.

O exemplo de `bob.yaml` na [SPEC](SPEC.md) e nos READMEs não as inclui. Sobrevivente sem waiver sai com `3`, a mutação reusa `.bob/mutation-cache.json`, clone novo é aviso e violação no diff sai com `1`, sem chave para desligar isso. `tests/test_invalid_config.py` cobre a recusa.

## .bob/waivers.yaml

O caminho é sempre `<cwd>/.bob/waivers.yaml` (`waivers_path`). `bob waive` cria a pasta se precisar.

Formato que `load_waivers` aceita:

```yaml
waivers:
  - id: app.billing.x_charge__mutmut_2
    reason: equivalente; o limite inclusivo não muda o contrato.
    author: Ada
    date: '2026-10-11'
```

| Campo | Origem em `bob waive` | Regra |
|---|---|---|
| `id` | o argumento (id do mutante ou nome da função), com `strip` | string não vazia |
| `reason` | `--reason`, uma linha, com `strip` | string; vazio ou com `\n` / `\r` é rejeitado |
| `author` | `git config user.name`; se falhar ou vier vazio, `$USER`; senão `unknown` | string não vazia no arquivo |
| `date` | data UTC de hoje, `YYYY-MM-DD` | string não vazia |

`bob waive` de um id que já existe uma vez substitui essa linha e sai com 0 quando o resto do arquivo é válido. Um arquivo que já contém duas entradas com o mesmo id sai com 4, em inglês no stderr, e não é reescrito.

Na hora de aplicar, um waiver casa com um mutante se o `id` é igual ao id do mutante, ao nome da função, a `arquivo:função` ou a `arquivo::função` (`_matching_reason`).

### Arquivo inválido

Estes casos saem com `4`, em inglês no stderr, citando `.bob/waivers.yaml` e o campo. Nada é gravado em `report.md` ou `report.json`, e o arquivo permanece como está. `check`, `doctor` e `waive` passam por `reject_waiver_syntax` antes do comando:

- erro de sintaxe YAML (a mensagem inclui o erro do parser);
- chave repetida no mesmo mapeamento, como `invalid YAML in .bob/waivers.yaml: found duplicate key 'id' on line 3`;
- o topo não é um mapeamento;
- `waivers` não é uma lista;
- um item não é um mapeamento;
- `id`, `reason`, `author` ou `date` ausente ou não é string;
- `reason` vazio ou com quebra de linha;
- uma chave desconhecida dentro da entrada;
- um id repetido.

Exemplo de mensagem, da spec e do CHANGELOG: `.bob/waivers.yaml: waivers[0].reason must be a string`.

O agente grava o waiver. A pessoa aprova no review do pull request. A skill `skills/harden/SKILL.md` descreve quando registrar em vez de enfraquecer o código de produção. Todo waiver aparece na seção `## Waivers` do relatório quando a mutação rodou ou quando já existe waiver. Ver [Relatórios](relatorios.md).
