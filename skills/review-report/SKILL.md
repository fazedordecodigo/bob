---
name: review-report
description: "Resumir `.bob/report.md` no corpo do PR. Use ao escrever ou atualizar um pull request depois de `bob check`."
---

# review-report

Escrever o corpo do PR no molde Summary / Evidence / Merge Danger. O relatório do bob entra em Evidence e em Merge Danger.

Fonte do formato: `docs/SPEC.md`. Rode `bob check` (skill `bob-check`) antes, para existirem `.bob/report.md` e `.bob/report.json` (`schema_version: 1`).

## Quando

- Escrever o corpo de um PR depois de `bob check`
- Atualizar um PR depois de um novo `bob check`

## Interface da CLI

Os comandos abaixo são os que a CLI registra.

```
bob check   [--base REF] [--gates crap,dry,deps,mutate] [--config bob.yaml] [--format md|json|both] [--out .bob/]
bob crap    [--base REF] [--threshold N] [--coverage-file PATH]
bob dry     [--base REF]
bob deps
bob mutate  [--base REF] [--since-last-run] [--max-workers N]
bob waive   <mutant-id|function> --reason "texto de uma linha"
bob doctor  # verifica ferramentas e versões instaladas
```

- `0` passou
- `1` algum gate falhou (limite violado)
- `2` baseline quebrado (testes falham antes de medir)
- `3` mutante sobrevivente sem waiver, ou `no_coverage` nas funções do diff
- `4` erro de configuração ou ferramenta ausente

## Passos

1. Confirmar `.bob/report.md`. Se faltar, gerar com `bob check --format both`. Feito quando `.bob/report.md` existe.
2. Ler o relatório na ordem da spec (abaixo). Feito quando as oito seções foram lidas.
3. Colocar os vereditos e **Onde focar o review** em Evidence (antes/depois: último `bob check` que falhou vs a corrida que passou).
4. Apontar o caminho `.bob/report.md` para a página completa. O corpo do PR fica o resumo de uma página.

Conclusão da skill: o PR tem vereditos, a lista de foco e o caminho para `.bob/report.md`.

## Formato do relatório

Lista de `docs/SPEC.md` (fonte):

1. Cabeçalho: commit, base, data, versões das ferramentas.
2. Veredito por gate: ✅ passou / ⚠️ aviso / ❌ falhou / ⏭️ não executado (com motivo).
3. **Onde focar o review**: arquivos alterados ordenados por risco (maior CRAP + sobreviventes + clones).
4. Top 5 funções de maior CRAP no diff (função, arquivo:linha, CC, cobertura, CRAP, delta).
5. Mutantes sobreviventes (sem waiver = falha) e mutantes sem teste (`no_coverage`) nas funções do diff, os dois com exit 3, agrupados por função e arquivo, e tabela de waivers com justificativa. Um waiver não cobre `no_coverage`.
6. Clones novos (pares, similaridade, linhas).
7. Violações e ciclos de dependência.
8. Rodapé: como reproduzir localmente (comando exato).

⏭️ permanece ⏭️, com o motivo.

## Molde do corpo do PR

```markdown
## Summary

<o menor diagrama, árvore ou trecho de diff que mostre o que muda>

## Evidence

- **Before:** <exit e linhas do `bob check` que falhou>
  **After:** <exit `0` e os vereditos atuais>
- **Onde focar o review:** <a lista do relatório>
- <cada waiver, com a justificativa>
- Relatório completo: `.bob/report.md`

## Merge Danger

**Door:** <one-way ou two-way. Reverter o PR é a porta de duas vias.>

**Blast Radius:** <uma palavra>

<Gates ❌ e sobreviventes sem waiver aumentam o blast radius. Liste os ⚠️ de clones e cada waiver para o humano julgar.>
```

Se o repositório já tem um template de PR, use o dele e ponha os mesmos itens nas seções de evidência e de risco.
