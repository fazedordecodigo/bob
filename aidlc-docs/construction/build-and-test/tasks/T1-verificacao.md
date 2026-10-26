# Verificação de PR contra Especificação — Estágio 3.6 Build and Test — Tarefa T1

- **Projeto**: `bob` (`bob-quality`)
- **Estágio**: `3.6 Build and Test`
- **Tarefa**: `T1` (`construction/build-and-test/tasks/T1.md`, `sha256: 045b13a70242f891e37919655c8cea340677d5b0655c44e59d0879f635c38910`)
- **Agente**: `bc-f1452baf-a39f-5eae-ac1b-ea19b60f2441` ([ET-build-and-test-T1](https://cursor.com/agents/bc-f1452baf-a39f-5eae-ac1b-ea19b60f2441))
- **Pull Request**: [#217](https://github.com/fazedordecodigo/bob/pull/217) (`[3.6][T1] Guarda hermetica completa em test_hermetic.py (U4-N14)`)
- **Branch da tarefa**: `aidlc/build-and-test/t1-hermetic-u4-n14`
- **Branch base**: `main` (`a658abddf41570168bc9b9e3ff36a8a7d423cdc2`)
- **Commit verificado (HEAD)**: `bfdfa0ddba68c688a0b6619803fc484cde139800`
- **Rodadas de correção**: `0` (houve apenas ajuste na própria ET `T1.md` para remover menção a `ruff`, que não integra a toolchain do repositório, sem novo commit no código)
- **Status**: **Aprovado para merge** (`4/4` critérios `Atende`, `6/6` checks de CI verdes)

---

## 1. Escopo de arquivos (`git diff --name-only origin/main...HEAD`)

| Arquivo | Mudança | Permitido pela ET? |
|---|---|---|
| `tests/test_hermetic.py` | `MODIFIED` (`+5 / -1`) | Sim (único arquivo listado em "Arquivos a modificar") |

Nenhum arquivo fora do escopo (`src/bob_quality/`, `tests/net_guard/sitecustomize.py`, `.github/`, `scripts/`, `docs/`, `website/`, `aidlc-docs/`) foi tocado.

---

## 2. Tabela Critério → Status → Evidência

| Critério | Status | Evidência verificada |
|---|---|---|
| **C1**: `git diff --name-only origin/main...HEAD` lista **exclusivamente** `tests/test_hermetic.py`. | **Atende** | Verificado via API do GitHub no PR [#217](https://github.com/fazedordecodigo/bob/pull/217): `files = [{'path': 'tests/test_hermetic.py', 'additions': 5, 'deletions': 1, 'changeType': 'MODIFIED'}]`. |
| **C2**: Em `tests/test_hermetic.py`, `_UNIT_ARGS` contém exatamente as 9 tuplas especificadas (`test_init_config.py`, `test_project_version.py`, `test_update.py`, `test_docs_pins.py`, `test_hook_install.py`, `test_setup_cmd.py -k "bob_yaml or hook or profile"`, `test_verify_install.py`, `test_release_workflow.py`, `test_release_checks.py`). | **Atende** | Verificado em `tests/test_hermetic.py` no commit `bfdfa0ddba68c688a0b6619803fc484cde139800` (linhas 12–22): exatamente as 9 tuplas na ordem especificada, 66 linhas totais. |
| **C3**: `pytest tests/test_hermetic.py -v` termina com exit code `0` e `10 passed` (`test_net_guard_catches_a_connection` + as 9 parametrizações de `test_u5_tests_open_no_network`), comprovando que nenhum teste de `U4`, `U5`, `U7` ou `U9` abre socket de rede. | **Atende** | Saída literal colada no PR #217 e confirmada nos jobs `CI / pytest (3.10)` e `CI / pytest (3.12)`: `10 passed in 3.90s` (`test_net_guard_catches_a_connection` + 9 parametrizações `test_u5_tests_open_no_network[...]`), exit code `0`, `BOB_NET_GUARD_LOG` vazio. Fecha `U4-N14` mantendo `U5-N14`, `U7-N14` e `U9-N12`. |
| **C4**: Todas as linhas de `tests/test_hermetic.py` têm `<= 100` colunas, `pytest -q` (`4905 passed`) e `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` terminam com exit code `0`. | **Atende** | Verificado em `bfdfa0ddba68c688a0b6619803fc484cde139800`: largura máxima de linha `82` colunas (`<= 100`); `pytest -q` = `4905 passed, 3 warnings, 32 subtests passed`; `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` = exit `0` (`crap`, `dry`, `deps`, `mutate`, `coverage` todos `passed`, diff coverage `100.00%`). |

---

## 3. Checks de CI no GitHub (`bfdfa0ddba68c688a0b6619803fc484cde139800`)

| Workflow / Job | Status | Conclusão |
|---|---|---|
| `CI / pytest (3.10)` | `COMPLETED` | `SUCCESS` |
| `CI / pytest (3.12)` | `COMPLETED` | `SUCCESS` |
| `bob / check` | `COMPLETED` | `SUCCESS` |
| `bob / cold` | `COMPLETED` | `SUCCESS` |
| `package / dist` | `COMPLETED` | `SUCCESS` |
| `verify-install / linux-x64` | `COMPLETED` | `SUCCESS` |
