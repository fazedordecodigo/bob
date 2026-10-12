# Exit codes

[Índice](README.md) · [CLI](cli.md) · [Gates](gates.md) · [Relatórios](relatorios.md) · [SPEC](SPEC.md)

Os códigos estão em `src/bob_quality/exit_codes.py`. A [SPEC](SPEC.md) os inspira no mutator. `bob check` fica com o maior código entre os gates (`_worse`).

| Código | Nome no código | Quando sai |
|---|---|---|
| `0` | `PASSED` | Todo gate que rodou passou, ou só avisou |
| `1` | `GATE_FAILED` | CRAP de uma função no escopo ≥ limite, ou violação de dependência no diff |
| `2` | `BASELINE_BROKEN` | A suíte quebra antes da medição |
| `3` | `UNWAIVED_SURVIVOR` | Mutante `survived` sem waiver |
| `4` | `CONFIG_OR_TOOL` | Configuração inválida ou ferramenta que impede a medição |

## Exit 0

Todos os gates pedidos que de fato rodaram passaram. Aviso também termina em `0`: clone novo, mutante `no_coverage` sem sobrevivente sem waiver, e TypeScript pulado num monorepo quando o que foi medido cabe no limite. O veredito do gate fica ⚠️. O exit continua `0`.

Um nome de gate desconhecido é `not_run` e contribui `0`.

`bob waive` com motivo válido sai com `0` e só escreve `.bob/waivers.yaml`.

`bob doctor` sai com `0` quando cada pino coincide com a versão encontrada.

## Exit 1

`crap_verdict` devolve `1` quando alguma função considerada tem CRAP maior ou igual a `crap.max_per_function` (ou a `--threshold`). O motivo traz os nomes no formato `função@arquivo:linha`.

`deps_verdict` devolve `1` quando alguma violação está marcada `in_diff`. O motivo traz `origem → destino`.

DRY não devolve `1`. Mutação não devolve `1`: sobrevivente sem waiver é `3`.

Se o CRAP falha (`1`) e a mutação também (`3`), o `check` sai com `3`.

## Exit 2

O gate `crap` roda pytest (Python) ou vitest (TypeScript) para medir cobertura. No Python, código de pytest fora de `0` e de `5` é baseline quebrada (`pytest_passed` em `exit_codes.py`). O comentário nesse módulo diz que o `5` é “nenhum teste coletado” e também passa. No TypeScript, `vitest_code != 0` em `typescript_probe.py` é exit `2`. Ausência de `coverage-final.json` depois de um vitest com código `0` é exit `4` (`probe.c8_no_report`).

O gate `mutate` também exige a baseline. Se o `crap` rodou antes na mesma execução, o código do pytest é reaproveitado. Sozinho, `bob mutate` chama `pytest_exit_code`. Falha: status `not_run` e exit `2`.

O [AGENTS.md](../AGENTS.md) registra que o exit `2` também sai do `bob check` padrão, porque o padrão inclui `crap`.

## Exit 3

Só o gate `mutate`. Em `_finish`, a lista que bloqueia são os mutantes com status `survived` e waiver vazio. Um ou mais: exit `3` e status `failed`. O motivo lista `função@arquivo:linha`.

Waiver casado por id, nome, `arquivo:função` ou `arquivo::função` tira o mutante dessa lista. `killed`, `timeout` e `no_coverage` não entram nela. `no_coverage` pode deixar o gate em `warn` com exit `0` ou, se já existe sobrevivente sem waiver, o exit continua `3` e o aviso de contagem vai no relatório.

A fase 2 da decisão 11 da spec ( `no_coverage` no diff falhando com `3`) não é o comportamento de `_finish`.

## Exit 4

Há dois jeitos de chegar no `4`.

### Antes de medir, sem gravar relatório

`cli.main` devolve `4` sem escrever `report.md`, `report.json` nem alterar `waivers.yaml` em dois casos distintos.

Um uso inválido da linha de comando (comando ausente, comando desconhecido, flag ilegal, valor fora das escolhas, valor fora da regra de `--threshold` ou de `--max-workers`) imprime o texto de uso do argparse no stderr. Esse texto não menciona baseline. A ajuda (`-h`, `--help`) sai com `0`. Isso não é o exit `2`. A regra de `--threshold` e de `--max-workers` está em [Outros comandos de medição](cli.md#outros-comandos-de-medição).

A configuração inválida imprime inglês no stderr quando:

- `--lang` ou `BOB_LANG` é vazio ou não é `en` nem `pt-BR`;
- `language` no YAML não é string ou não é um desses dois valores;
- o YAML do `bob.yaml` tem erro de sintaxe ou não é um mapeamento;
- uma chave lida por `_parsed` tem o tipo errado (`base`, `languages`, `paths`, `include`, `exclude`, `crap`, `max_per_function`, `scope`, `dependencies`, `python`, `typescript`);
- `.bob/waivers.yaml` existe e o YAML é inválido ou o formato não é o da [Configuração](configuracao.md#arquivo-inválido). A mensagem cita o caminho e o campo.

`--config` apontando para um arquivo que não existe não entra nessa barreira. `reject_config_types` volta sem erro se o arquivo não existe. `load_config` levanta `ConfigError`, e `run_check` grava um relatório de falha precoce (`_fail_early`) com exit `4`. O stdout e o stderr ficam vazios. Cada gate pedido fica `not_run`. O `reason` do `report.json` é `config file not found: <caminho>` (inglês). O `report.md` traduz o motivo. O teste `test_check_exits_4_when_config_is_missing` em `tests/test_cli.py` espera os dois arquivos. A flag existe em `check`, `crap`, `dry`, `deps` e `mutate`. `doctor` e `waive` não a aceitam. A decisão 12 da [SPEC](SPEC.md) não cobre esse caso.

Erro de sintaxe, tipo errado e waiver inválido são barrados em `_language` ou `_blocked_config`, que imprimem no stderr e retornam `4` sem chamar `write_report`.

`duplication` inválida entra na mesma barreira que as outras chaves: `reject_config_types` chama `_config_from_file`, o stderr fica em inglês e nenhum relatório é gravado. A recusa cobre um valor que não é mapeamento e um `min_tokens` que não é um inteiro maior que 0. Uma chave desconhecida, inclusive `mutation`, `duplication.tool`, `duplication.new_clones` e `dependencies.violation`, sai do mesmo jeito. O [CHANGELOG.md](../CHANGELOG.md) descreve esses casos.

Um `--reason` ausente no `bob waive` também é `4`, e essa frase segue o idioma da CLI, porque acontece dentro de `_waive_command` depois da barreira do arquivo.

### Durante a medição, com relatório

Se a ferramenta falta no meio do gate (lizard, mutmut, import-linter, dependency-cruiser, Node num repo só TypeScript, git que falha ao calcular o diff), o gate fica `not_run` e o exit é `4`. O mesmo exit `4` vale quando o JSON do dependency-cruiser não é um objeto ou não traz a lista `violations`, e quando a última linha `Contracts:` do import-linter com exit 0 não é `N kept, 0 broken.` `write_report` grava `.bob/report.md` e `report.json` com esse código. `GitError` em `_open` segue o mesmo relatório precoce.

`bob doctor` com pino ausente ou versão diferente sai com `4` no stdout do próprio doctor, sem relatório em `.bob/`.

Num monorepo com Python e TypeScript, Node ausente não usa este código para o CRAP e para deps: Python segue, TypeScript entra como aviso, e o exit é o do que foi medido (`0` ou `1`). DRY sem Node é `not_run` com `0`. Ver [Monorepo e Node ausente](gates.md#monorepo-e-node-ausente).
