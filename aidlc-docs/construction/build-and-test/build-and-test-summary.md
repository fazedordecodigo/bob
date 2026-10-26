# Resumo de Build e Testes — Stage 3.6 Build and Test

## 1. Visão Geral da Fase 3.6
- **Repositório:** `https://github.com/fazedordecodigo/bob`
- **Branch principal verificada:** `main` (`787ea6546da14a417d3eda9171ad5a6d0ed64919`)
- **Unidades integradas:** `U1` (`u1-esqueleto-bob-setup`) a `U9` (`u9-release-v0-1-0`), todas com checkpoints aprovados pelo Emerson.
- **Artefatos gerados em `construction/build-and-test/`:**
  - `build-instructions.md` — instruções completas de build determinístico (`python -m build`, `twine check`, `SHA256SUMS`).
  - `integration-test-instructions.md` — instruções do Comando de Verificação (`scripts/verify-install.sh`, passos `1..14` com `9a`/`9b`, modo default e modo `VERIFY_DIST`) e do ensaio `E0` (`release.yml` com `dry_run: true`).
  - `cross-unit-traceability.md` — matriz ponta a ponta `US1..US9` / `FR1..FR9` / `NFR1..NFR11` / `CT1..CT19` → `U1..U9` → PRs → testes e passos do harness.
  - `test-results.md` — resultados consolidados de build, suíte `pytest` (`4907` testes, 100% verde nos 4 runners), guarda hermética (`tests/test_hermetic.py`), `verify-install.sh` (15/15 passos nos 4 runners) e ensaio `E0` (`release.yml` `dry_run: true` 100% verde nos 4 runners, `0` itens `"Não atende"` e `0` itens `"Não verificado"`).
  - `tasks/T1.md` e `tasks/T1-verificacao.md` — fechamento de `U4-N14` em `tests/test_hermetic.py` (PR [#217](https://github.com/fazedordecodigo/bob/pull/217), merge `55c4de7`).
  - `tasks/T2.md` e `tasks/T2-verificacao.md` — correção das 11 falhas de portabilidade macOS do `E0` Run 1 (PR [#221](https://github.com/fazedordecodigo/bob/pull/221), merge `fae853b`).
  - `tasks/T3.md` e `tasks/T3-verificacao.md` — alinhamento de `tests/test_security_mutants.py` a `.resolve()` no macOS (PR [#222](https://github.com/fazedordecodigo/bob/pull/222), merge `512e7d4`), deixando `pytest` (`4907 passed`) 100% verde nos 4 runners e `verify (macos-arm64)` 100% verde (15/15 passos).
  - `tasks/T4.md` e `tasks/T4-verificacao.md` — propagação de `PIP_CACHE_DIR` em `pass_env()` de `scripts/verify-install.sh` e `.github/workflows/release.yml` (PR [#226](https://github.com/fazedordecodigo/bob/pull/226), merge `787ea65`), fechando `verify (macos-x64)` com 15/15 passos verdes no ensaio `E0` Run 4.

## 2. Estado dos Workflows na `main` (`787ea6546da14a417d3eda9171ad5a6d0ed64919`)
1. **`CI` (`ci.yml`, run `40245001110`):**
   - `pytest (3.10)`: `success` (`4907 passed`)
   - `pytest (3.12)`: `success` (`4907 passed`)
2. **`package` (`package.yml`, run `40245001105`):**
   - `dist`: `success` (`python -m build` + `twine check` + smoke test em venv limpo)
3. **`verify-install` (`verify-install.yml`, run `40245001115`):**
   - `linux-x64`: `success` (`15/15` passos `ok`)
4. **`release` — Ensaio `E0` Run 4 (`release.yml`, run [`40245141721`](https://github.com/fazedordecodigo/bob/actions/runs/40245141721), `dry_run: true`):**
   - `check` (`121325014122`): `success`
   - `verify (linux-x64)` (`121325092564`): `success` (`4907 passed` + 15/15 passos `verify-install.sh` com `VERIFY_DIST`)
   - `verify (linux-arm64)` (`121325092574`): `success` (`4907 passed` + 15/15 passos `verify-install.sh` com `VERIFY_DIST`)
   - `verify (macos-arm64)` (`121325092568`): `success` (`4907 passed` + 15/15 passos `verify-install.sh` com `VERIFY_DIST`)
   - `verify (macos-x64)` (`121325092595`): `success` (`4907 passed` + 15/15 passos `verify-install.sh` com `VERIFY_DIST`: passo 2 em `28 s`, passo 5 em `12 s`, passo 6 em `2 s`, passo 7 em `2 s`, passo 10 em `29 s`, passo 11 em `0 s`, passo 12 em `22 s`, passo 13 em `17 s`, passo 14 em `71 s`)
   - `publish` (`121334934293`): `skipped` (conforme `dry_run: true`)

## 3. Veredito Final do Stage 3.6 Build and Test e Stage 3.7 CI Pipeline
- **Status:** **100% Concluído (`Atende` em todas as metas; `0` `"Não atende"` e `0` `"Não verificado"`).**
- O repositório está pronto para a revisão final dos estágios 3.6 e 3.7 pelo Emerson e eventual disparo de publicação real (`dry_run: false`) quando o Emerson desejar.
