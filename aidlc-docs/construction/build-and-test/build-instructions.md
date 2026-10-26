# 3.6 Build and Test — Instruções de Build (`build-instructions.md`)

- **Projeto:** `bob` (`fazedordecodigo/bob`, pacote Python `bob-quality` `0.1.0`, CLI `bob`)
- **Estágio:** 3.6 Build and Test
- **Escopo / Estratégia de testes:** `mvp` sob medida (sem Operação) / `Standard`
- **Autor:** Arquiteto Técnico AI-DLC
- **Data:** 2026-10-24 (America/Sao_Paulo, UTC-3)

---

## 1. Pré-requisitos de Ambiente

| Ferramenta | Versão exigida | Origem / Contrato |
|---|---|---|
| Sistema operacional | Linux (`x86_64`, `aarch64`/`arm64`) ou macOS (`x86_64`, `arm64`) | NFR3, R-S1, ADR 0014 |
| Python | `>=3.10` (matriz de CI: `3.10` e `3.12`) com `venv` e `ensurepip` | `pyproject.toml` (`requires-python = ">=3.10"`), CT5 |
| Node.js + npm | `>=22.18.0 <23` (pinado na série 22 LTS) | `package.json` (`engines.node`), CT8, ADR 0008 |
| Git | `>=2.32` (`GIT_CONFIG_GLOBAL` e `GIT_CONFIG_NOSYSTEM`) | U5 (`unit-test-instructions.md`) |
| Shell POSIX | `/bin/sh` compatível com POSIX (`dash` no Debian/Ubuntu, `/bin/sh` no macOS) | CT2, U1-N11 |
| Utilitários de sistema | `curl`, `tar`, `sha256sum` (ou `shasum -a 256` no macOS) | CT2, CT9, ADR 0014 |
| `gitleaks` (para suíte de gates e CI) | `8.30.1` no `PATH`, conferido por SHA-256 oficial por plataforma | ADR 0014, CT9, `.github/workflows/ci.yml` |

### SHA-256 oficiais do `gitleaks` 8.30.1 (ADR 0014 / `src/bob_quality/gitleaks.py`)
- `linux_x64`: `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b6f2470ef`
- `linux_arm64`: `e4a487ee7ccd7d3a7f7ec08657610aa3606637dab9242fb529db5fb4ef2d33d5`
- `darwin_x64`: `dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a31f4ffbe845507`
- `darwin_arm64`: `b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13d87fd5be23b45`

---

## 2. Instalação de Dependências de Desenvolvimento

Na raiz do repositório:

```sh
python3 -m venv /tmp/dev
/tmp/dev/bin/pip install --upgrade pip build twine
/tmp/dev/bin/pip install -e '.[dev]'
npm ci
rm -rf src/bob_quality/node_modules
```

> **Nota importante (`npm_prefix`):** a pasta `src/bob_quality/node_modules` não deve existir durante os testes no checkout de desenvolvimento para não alterar a precedência de `npm_prefix()` (U1/U2 `unit-test-instructions.md`).

Para a documentação Docusaurus (`website/`, U8/U9):

```sh
cd website
npm ci
```

---

## 3. Comandos de Build

### 3.1 Build do pacote Python (`wheel` e `sdist`)
O pacote `bob-quality` usa `hatchling` (`pyproject.toml`) e inclui dentro do wheel (`src/bob_quality/plugin/`):
- `.claude-plugin/plugin.json`
- `skills/bob-check/SKILL.md`, `skills/harden/SKILL.md`, `skills/review-report/SKILL.md`
- `LICENSE`
- `package.json` e `package-lock.json` (fonte única das ferramentas npm pinadas — ADR 0008, ADR 0010)

```sh
rm -rf dist
/tmp/dev/bin/python -m build
/tmp/dev/bin/twine check --strict dist/*
```

Saídas geradas em `dist/`:
- `dist/bob_quality-0.1.0-py3-none-any.whl`
- `dist/bob_quality-0.1.0.tar.gz`

### 3.2 Montagem dos 3 Assets de Release (Contrato CT12 / U9 `release.yml`)
Cada release GitHub (`v<X.Y.Z>`) publica exatamente 3 arquivos em `dist/release/`:

```sh
rm -rf dist/release
mkdir -p dist/release
cp dist/bob_quality-0.1.0-py3-none-any.whl dist/release/
cp scripts/install.sh dist/release/install.sh
(
  cd dist/release
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum install.sh bob_quality-0.1.0-py3-none-any.whl
  else
    shasum -a 256 install.sh bob_quality-0.1.0-py3-none-any.whl
  fi
) | LC_ALL=C sort -k2 > dist/release/SHA256SUMS
```

Os 3 assets resultantes são:
1. `bob_quality-0.1.0-py3-none-any.whl`
2. `install.sh` (cópia byte a byte de `scripts/install.sh`)
3. `SHA256SUMS` (duas linhas `<64 hex>  <nome>`, ordenadas por nome com `LC_ALL=C sort -k2`)

### 3.3 Build do Site de Documentação (`website/`)

```sh
cd website
npm run build
npm test
```

O Docusaurus compila os 2 locales (`pt-BR` e `en`) com `onBrokenLinks: 'throw'` e `onBrokenAnchors: 'throw'`, validando todas as páginas de instalação, o Prompt de IA (`docs/instalacao-por-ia.md` e `i18n/en/.../ai-install-prompt.md`), os 22 ADRs publicados (`0008` a `0029`) e os checklists de release (`docs/release-checks.md`).

---

## 4. Verificação do Build

1. **Validação de metadados do pacote:**
   ```sh
   /tmp/dev/bin/twine check --strict dist/*
   ```
   Esperado: `PASSED` para o `.whl` e para o `.tar.gz`, exit `0`.

2. **Validação de conteúdo empacotado no `.whl` (ADR 0010 / U1-N10):**
   ```sh
   /tmp/dev/bin/pytest -q tests/test_package.py tests/test_packaging.py
   ```
   Esperado: confirma que o `.whl` contém as 3 skills (`bob-check`, `harden`, `review-report`), `plugin.json`, `LICENSE`, `package.json` e `package-lock.json`, e instala `.agents/skills` num projeto sem depender de clone do repositório.

3. **Validação de instalação limpa do `.whl` (`package.yml`):**
   ```sh
   python3 -m venv /tmp/pkg-venv
   /tmp/pkg-venv/bin/pip install dist/*.whl
   /tmp/pkg-venv/bin/bob --help
   /tmp/pkg-venv/bin/bob doctor
   ```
   Esperado: `bob --help` e `bob doctor` saem com `0`.

---

## 5. Solução de Problemas Comuns (Troubleshooting)

| Sintoma | Causa | Correção |
|---|---|---|
| `npm_prefix()` aponta para `src/bob_quality` em vez da raiz | Pasta `src/bob_quality/node_modules` residual no checkout | Executar `rm -rf src/bob_quality/node_modules` antes da suíte |
| `bob doctor` sai com `4` reclamando de versão do Node | Node fora da faixa `>=22.18.0 <23` | Ativar Node 22 LTS (`>=22.18.0 <23`) no `PATH` |
| `bob doctor` sai com `4` reclamando de ferramentas npm | `npm ci` não foi rodado na raiz ou no cache `BOB_HOME/npm` | Rodar `npm ci` na raiz (desenvolvimento) ou `bob setup` (projeto do usuário) |
| `gitleaks` ausente nos testes do gate `secrets` | Binário `gitleaks` 8.30.1 não está no `PATH` | Baixar o asset oficial 8.30.1 da plataforma, conferir o SHA-256 acima e colocar no `PATH` |
| Artefatos temporários sujando gates (`crap`, `dry`, `deps`) | Pastas `.bob/`, `mutants/`, `dist/` presentes na árvore | Limpar com `rm -rf .bob mutants dist` antes de rodar `bob check` |
