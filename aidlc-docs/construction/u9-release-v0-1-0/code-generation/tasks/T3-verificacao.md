# Verificação de PR contra a especificação — U9 T3 (#215)

- **Projeto:** bob
- **Unit:** U9 (`u9-release-v0-1-0`)
- **Tarefa:** `ET-u9-release-T3` (`construction/u9-release-v0-1-0/code-generation/tasks/T3.md`, v1, Q1 = B)
- **PR:** https://github.com/fazedordecodigo/bob/pull/215
- **Título:** `U9 T3: ADRs 0008–0029 em docs/adr`
- **Branch:** `aidlc/u9-release/t3-adrs` → `main` (`1b107922bf6553660231f598d758258b96fc091c`)
- **Commit (head):** `b84d6d36d7ade2015a4357e1cd772977c1ace271`
- **Agente:** `bc-80256afb-59d5-51f1-9cbf-606899665ab1` (`https://cursor.com/agents/bc-80256afb-59d5-51f1-9cbf-606899665ab1`)
- **Rodadas de correção:** 0
- **Data da verificação:** 2026-10-24 13:39 (UTC-3)
- **Veredito:** **Aprovado para checkpoint**

## 1–8. Checagens estruturais da skill

1. **Existência:** PR #215 aberto (`OPEN`, `isDraft: false`), branch `aidlc/u9-release/t3-adrs` apontando para `main` em `1b107922bf6553660231f598d758258b96fc091c`, título exato `U9 T3: ADRs 0008–0029 em docs/adr`.
2. **Bloqueios / decisões:** Nenhum bloqueio e nenhuma decisão fora da ET. Passo 0 bateu 100% com a especificação (8 ADRs na base, sha256 de `website/sidebars.js` e dos dois `adrs.md` idênticos ao esperado, `## Unreleased` na linha 3 de `CHANGELOG.md`).
3. **Escopo de arquivos:** 26 arquivos no diff (`+661/-0`): 22 arquivos novos em `docs/adr/0008-*.md`..`0029-*.md` e 4 arquivos modificados (`docs/architecture/adrs.md`, `website/i18n/pt-BR/docusaurus-plugin-content-docs/current/architecture/adrs.md`, `website/sidebars.js`, `CHANGELOG.md`). Nenhum arquivo proibido tocado (`docs/adr/0000-*.md`..`0007-*.md` intactos).
4. **Completude:** Todos os 22 arquivos de "Arquivos a criar" e os 4 de "Arquivos a modificar" estão presentes no commit `b84d6d36d7ade2015a4357e1cd772977c1ace271`.
5. **Conformidade de conteúdo:**
   - Todos os 25 arquivos anexados (`22` em `docs/adr/`, `docs/architecture/adrs.md`, `website/i18n/pt-BR/docusaurus-plugin-content-docs/current/architecture/adrs.md` e `website/sidebars.js`) conferidos por árvore Git e SHA256 contra `/workspace/dispatch/u9-t3.SHA256SUMS`: `25/25 OK` (`mismatches=[]`).
   - `CHANGELOG.md`: recebeu exatamente os 833 bytes / 12 linhas de `CHANGELOG-u9.txt` (sha256 `82f3a173984e4f9a4fa8e2d15150083879683aedafa3c37a0b679d575aeb360`) logo após a linha 4, com `0` remoções e `0` linhas > 100 bytes.
6. **Testes:** `website/tests/site.test.mjs` (`14 pass, 0 fail`) e `tests/test_docs_pins.py` + `tests/test_hermetic.py` (`75 passed`) verdes.
7. **Dependências:** `pyproject.toml` e `website/package.json` intactos.
8. **Evidência de execução (CI + local):**
   - `CI / pytest (3.10)`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110285120/job/120920391259`)
   - `CI / pytest (3.12)`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110285120/job/120920391444`)
   - `bob / check`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110285122/job/120920391524`)
   - `bob / cold`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110285122/job/120920391434`)
   - `package / dist`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110285054/job/120920391120`)
   - `verify-install / linux-x64`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110285138/job/120920391546`)
   - `website / build`: `SUCCESS` (`https://github.com/fazedordecodigo/bob/actions/runs/40110285150/job/120920391429`)

## 9. Tabela Critério → Evidência → Status

| # | Critério da ET (`T3.md`) | Evidência verificada | Status |
|---|---|---|---|
| 1 | 30 arquivos em `docs/adr/` (`0000`–`0007` existentes + `0008`–`0029` novos) | Árvore Git de `b84d6d36d7ade2015a4357e1cd772977c1ace271` em `docs/adr/` → `30` blobs | Atende |
| 2 | Os 25 arquivos anexados batem com os sha256 de `u9-t3.SHA256SUMS` | Verificação dos 25 blobs no commit `b84d6d36d7ade2015a4357e1cd772977c1ace271` contra `u9-t3.SHA256SUMS` → `25/25 OK` (`mismatches=[]`) | Atende |
| 3 | `git diff 1b10792 -- CHANGELOG.md` só adiciona as 12 linhas do anexo (`CHANGELOG-u9.txt`) logo após a linha 4 | `CHANGELOG.md` (`+12/-0`), idêntico a `CHANGELOG-u9.txt` (`82f3a173984e4f9a4fa8e2d15150083879683aedafa3c37a0b679d575aeb360`), `0` linhas > 100 bytes | Atende |
| 4 | `website / build` e checks obrigatórios verdes | 7/7 checks `SUCCESS` no commit `b84d6d36d7ade2015a4357e1cd772977c1ace271` (`website / build`, `bob / check`, `bob / cold`, `CI / pytest (3.10)`, `CI / pytest (3.12)`, `package / dist`, `verify-install / linux-x64`) + `npm test` (`14 pass, 0 fail`) + `4882 passed` | Atende |
| 5 | 26 arquivos no diff | `gh pr view 215 --json changedFiles,files` → `changedFiles: 26`, `+661/-0` | Atende |
