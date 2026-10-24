# U8: forma dos docs, do teste de paridade e do passo 14

Status: aceita pelo Emerson em 22/10/2026, no Plan Approval da U6, da U7 e da U8. Publicada em `docs/adr/` na U9.

## Decisão

- **Prompt.** O texto exato dos 2 arquivos fica num anexo da ET (`u8-docs/code-generation/tasks/T1-anexo/docs/`), gerado a partir do CT18. Só o bloco `perfil` muda, em 2 pontos: a troca da ADR 0021 e `S=${SHELL:-}` / `case "${S##*/}" in` no lugar de `case "${SHELL##*/}" in`. Com `set -u`, um `SHELL` ausente derrubava o bloco: conferido em `sh` e `dash`, 2026-10-22. O agente copia byte a byte (sha256 na ET).
- **"Bloco de shell"** (CT17, "primeiro bloco de código de instalação") = bloco cercado com info string `bash`, `sh`, `shell` ou `console`. Fica de fora o `mermaid` do README, que vem antes da instalação. Nos docs pt-BR, o comando único é a forma `… | sh -s -- --lang pt-BR` do CT2.
- **Seção `## Update` / `## Atualizar`** nos 4 docs de instalação, com `bob update` e `bob --version` (FR8.3), logo depois da alternativa.
- **Teste.** `tests/test_docs_pins.py` lê os pins pelas funções do pacote e o `install.sh` pelas fontes únicas. Entra na guarda de rede (`_UNIT_ARGS`).
- **Passo 14.**
  - `prompt_blocks` extrai os blocos com a mesma regex do CT18 para arquivos numerados.
  - `box_platform` usa a tabela do bloco `plataforma`.
  - `manifest` é um `python3 -c`.
  - O `pip freeze` é normalizado na linha `bob-quality @`.
  - `VERIFY_REMOTE=1` → "não se aplica".
  - Alvo ≤ 360 s.
- **Ordem.** T1 → T2 → T3 em sequência (mesmo arquivo de teste). A T4 roda depois da T1, em paralelo com a T2 e a T3. A T3 e a T4 escrevem no `CHANGELOG.md`: a que entra depois põe o parágrafo dela no topo (regra R-CL).

## Consequências

O CT17 ganha a seção de atualizar e a definição de bloco de shell (esclarecimento compatível). O teste falha se o CT2 mudar uma fonte única sem o prompt acompanhar (FR8.5).
