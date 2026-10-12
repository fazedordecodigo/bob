# Changelog

## Unreleased

A wrong value type in `bob.yaml`, and a YAML syntax error in `.bob/waivers.yaml`, exit `4`. The message is English on stderr and names the file. A wrong type also names the key, as in `bob.yaml: crap must be a mapping`. `check`, `doctor`, and `waive` do this the same way and write nothing. An invalid `duplication` key still writes the error report in the configured language, and `report.json` reasons stay English.

Um valor com tipo errado no `bob.yaml`, e um erro de sintaxe YAML em `.bob/waivers.yaml`, saem com `4`. A mensagem fica em inglês no stderr e cita o arquivo. Um tipo errado também cita a chave, como em `bob.yaml: crap must be a mapping`. `check`, `doctor` e `waive` fazem isso do mesmo jeito e não gravam nada. Uma chave `duplication` inválida continua gravando o relatório de erro no idioma configurado, e os `reason` do `report.json` continuam em inglês.

`.bob/report.json` is the same bytes in `en` and `pt-BR`. `reason`, the cycle rule name, and `reproduce` stay English there, and that `reproduce` omits `--lang`. `report.md` and the pull request comment translate the cycle rule and the unnamed dependency-cruiser fallback, and the reproduce line there includes `--lang`.

`.bob/report.json` tem os mesmos bytes em `en` e em `pt-BR`. `reason`, o nome da regra de ciclo e `reproduce` ficam em inglês nesse arquivo, e esse `reproduce` não leva `--lang`. O `report.md` e o comentário do PR traduzem a regra de ciclo e o fallback sem nome do dependency-cruiser, e a linha de reprodução ali inclui `--lang`.
