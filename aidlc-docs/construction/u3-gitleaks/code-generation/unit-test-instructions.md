# U3 — Instruções de teste da unit

## Preparação (igual ao `AGENTS.md`, ao `ci.yml` e à U1)
1. Python 3.10 ou 3.12 com `venv`/`ensurepip`; Node `>=22.18.0 <23` com `npm`; `git`, `curl`, `sha256sum`, `tar`; `dash`.
2. `python -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'`.
3. `npm ci` na raiz.
4. gitleaks 8.30.1 no `PATH`, conferido por sha256 como no `ci.yml` (para o gate do CI e os testes do gate `secrets`; o harness NÃO usa esse binário).
5. `rm -rf src/bob_quality/node_modules`.
6. Para o harness: nenhum `bob` e nenhum `gitleaks` no `PATH` limpo (`/usr/bin:/bin` + Node + Python base). Depois da T3, um `gitleaks` em `/usr/bin` faz o harness falhar de propósito (U3-N11).
7. Se a máquina do dev tem um bob instalado (`~/.local/share/bob-quality/bin/gitleaks`), os testes não podem depender dele: `tests/test_doctor.py` usa `BOB_HOME` vazio por fixture (D14). Para conferir: `BOB_HOME=/nao/existe python -m pytest -q tests/test_doctor.py` dá o mesmo resultado que sem a variável.
8. Nada de `.bob/`, `mutants/`, `dist/`, `node_modules/` no commit.

## Comando por tarefa (não é o comando geral)
| Tarefa | Comando escopado |
|---|---|
| T1 | `python -m pytest -q tests/test_gitleaks.py tests/test_messages.py` (≤ 60 s; sem internet; `tests/test_gitleaks.py` com 32 testes, ET v2) |
| T2 | `python -m pytest -q tests/test_setup_cmd.py tests/test_doctor.py tests/test_doctor_install.py tests/test_user_dirs.py tests/test_messages.py tests/test_gitleaks.py tests/test_verify_install.py` |
| T3 | `python -m pytest -q tests/test_verify_install.py` e `sh scripts/verify-install.sh --only 2,7,9a`, depois `sh scripts/verify-install.sh` |
| T4 | `python -m pytest -q tests/test_secrets_scan.py tests/test_check_dispatch.py tests/test_user_dirs.py` |
Esperado: última linha `N passed` com `0 failed` e sem `error`. `skipped` só os que já pulam na `main`.

## Regressão
`python -m pytest -q` → `0 failed`, `0 errors` em cada PR. Linha de base: `main` @ `387b0b6` (4322 passed no head do #190).

## Comando de Verificação da U3 (DoD 3)
`sh scripts/verify-install.sh --only 2,7,9a` → exit 0; 3 linhas `verify-install: passo <n>: ok` (2, 7, 9a), com `verify-install: passo 2: tempo <s> s` ≤ 300 e `verify-install: passo 7: tempo <s> s` ≤ 60. O harness inteiro (`1 2 3 4 7 8 9a 9b`) → exit 0, 8 linhas `ok`, ≤ 15 min (check `verify-install / linux-x64`).

## Metas
- Linhas novas/alteradas em `src/`: 100% cobertas (piso 80,0 mantido).
- CRAP < 10 por função alterada; mutate: 0 sobreviventes sem waiver; 0 waivers novos.
- `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → exit 0.
- `scripts/verify-install.sh`: `sh -n` e `dash -n` → 0.
- Testes de `gitleaks.py` sem internet (U3-N17).

## Mapa critério de pronto → teste
| Pronto (U3 / B3) | Prova |
|---|---|
| Pronto 1: tabela com os 4 assets e sha | `tests/test_gitleaks.py::test_assets_are_the_four_adr_0014_entries`; `::test_platform_key_maps_the_ct9_table` |
| Pronto 2: projeto novo sem gitleaks no `PATH`, passo 2 sem fixture, `BOB_HOME/bin/gitleaks version` = 8.30.1 | harness passo 2 (T3); `::test_ensure_installs_the_binary_and_the_link`; `test_setup_cmd.py::test_gitleaks_step_installs_when_missing` |
| Pronto 3: tar.gz adulterado → 4, cita `gitleaks` e "sha256", `BOB_HOME/tools/gitleaks` não existe | harness passo 9a (T3); `::test_tampered_archive_fails_integrity_and_installs_nothing[en,pt-BR]`; `test_setup_cmd.py::test_gitleaks_step_failure_stops_setup[en,pt-BR]` |
| Pronto 4: 2ª execução com 0 requisições | harness passo 7 (T3); `::test_second_ensure_downloads_nothing`; `test_setup_cmd.py::test_gitleaks_step_is_unchanged_when_present` |
| B3: "tira a fixture do gitleaks" | `test_verify_install.py::test_harness_has_no_gitleaks_fixture`; harness (todos os passos falham se o `PATH` tiver `gitleaks`) |
| B3: harness nos passos 2 (completo), 7 e 9a | `sh scripts/verify-install.sh --only 2,7,9a` → 0; check `verify-install / linux-x64` |
| FR2.1 (doctor acha o que o setup instalou) | `test_doctor.py::test_doctor_finds_gitleaks_in_bob_home_before_the_path`; harness passo 2 (`  bob doctor: 0` sem fixture) |
| CT14 (rede) | `::test_download_uses_a_30_s_timeout`, `::test_http_4xx_is_not_retried`, `::test_5xx_is_retried_twice`, `::test_network_error_is_retried_twice` |
