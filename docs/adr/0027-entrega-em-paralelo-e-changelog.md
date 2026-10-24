# Entrega em paralelo: CHANGELOG por unit e rebase mecânico

Status: aceita pelo Emerson em 22/10/2026, no Plan Approval da U6, da U7 e da U8. Publicada em `docs/adr/` na U9.

## Decisão

- **CHANGELOG.** Cada unit escreve no `CHANGELOG.md` só na ET que fecha a unit. Na U6 e na U7 é a T3; na U8, a T3 (docs) e a T4 (harness). Assim a U6 T1 e a U6 T2 não têm arquivo em comum e rodam em paralelo.
- **Âncoras fixas.** Pontos de inserção diferentes por unit, separados por pelo menos 1 linha que nenhuma das duas muda. Regras exatas de rebase em `u6-perfil-shell/shared-files-u6-u7.md`.
- **Ordem sugerida de merge.** U6 T1 e T2 (qualquer ordem), U7 T1, U7 T2, U6 T3, U7 T3 por último, com rebase.

## Consequências

Entre os merges, a `main` fica algumas horas sem entrada no CHANGELOG para a T1 e a T2. A seção é `## Unreleased`, então isso não afeta release.
