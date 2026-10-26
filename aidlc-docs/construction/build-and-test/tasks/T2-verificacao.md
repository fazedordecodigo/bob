# Verificação de PR contra Especificação — Estágio 3.6 Build and Test — Tarefa T2

- **Projeto**: `bob` (`bob-quality`)
- **Estágio**: `3.6 Build and Test`
- **Tarefa**: `T2` (`construction/build-and-test/tasks/T2.md`, `sha256: 7acf73c2ce5e6b30191b9bca96ac5d41adfd23d741a5eb5b8e98b0b167462dc8`)
- **Agente**: `bc-1ace0d07-fad1-5eb0-bf14-1cc63f74e8fc` ([ET-build-and-test-T2](https://cursor.com/agents/bc-1ace0d07-fad1-5eb0-bf14-1cc63f74e8fc))
- **Pull Request**: [#221](https://github.com/fazedordecodigo/bob/pull/221) (`[3.6][T2] Portabilidade macOS para o ensaio E0 (release.yml)`)
- **Branch da tarefa**: `aidlc/build-and-test/t2-macos-portability`
- **Branch base**: `main` (`55c4de7a00b10459313bea85dbdfb8f71698ddf5`)
- **Commit verificado (HEAD)**: `e70fb4a6c3ce3943dff24bd79a77048a59546282`
- **Rodadas de correção**: `0` (ajuste editorial na própria ET `T2.md` para refletir o protocolo de gerador `next`/`close` de `_detached` em `tests/test_security.py` e o escopo de largura de linha nas linhas alteradas, sem mudança em decisão aprovada e sem novo commit)
- **Status**: **Aprovado para merge** (`8/8` verificações estruturais `Atende`, `4/4` critérios `Atende`, `7/7` checks de CI verdes)

---

## 1. Escopo de arquivos (`git diff --name-only origin/main...HEAD`)

| Arquivo | Mudança | Permitido pela ET? |
|---|---|---|
| `src/bob_quality/install_skills.py` | `MODIFIED` (`+3 / -3`) | Sim |
| `src/bob_quality/security_gate.py` | `MODIFIED` (`+1 / -1`) | Sim |
| `scripts/install.sh` | `MODIFIED` (`+1 / -1`) | Sim |
| `docs/install-prompt.en.md` | `MODIFIED` (`+1 / -1`) | Sim |
| `docs/install-prompt.pt-BR.md` | `MODIFIED` (`+1 / -1`) | Sim |
| `tests/test_docs_pins.py` | `MODIFIED` (`+1 / -1`) | Sim |
| `tests/test_eslint_in_process.py` | `MODIFIED` (`+1 / -1`) | Sim |
| `tests/test_project_skills.py` | `MODIFIED` (`+18 / -0`) | Sim |
| `tests/test_security.py` | `MODIFIED` (`+34 / -0`) | Sim |

Total: `9` arquivos modificados (`+61 / -9`), `0` criados, `0` removidos. Nenhum arquivo fora do escopo foi tocado.

---

## 2. Verificações Estruturais (8/8)

| # | Verificação | Status | Evidência |
|---|---|---|---|
| 1 | PR aberto contra a branch base correta (`main` @ `55c4de7a00b10459313bea85dbdfb8f71698ddf5`) e não é draft | **Atende** | `state: OPEN`, `isDraft: false`, `baseRefName: main`, `baseRefOid: 55c4de7a00b10459313bea85dbdfb8f71698ddf5` |
| 2 | Nome da branch e título/commit seguem a ET | **Atende** | Branch `aidlc/build-and-test/t2-macos-portability`, commit `fix(macos): fix darwin portability in install_skills, security_gate, install.sh and tests`, título `[3.6][T2] Portabilidade macOS para o ensaio E0 (release.yml)` |
| 3 | Escopo de arquivos estrito (`9` arquivos permitidos) | **Atende** | `changedFiles: 9`, lista idêntica à seção "Arquivos Permitidos no Diff" da `T2.md` |
| 4 | Implementação exata das 4 correções de portabilidade macOS (`darwin`) | **Atende** | (1) `_remove_path` em `install_skills.py` usa `if _real_dir(path): shutil.rmtree(path); return` antes de `path.unlink()`; (2) `_detached` em `security_gate.py` aplica `.resolve()` a `Path(tempfile.mkdtemp(prefix="bob-semgrep-"))`; (3) `scripts/install.sh` e `docs/install-prompt.{en,pt-BR}.md` leem `ENVIRON["SHELL"]` via `awk`; (4) `_raw` em `tests/test_eslint_in_process.py` usa `os.path.sameopenfile(0, os.open(os.devnull, os.O_RDONLY))` |
| 5 | Testes unitários novos e atualizados presentes e sem enfraquecer asserções | **Atende** | `test_remove_path_uses_rmtree_for_real_dir_without_unlink` em `tests/test_project_skills.py` simula `PermissionError(1, ...)` (comportamento BSD/macOS em diretório real); `test_detached_resolves_symlinked_tempdir` em `tests/test_security.py` simula symlink `/var_tmp -> /real_tmp` em `tempfile.mkdtemp`; `test_prompt_profile_matches_install_sh` em `tests/test_docs_pins.py` verifica a linha `awk` |
| 6 | Regras de estilo e largura de linha (`<= 100` colunas nas linhas tocadas, sem `TODO` ou código morto) | **Atende** | Maior linha adicionada/modificada no diff tem `86` colunas (`<= 100`); `bob / check` (`crap,dry,deps,mutate,coverage`) verde |
| 7 | Comandos de verificação executados e saídas coladas no PR | **Atende** | Saídas literais no corpo do PR #221: `276 passed in 90.78s` nos 7 arquivos de teste afetados + guarda hermética; `4907 passed, 3 warnings, 32 subtests passed` na suíte completa |
| 8 | Todos os checks de CI verdes no GitHub | **Atende** | `7/7` checks `COMPLETED` / `SUCCESS` no commit `e70fb4a6c3ce3943dff24bd79a77048a59546282` |

---

## 3. Tabela Critério → Status → Evidência

| Critério | Status | Evidência verificada |
|---|---|---|
| **C1**: Testes diretamente afetados e guarda hermética (`pytest -q tests/test_project_skills.py tests/test_security.py tests/test_eslint_in_process.py tests/test_install_sh.py tests/test_docs_pins.py tests/test_verify_install.py tests/test_hermetic.py`) passam 100% (`0 failed`). | **Atende** | Saída colada no PR #221 e confirmada nos jobs de CI: `276 passed in 90.78s (0:01:30)`. |
| **C2**: Suíte completa de testes (`pytest -q`) passa 100% (`4907 passed`). | **Atende** | Saída colada no PR #221 e confirmada nos jobs `CI / pytest (3.10)` (`17m16s`) e `CI / pytest (3.12)` (`20m18s`): `4907 passed, 3 warnings, 32 subtests passed`. |
| **C3**: Nenhuma linha adicionada ou modificada no diff ultrapassa `100` colunas e os portões `bob / check` (`crap,dry,deps,mutate,coverage`) e `bob / cold` passam. | **Atende** | Verificado no diff do commit `e70fb4a6c3ce3943dff24bd79a77048a59546282` (máximo de `86` colunas nas linhas alteradas) e nos jobs `bob / check` (`SUCCESS` em `20m47s`) e `bob / cold` (`SUCCESS` em `31s`). |
| **C4**: `git status --short` e `git diff --name-only origin/main` listam exclusivamente os 9 arquivos permitidos. | **Atende** | Verificado via `gh pr view 221 --json files`: exatamente os 9 arquivos (`docs/install-prompt.en.md`, `docs/install-prompt.pt-BR.md`, `scripts/install.sh`, `src/bob_quality/install_skills.py`, `src/bob_quality/security_gate.py`, `tests/test_docs_pins.py`, `tests/test_eslint_in_process.py`, `tests/test_project_skills.py`, `tests/test_security.py`). |

---

## 4. Checks de CI no GitHub (`e70fb4a6c3ce3943dff24bd79a77048a59546282`)

| Workflow / Job | Status | Conclusão | Duração |
|---|---|---|---|
| `CI / pytest (3.10)` | `COMPLETED` | `SUCCESS` | `17m16s` |
| `CI / pytest (3.12)` | `COMPLETED` | `SUCCESS` | `20m18s` |
| `bob / check` | `COMPLETED` | `SUCCESS` | `20m47s` |
| `bob / cold` | `COMPLETED` | `SUCCESS` | `31s` |
| `package / dist` | `COMPLETED` | `SUCCESS` | `39s` |
| `verify-install / linux-x64` | `COMPLETED` | `SUCCESS` | `2m20s` |
| `website / build` | `COMPLETED` | `SUCCESS` | `3m1s` |
