# U6 — u6-perfil-shell — Desenho funcional (3.1, Minimal)

Kind: packaging | Base: `main` @ `22d461a60920ab13e7b09fd654fd0e4686ba14d0` | Data: 2026-10-22 (UTC-3)
Contratos: CT2 (passo `perfil`), CT3 (linha do resumo), CT6 (`BOB_INSTALL_PROFILE`), CT16, CT15 (passo 13). ADR 0013 (Q1 A do 2.6). Propostas: ADR 0021, 0022, 0023, 0026, 0027 (`../u6-u7-decisions-proposta.md`).
Perguntas: nenhuma. Todo comportamento visível sai do CT16, do CT3 e do passo 13. Os textos en são tradução dos pt aprovados.

## O que passa a existir
- Passo `perfil` no `install.sh`, entre `launcher` e `setup`. Nunca falha.
- `BOB_INSTALL_PROFILE` passado ao `bob setup`, e a linha `perfil do shell:` / `shell profile:` no resumo.
- Passo 13 do harness: 5 casos × 2 execuções.

## Estado atual do repo (conferido @ 22d461a)
- `scripts/install.sh` (480 linhas):
  - `STEPS` na linha 4, sem `perfil`; fontes únicas nas 4-11, sem `PROFILE_LINE`;
  - `say` nas 43-159 (pt 53-101, en 102-152; o `launcher_warning` vai para o stdout nas 154-158);
  - `step_launcher` nas 399-419; `step_setup` nas 421-426 (`exec "$bob_root/bin/bob" setup --lang "$bob_lang" </dev/null`, linha 424);
  - `_run_step` nas 428-443; `main` nas 445-478.
  - Nada lê `SHELL`, `ZDOTDIR` nem escreve perfil.
- `src/bob_quality/setup_cmd.py` (529 linhas): `_fail` nas 344-352; `_summary` nas 355-368 (linha do doctor na 368). Não lê `BOB_INSTALL_PROFILE`.
- `src/bob_quality/messages.py`: `setup.doctor_not_run` na 407 (en) e na 837 (pt-BR).
- `tests/test_install_sh.py` (1236 linhas, 64 casos):
  - `_ALLOWED` (33-53) sem `tail` nem `chmod`;
  - `_SOURCE_NAMES`/`_SOURCE`/`_CT2_STEPS` (54-89);
  - `_fake_wheel` (350-394) registra argv e stdin;
  - `_run` (508-539) sem `SHELL`.
- `tests/test_setup_cmd.py` (1665 linhas, 166 casos; `_MESSAGES` com 46 chaves, 73-258).
- `scripts/verify-install.sh` (1357 linhas): `run_oneliner` (357-399) não passa `SHELL` nem `BOB_HOME`.

## Regras de negócio
| # | Regra | Fonte |
|---|---|---|
| P1 | Roda só se `:$PATH:` não contém `:$HOME/.local/bin:`. Senão `already-on-path`, nada escrito. | CT16 |
| P2 | Arquivo por `${SHELL##*/}`: `zsh` → `${ZDOTDIR:-$HOME}/.zshrc`; `bash` → `$HOME/.bashrc`; outro ou vazio (inclusive `SHELL` ausente) → `$HOME/.profile`. | CT16, CT6 |
| P3 | Linha exata: `export PATH="$HOME/.local/bin:$PATH" # managed-by: bob-quality` (`PROFILE_LINE`). | CT16, CT5, CT18 |
| P4 | Arquivo regular (ou symlink para um) que já tem `# managed-by: bob-quality` → `already-marked:<arquivo>`, nada escrito. | CT16, ADR 0021 |
| P5 | Arquivo não existe → cria só com a linha + `\n`, modo `0644` → `<arquivo>`. | CT16 |
| P6 | Arquivo existe → acrescenta no fim, com `\n` antes se o último byte não é `\n`. Bytes anteriores iguais → `<arquivo>`. Symlink: escreve no destino (o `>>` segue o link). | CT16 |
| P7 | Falha ao criar, ao fazer `chmod` ou ao acrescentar → `failed:<arquivo>` e aviso no stdout (texto abaixo). O passo segue e imprime `install: perfil: ok`; o código de saída não muda. | CT16, ADR 0022 |
| P8 | O resultado vai para o `bob setup` em `BOB_INSTALL_PROFILE` (`export` antes do `exec`). | CT2, ADR 0022 |
| P9 | O `bob setup` imprime `  perfil do shell: <texto>` antes de `  bob doctor:`, também no resumo parcial. Valor fora dos 4 formatos → sem linha. | CT3, ADR 0023 |
| P10 | 2ª execução do comando único: `already-marked:<arquivo>` (ou `already-on-path`), 0 bytes mudam no perfil. | NFR4, passo 13 |

## Mensagens
`install.sh` (`say profile_warning <arquivo> <erro>`, no stdout):
- pt-BR: `install: perfil: aviso: não consegui gravar <arquivo> (<erro>). Para usar o comando bob, acrescente ao seu perfil: export PATH="$HOME/.local/bin:$PATH".`
- en: `install: perfil: warning: could not write <arquivo> (<erro>). To use the bob command, add to your profile: export PATH="$HOME/.local/bin:$PATH".`
- `<erro>`: o que vem depois do último `": "` da 1ª linha do stderr do shell. Sem texto: `erro desconhecido` / `unknown error`.

`messages.py` (chaves novas, depois de `setup.doctor_not_run`):
| Chave | en | pt-BR |
|---|---|---|
| `setup.profile` | `  shell profile: {text}` | `  perfil do shell: {text}` |
| `setup.profile_added` | `added ~/.local/bin to PATH in {path}. Open a new terminal or run: . {path}` | `acrescentei ~/.local/bin ao PATH em {path}. Abra um terminal novo ou rode: . {path}` |
| `setup.profile_on_path` | `~/.local/bin is already on PATH; nothing changed` | `~/.local/bin já está no PATH; nada mudou` |
| `setup.profile_marked` | `{path} already has the bob line; nothing changed` | `{path} já tem a linha do bob; nada mudou` |
| `setup.profile_failed` | `could not write {path}; see the warning above` | `não consegui gravar {path}; veja o aviso acima` |

## Mapa `BOB_INSTALL_PROFILE` → linha
| Valor | Linha (en) |
|---|---|
| `/h/.zshrc` | `  shell profile: added ~/.local/bin to PATH in /h/.zshrc. Open a new terminal or run: . /h/.zshrc` |
| `already-on-path` | `  shell profile: ~/.local/bin is already on PATH; nothing changed` |
| `already-marked:/h/.bashrc` | `  shell profile: /h/.bashrc already has the bob line; nothing changed` |
| `failed:/h/.profile` | `  shell profile: could not write /h/.profile; see the warning above` |
| ausente, `""`, `rel/.bashrc`, `already-marked`, `already-marked:`, `already-marked:rel`, `failed:`, `failed:rel`, `on-path` | nenhuma |

## Harness (CT15; passo 13)
- Cada caso tem `HOME` e projeto novos em `$T/s13/<caso>`, `BOB_HOME` do passo 2 (pacote reusado) e 2 execuções. O `PATH` é `tool_path`; no caso (d), `$HOME/.local/bin:` na frente.
- Casos:
  - (a) `SHELL=/bin/zsh`, sem `.zshrc`;
  - (b) `SHELL=/bin/bash`, `.bashrc` = `alias bob-antes=1`, sem `\n` no fim;
  - (c) `SHELL=/bin/sh`, sem `.profile`;
  - (d) `SHELL=/bin/bash`, com `~/.local/bin` no `PATH`;
  - (e) `SHELL=/bin/bash`, `.bashrc` = `# só leitura\n` em `0444`.
- Conferências:
  - Em (a)–(c):
    - conteúdo exato do arquivo;
    - modo `-rw-r--r--` quando criado;
    - `grep -c 'managed-by: bob-quality'` = 1;
    - resumo da 1ª execução com `_added` e da 2ª com `_marked`;
    - nenhum outro perfil criado;
    - `env -i HOME=… PATH=/usr/bin:/bin sh -c '. <arquivo>; command -v bob'` = `$HOME/.local/bin/bob`.
  - Em (d): nenhum dos 3 perfis existe; resumo `_onpath` nas 2 execuções.
  - Em (e): sai 0; sha igual; resumo `_failed` nas 2 execuções; 1ª execução com o aviso.
- Root → `die_passo 13`, porque (e) não reproduz como root.

## Códigos de saída
O passo `perfil` não muda código nenhum. O comando único continua com o código do `bob setup` (0 ou 4). O harness usa 0 e 1 (CT15).

## Fora do desenho
- O bloco `perfil` do prompt (U8, CT18; ganha `already-marked:$F`).
- Docs do perfil (U8).
- Remover a linha do perfil (não há desinstalação na v0.1.0).
