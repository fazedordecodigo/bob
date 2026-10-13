# O diff filtra o veredito

Status: aceita em 10/10/2026, registrada em 12/10/2026. O item da duplicação segue a decisão 4 revista em 12/10/2026 (#75).

## Contexto

A pesquisa diz para medir só o que mudou, para o custo ficar baixo. A decisão 3 da spec diz que os gates bloqueiam só pelas funções alteradas. A dívida antiga aparece como informação. A user story 11 tira a mutação do hook local pelo mesmo motivo.

Uma deleção pura dentro de uma função ficava fora do diff. O PR #17 faz o parser registrar a linha âncora quando o hunk novo tem comprimento zero.

## Decisão

As ferramentas medem a árvore de `paths.include`. O diff só escolhe o que pode bloquear.

`changed_lines` em `diff.py` roda `git diff --unified=0 <base>...HEAD` e guarda o lado novo. `function_is_changed` é verdade quando alguma linha alterada cai em `[start, end]`.

- CRAP bloqueia quando uma função considerada tem CRAP maior ou igual a `crap.max_per_function`. O padrão é 10. Com `crap.scope` igual a `changed`, só funções tocadas entram. Qualquer outra string não vazia conta toda função medida.
- jscpd vê a árvore inteira. Um clone é novo quando um dos lados cruza o diff. Entra na conta e no relatório o clone novo que passa em `duplication.min_similarity` e `duplication.min_lines`. O padrão é aviso, e o exit do gate continua 0. No modo fail (`duplication.new_clones: fail` ou `--dry-fail`), o gate sai com 1 quando a conta passa de `duplication.max_new_clones`. A decisão 4 fecha isso.
- Dependências bloqueiam a aresta cuja origem, destino, ou outro módulo do mesmo componente fortemente conexo em Python é um arquivo alterado. A decisão 6 ganhou a frase do componente no commit `9be1cb2`. Arestas fora do diff ficam no relatório e não mudam o exit.
- Mutação remuta função alterada ou função com sobrevivente sem waiver no cache. O cache mora em `.bob/mutation-cache.json`. A chave da corrida é a versão do mutmut e a impressão da suíte. Se uma das duas muda, os resultados guardados ficam inelegíveis para reuso, e a corrida ainda remuta um sobrevivente sem waiver fora do diff.

O campo `delta` existe no modelo e no top 5. Nada o preenche. A spec pede o delta contra a base. O PR #17 deixou esse delta fora da fatia.

## Consequências

Um hunk de deleção com comprimento zero marca a linha de início. A função que contém essa linha entra no CRAP e na mutação. A linha seguinte a uma deleção na fronteira de duas funções pode puxar a vizinha.

Editar uma linha dentro de um clone antigo torna esse clone novo, porque um dos lados passa a cruzar o diff. No modo fail, com o teto padrão 0, essa edição falha o gate.

Quando a chave do cache não bate, os corpos ficam inelegíveis para reuso e os nomes dos sobreviventes sem waiver permanecem. A corrida seguinte remuta o diff e essas funções. O PR #43 diz que a chave existe para não esconder sobrevivente.

A issue #24 continua aberta para métodos de classe. O prefixo que escolhe o mutante não cobre o id `xǁ`. A issue #8 continua aberta para o Stryker.
