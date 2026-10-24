# Distribuição por release do GitHub com assets

Status: aceita pelo Emerson em 18/10/2026, na aprovação do desenho da aplicação. Publicada em `docs/adr/` na U9.

## Contexto

- FR1.2: direto do GitHub, sem PyPI. FR1.4 e G-2.3: só release publicada conta.
- A API `GET /repos/{owner}/{repo}/releases/latest` devolve "the most recent non-prerelease, non-draft release" (https://docs.github.com/en/rest/releases/releases, acessada em 2026-10-18).
- O link `/releases/latest/download/<asset>` baixa o asset da última release (https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases, acessada em 2026-10-18).
- O repo não tem tags nem releases (2.1).

## Decisão

- Cada release leva três assets: `install.sh`, `bob_quality-<v>-py3-none-any.whl` e `SHA256SUMS` (dos outros dois).
- Comando do dev: `curl -fsSL https://github.com/fazedordecodigo/bob/releases/latest/download/install.sh | sh`.
- O `install.sh` acha a versão pela API `releases/latest` (ou `BOB_VERSION`) e baixa o wheel e o `SHA256SUMS` dessa tag.
- Tag no formato `vX.Y.Z`. A versão do wheel é a da tag (o workflow confere `pyproject.toml` = tag).
- `BOB_RELEASES_URL` troca a base de API e downloads. Uso: testes e espelho. Padrão: GitHub.
- O workflow `release` (C11) cria a release com os assets, depois do `bob doctor` e do `verify-install.sh`. Disparo manual pelo Emerson (P2).

## Alternativas

`pip install git+https://...@tag` direto (sem `install.sh` não há como conferir Python/Node antes nem criar launcher); pipx/uv (não são pré-requisitos); script em `raw.githubusercontent.com/.../main` (a `main` pode estar quebrada, como hoje).

## Consequências

- A API sem token tem limite por IP (Não verificado o número atual). Erro 403/429 vira `4` com ação "tente de novo ou defina `BOB_VERSION`".
- Release sem os três assets quebra a instalação. O workflow é o único caminho de criar release.
