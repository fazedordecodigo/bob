---
name: bob-check
description: "Rodar `bob check`, ler o JSON e iterar até exit 0. Use ao verificar um diff, antes de abrir ou atualizar um PR, ou quando um gate falhar."
---

# bob-check

Invocar a CLI, ler o veredito, corrigir o que ela nomeia, repetir até exit 0. Os comandos abaixo são os que a CLI registra.

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
bob waive   <file::function|Target> --reason "texto de uma linha"
bob doctor  # verifica ferramentas e versões instaladas
bob <comando> [--lang en|pt-BR]  # idioma da saída (padrão: en)
```

`--base` padrão vem de `bob.yaml` (`origin/main` se o repo não disser outro). Use a mesma base do PR.

`--format both` grava `.bob/report.json` e `.bob/report.md`.

Por padrão, o hook local roda `bob check --gates crap,dry,deps`. O CI roda `bob check --gates crap,dry,deps,mutate`. Um `bob check` sem `--gates` roda `crap,dry,deps` e não roda `mutate`.

- Hook local: `bob check --gates crap,dry,deps`
- CI: `bob check --gates crap,dry,deps,mutate`

## Exit codes

- `0` passou
- `1` algum gate falhou (limite violado)
- `2` baseline quebrado (testes falham antes de medir)
- `3` mutante sobrevivente sem waiver, ou `no_coverage` nas funções do diff. Um waiver não cobre `no_coverage`.
- `4` erro de configuração ou ferramenta ausente
O `4` é erro de configuração ou ferramenta ausente, ou uso inválido da CLI.
Uso inválido: o stderr começa com `usage: bob`, contém `error:` e não menciona baseline. Essa execução não grava relatório. Um arquivo `.bob/` já presente não é desta execução. Não é o exit `2`. A ajuda (`-h`, `--help`) sai com `0`. Catálogo em docs/exit-codes.md#exit-4.

## Ler o JSON

`.bob/report.json` (`schema_version: 1`) espelha `.bob/report.md`.

Veredito por gate: ✅ passou / ⚠️ aviso / ❌ falhou / ⏭️ não executado (com motivo). Exit `0` é o passe do check. ⚠️ (clone novo) não falha. `no_coverage` nas funções do diff é ❌ e sai `3`. ⏭️ fica ⏭️ com motivo. Violação de dependência é ❌.

Cada linha acionável traz função, arquivo:linha, métrica e limite.

## Iterar

Conclusão da skill: `bob check` sai com `0`.

1. Rodar `bob check --format both` com o `--base` do PR. Se o exit é `4` e o stderr começa com `usage: bob`, contém `error:` e não menciona baseline, seguir o passo 5 e repetir com o argv corrigido. Um `.bob/report.json` de outra corrida não fecha esse caso. Fora esse caso, feito quando o processo devolve um exit code e `.bob/report.json` existe.
2. Exit `1`: ajustar a função ou arquivo:linha até a métrica caber no limite. Feito quando o check é reexecutado.
3. Exit `2`: fazer os testes passarem (baseline). A medição começa depois disso. Feito quando o check é reexecutado.
4. Exit `3`: matar o mutante com teste mais forte, ou `bob waive <file::function|Target> --reason "texto de uma linha"`, copiando o Alvo da tabela de sobreviventes. Waiver vale só com motivo de uma linha. O id do mutante e o nome nu da função saem com `4`. `no_coverage` se mata com um teste que executa o mutante. `bob waive` recusa esse alvo. Feito quando o check é reexecutado.
5. Exit `4` com stderr que começa com `usage: bob`, contém `error:` e não menciona baseline: corrigir o argv e repetir. Não é o exit `2`. `bob doctor` não se aplica. Não ler `.bob/` deixado por outra corrida como veredito desta. Senão, `bob doctor` e corrigir ferramenta ou config. Feito quando o check é reexecutado.
