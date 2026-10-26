# Verificação: ET-u4-bob-yaml-T3 (v2) × PR #198
Verificada em 22/10/2026 00:45–01:05 (UTC-3) contra `T3.md` (v2, base `main` @ `031957f`). Só leituras remotas (API pública do GitHub por curl, `raw.githubusercontent.com`, `.diff` do PR e cursor-github para check runs, compare e logs dos jobs), sem clone nem fetch.

> **Verificação pós-merge.** O Emerson mergeou o PR #198 em 22/10/2026 às 00:43:39 (UTC-3) (`merged_at` 2026-10-22T03:43:39Z, `merged_by` fazedordecodigo), **antes** desta verificação. A verificação estava parada desde 21/10 14:48 porque o computador da box ficou fora do ar. O veredito abaixo vale para o head `79e7ad3` e para o commit de merge `bb08a2c` (squash, mesmo conteúdo).

PR: https://github.com/fazedordecodigo/bob/pull/198 | branch `aidlc/u4-bob-yaml/t3-verify-install` → `main` | head `79e7ad3e3712b0af9819a33366fb3986dbcdd30f` | base `031957f6c41dcc4e3b0bf3d998c346d0eee7b456` | `state: closed`, `merged: true`, `draft: false` | merge (squash) `bb08a2c0fd2ceed93223c3f4cd052b86b7cce5de`, pai único `031957f` | 1 commit, +212/−15, 3 arquivos.
Commit: `79e7ad3` (21/10 12:49 UTC-3, pai `031957f`); PR aberto em 21/10 13:36 (UTC-3). `compare 031957f...79e7ad3`: `ahead 1`, `behind 0`. Agente: `bc-2662dd6b-6b38-561b-8c35-d9ccd7690468`.

## Veredito: Aprovado (pós-merge)
R1–R8, os 3 arquivos, os 5 testes, os 3 ajustes, o CHANGELOG, o corpo e os 6 checks do head atendem. Nenhum desvio. 0 rodadas de correção. O merge foi do Emerson, antes da verificação.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título e branch | `ET-u4-bob-yaml-T3: Harness: passo 5 e preservação do bob.yaml/waivers`; `aidlc/u4-bob-yaml/t3-verify-install` → `main`, base `031957f` (a da ET) | Atende |
| Exatamente 3 arquivos; `100755` | `pulls/198/files`: `CHANGELOG.md` +8/−0, `scripts/verify-install.sh` +123/−8, `tests/test_verify_install.py` +81/−7; nenhum em `src/`, `scripts/install.sh` nem `.github/workflows/`; `.diff`: `index 7bdca15..ce3a38a 100755`; corpo: `100755 ce3a38a… scripts/verify-install.sh` | Atende |
| R1 | head l.2 `# Harness do comando de verificação (CT15): passos 1, 2, 3, 4, 5, 7, 8, 9a e 9b.`; l.4 `STEP_IDS='1 2 3 4 5 7 8 9a 9b'`; `--help` sem hunk no diff | Atende |
| R2 | `run_selected` (l.1165): `      3\|4\|5\|7) ensure_2 ;;` (l.1177) e `      5) step_5 ;;` (l.1184) entre `4) step_4 ;;` e `7) step_7 ;;` | Atende |
| R3 | `new_project` (l.330-343): `_file=${2:-src/app.py}`, `mkdir -p "$_proj/$(dirname "$_file")"`, `printf '%s\n' 'print("app")' > "$_file"`; chamadas existentes sem hunk | Atende |
| R4 | `expected_bob_yaml()` na l.823, logo antes de `step_5` (l.846): `printf '%s\n'` com 19 argumentos, 4º `"  include: $1"`. Conferido na box: a função extraída pela regex do teste 2, rodada com `sh`, dá exit 0 e saída idêntica a `_BODY` de `init_config.py` (head) para `[src]`, `[app]` e `["."]` (19 linhas) | Atende |
| R5 (a)–(f) | `step_5` (l.846-917), entre `step_4` (l.791) e `step_7` (l.919): casos `src app sem-codigo` com `src/app.py`, `app/main.py`, `README.md` e `[src]`, `[app]`, `["."]`; as 9 mensagens `die_passo 5` iguais às da ET (criar projeto, `saiu $_rc`, última linha `  bob doctor: 0`, falta o bob.yaml, `bob.yaml difere: $_diff` via `first_diff`, falta o aviso / aviso fora do lugar com `grep -Fx` do texto exato, `bob check saiu 4`); `bob check` num subshell com `env -i "HOME=$S2_HOME" "TMPDIR=…" LANG=C.UTF-8 "PATH=$(tool_path)" "$S2_HOME/.local/share/bob-quality/bin/bob" check --base HEAD --gates crap,dry,deps`, saída em `check.log`, só para em `4`; `_t0=$(date +%s)` antes do 1º `run_oneliner`, `_t1` depois do 3º `bob check`, `printf 'verify-install: passo 5: tempo %s s\n'` e `ok 5` | Atende |
| R6 | `step_7`: `grep -Fx '  preserved: bob.yaml (already exists; not changed)' "$T/s7/out.log"` → `die_passo 7 "o resumo não lista bob.yaml"`, depois do `digest` e antes de `_flat` (teste de versões); nenhum outro hunk no passo | Atende |
| R7 | `step_8`: `mkdir -p … .bob`; `bob.yaml` (3 linhas) e `.bob/waivers.yaml` (`# waivers do dev`) com `\|\| exit 1` antes do `git add -A`; `_files` em duas linhas antes do 1º laço; os dois laços `for _rel in $_files; do`; dois `grep -Fx` novos depois do de `.agents/skills/outra`, com as mensagens da ET | Atende |
| R8 | passos 1-4 e 9a/9b idênticos à base (`diff` dos trechos `step_1`…`step_4` e `step_9a`…`run_selected`: sem diferença); modo `100755`; na box, `sh -n` e `dash -n` do script do head: exit 0; nenhum `local`, `[[`, array, `$'…'` nem `echo -e` nas linhas novas | Atende |
| Teste 1 | `test_step_5_is_wired` (l.139): as 4 linhas em `text.splitlines()` | Atende |
| Teste 2 (3 casos) | `test_harness_expects_the_ct7_text` (l.156): `parametrize(("include", "item"), [(("src",), "[src]"), (("app",), "[app]"), ((".",), '["."]')])`, a regex da ET, `subprocess.run(["sh", "-c", function + '\nexpected_bob_yaml "$1"\n', "_", item], capture_output=True, text=True, check=False)`, `returncode == 0` e `stdout == render_config(include)` | Atende |
| Teste 3 | `test_step_5_checks_the_no_code_warning` (l.178): `t("en", "setup.warning_line", step="bob.yaml", text=t("en", "setup.warn_no_code"))`, `count == 1` | Atende |
| Teste 4 | `test_steps_7_and_8_check_the_preserved_lines` (l.188): `bob_yaml` `count == 2`, `waivers` `count == 1` | Atende |
| Teste 5 | `test_step_5_runs_bob_check_with_the_u4_gates` (l.204): os 3 literais da ET | Atende |
| Posição dos testes | os 5 logo depois de `test_step_9a_is_wired` (l.130) e antes de `test_help_exits_0` | Atende |
| Imports | `from bob_quality.init_config import render_config` e `from bob_quality.messages import t` (l.14-15) | Atende |
| Ajustes em testes existentes | `_HELP` → `"passos: 1 2 3 4 5 7 8 9a 9b\n"`; `test_step_ids_are_the_u1_and_u3_steps` → `test_step_ids_are_the_u1_u3_and_u4_steps` com `"1 2 3 4 5 7 8 9a 9b"`; `test_usage_errors_exit_1_before_preparing`: 1º parâmetro `("--only", "6")` com `passo desconhecido 6. `, os dois primeiros com `Passos: 1 2 3 4 5 7 8 9a 9b.`; nenhum outro hunk em teste existente | Atende |
| Sem skip/only | nenhum `skip`, `xfail`, `.only`, `noqa`, `pragma` nem assert comentado no diff | Atende |
| ≤ 100 colunas | maior linha nova: 100 caracteres (CHANGELOG pt-BR, l.1); código e testes abaixo disso; as linhas de 107 e 139 do script (l.765 e 659) são antigas, sem hunk | Atende |
| CHANGELOG | topo de `## Unreleased`, en e pt-BR, cada um seguido de linha em branco, antes da entrada da T2; juntando as quebras com espaço, os dois textos são idênticos aos da ET (conferido na box); linhas de 96, 96, 59 e 100, 99, 56 colunas | Atende |
| `python -m pytest -q tests/test_verify_install.py` | corpo: `21 passed`; CI: `tests/test_verify_install.py .....................` (21) em 3.10 e 3.12 | Atende |
| `--only 5,7,8` | corpo: exit 0, `passo 2: ok`, `passo 5: tempo 5 s`, `passo 5: ok`, `passo 7: ok`, `passo 8: ok` | Atende |
| Harness inteiro ≤ 900 s, 9 `ok` | corpo: exit 0, 9 linhas `ok`, 146 s. CI no head (job 119347731923): 9 linhas `ok` (1, 2, 3, 4, 5, 7, 8, 9a, 9b), de 16:37:01 a 16:40:28 UTC = **206 s**. CI no merge `bb08a2c` (job 119626028709): 9 `ok`, de 03:43:53 a 03:47:15 UTC = **202 s** | Atende |
| Passo 5 ≤ 180 s (U4-N10) | corpo: 5 s (local, nas duas corridas); CI head: `verify-install: passo 5: tempo 7 s` (log 2026-10-21T16:38:21Z); CI merge: `passo 5: tempo 7 s` (2026-10-22T03:45:13Z) | Atende |
| Suíte inteira | CI head: `4520 passed, 3 warnings` em 3.10 (1043 s) e 3.12 (1149 s); 0 failed, 0 errors. 4513 da `main` (`031957f`) + 7 casos novos (1 + 3 + 1 + 1 + 1) = 4520; os ajustes não mudam a contagem | Atende |
| `bob check … crap,dry,deps,mutate,coverage` → 0 | corpo: exit 0, 5 gates `passed`; comentário do `bob` (CI, `crap,dry,deps,mutate`, commit `79e7ad3`): 4 ✅, "No surviving mutants", "No mutants without tests", waivers só de 2026-10-11 (nenhum novo) | Atende |
| 6 checks verdes no head; job mostra `passo 5: ok` | tabela abaixo, todos `success` em `79e7ad3`; log do `verify-install / linux-x64`: `verify-install: passo 5: ok` | Atende |
| Corpo do PR | U4, CT15, CT7, verification-command passos 5, 7 e 8, US3.1, US3.2, NFR4, NFR5; `## Decisões tomadas: nenhuma`; `## Bloqueios` com "Nenhum."; comandos com saída e os dois tempos | Atende |
| Não mergeado pelo agente | `merged_by: fazedordecodigo` (Emerson), 22/10 00:43:39 (UTC-3) | Atende |

## Checks no head `79e7ad3` (início 21/10 13:36 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| bob / check | bob, run 39636334994 | success | 14m51s |
| bob / cold | bob, run 39636334994 | success | 1m23s |
| CI / pytest (3.10) | CI, run 39636334872 | success, `4520 passed, 3 warnings` | 18m53s |
| CI / pytest (3.12) | CI, run 39636334872 | success, `4520 passed, 3 warnings` | 20m35s |
| package / dist | package, run 39636334827 | success | 1m25s |
| verify-install / linux-x64 | verify-install, run 39636334811 | success, 9 linhas `ok`, passo 5 em 7 s, harness em 206 s | 3m48s |

Graphify Formal Verification não aparece nos check runs do head; é externo e não é exigido.

## Checks no merge `bb08a2c` (`main`, início 22/10 00:43 UTC-3)
O squash `bb08a2c` tem pai único `031957f`, e os 3 arquivos são byte a byte iguais aos do head `79e7ad3` (conferido por `raw.githubusercontent.com`). O push na `main` dispara 4 checks, todos verdes; `bob / check` e `bob / cold` são só de PR.
| Check | Workflow / run | Resultado (consulta às 01:05 UTC-3) |
|---|---|---|
| package / dist | package, run 39718430522 | success (1m32s) |
| verify-install / linux-x64 | verify-install, run 39718430518 | success (3m52s), 9 `ok`, passo 5 em 7 s, harness em 202 s |
| CI / pytest (3.10) | CI, run 39718430516 | success (19m41s), `4520 passed, 3 warnings` |
| CI / pytest (3.12) | CI, run 39718430516 | success (20m39s), `4520 passed, 3 warnings` |

## Observações (não reprovam)
- O passo 7 imprime `passo 7: tempo 0 s` e o `ok 7` sai cerca de 60 s depois (CI head: 16:38:23 → 16:39:25). Esse trecho é anterior à T3: o tempo do passo 7 não mudou, e a T3 só acrescentou um `grep`.
- A corrida local do agente (`146 s`) é mais rápida que a do CI (`206 s`); as duas ficam bem abaixo do teto de 900 s.
- O corpo cita `32 subtests passed` na suíte local; o CI não mostra subtests. A contagem de casos (4520) é a mesma.
- `mergeable_state` não se aplica: o PR já está mergeado.

## Registro
- 22/10/2026 00:43 (UTC-3): o Emerson mergeou o #198 (squash `bb08a2c`) antes da verificação.
- 22/10/2026 01:05 (UTC-3): verificação pós-merge, rodada 1 (head `79e7ad3`): aprovado, sem desvios. `traceability.json` (U4 T3 `verified`, PR 198 `merged`) e `trace.md` atualizados.
