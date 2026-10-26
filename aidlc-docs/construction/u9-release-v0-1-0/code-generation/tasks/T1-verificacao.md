# Verificação de PR contra a especificação — U9 T1 (#216)

- **Projeto:** bob
- **Unit:** U9 (`u9-release-v0-1-0`)
- **Tarefa:** `ET-u9-release-T1` (`construction/u9-release-v0-1-0/code-generation/tasks/T1.md`, v1)
- **PR:** https://github.com/fazedordecodigo/bob/pull/216
- **Título:** `U9 T1: workflow release e VERIFY_DIST`
- **Branch:** `aidlc/u9-release/t1-release-workflow` → `main` (`1b107922bf6553660231f598d758258b96fc091c`)
- **Commit (head):** `ebc3476315c041e562a2914e7317b1e7785e92a9`
- **Agente:** `bc-cbbe0656-8905-5398-911d-c3f5cdc924cd` (`https://cursor.com/agents/bc-cbbe0656-8905-5398-911d-c3f5cdc924cd`)
- **Rodadas de correção:** 0
- **Data da verificação:** 2026-10-24 13:48 (UTC-3)
- **Veredito:** **Aprovado para checkpoint**

## 1–8. Checagens estruturais da skill

1. **Existência:** PR #216 aberto (`OPEN`, `isDraft: false`), branch `aidlc/u9-release/t1-release-workflow` apontando para `main` em `1b107922bf6553660231f598d758258b96fc091c`, título exato `U9 T1: workflow release e VERIFY_DIST`.
2. **Bloqueios / decisões:** Nenhum bloqueio e nenhuma decisão fora da ET. Passo 0 bateu 100% com a especificação (`1b107922bf6553660231f598d758258b96fc091c`, 7 workflows existentes, `485:build_wheel() {`, `495:  WHL="bob_quality-$X-py3-none-any.whl"`, `39:die_preparo() {`, `0` ocorrências de `VERIFY_DIST`, `40` `def test_` em `tests/test_verify_install.py`).
3. **Escopo de arquivos:** 4 arquivos no diff (`+476/-0`): `.github/workflows/release.yml` (novo, 207 linhas), `scripts/verify-install.sh` (modificado, +6/-0), `tests/test_release_workflow.py` (novo, 228 linhas) e `tests/test_verify_install.py` (modificado, +35/-0). Nenhum arquivo proibido tocado (`CHANGELOG.md`, `pyproject.toml`, outros workflows, `tests/test_hermetic.py` e `aidlc-docs/` intactos).
4. **Completude:** Todos os 2 arquivos de "Arquivos a criar" e os 2 de "Arquivos a modificar" estão presentes no commit `ebc3476315c041e562a2914e7317b1e7785e92a9`.
5. **Conformidade de conteúdo:**
   - `.github/workflows/release.yml`: sha256 `21d441c86a322b9fe43e4e128cd519d8891e2dd54402f2ade191e266ec69d99d` (blob git `ad02eb5`), 100% idêntico byte a byte ao anexo.
   - `scripts/verify-install.sh`: `grep -c VERIFY_DIST scripts/verify-install.sh` = `3`; diff restrito às 6 linhas exatas de R2 logo após `  WHL="bob_quality-$X-py3-none-any.whl"`; `sh -n` e `dash -n` ok.
   - `tests/test_release_workflow.py` e `tests/test_verify_install.py`: 0 linhas > 100 colunas UTF-8.
6. **Testes:**
   - `tests/test_release_workflow.py`: 7 funções de teste com os nomes exatos (`test_release_runs_only_by_hand_on_main`, `test_release_jobs_and_permissions`, `test_release_matrix_is_the_four_platforms`, `test_release_builds_the_three_assets`, `test_release_verify_runs_the_verification_command`, `test_release_publish_creates_the_release_from_the_notes`, `test_release_pins_actions_like_ci`).
   - `tests/test_verify_install.py`: `test_build_wheel_uses_verify_dist` parametrizado `[present, missing]` (2 casos novos, 40 funções anteriores intactas, total de 56 casos).
   - Zero `.skip`, `.only`, `xit`, `@Ignore` ou waivers novos.
7. **Dependências:** `pyproject.toml` não foi modificado.
8. **Evidência de execução (CI + local):**
   - `CI / pytest (3.10)`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110929301/job/120922297470`)
   - `CI / pytest (3.12)`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110929301/job/120922297256`)
   - `bob / check`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110929284/job/120922297219`)
   - `bob / cold`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110929284/job/120922297443`)
   - `package / dist`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110929305/job/120922297236`)
   - `verify-install / linux-x64`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110929279/job/120922297451`)
   - Local: `pytest tests/test_release_workflow.py tests/test_verify_install.py -q` → `63 passed in 0.44s`; `sh scripts/verify-install.sh` → `15 ok` (passo 2 em 15 s, passo 14 em 32 s); `python -m pytest -q` → `4891 passed, 32 subtests passed`.

## 9. Tabela Critério → Evidência → Status

| # | Critério da ET (`T1.md`) | Evidência verificada | Status |
|---|---|---|---|
| 1 | `.github/workflows/release.yml` com o sha256 do anexo (`21d441c86a322b9fe43e4e128cd519d8891e2dd54402f2ade191e266ec69d99d`) | Blob git `ad02eb5` (207 linhas), sha256 `21d441c86a322b9fe43e4e128cd519d8891e2dd54402f2ade191e266ec69d99d` | Atende |
| 2 | `grep -c VERIFY_DIST scripts/verify-install.sh` = `3` e o diff do harness é só o bloco R2 | `scripts/verify-install.sh:496-501` (`+6/-0`), `grep -c VERIFY_DIST` = `3`, `sh -n` e `dash -n` ok | Atende |
| 3 | 7 testes novos em `tests/test_release_workflow.py`, todos verdes | `tests/test_release_workflow.py:1-228` (`7 passed`) | Atende |
| 4 | 2 casos novos em `tests/test_verify_install.py` (`test_build_wheel_uses_verify_dist[present,missing]`), verdes; os 40 anteriores intactos | `tests/test_verify_install.py:1138-1170` (`56 passed` no arquivo; `63 passed` nos dois arquivos; `4891 passed` na suíte) | Atende |
| 5 | Checks obrigatórios do PR verdes (`bob / check`, `bob / cold`, `CI / pytest (3.10)`, `CI / pytest (3.12)`, `package / dist`, `verify-install / linux-x64`) | 6/6 checks `SUCCESS` no commit `ebc3476315c041e562a2914e7317b1e7785e92a9` + `sh scripts/verify-install.sh` (`15 ok`) | Atende |
| 6 | Só os 4 arquivos listados no diff (`.github/workflows/release.yml`, `scripts/verify-install.sh`, `tests/test_release_workflow.py`, `tests/test_verify_install.py`) | `gh pr view 216 --json changedFiles,files` → `changedFiles: 4`, `+476/-0` | Atende |
