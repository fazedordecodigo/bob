# Skills, manifesto e LICENSE dentro do wheel (issue #45)

Status: aceita pelo Emerson em 18/10/2026, na aprovação do desenho da aplicação. Publicada em `docs/adr/` na U9.

## Contexto

O wheel não leva `skills/` nem `.claude-plugin/` (`pyproject.toml:42-43`; log do run 39159800688). O instalador fora de clone sai `4` e pede `--source` (`install_skills.py:147-150`).

## Decisão

- Pasta `src/bob_quality/plugin/` com três symlinks no git: `.claude-plugin` → `../../../.claude-plugin`, `skills` → `../../../skills`, `LICENSE` → `../../../LICENSE`.
- `package-data` acrescenta `plugin/.claude-plugin/plugin.json`, `plugin/skills/**/*` e `plugin/LICENSE`.
- `install_skills` resolve a fonte: `--source`; senão `parents[2]` se tiver manifesto (clone); senão `bob_quality/plugin/` (pacote).
- Teste de empacotamento abre o wheel e confere as três `SKILL.md`, o `plugin.json` e o `LICENSE`.
- Fecha a issue #45 (o texto dela sobre NOTICE do Pocock está superado pela ADR 0004).

## Alternativas

Copiar as skills para `src/` (duas cópias no repo); hook de build customizado (mais código); baixar as skills do GitHub na instalação (mais rede e outra conferência).

## Consequências

- Symlink de arquivo já funciona no build (`package.json`). Symlink de **diretório** em `package-data`: **Não verificado**. O teste do wheel pega a falha. Plano B: trocar o symlink `skills` por symlinks por arquivo.
