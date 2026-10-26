# U9 — Code Generation Plan

## Summary
- Unit U9 (packaging, C11). Base `main` @ `1b107922bf6553660231f598d758258b96fc091c`.
- Entrega o `release.yml` (CT13), o release-check (CT13) e as ADRs públicas.
- 3 ETs paralelas, sem arquivo em comum. Nenhuma publica nem dispara nada.

## Decisões fechadas
- Matriz: `ubuntu-latest`, `ubuntu-24.04-arm`, `macos-15-intel`, `macos-15` (públicos, grátis em repo público).
- ADR 0030 (proposta): `VERIFY_DIST` no harness. Adição compatível ao CT15 (v1.1).
- `download-artifact` novo: `9000827ccba6bdab643e8b6fd33ac0654aef8333 # v8.0.2`.
- `release.yml`, release-checks, ADRs, índices e `sidebars.js` vão como anexos byte a byte (`/workspace/dispatch/u9-t{1,2,3}/` + `.SHA256SUMS`).
- CHANGELOG: só a T3 (ADR 0027). Topo do `## Unreleased`.
- Q1 = B e Q2 = A assumidas (ver `../functional-design-questions.md`).

## Testing Contract
- Comando de Verificação: `python3 -m venv /tmp/dev && /tmp/dev/bin/pip install -e '.[dev]' && /tmp/dev/bin/pytest && sh scripts/verify-install.sh`.
- Checks obrigatórios do PR: `bob / check`, `bob / cold`, `CI / pytest (3.10)`, `CI / pytest (3.12)`, `package / dist`, `verify-install / linux-x64`; mais `website / build` na T2 e na T3.
- Testes novos: T1 `tests/test_release_workflow.py` (7) + 2 casos em `tests/test_verify_install.py`; T2 `tests/test_release_checks.py` (6 testes, 10 casos); T3 nenhum teste Python (o `website / build` e o `site.test.mjs` cobrem).
- Prova real nas 4 plataformas: E0 (`dry_run`), feito pelo Emerson depois do merge da T1.

## Passos
- [ ] P1 — T1: `release.yml` + `VERIFY_DIST` + testes.
- [ ] P2 — T2: `docs/release-checks/TEMPLATE.md` + `v0.1.0.md` + teste.
- [ ] P3 — T3: ADRs 0008–0029, índices en/pt-BR, `sidebars.js`, CHANGELOG.
- [ ] P4 — Verificação de cada PR contra a ET; checkpoint.
- [ ] P5 — E0 pelo Emerson (pronto 1). Falha em macOS/arm → ET corretiva T4.

## Tarefas
| ET | Arquivos | Paralela | Depende |
|---|---|---|---|
| T1 | `.github/workflows/release.yml` (novo), `tests/test_release_workflow.py` (novo), `scripts/verify-install.sh`, `tests/test_verify_install.py` | sim | — |
| T2 | `docs/release-checks/TEMPLATE.md`, `docs/release-checks/v0.1.0.md`, `tests/test_release_checks.py` (novos) | sim | — |
| T3 | 22 `docs/adr/00NN-*.md`, `docs/architecture/adrs.md`, `website/i18n/pt-BR/.../architecture/adrs.md`, `website/sidebars.js`, `CHANGELOG.md` | sim | — |

- T3 tem 26 arquivos. Exceção ao limite de ~8: cópia mecânica de anexos, sem decisão.
- Ordem sugerida de merge: T1, T2, T3. O `publish` exige `docs/release-checks/v0.1.0.md`, então E1 só depois da T2.
