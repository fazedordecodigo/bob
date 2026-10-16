# report.json

[Índice](../README.md) · [Relatórios](../guides/reports.md) · [Códigos de saída](../exit-codes.md)

`.bob/report.json` segue `src/bob_quality/schemas/report_v1.json`. `schema_version` é a constante `1`. O arquivo está em inglês nos dois idiomas de saída (`JSON_LANGUAGE = "en"` em `src/bob_quality/report.py`).

## Campos obrigatórios

O schema exige `schema_version`, `commit`, `base`, `generated_at`, `tool_versions`, `gates`, `focus`, `top_crap`, `reproduce` e `exit_code`.

`gates[]` exige `name` e `status`. `status` é `passed`, `warn`, `failed` ou `not_run`. `reason` é uma string ou null, e é renderizado em inglês.

`reproduce` no JSON omite `--lang`. A linha de reprodução no `report.md` inclui o `--lang` que a produziu.

## Campos que o renderer grava

O renderer também grava `old_debt`, `dependencies`, `old_dependencies`, `clones`, `waivers`, `survivors` e `mutation`. Nem todos estão em `required`.

`survivors[].target` é o alvo exato do waiver, ou `null` quando essa forma não existe. `survivors[].blocking` é um booleano. O cache de mutação não guarda `blocking`.

`mutation.no_coverage` tem `total` e `functions`. Cada linha de função tem `file`, `function` e `count`.

Campos opcionais, omitidos quando aquele gate não os produziu:

| Campo | Quando está presente | Forma |
|---|---|---|
| `test_smells` | o gate rodou | lista de `file`, `line`, `rule`, `waiver` |
| `supply` | o gate mediu | `measured`, `skipped`, `findings` |
| `diff_coverage` | pelo menos uma linguagem mediu | percentuais por linguagem e linhas `uncovered` de `file` e `line` |
| `typing` | o gate foi pedido | `absent`, `checkers`, `findings` |
| `secrets` | o gate mediu | achados que bloqueiam, cada um com `file`, `line` e `rule_id` |
| `cognitive` | o gate foi pedido | `file`, `name`, `start_line`, `end_line`, `score`, `language`, `waiver_id` |
| `dead_code` | o gate foi pedido | `symbols`, cada um com `file`, `line`, `name`, `kind`, `language`, `confidence`, `waiver`. `kind` permanece em inglês |
| `security` | o gate foi pedido | `findings` e `unmeasured`. Um achado tem `tool`, `rule`, `file`, `line`, `end_line`, `severity`, `disposition` e `waiver`. Disposition é `fail`, `warn`, `waived` ou `off_diff` |
| `churn` | sempre | medido, ou `{"kind": "unavailable"}` quando a contagem não pode ser lida |

`churn` é opcional no schema e é sempre gravado. Um objeto medido tem `kind`, `window_days`, `ends_on`, `files`, `hotspots` e `diffusion`. Cada arquivo tem `path`, `commits` e `relative`. `relative` é a taxa, ou `null`.

Depois de `mutation`, a ordem de renderização é `test_smells` quando esse gate rodou, `supply` quando mediu, `diff_coverage` quando pelo menos uma linguagem mediu, `typing` quando foi pedido, `secrets` quando mediu, `cognitive` quando foi pedido, `dead_code` quando foi pedido, e `security` quando foi pedido. `churn` vem em seguida, antes de `reproduce` e `exit_code`. Um check que não rodou um gate omite essa chave. `schema_version` permanece `1`.

## O que não muda com o idioma da saída

Os bytes do JSON são os mesmos em `en` e `pt-BR`:

- todo `reason` de gate;
- o nome da regra de ciclo (`Forbidden dependency cycle`);
- `reproduce`, que não inclui `--lang`.

`report.md` e o comentário do pull request traduzem a regra de ciclo e o fallback sem nome do dependency-cruiser, e a linha de reprodução inclui `--lang`.

## bob report

`bob report --in <dir> --out <file>` lê `<dir>/report.json` e grava Markdown. Ele sai com o `exit_code` guardado. O inteiro tem de ser `0`, `1`, `2`, `3` ou `4`. Um arquivo ausente, texto que não é JSON, ou uma forma inválida sai com `4`, imprime inglês no stderr e não grava o arquivo de saída. Ver [CLI](cli.md#bob-report).
