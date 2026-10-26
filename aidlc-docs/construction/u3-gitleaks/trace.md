# U3 — Rastreabilidade (u3-gitleaks)

Escopo: só esta unit. Estado: **concluída**: Plan Approval em 2026-10-19 23:11, T1 a T4 mergeadas (#191 a #194, última em 0b4c6ec) e checkpoint aprovado pelo Emerson em 2026-10-20 15:28 UTC-3. Base `main` @ `387b0b6d0b19907e02b0db78762d6d8656e7135c`. Q1 = A e Q2 = A (2026-10-19 23:10 UTC-3, "Q1 A, Q2 A."): I15 e I16 resolvidas; T4 é tarefa normal.

## FR/US → tarefa → prova
| FR / US | Tarefa | Prova (teste ou passo do harness) |
|---|---|---|
| FR2.2 (baixa e confere o gitleaks 8.30.1, Linux e macOS) | T1, T2, T3 | `test_assets_are_the_four_adr_0014_entries`, `test_platform_key_maps_the_ct9_table`, `test_ensure_installs_the_binary_and_the_link`, `test_gitleaks_step_installs_when_missing`; passo 2 |
| FR2.3 (falha de integridade não instala e para) | T1, T2, T3 | `test_tampered_archive_fails_integrity_and_installs_nothing[en,pt-BR]`, `test_archive_without_the_expected_binary_fails_extraction`, `test_gitleaks_step_failure_stops_setup[en,pt-BR]`, `test_doctor_install_gitleaks_failure_exits_4[en,pt-BR]`; passo 9a |
| FR2.1 (contribui: o doctor confere o que o setup instalou) | T2, T4 | `test_doctor_finds_gitleaks_in_bob_home_before_the_path`, `test_doctor_cli_finds_gitleaks_in_bob_home`; passo 2 (`  bob doctor: 0` sem fixture); `test_gitleaks_only_in_bob_home_is_not_a_missing_tool` (T4) |
| US1.3 crit. 1 (confere antes de usar, 100%) | T1, T3 | mesmos de FR2.2 e FR2.3; passos 2 e 9a |
| US1.3 crit. 2 (falha → 0 binários, mensagem com passo e ação, saída ≠ 0) | T1, T2, T3 | `test_tampered_archive_fails_integrity_and_installs_nothing`, `test_write_error_leaves_nothing_in_tools`, `test_gitleaks_step_failure_stops_setup`; passo 9a |
| US1.1 crit. 1 (contribui: um comando instala tudo) | T2, T3 | passo 2 sem fixture |
| US1.1 crit. 5 (contribui: gitleaks 8.30.1 e ferramentas pinadas) | T2, T3 | `test_gitleaks_pin_comes_from_the_gitleaks_table`; passo 2 (`gitleaks expected 8.30.1 found 8.30.1`, `BOB_HOME/bin/gitleaks version` = `8.30.1`) |
| NFR1 (≤ 5 min com o gitleaks; RE-Q1 A) | T3 | passo 2 (`tempo ≤ 300`) |
| NFR3 (Linux e macOS, x64 e arm64) | T1 | `test_platform_key_maps_the_ct9_table`, `test_platform_key_rejects_other_platforms`; prova automática só Linux x64 (matriz U9) |
| NFR4 (2ª execução) | T1, T2, T3 | `test_second_ensure_downloads_nothing`, `test_gitleaks_step_is_unchanged_when_present`; passo 7 |
| NFR6 (100% conferidos, 0 instalados na falha) | T1, T3 | `test_tampered_archive_fails_integrity_and_installs_nothing`; passo 9a |
| NFR7 (sem sudo) | T3 | passo 3 (inclui 9a) |
| NFR9 (erro claro, en/pt-BR) | T1, T2 | `test_gitleaks_messages_exist_in_both_languages`, `test_setup_messages_exist_in_both_languages`, `test_doctor_bob_home_relative_message_in_both_languages` |
| CT9 | T1 | `tests/test_gitleaks.py` (32 testes, ET v2) |
| CT3 (ordem 4) | T2 | `test_steps_follow_the_ct3_order` |
| CT8 ("U3 acrescenta") | T2 | `test_locate_binary_*` (5), `test_doctor_install_*` (4) |
| CT14 (tempos e retries do Python) | T1 | `test_download_uses_a_30_s_timeout`, `test_http_4xx_is_not_retried[404,429]`, `test_5xx_is_retried_twice`, `test_5xx_then_200_installs`, `test_network_error_is_retried_twice` |
| CT6 (`BOB_GITLEAKS_BASE_URL`) | T1, T3 | `test_base_url_accepts_https_and_loopback`, `test_base_url_rejects_other_urls`; passos 2 e 9a (espelho) |
| CT15 (harness) | T3 | `test_step_ids_are_the_u1_and_u3_steps`, `test_harness_has_no_gitleaks_fixture`; harness inteiro |
| ADR 0014 (tabela só no código) | T1, T2 | `rg -l -F` dos 4 sha em `src/` → só `gitleaks.py`; `test_doctor_has_no_gitleaks_literals`; `test_gitleaks_constants_match_the_gitleaks_table` |
| ADR 0019 (`BOB_HOME/bin` antes do `PATH`) | T2, T4 | `test_locate_binary_prefers_bob_home_bin`, `test_doctor_finds_gitleaks_in_bob_home_before_the_path` |

## Pronto da U3 (e DoD do B3) → ET → prova
| Pronto | ET | Prova |
|---|---|---|
| 1. Teste da tabela com os 4 assets e sha | T1 | `tests/test_gitleaks.py::test_assets_are_the_four_adr_0014_entries` |
| 2. Projeto novo sem gitleaks no `PATH`: passo 2 sem fixture; `BOB_HOME/bin/gitleaks version` = 8.30.1 | T3 (com T1, T2) | harness passo 2 (`check_gitleaks_install`, 5 GETs exatos); `test_harness_has_no_gitleaks_fixture` |
| 3. tar.gz adulterado → 4, cita `gitleaks` e "sha256", `BOB_HOME/tools/gitleaks` não existe | T1, T2, T3 | harness passo 9a; `test_tampered_archive_fails_integrity_and_installs_nothing`; `test_gitleaks_step_failure_stops_setup` |
| 4. 2ª execução com 0 requisições ao servidor local | T1, T2, T3 | harness passo 7 (0 GETs `/gitleaks/`, mtime igual); `test_second_ensure_downloads_nothing`; `test_gitleaks_step_is_unchanged_when_present` |
| B3: tira a fixture do gitleaks | T3 | `test_harness_has_no_gitleaks_fixture`; `run_oneliner` falha se achar `gitleaks` no `PATH` |
| B3: os 4 sha256 da ADR 0014 | T1 | `test_assets_are_the_four_adr_0014_entries` |
| B3: harness nos passos 2 (completo), 7 e 9a | T3 | `sh scripts/verify-install.sh --only 2,7,9a` → 0; check `verify-install / linux-x64` |
| DoD: PR cita unit, FR, US e CT; merge pelo Emerson | T1–T4 | critérios de aceite de cada ET |

## Tarefas e PRs
| Tarefa | ET | Branch | PR | Estado |
|---|---|---|---|---|
| T1 | `code-generation/tasks/T1.md` (v2) | `aidlc/u3-gitleaks/t1-gitleaks-module` | #191 (head 041208d) | verificado em 20/10 02:20; mergeado pelo Emerson em 20/10 09:01 (f8b4068) |
| T2 | `code-generation/tasks/T2.md` (v2) | `aidlc/u3-gitleaks/t2-setup-doctor` | #192 (head 6c5b3d1) | verificado em 20/10 11:19; mergeado pelo Emerson em 20/10 11:22 (8fafff6) |
| T3 | `code-generation/tasks/T3.md` (v1) | `aidlc/u3-gitleaks/t3-verify-install` | #193 (head 8e70681) | verificado em 20/10 12:58, entregue ao Maestro (tirado do rascunho em 20/10 12:59, head inalterado; ver `T3-verificacao.md`); mergeado pelo Emerson em 20/10 13:15 (e481ef6) |
| T4 | `code-generation/tasks/T4.md` (v1) | `aidlc/u3-gitleaks/t4-secrets-gate` | #194 (head 85b35a2) | verificado em 20/10 15:20, entregue ao Maestro; mergeado pelo Emerson em 20/10 15:23 (0b4c6ec) |

Nota ET-u3-gitleaks-T1 v2 (20/10/2026 02:20 UTC-3; decisão do dono da estratégia de testes): a lista fechada de testes não cobria ramos das R7, R8 e R10 exigidos pelo mutate com 0 sobreviventes; incorporados os 6 testes do #191 (`test_write_error_without_filename_names_the_destination`, `test_timeout_error_is_retried_twice`, `test_extractfile_none_fails_extraction`, `test_rollback_removes_temporary_binary`, `test_rollback_removes_temporary_link`, `test_write_error_keeps_an_existing_destination`); corrigido 5 funções públicas. Sem mudança de código, escopo ou decisão aprovada. Verificação: `code-generation/tasks/T1-verificacao.md`.

Nota ET-u3-gitleaks-T2 v2 (20/10/2026 10:35 UTC-3): a lista fechada não tinha teste que provasse que `step_gitleaks` passa `ctx.home` a `installed_version`; o mutate deixou o sobrevivente `setup_cmd.py:170` (`installed_version(None)`), relatado em Bloqueios no #192 (head 6758783). Incluído `test_gitleaks_step_passes_ctx_home_to_installed_version` (19 testes). Sem mudança de código, escopo ou decisão aprovada. 1 rodada de correção; verificação em 20/10 11:19: `code-generation/tasks/T2-verificacao.md`.

Nota T3 (20/10/2026 12:58 UTC-3): verificada contra a ET v1 (despachada), 0 rodadas de correção. O #193 foi aberto como rascunho com "Bloqueios: nenhum", sem motivo no corpo nem no commit; não fere critério de aceite (a ET exige rascunho só quando há bloqueio e não diz nada para o caso sem bloqueio). Tirado do rascunho pelo agente em 20/10 12:59, a meu pedido, sem mudar o head; a T4.md agora diz que, sem bloqueio, o PR abre pronto para revisão. O gate `mutate` não mede o harness (shell fora de `paths.include`). Verificação: `code-generation/tasks/T3-verificacao.md`.

Checkpoint da U3 (20/10/2026 15:28 UTC-3): aprovado pelo Emerson. T1–T4 mergeadas; `main` em `0b4c6ec` (#194, 15:23). O `verify-install` da `main` passou no run 39474299206 (8 passos ok). Verificação da T4: `code-generation/tasks/T4-verificacao.md`.

## Inconsistências registradas nesta unit (para o Maestro)
| # | Onde | Achado | Resolução no plano |
|---|---|---|---|
| I15 (herdada da U1) | CT14 ("`403`/`429` sem retry") × `CURL_OPTS` do CT18 (`--retry 2`) | O `curl --retry` repete `429` (não `403`). | **Resolvida** em 2026-10-19 23:10 UTC-3: Q1 = A ("Q1 A, Q2 A."). Mantido o `--retry 2`; CT14 ajustado no texto (`install.sh`: `429` até 2 retries do `curl`, `403` nunca; Python: `4xx` sem retry). Nota no "Registro" do `contract-summary.md`. Sem código. |
| I16 | `unit-of-work.md` (U3 estende só C02 e C08) × `secrets_gate.py:125` (`shutil.which`) | Depois da U3, o gitleaks do comando único fica só em `BOB_HOME/bin`; o `bob check --gates secrets` sai `4` "missing tool". Fere o FR2.1 para esse gate. | **Resolvida** em 2026-10-19 23:10 UTC-3: Q2 = A ("Q1 A, Q2 A."). T4 entra na U3. |
| I17 | `verification-command.md` passo 2 ("`bob --version` = versão da release") × B3 "passo 2 (completo)" | A linha do `bob --version` é da U7 (a U1 marcou "2 (parcial: bob --version)"). | Para a U3, "completo" = sem fixture + `BOB_HOME/bin/gitleaks version` = 8.30.1 + `bob doctor: 0`. A linha do `bob --version` segue com a U7. |
| I18 | CT9 (reuso se `--version` "contém" 8.30.1) × pronto 2 (`gitleaks version` = 8.30.1) | Dois comandos e duas regras (contém × igual). | D5: reuso pela 1ª versão `X.Y.Z[-pre]` de `--version` igual a 8.30.1 (recusa `8.30.1-beta.1` e `8.30.10`); o harness confere `gitleaks version` = 8.30.1 (pronto literal). Conferido no binário oficial: `version` → `8.30.1`, `--version` → `gitleaks version 8.30.1`. |
| I19 | CT9 (4 erros) × fluxo real | Faltam o erro de `BOB_GITLEAKS_BASE_URL` fora da regra (CT6) e o de escrita em `BOB_HOME`. | D9: `gitleaks.url_not_allowed` e `gitleaks.write` (acréscimo compatível). Também `DEFAULT_BASE_URL`, `base_url`, `asset_url`, `installed_version`. |
| I20 | CT9 (`ASSETS` com `(system, arch)`) | Não fixa a forma de `system`. | D4: `linux`/`darwin`, minúsculo. O bloco 11 do CT18 (U8) lê a mesma tabela. |
| I21 | CT15 ("até o U3": fixture) × harness da U1 (`run_oneliner` com `env -i`) | O `env -i` não repassa `BOB_GITLEAKS_BASE_URL`; sem isso o `bob setup` do harness baixaria do GitHub. | D16/R6 da T3: `GL_URL` repassada; espelho com `gitleaks/` e `gitleaks-bad/` (igual ao item 1 do passo 14 do CT15). |
| Nota | Pedido do Maestro ("`nfr.md` leve", "`tasks/T*.md`") × convenção da U1/U2 | A U1 e a U2 usam `nfr-requirements.md` + `nfr-design.md` e `code-generation/tasks/T<n>.md`. | Seguida a convenção da U1 (forma e detalhe pedidos "como a U1"). |
| Nota | Dica do doctor (`doctor.install_gitleaks`) | Mostra o asset linux_x64 em qualquer plataforma (já era assim). | D11: fora do escopo; sem mudança. |

## Não verificado (até os PRs)
- Tempos reais com o gitleaks dentro (U3-N1, U3-N5, U3-N13): medidos no PR da T3 e no job `verify-install / linux-x64`.
- `VERIFY_REMOTE=1` com o download real do GitHub dentro do `bob setup`: só depois da 1ª release (U9). O download real em Python é provado pelo e2e manual da T1 e da T2.
- macOS e arm64: só pela tabela e pelos testes de mapeamento; matriz na U9.
- Tempo de espera do `curl --retry` com `Retry-After` no `429` (efeito aceito em Q1 = A): não medido.
- Se algum teste fora de `test_doctor.py`/`test_setup_cmd.py` roda o passo `gitleaks` real ou depende de um `BOB_HOME` real (tratado como bloqueio nas ETs T2 e T4).
