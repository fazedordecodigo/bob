# Visão técnica

[Índice](../README.md) · [ADRs](adrs.md) · [SPEC](spec.md) · [Códigos de saída](../exit-codes.md)

O bob é a CLI do pacote pip `bob-quality` e o plugin de marketplace `bob`. Nada foi publicado no PyPI nem num marketplace. Uma execução mede um diff e devolve um relatório mais um código de saída. As skills `bob-check`, `harden` e `review-report` são o que Cursor, Claude Code, GitHub Copilot e Devin carregam. O Codex é nomeado só como leitor de `.agents/skills`.

Esta página descreve o código na `main`. O [ADR 0000](adr/0000-architecture-review.md) é a leitura de 12/10/2026 no commit `246d2eb`. Gates posteriores e o adaptador do Stryker estão na árvore agora. O ADR não mudou.

## Quatro costuras

1. `cli.py` resolve o idioma da saída e roda o preflight. `check`, `crap`, `dry`, `deps` e `mutate` viram `run_check`. `doctor`, `waive` e `report` saem desse caminho depois do mesmo preflight. `report` não mede.
2. Os gates iniciam as ferramentas pinadas. Os adaptadores interpretam texto ou JSON no modelo de `models.py`. O núcleo não importa um adaptador.
3. `crap.py`, `core.py` e `probe.py` juntam complexidade ciclomática e cobertura de linha, aplicam a fórmula e marcam o que o diff pode bloquear.
4. `check.py` monta o `Report`. `report.py` grava `.bob/report.md` e `.bob/report.json` com `schema_version` 1. O exit do processo é o código mais alto entre os gates.

## O que o diff filtra

As ferramentas medem a árvore sob `paths.include`. `changed_lines` em `diff.py` roda `git diff --unified=0 <base>...HEAD` e fica com o lado novo. Um hunk novo de comprimento zero ainda registra a linha âncora. `function_is_changed` é uma sobreposição inclusiva de `[start, end]`.

Só um achado que o diff seleciona pode mudar o código de saída. O resto pode aparecer no relatório. O [ADR 0002](adr/0002-o-diff-filtra-o-veredito.md) registra essa divisão. A regra do loader para `crap.scope` é mais estreita do que uma frase desse ADR: só `changed` e `all` são aceitos. Ver [Schema de configuração](../reference/configuration.md).

## Gates

`DEFAULT_GATES` é `crap`, `dry`, `deps`. Não há detector de CI dentro da CLI. A Action passa `crap,dry,deps,mutate`, a menos que o workflow defina `gates`.

`check.py` também roda `coverage`, `test_smells`, `cognitive`, `supply`, `security`, `typing`, `secrets` e `dead_code` quando `--gates` os nomeia. Um nome desconhecido é `not_run` e contribui com `0`. O churn é medido em todo check e não é um gate.

A mutação é diferencial. Python usa mutmut e `.bob/mutation-cache.json`. TypeScript usa Stryker, `.bob/stryker-incremental.json` e `.bob/stryker-mutants.json`. O [ADR 0001](adr/0001-adaptadores-sobre-ferramentas-de-mercado.md) registrou a ausência de um adaptador do Stryker. `src/bob_quality/adapters/stryker.py` está na árvore agora.

## Waivers e o relatório

Os waivers são `.bob/waivers.yaml`, com `id`, um `reason` de uma linha, `author` e `date`. Ids de mutação são `file::function` ou `file::function::<description>` ([ADR 0006](adr/0006-chave-estavel-do-waiver.md)). Os outros gates usam os prefixos de [Gates e waivers](../guides/gates-and-waivers.md).

`schema_version` permanece 1. Seções novas são opcionais em `report_v1.json`. O JSON permanece em inglês. O Markdown traduz os títulos. Ver [report.json](../reference/report-json.md).

## O que este repositório não faz

O workflow `package` gera um sdist e um wheel, roda `twine check` e roda `bob doctor`. Ele não publica. A publicação em marketplace fica na aprovação do Emerson. O site público de documentação é o [ADR 0007](adr/0007-gerador-do-site.md): Docusaurus 3.x, Algolia DocSearch, inglês como idioma padrão, pt-BR como segundo, primeiro em `https://fazedordecodigo.github.io/bob/`, isolado em `website/`. O domínio próprio é a [issue 163](https://github.com/fazedordecodigo/bob/issues/163).
