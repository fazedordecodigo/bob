# Adaptadores sobre ferramentas de mercado

Status: aceita em 10/10/2026, registrada em 12/10/2026.

A decisão está na spec e nos tickets. A página de pesquisa ainda lista a alternativa como aberta.

## Contexto

A pesquisa de 10/10/2026 deixa a decisão 2 em aberto. Usar crapper, mutator e dryer do Uncle Bob como base, ou usar ferramentas de mercado. A mesma página diz que a recomendação do Bob é usar o código dele como template, sob licença 0BSD, e que o código não deve ser copiado.

A spec trata a escolha como feita. Lizard, coverage.py, c8, mutmut, StrykerJS, jscpd, import-linter e dependency-cruiser entram como dependências com versão fixada. Cada uma fica atrás de um adaptador. A fórmula CRAP, os limiares, o escopo no diff, a mutação diferencial e os waivers ficam no núcleo.

O commit `55216ad` é a primeira aparição dessa lista. A decisão 2 escolhe o lizard para Python e TypeScript contarem a complexidade ciclomática do mesmo jeito. A spec chegou a tratar o radon como adaptador opcional. Não há `adapters/radon.py`, pin nem runner, e a spec não o lista.

## Decisão

O núcleo não importa ferramenta. Um adaptador recebe a saída bruta e devolve o modelo em `models.py`. Os gates é que disparam o processo.

- `parse_lizard_csv` devolve funções com complexidade ciclomática.
- `parse_coverage_json` e `parse_coverage_final` devolvem cobertura por linha.
- `mutants_from_raw` devolve mutantes do mutmut.
- `parse_jscpd_json` devolve clones.
- `parse_import_linter` e `parse_dependency_cruiser` devolvem violações.

Não há registro de adaptadores nem classe de protocolo. `adapters/__init__.py` é um docstring. `core.py` e `crap.py` não importam esses módulos.

Stryker continua na spec e na issue #8, que segue aberta. Não há adaptador nem pin. Radon não está na lista de adaptadores nem na decisão 2.

## Consequências

Uma linguagem nova entra por um adaptador e um runner. O veredito de CRAP, de dependência e de mutação não muda de arquivo.

O preço é uma fronteira fácil de furar sem um import proibido. As docstrings de `models.py` nomeiam as ferramentas. O adaptador do mutmut também decide o prefixo da corrida e o que conta como falha da suíte. `mutate.py` reconstrói `Mutant` a partir do cache. Um status desconhecido no cache vira `survived`. O mesmo rótulo na saída ao vivo levanta `MutmutParseError`.

grimp não tem adaptador. O pin direto é `grimp==3.17`. O gate de dependências pede o grafo com `python -c` e `cycles.py` percorre as arestas. A spec só nomeia import-linter e dependency-cruiser.

A cobertura que entra no CRAP é a fração de statements no intervalo da função. O PR #20 diz que branch e lcov não entram nessa fatia. A spec, na lista de adaptadores, ainda fala em cobertura de branch e em lcov.
