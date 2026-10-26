# Verificação: ET-u8-docs-T4 (v1) × PR #211
Verificada em 24/10/2026 09:12 (UTC-3) contra `T4.md` (v1, 22/10/2026; SHA base fixado no despacho em 24/10/2026: `465b1056cf1324c00780df42f5659a44ba169358`). Só leituras remotas pelo `gh` / GitHub API (PR, diff, commit, check runs, logs de job, conteúdo na ref do head), sem clone nem fetch. Transcript do agente indisponível no box; evidência = corpo do PR + CI + arquivos lidos na ref do head.

PR: https://github.com/fazedordecodigo/bob/pull/211 | branch `aidlc/u8-docs/t4-step-14` → `main` | head `22fc38485e11f62cb9e114ab828174bb31c985cf` | base `465b1056cf1324c00780df42f5659a44ba169358` | aberto, pronto para revisão (`isDraft: false`, `mergeable: MERGEABLE`), não mergeado | 1 commit (parent `465b105…`, 24/10/2026 07:41:50 UTC-3) | +533/−28, 3 arquivos.
Agente: `bc-b3042bc9-9c62-5b0c-b45a-30d69643b3fe`. `correction_round` 0 (aprovado na 1ª rodada contra a ET v1).

## Veredito: Aprovado para checkpoint
Todos os critérios de aceite, R1–R8, A1–A5 e os 5 testes novos (8 casos) atendem. Os 6 checks do head estão verdes. Nenhum desvio. O merge é do Emerson.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u8-docs-T4: Harness: passo 14 (comando único × prompt de IA) e pass_env`; `aidlc/u8-docs/t4-step-14` → `main`; base `465b1056…`; commit único `22fc384…` com parent `465b1056…` | Atende |
| Fora de rascunho; não mergeado pelo agente | `state: OPEN`, `isDraft: false`, `mergeable: MERGEABLE` | Atende |
| Passo 0 colado e igual ao esperado (9 itens) | corpo: (1) `465b1056…`; (2) linha 2 `… 12 e 13.` e `STEP_IDS='1 … 13'`; (3) `2`; (4) `350:release_pair`, `362:run_oneliner`, `1419:run_bob`, `1840:step_13`, `1861:run_selected`; (5) `30:NEW_WHL=`, `1889:      13) step_13 ;;`; (6) `0`; (7) `docs/install-prompt.en.md`; (8) `EXIT:0`; (9) `46 passed in 0.29s` | Atende |
| Exatamente 3 arquivos; nenhum proibido | `CHANGELOG.md` (+10/−0), `scripts/verify-install.sh` (+331/−24), `tests/test_verify_install.py` (+192/−4). Sem `docs/**`, `scripts/install.sh`, `src/**`, `.github/workflows/**`, `tests/test_docs_pins.py`, `.bob/waivers.yaml` | Atende |
| R1 linhas 2 e 4 | `verify-install.sh:2` `# Harness … 12, 13 e 14.`; `:4` `STEP_IDS='1 2 3 4 5 6 7 8 9a 9b 10 11 12 13 14'` | Atende |
| R2 globais | `:30 NEW_WHL=`, `:31 PASS_ENV=`, `:32 BLOCK_FAILED=` | Atende |
| R3 `pass_env()` | `:364`, logo após o `}` de `release_pair` (`:352`) + 1 linha em branco; `PASS_ENV=`; laço das 14 variáveis na ordem; `${NOME+x}`; `sed "s/'/'\\\\''/g"`; acrescenta ` 'NOME=valor'`. `for _name in PIP_INDEX_URL` só 1 vez (`:366`) | Atende |
| R4 `run_oneliner` e `run_bob` | laços removidos (2 × 11 linhas `-`); `  pass_env` + `  eval "set -- \"\$@\"$PASS_ENV"` em `:413-414` e `:1447-1448`; a linha `eval` aparece 3 vezes no arquivo (com `run_blocks`) | Atende |
| R5 ordem das funções novas | `step_13` 1840 < `box_platform` 1861 < `prompt_blocks` 1871 < `manifest` 1897 < `run_blocks` 2024 < `install_state` 2057 < `step_14` 2067 < `run_selected` 2167, cada uma seguida de linha em branco | Atende |
| R5a `box_platform` | `case "$(uname -s)/$(uname -m)"` com os 4 ramos e `*) return 1` | Atende |
| R5b `prompt_blocks` | `"$PY_DIR/python3" -c '…'` sem aspas simples; regex `^```sh bob-step=(\S+) platform=(\S+)\n(.*?)^```$`, `re.M \| re.S`; filtro `all`/SO/plataforma; `%02d.sh` a partir de 01; `sys.exit(1)` se ≠ 14 | Atende |
| R5c `manifest` | `BOB_HOME=$1/.local/share/bob-quality`; `missing/link/dir/file` (modo `& 0o777` octal + sha256); `versions/<x>/venv` → linha `freeze` com `pip freeze --all --disable-pip-version-check` (`check=True`) e normalização `bob-quality @ <wheel>`; árvore `PROJ/.agents/skills` ou `missing`; 4 caminhos avulsos; `sorted`, `\n` final | Atende |
| R5d `run_blocks` | 6 variáveis `_dir…_err`; `env -i HOME TMPDIR LANG=C.UTF-8 PATH=$(tool_path)`; `BOB_RELEASES_URL=$REL_ENV` e `BOB_GITLEAKS_BASE_URL=$GL_URL` condicionais; 2 linhas de R4; `sh`; sem `SHELL`; laço com `BLOCK_FAILED=${_f##*/}`, subshell `cd "$_proj" \|\| exit 99`, `>>`; `return` do código; `BLOCK_FAILED=` e `return 0` | Atende |
| R5e `install_state` | `manifest … > "$1" \|\| return 1`; `run_bob 14 … doctor` + `doctor<TAB><rc>`; `run_bob 14 … --version \|\| return 1` + conteúdo do `version.out` | Atende |
| R6 cabeçalho de `step_14` | 4 linhas exatas (`VERIFY_REMOTE=1` → `não se aplica`, `return 0`) | Atende |
| R6a–R6j | `release_pair`; `rm -rf`/`mkdir -p` das 5 pastas; `new_project`; `npm_config_cache` exportado; `_t0`; A via `run_oneliner 14` (9 args) + `  bob doctor: 0` + `install_state a.txt`; recriação; `box_platform`, `prompt_blocks docs/install-prompt.en.md`, `_mark`, `run_blocks` B; última linha `bob-prompt: verificação: ok (bob $X, bob doctor 0)`; 4 pedidos exatos ao espelho com `_flat`; `sudo.log`; `install_state b.txt` + `cmp -s` + `first_diff`; B2 com `file_sha` do `.profile`, `pacote: ok (reused)` = 1, `gitleaks: ok (reused)` = 1, última linha; `_secs > 360`; `passo 14: tempo` e `ok 14`. Todas as mensagens `die_passo 14` com o texto da ET | Atende |
| R7 `run_selected` | `:2195 13) step_13 ;;`, `:2196 14) step_14 ;;`; linha `ensure_2` intacta | Atende |
| R8 `CHANGELOG.md` | linhas 5-8 (en) e 10-13 (pt-BR) logo após `## Unreleased` + linha em branco, antes da entrada U7; texto unido idêntico ao da ET (comparação exata = True); quebra gulosa: larguras 99/100/98/57 e 94/100/98/62 bytes, a próxima palavra não caberia em nenhuma | Atende |
| A1–A5 (só estes mudaram) | linhas `-` em testes: só `_HELP` (A1), `STEP_IDS` (A2) e 2 × `Passos:` (A3); A4 `"GL_URL=\n" + _function(_text(), "pass_env") + "\n"` (`:737-739`); A5 `…GL_URL=http://g\n" + _body("pass_env") + "\n"` (`:505-507`) | Atende |
| 5 testes novos, 8 casos, nomes exatos, após `test_profile_line_comes_from_install_sh` | `test_step_14_is_wired` (884), `test_harness_passes_env_in_one_place` (933), `test_pass_env_quotes_the_values` (950; `plain`, `space`, `quote`), `test_prompt_blocks_filter_by_platform` (971; `linux-x64`, `darwin-arm64`), `test_manifest_lists_the_install` (1011; as 10 linhas exatas). Sem import novo; sem skip/only/xfail | Atende |
| `test_verify_install.py`: 54 passed | corpo `54 passed in 0.42s`; CI pytest 3.10: 43 + 11 = 54 pontos em `tests/test_verify_install.py` | Atende |
| `sh -n` / `dash -n` | corpo `EXIT:0`; reconferido no box sobre o arquivo do head: `EXIT:0` | Atende |
| `--only 14` e `VERIFY_REMOTE=1` | corpo: `EXIT:0`, `passo 14: ok` 1×, `tempo 31 s` (≤ 360); `não se aplica` 1× | Atende |
| Suíte inteira | CI 3.10 `4832 passed, 3 warnings` (21m37s) e 3.12 `4832 passed, 3 warnings` (19m12s); 0 failed, 0 errors | Atende |
| `bob check …` exit 0; 0 waivers novos | corpo: exit 0, crap/dry/deps/mutate/coverage passed, 0 waivers; CI `bob / check` success; `.bob/waivers.yaml` fora do diff | Atende |
| Colunas | `grep '^+[^+]' \| grep -vF '# Harness…' \| awk 'length > 101' \| wc -l` no diff do PR → `0` | Atende |
| Harness no CI | `verify-install / linux-x64` (job 120863661905): 15 linhas `passo …: ok` (1..8, 9a, 9b, 10..14), 192 s (≤ 900); tempos: passo 2 19 s, 10 17 s, 11 0 s, 13 10 s, 14 42 s (≤ 360) | Atende |
| 6 checks verdes | tabela abaixo | Atende |
| Corpo do PR | Resumo, Passo 0, Arquivos, Testes, Comandos (com tempos), `## Decisões tomadas: nenhuma`, `## Bloqueios` (`Nenhum.`), referências U8, CT15, CT18, ADR 0026, ADR 0028, ADR 0029, FR1.6–FR1.8, NFR10 | Atende |

## Checks no head `22fc38485e11f62cb9e114ab828174bb31c985cf`
| Check | Run / job | Resultado | Duração |
|---|---|---|---|
| bob / check | 40091064774 / 120863662138 | pass | 12m30s |
| bob / cold | 40091064774 / 120863661936 | pass | 34s |
| CI / pytest (3.10) | 40091064787 / 120863664741 | pass, 4832 passed | 22m13s |
| CI / pytest (3.12) | 40091064787 / 120863664538 | pass, 4832 passed | 19m48s |
| package / dist | 40091064824 / 120863662137 | pass | 39s |
| verify-install / linux-x64 | 40091064773 / 120863661905 | pass, 15 linhas ok | 3m12s |

## Observações (não reprovam)
- Pytest local não rodou no box (sem pytest instalado); a contagem de 54 vem do log do CI e do corpo do PR.
- `bob / check` no CI roda `crap,dry,deps,mutate`; `coverage` vem do corpo do PR, como nas ETs anteriores.
- O corpo relata um "Before" com exit 2 no `bob check` local por falta de `uv` no ambiente do agente; o "After" e o CI estão verdes.

## Registro
- 24/10/2026 09:12 (UTC-3): 1ª rodada contra a ET v1 (head `22fc384…`, base `465b105…`): aprovado para checkpoint, sem desvios (`correction_round` 0). `traceability.json` atualizado (U8 T4 `verified_awaiting_checkpoint`). O merge é do Emerson.
