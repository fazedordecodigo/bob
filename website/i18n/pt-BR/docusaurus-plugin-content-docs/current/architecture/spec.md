# SPEC

[Índice](../README.md) · [Visão técnica](overview.md) · [ADRs](adrs.md)

A especificação aprovada é [SPEC.md](SPEC.md). Ela permanece o registro do que foi decidido, inclusive comportamento que a CLI ainda não implementa. Estes guias documentam o código. Eles não editam a spec.

Leia a spec para o enunciado do problema, as histórias de usuário, as decisões de implementação e os critérios de aceitação do MVP. Leia os guias quando precisar do comando, da flag, da chave ou do código de saída que o processo de fato usa.

## Onde o código e a spec divergem

As notas abaixo são as divergências de que estas páginas dependem. O código é o comportamento.

**O CI não roda todo gate de dentro da CLI.** A spec diz que o check no CI roda todo gate. `DEFAULT_GATES` em `src/bob_quality/check.py` é `crap`, `dry`, `deps`. O input `gates` da Action tem padrão `crap,dry,deps,mutate` (`.github/actions/bob/action.yml`). `coverage`, `test_smells`, `cognitive`, `supply`, `security`, `typing`, `secrets` e `dead_code` só rodam quando `--gates` os nomeia. Não há detector de CI na CLI.

**A cobertura do CRAP é a fração de statements, não cobertura de branch.** A lista de adaptadores da spec diz que coverage.py e c8 devolvem cobertura de linha e de branch, inclusive lcov. `line_coverage` em `src/bob_quality/core.py` é a fração de linhas executáveis no intervalo da função. A fórmula em `src/bob_quality/crap.py` usa essa fração. O gate `coverage` é uma medição separada: diff-cover sobre o XML de coverage para Python e sobre o lcov do c8 para TypeScript.

**`crap.scope` aceita só `changed` e `all`.** O [ADR 0002](adr/0002-o-diff-filtra-o-veredito.md) diz que qualquer outra string não vazia conta toda função medida. O loader recusa qualquer outra string com exit `4`. Ver [Schema de configuração](../reference/configuration.md).

**O exit `4` durante a medição grava o relatório.** O preflight não grava nada. `_fail_early` em `check.py` grava o relatório quando o git falha ou uma ferramenta bloqueia a medição. A página de [códigos de saída](../exit-codes.md#saída-4) separa os dois caminhos. Uma frase curta do README que diz que o exit `4` não grava nada descreve o preflight.

**O Stryker está na árvore.** O [ADR 0001](adr/0001-adaptadores-sobre-ferramentas-de-mercado.md) e o [ADR 0000](adr/0000-architecture-review.md) registram um checkout sem adaptador do Stryker. `src/bob_quality/adapters/stryker.py` e os pins do Stryker em `doctor.py` estão na `main`. Esses ADRs são o registro da decisão anterior, não uma afirmação sobre a árvore atual.

**O relatório Markdown começa pelos waivers.** A ordem do relatório na spec começa pelo cabeçalho e pelo veredito. `to_markdown` emite `## Waivers` primeiro quando a seção existe. Ver [Relatórios](../guides/reports.md).

**O churn relativo está no relatório.** O [ADR 0005](adr/0005-modelo-de-gate-das-analises-novas.md) descreve o churn como a contagem de commits na janela. O código também grava uma taxa relativa: linhas alteradas divididas pela contagem de linhas do arquivo. A contagem de commits continua lá. A taxa é `null` quando o arquivo não tem linhas ou não pode ser lido. A seção ainda não muda o código de saída.
