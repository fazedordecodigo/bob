# U9 — Release v0.1.0: Functional Design

Base: `main` em `1b107922bf6553660231f598d758258b96fc091c` (merge do #213, 24/10/2026 11:51:50 UTC-3).
Unit: U9 (packaging), dona do C11. ADR 0011. Contratos: CT12 (formato da release), CT13 (`release.yml` e release-check), CT15 (harness).
Histórias: US7.2; US1.1 crit. 1 por plataforma; US1.5 crit. 7. FR1.2, FR1.4. NFR1, NFR3, NFR10, NFR11.

## 1. Estado medido na base

- Não há `release.yml`, nem `docs/release-checks/`, nem tag, nem release. Repo público.
- `pyproject.toml:7` = `0.1.0`; `__version__` = `0.1.0`; plugins Cursor e Claude = `0.1.0`.
- Pins dev: `build==1.6.1`, `twine==7.0.0`, `pytest==9.1.1`.
- `docs/adr/` tem só 0000–0007 (pt-BR). ADRs 0008–0029 só existem no `decisions.md` do AI-DLC.
- `publish-plugins.yml` dispara em tag `v*` e em release publicada, só valida (`contents: read`). Fica como está.
- `verify-install.sh` gera o wheel dele mesmo em `build_wheel()` (linha 485). Não aceita um wheel pronto.

## 2. Comportamento do `release.yml` (CT13)

- Só `workflow_dispatch`. Rodado fora da `main`, falha no 1º passo do job `check`.
- Entradas: `tag` (obrigatória), `prerelease` (padrão `true`), `dry_run` (padrão `false`).
- `check`: tag casa `^v[0-9]+\.[0-9]+\.[0-9]+$`, é igual a `v` + versão do pyproject e ainda não existe. Gera os 3 assets do CT12 e sobe o artefato `release-assets`.
- `verify`: matriz de 4 plataformas. Confere `SHA256SUMS`, confere que o `install.sh` é cópia byte a byte de `scripts/install.sh`, roda `bob doctor`, `pytest` e o harness com o wheel do run.
- `publish`: só com `dry_run == false`. Único job com `contents: write`. `gh release create` com `--target <sha>`, `--title <tag>`, `--notes-file docs/release-checks/<tag>.md`. `prerelease: true` → `--prerelease --latest=false`; senão `--latest`.
- Falha em qualquer job → nada é publicado.

| Plataforma | Runner | gitleaks |
|---|---|---|
| Linux x64 | `ubuntu-latest` | `linux_x64` |
| Linux arm64 | `ubuntu-24.04-arm` | `linux_arm64` |
| macOS x64 | `macos-15-intel` | `darwin_x64` |
| macOS arm64 | `macos-15` | `darwin_arm64` |

## 3. ADR 0030 (proposta) — `VERIFY_DIST` no harness

**Contexto.** O CT13 pede o Comando de Verificação "com os assets do run". O harness só sabe gerar o próprio wheel. Sem mudança, o `verify` testaria um wheel diferente do publicado.

**Decisão.** Adição compatível ao CT15. Em `build_wheel()`, logo depois de `WHL=…`: se `VERIFY_DIST` não está vazio, exige `$VERIFY_DIST/$WHL`, copia para `$T/dist/$WHL` e retorna 0. Se o arquivo não existe, `die_preparo "VERIFY_DIST sem $WHL"`. Sem `VERIFY_DIST`, nada muda. O texto de ajuda não muda.

**Alternativas.** (a) Gerar o wheel de novo no `verify`: build reproduzível não é garantido, testa outro arquivo. (b) Passar `--remote`: exige release publicada, inverte a ordem.

**Consequências.** CT15 vai para v1.1 (compatível). **Aviso ao Maestro**: o CT15 está aprovado; a ADR 0030 entra na Plan Approval da U9.

## 4. Release-check (CT13)

- `docs/release-checks/TEMPLATE.md`: modelo genérico (`vX.Y.Z`).
- `docs/release-checks/v0.1.0.md`: registro da v0.1.0 com o roteiro E0–E6 e comandos exatos.
- Seções: cabeçalho (Commit, Run, Comando de Verificação); matriz automática (4 plataformas); verificação manual (5 agentes); Prompt de IA (CT18); Fluxo.
- Desvio de forma do CT13: os marcadores `<sha>`, `<url>` etc. ficam entre crases. Motivo: o site (Docusaurus, `docs/` é a pasta de docs) trataria `<sha>` como HTML.
- E0 é o `dry_run` (pronto 1). E1–E6 seguem a unit-of-work.

## 5. ADRs públicas

- 22 arquivos `docs/adr/0008-…` a `docs/adr/0029-…`, no formato das 0000–0007: `# Título`, `Status: aceita pelo Emerson em DD/MM/AAAA…`, `## Contexto`, `## Decisão`, `## Consequências`.
- Corpo copiado do `decisions.md`. Rótulos `**X.**` viram `## X`. Sem reescrita.
- Datas: 0008–0020 em 18/10/2026 (aprovação do 2.6); 0021–0029 em 22/10/2026 (Plan Approval U6–U8).
- Índices: `docs/architecture/adrs.md` (en) e a cópia pt-BR em `website/i18n/pt-BR/…/architecture/adrs.md`. `website/sidebars.js` ganha as 22 entradas.
- Escopo 0008–0029 depende da Q1.

## 6. Pronto quando (unit-of-work)

1. `dry_run: true` verde nas 4 plataformas; artefato com só os 3 assets; `sha256sum -c` OK. (Depende do E0, feito pelo Emerson — Q2.)
2. Tag diferente da versão para antes de criar release. (Teste estático + passo `meta`.)
3. `v0.1.0.md` com as partes automáticas, 5 linhas manuais e a linha do Prompt de IA. (T2.)
4. ADRs 0008–0020 em `docs/adr/`. (T3; com a Q1 B, até 0029.)
5. `v0.1.0.md` com o roteiro E1–E6 e comandos exatos. (T2.)
6. Pronto para o Emerson disparar.

## 7. Fora de escopo

- Disparar o workflow, criar tag, publicar, promover. Só o Emerson.
- GitHub Pages (`pages` falha desde 18/10, Pages desligado). Vai ao Maestro à parte.
- Mudar `publish-plugins.yml`, versão, `## Unreleased` do CHANGELOG.
