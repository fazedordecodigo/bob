# U6 — u6-perfil-shell — Plano de geração de código

Bolt: B6 (U6, em paralelo com a U7) | Base: `main` @ `22d461a60920ab13e7b09fd654fd0e4686ba14d0` (#202, U5 fechada) | Profundidade: Minimal | Data: 2026-10-22 (UTC-3)
Aprovação do plano: **pendente** (Plan Approval conjunta da U6 e da U7, com o Emerson). Nada foi despachado.
Desenho: `../functional-design.md` (P1–P10), `../nfr-requirements.md` (U6-N1–N11), `../nfr-design.md`. Arquivos em comum com a U7: `../shared-files-u6-u7.md`.
ADRs propostas: 0021, 0022, 0023, 0026 e 0027, em `../../u6-u7-decisions-proposta.md`. Ainda não estão no `decisions.md`.
Perguntas: nenhuma de produto.
**Aviso ao Maestro antes do despacho da T1 e da T2:** CT6 e CT16 sobem para v2 (ADR 0021, `already-marked:<arquivo>`).
**Adendo T4 (2026-10-23 22:30, UTC-3):** o checkpoint da U6 foi aprovado pelo Emerson em 23/10 22:16 (UTC-3): "Aprovo o checkpoint da U6. Fechar a U6-N5 com a ET U6 T4, depois da U7 T3." A T4 fecha a parte "arquivos fora do `HOME` = 0" da U6-N5 (L2 do checkpoint), sem rebaixar a meta. Opção A: snapshot antes e depois. Plan Approval da T4: **aprovado pelo Emerson** em 23/10 22:57 (UTC-3). Base do despacho: `main` @ `4d1603323ddc13714fa50b5e98487cb0957c7f20` (#208 U7 T3 mergeada).

## Resumo
- **Constrói:**
  - o passo `perfil` do `install.sh` (CT16), com `PROFILE_LINE` como fonte única;
  - `BOB_INSTALL_PROFILE` para o `bob setup`, e a linha `perfil do shell:` no resumo (CT3);
  - o passo 13 do harness (CT15).
- **Toca:** `scripts/install.sh`, `tests/test_install_sh.py`, `src/bob_quality/setup_cmd.py`, `src/bob_quality/messages.py`, `tests/test_setup_cmd.py`, `tests/test_hermetic.py`, `scripts/verify-install.sh`, `tests/test_verify_install.py` e `CHANGELOG.md`.
- **Testes:**
  - T1: 8 testes novos (15 casos) e 4 ajustes. `test_install_sh.py` vai de 64 para 79.
  - T2: 4 testes novos (21 casos), 5 tuplas em `_MESSAGES` (+10 casos) e 1 ajuste na guarda. `test_setup_cmd.py` vai de 166 para 197.
  - T3: 5 testes novos (8 casos) e 3 ajustes. `test_verify_install.py` vai de 29 para 37.
  - T4: 2 testes novos (5 casos), 3 helpers, 0 ajustes. `test_install_sh.py` vai de 79 para 84.
  - Harness: passo 13.

## Decisões fechadas
| # | Decisão | Origem |
|---|---|---|
| D1 | `PROFILE_LINE` na linha 5 do `install.sh`. A marca e a linha para colar saem dela por expansão. O literal da linha aparece 1 vez no script. | ADR 0022, CT16 |
| D2 | O passo `perfil` vai entre `launcher` e `setup`. Ele nunca falha, e o aviso vai para o stdout. `<erro>` = texto depois do último `": "` da 1ª linha do stderr do shell. | CT2, CT16, ADR 0022 |
| D3 | `already-marked:<arquivo>`. | ADR 0021 |
| D4 | Resultado passado por `export BOB_INSTALL_PROFILE` antes do `exec` (sem `env`). | ADR 0022 |
| D5 | `_profile_text` puro. A linha sai em `_summary`, antes da linha do doctor, e também no resumo parcial. Valor inválido não gera linha. | ADR 0023, CT3 |
| D6 | Guarda de rede: `-k "hook or profile"` (troca a linha 14 de `test_hermetic.py`, sem criar parâmetro novo, então sem id repetido). | U5-N16, shared-files R-HE |
| D7 | Passo 13: 5 casos × 2 execuções, `BOB_HOME` do passo 2, `ensure_2` dentro do passo e root recusado. `run_oneliner` ganha `${10}` (`SHELL`) e `${11}` (`BOB_HOME`). A linha do perfil vem do `install.sh` (`profile_line`). | ADR 0026, CT15 |
| D8 | `CHANGELOG.md` só na T3. | ADR 0027 |
| D9 | Checks exigidos: `bob / check`, `bob / cold`, `CI / pytest (3.10)`, `CI / pytest (3.12)`, `package / dist`, `verify-install / linux-x64`. Nenhuma ET toca `docs/**` nem `website/**`, então `website / build` não entra. | bolt-plan |
| D10 | U6-N5 "fora do `HOME`": teste pytest em `tests/test_install_sh.py`. Raiz medida = `tmp_path` (projeto/`cwd`, espelho, `TMPDIR`, `ZDOTDIR`); `HOME` numa pasta irmã. Snapshot (modo, tamanho, `mtime_ns`, sha256; pasta só modo; symlink destino) antes e depois; diff `{}`; única exceção `zdot/.zshrc` (CT16). Dublês: espelho local, wheel falso (`bob setup` só grava o log) e stubs de `node`/`npm`; o resto é real. Harness sem mudança. Sem `CHANGELOG.md`. | checkpoint aprovado 23/10 22:16; ADR 0013; CT16 |

## Testing Contract
| Pronto / requisito | Prova automática | Onde |
|---|---|---|
| Pronto 1 (comando `bob` num terminal novo, FR1.1) | passo 13 (a)–(c): sourcing com `env -i` dá `$HOME/.local/bin/bob`. `test_profile_line_sources_in_sh` | T3, T1 |
| Pronto 2 (2ª execução sem mudança, linha única) | passo 13 (2 execuções, `grep -c` = 1). `test_second_run_is_already_marked` | T3, T1 |
| Pronto 3 (perfil sem escrita: aviso, saída 0) | passo 13 (e). `test_unwritable_profile_warns_and_exits_0[en,pt-BR]` | T3, T1 |
| CT16: arquivo por shell | `test_profile_file_follows_the_shell[6]`, `test_zdotdir_holds_the_zshrc`; passo 13 (a)–(c) | T1, T3 |
| CT16: bytes preservados | `test_profile_append_keeps_the_bytes[2]`, `test_profile_symlink_is_written_through`; passo 13 (b) | T1, T3 |
| CT16: já no PATH | `test_local_bin_on_path_writes_nothing`; passo 13 (d) | T1, T3 |
| CT3: linha do resumo | `test_profile_text_maps_each_value[16]`, `test_profile_line_sits_before_the_doctor_line[2]`, `test_profile_line_is_absent_without_the_variable[2]`, `test_profile_line_is_in_the_partial_summary`; passo 13 | T2, T3 |
| Hermeticidade (U5-N16) | `test_u5_tests_open_no_network[tests/test_setup_cmd.py]` com `-k "hook or profile"` | T2 |
| U6-N5: 0 arquivos fora do `HOME` (exceto `.zshrc` no `ZDOTDIR` fora do `HOME`) | `test_install_writes_nothing_outside_home[bash,sh,zsh]`, `test_zdotdir_outside_home_is_the_only_outside_write[new,existing]` | T4 |
| Qualidade | checks do PR + `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → 0 | T1–T3 |

## Passos
- [ ] P1 — `scripts/install.sh`: `PROFILE_LINE`, `STEPS`, `step_perfil`, `profile_warning` e `export` (T1).
- [ ] P2 — `tests/test_install_sh.py` (T1).
- [ ] P3 — `src/bob_quality/setup_cmd.py` e `src/bob_quality/messages.py` (T2).
- [ ] P4 — `tests/test_setup_cmd.py` e `tests/test_hermetic.py` (T2).
- [ ] P5 — `scripts/verify-install.sh`: `run_oneliner`, `profile_line`, `profile_case`, `step_13`, `STEP_IDS`, dispatch (T3).
- [ ] P6 — `tests/test_verify_install.py` (T3).
- [ ] P7 — `CHANGELOG.md` (T3).
- [ ] P8 — verificação da unit: harness inteiro verde no PR da T3 e na `main`, e checkpoint da U6 com o Emerson.
- [ ] P9 — `tests/test_install_sh.py`: snapshot fora do `HOME` antes e depois da instalação (U6-N5, NFR7; checkpoint aprovado 23/10 22:16) (T4).

## Tarefas
| Tarefa | ET | Passos | Base | Branch | Depende de |
|---|---|---|---|---|---|
| T1 — Passo perfil no install.sh | `tasks/T1.md` | P1, P2 | `main` @ `22d461a` | `aidlc/u6-perfil-shell/t1-install-perfil` | — |
| T2 — Linha perfil do shell no resumo do bob setup | `tasks/T2.md` | P3, P4 | `main` @ `22d461a` | `aidlc/u6-perfil-shell/t2-setup-perfil` | — |
| T3 — Harness: passo 13 (perfil do shell) | `tasks/T3.md` | P5, P6, P7 | `main` depois do merge da T1 e da T2 (SHA a fixar) | `aidlc/u6-perfil-shell/t3-verify-install` | T1, T2 |
| T4 — Teste: a instalação não escreve fora do HOME | `tasks/T4.md` | P9 | `main` @ `4d1603323ddc13714fa50b5e98487cb0957c7f20` (#208) | `aidlc/u6-perfil-shell/t4-fora-do-home` | após merge da U7 T3; Plan Approval da T4 |

**Paralelismo:**
- **T1 ∥ T2 (em paralelo).**
  - Não têm arquivo em comum: a T1 mexe em shell e no teste dele; a T2, em Python, `messages.py` e na guarda. Nenhuma das duas toca `CHANGELOG.md` (ADR 0027).
  - Cada uma passa sozinha. Sem a T2, o `bob setup` ignora `BOB_INSTALL_PROFILE`. Sem a T1, a variável nunca vem, e a T2 testa `_summary` direto.
  - Também rodam em paralelo com a U7 T1 e a U7 T2 (só `messages.py` e `test_hermetic.py` são comuns, em âncoras separadas: `shared-files-u6-u7.md`).
- **T3 depois da T1 e da T2 (em sequência).**
  - O passo 13 só passa com o passo `perfil` no `install.sh` (T1) e com a linha `shell profile:` no wheel (T2).
  - Toca `verify-install.sh`, `test_verify_install.py` e `CHANGELOG.md`, os mesmos da U7 T3. Ordem de merge sugerida: U6 T3 antes da U7 T3 (`shared-files-u6-u7.md`).
- **T4 depois do merge da U7 T3 (decisão do Emerson, 23/10 22:16).**
  - Toca só `tests/test_install_sh.py`. A U7 T3 não toca esse arquivo nem o `install.sh`, então as âncoras e os 79 casos da base não mudam com ela.
  - Nenhum arquivo em comum com a U8 (T1: prompts, `test_docs_pins.py`, `test_hermetic.py`; T2 e T3: docs, READMEs, `test_docs_pins.py`, `CHANGELOG.md` na T3; T4: `verify-install.sh`, `test_verify_install.py`, `CHANGELOG.md`). Pode rodar em paralelo com qualquer ET da U8, sem regra de rebase.

## Mecanismo de entrega
Igual à U5:
- O Maestro despacha cada ET, com o HEAD da base anotado, para um agente de código.
- O agente abre 1 PR para `main`.
- Eu verifico o PR contra a ET (`tasks/T<n>-verificacao.md`, escrito na hora da verificação).
- O Emerson faz o merge.

Antes do despacho da T3, eu fixo o SHA da base e reconfiro as âncoras de `scripts/verify-install.sh` e `tests/test_verify_install.py`. A T1 e a T2 não tocam esses arquivos, mas a U7 T3 toca. Nada é despachado por este plano.

## Riscos
| # | Risco | Mitigação |
|---|---|---|
| R1 | Root escreve em arquivo `0444`, então o caso (e) do passo 13 não reproduz como root. | O passo 13 recusa root (`die_passo 13`). No `test_install_sh.py`, a falha usa `ZDOTDIR` inexistente, que falha também como root. |
| R2 | O texto do `<erro>` muda entre shells (`Directory nonexistent` no dash, `No such file or directory` no bash). | O teste calcula o texto esperado com o mesmo `/bin/sh` (`_redirect_error`). O passo 13 usa `Permission denied`, igual no dash e no bash. |
| R3 | O passo `perfil` passa a gravar `~/.profile` nos `HOME` de teste e de harness (passos 2, 6, 7, 8 e 9). | Nenhum teste ou passo atual confere o conteúdo do `HOME` depois de uma instalação completa (conferido: os `_empty(home)` são só de falhas antes do `perfil`). O `digest` do harness é do projeto, não do `HOME`. |
| R4 | O tempo do harness cresce com o passo 13. | O `BOB_HOME` do passo 2 é reusado (pacote e npm prontos). Alvo ≤ 180 s, teto do harness ≤ 900 s mantido. |
| R5 | CT6 e CT16 v2 (incompatível) sem aviso. | O aviso ao Maestro está registrado no plano e na proposta. A ET cita a ADR 0021. |
| R6 | Conflito com a U7 T3 no harness. | Regras mecânicas R-VI1, R-VI2 e R-TV, e ordem de merge. |
| R7 | A T4 acha uma sobra real fora do `HOME` (por exemplo, no `TMPDIR` ou no projeto). | A ET manda parar e colar o diff; o arquiteto decide (achado de NFR7). Nada é mascarado no teste. |

## Autochecagem
- [x] Toda regra P1–P10 tem tarefa e teste.
- [x] Todo pronto da U6 tem prova automática (Testing Contract).
- [x] Referências arquivo:linha conferidas em `22d461a` (leitura remota, sem clone).
- [x] Cada ET tem passo 0 com resultado numérico, diz se toca `CHANGELOG.md` (só a T3) e se pode rodar em paralelo.
- [x] Literais e mutantes tratados em cada ET. Os gates `mutate`/`crap`/`dry` cobrem só `src/` (`bob.yaml: paths.include: [src]`). Shell é provado por teste e pelo harness.
- [x] Nenhuma meta rebaixada; nenhum waiver novo.
- [x] T4: U6-N5 coberta sem rebaixar; testes da T4 rodados pelo arquiteto numa cópia local dos 2 arquivos lidos em `4de8465` (`5 passed`) e com 2 mutações do `install.sh` (`5 failed`; `2 failed, 3 passed`).
