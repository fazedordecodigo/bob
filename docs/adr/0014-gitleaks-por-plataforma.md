# gitleaks 8.30.1 por plataforma

Status: aceita pelo Emerson em 18/10/2026, na aprovação do desenho da aplicação. Publicada em `docs/adr/` na U9.

## Contexto

RE-Q1 A, FR2.2, FR2.3. O doctor só conhece `linux_x64` (`doctor.py:91-97`).
Fonte: release oficial https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1 e o arquivo https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_checksums.txt, baixado no box em 2026-10-18. Os quatro valores abaixo batem com o campo `digest` da API de releases do GitHub para o mesmo asset. A release é publicada (não pré-release, não rascunho), de 2026-03-20 23:17 UTC-3.

| Plataforma (`uname -s`/`uname -m`) | Asset | sha256 |
|---|---|---|
| Linux / `x86_64` | `gitleaks_8.30.1_linux_x64.tar.gz` | `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb` |
| Linux / `aarch64`, `arm64` | `gitleaks_8.30.1_linux_arm64.tar.gz` | `e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080` |
| Darwin / `x86_64` | `gitleaks_8.30.1_darwin_x64.tar.gz` | `dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709` |
| Darwin / `arm64` | `gitleaks_8.30.1_darwin_arm64.tar.gz` | `b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5` |

URL de cada um: `https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/<asset>`. O valor de Linux x64 é o mesmo de `doctor.py:96`.

## Decisão

- A tabela acima vive só em `src/bob_quality/gitleaks.py`. Doctor e setup importam dela.
- O sha256 fica no código do bob. Não se baixa o `checksums.txt` na instalação (ele viria da mesma origem do binário).
- Fluxo: baixar para temporário → conferir sha256 → extrair só o membro `gitleaks` (sem caminho, sem link) → `chmod 0755` → mover para `BOB_HOME/tools/gitleaks/8.30.1/gitleaks` → ligar `BOB_HOME/bin/gitleaks`.
- Plataforma fora da tabela: `4`, com a lista suportada.
- `BOB_GITLEAKS_BASE_URL` troca a base de download (espelho e teste do caminho de falha).

## Alternativas

Pedir ao dev (rejeitado por RE-Q1 A); `brew`/gerenciador do SO (não existe em toda máquina; pode pedir `sudo`); `go install` (exige Go).

## Consequências

Trocar a versão do gitleaks exige editar só a tabela e os 4 sha256.
