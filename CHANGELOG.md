# Changelog

## Unreleased

Invalid command-line usage exits `4`, writes no report, and the stderr does not mention baseline. Help (`-h`, `--help`) stays `0`.

Um uso inválido da linha de comando sai com `4`, não grava relatório, e o stderr não menciona baseline. A ajuda (`-h`, `--help`) continua saindo com `0`.

A wrong value type in `bob.yaml`, and a YAML syntax error in `.bob/waivers.yaml`, exit `4`. The message is English on stderr and names the file. A wrong type also names the key, as in `bob.yaml: crap must be a mapping`. A `waivers.yaml` that is valid YAML with the wrong shape also exits `4`. The English stderr names the path and the field, as in `.bob/waivers.yaml: waivers[0].reason must be a string`, and the run writes no report. `check`, `doctor`, and `waive` do this the same way and write nothing. An invalid `duplication` key still writes the error report in the configured language, and `report.json` reasons stay English.

Um valor com tipo errado no `bob.yaml`, e um erro de sintaxe YAML em `.bob/waivers.yaml`, saem com `4`. A mensagem fica em inglês no stderr e cita o arquivo. Um tipo errado também cita a chave, como em `bob.yaml: crap must be a mapping`. Um `waivers.yaml` que é YAML válido com formato errado também sai com `4`. O stderr em inglês cita o caminho e o campo, como em `.bob/waivers.yaml: waivers[0].reason must be a string`, e a execução não grava relatório. `check`, `doctor` e `waive` fazem isso do mesmo jeito e não gravam nada. Uma chave `duplication` inválida continua gravando o relatório de erro no idioma configurado, e os `reason` do `report.json` continuam em inglês.

`.bob/report.json` is the same bytes in `en` and `pt-BR`. `reason`, the cycle rule name, and `reproduce` stay English there, and that `reproduce` omits `--lang`. `report.md` and the pull request comment translate the cycle rule and the unnamed dependency-cruiser fallback, and the reproduce line there includes `--lang`.

`.bob/report.json` tem os mesmos bytes em `en` e em `pt-BR`. `reason`, o nome da regra de ciclo e `reproduce` ficam em inglês nesse arquivo, e esse `reproduce` não leva `--lang`. O `report.md` e o comentário do PR traduzem a regra de ciclo e o fallback sem nome do dependency-cruiser, e a linha de reprodução ali inclui `--lang`.

bob ships only `bob-check`, `harden`, and `review-report`. The 27 Matt Pocock skills are gone from the repository and from both plugin manifests. `review-report` states its own Summary / Evidence / Merge Danger template. A later install deletes one of those folders only when its `NOTICE` is a regular file with the bytes the old installer copied from the vendored pin `49dd158d1076134a641b33efb035946536778336`. A symlink `NOTICE` does not count, even when it points at a copy of that file. A file, a symlink, or a folder that only shares the name stays, and the installer warns on stderr. It copies `LICENSE` and does not copy `NOTICE`. A second run leaves the same tree and the same warnings.

O bob traz só `bob-check`, `harden` e `review-report`. As 27 skills do Matt Pocock saíram do repositório e dos dois manifestos. A `review-report` traz o próprio molde Summary / Evidence / Merge Danger. Uma instalação seguinte apaga uma dessas pastas só quando o `NOTICE` dela é um arquivo regular com os bytes que o instalador antigo copiava do pin `49dd158d1076134a641b33efb035946536778336`. Um `NOTICE` que é link simbólico não conta, mesmo quando aponta para uma cópia desse arquivo. Um arquivo, um link simbólico ou uma pasta que só divide o nome ficam, e o instalador avisa no stderr. Ele copia o `LICENSE` e não copia o `NOTICE`. Uma segunda execução deixa a mesma árvore e os mesmos avisos.
