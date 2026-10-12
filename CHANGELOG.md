# Changelog

## Unreleased

`.bob/report.json` is the same bytes in `en` and `pt-BR`. `reason`, the cycle rule name, and `reproduce` stay English there, and that `reproduce` omits `--lang`. `report.md` and the pull request comment translate the cycle rule and the unnamed dependency-cruiser fallback, and the reproduce line there includes `--lang`.

`.bob/report.json` tem os mesmos bytes em `en` e em `pt-BR`. `reason`, o nome da regra de ciclo e `reproduce` ficam em inglês nesse arquivo, e esse `reproduce` não leva `--lang`. O `report.md` e o comentário do PR traduzem a regra de ciclo e o fallback sem nome do dependency-cruiser, e a linha de reprodução ali inclui `--lang`.

bob ships only `bob-check`, `harden`, and `review-report`. The 27 Matt Pocock skills are gone from the repository and from both plugin manifests. `review-report` states its own Summary / Evidence / Merge Danger template. A later install deletes one of those folders only when its `NOTICE` is the file the old installer copied from the vendored pin `49dd158d1076134a641b33efb035946536778336`. A file, a symlink, or a folder that only shares the name stays, and the installer warns on stderr. It copies `LICENSE` and does not copy `NOTICE`. A second run leaves the same tree and the same warnings.

O bob traz só `bob-check`, `harden` e `review-report`. As 27 skills do Matt Pocock saíram do repositório e dos dois manifestos. A `review-report` traz o próprio molde Summary / Evidence / Merge Danger. Uma instalação seguinte apaga uma dessas pastas só quando o `NOTICE` dela é o arquivo que o instalador antigo copiava do pin `49dd158d1076134a641b33efb035946536778336`. Um arquivo, um link simbólico ou uma pasta que só divide o nome ficam, e o instalador avisa no stderr. Ele copia o `LICENSE` e não copia o `NOTICE`. Uma segunda execução deixa a mesma árvore e os mesmos avisos.
