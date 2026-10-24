# Harness: passos 10, 11 e 13 e o passo 2 parcial

Status: aceita pelo Emerson em 22/10/2026, no Plan Approval da U6, da U7 e da U8. Publicada em `docs/adr/` na U9.

## Decisão

- **Dependências dentro do passo, não em `run_selected`.** O `step_13` chama `ensure_2` na 1ª linha. O `step_10` chama `ensure_8`, e o `step_11` chama `ensure_10`. A linha `3|4|5|6|7|12) ensure_2 ;;` não muda (uma linha a menos em comum entre a U6 e a U7).
- **Passo 13 (U6).**
  - 5 casos, cada um com `HOME` e projeto novos em `$T/s13/<a..e>`, 2 execuções do comando único.
  - `BOB_HOME` compartilhado com o do passo 2 (`$S2_HOME/.local/share/bob-quality`): o pacote é reusado e o passo fica em segundos.
  - `run_oneliner` ganha dois argumentos opcionais, `${10}` (`SHELL`) e `${11}` (`BOB_HOME`).
  - A checagem "bob já está no PATH" aceita só o `$HOME/.local/bin/bob` do próprio caso. Sem isso, o caso (d) não roda a 2ª vez. Nos outros passos o `PATH` nunca tem `~/.local/bin`, então nada muda neles.
  - Root → `die_passo 13`.
  - Alvo ≤ 180 s.
- **Passos 10 e 11 (U7).**
  - Subárvore própria do espelho, `$T/mirror/upd/` (como `bad/`):
    - `api/releases/latest` = `v<X.Y.Z+1>`;
    - `download/v<X>` e `download/v<X.Y.Z+1>`;
    - `latest/download/install.sh`;
    - pré-release `v99.1.0` (fora do `latest`, com `prerelease.json`) e rascunho `drafts/v99.1.1`.
  - O wheel novo é o wheel do build com a versão trocada (`rebrand_wheel`: renomeia o `dist-info`, troca `Version:` no `METADATA` e refaz o `RECORD`). Não dá para copiar `src/` e buildar de novo, por causa dos symlinks de `package.json`, `plugin/…` e outros.
  - O `bob update` roda no projeto e no `HOME` do passo 8, por `run_bob`, com `env -i` e a mesma lista de variáveis de proxy e índice do `run_oneliner` (cópia; a U8 T4 junta as duas em `pass_env`).
  - Conferências do passo 10:
    - o comando único num projeto novo, no mesmo `HOME`, instala a `latest` e não a pré-release (US7.2 crit. 1);
    - `bob --version`;
    - `.bob-version`;
    - `current`;
    - hashes;
    - linhas `preserved:`.
  - O passo 11 confere: 1 linha "já está…", 1 pedido (`api`), `digest` do projeto igual.
  - `VERIFY_REMOTE=1` → "não se aplica" nos dois.
  - Alvos: o `bob update` do passo 10 ≤ 300 s; o passo 11 ≤ 30 s.
- **Passo 2 parcial (U7).** Depois de `check_gitleaks_install 2`, só no modo espelho: `bob --version` no projeto do passo 2 = `bob $X` e `project skills: $X (.agents/skills)`.
- **Ids finais** (depois das duas units): `STEP_IDS='1 2 3 4 5 6 7 8 9a 9b 10 11 12 13'`.

## Consequências

O harness projetado fica em cerca de 232 + 150 (passos 10 e 11) + 60 (passo 13) ≈ 450 s no CI, abaixo de 900 s.
