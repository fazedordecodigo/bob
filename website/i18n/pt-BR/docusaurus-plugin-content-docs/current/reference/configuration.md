# Schema de configuração

[Índice](../README.md) · [Configuração](../guides/configuration.md) · [CLI](cli.md) · [Códigos de saída](../exit-codes.md)

`load_config` em `src/bob_quality/config.py` lê `bob.yaml`, ou o arquivo que `--config` nomeia. O objeto é `Config`. As chaves abaixo são as que `_SCHEMA` aceita. Qualquer outra chave sai com `4` com stderr em inglês (`file.unknown_key`) e não grava nada.

## Padrões

Estes valores valem quando a chave é omitida. `language: en` em prosa é o resultado da resolução, não uma chave que um arquivo vazio tem de conter. Sem a chave, `resolve_language` devolve `en`.

| Chave | Tipo | Padrão | Uso |
|---|---|---|---|
| `base` | string | `origin/main` | Ref do diff quando `--base` é omitido. Vazio conta como não definido. |
| `language` | `en` ou `pt-BR`, ou vazio | não definido, então `en` | Idioma da saída. Vazio conta como não definido. |
| `languages` | lista de `python` e `typescript` | `[python]`, ou detectado | Quais linguagens os gates medem. |
| `paths.include` | lista de strings | `[src]` | Raízes que são medidas. |
| `paths.exclude` | lista de strings | `[tests, node_modules, dist]` | Ficam fora da medição. |
| `crap.max_per_function` | número finito maior que 0 | `10` | Uma função com CRAP neste valor ou acima falha. Um bool não é um número. |
| `crap.scope` | `changed` ou `all` | `changed` | `changed` considera funções alteradas. `all` considera toda função medida. Qualquer outra string sai com `4`. |
| `cognitive.max_per_function` | inteiro maior que 0 | `15` | Uma função alterada com este score ou acima avisa. O exit permanece `0`. `null` é recusado. |
| `duplication.min_tokens` | inteiro maior que 0 | `50` | Mínimo de tokens do jscpd. `null` é recusado. |
| `duplication.new_clones` | `warn` ou `fail` | `warn` | Modo do DRY. Vazio conta como não definido. |
| `duplication.max_new_clones` | inteiro ≥ 0 | `0` | Teto no modo fail. Um bool não é um inteiro. |
| `duplication.min_similarity` | número finito de 0 a 100 | `0` | Similaridade mínima, em percentual, para um clone novo contar. |
| `duplication.min_lines` | inteiro ≥ 0 | `0` | Mínimo de linhas para um clone novo contar. |
| `coverage.min_percent` | número finito de 0 a 100 | `80` | Piso do gate de cobertura do diff. Um percentual igual ao piso passa. `null` é recusado. |
| `dependencies.python` | string | `.importlinter` | Caminho da config do import-linter. |
| `dependencies.typescript` | string | `.dependency-cruiser.cjs` | Caminho da config do dependency-cruiser. |
| `test_smells` | só `true` | `true` | O loader aceita `true`. O gate não lê o campo. |
| `typing` | mapeamento sem filhos | não definido | Aceito e ignorado. Não liga o gate de typing. |
| `secrets` | mapeamento sem filhos | não definido | Sem limiar e sem filhos. Não liga o gate de secrets. |
| `churn.window_days` | inteiro maior que 0 | `90` | Janela do churn, terminando na própria data do commit. |
| `supply.osv_fail_severities` | lista de `HIGH` e `CRITICAL` | `[HIGH, CRITICAL]` | Severidades de advisory que bloqueiam. `MODERATE` e `LOW` não são membros desta lista. |
| `supply.timeout_seconds` | inteiro maior que 0 | `30` | Timeout de cada chamada HTTP e de cada processo no gate de supply. |
| `security.fail_severities` | lista de strings | `[HIGH, CRITICAL, ERROR]` | Severidades que falham o gate de segurança. |
| `dead_code.min_confidence` | inteiro de 0 a 100, ou não definido | não definido | `--min-confidence` do Vulture. Não definido ou null não passa a flag. `0` passa. O knip ignora a chave. |

Gates opt-in não são ligados pela presença das chaves deles. O comando é `bob check --gates <name>`. Ver [Gates e waivers](../guides/gates-and-waivers.md).

## Linguagens e caminhos

`languages` omitido ou null é detectado. A mesma detecção roda quando `bob.yaml` falta e `--config` não foi passado. A varredura lê `paths.include`, pula `paths.exclude` e não segue symlinks. `.py` seleciona `python`. `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` e `.cjs` selecionam `typescript`, nessa ordem. Se nenhum desses arquivos existe, o resultado é `[python]`. Uma lista explícita é mantida como foi escrita. Uma lista vazia, ou um item repetido, sai com `4`.

`paths.exclude` casa um prefixo de caminho ou um componente de caminho. Não é um glob. `*.py` não exclui `src/app.py`. `tests` exclui `tests/a.py` e `src/tests/a.py`.

Cada entrada de `paths.include` é resolvida a partir do diretório de trabalho atual. Uma entrada que não está no disco sai com `4`. O stderr em inglês nomeia o arquivo e cada entrada ausente, como em `bob.yaml: paths.include does not exist: missing-root`. Uma lista omitida ou vazia permanece `[src]` e não é conferida. Um caminho que existe como arquivo, não como diretório, passa nesta conferência.

## Valores que saem com 4

Um tipo errado sai com `4`. O stderr em inglês nomeia o arquivo e a chave, como em `bob.yaml: crap must be a mapping` ou `bob.yaml: crap.max_per_function must be a number`. `check`, `doctor`, `waive`, `report` e os outros comandos fazem isso do mesmo jeito. Nenhum deles grava um arquivo neste caso.

Uma chave repetida num mapeamento sai com `4`. O stderr em inglês nomeia a chave e a linha, como em `invalid YAML in bob.yaml: found duplicate key 'base' on line 2`. Uma chave escrita no mapeamento ainda pode sobrepor um valor mesclado com `<<`.

YAML que não é um mapeamento, e YAML com erro de sintaxe, saem com `4`. A mensagem de sintaxe nomeia o arquivo e a primeira linha do parser.

`test_smells` omitido, `null` ou `true` guarda `True`. `false`, um mapeamento e qualquer outro valor saem com `4` com `bob.yaml: test_smells accepts only true`. O gate não lê o campo.

`churn` omitido, `churn: null` e `churn: {}` mantêm 90. `churn.window_days` definido como `null`, um float, um bool, `0` ou um inteiro negativo sai com `4`. Qualquer outra chave `churn.*` é uma chave desconhecida.

`secrets` omitido, `secrets:`, `secrets: null` e `secrets: {}` são o mesmo mapeamento vazio. `secrets: true` e `secrets: {threshold: 1}` saem com `4`.

`typing: {}`, `typing:` e `typing: null` carregam e não guardam campo em `Config`. Uma chave filha sai com `4` com `bob.yaml: unknown key typing.threshold`. Um não mapeamento como `typing: 1` sai com `4` com `bob.yaml: typing must be a mapping`.

Os membros de `security.fail_severities` têm de estar no vocabulário do scanner: `CRITICAL`, `ERROR`, `HIGH`, `INFO`, `LOW`, `MEDIUM`, `UNDEFINED`, `WARNING` (`severity_vocabulary` em `src/bob_quality/security_scanners.py`). Uma palavra fora dessa lista, um item repetido, uma lista vazia ou um valor que não é uma lista de strings sai com `4`. Uma lista omitida ou null permanece `HIGH`, `CRITICAL`, `ERROR`. `[]` não volta ao padrão. `ERROR` não é um alias de `HIGH`.

`supply.osv_fail_severities: [MODERATE]` sai com `bob.yaml: supply.osv_fail_severities[0] must be HIGH or CRITICAL`. Uma lista vazia, um item repetido ou uma string nua também saem com `4`. `supply.timeout_seconds: 0` sai com `bob.yaml: supply.timeout_seconds must be greater than 0`.

`dead_code.min_confidence` de `101`, `-1`, `true` ou `1.5` sai com `4` em `check`, `doctor` e `waive`. O stderr em inglês nomeia `dead_code.min_confidence`. Nada é gravado em `.bob/`.

`coverage.min_percent` abaixo de 0, acima de 100, não finito ou um bool sai com `4`.

## Chaves que o loader recusa

`_reject_unknown` recusa toda chave que não está na tabela acima. Estas três aparecem em notas antigas e são recusadas:

- `mutation`, inclusive `require_zero_unwaived_survivors`, `scope` ou `differential`. O erro é `bob.yaml: unknown key mutation`.
- `duplication.tool`. O erro é `bob.yaml: unknown key duplication.tool`.
- `dependencies.violation`. O erro é `bob.yaml: unknown key dependencies.violation`.

Um sobrevivente sem waiver ainda sai com `3`, a mutação ainda reusa `.bob/mutation-cache.json`, e uma violação de dependência no diff ainda sai com `1`. Não há chave para desligar isso. `tests/test_invalid_config.py` cobre a recusa.

O esboço de configuração da spec e o exemplo do README não listam toda chave da tabela acima. Esta página lista as chaves que o loader lê.
