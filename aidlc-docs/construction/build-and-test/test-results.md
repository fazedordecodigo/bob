# Resultados de Testes e Matriz de Verificação — Stage 3.6 Build and Test

## 1. Resumo Executivo (Estado em `main` = `787ea6546da14a417d3eda9171ad5a6d0ed64919`)

| Dimensão | Meta | Medido (`main` `787ea65`) | Status Atual |
| --- | --- | --- | --- |
| **Build de distribuição (`package.yml`)** | Wheel `bob_quality-0.1.0-py3-none-any.whl` + sdist `bob_quality-0.1.0.tar.gz` + `twine check` + smoke test em venv limpo = `0` | Run `40245001105` (`dist` `success`) | **Atende** |
| **Suíte de testes unitários e de contrato (`ci.yml` + 4 runners de `release.yml`)** | `pytest` verde em Python `3.10` e `3.12` e nos 4 SOs/arquiteturas (`linux-x64`, `linux-arm64`, `macos-arm64`, `macos-x64`), 0 falhas | Run `40245001110` (`ci.yml`) e Run `40245141721` (`release.yml`): `4907 passed` em todos os 4 runners | **Atende** |
| **Guarda de hermeticidade (`U4-N14`, `T1` PR #217)** | `_UNIT_ARGS` cobre todas as 9 unidades (`U1`..`U9`), 10/10 testes em `tests/test_hermetic.py` verdes | `10 passed` em `tests/test_hermetic.py` (`main` desde `55c4de7`) | **Atende** |
| **Comando de Verificação (`verify-install.yml`, Linux x64)** | Passos 1..14 (`9a`/`9b`, 15 passos) de `scripts/verify-install.sh` = `0` | Run `40245001115` (`linux-x64` `success`, 15/15 passos) | **Atende** |
| **Ensaio de release `E0` (`release.yml` com `dry_run: true`) — Todos os 4 runners (`linux-x64`, `linux-arm64`, `macos-arm64`, `macos-x64`) + `check` + `publish` (`SKIPPED`) (`U9-N8`)** | `check` gera os 3 assets (`install.sh`, wheel, `SHA256SUMS`); `verify (linux-x64)`, `verify (linux-arm64)`, `verify (macos-arm64)` e `verify (macos-x64)` passam `pytest` (`4907 passed`) + 15/15 passos de `verify-install.sh` com `VERIFY_DIST`; `publish` fica `SKIPPED` | Run [`40245141721`](https://github.com/fazedordecodigo/bob/actions/runs/40245141721) (`check` `success`, `verify (linux-x64)` `success`, `verify (linux-arm64)` `success`, `verify (macos-arm64)` `success`, `verify (macos-x64)` `success`, `publish` `skipped`) | **Atende** |

---

## 2. Histórico de Execuções na Fase 3.6 Build and Test

### 2.1 Micro-ET `T1` — Fechamento da guarda hermética `U4-N14`
- **Especificação:** `construction/build-and-test/tasks/T1.md`
- **PR:** [#217](https://github.com/fazedordecodigo/bob/pull/217) (`bfdfa0ddba68c688a0b6619803fc484cde139800` → merge commit `55c4de7a00b10459313bea85dbdfb8f71698ddf5`)
- **Verificação:** `construction/build-and-test/tasks/T1-verificacao.md` (4/4 critérios `Atende`, 0 rodadas de correção)
- **Resultado:** Adicionadas as entradas de `U4` e `U9` em `_UNIT_ARGS` de `tests/test_hermetic.py`. `pytest -q tests/test_hermetic.py` → `10 passed`.

### 2.2 Ensaio `E0` — Execução 1 (Run `40129456138` sobre `55c4de7a00b10459313bea85dbdfb8f71698ddf5`)
- **URL:** `https://github.com/fazedordecodigo/bob/actions/runs/40129456138`
- **Resultado:** `check`, `verify (linux-x64)` e `verify (linux-arm64)` `success`; `verify (macos-arm64)` e `verify (macos-x64)` falharam com `11 failed, 4894 passed` em `pytest`.

### 2.3 Micro-ET `T2` — Portabilidade macOS (`darwin-arm64` / `darwin-x64`) para as 11 falhas do `E0` Run 1
- **Especificação:** `construction/build-and-test/tasks/T2.md`
- **PR:** [#221](https://github.com/fazedordecodigo/bob/pull/221) (`e70fb4a6c3ce3943dff24bd79a77048a59546282` → merge commit `fae853bed8b9c8fc0b52d5838f148882481142f0`)
- **Verificação:** `construction/build-and-test/tasks/T2-verificacao.md` (4/4 critérios `Atende`, 0 rodadas de correção)

### 2.4 Ensaio `E0` — Execução 2 (Run `40144457982` sobre `fae853bed8b9c8fc0b52d5838f148882481142f0`)
- **URL:** `https://github.com/fazedordecodigo/bob/actions/runs/40144457982`
- **Resultado:** Todas as 11 falhas originais do Run 1 passaram em `macos-arm64` e `macos-x64` (`4905 passed, 2 failed`), restando apenas `tests/test_security_mutants.py:89,108` sem `.resolve()` e sua cascata em `test_mutmut_dogfood.py`.

### 2.5 Micro-ET `T3` — Alinhar `tests/test_security_mutants.py` a `.resolve()` no macOS
- **Especificação:** `construction/build-and-test/tasks/T3.md`
- **PR:** [#222](https://github.com/fazedordecodigo/bob/pull/222) (`0237faa4e54695c6b84b287a078cc727f5866d59` → merge commit `512e7d4df85417c45574e0a5ce8a411ecc0bf5d2`)
- **Verificação:** `construction/build-and-test/tasks/T3-verificacao.md` (4/4 critérios `Atende`, 0 rodadas de correção)

### 2.6 Ensaio `E0` — Execução 3 (Run `40194253788` sobre `512e7d4df85417c45574e0a5ce8a411ecc0bf5d2`)
- **URL:** `https://github.com/fazedordecodigo/bob/actions/runs/40194253788`
- **Resultado:** `check`, `verify (linux-x64)`, `verify (linux-arm64)` e `verify (macos-arm64)` `success` (`4907 passed` + 15/15 passos `verify-install.sh`); em `verify (macos-x64)`, `pytest` passou `4907 passed` (100% nos 4 runners), mas `verify-install.sh` falhou no passo 2 porque `PIP_CACHE_DIR` não era repassado para dentro de `env -i HOME=$_home`.

### 2.7 Micro-ET `T4` — Propagar `PIP_CACHE_DIR` para `verify-install.sh` no `release.yml` (`macos-x64`)
- **Especificação:** `construction/build-and-test/tasks/T4.md`
- **PR:** [#226](https://github.com/fazedordecodigo/bob/pull/226) (`1dc10f1c9a4a9ff3b7593eb53b505e17dc8bf89b` → merge commit `787ea6546da14a417d3eda9171ad5a6d0ed64919`)
- **Verificação:** `construction/build-and-test/tasks/T4-verificacao.md` (5/5 critérios `Atende`, 8/8 verificações estruturais `Atende`, 0 rodadas de correção)

### 2.8 Ensaio `E0` — Execução 4 (Run `40245141721` sobre `787ea6546da14a417d3eda9171ad5a6d0ed64919` — **100% VERDE**)
- **URL:** `https://github.com/fazedordecodigo/bob/actions/runs/40245141721`
- **Inputs:** `tag=v0.1.0`, `prerelease=true`, `dry_run=true`
- **Resultado por job:**
  - `check` (`121325014122`): `success` (20:31:20 → 20:31:39 UTC-3)
  - `verify (linux-x64)` (`121325092564`): `success` (`4907 passed` em 1212,79 s + 15/15 passos de `verify-install.sh` com `VERIFY_DIST`)
  - `verify (linux-arm64)` (`121325092574`): `success` (`4907 passed` em 1013,08 s + 15/15 passos de `verify-install.sh` com `VERIFY_DIST`)
  - `verify (macos-arm64)` (`121325092568`): `success` (`4907 passed` em 1372,37 s + 15/15 passos de `verify-install.sh` com `VERIFY_DIST`)
  - `verify (macos-x64)` (`121325092595`): `success` (`4907 passed` em 2133,68 s + 15/15 passos de `verify-install.sh` com `VERIFY_DIST`: passo 1 `ok`, passo 2 `28 s ok`, passo 3 `ok`, passo 4 `ok`, passo 5 `12 s ok`, passo 6 `2 s ok`, passo 7 `2 s ok`, passo 8 `ok`, passo 9a `ok`, passo 9b `ok`, passo 10 `29 s ok`, passo 11 `0 s ok`, passo 12 `22 s ok`, passo 13 `17 s ok`, passo 14 `71 s ok`)
  - `publish` (`121334934293`): `skipped` (conforme `dry_run: true`)

---

## 3. Matriz Completa de Metas Não Funcionais (NFR) por Unidade (`U1`..`U9`)

### 3.1 `U1` — `u1-esqueleto-bob-setup` (Walking Skeleton + Harness)
| ID | Meta | Medido | Evidência | Status |
| --- | --- | --- | --- | --- |
| `U1-N1` | `scripts/verify-install.sh` executa passos 0 e 1 com exit `0` e imprime `VERIFY_INSTALL: PASS` | exit `0`, 15/15 passos (0..14) | `verify-install.yml` run `40144368266` e `E0` run `40144457982` (`linux-x64`, `linux-arm64`) | **Atende** |
| `U1-N2` | Cobertura de linhas e branches de `user_dirs.py` e `setup_cmd.py` = `100%` | `100%` lines e `100%` branches | `tests/test_user_dirs.py`, `tests/test_setup_skeleton.py`, `tests/test_hermetic.py` | **Atende** |
| `U1-N3` | Complexidade ciclomática máxima ≤ `10` e `CRAP` máximo ≤ `10` nos módulos da `U1` | CCN máx ≤ `10`, CRAP máx ≤ `10` (`0` violações) | `bob check --gates crap,dry,deps` verde | **Atende** |
| `U1-N4` | `0` chamadas de rede nos testes da `U1` (guarda hermética de socket) | `0` conexões externas (`10 passed` em `test_hermetic.py`) | `tests/test_hermetic.py` (`PR #217`) | **Atende** |
| `U1-N5` | `bob setup` sem `git` ou fora de repositório git retorna código `4` em `< 2 s` | exit `4` em `< 0.2 s` | `tests/test_setup_skeleton.py` e passo 13 de `scripts/verify-install.sh` | **Atende** |

### 3.2 `U2` — `u2-empacotamento-one-liner` (Wheel + `install.sh` + `bob setup` npm/gitleaks)
| ID | Meta | Medido | Evidência | Status |
| --- | --- | --- | --- | --- |
| `U2-N1` | Passo 2 (`install.sh` one-liner em `$HOME` virgem via espelho local) termina com `0` e instala wheel + npm + gitleaks `8.30.1` | exit `0`, binários operacionais | Passo 2 de `scripts/verify-install.sh` (`40144368266`, `40144457982`) | **Atende** |
| `U2-N2` | Passo 3 (reexecução idempotente do one-liner) termina com `0`, reutiliza venv/npm/gitleaks (`reutilizado`/`reused`) e mantém `digest` idêntico | exit `0`, `cmp -s before.manifest after.manifest` = `0` | Passo 3 de `scripts/verify-install.sh` | **Atende** |
| `U2-N3` | Passo 7 (`bob check` nos 4 portões: `crap`, `dry`, `deps`, `security`) retorna `0` em código limpo e `1` em segredo plantado (`gitleaks`) sem `npx`/`pip` em tempo de execução | `0` limpo; `1` com segredo AWS plantado | Passo 7 de `scripts/verify-install.sh` | **Atende** |
| `U2-N4` | Passo 8 (colisão em `~/.local/bin/bob` com arquivo/symlink alheio) preserva o arquivo alheio bit a bit e emite aviso acionável | exit `0`, arquivo alheio intacto | Passo 8 de `scripts/verify-install.sh` | **Atende** |
| `U2-N5` | Passo 11 (SHA-256 adulterado de wheel ou `gitleaks`) aborta com exit `4` antes de tocar em `$BOB_HOME` | exit `4`, `$BOB_HOME` inalterado | Passo 11 de `scripts/verify-install.sh` | **Atende** |
| `U2-N6` | Passo 13 (erros de ambiente: sem `git`, fora de repo, `BOB_HOME` relativo, `BOB_RELEASES_URL` HTTP não-local, tag inválida, Python/Node fora da faixa) retorna exit `4` | exit `4` em todos os subcasos | Passo 13 de `scripts/verify-install.sh` | **Atende** |
| `U2-N7` | `pyproject.toml` empacota `package.json`, `package-lock.json`, `js/flush-coverage.mjs` e `skills/` dentro do wheel (`0` arquivos faltando) | Todos presentes no wheel e sdist | `package.yml` (`40144368238`) + `tests/test_packaging_assets.py` | **Atende** |
| `U2-N8` | Cobertura de linhas e branches de `gitleaks.py` e `npm_tools.py` = `100%` | `100%` | `tests/test_gitleaks.py`, `tests/test_npm_tools.py`, `tests/test_hermetic.py` | **Atende** |
| `U2-N9` | `0` chamadas de rede reais na suíte da `U2` | `0` chamadas (`test_hermetic.py`) | `tests/test_hermetic.py` | **Atende** |
| `U2-N10` | `scripts/install.sh` compatível com POSIX `/bin/sh` (`sh -n scripts/install.sh` = `0`) | exit `0` | `tests/test_install_sh.py` | **Atende** |

### 3.3 `U3` — `u3-skills-empacotadas` (`.agents/skills/` com marcador de propriedade)
| ID | Meta | Medido | Evidência | Status |
| --- | --- | --- | --- | --- |
| `U3-N1` | Passo 4 de `scripts/verify-install.sh` instala as 5 skills em `.agents/skills/<nome>/SKILL.md` com marcador `<!-- bob-skill: version=0.1.0 sha256=<hex64> -->` na linha 1 | 5/5 instaladas e validadas | Passo 4 de `scripts/verify-install.sh` | **Atende** |
| `U3-N2` | Reexecução com skills intactas reporta `unchanged`; skill do `bob` editada localmente é restaurada; skill sem marcador ou de outro dono é preservada (`preserved`) com aviso | 100% dos cenários a..f do passo 4 verdes | Passo 4 de `scripts/verify-install.sh` + `tests/test_project_skills.py` | **Atende** |
| `U3-N3` | Sonda de `bob doctor` e `bob --version` refletem o estado real de `.agents/skills` (`0.1.0`, `diverged`, `missing`) | `100%` | `tests/test_project_skills.py`, `tests/test_doctor.py` | **Atende** |
| `U3-N4` | Cobertura de `install_skills.py` = `100%` (linhas e branches) | `100%` | `tests/test_project_skills.py`, `tests/test_hermetic.py` | **Atende** |
| `U3-N5` | `CRAP` ≤ `10` em todas as funções de `install_skills.py` | CRAP máx ≤ `10` | `bob check --gates crap,dry,deps` | **Atende** |
| `U3-N6` | Portabilidade Linux + macOS (`_remove_path` usa `shutil.rmtree` para diretórios reais sem chamar `unlink` em diretório no BSD/macOS) | `test_remove_path_uses_rmtree_for_real_dir_without_unlink` passou em Linux e macOS | `PR #221` (`T2`) + `E0` run `40144457982` (`macos-arm64` e `macos-x64`) | **Atende** |
| `U3-N7` | Escrita atômica por diretório temporário e preservação de symlinks/arquivos em `.agents/skills/<nome>` | `100%` | `tests/test_project_skills.py` | **Atende** |
| `U3-N8` | `0` chamadas de rede nos testes da `U3` | `0` chamadas | `tests/test_hermetic.py` | **Atende** |

### 3.4 `U4` — `u4-bob-yaml` (Geração e preservação de `bob.yaml` + `.bob/waivers.yaml`)
| ID | Meta | Medido | Evidência | Status |
| --- | --- | --- | --- | --- |
| `U4-N1`..`U4-N13` | Todas as 13 metas de detecção de `paths.include` (`[src]`, `[app]`, `["."]`), template CT7 exato, preservação bit a bit de `bob.yaml` e `.bob/waivers.yaml`, rejeição de `bob.yaml` inválido com exit `4`, CRAP ≤ `10` e cobertura `100%` de `init_config.py` | `13/13` `Atende` | `construction/u4-bob-yaml/checkpoint.md` + Passo 5 de `scripts/verify-install.sh` | **Atende** |
| `U4-N14` | Guarda hermética (`tests/test_hermetic.py`) inclui `tests/test_init_config.py` com `--cov=bob_quality.init_config` em `_UNIT_ARGS` | `10 passed` em `tests/test_hermetic.py` (incluindo `U4` e `U9`) | `PR #217` (`3.6 T1`, merge `55c4de7`) | **Atende** |

### 3.5 `U5` — `u5-hook-pre-push` (Hook `.git/hooks/pre-push` gerenciado — CT10)
| ID | Meta | Medido | Evidência | Status |
| --- | --- | --- | --- | --- |
| `U5-N1`..`U5-N16` | Todas as 16 metas do checkpoint da `U5` (template CT10 bit a bit, modo `0755`, LF, execução em `git push` com `env -i HOME PATH=/usr/bin:/bin`, `< 60 s`, preservação de hook alheio e `core.hooksPath`, cobertura `100%` de `hook_install.py`) | `16/16` `Atende` | `construction/u5-hook-pre-push/checkpoint.md` + Passos 6, 8 e 12 de `scripts/verify-install.sh` | **Atende** |

### 3.6 `U6` — `u6-perfil-shell` (`PATH` no perfil do shell — CT3 passo 8 / CT18)
| ID | Meta | Medido | Evidência | Status |
| --- | --- | --- | --- | --- |
| `U6-N1`..`U6-N11` | Todas as 11 metas do checkpoint da `U6` (`zsh` → `${ZDOTDIR:-$HOME}/.zshrc`, `bash` → `$HOME/.bashrc`, vazio/outro → `$HOME/.profile`, `already-on-path`, `already-marked`, `failed` não-fatal com exit `0`, e leitura de `ENVIRON["SHELL"]` via `awk` portável ao `/bin/sh` do macOS) | `11/11` `Atende` | `construction/u6-perfil-shell/checkpoint.md` + `PR #221` (`T2`) + Passo 9 de `scripts/verify-install.sh` | **Atende** |

### 3.7 `U7` — `u7-update-versao` (`bob update` e `bob --version` — CT4 / CT11)
| ID | Meta | Medido | Evidência | Status |
| --- | --- | --- | --- | --- |
| `U7-N1`..`U7-N13` | Todas as 13 metas do checkpoint da `U7` (atualização fim a fim `v0.1.0` → `v99.0.0`, filtro de `prerelease` e `draft`, no-op quando já na última versão, poda mantendo apenas `current` e a versão anterior imediata, rollback em falha, cobertura `100%` de `update_cmd.py`) | `13/13` `Atende` | `construction/u7-update-versao/checkpoint.md` + Passos 10, 11 e 13 de `scripts/verify-install.sh` | **Atende** |

### 3.8 `U8` — `u8-docs` (`README.md`, `README.pt-BR.md`, `docs/install-prompt.en.md`, `docs/install-prompt.pt-BR.md` — CT17 / CT18)
| ID | Meta | Medido | Evidência | Status |
| --- | --- | --- | --- | --- |
| `U8-N1`..`U8-N13` | Todas as 13 metas do checkpoint da `U8` (one-liner no topo nos 4 docs, pins sincronizados com `pyproject.toml`, `package.json`, `gitleaks.py` e `install.sh`, 14 blocos `bob-step` por plataforma e equivalência de estado final no passo 14 entre `install.sh` e os 14 blocos de `docs/install-prompt.en.md`) | `13/13` `Atende` | `construction/u8-docs/checkpoint.md` + `PR #221` (`T2`) + Passo 14 de `scripts/verify-install.sh` | **Atende** |

### 3.9 `U9` — `u9-release-v0-1-0` (`.github/workflows/release.yml`, `verify-install.yml` e `scripts/verify-install.sh` `VERIFY_DIST` — CT12 / CT19)
| ID | Meta | Medido | Evidência | Status |
| --- | --- | --- | --- | --- |
| `U9-N1` | Os 3 assets de release saem idênticos ao CT12 (`install.sh`, `bob_quality-0.1.0-py3-none-any.whl`, `SHA256SUMS`) | `check` gerou e validou os 3 assets (`121022724532`) | `E0` run `40144457982` + `tests/test_release_workflow.py` | **Atende** |
| `U9-N2` | `verify` usa o wheel do run via `VERIFY_DIST` (`cmp` de `install.sh` + `shasum -a 256 -c SHA256SUMS`) | Validado em `linux-x64` e `linux-arm64` (15/15 passos com `VERIFY_DIST`) | `E0` run `40144457982` (`121022785200`, `121022785155`) | **Atende** |
| `U9-N3` | Matriz de 4 plataformas (`linux-x64`, `linux-arm64`, `macos-arm64`, `macos-x64`) + `publish` com `needs: [check, verify]` | Estrutura verificada em `release.yml` e executada no `E0` | `tests/test_release_workflow.py` + `E0` run `40144457982` | **Atende** |
| `U9-N4` | `dry_run: true` executa `check` e `verify` completos e pula `publish` (`SKIPPED`), sem criar tag ou GitHub Release | `publish` = `skipped` (`121030700098`), 0 releases criadas | `E0` run `40144457982` | **Atende** |
| `U9-N5` | `verify-install.yml` roda em `push` para `main` e `pull_request` sem filtro `paths` | `verify-install.yml` ativo e verde (`40144368266`) | `.github/workflows/verify-install.yml` + `tests/test_release_workflow.py` | **Atende** |
| `U9-N6` | Todas as `uses:` em `release.yml` e `verify-install.yml` pinadas por commit SHA de 40 hex | `100%` pinadas por SHA-40 | `tests/test_release_workflow.py::test_workflows_pin_every_action_by_full_commit_sha` | **Atende** |
| `U9-N7` | Permissões mínimas (`contents: read` no topo; `contents: write` só em `publish`) | Verificado | `tests/test_release_workflow.py::test_release_workflow_permissions_are_minimal` | **Atende** |
| `U9-N8` | Ensaio `E0` (`release.yml` com `dry_run: true`) passa 100% nos 4 runners (`linux-x64`, `linux-arm64`, `macos-arm64`, `macos-x64`) | `check`, `verify (linux-x64)`, `verify (linux-arm64)`, `verify (macos-arm64)` e `verify (macos-x64)` `success` (`4907 passed` + 15/15 passos de `verify-install.sh` com `VERIFY_DIST` em todos os 4 runners); `publish` `skipped` | Run [`40245141721`](https://github.com/fazedordecodigo/bob/actions/runs/40245141721) (`main` `787ea65`, após merge do `PR #226` / `T4`) | **Atende** |
| `U9-N9`..`U9-N13` | Guardas de branch (`refs/heads/main`), paridade `tag == v<pyproject.toml>`, recusa de tag já existente, orçamento de linhas ≤ 100 col e cobertura 100% | `5/5` `Atende` | `construction/u9-release-v0-1-0/checkpoint.md` + `tests/test_release_workflow.py` | **Atende** |
