# Changelog

## Unreleased

`.bob/report.json` is the same bytes in `en` and `pt-BR`. `reason`, the cycle rule name, and `reproduce` stay English there, and that `reproduce` omits `--lang`. `report.md` and the pull request comment translate the cycle rule and the unnamed dependency-cruiser fallback, and the reproduce line there includes `--lang`.

`.bob/report.json` tem os mesmos bytes em `en` e em `pt-BR`. `reason`, o nome da regra de ciclo e `reproduce` ficam em inglês nesse arquivo, e esse `reproduce` não leva `--lang`. O `report.md` e o comentário do PR traduzem a regra de ciclo e o fallback sem nome do dependency-cruiser, e a linha de reprodução ali inclui `--lang`.

bob ships only its own three skills, `bob-check`, `harden`, and `review-report`. The 27 Matt Pocock skills in `skills/vendor/mattpocock/`, with their `LICENSE` and `NOTICE`, are gone from the repository and from both plugin manifests. `review-report` now states its own Summary / Evidence / Merge Danger template instead of pointing at Pocock's `pr` skill. Running the installer again does not delete the folders an earlier install copied. Each of those copies has a `NOTICE` that names `mattpocock/skills`, so `grep -l mattpocock .agents/skills/*/NOTICE .github/skills/*/NOTICE` finds them. Delete the folder that holds each match.

O bob traz só as três skills dele, `bob-check`, `harden` e `review-report`. As 27 skills do Matt Pocock em `skills/vendor/mattpocock/`, com o `LICENSE` e o `NOTICE`, saíram do repositório e dos dois manifestos do plugin. A `review-report` agora traz o próprio molde Summary / Evidence / Merge Danger, em vez de apontar para a skill `pr` do Pocock. Rodar o instalador de novo não apaga as pastas que uma instalação anterior copiou. Cada uma dessas cópias tem um `NOTICE` que cita `mattpocock/skills`, e `grep -l mattpocock .agents/skills/*/NOTICE .github/skills/*/NOTICE` acha todas. Apague a pasta de cada resultado.
