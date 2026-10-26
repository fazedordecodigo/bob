# Arquivos compartilhados entre a U6 e a U7

Base: `main` @ `22d461a60920ab13e7b09fd654fd0e4686ba14d0`. As linhas citadas são desse SHA.
Cópia idêntica em `construction/u7-update-versao/shared-files-u6-u7.md`. Se uma mudar, a outra muda no mesmo commit.
Decisão: ADR 0027 (proposta em `construction/u6-u7-decisions-proposta.md`).

## Tabela
| Arquivo | ET da U6 | ET da U7 | Tipo de conflito | Mitigação |
|---|---|---|---|---|
| `CHANGELOG.md` | T3 (2 parágrafos no topo de `## Unreleased`, depois da linha 4 em branco) | T3 (idem) | textual certo: as duas inserem no mesmo ponto | só a T3 de cada unit escreve. Rebase: regra R-CL |
| `scripts/verify-install.sh` | T3: linha 2 (comentário), linha 4 (`STEP_IDS`); `run_oneliner` (357-399); `profile_case` e `step_13` depois do `}` de `step_12` (linha 1312); dispatch `      13) step_13 ;;` depois da linha 1339 (`12) step_12 ;;`) | T3: linha 2, linha 4; `STEP8_DONE=0` e `STEP10_DONE=0` depois da linha 13; `NEW_X=`, `NEW_TAG=`, `NEW_WHL=` depois da linha 25; `step_2` (3 linhas entre as linhas 750 e 751: `check_version`, só no modo espelho); `ensure_8`/`ensure_10` depois do `}` de `ensure_2` (linha 777); funções novas depois do `}` de `step_9b` (linha 1276); linha 1336 (`8) step_8` → `8) ensure_8`); `      10) ensure_10 ;;` e `      11) step_11 ;;` depois da linha 1338 (`9b) step_9b ;;`) | textual certo nas linhas 2 e 4; nenhum nos outros pontos (separados por pelo menos 1 linha sem mudança: a 1339 fica entre as inserções da U7 e da U6) | regras R-VI1 e R-VI2; a linha `3\|4\|5\|6\|7\|12) ensure_2 ;;` (1326) **não muda** em nenhuma das duas (dependência dentro do passo, ADR 0026) |
| `tests/test_verify_install.py` | T3: `_HELP` (linha 27); `test_step_ids_are_the_u1_u3_u4_and_u5_steps` (94-95); parâmetros de `test_usage_errors_exit_1_before_preparing` (366, 368, 369 e 376); testes novos depois de `test_pytest_pin_matches_pyproject` (termina na 345) | T3: `_HELP` (27); 94-95; parâmetros (366-369 e 376); testes novos depois de `test_step_8_checks_the_foreign_hook` (termina na 310) | textual certo nas linhas 27, 95, 369 e 376; as linhas 94, 366 e 368 mudam igual nas duas (`def test_step_ids_are_the_known_steps() -> None:`, `("--only", "15")` e `"verify-install: uso: passo desconhecido 15. "`), então não conflitam | regra R-TV |
| `src/bob_quality/messages.py` | T2: chaves `setup.profile*` depois de `"setup.doctor_not_run"` (en 407, pt-BR 837) | T1: `version.*` depois de `"doctor.bob_home_relative"` (en 222, pt-BR 652). T2: `cli.update` e `cli.version` depois de `"cli.setup"` (en 66, pt-BR 493); `version.bob` e `update.*` depois do último `version.*` da T1 | nenhum esperado: 4 âncoras diferentes, longe umas das outras (≥ 150 linhas) | se o git acusar conflito mesmo assim: regra R-MS |
| `tests/test_hermetic.py` | T2: troca a linha 14 `("tests/test_setup_cmd.py", "-k", "hook"),` por `("tests/test_setup_cmd.py", "-k", "hook or profile"),` | T1: insere `("tests/test_project_version.py",),` entre a linha 12 (`_UNIT_ARGS … = (`) e a 13. T2: insere `("tests/test_update.py",),` logo depois do item da T1 | nenhum esperado: a linha 13 (`("tests/test_hook_install.py",),`) separa as mudanças | se conflitar: regra R-HE |
| `scripts/install.sh` | T1 | — (a U7 só **roda** o script no passo 10) | nenhum textual; comportamento: o passo 10 roda o `install.sh` com o passo `perfil` se a U6 T1 já entrou | o passo 10 não confere linha de perfil; vale com e sem a U6 |
| `src/bob_quality/setup_cmd.py` | T2 (`_summary`, constantes, `import os`) | — (a U7 T2 só **importa** `step_projeto`, `SetupContext` e `run_setup`) | nenhum | nomes importados pela U7 não mudam na U6 |
| Registro de passos do `bob setup` (`STEPS`, `setup_cmd.py:248-256`) | não muda (a linha do perfil vem por `BOB_INSTALL_PROFILE`, não por passo) | não muda | nenhum | — |

## Regras de rebase (mecânicas)
A ET que entra em segundo faz `git fetch origin && git rebase origin/main` e resolve **só** com estas regras. Depois roda de novo os comandos da própria ET e cola no PR a saída nova (seção "Rebase").
- **R-CL (`CHANGELOG.md`).** Fica com os dois lados. Os 2 parágrafos (en, pt-BR) da ET que está fazendo rebase vão **no topo** de `## Unreleased`, logo depois da linha em branco que segue o título. Depois vêm os 2 parágrafos da outra unit, sem mudança, e o resto. Cada parágrafo seguido de uma linha em branco. Nenhum texto muda.
- **R-VI1 (`scripts/verify-install.sh`, linhas 2 e 4).** O resultado é sempre este, nas duas ordens de merge:
  - linha 2: `# Harness do comando de verificação (CT15): passos 1, 2, 3, 4, 5, 6, 7, 8, 9a, 9b, 10, 11, 12 e 13.`
  - linha 4: `STEP_IDS='1 2 3 4 5 6 7 8 9a 9b 10 11 12 13'`
  - Regra geral: a união dos ids, na ordem `1 2 3 4 5 6 7 8 9a 9b 10 11 12 13 14`.
- **R-VI2 (`scripts/verify-install.sh`, demais pontos).** Se o git acusar conflito em `run_selected`, o bloco `case "$_id" in` do dispatch fica nesta ordem exata. Linhas de outras units seguem a mesma ordem numérica.
  ```
      1) step_1 ;;
      2) ensure_2 ;;
      3) step_3 ;;
      4) step_4 ;;
      5) step_5 ;;
      6) step_6 ;;
      7) step_7 ;;
      8) ensure_8 ;;
      9a) step_9a ;;
      9b) step_9b ;;
      10) ensure_10 ;;
      11) step_11 ;;
      12) step_12 ;;
      13) step_13 ;;
  ```
  - Funções conflitando: as duas ficam. As da U7 `ensure_8` e `ensure_10` ficam logo depois de `ensure_2`; `next_patch`, `rebrand_wheel`, `sums_two`, `build_update_mirror`, `run_bob`, `check_version`, `step_10` e `step_11`, nessa ordem, ficam entre `step_9b` e `pytest_pin`. As da U6 (`profile_case`, `step_13`) ficam entre `step_12` e `run_selected`.
- **R-TV (`tests/test_verify_install.py`).**
  - `_HELP`, 2ª linha: `"passos: 1 2 3 4 5 6 7 8 9a 9b 10 11 12 13\n"`.
  - `test_step_ids_are_the_known_steps`: `assert _assign("STEP_IDS") == "1 2 3 4 5 6 7 8 9a 9b 10 11 12 13"`.
  - `test_usage_errors_exit_1_before_preparing`:
    - 1º parâmetro: `("--only", "15")`, com `"verify-install: uso: passo desconhecido 15. "` e `"Passos: 1 2 3 4 5 6 7 8 9a 9b 10 11 12 13."`;
    - 2º parâmetro: `"Passos: 1 2 3 4 5 6 7 8 9a 9b 10 11 12 13."`.
  - Testes novos: os dois blocos ficam, cada um no seu ponto (U7 depois de `test_step_8_checks_the_foreign_hook`, U6 depois de `test_pytest_pin_matches_pyproject`).
  - Contagem esperada depois das duas T3: 29 + 8 (U6) + 9 (U7) = **46 casos** em `tests/test_verify_install.py`.
- **R-MS (`src/bob_quality/messages.py`).** Fica com os dois lados, cada bloco de chaves na sua âncora (tabela acima). Nenhuma chave se repete entre a U6 e a U7: os prefixos são diferentes (`setup.profile*` × `version.*`, `update.*`, `cli.update`, `cli.version`).
- **R-HE (`tests/test_hermetic.py`).** `_UNIT_ARGS` fica exatamente:
  ```python
  _UNIT_ARGS: tuple[tuple[str, ...], ...] = (
      ("tests/test_project_version.py",),
      ("tests/test_update.py",),
      ("tests/test_hook_install.py",),
      ("tests/test_setup_cmd.py", "-k", "hook or profile"),
  )
  ```
- Qualquer conflito fora destas regras: **pare**, abra o PR como rascunho (ou, se já está aberto, ponha em "Bloqueios") com a saída do `git status` e do `git diff`, e não resolva por conta própria.

## Ordem sugerida de merge
1. **U6 T1 e U6 T2**, em qualquer ordem (não têm arquivo em comum).
2. **U7 T1**, depois **U7 T2** (em sequência: compartilham `messages.py` e `tests/test_hermetic.py`, e a T2 importa o módulo da T1). A U7 T1 pode rodar em paralelo com a U6 T1 e a U6 T2.
3. **U6 T3** (depende da U6 T1 e da T2).
4. **U7 T3** por último, com rebase (R-CL, R-VI1, R-TV).

Justificativa:
- A U6 é menor e as duas primeiras ETs dela rodam em paralelo, então tende a ficar pronta antes.
- Mergear a U6 T3 antes faz o passo 10 da U7 já rodar com o `install.sh` final (passo `perfil`) e o resumo final (linha `shell profile:`). Assim a U7 T3 prova o estado que a U8 vai documentar.
- A U7 T3 é a ET de maior risco de CI (rebrand do wheel, `npm ci` do venv novo). Deixá-la por último evita que um bloqueio nela segure a U6.
- As duas ordens funcionam: R-CL, R-VI1 e R-TV dão o mesmo resultado nas duas.

## Depois da U6 e da U7: o que a U8 encontra (2026-10-22)
A U8 só é despachada depois dos merges da U6 e da U7 (`../u8-docs/code-generation/code-generation-plan.md`). Ela parte destas formas finais e não reabre as regras acima:
- `scripts/verify-install.sh`: linhas 2 e 4 em R-VI1 (`… 12 e 13`); dispatch em R-VI2. A U8 T4 aplica a regra geral de R-VI1 com o id `14`. A linha 2 vira `… 12, 13 e 14.`, `STEP_IDS` vira `'1 2 3 4 5 6 7 8 9a 9b 10 11 12 13 14'` e entra `      14) step_14 ;;` logo depois de `      13) step_13 ;;`.
- `tests/test_verify_install.py`: 46 casos (R-TV). A U8 T4 leva a 54. `--only 15` continua sendo o id desconhecido.
- O laço de repasse de variáveis de `run_oneliner` (U6) e de `run_bob` (U7) vira `pass_env` na U8 T4. Os testes da U6 e da U7 que montam essas funções ganham só a definição de `pass_env`; as saídas esperadas não mudam.
- `tests/test_hermetic.py`: forma de R-HE; a U8 T1 acrescenta `("tests/test_docs_pins.py",),` logo depois de `("tests/test_update.py",),`.
- `CHANGELOG.md`: a U8 T3 e a U8 T4 seguem R-CL entre si. A que entra depois fica no topo; abaixo das duas vêm as entradas da U6 T3 e da U7 T3.
