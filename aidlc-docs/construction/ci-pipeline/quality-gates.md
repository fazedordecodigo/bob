# 3.7 CI Pipeline — Portões de Qualidade (`quality-gates.md`)

- **Projeto:** `bob` (`fazedordecodigo/bob`)
- **Estágio:** 3.7 CI Pipeline
- **Autor:** Arquiteto Técnico AI-DLC
- **Data:** 2026-10-24 (America/Sao_Paulo, UTC-3)

---

## 1. Portões Obrigatórios Antes de Merge em Pull Requests (`main`)

Todo Pull Request aberto contra a branch `main` precisa passar por **7 checks bloqueantes** antes do merge:

| # | Check do GitHub Actions | Workflow | O que valida | Critério de Aprovação (Binário) |
|---:|---|---|---|---|
| 1 | `CI / pytest (3.10)` | `ci.yml` | Suíte completa `pytest` em Python 3.10 + Node 22 + `gitleaks` 8.30.1 (inclui `test_hermetic.py` e `test_hook.py`) | Exit `0`, `0 failed`, `0 errors` (`4907 passed`) |
| 2 | `CI / pytest (3.12)` | `ci.yml` | Suíte completa `pytest` em Python 3.12 + Node 22 + `gitleaks` 8.30.1 | Exit `0`, `0 failed`, `0 errors` (`4907 passed`) |
| 3 | `bob / check` | `bob.yml` | `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` + `gitleaks git --no-banner --redact` | Exit `0`: CRAP `< 10` por função alterada; `0` mutantes sobreviventes sem waiver (`0` waivers novos); cobertura total `>= 80.0%` e `100%` das linhas alteradas em `src/`; `0` violações arquiteturais `deps`; `0` segredos no `gitleaks` |
| 4 | `bob / cold` | `bob.yml` | `bob cold --base origin/main --format json` | Exit `0` |
| 5 | `package / dist` | `package.yml` | `python -m build`, `twine check --strict dist/*` e instalação do `.whl` num venv limpo seguida de `bob --help` e `bob doctor` | Exit `0` em todas as etapas |
| 6 | `verify-install / linux-x64` | `verify-install.yml` | Execução completa do Comando de Verificação ponta a ponta `sh scripts/verify-install.sh` (15 passos: `1, 2, 3, 4, 5, 6, 7, 8, 9a, 9b, 10, 11, 12, 13, 14`) | Exit `0`; `15` linhas `verify-install: passo <id>: ok`; passo 2 `<= 300 s`, passo 5 `<= 180 s`, passo 6 `<= 60 s`, passo 7 `<= 60 s`, passo 10 `<= 300 s`, passo 11 `<= 30 s`, passo 12 `<= 240 s`, passo 13 `<= 180 s`, passo 14 `<= 360 s`, duração total `<= 900 s` |
| 7 | `website / build` | `website.yml` | `npm ci && npm run build && npm test` em `website/` (quando o PR toca `website/**` ou `docs/**`) | Exit `0`; build Docusaurus nos 2 locales (`pt-BR` e `en`) sem nenhum link ou âncora quebrada (`onBrokenLinks: 'throw'`, `onBrokenAnchors: 'throw'`) |

---

## 2. Limiares dos Gates de Qualidade de Código (`bob.yaml`)

Os limiares do próprio repositório `bob` são auditados a cada PR pelo job `bob / check` e permanecem intactos (nenhuma meta foi rebaixada em nenhuma unit):

| Gate | Parâmetro em `bob.yaml` | Meta exigida |
|---|---|---|
| `crap` | `crap.max_per_function` | `< 10` em toda função criada ou modificada |
| `coverage` | `coverage.min_percent` | `>= 80.0%` global + `100%` das linhas novas/alteradas em `src/` |
| `mutate` | sobreviventes em código alterado | `0` mutantes sobreviventes (`0` waivers adicionados em `.bob/waivers.yaml`) |
| `deps` | fronteiras de módulos | `0` ciclos ou importações proibidas |
| `dry` | duplicação estrutural (`jscpd`) | monitorado no relatório sem regressão de bloqueio |
| `secrets` | `gitleaks` 8.30.1 | `0` segredos vazados no histórico e no diff |

---

## 3. Portões Obrigatórios Antes de Publicar uma Release (`release.yml`)

A publicação de qualquer release (`vX.Y.Z`) é protegida pelo grafo `needs: [check, verify]` no workflow `.github/workflows/release.yml`:

1. **Gate `check`:**
   - Tag válida (`^v[0-9]+\.[0-9]+\.[0-9]+$`), igual a `v<version>` do `pyproject.toml`, e ainda inexistente no repositório.
   - `twine check --strict` verde e 3 assets (`bob_quality-<ver>-py3-none-any.whl`, `install.sh`, `SHA256SUMS`) gerados e conferidos.
2. **Gate `verify` (Matriz de 4 Plataformas: `linux-x64`, `linux-arm64`, `macos-arm64`, `macos-x64`):**
   - `pytest` completo (`0 failed`, `0 errors`) em cada uma das 4 plataformas.
   - `VERIFY_DIST="$PWD/dist/release" sh scripts/verify-install.sh` completo (`15/15` passos `ok`, passo 2 `<= 300 s`, passo 10 `<= 300 s`) consumindo o `.whl` e o `install.sh` exatos gerados pelo job `check`.
3. **Gate `publish`:**
   - Só executa se `check` e os 4 runners de `verify` terminarem com `SUCCESS` **e** `inputs.dry_run != true`.
   - Quando `inputs.prerelease == true`, passa obrigatoriamente `--prerelease --latest=false` ao `gh release create`, garantindo que pré-releases nunca sejam promovidas a `releases/latest` (FR1.4, FR6.1, NFR11, U9-N4).

---

## 4. Alinhamento entre Build and Test (3.6) e CI Pipeline (3.7)

| Comando validado no 3.6 Build and Test | Onde é imposto automaticamente no 3.7 CI Pipeline |
|---|---|
| `python -m build && twine check --strict dist/*` | `package.yml` (`package / dist`) e `release.yml` (`check`) |
| `pytest` (incluindo todas as suítes unitárias de `U1..U9`, `test_hermetic.py` e `test_hook.py`) | `ci.yml` (`pytest (3.10)` e `pytest (3.12)`) e `release.yml` (`verify` nos 4 runners) |
| `sh scripts/verify-install.sh` (15 passos ponta a ponta) | `verify-install.yml` (`verify-install / linux-x64`) e `release.yml` (`verify` nos 4 runners com `VERIFY_DIST`) |
| `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` | `bob.yml` (`bob / check`) e localmente no hook `pre-push` (`crap,dry,deps`) |
| `cd website && npm ci && npm run build && npm test` | `website.yml` (`website / build`) |
