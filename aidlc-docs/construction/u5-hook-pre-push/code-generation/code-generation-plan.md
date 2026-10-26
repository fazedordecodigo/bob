# U5 — u5-hook-pre-push — Plano de geração de código

Bolt: B5 (U5) | Base: `main` @ `b142631935df7cad40f241501969dfea03595057` (#199, U4 fechada) | Profundidade: Minimal | Data: 2026-10-22 (UTC-3)
Aprovação do plano: **pendente** (Plan Approval do Emerson). Nada foi despachado.
Desenho: `../functional-design.md` (H1–H13), `../nfr-requirements.md` (U5-N1–N16), `../nfr-design.md`. Rastreio: `../trace.md`.
Perguntas: nenhuma. Toda decisão abaixo sai de doc aprovado (CT10, CT3, CT5, CT15, ADR 0013/0016/0017, unit-of-work) ou é técnica e reversível (D3–D12), registrada no complemento da ADR 0016 (`inception/application-design/decisions.md`) e na nota do CT10 (`inception/contracts/contract-summary.md`).

## Resumo
- Constrói: `bob_quality.hook_install` (C06, CT10: `install_hook`, `render_hook`, `HookResult`, `HookPathError`), o passo `hook` do `bob setup` (CT3 ordem 7), a guarda de rede dos testes (U5-N16) e os passos 6 e 12 do harness, com o hook conferido nos passos 7 e 8.
- Toca: `src/bob_quality/hook_install.py` (novo), `src/bob_quality/messages.py`, `src/bob_quality/setup_cmd.py`, `scripts/verify-install.sh`, `tests/test_hook_install.py` (novo), `tests/test_hook.py`, `tests/net_guard/sitecustomize.py` (novo), `tests/test_hermetic.py` (novo), `tests/test_setup_cmd.py`, `tests/test_verify_install.py`, `CHANGELOG.md`.
- Testes: 18 novos na T1 em `test_hook_install.py` (37 casos), 1 novo em `test_hook.py` (+ ajuste da instalação), 2 em `test_hermetic.py` (2 casos na T1, 3 com a T2); 13 novos na T2 (18 casos, + 4 ajustes); 7 novos na T3 (8 casos, + 4 ajustes); passos 6, 7, 8 e 12 do harness; e2e manual na T2.

## Decisões fechadas
| # | Decisão | Origem |
|---|---|---|
| D1 | Interface CT10 sem mudança de nome. Acréscimos compatíveis: `HOOK_MARKER`, `HookPathError(ValueError)`, `render_hook(bob_bin) -> bytes`, campo `HookResult.hooks_path: str = ""` (I37). | CT10; complemento da ADR 0016 |
| D2 | Template em bytes, montado de `HOOK_MARKER` e `os.fsencode(str(bob_bin))`; LF; modo `_MODE = 0o755`. Sem literal de codificação (evita o mutante equivalente `"utf-8"` → `"UTF-8"`). | CT10, ADR 0016 |
| D3 | Caminho citável: absoluto e sem nenhum dos bytes `"`, `$`, `` ` ``, `\`, `\n` (tupla `_UNSAFE`, 1 literal por byte, 1 caso de teste por literal). Senão `HookPathError` antes de qualquer git (I38). | CT10 ("absoluto, sem aspas internas") |
| D4 | Ordem: citar caminho → `git config --get core.hooksPath` (0 → preserva; 1 → segue; outro → erro) → `git rev-parse --git-path hooks` → link/não-arquivo → marca na linha 2 → igual? → grava. Primeira linha do stdout por `partition("\n")[0]` (sem `strip`, sem mutante de `rstrip`/`strip`). | ADR 0016, CT10 |
| D5 | Link (mesmo apontando para hook do bob) e não-arquivo: preservados sem leitura (I38). Marca só na linha 2 exata (`split(b"\n")[1:2] == [HOOK_MARKER]`). | ADR 0017, CT5 |
| D6 | Igual = bytes iguais E modo `0o755`. Só modo diferente → `updated` (I38). | CT10 |
| D7 | Gravação: `pre-push.tmp-<pid>` na mesma pasta → `write_bytes` → `os.chmod` → `os.replace`; `unlink(missing_ok=True)` em qualquer exceção. Pasta de hooks ausente: `mkdir(exist_ok=True)` (sem `parents`: a pasta-mãe é o git dir, que existe; `parents=True` seria mutante equivalente). | ADR 0017 |
| D8 | Erros do git: `OSError` → `ToolError(tool.missing, tool="git")`; saída inesperada → `ToolError(git.command_failed)` (chave nova, en/pt-BR). | CT1 |
| D9 | Passo `hook` em `STEPS` depois de `bob.yaml`; mapa de estados e falhas do `functional-design.md`. Preservado gera linha `preservado:` **e** aviso (FR5.3 pede aviso; diferente do `bob.yaml`, I42). Os textos pt do CT10 ficam no catálogo sem o prefixo, que vem de `setup.warning_line` (I36). Falha sai `4`. | CT3, CT10, FR5.3 |
| D10 | `tests/test_hook.py` passa a instalar o hook com `install_hook(repo, Path(sys.executable).parent / "bob")`; o estático `src/bob_quality/hooks/pre-push` fica (docs da U8) e um teste prende o comando dele ao do template (I40). | CT10, pronto 2 |
| D11 | Hermeticidade medida (U5-N16): `tests/net_guard/sitecustomize.py` (ativo só com `BOB_NET_GUARD_LOG`) + `tests/test_hermetic.py` com controle positivo e 0 tentativas no pytest interno dos testes da U5. | L6/U4-N14, D21 da U1 |
| D12 | Harness: passo 6 (push com `env -i HOME=… PATH=/usr/bin:/bin` para remoto bare; confere `.bob/report.md`, I35); passo 12 instala o pin do pytest do `pyproject.toml` no venv do bob do passo 2 e roda `tests/test_hook.py` (I39); passo 7 confere o mtime do hook; passo 8 ganha um hook alheio. `--only 6` deixa de ser exemplo de passo desconhecido nos testes (vira `--only 10`, I41). | CT15, verification-command 6, 7, 8, 12 |
| D13 | 3 tarefas sequenciais (T1 → T2 → T3), 1 PR cada. Checks exigidos: `bob / check`, `bob / cold`, `CI / pytest (3.10)`, `CI / pytest (3.12)`, `package / dist`, `verify-install / linux-x64`. Nenhuma toca `docs/**` nem `website/**`, então `website / build` não entra. | bolt-plan B5, U4 |

## Testing Contract
| Pronto / requisito | Prova automática | Onde |
|---|---|---|
| Pronto 1 (push com `env -i` dispara o hook e roda `bob check --gates crap,dry,deps`) | passo 6 (push, remoto, `.bob/report.md` com 3 gates); `test_render_hook_is_the_ct10_text`; `test_static_hook_runs_the_same_command`; e2e da T2 | T3, T1, T2 |
| Pronto 2 (`tests/test_hook.py` < 60 s) | `tests/test_hook.py` (6 + 1) no CI com o template novo; passo 12 com o bob instalado | T1, T3 |
| Pronto 3a (hook alheio: mesmo hash, aviso) | `test_install_preserves_a_foreign_hook`, `test_install_never_follows_a_link_or_a_folder`, `test_hook_step_preserves_a_foreign_hook`, `test_hook_step_foreign_warning_reaches_the_output`; passo 8 | T1, T2, T3 |
| Pronto 3b (`core.hooksPath`: nada gravado, aviso com a linha) | `test_install_respects_core_hooks_path`, `test_hook_step_respects_core_hooks_path`; e2e da T2 | T1, T2 |
| NFR4 (2ª execução sem mudança) | `test_install_is_unchanged_on_the_second_run`, `test_hook_step_second_run_is_unchanged`; passo 7 | T1, T2, T3 |
| Atomicidade (ADR 0017) | `test_write_error_leaves_no_temporary`, `test_temporary_is_next_to_the_hook` | T1 |
| Erros com saída 4 | `test_hook_step_bad_bob_path_fails`, `…_git_failure_fails`, `…_write_error_fails`, `…_failure_stops_setup` | T2 |
| Hermeticidade (U5-N16) | `test_net_guard_catches_a_connection`, `test_u5_tests_open_no_network` | T1, T2 |
| Qualidade (U5-N15) | checks do PR + `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → 0 | T1–T3 |

## Passos
- [ ] P1 — `src/bob_quality/hook_install.py`: CT10 + H1–H10 (T1).
- [ ] P2 — `src/bob_quality/messages.py`: `git.command_failed` (T1); 8 chaves `setup.*` (T2).
- [ ] P3 — `src/bob_quality/setup_cmd.py`: `step_hook` + `STEPS` (T2).
- [ ] P4 — testes: `tests/test_hook_install.py`, `tests/test_hook.py` (T1); `tests/test_setup_cmd.py` (T2).
- [ ] P5 — hermeticidade: `tests/net_guard/sitecustomize.py`, `tests/test_hermetic.py` (T1; +1 parâmetro na T2).
- [ ] P6 — `scripts/verify-install.sh`: passos 6 e 12, `expected_hook`, `pytest_pin`, passos 7 e 8, `STEP_IDS`, `run_selected` (T3).
- [ ] P7 — `tests/test_verify_install.py` (T3).
- [ ] P8 — `CHANGELOG.md` em cada tarefa (en e pt-BR, no topo de `## Unreleased`).
- [ ] P9 — verificação da unit: harness inteiro verde no PR da T3 e na `main`; checkpoint da U5 com o Emerson.

## Tarefas
| Tarefa | ET | Passos | Base | Branch | Depende de |
|---|---|---|---|---|---|
| T1 — Instalador do hook pre-push (hook_install.py) | `tasks/T1.md` | P1, P2, P4, P5, P8 | `main` @ `b142631935df7cad40f241501969dfea03595057` | `aidlc/u5-hook-pre-push/t1-hook-install` | — |
| T2 — Passo hook no bob setup | `tasks/T2.md` | P2, P3, P4, P5, P8 | `main` após o merge da T1 (SHA a fixar) | `aidlc/u5-hook-pre-push/t2-setup-step` | T1 |
| T3 — Harness: passos 6 e 12 e hook nos passos 7 e 8 | `tasks/T3.md` | P6, P7, P8 | `main` após o merge da T2 (SHA a fixar) | `aidlc/u5-hook-pre-push/t3-verify-install` | T2 |
Por que em sequência: a T2 importa `hook_install` e usa `git.command_failed`; a T3 só passa no harness com o passo `hook` no wheel. Arquivos em comum: `CHANGELOG.md` (as três; entrada nova no topo de `## Unreleased`, sem conflito porque a ordem é fixa), `messages.py` (T1 insere depois de `git.ls_files_failed`; T2 insere depois de `setup.bob_yaml_write`; blocos diferentes) e `tests/test_hermetic.py` (T1 cria; T2 acrescenta 1 parâmetro). Nenhuma tarefa roda em paralelo.

## Mecanismo de entrega
Igual à U4: o Maestro despacha cada ET (com o HEAD da base anotado) para um agente de código; o agente abre 1 PR para `main`; eu verifico o PR contra a ET (`tasks/T<n>-verificacao.md`); o Emerson faz o merge. Antes do despacho da T2 e da T3, eu fixo o SHA da base e confiro de novo os números de linha que a tarefa anterior mudou. Nada é despachado por este plano.

## Riscos
| # | Risco | Mitigação |
|---|---|---|
| R1 | No push do passo 6, com `PATH=/usr/bin:/bin`, o `bob check` sair ≠ 0 (ex.: ferramenta ausente vira `4`). Pela leitura, sem Node o `dry` fica ⏭️ e contribui `0` (`dry_gate._tooling`, linhas 73-75); `crap` e `deps` rodam pelo venv do bob. | Passo 0 da T3 mede o push com `env -i` antes de mexer no script; se sair ≠ 0, para e reporta. A meta não muda. |
| R2 | Passo 12 precisa de pytest e o workflow do harness não instala `.[dev]` (I39). | O passo instala só o pin do `pyproject.toml` no venv do bob de teste (`$T`, descartável); `test_pytest_pin_matches_pyproject` prende o pin. Passo 0 da T3 mede. |
| R3 | `test_hermetic.py` roda pytest aninhado: soma tempo ao CI e ao gate `crap` (coverage roda a suíte). | Só os arquivos da U5 entram no pytest interno (≈ 45 casos, só git local); medido no PR da T1. Sob `mutate`, o teste não cobre linhas de `src/` em processo e não é escolhido por mutante. |
| R4 | `core.hooksPath` global na máquina do dev faz `test_hook.py` e o e2e virarem `preserved_hookspath`. | `test_hook_install.py` isola com `GIT_CONFIG_GLOBAL` e `GIT_CONFIG_NOSYSTEM` (fixture autouse); em `test_hook.py`, o `assert … == "created"` falha com motivo claro. O CI não tem `core.hooksPath`. |
| R5 | Docs (`README.md:319-326`, `docs/guides/pre-push.md`) seguem com o `cp` manual até a U8. | A cópia manual continua funcionando e é preservada com aviso (sem a marca); paridade de comando por teste (D10). Registrado como I40 para a U8. |
| R6 | `VERIFY_REMOTE=1`: os passos 6 e 12 só passam no modo remoto depois de uma release com a U5. | Fora de escopo da T3, igual à U4. |
| R7 | Tempo do harness (+ passos 6 e 12). | Reusam `S2_HOME`; alvos medidos U5-N11 (≤ 60 s), U5-N12 (≤ 240 s); teto U5-N13 ≤ 900 s mantido. |

## Autochecagem
- [x] Toda regra H1–H13 tem tarefa e teste (`../trace.md`).
- [x] Todo pronto da U5 (1, 2, 3) tem prova automática (Testing Contract).
- [x] Referências arquivo:linha conferidas em `b142631` (leitura remota, sem clone).
- [x] Cada ET tem passo 0 com código de saída esperado e ordem de parada; diz se toca `CHANGELOG.md` (as três tocam) e a ordem.
- [x] Cada ET traz as lições da U4: literais sem mutante equivalente (ou o teste que mata), sobrevivente fora da lista vai para Bloqueios, bloqueio depois do PR só no corpo, PR pronto para revisão (rascunho só com bloqueio), CHANGELOG ≤ 100 colunas quebrado só em espaço.
- [x] Os 6 checks estão nomeados em cada ET; nenhuma toca `docs/**` ou `website/**`.
- [x] Nenhuma meta rebaixada; nenhum waiver novo; U4-N14 (hermeticidade) ganha medida (U5-N16).
- [x] Perguntas: nenhuma de produto; nenhum arquivo de perguntas.
