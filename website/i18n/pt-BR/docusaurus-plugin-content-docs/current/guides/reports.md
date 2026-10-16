# Leitura do relatório

[Índice](../README.md) · [report.json](../reference/report-json.md) · [Códigos de saída](../exit-codes.md) · [CI](ci.md)

`bob check` e os comandos de um só gate gravam `.bob/report.md` e `.bob/report.json` por padrão. `--out` muda o diretório. `--format md`, `json` ou `both` (o padrão) escolhe o arquivo. `crap`, `dry`, `deps` e `mutate` sempre gravam os dois, porque `cli.py` chama `run_check` com `fmt="both"`.

`bob report` renderiza um `report.json` salvo como Markdown. Ele não mede de novo. Ver [CLI](../reference/cli.md#bob-report).

O schema é `src/bob_quality/schemas/report_v1.json`. `schema_version` é `1`.

## Ordem do Markdown

`to_markdown` em `src/bob_quality/report.py` emite as seções abaixo no idioma da saída. Os títulos aqui são os de `en`.

1. Título `# bob report`.
2. `## Waivers`, só quando já existem waivers ou a mutação rodou. O título `## Waivers` é a mesma string nos dois idiomas. As colunas da tabela são target, reason, author e date. Sem linhas o texto é `No waivers.`
3. Um cabeçalho com o commit, a base, a data e as versões das ferramentas. Os rótulos `Commit:` e `Base:` permanecem em inglês.
4. `## Verdict`, uma linha por gate: ✅ passed, ⚠️ warning, ❌ failed ou ⏭️ not run. Um motivo, quando há um, fica entre parênteses.
5. `## Where to focus the review`. Arquivos alterados ordenados por risco (maior CRAP, mais clones e, quando a mutação rodou, 100 a mais de risco para cada sobrevivente que bloqueia). Um sobrevivente com waiver, ou fora do diff, não acrescenta risco e não acrescenta um arquivo novo. Um arquivo com um clone recebe o sufixo `, clone`.
6. `## Top 5 functions by CRAP (diff)`. Função, arquivo:linha, CC, cobertura como percentual inteiro, CRAP e delta. Um delta ausente é `—`.
7. `## Information (old debt)`, só quando uma função fora do diff está no limite ou acima. O item termina com `outside the diff; does not block`.
8. `## Dependency violations and cycles`, depois `## Information (dependencies outside the diff)` quando há violações fora do diff.
9. `## New clones`. Cada par lista os arquivos, as linhas, os tokens e a similaridade.
10. `## Surviving mutants`, só quando a mutação rodou. Colunas: target, function, location, operator, waiver. O target é o que `bob waive` aceita para aquele sobrevivente, ou `—` quando outro sobrevivente da função tem a mesma descrição. Um sobrevivente sem waiver que não bloqueia carrega `outside the diff; does not block` na location.
11. `## Mutants without tests`, só quando o resumo da mutação tem `no_coverage`. A linha do total diz que isso bloqueia.
12. `## Diff coverage`, só quando o gate `coverage` está no veredito. Ela lista o percentual de cada linguagem medida e cada linha sem cobertura como `` `file:line` ``. Se o gate rodou e nenhuma linguagem mediu, a seção mostra o motivo e não tem tabela.
13. `## Diff tests`, só quando `test_smells` rodou. O id é `tests:<file>:<line>:<rule>`.
14. `## New dependencies`, só quando o gate de supply mediu.
15. `## Types`, só quando o gate de typing foi pedido.
16. `## Secrets`, só quando o gate de secrets mediu. O target é `secret:<rule>:<file>:<line>`. A linha `Outside the diff; does not block.` introduz achados que não mudam o exit.
17. `## Cognitive complexity`, só quando `cognitive` foi pedido, inclusive `not_run`.
18. `## Dead code`, só quando `dead_code` foi pedido, inclusive `not_run`.
19. `## Security`, só quando `security` rodou, inclusive `not_run`. A disposition no Markdown é traduzida. O JSON mantém `fail`, `warn`, `waived` e `off_diff`.
20. `## Churn`, sempre, inclusive numa falha precoce e quando a contagem não pode ser lida. A janela é `churn.window_days` dias terminando na data do commit. Diffusion é quantos arquivos incluídos mudaram e em quantos diretórios pai eles estão. O churn relativo é linhas alteradas divididas pela contagem de linhas do arquivo, mostrado com 4 casas decimais, ou `n/a` quando o arquivo não tem linhas ou não pode ser lido. O hotspot de uma função alterada é a contagem de commits vezes a complexidade ciclomática dela. A seção não muda o código de saída. Quando a contagem não pode ser lida, o título permanece e os números não.
21. `## How to reproduce`. O comando, numa cerca, inclusive o `--lang` que produziu o arquivo.

Seções vazias de dívida e de mutação são omitidas. Foco, o top 5, clones, o veredito e o churn estão presentes mesmo vazios. Um churn de fato vazio diz que não há arquivo incluído. Churn indisponível não mostra um zero.

A spec descreve uma ordem que começa pelo cabeçalho e pelo veredito, e coloca os waivers ao lado dos mutantes. O código coloca `## Waivers` antes do cabeçalho quando a seção existe. Esta página documenta o código.

## O comentário do pull request

A Action cria ou atualiza um comentário com o Markdown num pull request. O limite do corpo é `GITHUB_BODY_LIMIT = 65536` em `.github/actions/bob/upsert_comment.py`. Acima disso, o comentário é truncado e a nota usa o idioma de saída resolvido. Ver [CI](ci.md).

## Quando não há arquivo de relatório

- `bob doctor` imprime no stdout. Ele não grava `.bob/report.md`.
- `bob waive` só edita `.bob/waivers.yaml`.
- Configuração inválida recusada em `cli.main` antes de `run_check` não grava relatório. Uso inválido da linha de comando não grava relatório. Um arquivo `--config` ausente em `check`, `crap`, `dry`, `deps` ou `mutate` não grava relatório. Ver [Saída 4](../exit-codes.md#saída-4).
- Uma ferramenta ausente durante a medição grava o relatório, com o gate quebrado em `not_run`.
