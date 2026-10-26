# 3.7 CI Pipeline — Configuração da Pipeline de CI (`ci-config.md`)

- **Projeto:** `bob` (`fazedordecodigo/bob`)
- **Estágio:** 3.7 CI Pipeline
- **Ferramenta de CI/CD:** GitHub Actions (`.github/workflows/`)
- **Autor:** Arquiteto Técnico AI-DLC
- **Data:** 2026-10-24 (America/Sao_Paulo, UTC-3)

---

## 1. Visão Geral da Arquitetura de CI

O repositório `fazedordecodigo/bob` opera com **6 workflows GitHub Actions** versionados em `.github/workflows/`, cobrindo testes unitários/de componente em múltiplas versões de Python, dogfooding dos próprios quality gates do `bob`, empacotamento `.whl`/`.tar.gz`, verificação de instalação ponta a ponta num ambiente limpo (`verify-install.sh`), compilação estrita da documentação Docusaurus (`website/`) e pipeline de release multi-plataforma (`linux-x64`, `linux-arm64`, `macos-arm64`, `macos-x64`).

Todas as GitHub Actions de terceiros seguem a política de segurança do repositório (NFR6 / U9-N6): **pinagem por commit SHA de 40 caracteres hexadecimais** com comentário da tag semântica e `permissions: contents: read` por padrão no topo de cada workflow.

---

## 2. Catálogo dos Workflows (`.github/workflows/`)

| Arquivo | Nome do Workflow | Gatilhos (`on`) | Jobs | Runners | Propósito |
|---|---|---|---|---|---|
| `ci.yml` | `CI` | `push` (`main`), `pull_request` (`main`) | `pytest (3.10)`, `pytest (3.12)` | `ubuntu-latest` | Roda toda a suíte `pytest` (4907 testes, incluindo `tests/test_hermetic.py` e `tests/test_hook.py`) com Node 22 LTS e `gitleaks` 8.30.1 conferido por SHA-256 |
| `bob.yml` | `bob` | `pull_request` (`main`) | `check`, `cold` | `ubuntu-latest` | Dogfooding do próprio `bob`: roda `bob check --base origin/main --gates crap,dry,deps,mutate,coverage`, `gitleaks git` e `bob cold` |
| `package.yml` | `package` | `push` (`main`), `pull_request` (`main`) | `dist` | `ubuntu-latest` | Constrói `sdist` e `wheel` (`python -m build`), valida metadados (`twine check --strict dist/*`) e testa `bob --help` e `bob doctor` num venv limpo instalado a partir do `.whl` |
| `verify-install.yml` | `verify-install` | `push` (`main`), `pull_request` (`main`) | `linux-x64` (`timeout-minutes: 20`) | `ubuntu-latest` | Executa o harness ponta a ponta `sh scripts/verify-install.sh` (todos os 15 passos: `1..14`, com `9a` e `9b`) |
| `website.yml` | `website` | `push` (`main` com `website/**` ou `docs/**`), `pull_request` (`main` com `website/**` ou `docs/**`), `workflow_dispatch` | `build`, `deploy` (só `push` na `main`) | `ubuntu-latest` | Executa `npm ci`, `npm run build` (2 locales: `pt-BR` e `en`, com `onBrokenLinks: 'throw'` e `onBrokenAnchors: 'throw'`) e `npm test` |
| `release.yml` | `release` | `workflow_dispatch` (`tag`, `prerelease`, `dry_run`) | `check`, `verify` (matriz de 4 plataformas), `publish` | `ubuntu-latest`, `ubuntu-24.04-arm`, `macos-15-intel`, `macos-15` | Gera os 3 assets da release (`check`), roda `pytest` + `VERIFY_DIST=... sh scripts/verify-install.sh` nas 4 plataformas (`verify`) e, somente se `dry_run == false` e os 5 jobs anteriores passarem, cria a tag/release no GitHub (`publish`) |

---

## 3. Especificação Detalhada do Workflow de Release (`.github/workflows/release.yml` — U9)

### 3.1 Entradas (`workflow_dispatch`)
- `tag` (`string`, obrigatório, padrão `'v0.1.0'`): tag da release no formato `vX.Y.Z`.
- `prerelease` (`boolean`, opcional, padrão `true`): publica com `--prerelease --latest=false` (CT12 / U9-N4).
- `dry_run` (`boolean`, opcional, padrão `false`): quando `true` (ensaio `E0`), executa `check` e os 4 jobs de `verify` sem criar tag nem release (`publish` fica `SKIPPED`).

### 3.2 Topologia de Jobs e Permissões
1. **Permissão global no topo:** `permissions: contents: read` (U9-N5).
2. **Job `check` (`ubuntu-latest`, `timeout-minutes: 10`):**
   - Valida que `inputs.tag` casa com `^v[0-9]+\.[0-9]+\.[0-9]+$` e que é idêntica a `v<version>` lida de `pyproject.toml` (U9-N9).
   - Verifica que a tag ainda não existe no repositório remoto (`git ls-remote --exit-code --tags origin "refs/tags/$TAG"` deve sair `2`).
   - Constrói `dist/bob_quality-<ver>-py3-none-any.whl`, valida com `twine check --strict`, monta `dist/release/{bob_quality-<ver>-py3-none-any.whl, install.sh, SHA256SUMS}` conforme CT12 (U9-N1) e publica o artefato de workflow `release-assets` (`retention-days: 1`).
3. **Job `verify` (`needs: check`, `fail-fast: false`, `timeout-minutes: 30`):**
   - Matriz de 4 plataformas oficiais (NFR3, R-S1, U9-N3, U9-N8):
     - `linux-x64`: runner `ubuntu-latest`, asset `gitleaks_8.30.1_linux_x64.tar.gz`, sha256 `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b6f2470ef`
     - `linux-arm64`: runner `ubuntu-24.04-arm`, asset `gitleaks_8.30.1_linux_arm64.tar.gz`, sha256 `e4a487ee7ccd7d3a7f7ec08657610aa3606637dab9242fb529db5fb4ef2d33d5`
     - `macos-arm64`: runner `macos-15`, asset `gitleaks_8.30.1_darwin_arm64.tar.gz`, sha256 `b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13d87fd5be23b45`
     - `macos-x64`: runner `macos-15-intel`, asset `gitleaks_8.30.1_darwin_x64.tar.gz`, sha256 `dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a31f4ffbe845507`
   - Em cada runner:
     - Baixa o artefato `release-assets` produzido pelo job `check` e confere `SHA256SUMS` e a igualdade byte a byte `cmp -s dist/release/install.sh scripts/install.sh`.
     - Instala `gitleaks` 8.30.1 num diretório dedicado fora do `PATH` global (`$RUNNER_TEMP/gitleaks-ci`) para alimentar apenas o passo `pytest` (mantendo o `PATH` do harness `verify-install.sh` livre de `gitleaks` pré-instalado, conforme U3-N11).
     - Executa `PATH="$RUNNER_TEMP/gitleaks-ci:$PATH" pytest`.
     - Executa `VERIFY_DIST="$PWD/dist/release" sh scripts/verify-install.sh` (todos os 15 passos usando o `.whl` real do run — U9-N2, U9-N10).
4. **Job `publish` (`needs: [check, verify]`, `if: ${{ inputs.dry_run != true }}`, `permissions: contents: write`, `timeout-minutes: 10`):**
   - Baixa `release-assets`, revalida `SHA256SUMS` e executa `gh release create "$TAG" --verify-tag=false --target "$GITHUB_SHA" --title "$TAG" --generate-notes $FLAGS bob_quality-*.whl install.sh SHA256SUMS` (com `--prerelease --latest=false` quando `inputs.prerelease == true`).

---

## 4. Pinagem de Actions (Supply-Chain Security)

| Action | Commit SHA pinado | Versão |
|---|---|---|
| `actions/checkout` | `34e114876b0b11c390a56381ad16ebd13914f8d5` | `v4` |
| `actions/setup-python` | `a26af69be951a213d495a4c3e4e4022e16d87065` | `v5` |
| `actions/setup-node` | `49933ea5288caeca8642d1e84afbd3f7d6820020` | `v4` |
| `actions/upload-artifact` | `ea165f8d65b6e75b540449e92b4886f43607fa02` | `v4` |
| `actions/download-artifact` | `d3f86a106a0bac45b974a628896c90dbdf5c8093` | `v4` |

Essa pinagem é verificada automaticamente na suíte por `tests/test_action_workflow.py`, `tests/test_verify_install_workflow.py` e `tests/test_release_workflow.py`.
