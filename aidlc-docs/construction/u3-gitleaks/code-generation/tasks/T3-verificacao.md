# Verificação: ET-u3-gitleaks-T3 (v1) × PR #193
Verificado em 20/10/2026 12:58 (UTC-3), contra a ET v1 (a despachada, `/workspace/dispatch/u3-t3/T3.md`, idêntica à do repositório de docs), só com leituras remotas (cursor-github), sem clone.
PR: https://github.com/fazedordecodigo/bob/pull/193 | branch `aidlc/u3-gitleaks/t3-verify-install` → `main` | head `8e70681b591f70b634078de28c1834ada6d2c20b` | base `8fafff6` | aberto, **rascunho**, não mergeado, `mergeable: true` (`mergeable_state: blocked`) | 1 commit (`8e70681`, 20/10 11:36 UTC-3), +196/−39. PR aberto em 20/10 12:33 UTC-3.

## Veredito: Aprovado para checkpoint (contra a ET v1), com ressalvas
Todos os critérios de aceite e R1–R12 atendem. 0 rodadas de correção. Ressalvas: o PR está em rascunho (ressalva 1), e o `mutate` não mede o harness (ressalva 2).

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Exatamente 3 arquivos; modo `100755` | `CHANGELOG.md` (+4), `scripts/verify-install.sh` (+135/−15), `tests/test_verify_install.py` (+57/−24); `changed_files: 3`; diff `index 67b1150..7bdca15 100755`, sem mudança de modo | Atende |
| R1 | comentário da l.2 exato; `STEP_IDS='1 2 3 4 7 8 9a 9b'`; `GITLEAKS_*` intactos; `GL_ASSET=` e `GL_URL=` junto das globais | Atende |
| R2 | `tool_path` imprime `$T/fake-sudo:$NODE_DIR:$PY_DIR:/usr/bin:/bin`; `fixture-bin` e `gl-src` ausentes do arquivo no head | Atende |
| R3 | extração trocada por `mkdir -p` das 2 pastas, 2 `cp`, `printf '\n' >>` no bad e `GL_ASSET=$_asset`; cada falha leva a `die_preparo "não consegui montar o espelho"`; plataforma e cache intactos | Atende |
| R4 | `prepare_gitleaks` entre `build_mirror` e `start_server`, só no modo espelho; `prepare_fakes` nos dois modos | Atende |
| R5 | `release_pair`: remoto `GL_URL=`; espelho `GL_URL=$BASE/gitleaks` | Atende |
| R6 | `_gl=$(PATH="$_path" command -v gitleaks 2>/dev/null) \|\| _gl=` logo depois da checagem do `bob`, com a mensagem exata; `BOB_GITLEAKS_BASE_URL=$GL_URL` depois de `BOB_RELEASES_URL`, só se não vazia | Atende |
| R7 | `check_gitleaks_install()`: `BH=$2/.local/share/bob-quality`; (a) `readlink`, (b) `version`, (c) modo `755` com o comando Python exato; as 3 mensagens exatas | Atende |
| R8 | `_want` com 5 linhas, a última `GET /gitleaks/$GL_ASSET 200`; `check_gitleaks_install 2 "$S2_HOME"` fora do `if` e antes do `printf` do tempo | Atende |
| R9 | `_gl_bin`, `die_passo 7 "o gitleaks não está instalado"`, `_gl_before`, `_gl_mark` (espelho) antes do `run_oneliner`; depois, mtime → `"o gitleaks foi reinstalado"` e ` /gitleaks/` → `"o gitleaks foi baixado de novo"` | Atende |
| R10 | `step_9a` entre `step_8` e `step_9b`; mensagem de `VERIFY_REMOTE=1`; `release_pair` e depois `GL_URL=$BASE/gitleaks-bad`; `_mark`; argumentos do `run_oneliner` exatos; as 7 checagens na ordem, com as mensagens exatas; `ok 9a` | Atende |
| R11 | `GL_URL=$BASE/gitleaks` antes do `run_oneliner` do 9b | Atende |
| R12 | `9a) step_9a ;;` entre `8)` e `9b)`; mensagens novas só em pt-BR; `sh -n` e `dash -n` do arquivo do head: 0; sem bashismo novo; `main "$@"` é a última linha | Atende |
| Largura | `.py`: nenhuma linha nova passa de 100 colunas. Shell: a linha do Python de R7 tem 107 colunas, mas é literal exigido pela ET e o arquivo já tem linha de 139 (a regra de largura da T5 da U1 vale só para `.py`; shell segue o estilo do arquivo) | Atende |
| 5 testes novos, nomes exatos | `test_gitleaks_constants_match_the_gitleaks_table`, `test_harness_has_no_gitleaks_fixture`, `test_harness_serves_gitleaks_from_the_mirror`, `test_harness_passes_the_gitleaks_base_url`, `test_step_9a_is_wired`, com os conteúdos da tabela. 11 `def test_` no head = 7 da base − 1 substituído + 5 | Atende |
| Ajustes da lista fechada | `test_step_ids_are_the_u1_steps` renomeado para `test_step_ids_are_the_u1_and_u3_steps` (`"1 2 3 4 7 8 9a 9b"`); `test_gitleaks_constants_match_the_doctor_pin` removido; `_gitleaks()` e `from bob_quality.doctor import BinaryPin, PINS` removidos; `from bob_quality import gitleaks`; `_HELP` com `passos: 1 2 3 4 7 8 9a 9b`; caso `"5"` com `Passos: 1 2 3 4 7 8 9a 9b.` e caso `("--only", "9c")` novo. Além disso foi removida a tupla `_SHA_NAMES` (observação 1) | Atende |
| Sem skip/xfail/only | nada no diff | Atende |
| CHANGELOG | os 2 parágrafos exatos no topo de `## Unreleased` | Atende |
| Suíte | CI: 3.12 `4428 passed, 3 warnings in 1172.67s (0:19:32)`; 3.10 `4428 passed, 3 warnings in 1144.94s (0:19:04)` (= 4423 da T2 + 5); corpo: `14 passed` em `test_verify_install.py` | Atende |
| `--only 2,7,9a` | corpo: passo 2 com tempo 45 s (≤ 300) e ok, passo 7 com tempo 0 s (≤ 60) e ok, passo 9a ok; EXIT 0; ordem certa | Atende |
| Harness inteiro | corpo: 8 linhas `ok`, `real 146.968` (≤ 900). CI (`verify-install / linux-x64`, `sh scripts/verify-install.sh`): `passo 1..9b: ok`, inclusive `passo 9a: ok` (8 linhas), passo 2 com tempo 64 s, passo 7 com 1 s; o harness rodou de 12:34:13 a 12:37:32 UTC-3 | Atende |
| Prova negativa | corpo: cópia sem o `printf '\n' >>`; `verify-install: passo 9a: saiu 0 com gitleaks adulterado`, EXIT 1; cópia apagada, não commitada | Atende |
| `PATH=/usr/bin:/bin command -v gitleaks` | corpo: vazio | Atende |
| `bob check` | job `check` success, o que implica exit 0 de `bob check --gates crap,dry,deps,mutate --base origin/main` (`run_check.sh` + `propagate_exit.sh`); corpo: `… mutate,coverage` com EXIT 0 e 0 sobreviventes (ressalva 2) | Atende |
| 6 checks verdes | tabela abaixo | Atende |
| Citações no corpo | U3, CT6, CT9, CT15, FR2.2, FR2.3, NFR1, NFR6, US1.3, US1.1 crit. 1, passos 2, 7 e 9a; "Decisões tomadas" = "nenhuma"; "Bloqueios" = "nenhum" | Atende |
| Não mergeado | `merged: false` | Atende |

## Checks no head `8e70681` (início 20/10 12:34 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| pytest (3.12) | CI / 39449597803 | success | 20m53s |
| pytest (3.10) | CI / 39449597803 | success | 20m30s |
| check | bob / 39449597779 | success | 12m23s |
| verify-install / linux-x64 | verify-install / 39449597739 | success | 3m41s |
| dist | package / 39449597972 | success | 1m29s |
| cold | bob / 39449597779 | success | 1m15s |

## Ressalvas
1. **Rascunho com "Bloqueios: nenhum".** Nem o corpo nem o único commit explicam o rascunho. O commit é de 11:36 e o PR foi aberto às 12:33 (UTC-3); as 6 corridas são do head e todas verdes. Não há bloqueio escondido: nenhum critério falha e o corpo não menciona problema. O mais provável é o padrão do agente de abrir PR como rascunho (no #192 o agente também teve de tirar o PR do rascunho), mas isso é inferência, não prova. **Não é desvio de critério de aceite:** a ET exige rascunho quando há bloqueio e não diz nada para o caso sem bloqueio; nenhum critério pede "fora de rascunho". É uma lacuna da ET, na seção "Entrega". Para o merge, alguém precisa marcar "Ready for review"; não mudei nada no GitHub.
2. **`mutate` sem efeito nesta tarefa.** O próprio corpo diz que nenhuma função do diff foi medida, porque shell e testes ficam fora de `paths.include`. A regra do mutate da ET foi cumprida, mas não teve o que medir; a prova do harness é o job `verify-install` e a prova negativa.

## Observações (não reprovam)
1. `_SHA_NAMES` foi removida de `test_verify_install.py` sem estar na lista de ajustes. Ela só servia ao teste substituído e ficaria sem uso, como o `_gitleaks()` que a ET mandou apagar; manter seria código morto (restrições da T1).
2. Cada check tem 1 anotação (não lida).

## Registro
- 20/10/2026 12:58 (UTC-3): aprovado contra a ET v1; `traceability.json` (U3 T3: `verified`, PR 193, `et_version` v1, `correction_rounds` 0) e `trace.md` atualizados. Entregue ao Maestro. Merge é do Emerson, depois de tirar o PR do rascunho.
