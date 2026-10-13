# Relatórios

[Índice](README.md) · [CLI](cli.md) · [Gates](gates.md) · [Exit codes](exit-codes.md) · [SPEC](SPEC.md)

`bob check` e os comandos de um gate só gravam, por padrão, `.bob/report.md` e `.bob/report.json`. `--out` muda a pasta. `--format md`, `json` ou `both` (padrão `both`) escolhe o arquivo. `crap`, `dry`, `deps` e `mutate` gravam os dois, porque o `cli.py` chama `run_check` com `fmt="both"`.

O schema está em `src/bob_quality/schemas/report_v1.json`. `schema_version` é a constante `1`.

## Ordem do Markdown

`to_markdown` em `src/bob_quality/report.py` emite, no idioma da saída:

1. Título: `# Relatório bob` em `pt-BR`, `# bob report` em `en`.
2. `## Waivers`, só quando já há waivers ou a mutação rodou. Sem entradas, o texto é `Nenhum waiver.` A tabela tem alvo, motivo, autor e data. O título `## Waivers` é fixo nos dois idiomas (string literal em `_waiver_section`).
3. Cabeçalho: commit, base, data e versões das ferramentas. As linhas `Commit:` e `Base:` ficam em inglês no código (`_header`).
4. `## Veredito`: uma linha por gate, ✅ passou, ⚠️ aviso, ❌ falhou ou ⏭️ não executado. Com motivo, ele vai entre parênteses.
5. `## Onde focar o review`: arquivos alterados ordenados pelo maior CRAP, com clones e, se a mutação rodou, um acréscimo de risco para sobrevivente sem waiver (`focus_with_survivors` soma 100). Arquivo com clone ganha o sufixo `, clone`.
6. `## Top 5 funções por CRAP (diff)`: função, arquivo:linha, CC, cobertura em percentual inteiro, CRAP e delta. Delta ausente vira `—`.
7. `## Informação (dívida antiga)`, só se existir função fora do diff no limite ou acima. O item termina com `fora do diff; não bloqueia`.
8. `## Violações e ciclos de dependência`, e em seguida `## Informação (dependências fora do diff)` quando há violações fora do diff.
9. `## Clones novos`. Cada par traz arquivos, linhas, tokens e similaridade.
10. `## Mutantes sobreviventes`, só se a mutação rodou. Colunas: id, função, local, operador, waiver.
11. `## Mutantes sem teste`, só se o resumo de mutação traz `no_coverage`. Total, e tabela por função e arquivo. A linha do total diz que bloqueia.
12. `## Como reproduzir`: o comando, dentro de uma cerca, com `--lang` do idioma que gerou o arquivo.

Seções vazias de dívida e de mutação somem. Foco, top 5, clones e veredito aparecem mesmo vazios, com a frase de “nenhum”.

A [SPEC](SPEC.md) descreve a ordem começando pelo cabeçalho e pelo veredito, e coloca waivers junto dos mutantes. O código coloca `## Waivers` antes do cabeçalho quando a seção existe. O README em português lista essa ordem do código.

## report.json

Campos obrigatórios no schema: `schema_version`, `commit`, `base`, `generated_at`, `tool_versions`, `gates`, `focus`, `top_crap`, `reproduce`, `exit_code`. O render também escreve `old_debt`, `dependencies`, `old_dependencies`, `clones`, `waivers`, `survivors` e `mutation` quando `to_json` os inclui.

`gates[].status` é `passed`, `warn`, `failed` ou `not_run`. O `reason` no JSON é renderizado em inglês (`JSON_LANGUAGE`).

### O que não muda com o idioma

O arquivo JSON é o mesmo em `en` e `pt-BR`:

- todo `reason` de gate;
- o nome da regra de ciclo (`Forbidden dependency cycle`);
- `reproduce`, que não leva `--lang`.

O `report.md` e o comentário do pull request traduzem a regra de ciclo e o fallback sem nome do dependency-cruiser, e a linha de reprodução inclui `--lang`. Fonte: `report.py` e a decisão 12 da [SPEC](SPEC.md), repetida no [CHANGELOG.md](../CHANGELOG.md).

## Comentário no pull request

A Action (`.github/actions/bob/upsert_comment.py`) cria ou atualiza um único comentário com o Markdown, em pull request. O limite do corpo é `GITHUB_BODY_LIMIT = 65536`. Acima disso, o comentário é truncado e a nota usa o idioma do input `language` (ou `BOB_LANG` / `bob.yaml` / `en`). O exit code do job é o do bob (`propagate_exit.sh`).

O artefato `bob-mutation-cache` sobe com `.bob/mutation-cache.json` mesmo quando o check falha (`if: always()` na action). O GitHub guarda esse artefato por 7 dias (`retention-days: 7`).

## Onde o relatório não aparece

- `bob doctor` imprime no stdout.
- `bob waive` só mexe em `.bob/waivers.yaml`.
- Configuração inválida barrada em `cli.main` antes do `run_check` não grava relatório. Isso inclui `duplication` inválida e chave desconhecida. Um uso inválido da linha de comando também não grava relatório. Um `--config` inexistente em `check`, `crap`, `dry`, `deps` ou `mutate` grava o relatório de falha precoce. Ver [Exit 4](exit-codes.md#exit-4).
