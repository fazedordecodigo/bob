# bob

Quality gates (CRAP, DRY, mutação, dependências) + skills para agentes de codificação (Cursor, Claude Code, GitHub Copilot, Devin), inspirados no fluxo do Uncle Bob e nas skills do Matt Pocock.

- CLI: `bob` (`bob check | crap | dry | deps | mutate | report | waive | doctor`)
- Pacote PyPI: `bob-quality` (ainda não publicado)
- Nome nos marketplaces: `bob` (ainda não publicado)
- Configuração: `bob.yaml`

Skills (issue #7):

- Fluxo de spec do Pocock (MIT, atribuído): `skills/vendor/mattpocock/`
- `skills/bob-check/` — quando e como rodar `bob check`
- `skills/review-report/` — resumir `.bob/report.md` no PR
- Índice para agentes: `AGENTS.md`

A CLI `bob` ainda não está neste branch (issue #1).

Licença: MIT.
