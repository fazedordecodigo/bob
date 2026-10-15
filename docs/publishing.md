# Publicar o plugin bob no Cursor

O job `cursor` em [`.github/workflows/publish-plugins.yml`](../.github/workflows/publish-plugins.yml) confere a árvore do plugin. A listagem no marketplace continua manual. O Emerson envia o repositório em [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish).

A história 19, o critério 12 e a linha de fora de escopo em [SPEC.md](SPEC.md) deixam a publicação no marketplace para o OK dele.

## Conferir a árvore

Na raiz do clone, com o extra `dev` instalado:

```bash
python scripts/validate_cursor_plugin.py --root . --tag v0.1.0
```

Uma lista vazia e o exit `0` significam que o manifesto, a versão e o checklist batem com a tag. Uma lista JSON e o exit `1` nomeiam cada falha. O exit `2` é uso inválido, e a mensagem fica no stderr.

O script lê `scripts/cursor_plugin.schema.json`. Esse arquivo é a cópia byte a byte de [`schemas/plugin.schema.json`](https://github.com/cursor/plugins/blob/5229aad76c37451561c5b81a9b5072ae1c549a5b/schemas/plugin.schema.json) no commit `5229aad76c37451561c5b81a9b5072ae1c549a5b` do repositório `cursor/plugins`. O teste `test_schema_bytes_match_the_pinned_cursor_plugins_commit` trava o SHA-256.

## O que a tag dispara

O workflow dispara em três casos.

- Push de uma tag `v*`.
- Release do tipo `published`.
- `workflow_dispatch`, com o input booleano `dry_run`. O padrão é `true`.

O job instala o extra `dev` e roda o mesmo script. Em tag ou release, ele passa `--tag` com o nome da tag. Num dispatch a partir de um branch, ele omite `--tag` e compara só `.cursor-plugin/plugin.json` com `[project].version` no `pyproject.toml`.

O log imprime `dry_run=`. Os dois valores percorrem os mesmos passos. O job não envia o plugin a lugar nenhum.

`permissions` é `contents: read`. O arquivo não referencia `secrets`. Não há segredo para criar nesta fase.

Um job de outra plataforma entra como irmão de `cursor`, no mesmo `jobs`.

## Enviar a primeira listagem

Abra [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish) com a conta do Emerson. O envio pede o repositório público `https://github.com/fazedordecodigo/bob`.

A página [Plugins reference](https://cursor.com/docs/reference/plugins) lista o que a revisão confere. Neste repositório cada item aponta para um arquivo.

- Manifesto `.cursor-plugin/plugin.json`, nome `bob`.
- `description` no mesmo arquivo.
- Skills `./skills/bob-check`, `./skills/harden` e `./skills/review-report`, cada uma com `name` e `description` no frontmatter.
- Logo commitado em `assets/logo.svg`, campo `logo` com esse caminho relativo.
- `README.md`, seção `Usage`, com `bob check` e `bob.yaml`.
- Caminhos do manifesto relativos, sem `..`.

O formulário em si não devolveu os rótulos dos campos nesta sessão. O que a página pública pede é o link do repositório. Confira na tela logada se ela pede mais algum texto.

## Depois da listagem

A página [Marketplace security](https://cursor.com/help/security-and-privacy/marketplace-security) responde "Are plugin updates reviewed?" com esta frase: "Plugins in the marketplace are not automatically updated from source code." Cada atualização passa por revisão manual.

Uma tag `v*` deixa o manifesto, o `pyproject.toml` e a tag na mesma versão. O marketplace público só recebe essa versão depois da revisão do Cursor. A tag não substitui o formulário nem uma nova rodada de revisão.

A decisão que fica com o Emerson é aceitar essa revisão manual a cada versão. A documentação usada acima não descreve uma API de publicação.

O nome do plugin continua `bob`. A issue #145 já registra que esse nome pode colidir na revisão.

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

Depois, rode **Developer: Reload Window** e abra Customize. Este checkout não abre o IDE, então esse reload fica para uma pessoa com o Cursor aberto.
