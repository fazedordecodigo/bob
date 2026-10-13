---
name: harden
description: "Matar um mutante sobrevivente dentro do razoável, ou gravar um waiver. Use quando `bob mutate` ou `bob check --gates mutate` sair com 3, ou quando o relatório listar um sobrevivente sem waiver."
---

# harden

Matar o mutante com um teste mais forte, ou registrar um waiver de uma linha. A regra é nunca enfraquecer o código de produção para o mutante morrer.

## Quando

- `bob mutate` ou `bob check --gates mutate` sai com 3
- `.bob/report.md` lista um mutante sobrevivente sem waiver
- O mesmo exit lista `no_coverage` nas funções do diff. Um waiver não cobre esse status. O teste tem de executar o mutante.

## Passos

1. Ler o sobrevivente: alvo, função, arquivo:linha e operador, no relatório.
2. Escrever um teste que falha se o operador estiver aplicado e passa no código atual. Feito quando uma nova `bob mutate` não lista mais esse sobrevivente sem waiver.
3. Se o mutante não deve ser morto (comportamento equivalente, ou fora do que dá para provar com um teste pequeno), gravar `bob waive <file::function|Target> --reason "texto de uma linha"`. Copie o Alvo da tabela para dispensar só esse mutante. Alvo `—` quer dizer que outro sobrevivente da mesma função tem a mesma descrição. Aí só `arquivo::função` dispensa, e ele cobre todo sobrevivente da função. `bob waive` sai com 4 se o alvo não é de um sobrevivente da última mutação. Feito quando o waiver aparece no topo de `.bob/report.md` e o exit deixa de ser 3.
4. Repetir até não restar sobrevivente sem waiver.

## Dentro do razoável

Mate o mutante quando um teste local, no arquivo de teste da função, consegue provar a diferença. Não persiga mutante que exige cenário artificial, efeito colateral irrelevante ou comportamento que o contrato não distingue. Esse caso é waiver, para o humano julgar no review.

## Nunca enfraquecer o código de produção

O teste é que aperta. O código de produção fica.

Não faça isto para o mutante morrer:

- apagar um check, um `raise` ou um ramo
- alargar uma comparação (`>` para `>=`) ou afrouxar um limite
- mudar o valor que a função devolve
- marcar a linha com `pragma: no mutate` para esconder o mutante

Waiver sem motivo é rejeitado. Motivo de uma linha, no topo do relatório.
