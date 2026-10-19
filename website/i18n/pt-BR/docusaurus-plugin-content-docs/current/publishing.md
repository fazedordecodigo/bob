# Publicação do plugin do Cursor

[Índice](README.md) · [Agentes](getting-started/agents.md) · [SPEC](SPEC.md)

O job `cursor` em [`.github/workflows/publish-plugins.yml`](https://github.com/fazedordecodigo/bob/blob/main/.github/workflows/publish-plugins.yml) confere a árvore do plugin. A listagem no marketplace continua manual. O Emerson envia o repositório em [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish).

A história 19, o critério de aceitação 12 e a linha de fora de escopo em [SPEC.md](SPEC.md) deixam a publicação em marketplace para a aprovação dele.

## Conferir a árvore

Na raiz do clone, com o extra `dev` instalado:

```bash
python scripts/validate_cursor_plugin.py --root . --tag v0.1.0
```

Uma lista vazia e exit `0` significam que o manifesto, a versão e o checklist batem com a tag. Uma lista JSON e exit `1` nomeiam cada falha. Exit `2` é uso inválido, e a mensagem está no stderr.

Cada objeto dessa lista tem `code`, `subject` e `message`. O código `uri` vale para `homepage` e `repository` quando o campo está presente. O valor tem de ser um URI `http` ou `https` com host. O script recusa espaço no começo ou no fim, host em branco ou só com espaço (`http:// /x`, `https://%20/`), porta fora de 0–65535 (por exemplo `99999`, que não derruba o processo) e credencial na URL (`user:secret@`). A mensagem diz que o campo tem de ser um URI http ou https com host. Os dois campos falham de forma independente.

O script lê `scripts/cursor_plugin.schema.json`. Esse arquivo é uma cópia byte a byte de [`schemas/plugin.schema.json`](https://github.com/cursor/plugins/blob/5229aad76c37451561c5b81a9b5072ae1c549a5b/schemas/plugin.schema.json) no commit `5229aad76c37451561c5b81a9b5072ae1c549a5b` de `cursor/plugins`. O teste `test_schema_bytes_match_the_pinned_cursor_plugins_commit` trava o SHA-256.

## O que uma tag dispara

O workflow roda em três casos.

- Um push de uma tag `v*`.
- Um release do tipo `published`.
- `workflow_dispatch`, com o input booleano `dry_run`. O padrão é `true`.

O job instala o extra `dev` e roda o mesmo script. Numa tag ou num release ele passa `--tag` com o nome da tag. Num dispatch a partir de um branch ele omite `--tag` e compara só `.cursor-plugin/plugin.json` com `[project].version` em `pyproject.toml`.

O log imprime `dry_run=`. Os dois valores percorrem os mesmos passos. O job não envia o plugin a lugar nenhum.

`permissions` é `contents: read`. O arquivo não referencia `secrets`. Não há segredo a criar para esta fase.

O passo de checkout define `persist-credentials: false`. O token usado para clonar não fica nas credenciais de git do job depois desse passo.

Um job para outra plataforma é um irmão de `cursor`, nos mesmos `jobs`.

## Enviar a primeira listagem

Abra [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish) com a conta do Emerson. O envio pede o repositório público `https://github.com/fazedordecodigo/bob`.

A página [Plugins reference](https://cursor.com/docs/reference/plugins) lista o que o review confere. Neste repositório cada item aponta para um arquivo.

- Manifesto `.cursor-plugin/plugin.json`, nome `bob`.
- `description` no mesmo arquivo.
- Skills `./skills/bob-check`, `./skills/harden` e `./skills/review-report`, cada uma com `name` e `description` no frontmatter.
- O logo versionado `assets/logo.svg`, campo `logo` com esse caminho relativo.
- `README.md`, seção `Usage`, com `bob check` e `bob.yaml`.
- Caminhos do manifesto que são relativos, sem `..`.

O formulário em si não devolveu os rótulos dos campos na sessão que escreveu esta página. O que a página pública pede é o link do repositório. Confira a tela autenticada para qualquer texto adicional que ela peça.

## Depois da listagem

A página [Marketplace security](https://cursor.com/help/security-and-privacy/marketplace-security) responde "Are plugin updates reviewed?" com esta frase: "Plugins in the marketplace are not automatically updated from source code." Cada atualização passa por review manual.

Uma tag `v*` coloca o manifesto, `pyproject.toml` e a tag na mesma versão. O marketplace público recebe essa versão só depois do review da Cursor. A tag não substitui o formulário nem uma nova rodada de review.

A decisão que fica com o Emerson é aceitar esse review manual para cada versão. A documentação usada acima não descreve uma API de publicação.

O nome do plugin permanece `bob`. A issue #145 já registra que esse nome pode colidir no review.

## Carregar no Cursor local

A cópia em `~/.cursor/plugins/local/bob` tem de ser um diretório real. O Cursor ignora um symlink cujo alvo está fora dessa pasta. Fonte: [Test plugins locally](https://cursor.com/docs/plugins).

```bash
rm -rf ~/.cursor/plugins/local/bob
mkdir -p ~/.cursor/plugins/local/bob
git archive HEAD | tar -x -C ~/.cursor/plugins/local/bob
test ! -L ~/.cursor/plugins/local/bob
test -f ~/.cursor/plugins/local/bob/.cursor-plugin/plugin.json
test -f ~/.cursor/plugins/local/bob/assets/logo.svg
test -f ~/.cursor/plugins/local/bob/skills/bob-check/SKILL.md
```

Depois rode **Developer: Reload Window** e abra Customize. Este checkout não abre a IDE, então esse reload é para uma pessoa com o Cursor aberto.
