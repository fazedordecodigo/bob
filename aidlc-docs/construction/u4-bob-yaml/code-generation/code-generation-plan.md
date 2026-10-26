# U4 — u4-bob-yaml — Plano de geração de código

Bolt: B4 (U4) | Base: `main` @ `0b4c6ec` (#194, U3 fechada) | Profundidade: Minimal | Data: 2026-10-20 (UTC-3)
Aprovação do plano: **pendente** (Plan Approval do Emerson).
Desenho: `../functional-design.md` (R1–R10), `../nfr-requirements.md` (U4-N1–N14), `../nfr-design.md`.
Perguntas: nenhuma. Toda decisão abaixo sai de doc aprovado (CT7, CT3, CT15, ADR 0015/0017, unit-of-work) ou é técnica e reversível (D3, D4, D5).
Atualização 2026-10-20 21:40 UTC-3: o passo 0 da T2 confirmou o risco R1 (PR #196, `crap` saiu `4` sem código). Q1 em `../code-generation-questions.md`, respondida pelo Emerson às 21:18 (UTC-3): opção A (D14). Entra a T1b antes da T2 (passo P9). Aprovação da T1b: pendente nesse momento (aprovada às 21:42; linha seguinte). Emendas ao CT7 e à ADR 0015 em rascunho: `tasks/T1b-emenda.md` (aplicadas E1–E3 às 21:50).
Atualização 2026-10-20 21:50 UTC-3: o Emerson aprovou às 21:42 (UTC-3): "Aprovo a T1b e as emendas E1 a E3, com a T1c separada para a E4. Pode despachar a T1b." (D15). A T1b foi despachada às 21:47 sobre `0d85510` para o agente `bc-2343a08e-5bb5-5621-8b6b-b94b3c494a0e` (anexos em `/workspace/dispatch/u4-t1b/`). E1–E3 aplicadas (ADR 0015 linhas 220-221; CT1 linhas 53-54; CT7 linhas 322 e 324). A E4 (docs de exit codes) virou a T1c (`tasks/T1c.md`, passo P10), depois da T3.
Atualização 2026-10-20 23:50 UTC-3: PR #197 da T1b (head `953f91b`, 1 commit sobre `0d85510`, 6 arquivos, +239/−2) verificado contra a ET v1 e aprovado para checkpoint, sem rodada de correção: 6/6 checks verdes, `4486 passed` em 3.10 e 3.12, passo 0 e e2e conforme a ET (`tasks/T1b-verificacao.md`). P9 fica aberto até o merge, que é do Emerson. `tasks/T2.md` (v3) foi preparada com os números de `messages.py` no head `953f91b` e o esperado do passo 0 com a T1b; o SHA da base da T2 se fixa depois do merge.
Atualização 2026-10-21 10:47 UTC-3: o Emerson mergeou o PR #197 (T1b) às 10:37 (merge commit `637ec39dfe55db138553b827a6bb8a72905476f1`); P9 fechado. A T2 v3 teve a base fixada em `637ec39` às 10:45, com o passo 0 endurecido de ≠ 4 para `EXIT:0` a pedido do Maestro (já no `tasks/T2.md`), e foi retomada às 10:47 por reply ao agente `bc-691329cf-9c32-599d-b0e2-34a6b6196ac0` no mesmo PR #196 (run `run-42340d21-0e04-4577-b9c9-a3cdd57990f9`; anexos em `/workspace/dispatch/u4-t2/`).
Atualização 2026-10-21 12:2x UTC-3: PR #196 da T2 v3 (head `0990f84`; histórico `d90c24d` → merge `88248c7` de `637ec39`, sem force-push → `0990f84`; 4 arquivos, +340/−1) verificado e aprovado para checkpoint, sem rodada de correção: passo 0 `EXIT:0`, 6/6 checks verdes, `4513 passed` em 3.10 e 3.12 (4486 + 15 casos novos + 12 de `_MESSAGES`), e2e conforme a ET (`tasks/T2-verificacao.md`). P2–P4 ficam abertos até o merge, que é do Emerson. `tasks/T3.md` v2 (v1 em `tasks/T3-v1.md`): base "main após o merge da T2 (SHA a fixar)", números conferidos em `0990f84`.

## Resumo
- Constrói: `bob_quality.init_config` (C05, CT7: `write_default_config`, `render_config`), o passo `bob.yaml` do `bob setup` (CT3 ordem 6) e o passo 5 do harness, com a preservação do `bob.yaml` e de `.bob/waivers.yaml` conferida nos passos 7 e 8.
- Toca: `src/bob_quality/init_config.py` (novo), `src/bob_quality/setup_cmd.py`, `src/bob_quality/messages.py`, `src/bob_quality/check.py` (T1b), `scripts/verify-install.sh`, `tests/test_init_config.py` (novo), `tests/test_setup_cmd.py`, `tests/test_check_dispatch.py` (T1b), `tests/test_check_report.py` (T1b), `tests/test_mutation_branches.py` (T1b), `tests/test_verify_install.py`, `CHANGELOG.md`; e, na T1c (só docs), `docs/exit-codes.md`, `website/i18n/pt-BR/docusaurus-plugin-content-docs/current/exit-codes.md`, `docs/adr/0003-exit-codes.md`, `README.md`, `README.pt-BR.md`.
- Testes: 23 novos na T1 (24 na v2), 5 novos na T1b (10 casos; mais 2 ajustes: imports de `test_check_dispatch.py` e 2 linhas em `test_mutation_branches.py`), 10 novos na T2 (mais 3 ajustes em lista fechada), 5 novos na T3 (mais 3 ajustes); passos 5, 7 e 8 do harness; e2e manual na T1b e na T2. A T1c não tem teste novo (verificação por `website / build`, `test_gate_publications.py`, `test_skills_contract.py` e `grep`).

## Decisões fechadas
| # | Decisão | Origem |
|---|---|---|
| D1 | Interface CT7 sem mudança de nome; acréscimos `CONFIG_NAME` e `render_config` | CT7, functional-design |
| D2 | Regra de `include` = CT7 passos 1–5 (`[src]` › pastas em ordem de código › `["."]` com ou sem código na raiz) | CT7, ADR 0015 |
| D3 | Lista do git por `suite_fingerprint._listed_files` (reuso; `-co --exclude-standard -z`, igual ao argv do CT7 com `-c` ≡ `--cached`, `-o` ≡ `--others`). Sufixos de `config._SUFFIX_LANGUAGE` e exclusão por `config._excluded`, sem cópia das tabelas (DRY). | CT7 passos 1–3, DoD (dry) |
| D4 | Só contam arquivos regulares que existem e não são link (I23) | CT7 passo 2, FR4.4 |
| D5 | Itens de `include` sem aspas quando o YAML devolve o mesmo texto; senão, aspas JSON (I22). `"."` sempre entre aspas. | CT7, FR4.4 |
| D6 | Escrita: `bob.yaml.tmp-<pid>` → `load_config(tmp, project)` → `os.replace`; `unlink` em qualquer exceção | CT7 passo 6, ADR 0017 |
| D7 | `bob.yaml` existente (arquivo, link, pasta) → `preserved` antes de qualquer outra ação | CT7, ADR 0017, FR4.6 |
| D8 | Passo `bob.yaml` em `STEPS` depois de `skills`. `.bob/waivers.yaml`, quando existe, entra como preservado no resumo (I24). | CT3, pronto 4 |
| D9 | `bob.yaml` preservado só aparece na linha `  preserved:`; não vira aviso (I26) | CT3 |
| D10 | Falhas: `ConfigError` → `setup.bob_yaml_invalid` (texto do CT3); `ToolError` → `_failed_reason`; `OSError` → `setup.bob_yaml_write` (I28). Todas saem `4`. | CT3, CT1 |
| D11 | Harness: passo 5 reusa `S2_HOME` (via `ensure_2`) e roda 3 projetos novos. Confere o texto do `bob.yaml` por `cmp` com `expected_bob_yaml`, o aviso em en (I27) e `bob check --base HEAD --gates crap,dry,deps` ≠ 4, pelo launcher `$S2_HOME/.local/share/bob-quality/bin/bob`. | CT15, verification-command passo 5 |
| D12 | Passos 7 e 8 ganham as linhas `  preserved:`; o passo 8 ganha `bob.yaml` e `.bob/waivers.yaml` no projeto, com conferência por sha | verification-command passos 7 e 8 |
| D13 | 3 tarefas sequenciais, 1 PR cada; checks exigidos: `check`, `pytest (3.10)`, `pytest (3.12)`, `dist`, `cold`, `verify-install / linux-x64` (com a T1b e a T1c: 5 tarefas, T1 → T1b → T2 → T3 → T1c; a T1c soma o check `website / build`) | bolt-plan B4, U3 |
| D14 | Sem código a medir (`detect_languages(cwd, include, exclude)` vazio), `crap` e `coverage` ficam ⏭️ `not_run` com `check.no_code` ("no code to measure" / "nenhum código a medir") e contribuem `0`; decidido no laço de `check._measure`, sem rodar ferramenta e sem comparar texto de erro. Com código, erro real de coverage segue `4`. `dry` e `deps` não mudam (saem `0` sem código, pela leitura). | Q1 = A (Emerson, 2026-10-20 21:18 UTC-3); T1b |
| D15 | T1b e emendas E1–E3 aprovadas; a E4 (docs de exit codes) sai numa ET separada, a T1c, depois da T3. Ordem: T1b → T2 v3 (no #196) → T3 → T1c. A T1c não toca `CHANGELOG.md` (só docs; a T1b já registrou o comportamento) e não toca arquivo da T2 nem da T3. | Emerson, 2026-10-20 21:42 UTC-3 |

## Testing Contract
| Pronto / requisito | Prova automática | Onde |
|---|---|---|
| Pronto 1 (`[src]`, `[app]`, `["."]`, `bob check` ≠ 4) | passo 5; `test_write_creates_src_when_src_has_code`, `test_write_lists_every_code_folder_in_code_point_order`, `test_code_only_in_the_root_is_dot`, `test_no_code_is_dot_and_created_no_code`, `test_generated_files_pass_load_config` | T3, T1 |
| Pronto 2 (aviso só no 3º) | passo 5; `test_bob_yaml_step_warns_when_there_is_no_code`, `test_bob_yaml_step_no_code_warning_reaches_the_output` | T3, T2 |
| Pronto 3 (chaves = README, sem `languages`) | `test_render_config_is_the_ct7_text`; passo 5 (`cmp`); `test_harness_expects_the_ct7_text` | T1, T3 |
| Pronto 4 (mesmo hash e resumo lista os dois) | passo 8; `test_existing_bob_yaml_is_preserved`, `test_bob_yaml_step_lists_existing_waivers`, `test_bob_yaml_step_reaches_the_summary` | T3, T1, T2 |
| NFR4 (2ª execução sem mudança) | passo 7; `test_second_write_is_preserved_and_changes_nothing` | T3, T1 |
| Atomicidade (CT7 passo 6) | `test_validates_the_temporary_file_before_renaming`, `test_config_error_removes_the_temporary`, `test_rename_error_removes_the_temporary`, `test_write_error_leaves_no_temporary` | T1 |
| Erros com saída 4 | `test_bob_yaml_step_invalid_config_fails`, `…_git_failure_fails`, `…_write_error_fails`, `…_failure_stops_setup` | T2 |
| Sem código → `crap`/`coverage` ⏭️ e `bob check` 0 (Q1 = A) | `test_measure_skips_crap_and_coverage_without_code`, `test_measure_finds_no_code_outside_the_include_rule`, `test_a_repo_without_code_skips_crap_and_coverage_and_exits_0`; e2e da T1b (7 `EXIT:0`) | T1b |
| Erro real de coverage com código segue `4` | `test_measure_runs_crap_and_coverage_when_there_is_code`, `test_a_missing_coverage_file_keeps_the_coverage_gate_a_tool_failure`, `test_a_missing_coverage_file_stays_a_tool_failure` (existente, sem edição) | T1b |
| Docs de exit codes dizem "no code to measure" → `0` (E4) | `website / build` (`npm run build` com `onBrokenLinks`/`onBrokenAnchors: 'throw'`, `npm test`), `test_gate_publications.py`, `test_skills_contract.py` (âncora `exit-4`), `grep` dos textos D1–D7 | T1c |
| Qualidade (U4-N13) | checks do PR + `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → 0 | T1–T3, T1b |

## Passos
- [ ] P1 — `src/bob_quality/init_config.py`: CT7 + R1–R7 (T1).
- [ ] P2 — `src/bob_quality/messages.py`: 6 chaves `setup.*` en/pt-BR (T2).
- [ ] P3 — `src/bob_quality/setup_cmd.py`: `step_bob_yaml` + `STEPS` (T2).
- [ ] P4 — testes de P1 (T1); de P2 e P3 (T2).
- [ ] P5 — `scripts/verify-install.sh`: passo 5, `expected_bob_yaml`, passos 7 e 8, `STEP_IDS`, `run_selected`, ajuda (T3).
- [ ] P6 — `tests/test_verify_install.py` (T3).
- [ ] P7 — `CHANGELOG.md` em cada tarefa (en e pt-BR, no topo de `## Unreleased`).
- [ ] P8 — verificação da unit: harness inteiro verde no PR da T3 e na `main`; checkpoint da U4 com o Emerson.
- [x] P9 — `src/bob_quality/check.py` (`_NEEDS_CODE`, `_skipped_without_code`, laço de `_measure`) e `messages.py` (`check.no_code`), com testes e `CHANGELOG.md` (T1b; D14). Vem antes de P2–P4. Implementado no PR #197 (verificado às 23:50); mergeado em 21/10 10:37 (`637ec39`).
- [ ] P10 — docs: `docs/exit-codes.md`, espelho pt-BR em `website/i18n`, `docs/adr/0003-exit-codes.md`, `README.md` e `README.pt-BR.md` dizem que, sem código a medir, `crap` e `coverage` ficam `not_run` ("no code to measure") com exit 0 (T1c; D15; emenda E4). Vem depois de P5–P6.

## Tarefas
| Tarefa | ET | Passos | Base | Branch | Depende de |
|---|---|---|---|---|---|
| T1 — Gerador do bob.yaml (init_config.py) | `tasks/T1.md` | P1, P4, P7 | `main` @ `0b4c6ec` | `aidlc/u4-bob-yaml/t1-init-config` | — |
| T1b — Gates crap e coverage sem código a medir saem 0 | `tasks/T1b.md` (v1; aprovada às 21:42; despachada às 21:47 para `bc-2343a08e`; PR #197, head `953f91b`, verificado às 23:50, mergeado em 21/10 10:37 como `637ec39`) | P9, P7 | `main` @ `0d85510` | `aidlc/u4-bob-yaml/t1b-no-code` | T1 |
| T2 — Passo bob.yaml no bob setup | `tasks/T2.md` (v3) | P2, P3, P4, P7 | `main` @ `637ec39` (T1b mergeada, #197) | `aidlc/u4-bob-yaml/t2-setup-step` (PR #196; retomada em 21/10 10:47 pelo agente `bc-691329cf`, run `run-42340d21-0e04-4577-b9c9-a3cdd57990f9`; head `0990f84`, verificado às 12:2x, aguardando merge) | T1, T1b |
| T3 — Harness: passo 5 e preservação do bob.yaml/waivers | `tasks/T3.md` (v2) | P5, P6, P7 | `main` após o merge da T2 (SHA a fixar) | `aidlc/u4-bob-yaml/t3-verify-install` | T2 |
| T1c — Documentar o not_run "no code to measure" com exit 0 | `tasks/T1c.md` (v1) | P10 | `main` após o merge da T3 (SHA a fixar) | `aidlc/u4-bob-yaml/t1c-docs-no-code` | T1b, T3 |
Por que em sequência: a T2 importa `init_config`, e a T3 só passa no harness com o passo do `bob setup` já no wheel. A T1b vem antes da T2 porque o passo 0 da T2 (e o pronto 1: `bob check` ≠ 4 no projeto sem código) depende dela. Cada tarefa toca arquivos diferentes, exceto `CHANGELOG.md` (entrada nova no topo) e `messages.py` (T1b insere `check.no_code` perto de `check.gate_not_implemented`; a T2 insere `setup.*` depois de `setup.warn_duplicate`, sem conflito de linha). A T1c vem por último porque só documenta o que a T1b entrega e não divide arquivo com a T2 nem com a T3 (sem `CHANGELOG.md`).

## Mecanismo de entrega
Igual à U3: o Maestro despacha cada ET (com o HEAD da base anotado) para um agente de código; o agente abre 1 PR para `main`; eu verifico o PR contra a ET (`tasks/T<n>-verificacao.md`); o Emerson faz o merge. Nada é despachado por este plano.

## Riscos
| # | Risco | Mitigação |
|---|---|---|
| R1 | **Confirmado** em 2026-10-20 (passo 0 da T2, PR #196, `0d85510`): `bob check --base HEAD --gates crap` saiu `4` num projeto sem código (`coverage.py: No data to report.`). Causa: `coverage json` sai ≠ 0 → `ToolError` (`tools.py:176-177`) → `python_probe.py:39-43` → `not_run` com `CONFIG_OR_TOOL`. Pela leitura, o gate `coverage` também sai `4` (`coverage_gate.py:156-159`, `:239-245`); `dry` e `deps` saem `0`. | Q1 = A (Emerson, 21:18 UTC-3) → T1b (D14) antes da T2. A T1b mede os 4 gates no passo 0 e para se `dry` ou `deps` saírem ≠ 0. A meta não muda. |
| R2 | Passo 5 aumenta o tempo do harness | Reusa `S2_HOME`; alvo U4-N10 ≤ 180 s, medido; teto U4-N11 ≤ 900 s mantido. |
| R3 | Nome de pasta que o YAML lê diferente (I22) | D5 + `test_render_config_quotes_items_that_are_not_plain` + `test_generated_files_pass_load_config`. |
| R4 | Reuso de função privada (`_listed_files`, `_SUFFIX_LANGUAGE`, `_excluded`) | Teste de contrato `test_files_come_from_the_suite_fingerprint_listing`; se mudarem, a suíte quebra. |

## Autochecagem
- [x] Toda regra R1–R10 tem tarefa e teste (`../trace.md`).
- [x] Todo pronto da U4 (1–4) tem prova automática (Testing Contract).
- [x] Referências arquivo:linha conferidas em `0b4c6ec`.
- [x] Cada ET traz o texto literal das lições (a), (b) e (c), e a T2 traz a receita completa do e2e (d).
- [x] Os 6 checks estão nomeados em cada ET (inclusive na T1b); a T1c nomeia também `website / build` (o PR toca `docs/**` e `website/**`).
- [x] A T1b traz as lições (mutate em Bloqueios, skip/only, colunas com CHANGELOG, PR pronto sem bloqueio, bloqueio após o PR só no corpo, literais de mutante equivalente) e referências conferidas em `0d85510`.
- [x] A T1c traz as mesmas lições, a lista fechada de 5 arquivos, os textos D1–D7 exatos (en e pt-BR) e a verificação dos docs (build do site com `onBrokenLinks`/`onBrokenAnchors: 'throw'`, `npm test`, `test_gate_publications.py`, `test_skills_contract.py` e a âncora `docs/exit-codes.md#exit-4`), conferidos em `0d85510`.
- [x] Nenhuma meta rebaixada; nenhum waiver novo.
- [x] Perguntas: Q1 (`../code-generation-questions.md`) respondida pelo Emerson às 21:18 (UTC-3); nenhuma outra aberta.
