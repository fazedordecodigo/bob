# 3.6 Build and Test — Instruções de Testes de Integração e Ponta a Ponta (`integration-test-instructions.md`)

- **Projeto:** `bob` (`fazedordecodigo/bob`)
- **Estágio:** 3.6 Build and Test
- **Estratégia de testes ativa (`aidlc-state.md`):** `Standard`
- **Comando de Verificação aprovado pelo Emerson (18/10/2026 20:28 UTC-3):**
  ```sh
  python3 -m venv /tmp/dev && /tmp/dev/bin/pip install -e '.[dev]' && /tmp/dev/bin/pytest && sh scripts/verify-install.sh
  ```

---

## 1. Arquitetura dos Testes de Integração

O projeto combina três camadas complementares de verificação integrada:

1. **Testes de integração em `pytest` com espelho HTTP local (`127.0.0.1`):**
   - `tests/test_install_sh.py`: sobe um servidor HTTP local em `127.0.0.1` servindo `/api/releases/latest`, `/releases/download/v<ver>/install.sh`, `.whl` e `SHA256SUMS`, e exercita `scripts/install.sh` ponta a ponta em diretórios temporários isolados (`HOME`, `BOB_HOME`, `TMPDIR`).
   - `tests/test_update.py`: testa `bob update` ponta a ponta contra o espelho local (descoberta de release publicada, filtro de pré-release e rascunho, conferência de `SHA256SUMS`, reexecução do `install.sh` mantendo `BOB_HOME`, preservação de `bob.yaml`, waivers, hook e skills alheias).
   - `tests/test_hook.py`: instala o hook pre-push real com `install_hook()` num repositório Git com remoto `bare` e executa `git push` real validando o tempo (`< 60 s`) e o bloqueio/aprovação dos gates.
   - `tests/test_package.py`: constrói o wheel real e valida a instalação das skills e do CLI sem clone.

2. **Guarda de hermeticidade de rede (`tests/test_hermetic.py` + `tests/net_guard/sitecustomize.py`):**
   - Intercepta `socket.socket.connect`, `socket.socket.connect_ex` (`AF_INET`/`AF_INET6`) e `socket.getaddrinfo` em subprocessos `pytest` sem cache (`-p no:cacheprovider`).
   - Garante `0` conexões de rede nas 9 suítes unitárias/de componente das units U4–U8 (`tests/test_init_config.py`, `tests/test_check_dispatch.py -k bob_yaml`, `tests/test_check_report.py -k bob_yaml`, `tests/test_mutation_branches.py -k bob_yaml`, `tests/test_hook_install.py`, `tests/test_setup_cmd.py -k "bob_yaml or hook or profile"`, `tests/test_project_version.py`, `tests/test_update.py`, `tests/test_docs_pins.py`).

3. **Harness ponta a ponta `scripts/verify-install.sh` (15 passos: `1, 2, 3, 4, 5, 6, 7, 8, 9a, 9b, 10, 11, 12, 13, 14`):**
   - Constrói o wheel real (ou usa o wheel pronto via `VERIFY_DIST` no `release.yml`), sobe um espelho HTTP local com duas releases (`v0.1.0` e `v99.0.0`, além de pré-release `v99.1.0-rc.1` e rascunho `v99.1.1`), limpa o `PATH` para `/usr/bin:/bin` + diretórios de `python3` e `node` (sem `bob` e sem `gitleaks` pré-instalados) e instala um `sudo` falso que grava em `sudo.log` e falha com exit `99`.

---

## 2. Como Executar os Testes de Integração

### 2.1 Execução Completa (Comando de Verificação do Projeto)
```sh
python3 -m venv /tmp/dev && /tmp/dev/bin/pip install -e '.[dev]' && /tmp/dev/bin/pytest && sh scripts/verify-install.sh
```

### 2.2 Execução Seletiva do Harness (`scripts/verify-install.sh`)
```sh
# Todos os 15 passos (modo local padrão: constrói o wheel da árvore atual)
sh scripts/verify-install.sh

# Passo específico (resolve dependências internas de estado automaticamente, ex.: passo 10 roda o 8 antes)
sh scripts/verify-install.sh --only 5,7,8
sh scripts/verify-install.sh --only 6,12
sh scripts/verify-install.sh --only 10,11
sh scripts/verify-install.sh --only 13
sh scripts/verify-install.sh --only 14

# Modo VERIFY_DIST (usado no workflow release.yml para testar exatamente os 3 assets gerados no job check)
VERIFY_DIST=/caminho/absoluto/dist/release sh scripts/verify-install.sh
```

### 2.3 Execução da Guarda Hermética
```sh
/tmp/dev/bin/pytest -q tests/test_hermetic.py
```
Esperado: `10 passed` (`1` controle positivo que prova que a guarda captura conexões + `9` entradas de `_UNIT_ARGS` com `0` bytes no log de rede).

---

## 3. Cobertura dos 15 Passos do Harness (`scripts/verify-install.sh`)

| Passo | Unidade | O que verifica ponta a ponta | Critérios / Metas NFR |
|---|---|---|---|
| `1` | U1 | Pré-condições: falha cedo (exit `4`, `0` arquivos escritos fora de `TMPDIR`, `BOB_HOME` inexistente) quando falta `.git`, Python fora de faixa, Node fora de faixa ou ferramenta ausente | US1.2, FR7.2, FR7.3, U1-N7, U1-N8 |
| `2` | U1, U3, U7 | Instalação limpa em projeto novo via comando único (`install.sh`), download real e conferência SHA-256 do `gitleaks` 8.30.1, `bob doctor` = `0`, `bob --version` e linha `project skills: <ver> (.agents/skills)`, tempo `≤ 300 s` | US1.1, FR1.1–1.5, FR2.1–2.2, FR6.4, NFR1, U1-N1, U3-N1, U9-N10 |
| `3` | U1, U3, U6 | Zero chamadas ao `sudo` falso (`sudo.log` com `0` bytes) em todos os fluxos | NFR7, U1-N3, U3-N12, U6-N5 |
| `4` | U1 | Skills instaladas exclusivamente em `.agents/skills` (`bob-check`, `harden`, `review-report`), `0` pastas `.claude`, `.github`, `.cursor`, `.devin` criadas, `0` symlinks | US2.1, FR3.1–3.3, U1-N9 |
| `5` | U4 | Geração de `bob.yaml` válido em 3 topologias (`src/`, `app/`, `sem-codigo` com aviso e `paths.include: ["."]`), `bob check --base HEAD --gates crap,dry,deps` ≠ `4` nos 3 projetos, tempo `≤ 180 s` | US3.1, FR4.1–4.5, U4-N1..N4, U4-N10 |
| `6` | U5 | Hook `pre-push` instalado (template CT10, modo `0755`), `git push` real com `env -i HOME=$HOME PATH=/usr/bin:/bin` dispara `bob check --gates crap,dry,deps` sem ativar venv e grava `.bob/report.md`, tempo `≤ 60 s` | US4.1, FR5.1–5.2, U5-N1, U5-N2, U5-N11 |
| `7` | U1, U3, U4, U5 | Idempotência na 2ª execução seguida: `0` arquivos do projeto alterados, `0` `npm ci` rodados, `0` downloads de `gitleaks`, `mtime` de `bob.yaml` e `pre-push` intactos, tempo `≤ 60 s` | NFR4, U1-N4, U1-N13, U3-N4, U3-N5, U4-N6, U5-N6 |
| `8` | U1, U4, U5 | Preservação byte a byte de `bob.yaml`, `.bob/waivers.yaml`, hook `pre-push` alheio, skill alheia (`.agents/skills/outra`), `package.json`, `node_modules` e `src/app.py`, com linhas `preserved:` no resumo | US3.2, FR2.4, FR3.4, FR4.6, FR5.3, NFR5, U1-N5, U4-N5, U5-N4 |
| `9a` | U3 | Adulteração (+1 byte) no `.tar.gz` do `gitleaks`: falha com exit `4`, `0` binários instalados em `BOB_HOME`, `0` arquivos do projeto alterados | US1.3, FR2.3, NFR6, U3-N2, U3-N3 |
| `9b` | U1 | Adulteração (+1 byte) no `.whl` do `bob-quality`: falha com exit `4`, `0` `versions/` criados, `0` arquivos do projeto alterados | NFR6, U1-N6 |
| `10` | U7 | `bob update` atualiza da `v0.1.0` para a última release publicada (`v99.0.0`), ignorando pré-release (`v99.1.0-rc.1`) e rascunho (`v99.1.1`), atualiza `.bob-version` nas 3 skills, preserva `bob.yaml`, waivers, hook e skill alheia, `bob doctor` = `0`, tempo `≤ 300 s` | US5.1, US5.2, US7.2, FR6.1–6.4, U7-N1, U7-N2, U7-N4, U7-N7, U9-N10 |
| `11` | U7 | 2ª execução de `bob update` quando já está na última release: imprime aviso `up to date`, faz apenas `1` requisição (`/api`), não altera nenhum byte do projeto, tempo `≤ 30 s` | FR6.5, NFR4, U7-N3, U7-N8 |
| `12` | U5 | Suíte `tests/test_hook.py` executada pelo harness com o binário instalado, cada execução do hook `< 60 s`, tempo total do passo `≤ 240 s` | NFR8, U5-N3, U5-N12 |
| `13` | U6 | Configuração do perfil de shell (`zsh`, `bash`, `sh`, `fish`/desconhecido e perfil sem permissão de escrita): `command -v bob` resolve `$HOME/.local/bin/bob` num terminal novo, linha única com marcador `managed-by: bob-quality`, bytes anteriores preservados, perfil read-only avisa e sai `0`, tempo `≤ 180 s` | US1.1, FR1.1, FR7.1, NFR4, NFR5, NFR7, NFR9, U6-N1..N7 |
| `14` | U8 | Paridade entre o comando único (instalação A) e os blocos do Prompt de IA extraídos de `docs/getting-started/ai-install-prompt.md` (instalação B): `0` downloads/menções a `install.sh`, `0` chamadas a `sudo`, manifesto final A = B byte a byte, 2ª execução com `2` linhas `reused`, tempo `≤ 360 s` | US1.5, US7.1, FR1.6–1.8, FR8.4–8.5, NFR10, NFR11, U8-N5..N7, U8-N10 |
