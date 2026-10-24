# Passo `perfil` do `install.sh`: forma da escrita, do aviso e da passagem do resultado

Status: aceita pelo Emerson em 22/10/2026, no Plan Approval da U6, da U7 e da U8. Publicada em `docs/adr/` na U9.

## Decisão

- `PROFILE_LINE` é a 2ª fonte única do topo (linha 5, logo depois de `STEPS`). A marca (`# managed-by: bob-quality`) e a linha para colar (`export PATH="$HOME/.local/bin:$PATH"`) saem dela por expansão (`"#${PROFILE_LINE#* #}"` e `${PROFILE_LINE%% #*}`). O literal da marca não se repete no script.
- O aviso de falha vai para o stdout (como o `launcher_warning`), em en e pt-BR. O `<erro>` do CT16 é o texto depois do último `": "` da 1ª linha do stderr do shell ao abrir ou criar o arquivo. Exemplos: `Permission denied` (dash e bash) e `Directory nonexistent` (dash). Sem texto, vira `unknown error` / `erro desconhecido`, como no `launcher_try`.
- Falha ao criar, ao fazer `chmod 0644` ou ao acrescentar: todas dão `failed:<arquivo>`. O passo nunca chama `fail` e sempre imprime `install: perfil: ok`.
- O resultado vai para o filho por `export BOB_INSTALL_PROFILE="$profile_result"` e depois `exec "$bob_root/bin/bob" setup --lang "$bob_lang" </dev/null`. Não usa `exec env …`: o efeito é o mesmo e não traz o binário `env` para a lista de ferramentas.
- `tail` e `chmod` entram na lista de utilitários usados (POSIX base). O passo `ferramentas` não os confere, como não confere `mkdir`, `ln` e `awk`.

## Consequências

O CT2 ganha um esclarecimento compatível na linha `setup`. Root escreve em arquivo só leitura, então o caso (e) do passo 13 não reproduz como root. O harness recusa rodar como root no passo 13 (ADR 0026).
