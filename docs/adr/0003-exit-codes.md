# Exit codes 0, 1, 2, 3 e 4

Status: aceita em 10/10/2026, com ajustes em 11/10/2026. Registrada em 12/10/2026. O exit 1 do dry segue a decisão 4 revista em 12/10/2026 (#75).

## Contexto

A pesquisa publica o contrato do gate como JSON mais os códigos 0, 2 e 3, no espírito do crapper e do mutator. A spec publica cinco códigos e diz que são inspirados no mutator.

```text
0 passou
1 algum gate falhou
2 baseline quebrado
3 mutante sobrevivente sem waiver
4 erro de configuração ou ferramenta ausente
```

As duas listas continuam nos dois documentos. Não há uma frase que diga por que 1 e 4 foram acrescentados ao trio.

## Decisão

`exit_codes.py` nomeia os cinco inteiros. `check.py` fica com o maior. Um aviso contribui 0.

O uso que a spec e os PRs fecharam é este.

- 1 sai de `crap_verdict`, de `deps_verdict` ou do dry no modo fail. CRAP igual ao limite falha. Uma violação de dependência no diff falha. No modo fail, mais clones novos que `duplication.max_new_clones` falham. No modo warn, que é o padrão da decisão 4, a duplicação contribui 0. O PR #26 corrigiu o jscpd. No dry, falta de Node ou falha da ferramenta vira gate `not_run` e exit 0, mesmo no modo fail.
- 2 sai quando a suíte que mede cobertura falha, ou quando a mutação reusa essa falha. Pytest 0 e 5 contam como suíte boa. Vitest só aceita 0.
- 3 sai de `mutate._finish`, quando o status é `survived` e não há waiver, e quando há `no_coverage` nas funções do diff. `suspicious` e `segfault` do mutmut entram no status `survived`. `timeout` não. Um waiver não cobre `no_coverage`. O aviso sem mudar o exit foi a decisão do Emerson em 11/10/2026, entregue no PR #36. A fase 2, em que `no_coverage` no diff falha, é a issue #41.
- 4 sai do preflight, em inglês no stderr, sem gravar relatório, para YAML inválido e para waiver ilegível. O PR #51 fechou o caminho que dava traceback e exit 1. O preflight também sai 4 para `duplication.new_clones`, `max_new_clones`, `min_similarity` e `min_lines` com tipo ou valor inválido. Um `--max-new-clones` negativo sai 4 sem gravar relatório, com `--max-new-clones must be at least 0` no stderr. Um `--max-new-clones` que não é inteiro é uso inválido e também sai 4. 4 também sai quando a ferramenta ausente impede a medição pedida. Num repositório com Python e TypeScript, Node ausente não é 4. O Python segue. O TypeScript aparece pulado. A decisão 10, datada de 11/10/2026, aprova o que o PR #27 já fazia.

Um nome de gate desconhecido grava `not_run` e contribui 0. O processo pode sair 0.

## Consequências

O agente que lê a skill `bob-check` trata 2 como suíte quebrada. O `ArgumentParser` da CLI sai com 4 quando falta o subcomando ou a flag é ilegal, e não grava relatório. Esse 4 não é `BASELINE_BROKEN`. O Emerson deu o OK em 13/10/2026, às 15:05.

O inteiro 4 tem mais de um caminho. O preflight não grava arquivo. `_fail_early` grava o relatório com os gates em `not_run`. Ferramenta ausente no CRAP, no deps ou na mutação grava o relatório e marca só o gate quebrado. jscpd quebrado não usa 4.

A decisão 10 não está no orquestrador. Está em `crap_gate` e em `deps_gate`. O dry não a aplica, porque o dry sem ferramenta devolve 0 nos dois modos.

A issue #53 segue aberta para a validação semântica que o PR #51 deixou de fora.
