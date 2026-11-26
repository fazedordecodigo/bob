# Release check vX.Y.Z

Modelo do registro de cada release (CT13). Copie para `docs/release-checks/vX.Y.Z.md`, troque `vX.Y.Z` pela tag e preencha durante o fluxo E0–E6. O workflow `release` publica esse arquivo como notas da release.

- Commit (SHA do build de E0): `<sha>`
- Ensaio E0: `<url>`
- Publicação E1: `<url>`
- Comando de Verificação: `<passou|falhou>` (`<url do run>`)

## Comando de Verificação na matriz (automático)

O job `verify` do workflow `release` roda em cada plataforma: `shasum -a 256 -c SHA256SUMS` nos assets do run, `cmp` do `install.sh` com `scripts/install.sh`, o `bob doctor`, o `pytest` e o `sh scripts/verify-install.sh` (passos 1 a 14) com o wheel do run (`VERIFY_DIST`).

| Plataforma | Runner | Resultado | Tempo do passo 2 | Tempo do passo 14 |
|---|---|---|---|---|
| Linux x64 | `ubuntu-latest` | | | |
| Linux arm64 | `ubuntu-24.04-arm` | | | |
| macOS x64 | `macos-15-intel` | | | |
| macOS arm64 | `macos-15` | | | |

## Verificação manual (projeto do passo 2, skills só em .agents/skills)

| Agente | Data (UTC-3) | Versão do agente | Lista bob-check, harden, review-report uma vez? | Evidência |
|---|---|---|---|---|
| Cursor | | | | |
| Claude Code (RA1; ADR 0009 Risco 1) | | | | |
| GitHub Copilot | | | | |
| Devin CLI | | | | |
| Devin web | | | | |

Pelo RA1, o Claude Code não listar as skills não bloqueia a promoção: registre como está. Para os outros 4 agentes, uma falha bloqueia.

## Prompt de IA (CT18, alternativa sem install.sh)

Um agente de IA real recebe `docs/install-prompt.<idioma>.md` num projeto novo e segue os passos. Conferir: não baixou nem rodou `install.sh`, não usou `sudo`, colou a saída de `setup` e `verificação`, e o resultado bate com o passo 2 (mesmos itens do manifesto do passo 14).

| Agente usado | Data (UTC-3) | Saída de `verificação` (`bob doctor` = 0, `bob --version`) | Sem `install.sh`/`sudo`? | Mesmo resultado do one-liner? | Evidência |
|---|---|---|---|---|---|
| | | | | | |

## Fluxo

- E0: na `main`, dispare o ensaio e aguarde todos os jobs de verificação passarem:

  ```sh
  gh workflow run release.yml --repo fazedordecodigo/bob --ref main -f tag=vX.Y.Z -f dry_run=true
  ```

  Registre o SHA completo da linha `release: SHA do build:` no passo **Selecionar o commit da release** e guarde o `SHA256SUMS` do artefato `release-assets`.
- E1: antes de disparar, faça merge na `main` do registro com as evidências de E0. As notas saem do commit que disparou E1; os assets e a tag usam o SHA aprovado em E0. Passe esse SHA como `E0_SHA`, mesmo que a `main` já tenha avançado:

  ```sh
  gh workflow run release.yml --repo fazedordecodigo/bob --ref main -f tag=vX.Y.Z -f dry_run=false -f prerelease=true -f sha="$E0_SHA"
  ```

- E2 antes de promover (`releases/latest` HTTP): `<código>`
- Promovida por: `<nome>`, em `<data UTC-3>`
- E6 depois de promover: `tag_name` = `<tag>`; `sha256sum -c SHA256SUMS`: `<OK|falhou>`; `cmp` entre o `SHA256SUMS` publicado e o de E0: `<idênticos|diferentes>`
