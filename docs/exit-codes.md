# Exit codes

[Índice](README.md) · [CLI](cli.md) · [Gates](gates.md) · [Relatórios](relatorios.md) · [SPEC](SPEC.md)

Os códigos estão em `src/bob_quality/exit_codes.py`. A [SPEC](SPEC.md) os inspira no mutator. `bob check` fica com o maior código entre os gates (`_worse`).

| Código | Nome no código | Quando sai |
|---|---|---|
| `0` | `PASSED` | Todo gate que rodou passou, ou só avisou |
| `1` | `GATE_FAILED` | CRAP de uma função no escopo ≥ limite, violação de dependência no diff, ou, no modo fail do DRY, mais clones novos que `duplication.max_new_clones` |
| `2` | `BASELINE_BROKEN` | A suíte quebra antes da medição |
| `3` | `UNWAIVED_SURVIVOR` | Mutante `survived` sem waiver numa linha do diff, ou `no_coverage` nas funções do diff |
| `4` | `CONFIG_OR_TOOL` | Configuração inválida ou ferramenta que impede a medição |

## Exit 0

Todos os gates pedidos que de fato rodaram passaram. Aviso também termina em `0`: clone novo no modo warn ou até o teto no modo fail, e TypeScript pulado num monorepo quando o que foi medido cabe no limite. O veredito do gate fica ⚠️. O exit continua `0`. `no_coverage` nas funções do diff não é aviso: sai `3`.

Um nome de gate desconhecido é `not_run` e contribui `0`.

`bob waive` com motivo válido e alvo de um sobrevivente do último relatório de mutação sai com `0` e só escreve `.bob/waivers.yaml`.

`bob doctor` sai com `0` quando cada pino coincide com a versão encontrada.

## Exit 1

`crap_verdict` devolve `1` quando alguma função considerada tem CRAP maior ou igual a `crap.max_per_function` (ou a `--threshold`). O motivo traz os nomes no formato `função@arquivo:linha`.

`deps_verdict` devolve `1` quando alguma violação está marcada `in_diff`. O motivo traz `origem → destino`.

DRY devolve `1` só no modo fail (`duplication.new_clones: fail` ou `--dry-fail`), quando a conta de clones novos passa de `duplication.max_new_clones` ou de `--max-new-clones`. O motivo traz a chave e o teto, como `1 new clone exceeds duplication.max_new_clones 0`. No modo warn, o padrão, DRY não devolve `1`. Mutação não devolve `1`: sobrevivente sem waiver é `3`.

Se o CRAP falha (`1`) e a mutação também (`3`), o `check` sai com `3`.

## Exit 2

O gate `crap` roda pytest (Python) ou vitest (TypeScript) para medir cobertura. No Python, código de pytest fora de `0` e de `5` é baseline quebrada (`pytest_passed` em `exit_codes.py`). O comentário nesse módulo diz que o `5` é “nenhum teste coletado” e também passa. No TypeScript, `vitest_code != 0` em `typescript_probe.py` é exit `2`. Ausência de `coverage-final.json` depois de um vitest com código `0` é exit `4` (`probe.c8_no_report`).

O gate `mutate` também exige a baseline. Se o `crap` rodou antes na mesma execução, o código do pytest é reaproveitado. Sozinho, `bob mutate` chama `pytest_exit_code`. Falha: status `not_run` e exit `2`.

O [AGENTS.md](../AGENTS.md) registra que o exit `2` também sai do `bob check` padrão, porque o padrão inclui `crap`.

## Exit 3

Só o gate `mutate`. Em `_finish`, a lista que bloqueia são os mutantes com status `survived`, waiver vazio e linha no lado novo do diff. Sem arquivo, ou com linha menor ou igual a zero, esse sobrevivente também bloqueia. Um ou mais: exit `3` e status `failed`. O motivo lista só esses, no formato `função@arquivo:linha`. Sobrevivente sem waiver fora do diff fica na tabela e não muda o exit.

Waiver casado por `arquivo::função` ou `arquivo::função::<descrição>` tira o sobrevivente dessa lista. O id do mutante e o nome nu da função não casam. Um id que não casa com nada deixa o sobrevivente na lista. No TypeScript, uma linha inserida acima do mutante muda a descrição, e o waiver antigo deixa de casar. Ver a [ADR 0006](adr/0006-chave-estavel-do-waiver.md). `killed` e `timeout` não entram nela. `no_coverage` nas funções do diff também sai `3`, e o waiver não o tira. Se já existe sobrevivente que bloqueia, o motivo do exit continua o do sobrevivente, e a contagem de `no_coverage` vai no relatório.

## Exit 4

Há dois jeitos de chegar no `4`.

### Antes de medir, sem gravar relatório

`cli.main` devolve `4` sem escrever `report.md`, `report.json` nem alterar `waivers.yaml` em dois casos distintos.

Um uso inválido da linha de comando (comando ausente, comando desconhecido, flag ilegal, valor fora das escolhas, valor fora da regra de `--threshold` ou de `--max-workers`) imprime o texto de uso do argparse no stderr. Esse texto não menciona baseline. A ajuda (`-h`, `--help`) sai com `0`. Isso não é o exit `2`. A regra de `--threshold` e de `--max-workers` está em [Outros comandos de medição](cli.md#outros-comandos-de-medição). Um `--max-new-clones` negativo em `bob dry` ou `bob check` também sai com `4`, com `--max-new-clones must be at least 0` em inglês no stderr.

`--config` antes do comando é uso inválido. A última linha do stderr fica em inglês, mesmo com `--lang pt-BR`, como `bob: error: --config goes after the command: bob check --config ci.yaml`. `doctor` não aceita a flag. A última linha é `bob: error: doctor does not accept --config`. `waive` também não aceita. A última linha é `bob: error: waive does not accept --config`.

A configuração inválida imprime inglês no stderr quando:

- `--lang` ou `BOB_LANG` é vazio ou não é `en` nem `pt-BR`;
- `language` no YAML não é string ou não é um desses dois valores;
- o YAML do `bob.yaml` tem erro de sintaxe, repete uma chave no mesmo mapeamento, ou não é um mapeamento. A chave repetida cita a chave e a linha, como `invalid YAML in bob.yaml: found duplicate key 'base' on line 2`;
- uma chave lida por `_parsed` tem o tipo errado (`base`, `languages`, `paths`, `include`, `exclude`, `crap`, `max_per_function`, `scope`, `dependencies`, `python`, `typescript`);
- `.bob/waivers.yaml` existe e o YAML é inválido, repete uma chave, ou o formato não é o da [Configuração](configuracao.md#arquivo-inválido). A mensagem cita o caminho e o campo. A chave repetida cita a chave e a linha, como `invalid YAML in .bob/waivers.yaml: found duplicate key 'id' on line 3`;

`--config` apontando para um arquivo que não existe entra nessa barreira. `reject_config_types` chama `load_config`. O arquivo ausente levanta `ConfigError`, e `_blocked_config` imprime inglês no stderr (`config file not found: <caminho>`) e devolve `4` sem gravar relatório. A flag existe em `check`, `crap`, `dry`, `deps` e `mutate`. `doctor` e `waive` não a aceitam. Um `bob.yaml` ausente, sem `--config`, continua nos padrões.

Erro de sintaxe, chave repetida, tipo errado e waiver inválido são barrados em `_language` ou `_blocked_config`, que imprimem no stderr e retornam `4` sem chamar `write_report`.

`duplication` inválida entra na mesma barreira que as outras chaves: `reject_config_types` chama `_config_from_file`, o stderr fica em inglês e nenhum relatório é gravado. A recusa cobre um valor que não é mapeamento, um `min_tokens` que não é um inteiro maior que 0, e `new_clones`, `max_new_clones`, `min_similarity` ou `min_lines` com tipo ou valor inválido. Uma chave desconhecida, inclusive `mutation`, `duplication.tool` e `dependencies.violation`, sai do mesmo jeito. O [CHANGELOG.md](../CHANGELOG.md) descreve esses casos.

Uma entrada de `paths.include` que não existe no disco entra na mesma barreira. O stderr fica em inglês e cita o arquivo e cada entrada ausente, como `bob.yaml: paths.include does not exist: missing-root`. Nada é gravado. Um `paths.include` omitido ou vazio continua `src` e não é verificado. `run_check` chamado direto, sem a CLI, grava o relatório precoce com esse motivo e o mesmo exit `4`.

Um `--reason` ausente no `bob waive` também é `4`, e essa frase segue o idioma da CLI, porque acontece dentro de `_waive_command` depois da barreira do arquivo. Um alvo que nenhum sobrevivente de `.bob/mutation-cache.json` ou `.bob/stryker-mutants.json` tem também sai com `4`, no idioma da CLI, e `waivers.yaml` não muda.

### Durante a medição, com relatório

Se a ferramenta falta no meio do gate (lizard, mutmut, import-linter, dependency-cruiser, Node num repo só TypeScript, git que falha ao calcular o diff), o gate fica `not_run` e o exit é `4`. O mesmo exit `4` vale quando o JSON do dependency-cruiser não é um objeto ou não traz a lista `violations`, e quando a última linha `Contracts:` do import-linter com exit 0 não é `N kept, 0 broken.` `write_report` grava `.bob/report.md` e `report.json` com esse código. `GitError` em `_open` segue o mesmo relatório precoce.

`bob doctor` com pino ausente ou versão diferente sai com `4` no stdout do próprio doctor, sem relatório em `.bob/`.

Num monorepo com Python e TypeScript, Node ausente não usa este código para o CRAP e para deps: Python segue, TypeScript entra como aviso, e o exit é o do que foi medido (`0` ou `1`). DRY sem Node é `not_run` com `0`, também no modo fail. Ver [Monorepo e Node ausente](gates.md#monorepo-e-node-ausente).
