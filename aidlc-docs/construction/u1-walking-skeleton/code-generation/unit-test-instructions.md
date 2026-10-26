# U1 — Instruções de teste da unit

## Preparação (igual ao `AGENTS.md` e ao `ci.yml`)
1. Python 3.10 ou 3.12 com `venv`/`ensurepip`; Node `>=22.18.0 <23` com `npm`; `git`, `curl`, `sha256sum`; `dash` (o `ubuntu-latest` tem).
2. `python -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'`.
3. `npm ci` na raiz.
4. gitleaks 8.30.1 no `PATH`, conferido por sha256 como no `ci.yml`.
5. `rm -rf src/bob_quality/node_modules` (muda o prefixo que `npm_prefix()` escolhe).
6. Para o harness: nenhum `bob` no `PATH` limpo (`/usr/bin:/bin` + Node + Python base). O venv `.venv` não entra no `PATH` do harness (D23).
7. Nada de `.bob/`, `mutants/`, `dist/`, `node_modules/` no commit.

## Comando por tarefa (não é o comando geral)
| Tarefa | Comando escopado |
|---|---|
| T1 | `python -m pytest -q tests/test_package.py tests/test_packaging.py tests/test_skills_contract.py` |
| T2 | `python -m pytest -q tests/test_project_skills.py tests/test_packaging.py tests/test_package.py` |
| T3 | `python -m pytest -q tests/test_user_dirs.py tests/test_setup_cmd.py tests/test_usage_exit.py tests/test_messages.py tests/test_project_skills.py` |
| T4 | `python -m pytest -q tests/test_install_sh.py` (≤ 180 s) |
| T5 | `python -m pytest -q tests/test_verify_install.py tests/test_install_sh.py` e `sh scripts/verify-install.sh` |
| T6 | `python -m pytest -q tests/test_verify_install_workflow.py` |
Esperado: última linha `N passed` com `0 failed` e sem `error`. `skipped` só os que já pulam na `main` (os testes de wheel pulam sob mutmut e sob o coverage do gate CRAP: padrão existente `_skip_under_mutmut`).

## Regressão
`python -m pytest -q` → `0 failed`, `0 errors` em cada PR. Linha de base: `main` @ `053dcaab` (4118 passed no head do #183).

## Comando de Verificação da U1 (DoD 3)
`sh scripts/verify-install.sh --only 1,2,3,4,7,8,9b` (= sem `--only` enquanto só existirem esses passos) → exit 0; 7 linhas `verify-install: passo <n>: ok`; ≤ 15 min.

## Metas
- Linhas novas/alteradas em `src/`: 100% cobertas (piso 80,0 mantido).
- CRAP < 10 por função alterada; mutate: 0 sobreviventes sem waiver; 0 waivers novos.
- `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → exit 0.
- `scripts/*.sh`: `sh -n` e `dash -n` → 0 (os gates do bob não medem shell; a prova é o pytest + o harness).

## Dados e dublês
| Dublê | Onde | Para quê |
|---|---|---|
| plugin sintético (`alpha`, `beta`, `LICENSE`, manifesto) | `test_project_skills.py` | regras de posse sem depender das skills reais |
| `_digest(root)` (sha256 + tipo + `st_mtime_ns`/alvo) | `test_project_skills.py`, `test_install_sh.py`, harness | 0 bytes e 0 escritas |
| `git_project` (git init + `src/app.py` + 1 commit) | `test_setup_cmd.py`, `test_install_sh.py`, harness | projeto novo (R-S8) |
| `monkeypatch` de `STEPS`, `doctor.run_doctor`, `npm_tools.*`, `_node_version_text`, `_python_floor` | `test_setup_cmd.py` | sem rede e sem `npm ci` |
| wheel sintético `bob_quality-9.9.9` com `bob` falso (`FAKE_BOB_LOG`, `FAKE_BOB_RC`) | `test_install_sh.py` | `install.sh` sem PyPI |
| `ThreadingHTTPServer` local com log de requisições | `test_install_sh.py` | espelho `BOB_RELEASES_URL` |
| `_toolbox` (só os comandos permitidos + stubs `node`, `npm`, `uname`, `python3`) | `test_install_sh.py` | pré-requisitos ausentes/velhos sem mexer no sistema |
| espelho `T/mirror` + `http.server`, `sudo` falso, `node` 20 falso, gitleaks em cache | `scripts/verify-install.sh` | Comando de Verificação |

## Mapa teste → regra/pronto
| Regra / Pronto | Prova |
|---|---|
| Pronto 1 (one-liner sai 0, `bob doctor: 0`) | harness passo 2; `test_full_install_via_the_mirror`; `test_all_steps_pass_and_doctor_0_exits_0` |
| Pronto 2 (≤ 300 s) | harness passo 2 (`tempo`) |
| Pronto 3 (skills só em `.agents/skills`) | harness passo 4; `test_install_creates_only_agents_skills`; `test_default_source_installs_the_three_bob_skills` |
| Pronto 4 (Node 20 falso) | harness passo 1; `test_failed_prerequisite_writes_nothing[node_out]` |
| Pronto 5 (sem `sudo`) | harness passo 3; `test_install_sh_never_mentions_sudo` |
| Pronto 6 (2ª execução) | harness passo 7; `test_second_install_writes_nothing`; `test_second_run_reuses_the_venv`; `test_npm_step_skips_npm_ci_when_the_prefix_matches` |
| Pronto 7 (skill alheia) | harness passo 8; `test_foreign_folder_is_preserved_byte_for_byte`; `test_skills_step_reports_installed_preserved_and_warnings` |
| Pronto 8 (wheel adulterado) | harness passo 9b; `test_tampered_wheel_exits_4_and_creates_no_version`; `test_missing_wheel_line_is_an_integrity_failure` |
| Pronto 9 (teste do wheel) | `test_wheel_ships_the_plugin_skills_manifest_and_license`; `test_installed_wheel_installs_agents_skills_without_a_clone` |
| CT4 regras 1–6 | `test_project_skills.py` (17 testes) |
| CT1 / NFR9 (en e pt-BR) | `test_failed_prerequisite_writes_nothing[*-en|pt-BR]`, `test_usage_errors_exit_4`, `test_first_failed_step_stops_and_prints_a_partial_summary[en|pt-BR]`, `test_setup_messages_exist_in_both_languages` |
| I9 paridade | `test_node_and_python_ranges_match_the_package`, `test_bob_home_matches_user_dirs`, `test_relative_bob_home_matches_user_dirs`, `test_single_source_lines` |
| FR2.4 / NFR5 (manifestos do projeto) | `test_setup_does_not_touch_the_project_package_files`; harness passo 8 |
