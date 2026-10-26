# U7 — u7-update-versao — Plano de geração de código

Bolt: B7 (U7, em paralelo com a U6) | Base: `main` @ `22d461a60920ab13e7b09fd654fd0e4686ba14d0` (#202, U5 fechada) | Profundidade: Minimal | Data: 2026-10-22 (UTC-3)
Aprovação do plano: **pendente** (Plan Approval conjunta da U6 e da U7, com o Emerson). Nada foi despachado.
Desenho: `../functional-design.md` (V1–V5, `--version`, U1–U6, Mensagens, Harness), `../nfr-requirements.md` (U7-N1–N13), `../nfr-design.md`. Arquivos em comum com a U6: `../shared-files-u6-u7.md`.
ADRs propostas: 0024, 0025, 0026 e 0027, em `../../u6-u7-decisions-proposta.md`. Ainda não estão no `decisions.md`.
**Pergunta de produto aberta:** `../functional-design-questions.md` Q1 (skills instaladas só em parte). **A T1 só é despachada com Q1 = A** (recomendação). Outra resposta gera a T1 v2 antes do despacho. A T2 e a T3 não dependem da resposta, só da T1 mergeada.

## Resumo
- **Constrói:**
  - `project_version` (estado das skills do projeto) e a linha `project skills:` no `bob doctor` (C08, ADR 0024);
  - `bob update` e `bob --version` (C10, CT11, ADR 0025);
  - o `--version` no passo 2 e os passos 10 e 11 do harness (CT15, ADR 0026).
- **Toca:**
  - T1: `src/bob_quality/project_version.py` (novo), `src/bob_quality/install_skills.py`, `src/bob_quality/doctor.py`, `src/bob_quality/messages.py`, `tests/test_project_version.py` (novo), `tests/test_doctor.py`, `tests/test_hermetic.py`;
  - T2: `src/bob_quality/update.py` (novo), `src/bob_quality/cli.py`, `src/bob_quality/messages.py`, `tests/test_update.py` (novo), `tests/test_usage_exit.py`, `tests/test_hermetic.py`;
  - T3: `scripts/verify-install.sh`, `tests/test_verify_install.py`, `CHANGELOG.md`.
- **Testes:**
  - T1: 12 testes novos (47 casos) e 1 ajuste (`_expected_versions` em `test_doctor.py`). `test_project_version.py`: 43; `test_doctor.py`: 81 → 85; guarda +1.
  - T2: 22 testes novos (78 casos) e 3 ajustes em `test_usage_exit.py` (79 casos, sem mudança de contagem); guarda +1.
  - T3: 7 testes novos (9 casos) e 3 ajustes. `test_verify_install.py`: 37 → 46 (ou 29 → 38 sem a U6 T3).
  - Harness: `--version` no passo 2, passos 10 e 11.

## Decisões fechadas
| # | Decisão | Origem |
|---|---|---|
| D1 | Estado das skills lido de `.agents/skills/<nome>/.bob-version` só para os nomes do manifesto empacotado (`install_skills.manifest_skill_names`). Bytes `\d+\.\d+\.\d+\n`; symlink ou arquivo irregular conta como ausente. | ADR 0024, V1–V3 |
| D2 | Instalação parcial = `mixed (<versões>, not installed)` (pendente de Q1; recomendação A). | Q1 |
| D3 | `bob doctor` ganha a linha `project skills:` como última linha do stdout, só quando os pins foram lidos. O código de saída não muda. | ADR 0024, V5 |
| D4 | `bob --version` = `argparse.Action` próprio (`nargs=0`), 2 linhas, código 0. Funciona fora de repo git. | ADR 0025 |
| D5 | `bob update` em Python (`update.py`): lê `releases/latest`; pacote ≥ última e projeto `installed` ≥ última → "já está", `0`; pacote ≥ última e projeto atrás → `run_setup`; pacote atrás → baixa `install.sh` e `SHA256SUMS` da tag, confere o sha256 e roda `sh install.sh --lang <lang>` com `BOB_VERSION=<tag>`. | ADR 0025, CT11, U1–U6 |
| D6 | Rede do `update.py` copiada do `gitleaks.py` (constantes iguais, presas por teste), sem importar nomes privados. O `dry` reporta o clone, que não bloqueia o gate. Juntar fica para depois. | ADR 0025 |
| D7 | Harness: espelho próprio `$T/mirror/upd/` montado no passo 10 com um wheel rebatizado `X.Y.(Z+1)`; passo 10 reusa projeto e `HOME` do passo 8 (`ensure_8`); passo 11 depende do 10 (`ensure_10`). Os dois dizem "não se aplica" com `VERIFY_REMOTE=1`. | ADR 0026, CT15 |
| D8 | `CHANGELOG.md` só na T3. | ADR 0027 |
| D9 | Checks exigidos: `bob / check`, `bob / cold`, `CI / pytest (3.10)`, `CI / pytest (3.12)`, `package / dist`, `verify-install / linux-x64`. Nenhuma ET toca `docs/**` nem `website/**`, então `website / build` não entra. | bolt-plan |

## Testing Contract
| Pronto / requisito | Prova automática | Onde |
|---|---|---|
| Pronto 1 (update de v-antiga para v-nova; `--version`; `.bob-version`; preservação; doctor 0) | passo 10 (R6c–R6h); `test_new_release_downloads_checks_and_runs_install_sh[en,pt-BR]`; `test_install_keeps_the_environment_and_pins_the_tag` | T3, T2 |
| Pronto 1 (pré-release ignorada; US7.2 crit. 1) | passo 10: pedidos exatos ao espelho e o comando único num projeto novo instala `latest` (R6i) | T3 |
| Pronto 2 (2ª execução: "já está", 0 mudanças) | passo 11; `test_up_to_date_prints_and_changes_nothing[2]` | T3, T2 |
| Pronto 3 (rascunho mais novo: nada muda) | passo 10/11: pedidos exatos (nenhum a `drafts/` ou `v99.1.*`) | T3 |
| Passo 2 parcial (`bob --version` = release) | `check_version 2 …` no passo 2; `test_cli_version_flag[2]`; `test_version_lines[2]` | T3, T2 |
| Linha "skills do projeto" (C08) | `test_doctor_last_line_is_the_project_skills[4]`; `test_skills_text_in_both_languages[8]`; testes 4–8 da T1 | T1 |
| Só projeto atrasado → `bob setup` | `test_old_project_runs_setup_without_download[old,none,partial]` | T2 |
| Integridade (NFR6) | `test_integrity_failures[3]`, `test_sums_first_matching_line_wins` | T2 |
| Rede (CT14) | `test_api_errors_exit_4[5]`, `test_retry_then_success`, `test_download_errors[3]`, `test_constants_match_install_sh_and_gitleaks` | T2 |
| Nunca falha calado (NFR9) | `test_releases_url_rejects[3]`, `test_bad_tag_is_an_invalid_response[7]`, `test_tmp_failures[2]`, `test_sh_failure`, `test_project_errors[2]` | T2 |
| Hermeticidade (U5-N16) | `test_u5_tests_open_no_network[tests/test_project_version.py]` e `[tests/test_update.py]` | T1, T2 |
| Qualidade | checks do PR + `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → 0 | T1–T3 |

## Passos
- [ ] P1 — `src/bob_quality/project_version.py` e `manifest_skill_names` em `install_skills.py` (T1).
- [ ] P2 — linha `project skills:` em `doctor.py` e chaves `version.*` em `messages.py` (T1).
- [ ] P3 — `tests/test_project_version.py`, ajuste e teste novo em `tests/test_doctor.py`, guarda (T1).
- [ ] P4 — verificação da T1 (Q1 respondida antes do despacho).
- [ ] P5 — `src/bob_quality/update.py` (T2).
- [ ] P6 — `src/bob_quality/cli.py` (`--version`, `update`) e chaves `cli.*`, `version.bob` e `update.*` (T2).
- [ ] P7 — `tests/test_update.py`, `tests/test_usage_exit.py`, guarda (T2).
- [ ] P8 — verificação da T2.
- [ ] P9 — `scripts/verify-install.sh`: globais, `ensure_8`/`ensure_10`, `check_version` no passo 2, espelho do update, passos 10 e 11, dispatch (T3).
- [ ] P10 — `tests/test_verify_install.py` (T3).
- [ ] P11 — `CHANGELOG.md` (T3) e verificação da unit: harness inteiro verde no PR da T3 e na `main`, e checkpoint da U7 com o Emerson.

## Tarefas
| Tarefa | ET | Passos | Base | Branch | Depende de |
|---|---|---|---|---|---|
| T1 — Versão das skills do projeto (project_version) e linha no bob doctor | `tasks/T1.md` | P1–P4 | `main` @ `22d461a` (ou a `main` do despacho) | `aidlc/u7-update-versao/t1-project-version` | Q1 = A |
| T2 — bob update e bob --version | `tasks/T2.md` | P5–P8 | `main` depois do merge da T1 (SHA a fixar) | `aidlc/u7-update-versao/t2-update` | T1 |
| T3 — Harness: passos 10 e 11 (bob update) e --version no passo 2 | `tasks/T3.md` | P9–P11 | `main` depois do merge da T2 e da U6 T3 (SHA a fixar) | `aidlc/u7-update-versao/t3-verify-install` | T2; U6 T3 (ordem sugerida) |

**Paralelismo:**
- **T1 ∥ U6 T1 ∥ U6 T2 (em paralelo).**
  - A T1 só divide com a U6 T2 `messages.py` e `test_hermetic.py`, em âncoras separadas (R-MS, R-HE).
  - Não toca `CHANGELOG.md` (ADR 0027).
- **T2 depois da T1 (em sequência).**
  - A T2 importa `project_version`.
  - As duas mexem em `messages.py` (a T2 insere depois do bloco `version.*` da T1) e em `test_hermetic.py` (a linha da T2 vem depois da linha da T1).
  - A T2 roda em paralelo com a U6 T1, a U6 T2 e a U6 T3.
- **T3 depois da T2 (em sequência), e por último na U6/U7.**
  - O passo 10 só passa com `bob update` e `bob --version` no wheel (T2), e o passo 2 só com `--version`.
  - Toca `verify-install.sh`, `test_verify_install.py` e `CHANGELOG.md`, os mesmos da U6 T3. A ordem sugerida põe a U6 T3 antes (`shared-files-u6-u7.md`). A ET traz as variantes A (sem a U6 T3) e B (com ela).
- **Nenhuma ET da U7 roda em paralelo com outra ET da U7.**

## Mecanismo de entrega
Igual à U5 e à U6:
- O Maestro despacha cada ET, com o HEAD da base anotado, para um agente de código.
- O agente abre 1 PR para `main`.
- Eu verifico o PR contra a ET (`tasks/T<n>-verificacao.md`, escrito na hora da verificação).
- O Emerson faz o merge.

Antes do despacho da T2 e da T3, eu fixo o SHA da base e reconfiro as âncoras: `messages.py`, `test_hermetic.py` e `cli.py` na T2; `verify-install.sh` e `test_verify_install.py` na T3. Nada é despachado por este plano.

## Riscos
| # | Risco | Mitigação |
|---|---|---|
| R1 | Q1 sem resposta segura a T1 e, por tabela, a T2 e a T3. | Q1 vai para o Emerson junto com a Plan Approval. Outra resposta muda só os testes 7, 8, 9 e 11 da T1 (T1 v2). |
| R2 | O passo 10 reinstala um venv inteiro (pip e `npm ci`) e pode estourar o teto. | Alvo ≤ 300 s só para o `bob update`, como no passo 2. O harness inteiro fica ≤ 900 s: hoje ~232 s, + ≤ 180 s (U6), + ≤ 300 s, + ≤ 30 s. |
| R3 | O wheel rebatizado pode divergir do real (RECORD, METADATA). | `rebrand_wheel` regrava o `RECORD` e só troca a versão. `test_rebrand_wheel_changes_only_the_version` prende o formato, e o passo 10 confere `bob --version` com a v-nova. |
| R4 | Clone de código de rede entre `update.py` e `gitleaks.py`. | O `dry` só reporta. As constantes ficam presas por teste (`test_constants_match_install_sh_and_gitleaks`). Juntar entra no backlog. |
| R5 | `run_bob` copia o laço de repasse de variáveis do `run_oneliner`. | Fora de `src/` (sem `dry`). O teste 6 da T3 prende o ambiente. |
| R6 | Conflito com a U6 T3 no harness, no teste do harness e no CHANGELOG. | Regras R-CL, R-VI1, R-VI2 e R-TV, e as variantes A/B na T3. |
| R7 | O `bob update` roda o `install.sh` novo no `HOME` do passo 8: com a U6, o passo `perfil` escreve `~/.profile` ali. | O passo 10 não confere o `HOME` além de `current` e do launcher. O `digest` é do projeto. |
| R8 | `VERIFY_REMOTE=1` não prova o `bob update` contra o GitHub real. | Os passos 10 e 11 dizem "não se aplica", como o 9a e o 9b. A prova real fica no release-check da U9. |

## Autochecagem
- [x] Toda regra V1–V5, `--version` e U1–U6 tem tarefa e teste.
- [x] Todo pronto da U7 tem prova automática (Testing Contract).
- [x] Referências arquivo:linha conferidas em `22d461a` (leitura remota, sem clone). Âncoras deslocadas pela T1/U6 descritas por texto.
- [x] Cada ET tem passo 0 com resultado numérico, diz se toca `CHANGELOG.md` (só a T3) e se pode rodar em paralelo.
- [x] Literais e mutantes tratados em cada ET. Os gates `mutate`/`crap`/`dry` cobrem só `src/` (`bob.yaml: paths.include: [src]`). Shell é provado por teste e pelo harness.
- [x] Nenhuma meta rebaixada; nenhum waiver novo.
