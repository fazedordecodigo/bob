# Changelog

## Unreleased

A Stryker report that is not UTF-8 exits `4` with the mutate gate `not_run`, and the run writes the report instead of a traceback. The `bob-mutation-cache` artifact uploads and restores `.bob/stryker-incremental.json` next to `.bob/mutation-cache.json`.

Um relatório do Stryker que não é UTF-8 sai com `4`, com o gate mutate em `not_run`, e a execução grava o relatório em vez de um traceback. O artefato `bob-mutation-cache` sobe e restaura `.bob/stryker-incremental.json` junto de `.bob/mutation-cache.json`.

`extract_cache` prints `restored mutmut`, `restored incremental`, or `restored both` after it writes those files from the `bob-mutation-cache` zip. It prints nothing when the zip has neither file.

O `extract_cache` imprime `restored mutmut`, `restored incremental` ou `restored both` depois de gravar esses arquivos do zip `bob-mutation-cache`. Não imprime nada quando o zip não traz nenhum dos dois.

`bob check --gates secrets` scans `paths.include` with gitleaks 8.30.1. A secret on a new diff line fails with exit `1`. The report lists the file, the line, and the rule id. It does not print the secret. Waive a finding in `.bob/waivers.yaml` with the id `secret:<rule>:<file>:<line>`. `secrets` in `bob.yaml` is an empty mapping and does not turn the gate on. The gate stays out of the default list, the pre-push hook, and the Action default. `bob doctor` pins gitleaks 8.30.1. A `.gitleaksignore` file under an include root exits `4` before the scan.

`bob check --gates secrets` varre `paths.include` com o gitleaks 8.30.1. Um segredo numa linha nova do diff falha com exit `1`. O relatório lista o arquivo, a linha e o id da regra. Ele não imprime o segredo. O waiver em `.bob/waivers.yaml` usa o id `secret:<regra>:<arquivo>:<linha>`. `secrets` no `bob.yaml` é um mapeamento vazio e não liga o gate. O gate fica fora da lista padrão, do hook pre-push e do padrão da Action. O `bob doctor` pina o gitleaks 8.30.1. Um `.gitleaksignore` numa raiz de include sai com `4` antes da varredura.

`bob --config ci.yaml check` exits `4` and writes no report. The last stderr line is `bob: error: --config goes after the command: bob check --config ci.yaml`. A path with a space is quoted, as in `bob crap --config 'my ci.yaml'`. `doctor` and `waive` do not accept `--config`. `bob --help` does not list `--config`.

`bob --config ci.yaml check` sai com `4` e não grava relatório. A última linha do stderr é `bob: error: --config goes after the command: bob check --config ci.yaml`. Um caminho com espaço sai entre aspas, como em `bob crap --config 'my ci.yaml'`. `doctor` e `waive` não aceitam `--config`. O `bob --help` não lista `--config`.

A repeated key in one YAML mapping exits `4` and writes no report. The English stderr names the key and the line, as in `invalid YAML in bob.yaml: found duplicate key 'base' on line 2`. A repeated key in `.bob/waivers.yaml` names the key and the line the same way. A key written in the mapping can still override a value merged with `<<`.

Uma chave repetida num mapeamento YAML sai com `4` e não grava relatório. O stderr em inglês cita a chave e a linha, como em `invalid YAML in bob.yaml: found duplicate key 'base' on line 2`. Uma chave repetida no `.bob/waivers.yaml` cita a chave e a linha do mesmo jeito. Uma chave escrita no mapeamento ainda pode substituir um valor mesclado com `<<`.

The mutate gate exits `3` only for an unwaived survivor on a changed line. An unwaived survivor on a line the diff did not change stays in the report, marked outside the diff, and does not change the exit or the review focus. A survivor with no file, or with a line at or below zero, still exits `3`. Remutation is unchanged: a changed function, and a cached function that still has an unwaived survivor, are still mutated. The cache does not store `blocking`.

O gate mutate sai com `3` só para um sobrevivente sem waiver numa linha alterada. Sobrevivente sem waiver numa linha que o diff não mudou fica no relatório, marcado fora do diff, e não muda o exit nem o foco do review. Sobrevivente sem arquivo, ou com linha menor ou igual a zero, continua saindo com `3`. A remutação não muda: função alterada, e função do cache que ainda tem sobrevivente sem waiver, continuam sendo mutadas. O cache não guarda `blocking`.

`grimp==3.17` is a direct pin in `pyproject.toml`, and `bob doctor` lists it. `bob doctor` no longer treats a PATH binary as a pip tool. The version it expects is the one `bob-quality` declares.

`grimp==3.17` é um pin direto no `pyproject.toml`, e o `bob doctor` lista essa versão. O `bob doctor` não trata mais um binário do PATH como ferramenta pip. A versão que ele espera é a que o `bob-quality` declara.

Invalid command-line usage exits `4`, writes no report, and the stderr does not mention baseline. Help (`-h`, `--help`) stays `0`.

Um uso inválido da linha de comando sai com `4`, não grava relatório, e o stderr não menciona baseline. A ajuda (`-h`, `--help`) continua saindo com `0`.

`bob crap --threshold` accepts a finite number greater than 0, the same rule as `crap.max_per_function`. `bob mutate --max-workers` accepts an integer from 1 to 64. Any other value, including `nan`, `inf`, `-inf`, `1e309`, `0`, and a negative number, is a usage error. It exits `4`, prints the argparse usage and an English message on stderr, as in `bob crap: error: argument --threshold: invalid value: 'nan' (use a finite number greater than 0)`, and writes no report.

`bob crap --threshold` aceita um número finito maior que 0, a mesma regra de `crap.max_per_function`. `bob mutate --max-workers` aceita um inteiro de 1 a 64. Qualquer outro valor, inclusive `nan`, `inf`, `-inf`, `1e309`, `0` e um número negativo, é uso inválido. Sai com `4`, imprime o uso do argparse e uma mensagem em inglês no stderr, como em `bob crap: error: argument --threshold: invalid value: 'nan' (use a finite number greater than 0)`, e não grava relatório.

An invalid semantic value in `bob.yaml` or `.bob/waivers.yaml` exits `4`. The English stderr names the path and the field, as in `bob.yaml: crap.scope must be changed or all` or `.bob/waivers.yaml: waivers[0].reason must be one non-empty line`, and the run writes no report. `check`, `doctor`, and `waive` do this the same way. That covers an unknown key, a bad `crap.scope`, a bad `languages` member, a non-positive or non-finite `crap.max_per_function` (an integer too large to convert to float counts as not finite), a negative `duplication.min_tokens`, an invalid `duplication`, `waivers` set to `0`, `false`, or `""`, and an empty `reason`.

Um valor semântico inválido no `bob.yaml` ou no `.bob/waivers.yaml` sai com `4`. O stderr em inglês cita o caminho e o campo, como em `bob.yaml: crap.scope must be changed or all` ou `.bob/waivers.yaml: waivers[0].reason must be one non-empty line`, e a execução não grava relatório. `check`, `doctor` e `waive` fazem isso do mesmo jeito. Isso cobre uma chave desconhecida, um `crap.scope` inválido, um item de `languages` inválido, um `crap.max_per_function` que não é positivo ou não é finito (um inteiro grande demais para virar float também não é finito), um `duplication.min_tokens` negativo, um `duplication` inválido, um `waivers` igual a `0`, `false` ou `""`, e um `reason` vazio.

A wrong value type in `bob.yaml`, and a YAML syntax error in `.bob/waivers.yaml`, exit `4`. The message is English on stderr and names the file. A wrong type also names the key, as in `bob.yaml: crap must be a mapping`. A `waivers.yaml` that is valid YAML with the wrong shape also exits `4`. The English stderr names the path and the field, as in `.bob/waivers.yaml: waivers[0].reason must be a string`, and the run writes no report. `check`, `doctor`, and `waive` do this the same way and write nothing.

Um valor com tipo errado no `bob.yaml`, e um erro de sintaxe YAML em `.bob/waivers.yaml`, saem com `4`. A mensagem fica em inglês no stderr e cita o arquivo. Um tipo errado também cita a chave, como em `bob.yaml: crap must be a mapping`. Um `waivers.yaml` que é YAML válido com formato errado também sai com `4`. O stderr em inglês cita o caminho e o campo, como em `.bob/waivers.yaml: waivers[0].reason must be a string`, e a execução não grava relatório. `check`, `doctor` e `waive` fazem isso do mesmo jeito e não gravam nada.

`.bob/report.json` is the same bytes in `en` and `pt-BR`. `reason`, the cycle rule name, and `reproduce` stay English there, and that `reproduce` omits `--lang`. `report.md` and the pull request comment translate the cycle rule and the unnamed dependency-cruiser fallback, and the reproduce line there includes `--lang`.

`.bob/report.json` tem os mesmos bytes em `en` e em `pt-BR`. `reason`, o nome da regra de ciclo e `reproduce` ficam em inglês nesse arquivo, e esse `reproduce` não leva `--lang`. O `report.md` e o comentário do PR traduzem a regra de ciclo e o fallback sem nome do dependency-cruiser, e a linha de reprodução ali inclui `--lang`.

bob ships only `bob-check`, `harden`, and `review-report`. The 27 Matt Pocock skills are gone from the repository and from both plugin manifests. `review-report` states its own Summary / Evidence / Merge Danger template. A later install deletes one of those folders only when its `NOTICE` is a regular file with the bytes the old installer copied from the vendored pin `49dd158d1076134a641b33efb035946536778336`. A symlink `NOTICE` does not count, even when it points at a copy of that file. A file, a symlink, or a folder that only shares the name stays, and the installer warns on stderr. It copies `LICENSE` and does not copy `NOTICE`. A second run leaves the same tree and the same warnings.

O bob traz só `bob-check`, `harden` e `review-report`. As 27 skills do Matt Pocock saíram do repositório e dos dois manifestos. A `review-report` traz o próprio molde Summary / Evidence / Merge Danger. Uma instalação seguinte apaga uma dessas pastas só quando o `NOTICE` dela é um arquivo regular com os bytes que o instalador antigo copiava do pin `49dd158d1076134a641b33efb035946536778336`. Um `NOTICE` que é link simbólico não conta, mesmo quando aponta para uma cópia desse arquivo. Um arquivo, um link simbólico ou uma pasta que só divide o nome ficam, e o instalador avisa no stderr. Ele copia o `LICENSE` e não copia o `NOTICE`. Uma segunda execução deixa a mesma árvore e os mesmos avisos.
