---
name: harden
description: "Matar um mutante sobrevivente dentro do razoável, ou gravar um waiver. Use quando `bob mutate` ou `bob check --gates mutate` sair com 3, ou quando o relatório listar um sobrevivente sem waiver."
---

# harden

Matar o mutante com um teste mais forte, ou registrar um waiver de uma linha. A regra é nunca enfraquecer o código de produção para o mutante morrer.

## Quando

- `bob mutate` ou `bob check --gates mutate` sai com 3
- `.bob/report.md` lista um mutante sobrevivente sem waiver

## Passos

1. Ler o sobrevivente: id, função, arquivo:linha e operador, no relatório.
2. Escrever um teste que falha se o operador estiver aplicado e passa no código atual. Feito quando uma nova `bob mutate` não lista mais esse id como sobrevivente sem waiver.
3. Se o mutante não deve ser morto (comportamento equivalente, ou fora do que dá para provar com um teste pequeno), gravar `bob waive <mutant-id|function> --reason "texto de uma linha"`. Feito quando o waiver aparece no topo de `.bob/report.md` e o exit deixa de ser 3.
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
