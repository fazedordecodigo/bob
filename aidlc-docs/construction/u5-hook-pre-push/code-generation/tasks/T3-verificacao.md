# Verificação: ET-u5-hook-pre-push-T3 (v1) × PR #202
Verificada em 22/10/2026 19:03 (UTC-3) contra `T3.md` (v1, base fixada em `main` @ `144b997`). Só leituras remotas, sem clone nem fetch: API pública do GitHub por curl (PR, arquivos, commits, comentários e árvores git do head e da base), `raw.githubusercontent.com` (os 3 arquivos, `pyproject.toml` e `messages.py` no head e na base) e cursor-github (check runs e logs dos jobs). Esperei os checks terminarem: o último fechou às 18:55 (UTC-3).

PR: https://github.com/fazedordecodigo/bob/pull/202 | branch `aidlc/u5-hook-pre-push/t3-verify-install` → `main` | head `03e39e5452351bab1b84ffb96abca289fbf81bcd` | base `144b997079375d78a97530aaa10b506d89d42ab1` | aberto, pronto para revisão (`draft: false`), não mergeado, `mergeable: true` | 1 commit, +308/−11, 3 arquivos.
Commit: `03e39e5` (22/10 18:34 UTC-3, pai `144b997`) "Harness: passos 6 e 12 e hook nos passos 7 e 8"; PR aberto em 22/10 18:34 (UTC-3). Agente: `bc-161623bf-36a4-55d2-8be4-a81c0bf19d43`.

## Veredito: Aprovado para checkpoint
Os critérios de aceite, R1–R9 e os 7 testes (8 casos) atendem. Os 6 checks obrigatórios do head estão verdes. O job `verify-install / linux-x64` mostra as 11 linhas `ok`, com os passos 6 e 12. Nenhum desvio. 0 rodadas de correção. Uma diferença de forma no corpo está nas Observações e não reprova. O merge é do Emerson.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u5-hook-pre-push-T3: Harness: passos 6 e 12 e hook nos passos 7 e 8`; `aidlc/u5-hook-pre-push/t3-verify-install` → `main`; `base.sha` = `144b997…` (a da ET); pai do commit = `144b997` | Atende |
| Fora de rascunho; não mergeado pelo agente | `draft: false`, `state: open`, `merged: false`, `merged_by: null`; Bloqueios "Nenhum." | Atende |
| Passo 0 colado e igual | corpo, "Passo 0", base `144b997…`, bloco da ET colado sem mudança: `PIN:pytest==9.1.1`, `BASE:0`, `SETUP:0`, `# managed-by: bob-quality`, push `3297675..65cfee8`, `PUSH:0`, `# bob report`, `` - ✅ `crap`: passed ``, `` - ⏭️ `dry`: not run (Node missing: …) ``, `` - ✅ `deps`: passed ``, `7 passed in 8.70s`, `EXIT:0` | Atende |
| Exatamente 3 arquivos; script `100755` | `pulls/202/files`: `CHANGELOG.md` +9/−0, `scripts/verify-install.sh` +154/−3, `tests/test_verify_install.py` +145/−8. Árvore git do head e da base: `scripts/verify-install.sh` modo `100755` nos dois. Nenhum proibido (`install.sh`, `.github/workflows/`, `src/`, `tests/test_hook.py`, `pyproject.toml`, `docs/**`, `website/**`); `pyproject.toml` idêntico na base e no head | Atende |
| R1 linha 2, `STEP_IDS` e ajuda | l.2 `# Harness do comando de verificação (CT15): passos 1, 2, 3, 4, 5, 6, 7, 8, 9a, 9b e 12.`; l.4 `STEP_IDS='1 2 3 4 5 6 7 8 9a 9b 12'`; `parse_args` (com o `--help`) igual à base (script na box); `_HELP` dos testes com `passos: 1 2 3 4 5 6 7 8 9a 9b 12` | Atende |
| R2 `run_selected` | `      3\|4\|5\|6\|7\|12) ensure_2 ;;`; `      6) step_6 ;;` entre `5)` e `7)`; `      12) step_12 ;;` depois de `9b)` | Atende |
| R3 `expected_hook` | logo depois de `step_5`, antes de `step_6`/`step_7`; `printf '%s\n'` com os 8 argumentos da ET. Na box, a função extraída e rodada com `sh` dá bytes iguais ao template do CT10 para `/h/.local/share/bob-quality/bin/bob` e `/opt/bob home/bin/bob` | Atende |
| R4 `step_6` | logo depois de `expected_hook`. (a) `mkdir`, `new_project`, `git init -q --bare`, subshell com `remote add` e `push -q`, cada um com `\|\| exit 1` → "não consegui criar o projeto". (b) `release_pair` + `run_oneliner 6 …` com os 8 argumentos; "saiu $_rc; veja …"; última linha ≠ `  bob doctor: 0`. (c) "falta o hook"; `expected_hook "$S2_HOME/…/bin/bob" > expected.hook`; `cmp -s` → "o hook difere: $_diff" (`first_diff`); modo ≠ `-rwxr-xr-x`. (d) commit `feature` → "não consegui criar o commit". (e) `env -i "HOME=$S2_HOME" PATH=/usr/bin:/bin git push origin HEAD:main` em `push.log`, "o push saiu $_rc; veja …". (f) "o remoto não recebeu o commit". (g) falta `.bob/report.md`; 1ª linha ≠ `# bob report`; `grep -F` de `` `crap`: ``, `` `dry`: ``, `` `deps`: `` com as 3 mensagens. (h) `tempo %s s` e `ok 6` | Atende |
| R5 `step_7` | depois de `_gl_before=…`: `_hook=$S2_PROJ/.git/hooks/pre-push`, "falta o hook", `_hook_before=$(file_mtime "$_hook")`; depois do `fi` do `digest` e antes do `grep` do `bob.yaml`: mtime ≠ → "o hook foi regravado". Nenhum outro hunk no passo | Atende |
| R6 `step_8` | no subshell, depois do `printf` de `.bob/waivers.yaml` e antes do `git add -A`: `printf '%s\n' '#!/bin/sh' '# hook do dev' 'exit 0' > .git/hooks/pre-push \|\| exit 1` (quebrado com `\`) e `chmod 0755 … \|\| exit 1`; `  _files="$_files .git/hooks/pre-push"` como 3ª linha de `_files`; `grep -Fx '  preserved: .git/hooks/pre-push (pre-push hook without the bob marker)'` → "o resumo não lista o hook pre-push"; as 3 linhas `_warn` exatas (1 vez cada no script; 91, 79 e 45 colunas) e `grep -Fx "$_warn"` → "falta o aviso do hook pre-push"; tudo antes de `_last` | Atende |
| R6 aviso montado = mensagem da T2 | na box: as 3 linhas `_warn` rodadas com `T=/t` em `sh` dão exatamente `t("en", "setup.warning_line", step="hook", text=t("en", "setup.warn_hook_foreign", path=".git/hooks/pre-push", bob="/t/s8/home/.local/share/bob-quality/bin/bob"))` do `messages.py` do head; a linha `preserved:` aparece 1 vez no script | Atende |
| R7 `pytest_pin` | logo depois de `step_9b`; `sed -n 's/^    "\(pytest==[^"]*\)",$/\1/p' pyproject.toml`. Na box, contra o `pyproject.toml` do head, imprime `pytest==9.1.1` | Atende |
| R8 `step_12` | logo depois de `pytest_pin`. (a) `_venv=$S2_HOME/.local/share/bob-quality/current/venv`, `-x "$_venv/bin/python"` → "falta o venv do bob"; pin vazio → "não achei o pin…". (b) `mkdir -p "$T/s12/tmp"`; `"$_venv/bin/python" -m pip install -q "$_pin"` sem `env -i`, em `pip.log` → "pip install $_pin falhou; veja …". (c) `env -i "HOME=$S2_HOME" "TMPDIR=$T/s12/tmp" LANG=C.UTF-8 "PATH=$_venv/bin:$(tool_path)" "$_venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_hook.py` em `pytest.log`; "saiu $_rc"; `grep -F '7 passed'` → "não rodou os 7 testes". (d) `tempo %s s` e `ok 12`. Roda na raiz porque `main` exige `scripts/install.sh` no diretório atual | Atende |
| R9 passos intactos, POSIX, colunas | script na box: `step_1`–`step_5`, `step_9a`, `step_9b`, `ensure_2`, `parse_args`, `new_project`, `run_oneliner`, `release_pair`, `file_mtime`, `digest`, `main`, `die_passo` e `ok` iguais à base. `sh -n` e `dash -n` do script do head passam na box. Nenhum `local`, `[[`, `$'…'` ou `echo -e` nas linhas novas | Atende |
| Linhas novas ≤ 100 colunas | script sobre os `patch` de `pulls/202/files`, `len` do Python: maior linha adicionada = 98 com o `+` | Atende |
| 7 testes com nome exato e 8 casos | script: os 7 `def test_` novos batem com a ET, na ordem, logo depois de `test_step_5_runs_bob_check_with_the_u4_gates`; `test_harness_expects_the_ct10_text` com 2 casos (`/h/…/bin/bob`, `/opt/bob home/bin/bob`). CI: `tests/test_verify_install.py` com 29 casos; `collected 4605` = 4597 da `main` + 8. Nenhum `skip`, `xfail`, `only`, `noqa`, `pragma` ou assert comentado | Atende |
| Conteúdo dos testes | 1 (4 linhas em `splitlines()`); 2 (`re.search` da ET, `sh -c` com `"_", p`, exit 0 e bytes = `render_hook(Path(p))`); 3 (as 5 strings); 4 (contagens 1 e 2); 5 (linha `preserved` 1 vez, 3 linhas `_warn` e `_files` em `splitlines()`, `sh -c "T=/t\n…"` = mensagem); 6 (3 linhas + 2 strings); 7 (`pytest_pin` com `cwd=ROOT`, pin em `tomllib.loads(...)["project"]["optional-dependencies"]["dev"]` e começa com `pytest==`). Imports: `from bob_quality.hook_install import render_hook` antes de `bob_quality.init_config`; `tomllib` com reserva `tomli` | Atende |
| Só os ajustes da lista fechada | `_HELP` (`passos: … 6 … 12`); renomeação para `test_step_ids_are_the_u1_u3_u4_and_u5_steps` com `"1 2 3 4 5 6 7 8 9a 9b 12"`; `test_step_5_is_wired` com `3\|4\|5\|6\|7\|12`; `test_usage_errors_exit_1_before_preparing`: 1º parâmetro `("--only", "10")` / `passo desconhecido 10.` e `Passos: 1 2 3 4 5 6 7 8 9a 9b 12.` nos dois primeiros. Nenhum outro hunk em teste existente; o único nome removido é o renomeado | Atende |
| `CHANGELOG.md` | 2 parágrafos no topo de `## Unreleased`, acima da entrada da T2 (`` `bob setup` installs the pre-push hook… ``); en e depois pt-BR, cada um seguido de linha vazia; unidos por espaço, iguais palavra por palavra (em bytes) ao texto da ET; linhas com 97/96/87 e 82/93/93/16 colunas; quebras só em espaço | Atende |
| `--only 6,7,8,12` com 5 `ok` e 2 tempos | corpo: exit 0, 112 s; `passo 2: ok`, `passo 6: tempo 1 s`, `passo 6: ok`, `passo 7: ok`, `passo 8: ok`, `passo 12: tempo 9 s`, `passo 12: ok` | Atende |
| Harness inteiro: exit 0, 11 `ok`, ≤ 900 s | corpo: exit 0, 159 s, 11 linhas `ok`. CI (`verify-install / linux-x64`): 11 linhas `ok` (1, 2, 3, 4, 5, 6, 7, 8, 9a, 9b, 12), harness de 18:35:05 a 18:38:57 (UTC-3), cerca de 232 s | Atende |
| Job `verify-install` mostra os passos 6 e 12 | log do job: `verify-install: passo 6: tempo 1 s` / `passo 6: ok` (18:36:27); `passo 7: tempo 1 s` / `passo 7: ok`; `passo 8: ok` (18:37:36); `passo 12: tempo 14 s` / `passo 12: ok` (18:38:57). Alvos U5-N11 (push ≤ 60 s) e U5-N12 (passo 12 ≤ 240 s) atendidos | Atende |
| Suíte inteira 0 failed, 0 errors | CI: `4605 passed, 3 warnings` em 3.10 (1120.57 s) e 3.12 (761.96 s); os 3 warnings são o aviso já existente de `verify_requirements`. Corpo: `4605 passed` local; `29 passed` em `test_verify_install.py` | Atende |
| `bob check` 5 gates → 0 | corpo: exit 0, os 5 gates ✅, nenhum sobrevivente, nenhum `no_coverage`, nenhum waiver novo. Comentário do `bob` (CI, commit `03e39e5`, 18:46 UTC-3): crap/dry/deps/mutate ✅, "No changed file with CRAP risk", "No surviving mutants", "No mutants without tests", sem violação de dependência, sem clone novo; os 16 waivers são de 2026-10-11 (nenhum novo) | Atende |
| 6 checks verdes no head | tabela abaixo | Atende |
| Corpo do PR | Resumo, Passo 0 (bloco e saída), Arquivos, Testes (7 nomes e ajustes), Comandos (cada um com a saída, tempos dos passos 6 e 12 e do harness), Decisões tomadas (nenhuma), `## Bloqueios` "Nenhum."; Referências: U5, CT15, CT10, verification-command passos 6, 7, 8 e 12, US4.1, FR5.1, FR5.2, FR5.3, NFR4, NFR5, NFR8 | Atende (ver Observações) |

## Checks no head `03e39e5` (início 22/10 18:34 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| bob / check | bob, run 39858419648 | success | 11m55s |
| bob / cold | bob, run 39858419648 | success | 1m21s |
| CI / pytest (3.10) | CI, run 39858419565 | success, `4605 passed, 3 warnings` | 20m06s |
| CI / pytest (3.12) | CI, run 39858419565 | success, `4605 passed, 3 warnings` | 13m40s |
| package / dist | package, run 39858419586 | success | 1m24s |
| verify-install / linux-x64 | verify-install, run 39858419716 | success, 11 linhas `ok`; passo 6 em 1 s, passo 12 em 14 s | 4m10s |
| website / build | — | não se aplica (o PR não toca `docs/` nem `website/`) | — |
| pages / deploy | — | não exigido | — |

## Observações (não reprovam)
- Corpo: as Decisões vêm como `## Decisões tomadas` com "nenhuma" na linha de baixo, não como o título `## Decisões tomadas: nenhuma` das T1 e T2. O conteúdo é o pedido: nenhuma decisão. Não reprovo por isso.
- O `bob / check` levou 11m55s, metade das T1 e T2 (20–24 min). O diff não toca `src/`, então o `mutate` não tem mutante novo, como a ET previa ("Literais e mutantes").
- O passo 12 levou 14 s no CI e 8–9 s na máquina do agente. O harness inteiro levou cerca de 232 s no CI e 159 s no corpo. Tudo abaixo dos alvos (240 s e 900 s).
- O passo 0 e as corridas do agente usaram o Node v22.23.4 no início do `PATH`, porque o `node` padrão da imagem do agente não tem `npm` ao lado. É o mesmo ambiente da T2.
- No passo 0, o `dry` sai ⏭️ `not run` no push, como a ET aceita (push sem Node no `PATH`; ver I43).
- `--format both` aparece no comando de `bob check` do corpo, além do que a ET pede. Não muda os gates nem o exit.
- O corpo cita `32 subtests passed` na corrida local; o CI não mostra subtests. A contagem de casos (4605) é a mesma.
- Na primeira consulta, `mergeable_state` era `unstable`, com checks ainda rodando.

## Registro
- 22/10/2026 19:03 (UTC-3): rodada 1 (head `03e39e5`): aprovado para checkpoint, sem desvios. `traceability.json` (U5 T3 `verified`, PR 202 `open`) e `trace.md` da U5 atualizados. Status da unit sem mudança. O merge é do Emerson.
