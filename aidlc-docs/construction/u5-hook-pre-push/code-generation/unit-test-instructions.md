# U5 — Instruções de testes unitários

## Preparação
- Python 3.10+ com `pip install -e '.[dev]'` (como no CI); `git` ≥ 2.32 no `PATH` (usa `GIT_CONFIG_GLOBAL`). Rede: não precisa, exceto no e2e manual da T2, no passo 0 da T3 e no harness (npm, gitleaks, PyPI do pin do pytest).
- Os testes da U5 criam repositórios git em `tmp_path` (`git init -q`, `user.email`/`user.name` locais) e não tocam no checkout. `test_hook_install.py` e os testes `hook` de `test_setup_cmd.py` isolam a config global do git (`GIT_CONFIG_GLOBAL` para um arquivo vazio, `GIT_CONFIG_NOSYSTEM=1`): um `core.hooksPath` global na máquina do dev não muda o resultado.
- `tests/test_hook.py` precisa do `bob` ao lado do Python que roda os testes (`Path(sys.executable).parent / "bob"`), o que o `pip install -e` garante.

## Comando por tarefa
| Tarefa | Comando | Esperado |
|---|---|---|
| T1 | `python -m pytest -q tests/test_hook_install.py tests/test_hook.py tests/test_hermetic.py tests/test_messages.py` | exit 0; 37 casos em `test_hook_install.py`, 7 em `test_hook.py`, 2 em `test_hermetic.py`; `0 failed`; os 2 tempos medidos de `test_hook.py` < 60 s (`--durations=0`) |
| T2 | `python -m pytest -q tests/test_setup_cmd.py tests/test_hermetic.py tests/test_messages.py` | exit 0; 18 casos novos de `hook` + 16 de `_MESSAGES`; 3 casos em `test_hermetic.py`; `0 failed` |
| T3 | `python -m pytest -q tests/test_verify_install.py` e `sh scripts/verify-install.sh --only 6,7,8,12` | exit 0; harness com `… passo 2: ok`, `… 6: tempo <s> s`, `… 6: ok`, `… 7: ok`, `… 8: ok`, `… 12: tempo <s> s`, `… 12: ok` |

## Hermeticidade (U5-N16)
- `python -m pytest -q tests/test_hermetic.py` → exit 0. O controle positivo (`test_net_guard_catches_a_connection`) prova que a guarda pega uma conexão; `test_u5_tests_open_no_network[…]` roda os testes da U5 num pytest filho com `PYTHONPATH=tests/net_guard` e `BOB_NET_GUARD_LOG`, e exige log vazio.
- Medida manual equivalente: `BOB_NET_GUARD_LOG=$(mktemp) PYTHONPATH=tests/net_guard python -m pytest -q -p no:cacheprovider tests/test_hook_install.py` → exit 0 e o arquivo do log com 0 bytes.
- `rg -n "https?://" tests/test_hook_install.py` → exit 1 (nenhuma URL).
- Limite: git e node não passam pela guarda (não são Python). Nos testes da U5 eles só tocam `tmp_path`.

## Regressão
- `python -m pytest -q` → exit 0, `0 failed`, sem `error`, em toda tarefa.
- `test_setup_cmd.py::test_setup_does_not_touch_the_project_package_files` passa sem edição a partir da T2 (roda os `STEPS` reais, agora com `hook`, que grava só em `.git/hooks`).
- `tests/test_hook.py`: os 6 testes existentes passam sem edição de corpo a partir da T1 (só muda `_install_hook`).
- `src/bob_quality/hooks/pre-push` com o mesmo sha256 da `b142631` em todas as tarefas.
- Harness inteiro (`sh scripts/verify-install.sh`) no check `verify-install / linux-x64` de cada PR: 9 linhas `ok` até a T2; 11 a partir da T3.

## Comando de Verificação (subconjunto U5)
- Passo 6: `sh scripts/verify-install.sh --only 6` (faz o 2 antes) → `ok 2` e `ok 6`.
- Passos 7 e 8: `sh scripts/verify-install.sh --only 7,8` → `ok 2`, `ok 7`, `ok 8`.
- Passo 12: `sh scripts/verify-install.sh --only 12` → `ok 2` e `ok 12`.

## Metas
`bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → exit 0 (CRAP < 10 por função, 0 sobreviventes, 0 waivers novos, cobertura ≥ 80,0 e 100% das linhas novas de `src/`); `gitleaks` 0 achados (check `bob / check`).

## Mapa pronto → teste
| Pronto | Teste |
|---|---|
| 1 (push com `env -i` dispara o hook e roda `bob check --gates crap,dry,deps`) | harness passo 6; `test_render_hook_is_the_ct10_text`; `test_static_hook_runs_the_same_command`; `test_harness_expects_the_ct10_text`; `test_step_6_pushes_with_a_clean_env`; e2e da T2; passo 0 da T3 |
| 2 (`tests/test_hook.py` < 60 s) | `tests/test_hook.py` (7 testes, 2 medem < 60 s) no CI e no passo 12; `test_managed_hook_calls_the_bob_next_to_python` |
| 3a (hook alheio: mesmo hash, aviso) | harness passo 8; `test_install_preserves_a_foreign_hook[5]`; `test_install_never_follows_a_link_or_a_folder[2]`; `test_hook_step_preserves_a_foreign_hook[3]`; `test_hook_step_foreign_warning_reaches_the_output[en,pt-BR]`; `test_step_8_checks_the_foreign_hook` |
| 3b (`core.hooksPath`: nada gravado, aviso com a linha) | `test_install_respects_core_hooks_path[2]`; `test_hook_step_respects_core_hooks_path`; e2e da T2 (`hookspath`) |
