# Atualização e versão visível

Status: aceita pelo Emerson em 18/10/2026, na aprovação do desenho da aplicação. Publicada em `docs/adr/` na U9.

## Contexto

FR6.1–FR6.5, US5.1, US5.2, US7.2.

## Decisão

- `bob update`: lê a última release publicada (ADR 0011). Compara `vX.Y.Z` como tupla de inteiros com a versão do pacote (`importlib.metadata`).
- Igual: "já está na release mais nova", 0 arquivos alterados, sai `0`.
- Mais velha que a instalada: mesma mensagem, sai `0`.
- Mais nova: baixa `install.sh` e `SHA256SUMS` dessa tag, confere, roda com `BOB_VERSION=<tag>` na pasta atual. O `bob setup` da versão nova atualiza as skills com marcador e preserva o resto.
- `bob --version`: duas linhas: versão do pacote; versão das skills em `.agents/skills` (lida de `.bob-version`) ou "skills não instaladas neste projeto".
- O mesmo `curl ... | sh` também atualiza (pega a última). `bob update` é o atalho documentado.

## Alternativas

Atualizar só o pacote com pip (não atualiza skills); seguir a `main` (rejeitado em RQ-Q1 A).

## Consequências

"Projeto na release antiga" = `.bob-version` antigo nas skills. Pacote novo e skills velhas num projeto não reconfigurado: o `bob --version` mostra a diferença.
