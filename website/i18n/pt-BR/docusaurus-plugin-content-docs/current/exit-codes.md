# Códigos de saída

[Índice](README.md) · [CLI](reference/cli.md) · [Gates e waivers](guides/gates-and-waivers.md) · [Relatórios](guides/reports.md) · [SPEC](SPEC.md)

Os códigos estão em `src/bob_quality/exit_codes.py`. A spec os toma do mutator. `bob check` fica com o código mais alto entre os gates (`_worse` em `src/bob_quality/check.py`).

| Código | Nome no código | Quando sai |
|---|---|---|
| `0` | `PASSED` | Todo gate que rodou passou, ou só avisou |
| `1` | `GATE_FAILED` | Um achado que bloqueia no diff: CRAP no limite ou acima, uma violação de dependência, modo fail do DRY acima do teto, ou, quando esse gate foi pedido, cobertura do diff abaixo do piso, um achado de supply que bloqueia, um achado de segurança que bloqueia, um diagnóstico ou escape de tipo novo, ou um segredo novo |
| `2` | `BASELINE_BROKEN` | A suíte quebra antes da medição |
| `3` | `UNWAIVED_SURVIVOR` | Um mutante `survived` sem waiver numa linha alterada, ou `no_coverage` numa função alterada |
| `4` | `CONFIG_OR_TOOL` | Configuração inválida, uso inválido da linha de comando, ou uma ferramenta que bloqueia a medição pedida |

## Saída 0

Todo gate pedido que de fato rodou passou. Um aviso também termina em `0`: um clone novo no modo warn ou no teto no modo fail, TypeScript pulado num repositório misto quando o que foi medido está dentro do limite, um achado de segurança no diff fora de `security.fail_severities`, e um símbolo morto no diff. O mesmo `0` vale quando o gate `security` mediu uma linguagem e a outra ficou de fora: o passe vira `warn`. O veredito do gate mostra ⚠️. O exit permanece `0`. `no_coverage` numa função alterada não é um aviso. Sai com `3`.

Um nome de gate desconhecido é `not_run` e contribui com `0`.

Sem código a medir, `crap` e `coverage` ficam `not_run` com o motivo `nenhum código a medir` e contribuem com `0`. Sem código quer dizer nenhum arquivo `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` ou `.cjs` sob `paths.include` e fora de `paths.exclude`, sem seguir symlinks. Esses dois gates então não rodam ferramenta, e o relatório mostra ⏭️.

`bob waive` com um motivo válido e um alvo de um sobrevivente do último relatório de mutação sai com `0` e só grava `.bob/waivers.yaml`.

`bob doctor` sai com `0` quando todo pin casa com a versão encontrada.

`bob report` sai com o inteiro guardado no JSON salvo, que pode ser `0`.

## Saída 1

`crap_verdict` devolve `1` quando uma função considerada tem CRAP maior ou igual a `crap.max_per_function` (ou `--threshold`). O motivo lista nomes como `function@file:line`.

`deps_verdict` devolve `1` quando uma violação está marcada no diff. O motivo lista `origin → destination`.

O DRY devolve `1` só no modo fail (`duplication.new_clones: fail` ou `--dry-fail`), quando os clones novos contados passam de `duplication.max_new_clones` ou `--max-new-clones`. O motivo nomeia a chave e o teto, como em `1 new clone exceeds duplication.max_new_clones 0`. No modo warn, o padrão, o DRY não devolve `1`.

Quando o gate foi pedido:

- `coverage` devolve `1` quando uma linguagem medida está abaixo de `coverage.min_percent`. Um percentual igual ao piso passa.
- `supply` devolve `1` quando um pacote novo responde 404, um import não está declarado, ou a severidade de um advisory está em `supply.osv_fail_severities`.
- `security` devolve `1` quando um achado no diff tem uma severidade em `security.fail_severities` e não tem waiver. Um achado fora do diff, um achado com waiver e uma severidade fora da lista não devolvem `1`. Se a outra linguagem não mediu, a falha permanece `1`.
- `typing` devolve `1` para um diagnóstico novo ou um escape novo numa linha do diff sem waiver.
- `secrets` devolve `1` para um segredo novo numa linha do diff sem waiver.

A mutação não devolve `1`. Um sobrevivente sem waiver é `3`. `cognitive`, `test_smells` e `dead_code` não devolvem `1`.

Se o CRAP falha (`1`) e a mutação também falha (`3`), `check` sai com `3`.

## Saída 2

O gate `crap` roda pytest (Python) ou vitest (TypeScript) para medir cobertura. Em Python, um código do pytest diferente de `0` e `5` é uma baseline quebrada (`pytest_passed` em `exit_codes.py`). O comentário nesse módulo diz que `5` é "no tests collected" e também passa. Em TypeScript, `vitest_code != 0` é exit `2`. Um `coverage-final.json` ausente depois que o vitest sai com `0` é exit `4`.

O gate `mutate` também exige a baseline. Se `crap` rodou antes na mesma execução, o código do pytest é reusado. Sozinho, `bob mutate` chama o exit do pytest. Na falha o status é `not_run` e o exit é `2`.

O gate `coverage` sai com `2` quando a suíte quebra antes de o artefato de cobertura existir.

O [AGENTS.md](https://github.com/fazedordecodigo/bob/blob/main/AGENTS.md) registra que o exit `2` também vem do `bob check` padrão, porque o padrão inclui `crap`.

## Saída 3

Só o gate `mutate`. A lista que bloqueia são mutantes com status `survived`, waiver vazio e uma linha no lado novo do diff. Sem arquivo, ou com uma linha em zero ou abaixo, esse sobrevivente também bloqueia. Um ou mais: exit `3` e status `failed`. O motivo lista só esses, como `function@file:line`. Um sobrevivente sem waiver fora do diff permanece na tabela e não muda o exit.

Um waiver casado por `file::function` ou `file::function::<description>` tira o sobrevivente dessa lista. O id do mutante e um nome de função nu não casam. Um id que não casa com nada deixa o sobrevivente na lista. Em TypeScript, uma linha inserida acima do mutante muda a descrição, e o waiver antigo para de casar. Ver [ADR 0006](adr/0006-chave-estavel-do-waiver.md). `killed` e `timeout` não estão na lista. `no_coverage` numa função alterada também sai com `3`, e um waiver não o remove. Se um sobrevivente que bloqueia já existe, o motivo do exit permanece o do sobrevivente, e a contagem de `no_coverage` vai para o relatório.

## Saída 4

Há dois caminhos para chegar a `4`.

### Antes da medição, nada é gravado

`cli.main` devolve `4` sem gravar `report.md` ou `report.json`, e sem mudar `waivers.yaml`, em dois casos diferentes.

Uso inválido da linha de comando (comando ausente, comando desconhecido, flag ilegal, um valor fora das escolhas, um valor fora da regra de `--threshold` ou `--max-workers`) imprime o uso do argparse no stderr. Esse texto não menciona baseline. A ajuda (`-h`, `--help`) sai com `0`. Isso não é exit `2`. A regra de `--threshold` e `--max-workers` está em [Outros comandos de medição](reference/cli.md#outros-comandos-de-medição). Um `--max-new-clones` negativo em `bob dry` ou `bob check` também sai com `4`, com `--max-new-clones must be at least 0` em inglês no stderr.

`--config` antes do comando é uso inválido. A última linha do stderr permanece em inglês mesmo com `--lang pt-BR`, como em `bob: error: --config goes after the command: bob check --config ci.yaml`. `doctor` não aceita a flag. A última linha é `bob: error: doctor does not accept --config`. `waive` não aceita. A última linha é `bob: error: waive does not accept --config`. `report` também não aceita.

Configuração inválida imprime inglês no stderr quando:

- `--lang` ou `BOB_LANG` está vazio ou não é `en` nem `pt-BR`;
- `language` no YAML não é string ou não é um desses dois valores;
- `bob.yaml` tem erro de sintaxe, repete uma chave no mesmo mapeamento, ou não é um mapeamento. Uma chave repetida nomeia a chave e a linha, como em `invalid YAML in bob.yaml: found duplicate key 'base' on line 2`;
- uma chave tem o tipo errado, inclusive `base`, `languages`, `paths`, `include`, `exclude`, `crap`, `cognitive`, `duplication`, `coverage`, `dependencies`, `security` e `dead_code`;
- `security.fail_severities` tem uma palavra fora do vocabulário, um item repetido ou uma lista vazia;
- `.bob/waivers.yaml` existe e o YAML é inválido, repete uma chave, ou a forma não é a de [Configuração](guides/configuration.md#bobwaiversyaml). A mensagem nomeia o caminho e o campo. Uma chave repetida nomeia a chave e a linha, como em `invalid YAML in .bob/waivers.yaml: found duplicate key 'id' on line 3`.

Um caminho de `--config` que não é um arquivo está nesta barreira. O arquivo ausente levanta `ConfigError`, e o preflight imprime inglês no stderr (`config file not found: <path>`) e devolve `4` sem gravar relatório. A flag existe em `check`, `crap`, `dry`, `deps` e `mutate`. `doctor` e `waive` não a aceitam. Um `bob.yaml` ausente, sem `--config`, permanece nos padrões.

Um `duplication` inválido está na mesma barreira que as outras chaves. Stderr em inglês, sem relatório. A recusa cobre um valor que não é um mapeamento, um `min_tokens` que não é um inteiro maior que 0, e `new_clones`, `max_new_clones`, `min_similarity` ou `min_lines` com o tipo ou o valor errado. Uma chave desconhecida, inclusive `mutation`, `duplication.tool` e `dependencies.violation`, segue o mesmo caminho.

Uma entrada de `paths.include` que não está no disco está na mesma barreira. O stderr em inglês nomeia o arquivo e cada entrada ausente, como em `bob.yaml: paths.include does not exist: missing-root`. Nada é gravado. Um `paths.include` omitido ou vazio permanece `src` e não é conferido. `run_check` chamado direto, sem a CLI, grava o relatório precoce com esse motivo e o mesmo exit `4`.

Um `--reason` ausente em `bob waive` também é `4`, e essa frase segue o idioma da CLI, porque acontece dentro do comando waive depois da barreira do arquivo. Um alvo que nenhum sobrevivente em `.bob/mutation-cache.json` ou `.bob/stryker-mutants.json` tem também sai com `4`, no idioma da CLI, e `waivers.yaml` não muda.

### Durante a medição, com relatório

Se a ferramenta falta no meio de um gate que pode sair com `1` ou `3` (lizard, mutmut, import-linter, dependency-cruiser, Node num repositório só de TypeScript, Bandit ou Semgrep quando nenhuma linguagem do gate `security` mediu, git falhando ao calcular o diff), o gate é `not_run` e o exit é `4`. O relatório é gravado. `write_report` grava `.bob/report.md` e `report.json` com esse código. `GitError` no passo de abertura usa o mesmo relatório precoce.

`bob doctor` com um pin ausente ou uma versão diferente sai com `4` no próprio stdout do doctor, sem relatório em `.bob/`.

Um gate só de aviso (`cognitive`, `test_smells`, `dead_code`) trata uma ferramenta ausente ou quebrada como `not_run` e contribui com `0`. O jscpd faz o mesmo: DRY sem Node é `not_run` com `0`, também no modo fail.

Num projeto com código, falha da ferramenta de cobertura continua `4`. Por exemplo, o `No data to report.` do coverage.py deixa `crap` ou `coverage` em `not_run` com exit `4`. Só um projeto sem código a medir recebe o `0` descrito em Saída 0.

Num repositório com Python e TypeScript, um Node ausente não usa este código para CRAP nem para deps. Python continua, TypeScript entra como aviso, e o exit é o que foi medido (`0` ou `1`). Ver [Python e TypeScript juntos](guides/gates-and-waivers.md#python-e-typescript-juntos).

O resumo do README que diz que o exit `4` não grava nada descreve o caminho do preflight. Ele não descreve este caminho de medição. Esta página documenta os dois.
