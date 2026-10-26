# Verificação: ET-u6-perfil-shell-T3 (v2) × PR #207
Verificada em 23/10/2026 21:48 (UTC-3) contra `T3.md` (v2, 23/10 21:15 UTC-3; v1 em `T3.v1.md`; base de despacho `377b855`, variante A). Só leituras remotas pelo MCP `cursor-github` (PR, diff, commits, check runs, logs de job, conteúdo na branch, comentários), sem clone nem fetch. Transcript do agente indisponível (não está em `/workspace/cloud-agent-transcripts/`; o Agent Store só tem `inbox/`); evidência = corpo do PR + CI.

PR: https://github.com/fazedordecodigo/bob/pull/207 | branch `aidlc/u6-perfil-shell/t3-verify-install` → `main` | head `81ac85ffeab3fa7bf04f94e772a8d38b8d423cc1` | base `377b855daecb1f0354254c19f1ae62fb36800bab` | aberto, pronto para revisão (`draft: false`), não mergeado | 2 commits (`bd60e8e` sobre `377b855`, 23/10 20:12 UTC-3; `81ac85f` "o teste 5 confere o PROFILE_LINE inteiro", 23/10 21:14 UTC-3) | +452/−10, 3 arquivos.
Agente: `bc-c25b835a-c8b8-5916-819e-797226d9248a`. `correction_round` 1 (lacuna da ET v1: teste 5 com `managed-by` e coluna da linha `_warn`; corrigida na v2).

## Veredito: Aprovado para checkpoint
Os critérios de aceite, R1–R6, A1–A3 e os 5 testes (8 casos) da ET v2 atendem. Os 6 checks obrigatórios do head estão verdes. Nenhum desvio que reprove. O merge é do Emerson (ordem: U6 T3 primeiro, depois a U7 T3 rebaseia).

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u6-perfil-shell-T3: Harness: passo 13 (perfil do shell)`; `aidlc/u6-perfil-shell/t3-verify-install` → `main`; base `377b855…`; 1º commit com parent `377b855` | Atende |
| Fora de rascunho; não mergeado pelo agente | `draft: false`, `state: open`, `merged: false` | Atende |
| Passo 0 colado e igual ao esperado (variante A) | corpo: `377b855…`; `STEP_IDS='1 2 3 4 5 6 7 8 9a 9b 12'`; `PROFILE_LINE=…# managed-by: bob-quality'`; `10`; as 4 linhas do resumo exatas; `1000`; `EXIT:0`; `29 passed`; `EXIT:0`; `1` | Atende |
| Exatamente 3 arquivos | `CHANGELOG.md`, `scripts/verify-install.sh`, `tests/test_verify_install.py`. Nenhum proibido (`scripts/install.sh`, `src/**`, outros testes, `docs/**`, `website/**`, `README*`, `.github/workflows/`, `pyproject.toml`) | Atende |
| CHANGELOG: texto exato no topo de `## Unreleased` | 2 parágrafos (en, pt-BR) logo após a linha em branco do título, antes da entrada U5; texto reunido == texto da ET (conferido por script); cada um seguido de linha em branco; máx. 100 colunas, quebra em espaço | Atende |
| R1 linhas 2 e 4 | `# Harness … 9a, 9b, 12 e 13.`; `STEP_IDS='1 2 3 4 5 6 7 8 9a 9b 12 13'` | Atende |
| R2 `run_oneliner` | `_shell=${10:-}`/`_bobhome=${11:-}` após `_err=$9`; condição `&& [ "$_bob" != "$_home/.local/bin/bob" ]`, mensagem igual; 2 blocos de 3 linhas `SHELL`/`BOB_HOME` entre o `fi` do `GL_URL` e o `for _name`; nada mais muda | Atende |
| R3 `profile_line()` | logo após `node_below`, `sed` exato; o valor de `PROFILE_LINE` não aparece no harness (teste 5); `expected_hook` da U5 (`'# managed-by: bob-quality'`, linha 934 no head) intacto, fora do diff | Atende |
| R4a preparo | `_c`, `_h`, `mkdir -p`, `new_project`, mensagem de preparo; `_pf` por caso; `_path=$(tool_path)`; b `alias bob-antes=1` sem `\n`; d PATH com `$_h/.local/bin`; e `# só leitura` + `chmod 0444` | Atende |
| R4b linhas exatas | as 8 linhas na ordem, com 2 espaços; `_warn` inteira numa linha (131 col.; exceção v2) | Atende |
| R4c execuções | chamada com os 11 argumentos (`"$2" "$S2_HOME/.local/share/bob-quality"`); rc, `last_nonempty`, `_want` por caso/execução, aviso e `install: perfil: ok` no caso e; mensagens exatas | Atende |
| R4d pós-execuções | conteúdo a/c, b, e via `show_file`; modo 644 com `format(… & 0o777, "o")` como em `check_gitleaks_install`; marca única; `env -i … sh -c '. "$1"; command -v bob'`; perfil a mais (d: os 3) | Atende |
| R5 `step_13()` | linhas 2–5 exatas (root, `ensure_2`); `release_pair`; `_t0`; 5 linhas `profile_case`; `_secs > 180` → die; linha `tempo`; `ok 13` | Atende |
| R6 `run_selected` | `      13) step_13 ;;` logo após `12) step_12 ;;`; `3\|4\|5\|6\|7\|12) ensure_2 ;;` sem mudança | Atende |
| A1–A3 | `_HELP` 2ª linha `… 12 13`; `test_step_ids_are_the_known_steps` com `… 12 13`; `--only 15` + `Passos: … 12 13.` e `9c` com `… 12 13.`; nenhum outro teste existente muda | Atende |
| Helpers e 5 testes com nomes exatos | `_function` e `_INSTALL` antes do teste 1, após `test_pytest_pin_matches_pyproject`; `test_step_13_is_wired`, `test_run_oneliner_passes_shell_and_bob_home` (`with`, `without`, `own_bob`, `foreign_bob`), `test_step_13_summary_lines_are_the_ct3_texts`, `test_step_13_warning_is_the_install_sh_text`, `test_profile_line_comes_from_install_sh` | Atende |
| Teste 5 na forma v2 | `assert checked.stdout == found.group(1) + "\n"` e `assert found.group(1) not in _text()`; sem `"managed-by" not in _text()` | Atende |
| Sem skip/xfail/only/waiver | diff sem `skip`, `xfail`, `only`, asserts comentados; nenhum arquivo de waiver/limite tocado; waivers do relatório bob são os pré-existentes (11/10) | Atende |
| `test_verify_install.py`: 37 passed | corpo: `37 passed in 2.14s`; CI pytest 3.10 e 3.12: 37 pontos em `tests/test_verify_install.py` | Atende |
| Colunas (critério v2) | diff: única linha nova > 100 colunas é a `_warn=` (131), excetuada; resto ≤ 100 | Atende |
| `--only 13` sai 0, tempo ≤ 180 s | corpo: `EXIT:0`, `passo 2: ok`, `passo 13: tempo 8 s`, `passo 13: ok`; `--only 15` → mensagem exata e `RC:1`; `sh -n`/`dash -n` RC:0 | Atende |
| Harness inteiro no CI, ≤ 900 s, 12 linhas ok | job `linux-x64` (run 40044012834): success, 21:14:55–21:16:25 UTC-3 (90 s); `grep -c 'verify-install: passo .*: ok'` = 12 (1–9b, 12, 13); `verify-install: passo 13: tempo 6 s`; `passo 13: ok` | Atende |
| Suíte inteira 0 failed / 0 errors | CI 3.10 e 3.12: `4790 passed, 3 warnings` (4782 + 8); corpo: `4790 passed, 3 warnings, 32 subtests passed` | Atende |
| `bob check … crap,dry,deps,mutate,coverage` exit 0; mutmut dogfood | corpo: EXIT:0, os 5 gates passed; CI `bob / check` (crap,dry,deps,mutate) success, relatório: 4 ✅, "No surviving mutants", "No new clones", sem violação de deps; suíte com dogfood do mutmut verde no CI | Atende |
| 6 checks verdes | tabela abaixo | Atende |
| Corpo do PR | Resumo, Passo 0 (bloco, saída, variante A), Arquivos, Testes (5 nomes + A1–A3), Comandos (com `passo 13: tempo` e duração do job), `## Decisões tomadas: nenhuma`, `## Bloqueios` / Nenhum; refs U6, CT15, CT16, CT3, ADR 0013, ADR 0026, ADR 0027, FR1.1, NFR2, NFR4, NFR5, NFR9 | Atende |

## Checks no head `81ac85f` (CI no merge `072d9d8` = `81ac85f` sobre `377b855`; início 23/10 21:14 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| bob / check | bob, run 40044012770 | success; crap/dry/deps/mutate ✅ | 11m29s |
| bob / cold | bob, run 40044012770 | success | 0m39s |
| CI / pytest (3.10) | CI, run 40044012878 | success, `4790 passed, 3 warnings` | 20m17s |
| CI / pytest (3.12) | CI, run 40044012878 | success, `4790 passed, 3 warnings` | 20m47s |
| package / dist | package, run 40044012765 | success | 0m40s |
| verify-install / linux-x64 | verify-install, run 40044012834 | success, 12 linhas `ok`; passo 2 14 s, passo 12 8 s, passo 13 6 s | 1m30s |
| website / build | — | não se aplica (o PR não toca `docs/` nem `website/`) | — |

## Observações (não reprovam)
- Helpers de teste extras não listados na ET: `_SUMMARY_LINES` e `_WARN_LINES` (as 4+4 linhas de R4b, partidas em literais adjacentes para caber em 100 colunas) e `_env_rows` (monta a lista esperada do teste 2). Só organização interna; as asserções e os valores são os da ET.
- R4a/R4c em várias linhas com `\` (preparo e chamada de `run_oneliner`); equivalente e dentro de 100 colunas.
- `mergeable_state: blocked` com checks verdes: proteção de branch, não falha de CI.
- O CI do `bob / check` roda `crap,dry,deps,mutate` (sem `coverage`); a evidência do `coverage` está no corpo do PR (mesmo padrão da T2).
- O `bob / check` loga `dry-before not_run` (linha de base sem npm); `dry-after passed`.
- Transcript do agente não disponível no box.

## Registro
- 23/10/2026 21:48 (UTC-3): rodada contra a v2 (head `81ac85f`, base `377b855`): aprovado para checkpoint, sem desvios. `correction_round` 1 (lacuna da ET v1). `traceability.json` (U6 T3 `approved_for_checkpoint`, PR 207 `open`) atualizado. Status da unit sem mudança. O merge é do Emerson.
