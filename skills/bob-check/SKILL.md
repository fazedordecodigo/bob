---
name: bob-check
description: "Rodar `bob check`, ler o JSON e iterar até exit 0. Use ao verificar um diff, antes de abrir ou atualizar um PR, ou quando um gate falhar."
---

# bob-check

Invocar a CLI, ler o veredito, corrigir o que ela nomeia, repetir até exit 0. A superfície abaixo é a de `docs/SPEC.md`, citada à risca.

## Quando

- Depois de mudar código de produção ou testes no diff
- Antes de abrir ou atualizar um PR
- Depois de um `bob check` com exit diferente de 0

## Invocar

```
bob check   [--base REF] [--gates crap,dry,deps,mutate] [--config bob.yaml] [--format md|json|both] [--out .bob/]
bob crap    [--base REF] [--threshold N] [--coverage-file PATH]
bob dry     [--base REF]
bob deps
bob mutate  [--base REF] [--since-last-run] [--max-workers N]
bob report  [--in .bob/] [--out .bob/report.md]
bob waive   <mutant-id|function> --reason "texto de uma linha"
bob doctor  # verifica ferramentas e versões instaladas
bob <comando> [--lang en|pt-BR]  # idioma da saída (padrão: en)
```

`--base` padrão vem de `bob.yaml` (`origin/main` se o repo não disser outro). Use a mesma base do PR.

`--format both` grava `.bob/report.json` e `.bob/report.md`.

Por padrão, `check` no hook local executa `crap,dry,deps`; no CI executa todos.

- Hook local: `bob check --gates crap,dry,deps`
- CI: `bob check` (todos os gates, inclusive `mutate`)

## Exit codes

- `0` passou
- `1` algum gate falhou (limite violado)
- `2` baseline quebrado (testes falham antes de medir)
- `3` mutante sobrevivente sem waiver
- `4` erro de configuração ou ferramenta ausente

## Ler o JSON

`.bob/report.json` (`schema_version: 1`) espelha `.bob/report.md`.

Veredito por gate: ✅ passou / ⚠️ aviso / ❌ falhou / ⏭️ não executado (com motivo). Exit `0` é o passe do check. ⚠️ (clones novos e mutantes sem teste) não falha. ⏭️ fica ⏭️ com motivo. Violação de dependência é ❌.

Cada linha acionável traz função, arquivo:linha, métrica e limite.

## Iterar

Conclusão da skill: `bob check` sai com `0`.

1. Rodar `bob check --format both` com o `--base` do PR. Feito quando o processo devolve um exit code e `.bob/report.json` existe.
2. Exit `1`: ajustar a função ou arquivo:linha até a métrica caber no limite. Feito quando o check é reexecutado.
3. Exit `2`: fazer os testes passarem (baseline). A medição começa depois disso. Feito quando o check é reexecutado.
4. Exit `3`: matar o mutante com teste mais forte, ou `bob waive <mutant-id|function> --reason "texto de uma linha"`. Waiver vale só com motivo de uma linha. Feito quando o check é reexecutado.
5. Exit `4`: `bob doctor` e corrigir ferramenta ou config. Feito quando o check é reexecutado.
