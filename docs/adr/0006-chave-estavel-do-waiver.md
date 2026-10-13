# A chave estável do waiver de mutação

Status: aceita em 12/10/2026, às 19h58 (São Paulo), na decisão do Emerson na #25. O merge desta ADR e da mudança na spec precisa do OK dele.

## Contexto

A [#25](https://github.com/fazedordecodigo/bob/issues/25) pede uma chave estável para o waiver de mutação. O casamento aceitava o id do mutmut (`bob_quality.mutate.x_f__mutmut_12`), o nome nu da função, `arquivo:função` e `arquivo::função`. O número `__mutmut_N` muda quando uma mutação entra ou sai antes dele na mesma função. O nome nu casava em todo arquivo. `bob waive` gravava qualquer alvo, inclusive um que não existe.

O mutmut lê `setup.cfg` e grava `mutants/` no cwd. O bob injetava a configuração no `setup.cfg` do repo e o restaurava num `finally`. Um SIGKILL não executa o `finally`.

O Emerson decidiu em 12/10/2026, às 19h58 (São Paulo): a chave é arquivo, função e descrição da mutação, no lugar de `__mutmut_N`. Os waivers existentes migram para o formato novo.

## Decisão

O id de um waiver de mutação tem duas formas.

- `arquivo::função` dispensa todo sobrevivente da função.
- `arquivo::função::<descrição>` dispensa um sobrevivente.

A descrição é o `operator` que o bob já guarda no `Mutant`, sem espaço nas pontas. No Python é o texto do `mutmut show`, como a [0001](0001-adaptadores-sobre-ferramentas-de-mercado.md) fixa: as linhas removidas juntadas por ` ; `, depois ` -> `, depois as linhas acrescentadas. O relatório JSON do Stryker não traz diff. No TypeScript a descrição é `{mutatorName}@{linha}:{coluna}-{linha}:{coluna}`, do início ao fim do mutante, mais ` -> {replacement}` quando o relatório traz `replacement`. O `mutatorName` sozinho não basta, porque dois `ArithmeticOperator` da mesma função dividiriam a chave.

A forma exata só existe quando nenhum outro sobrevivente do mesmo arquivo e da mesma função tem a mesma descrição. Dois sobreviventes iguais só têm a forma de função, e um humano decide se ela vale. Mutante `killed`, `timeout` ou `no_coverage` não tem alvo. Mutante sem arquivo também não.

`survivor_targets`, em `waivers.py`, é o único lugar que monta essas chaves. Python e TypeScript passam por ele. O id da ferramenta (`__mutmut_N` e `arquivo:número` do Stryker), o nome nu e `arquivo:função` deixam de casar. O id do mutante continua no relatório. Um id com prefixo da [0005](0005-modelo-de-gate-das-analises-novas.md), como `coverage:<arquivo>`, nunca é igual a uma chave que começa com o caminho do arquivo. Não há lista de prefixos.

A coluna Alvo da tabela de sobreviventes mostra a forma exata, ou `—` quando ela não existe. O `report.json` traz o mesmo valor no campo `target`.

`bob waive` só grava um alvo de sobrevivente lido de `.bob/mutation-cache.json` (Python) ou `.bob/stryker-mutants.json` (TypeScript). O gate do Stryker grava esse segundo arquivo depois de ler o relatório. Um alvo fora dos dois sai com 4 antes de qualquer escrita. Motivo ausente e alvo vazio continuam verificados antes. `write_waivers` é o único escritor de `.bob/waivers.yaml`, e um id longo fica numa linha.

`load_waivers` não confere o formato do id. Um id editado à mão que não casa com nada deixa o sobrevivente sem waiver, e o gate sai com 3.

O mutmut roda em `<--out>/mutmut/`. Essa pasta tem um link simbólico para cada entrada do topo do repo, menos `.git`, `mutants` e a entrada que contém a própria pasta. Quando o bob injeta a configuração, o `setup.cfg` dela é um arquivo próprio. O `setup.cfg` e o `mutants/` do repo nunca são escritos, então um processo morto não deixa nada para restaurar.

Os 17 waivers do próprio bob foram confrontados com uma corrida do mutmut 3.8.0 nas seis funções, pelo adaptador do bob. Dezesseis viraram a forma exata, com o mesmo motivo, autor e data. `bob_quality.mutmut_tool.x_failure_text__mutmut_8` está `killed`. O teste `test_nonzero_mutmut_keeps_the_error_after_the_spinner` mata essa mutação, que troca o `"\n"` do `replace` por `"XX\nXX"`. A linha foi removida. Ela não dispensava nenhum sobrevivente, e guardar a descrição poderia alcançar um gêmeo depois.

## Consequências

No Python, um waiver exato continua valendo depois de uma edição em outra parte da função, inclusive uma linha inserida acima, desde que o texto da mutação não mude. No TypeScript, uma linha inserida acima do mutante muda a descrição. O waiver antigo deixa de casar, o gate sai com 3 e o agente grava o alvo novo. O waiver não passa para outro mutante.

O waiver de função cobre também os sobreviventes que a função ganhar depois. O revisor vê essa forma na tabela de waivers.

Um gate da [0005](0005-modelo-de-gate-das-analises-novas.md) que ainda não existe não tem alvo conhecido. `bob waive` recusa os ids dele com 4 até a issue que implementar o gate somar esses ids aos alvos conhecidos.

A mudança na spec e esta ADR precisam do OK do Emerson no merge.
