# `BOB_INSTALL_PROFILE` leva o arquivo também em `already-marked`

Status: aceita pelo Emerson em 22/10/2026, no Plan Approval da U6, da U7 e da U8. Publicada em `docs/adr/` na U9.

## Contexto

O CT6 e o CT16 dão os valores `<arquivo>`, `already-on-path`, `already-marked` e `failed:<arquivo>`. Mas o texto aprovado do resumo (CT3) e o passo 13 do Comando de Verificação pedem `<arquivo> já tem a linha do bob; nada mudou`. Com `already-marked` sozinho, o `bob setup` não sabe qual arquivo citar. A outra saída seria o Python refazer a regra de `$SHELL`/`ZDOTDIR`, o que duplica a ADR 0013 em duas linguagens.

## Decisão

O valor passa a ser `already-marked:<arquivo absoluto>`. Os outros três ficam iguais. O `bob setup` aceita só estes 4 formatos. Qualquer outro, inclusive `already-marked` sem arquivo, é ignorado (sem linha).

## Consequências

É mudança de formato numa variável lida por máquina, então é incompatível: CT6 (linha `BOB_INSTALL_PROFILE`) e CT16 sobem para v2. Não há v1 a manter, porque nenhuma consumidora implementou o valor ainda. O bloco `perfil` do prompt (CT18, U8) grava `R="already-marked:$F"` (ver ADR 0028). **Aviso ao Maestro antes da ET**, porque o CT6 e o CT16 estão aprovados.
