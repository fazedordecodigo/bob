# O diff filtra o veredito

Status: aceita em 10/10/2026, registrada em 12/10/2026.

## Contexto

A pesquisa diz para medir só o que mudou, para o custo ficar baixo. A decisão 3 da spec diz que os gates bloqueiam só pelas funções alteradas. A dívida antiga aparece como informação. A user story 11 tira a mutação do hook local pelo mesmo motivo.

Uma deleção pura dentro de uma função ficava fora do diff. O PR #17 faz o parser registrar a linha âncora quando o hunk novo tem comprimento zero.

## Decisão

As ferramentas medem a árvore de `paths.include`. O diff só escolhe o que pode bloquear.

`changed_lines` em `diff.py` roda `git diff --unified=0 <base>...HEAD` e guarda o lado novo. `function_is_changed` é verdade quando alguma linha alterada cai em `[start, end]`.

- CRAP bloqueia quando uma função considerada tem CRAP maior ou igual a `crap.max_per_function`. O padrão é 10. Com `crap.scope` igual a `changed`, só funções tocadas entram. Qualquer outra string não vazia conta toda função medida.
- jscpd vê a árvore inteira. Um clone entra no relatório quando um dos lados cruza o diff. O status é aviso. O exit do gate continua 0. A decisão 4 fecha isso para o MVP.
- Dependências bloqueiam a aresta cuja origem, destino, ou outro módulo do mesmo componente fortemente conexo em Python é um arquivo alterado. A decisão 6 ganhou a frase do componente no commit `9be1cb2`. Arestas fora do diff ficam no relatório e não mudam o exit.
- Mutação remuta função alterada ou função com sobrevivente sem waiver no cache. O cache mora em `.bob/mutation-cache.json`. A chave da corrida é a versão do mutmut e a impressão da suíte. Se uma das duas muda, o mapa de funções é descartado.

O campo `delta` existe no modelo e no top 5. Nada o preenche. A spec pede o delta contra a base. O PR #17 deixou esse delta fora da fatia.

## Consequências

Um hunk de deleção com comprimento zero marca a linha de início. A função que contém essa linha entra no CRAP e na mutação. A linha seguinte a uma deleção na fronteira de duas funções pode puxar a vizinha.

Quando a chave do cache não bate, `_read_cache` devolve um mapa vazio. A corrida seguinte só vê as funções do diff atual. Um sobrevivente sem waiver que estava no cache, numa função que o diff não tocou, deixa de existir para o bob. O PR #43 diz que a chave existe para não esconder sobrevivente. O descarte inteiro, seguido do filtro do diff, esconde justamente esse conjunto.

A issue #24 continua aberta para métodos de classe. O prefixo que escolhe o mutante não cobre o id `xǁ`. A issue #8 continua aberta para o Stryker.
