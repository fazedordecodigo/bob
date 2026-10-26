# U1 — Rastreabilidade (u1-walking-skeleton)

Escopo: só esta unit. Estado: **concluída**: T1 a T6 mergeadas (última #190, 387b0b6) e checkpoint aprovado pelo Emerson em 2026-10-19 22:44 UTC-3. Base `main` @ `053dcaab7796f8885c4830ee3a5f6bf1fc75d65a`.

## FR/US → tarefa → prova
| FR / US | Tarefa | Prova (teste ou passo do harness) |
|---|---|---|
| FR1.1 (comando único) | T4, T5 | `test_full_install_via_the_mirror`, `test_curl_pipe_sh_works`; passo 2 |
| FR1.2 (pré-requisitos antes de escrever) | T4 | `test_failed_prerequisite_writes_nothing` (11 casos × 2 idiomas), `test_missing_sha_tool`; passo 1 |
| FR1.3 (venv por usuário, launcher) | T4 | `test_full_install_via_the_mirror` (layout CT5), `test_foreign_local_bin_bob_is_kept`; passo 7 |
| FR1.4 (última release; `BOB_VERSION` só testes) | T4 | `test_bob_version_pins_the_tag`, `test_api_error_says_try_again_later`, `test_bob_version_is_offered_only_in_its_own_error`; passo 2 (pedidos ao espelho) |
| FR1.5 (`bob setup` → `bob doctor`) | T3 | `test_all_steps_pass_and_doctor_0_exits_0`, `test_doctor_4_makes_setup_exit_4`; passo 2 |
| FR2.4 (não mexe nos manifestos do projeto) | T3, T5 | `test_setup_does_not_touch_the_project_package_files`; passo 8 |
| FR3.1–FR3.3 (skills só em `.agents/skills`, do pacote) | T1, T2, T3 | `test_wheel_ships_the_plugin_skills_manifest_and_license`, `test_install_creates_only_agents_skills`, `test_default_source_installs_the_three_bob_skills`; passo 4 |
| FR3.4 (posse) | T2, T3 | `test_unmarked_folder_is_preserved_and_reported`, `test_foreign_folder_is_preserved_byte_for_byte`, `test_retired_owned_skill_is_removed`, `test_skills_step_reports_installed_preserved_and_warnings`; passo 8 |
| FR7.1, FR7.2 (erros CT1, en/pt-BR) | T3, T4 | `test_first_failed_step_stops_and_prints_a_partial_summary`, `test_setup_messages_exist_in_both_languages`, `test_usage_errors_exit_4` |
| FR7.3 (Node fora da faixa) | T4, T5 | `test_failed_prerequisite_writes_nothing[node_out-*]`; passo 1 |
| US1.1 crit. 1–3, 6 | T4, T5 | passos 2, 7 |
| US1.1 crit. 4 (sem sudo) | T4, T5 | passo 3; `test_install_sh_never_mentions_sudo` |
| US1.2 | T4, T5 | passo 1 |
| US2.1 | T2, T5 | passo 4 (pasta); verificação manual por release (CT13) para a leitura pelo agente |
| US6.1 | T3, T4 | `test_full_install_via_the_mirror`, `test_all_steps_pass_and_doctor_0_exits_0` |
| US1.4 crit. 1 (contribui) | T5 | passo 8 (vitest 4.1.0 do projeto, `bob doctor: 0`) |
| US3.2 (skills alheias; contribui) | T2, T5 | passo 8 |
| US7.2 crit. 1 (contribui) | T5 | espelho: pré-release e rascunho fora do `latest`; passo 2 (pedidos) |
| NFR1 | T5 | passo 2 (≤ 300 s) |
| NFR2 | T4 | passo 2 |
| NFR3 | — | U9 (matriz). U1 só Linux x64 |
| NFR4 | T2, T3, T4, T5 | passo 7 |
| NFR5 | T2, T3, T5 | passo 8 |
| NFR6 (wheel) | T4, T5 | `test_tampered_wheel_exits_4_and_creates_no_version`; passo 9b |
| NFR7 | T4, T5 | passo 3 |
| NFR9 | T3, T4 | testes por idioma |

## Pronto da U1 → prova
| Pronto | Prova |
|---|---|
| 1 | passo 2 (`  bob doctor: 0`), gitleaks pela fixture do harness (D24) |
| 2 | passo 2 (`tempo ≤ 300 s`) |
| 3 | passo 4 |
| 4 | passo 1 |
| 5 | passo 3 |
| 6 | passo 7 |
| 7 | passo 8 |
| 8 | passo 9b |
| 9 | `tests/test_package.py::test_wheel_ships_the_plugin_skills_manifest_and_license` |

## Tarefas e PRs
| Tarefa | ET | Branch | PR | Estado |
|---|---|---|---|---|
| T1 | `code-generation/tasks/T1.md` | `aidlc/u1-walking-skeleton/t1-wheel-plugin` | [#184](https://github.com/fazedordecodigo/bob/pull/184) (head `cfb3239`) | mergeado em 19/10 09:12 (80cf976) |
| T2 | `code-generation/tasks/T2.md` | `aidlc/u1-walking-skeleton/t2-project-skills` | [#185](https://github.com/fazedordecodigo/bob/pull/185) (mergeado 11:45, baa77da) + [#186](https://github.com/fazedordecodigo/bob/pull/186) (largura de linha) | mergeado em 19/10 13:06 (358e60e) |
| T3 | `code-generation/tasks/T3.md` | `aidlc/u1-walking-skeleton/t3-bob-setup` | #187 (head 9f7fc28) | mergeado em 19/10 16:50 (28fba5c) |
| T4 | `code-generation/tasks/T4.md` | `aidlc/u1-walking-skeleton/t4-install-sh` | #188 (head 523d184) | mergeado em 19/10 18:50 (b00a2fa) |
| T5 | `code-generation/tasks/T5.md` | `aidlc/u1-walking-skeleton/t5-verify-install` | #189 (head d17bc2c) | mergeado em 19/10 20:45 (4063e01) |
| T6 | `code-generation/tasks/T6.md` | `aidlc/u1-walking-skeleton/t6-verify-install-ci` | #190 (head 1abb835) | mergeado em 19/10 22:39 (387b0b6); run na main [39354654559](https://github.com/fazedordecodigo/bob/actions/runs/39354654559) verde, linux-x64 em 2m50s |

## Inconsistências registradas nesta unit (para o Maestro)
| # | Onde | Achado | Resolução no plano |
|---|---|---|---|
| I10 | CT4 regra 6 ("cópia com `.bob-version` em `.claude/skills`…") × ADR 0009 / `component-interfaces.md` §2 ("cópia do bob … gera aviso") | O instalador antigo não gravava `.bob-version`; pela regra 6 literal, as cópias antigas em `.claude/skills`/`.github/skills` nunca seriam achadas. | D9: duplicata = pasta com nome do manifesto e `SKILL.md`, com ou sem marcador. Só aviso. |
| I11 | CT3 ("um passo não imprime"; `doctor` como passo 8 de `STEPS`) × FR1.5 e `npm_tools.install_npm_dependencies` (imprime) | O código do doctor vira o código final e a saída dele é impressa; o `npm ci` já imprime o fallback. | D11/D12: doctor fora de `STEPS`, como fase final fixa; o passo `npm` deixa passar a saída existente; progresso e avisos impressos pelo `run_setup`. U3/U4/U5 continuam só inserindo tuplas em `STEPS`. |
| I12 | 2.6 / CT15 (`PATH=/usr/bin:/bin:<node>:<python>`) × runner | No `ubuntu-latest`, `/usr/bin` tem `python3` do sistema e pode ter outro `node`; com essa ordem, o harness não usa o Node/Python escolhidos. | D23: `<NODE_DIR>:<PY_DIR>` antes de `/usr/bin:/bin`; `PY_DIR` = `bin` do Python base, nunca um venv. |
| I13 | CT4 `SkillsResult` | A regra 3 pede aviso por pasta sem marcador, mas o `SkillsResult` não distingue "sem marcador" de "alheia". | D6: campo novo `unmarked: tuple[Path, ...] = ()` (acréscimo compatível). |
| I14 | CT18 (`STEPS` com `perfil`; `PROFILE_LINE`) × U1 sem `perfil` | O passo e a linha são do U6. | D17: U1 declara `STEPS` sem `perfil` e sem `PROFILE_LINE`; o U6 acrescenta os dois (o teste de paridade do U8 lê depois do U6). |
| I15 | CT14 ("`403`/`429` sem retry") × `CURL_OPTS` do CT18 (`--retry 2`) | O `curl --retry` trata `429` como transitório e tenta de novo. | Mantido o `CURL_OPTS` do CT18 (fonte única). Efeito: até 2 tentativas extras no limite de taxa. Para o Maestro decidir se o CT14 é ajustado. |
| Nota | CT2 (`download`) × CT14 (`404` "release incompleta") | O CT2 tem uma mensagem só para `download`. | D19: `404` tem mensagem própria (`download_missing`). |
| Nota | CT1 (aviso `<prefixo>: <passo>: aviso: <texto>.`) × `component-interfaces.md` §2 (aviso de duplicata sem `aviso:`) | Formato diferente. | T3: aviso impresso no formato CT1 (`bob setup: skills: aviso: achei uma cópia…`). |
| Nota | CT6 (`BOB_HOME` relativo no `install.sh` com passo `launcher`) | Checado no início (antes de `projeto`), mas a mensagem mantém o id `launcher` do CT6. No `bob setup` o id é `projeto`. | T3/T4 conforme. |

## Não verificado (até os PRs)
- Tempos reais (U1-N1, U1-N12, U1-N13): medidos no PR da T5.
- `python -m build` com os symlinks de `plugin/` no CI (`ubuntu-latest`, setuptools da hora do build): conferido só no box (setuptools 84.0.0).
- Se algum teste existente varre `src/` e passa a ver as skills em dobro por `plugin/skills` (risco tratado na T1 como bloqueio).
- `bob setup` com o wheel real, dentro do venv do `install.sh` (e2e manual da T4 e passo 2 da T5).
- Comportamento real do GitHub (302, limite de taxa, `latest` com pré-release): só com `VERIFY_REMOTE=1`, depois da primeira release (U9).
