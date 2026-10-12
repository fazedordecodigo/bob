# Configuração

[Índice](README.md) · [CLI](cli.md) · [Gates](gates.md) · [Relatórios](relatorios.md) · [SPEC](SPEC.md)

Dois arquivos. `bob.yaml` na raiz do repositório (ou o caminho de `--config`) define base, idiomas, caminhos e limiares. `.bob/waivers.yaml` guarda os waivers de mutação e entra no git junto com o código.

## bob.yaml

Se o arquivo não existe e `--config` não foi passado, `load_config` devolve os padrões de `Config` em `src/bob_quality/config.py`. Se `--config` aponta para um arquivo que não existe, a execução sai com `4`, a mensagem em inglês no stderr cita o caminho, e nada é gravado.

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
| `crap.scope` | string | `changed` | `changed` olha só funções alteradas. Qualquer outro texto faz toda função medida contar (`crap_verdict` em `core.py`) |
| `duplication.min_tokens` | inteiro | `50` | Mínimo de tokens do jscpd |
| `dependencies.python` | string | `.importlinter` | Config do import-linter |
| `dependencies.typescript` | string | `.dependency-cruiser.cjs` | Config do dependency-cruiser |

Um tipo errado sai com `4`. A mensagem em inglês no stderr cita o arquivo e a chave, por exemplo `bob.yaml: crap must be a mapping` ou `bob.yaml: crap.max_per_function must be a number`. Isso vale para `check`, `doctor`, `waive` e os outros comandos, e nenhum deles grava arquivo nesse caso. Ver [Exit 4](exit-codes.md#exit-4).

`duplication` que não é mapeamento, ou `min_tokens` que não vira inteiro, é o caso do [CHANGELOG](../CHANGELOG.md): o relatório de erro é gravado no idioma já configurado.

### languages

A [SPEC](SPEC.md) escreve `languages: [python, typescript]` com o comentário “autodetect se omitido”. Em `config.py`, a chave ausente, nula ou o arquivo ausente viram `["python"]`. Não há função de autodetecção no módulo. Para medir TypeScript é preciso listar `typescript` (e `python` também, num monorepo misto).

O gate DRY mapeia `typescript` para os formatos `typescript` e `javascript` do jscpd (`dry_gate.py`).

### Chaves que o loader recusa

O `_SCHEMA` em `src/bob_quality/config.py` aceita `base`, `language`, `languages`, `paths.include`, `paths.exclude`, `crap.max_per_function`, `crap.scope`, `duplication.min_tokens`, `dependencies.python` e `dependencies.typescript`. `_reject_unknown` recusa qualquer outra chave: exit `4`, mensagem em inglês no stderr, nenhum arquivo gravado.

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

Um `id` repetido substitui a entrada antiga (`add_waiver` filtra o id e acrescenta a nova no fim).

Na hora de aplicar, um waiver casa com um mutante se o `id` é igual ao id do mutante, ao nome da função, a `arquivo:função` ou a `arquivo::função` (`_matching_reason`).

### Arquivo inválido

Estes casos saem com `4`, em inglês no stderr, citando `.bob/waivers.yaml` e o campo. Nada é gravado em `report.md` ou `report.json`, e o arquivo permanece como está. `check`, `doctor` e `waive` passam por `reject_waiver_syntax` antes do comando:

- erro de sintaxe YAML (a mensagem inclui o erro do parser);
- o topo não é um mapeamento;
- `waivers` não é uma lista;
- um item não é um mapeamento;
- `id`, `reason`, `author` ou `date` ausente ou não é string;
- `reason` vazio ou com quebra de linha.

Exemplo de mensagem, da spec e do CHANGELOG: `.bob/waivers.yaml: waivers[0].reason must be a string`.

O agente grava o waiver. A pessoa aprova no review do pull request. A skill `skills/harden/SKILL.md` descreve quando registrar em vez de enfraquecer o código de produção. Todo waiver aparece na seção `## Waivers` do relatório quando a mutação rodou ou quando já existe waiver. Ver [Relatórios](relatorios.md).
