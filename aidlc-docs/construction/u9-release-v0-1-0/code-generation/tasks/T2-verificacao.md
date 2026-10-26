# Verificação de PR contra a especificação — U9 T2 (#214)

- **Projeto:** bob
- **Unit:** U9 (`u9-release-v0-1-0`)
- **Tarefa:** `ET-u9-release-T2` (`construction/u9-release-v0-1-0/code-generation/tasks/T2.md`, v1)
- **PR:** https://github.com/fazedordecodigo/bob/pull/214
- **Título:** `U9 T2: release-check v0.1.0`
- **Branch:** `aidlc/u9-release/t2-release-checks` → `main` (`1b107922bf6553660231f598d758258b96fc091c`)
- **Commit (head):** `eb457472a77fdb976813d6fd4ac85ea509358431`
- **Agente:** `bc-235c9d87-aeae-5197-8fc0-cc8b753559fa` (`https://cursor.com/agents/bc-235c9d87-aeae-5197-8fc0-cc8b753559fa`)
- **Rodadas de correção:** 0
- **Data da verificação:** 2026-10-24 13:39 (UTC-3)
- **Veredito:** **Aprovado para checkpoint**

## 1–8. Checagens estruturais da skill

1. **Existência:** PR #214 aberto (`OPEN`, `isDraft: false`), branch `aidlc/u9-release/t2-release-checks` apontando para `main` em `1b107922bf6553660231f598d758258b96fc091c`, título exato `U9 T2: release-check v0.1.0`.
2. **Bloqueios / decisões:** Nenhum bloqueio e nenhuma decisão fora da ET. Passo 0 bateu 100% (`1b107922bf6553660231f598d758258b96fc091c`, `docs/release-checks` ausente, `tests/test_release_checks.py` ausente).
3. **Escopo de arquivos:** 3 arquivos no diff (`docs/release-checks/TEMPLATE.md`, `docs/release-checks/v0.1.0.md`, `tests/test_release_checks.py`), `+295/-0`. Nenhum arquivo proibido tocado (`sidebars.js`, `CHANGELOG.md`, workflows e ADRs intactos).
4. **Completude:** Todos os 3 arquivos de "Arquivos a criar" existem no commit `eb457472a77fdb976813d6fd4ac85ea509358431`.
5. **Conformidade de conteúdo:**
   - `docs/release-checks/TEMPLATE.md`: sha256 `a124c952c8a22a658ba226c0bbea1bf62ca369a8ba1abcdc4dd272933ea583aa` (idêntico ao anexo, blob git `6215e54`).
   - `docs/release-checks/v0.1.0.md`: sha256 `d6d62dc5deec610f0fbd740d194d1c3714f1b350c10293982bae8928f57f59da` (idêntico ao anexo, blob git `30638a1`).
   - `tests/test_release_checks.py`: 133 linhas, 0 linhas > 100 colunas UTF-8, somente leitura.
6. **Testes:** As 6 funções especificadas existem com os nomes exatos (`test_release_check_titles`, `test_release_checks_have_the_ct13_sections`, `test_manual_table_lists_the_five_agents`, `test_matrix_table_lists_the_four_runners`, `test_v0_1_0_has_the_e0_to_e6_script`, `test_release_checks_have_no_relative_links`), totalizando 10 casos parametrizados. Zero `.skip`, `.only`, `xit`, `@Ignore` ou waivers novos.
7. **Dependências:** `pyproject.toml` não foi modificado.
8. **Evidência de execução (CI + local):**
   - `CI / pytest (3.10)`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110105233/job/120919848513`)
   - `CI / pytest (3.12)`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110105233/job/120919848410`)
   - `bob / check`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110105230/job/120919848673`)
   - `bob / cold`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110105230/job/120919848954`)
   - `package / dist`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110105250/job/120919848380`)
   - `verify-install / linux-x64`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110105305/job/120919849025`)
   - `website / build`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110105338/job/120919848819`)
   - Local: `pytest tests/test_release_checks.py -q` → `10 passed in 0.03s`; `cd website && npm ci && npm run build && npm test` → `14 pass, 0 fail`; `python -m pytest -q` → `4892 passed, 32 subtests passed`.

## 9. Tabela Critério → Evidência → Status

| # | Critério da ET (`T2.md`) | Evidência verificada | Status |
|---|---|---|---|
| 1 | Os 2 `.md` (`docs/release-checks/TEMPLATE.md` e `docs/release-checks/v0.1.0.md`) com os sha256 dos anexos | `TEMPLATE.md` = `a124c952c8a22a658ba226c0bbea1bf62ca369a8ba1abcdc4dd272933ea583aa` (blob `6215e54`, 44 linhas); `v0.1.0.md` = `d6d62dc5deec610f0fbd740d194d1c3714f1b350c10293982bae8928f57f59da` (blob `30638a1`, 118 linhas) | Atende |
| 2 | 6 testes / 10 casos verdes em `tests/test_release_checks.py` (`test_release_check_titles`, `test_release_checks_have_the_ct13_sections[TEMPLATE,v0.1.0]`, `test_manual_table_lists_the_five_agents[TEMPLATE,v0.1.0]`, `test_matrix_table_lists_the_four_runners[TEMPLATE,v0.1.0]`, `test_v0_1_0_has_the_e0_to_e6_script`, `test_release_checks_have_no_relative_links[TEMPLATE,v0.1.0]`) | `tests/test_release_checks.py:1-133`; saída `10 passed in 0.03s`; suíte completa `4892 passed` | Atende |
| 3 | Checks obrigatórios + `website / build` verdes | 7/7 checks `SUCCESS` no commit `eb457472a77fdb976813d6fd4ac85ea509358431` (`pytest (3.10)`, `pytest (3.12)`, `bob / check`, `bob / cold`, `package / dist`, `verify-install / linux-x64`, `website / build`) | Atende |
| 4 | Só 3 arquivos no diff (`docs/release-checks/TEMPLATE.md`, `docs/release-checks/v0.1.0.md`, `tests/test_release_checks.py`) | `gh pr view 214 --json changedFiles,files` → `changedFiles: 3`, `+295/-0` | Atende |
