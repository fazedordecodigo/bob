# U7 — Instruções de testes unitários

## Preparação
- Python 3.10+ com `pip install -e '.[dev]'` (como no CI). `/bin/sh` POSIX (dash no CI) e `git`.
- Rede: não precisa, exceto no harness (passos 2, 8, 10 e 11).
- `tests/test_project_version.py`: só arquivos em `tmp_path`.
- `tests/test_update.py`:
  - `urlopen` falso;
  - `importlib.metadata.version` trocado;
  - `BOB_HOME` em `tmp_path`;
  - `tempfile.tempdir` em `tmp_path / "t"`.
  - Os únicos processos reais são `git init` e um `sh` com um `install.sh` falso que só grava um log.
- Nenhum teste lê o `HOME` real nem fala com `api.github.com`.

## Comando por tarefa
| Tarefa | Comando | Esperado |
|---|---|---|
| T1 | `python -m pytest -q tests/test_project_version.py tests/test_project_skills.py tests/test_doctor.py tests/test_hermetic.py tests/test_messages.py` | exit 0; `162 passed` (43 + 20 + 85 + 4 + 10) |
| T2 | `python -m pytest -q tests/test_update.py tests/test_usage_exit.py tests/test_hermetic.py tests/test_messages.py` | exit 0; `172 passed` (78 + 79 + 5 + 10). Com a U6 T2 mergeada, a contagem não muda: ela troca uma linha da guarda, sem criar parâmetro |
| T3 | `python -m pytest -q tests/test_verify_install.py` e `sh scripts/verify-install.sh --only 11` | exit 0; `46 passed` (ou `38 passed` sem a U6 T3); harness com `… passo 8: ok`, `… passo 10: tempo <s> s` (≤ 300), `… passo 10: ok`, `… passo 11: tempo <s> s` (≤ 30) e `… passo 11: ok` |

## Hermeticidade (U5-N16)
- `python -m pytest -q tests/test_hermetic.py` → exit 0, com `test_u5_tests_open_no_network[tests/test_project_version.py]` e `[tests/test_update.py]`.
- Medida manual:
  - `BOB_NET_GUARD_LOG=$(mktemp) PYTHONPATH=tests/net_guard python -m pytest -q -p no:cacheprovider tests/test_update.py` → exit 0, com o log de 0 bytes;
  - o mesmo para `tests/test_project_version.py`.

## Regressão
- `python -m pytest -q` → exit 0, `0 failed`, sem `error`, em toda tarefa.
- `tests/test_doctor.py`: os 81 casos existentes passam com só o ajuste A1 da T1 (`_expected_versions` ignora a última linha).
- `tests/test_usage_exit.py`: os 79 casos passam com A1–A3 da T2 (`_COMMANDS`, `_TOP_HELP`, `_SUB_HELP`).
- `tests/test_verify_install.py`: os casos existentes passam com A1–A3 da T3 (`_HELP`, `STEP_IDS`, `--only 15`).
- Harness inteiro (`sh scripts/verify-install.sh`) no check `verify-install / linux-x64` de cada PR:
  - 11 linhas `ok` na T1 e na T2 (12 com a U6 T3);
  - 14 a partir da T3 com a U6 T3 (13 sem ela).

## Comando de Verificação (subconjunto U7)
- **Passo 2 (parcial):** `sh scripts/verify-install.sh --only 2` → `ok 2`, com `bob --version` = `bob $X` e `project skills: $X (.agents/skills)`.
- **Passo 10:** `sh scripts/verify-install.sh --only 10` (faz o 8 antes) → `ok 8`, `passo 10: tempo` ≤ 300 s e `ok 10`.
- **Passo 11:** `sh scripts/verify-install.sh --only 11` (faz o 8 e o 10 antes) → `ok 11`, com `passo 11: tempo` ≤ 30 s.
- **`VERIFY_REMOTE=1`:** os passos 10 e 11 imprimem "não se aplica (VERIFY_REMOTE=1)" e saem 0.

## Metas
`bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → exit 0:
- CRAP < 10 por função;
- 0 sobreviventes;
- 0 waivers novos;
- cobertura ≥ 80,0 e 100% das linhas novas de `src/`.

O clone `update.py` × `gitleaks.py` aparece no `dry` e não bloqueia. `gitleaks` com 0 achados (check `bob / check`).

## Mapa pronto → teste
| Pronto | Teste |
|---|---|
| 1 (update para v-nova, `--version`, `.bob-version`, preservação, doctor 0) | passo 10; `test_new_release_downloads_checks_and_runs_install_sh[en,pt-BR]`; `test_install_keeps_the_environment_and_pins_the_tag`; `test_cli_version_flag[2]` |
| 1 (pré-release fora) | passo 10 (pedidos exatos e o comando único num projeto novo) |
| 2 (2ª execução sem mudança) | passo 11; `test_up_to_date_prints_and_changes_nothing[same,newer]` |
| 3 (rascunho mais novo: nada muda) | passos 10 e 11 (nenhum pedido a `drafts/`) |
| C08 (linha `skills do projeto`) | `test_doctor_last_line_is_the_project_skills[4]`; `test_skills_line_reads_the_project`; `check_version` no passo 2 |
