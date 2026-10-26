# U6 — Instruções de testes unitários

## Preparação
- Python 3.10+ com `pip install -e '.[dev]'` (como no CI). `/bin/sh` POSIX (dash no CI) e `git`.
- Rede: não precisa, exceto no harness (passo 13).
- Os testes de `tests/test_install_sh.py` sobem um espelho local (`127.0.0.1`). Cada instalação usa `HOME` e `TMPDIR` próprios num `mkdtemp`. Nenhum teste lê ou grava o perfil real do dev.
- Os testes `profile` de `tests/test_setup_cmd.py` só usam `monkeypatch.setenv`/`delenv` e `capsys`. Não criam arquivo.

## Comando por tarefa
| Tarefa | Comando | Esperado |
|---|---|---|
| T1 | `python -m pytest -q tests/test_install_sh.py` | exit 0; `79 passed` |
| T2 | `python -m pytest -q tests/test_setup_cmd.py tests/test_hermetic.py tests/test_messages.py` | exit 0; `197` casos em `test_setup_cmd.py`, `3` em `test_hermetic.py`, `10` em `test_messages.py` (`210 passed`) |
| T3 | `python -m pytest -q tests/test_verify_install.py` e `sh scripts/verify-install.sh --only 13` | exit 0; `37 passed` (ou `46 passed` se a U7 T3 já entrou); harness com `… passo 2: ok`, `… passo 13: tempo <s> s` (≤ 180) e `… passo 13: ok` |
| T4 | `python -m pytest -q tests/test_install_sh.py` e `python -m pytest -q tests/test_install_sh.py -k outside` | exit 0; `84 passed`; com `-k outside`: `5 passed, 79 deselected` |

## Hermeticidade (U5-N16)
- `python -m pytest -q tests/test_hermetic.py` → exit 0, com `test_u5_tests_open_no_network[tests/test_setup_cmd.py]` rodando `-k "hook or profile"`.
- Medida manual: `BOB_NET_GUARD_LOG=$(mktemp) PYTHONPATH=tests/net_guard python -m pytest -q -p no:cacheprovider tests/test_setup_cmd.py -k profile` → exit 0, com o log de 0 bytes.
- `tests/test_install_sh.py` fica fora da guarda: usa servidor em `127.0.0.1`, como antes da U6.

## Regressão
- `python -m pytest -q` → exit 0, `0 failed`, sem `error`, em toda tarefa.
- `tests/test_install_sh.py`: os 64 casos existentes passam com só os 4 ajustes listados na T1 (`_ALLOWED`, `_SOURCE_NAMES`/`_SOURCE`/`once`, `_CT2_STEPS`, `_assert_install_stdout`).
- `tests/test_install_sh.py` na T4: os 79 casos existentes passam sem edição (a T4 só acrescenta).
- `tests/test_setup_cmd.py`: os testes do resumo existentes passam sem edição (sem a variável, sem linha).
- Harness inteiro (`sh scripts/verify-install.sh`) no check `verify-install / linux-x64` de cada PR: 11 linhas `ok` na T1 e na T2; 12 a partir da T3 (14 com a U7 T3).

## Comando de Verificação (subconjunto U6)
- Passo 13: `sh scripts/verify-install.sh --only 13` (faz o 2 antes) → `ok 2` e `ok 13`.
- Passo 2: a última linha continua `  bob doctor: 0`. A linha `  shell profile: …` vem antes dela.

## Metas
`bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → exit 0:
- CRAP < 10 por função;
- 0 sobreviventes;
- 0 waivers novos;
- cobertura ≥ 80,0 e 100% das linhas novas de `src/`.

`gitleaks` com 0 achados (check `bob / check`).

## Mapa pronto → teste
| Pronto | Teste |
|---|---|
| 1 (terminal novo acha o `bob`) | passo 13 (a)–(c); `test_profile_line_sources_in_sh`; `test_profile_file_follows_the_shell[6]` |
| 2 (2ª execução sem mudança) | passo 13 (2 execuções); `test_second_run_is_already_marked` |
| 3 (perfil sem escrita: aviso e saída 0) | passo 13 (e); `test_unwritable_profile_warns_and_exits_0[en,pt-BR]` |
| CT3 (linha no resumo) | `test_profile_text_maps_each_value[16]`; `test_profile_line_sits_before_the_doctor_line[en,pt-BR]`; `test_profile_line_is_in_the_partial_summary`; `test_step_13_summary_lines_are_the_ct3_texts` |
| U6-N5 (0 arquivos fora do `HOME`; exceção `.zshrc` no `ZDOTDIR`) | `test_install_writes_nothing_outside_home[bash,sh,zsh]`; `test_zdotdir_outside_home_is_the_only_outside_write[new,existing]` |
