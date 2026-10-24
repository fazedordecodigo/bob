# Hook pre-push gerenciado

Status: aceita pelo Emerson em 18/10/2026, na aprovação do desenho da aplicação. Publicada em `docs/adr/` na U9.

## Contexto

FR5.1–FR5.3. Hoje é `cp` manual e o hook chama `bob` pelo `PATH`.

## Decisão

- Destino: `$(git rev-parse --git-path hooks)/pre-push`.
- `git config --get core.hooksPath` definido: não escreve. Aviso com a linha a pôr no gerenciador de hooks do projeto. Conta como "hook preservado".
- Arquivo existente sem a linha `# managed-by: bob-quality`: preservado, com aviso (FR5.3).
- Arquivo com a linha: reescrito só se o conteúdo difere.
- Template:
  ```sh
  #!/bin/sh
  # managed-by: bob-quality
  set -e
  unset PYTEST_ADDOPTS
  unset PYTEST_PLUGINS
  BOB="<BOB_HOME absoluto>/bin/bob"
  [ -x "$BOB" ] || BOB=bob
  exec "$BOB" check --gates crap,dry,deps </dev/null
  ```
- O caminho é o launcher estável (ADR 0013). Atualizar não muda o hook.

## Alternativas

`core.hooksPath` próprio (muda config do repo e quebra outros hooks); hook versionado no projeto (exige editar arquivos do dev).

## Consequências

O hook do bob roda o mesmo comando de hoje. O alvo de NFR8 (< 60 s, `tests/test_hook.py`) segue válido.

## Complemento (U5, 3.5, 2026-10-22, UTC-3)

Refinamento compatível, decidido pelo Arquiteto no plano da U5 (`construction/u5-hook-pre-push/code-generation/code-generation-plan.md`, D1–D9); nada acima muda.
- Ordem: confere o caminho → `git config --get core.hooksPath` (saída `0` preserva; `1` segue; outra é erro de ferramenta) → `git rev-parse --git-path hooks` → decide → grava.
- Caminho do launcher: absoluto e sem `"`, `$`, `` ` ``, `\` ou quebra de linha (o que o `sh` não lê literal entre aspas duplas). Senão, o passo `hook` falha com saída `4` e nada é gravado.
- Link (mesmo para um hook do bob) e pasta no lugar de `pre-push`: preservados sem leitura, com aviso (ADR 0017).
- "Difere" inclui o modo: hook do bob com os mesmos bytes e modo ≠ `0755` é regravado.
- Gravação por `pre-push.tmp-<pid>` na mesma pasta + `os.replace`; o temporário é apagado em qualquer falha.
- Hook preservado e `core.hooksPath` aparecem na linha `preservado:` **e** como aviso com a linha a acrescentar (FR5.3).
- O hook estático `src/bob_quality/hooks/pre-push` fica (caminho manual dos docs, que a U8 atualiza); um teste prende o comando dele ao do template.
