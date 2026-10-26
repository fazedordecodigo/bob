# Verificação: ET-u5-hook-pre-push-T2 (v1) × PR #201
Verificada em 22/10/2026 15:58 (UTC-3) contra `T2.md` (v1, base fixada em `main` @ `7f9ad59`). Só leituras remotas, sem clone nem fetch: API pública do GitHub por curl, `raw.githubusercontent.com` (os 5 arquivos no head e na base) e cursor-github (check runs e logs dos jobs).

PR: https://github.com/fazedordecodigo/bob/pull/201 | branch `aidlc/u5-hook-pre-push/t2-setup-step` → `main` | head `fbd14d03888dab671a4c3eb38c78a5911df71643` | base `7f9ad593ca9d905b1c66cc03a8c30773c326af76` | aberto, pronto para revisão (`draft: false`), não mergeado, `mergeable: true` (`mergeable_state: clean`) | 1 commit, +473/−2, 5 arquivos.
Commit: `fbd14d0` (22/10 14:51 UTC-3, pai `7f9ad59`) "Passo hook no bob setup"; PR aberto em 22/10 15:16 (UTC-3). Agente: `bc-53456d48-5f27-5a7c-b0a7-b540762ec407`.

## Veredito: Aprovado para checkpoint
Os 12 critérios de aceite, R1–R8, os 8 textos de R7 (byte a byte, en e pt-BR) e os 13 testes atendem. Os 6 checks obrigatórios do head estão verdes. Nenhum desvio. 0 rodadas de correção. Há imprecisões da ET e do corpo nas Observações; nenhuma reprova. O merge é do Emerson.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u5-hook-pre-push-T2: Passo hook no bob setup`; `aidlc/u5-hook-pre-push/t2-setup-step` → `main`; `base.sha` = `7f9ad59…` (a da ET); pai do commit = `7f9ad59` | Atende |
| Fora de rascunho; não mergeado pelo agente | `draft: false`, `state: open`, `merged: false`, `merged_by: null`; Bloqueios "Nenhum." | Atende |
| Passo 0 colado e igual | corpo, "Passo 0", base `7f9ad59…`: `created unchanged .git/hooks/pre-push`, `RC:0`, `# managed-by: bob-quality`, `41 passed in 0.75s`, `EXIT:0` | Atende |
| Exatamente 5 arquivos | `pulls/201/files`: `CHANGELOG.md` +8/−0, `src/bob_quality/messages.py` +38/−0, `src/bob_quality/setup_cmd.py` +65/−0, `tests/test_hermetic.py` +4/−1, `tests/test_setup_cmd.py` +358/−1. Nenhum proibido (`hook_install.py`, `test_hook_install.py`, `hooks/pre-push`, `test_hook.py`, `scripts/`, `docs/**`, `website/**`, `README*`, `.github/workflows/`, `pyproject.toml`) | Atende |
| R1 imports | `setup_cmd.py` l.18 `from bob_quality import hook_install` (entre `gitleaks` e `init_config`); l.25 `from bob_quality.hook_install import HookPathError, HookResult`; chamada `hook_install.install_hook(ctx.project, bob)` pelo módulo (l.231) | Atende |
| R2 constantes | l.115–124, logo depois de `_BOB_YAML_WRITE`, na ordem da ET: `_HOOK` … `_HOOK_FILE = ".git/hooks/pre-push"`. `grep -cF`: `"hook"`, `".git/hooks/pre-push"` e cada chave `setup.*` aparecem 1 vez no módulo | Atende |
| R3 `step_hook` | l.227, logo depois de `step_bob_yaml`; docstring exata; `bob = ctx.home.bin_bob`; `except` na ordem `HookPathError` → `msg(_HOOK_BAD_PATH, path=str(bob))`, `ToolError` → `_failed_reason(_HOOK, exc)`, `OSError` → `msg(_HOOK_WRITE, path=exc.filename or _HOOK_FILE, detail=exc.strerror or type(exc).__name__)`; sucesso → `_hook_result(ctx, result)` | Atende |
| R4 `_hook_result` | l.489, logo antes de `_config_result`; `created`/`updated` → `_INSTALLED` com `_ITEM_HOOK`/`_ITEM_HOOK_UPDATED`; `unchanged` → `StepResult(_UNCHANGED)`; `preserved` → `"preserved"` com `_PRESERVED_HOOK` e `_WARN_HOOK_FOREIGN(path, bob)`; `preserved_hookspath` → `_PRESERVED_HOOKSPATH(value)` e `_WARN_HOOKSPATH(value, bob)`; `bob = str(ctx.home.bin_bob)` | Atende |
| R5 `_shown` | `path.is_relative_to(ctx.project)` → `_relative(ctx, path)`; senão `str(path)` | Atende |
| R6 `STEPS` | `(_HOOK, step_hook)` depois de `(_BOB_YAML, step_bob_yaml)`; nenhum outro hunk em `STEPS`, `_run`, `_announce`, `_summary` | Atende |
| R7 8 textos, byte a byte | script na box: chaves extraídas da tabela "Textos de R7" da ET, comparadas em UTF-8 com os dicionários do head (módulo importado): en 8/8 e pt-BR 8/8 iguais; as 8 vêm logo depois de `setup.bob_yaml_write` e fecham os dois dicts, na ordem da ET; os mesmos textos estão na tabela "Mensagens" do `functional-design.md`. Concatenação implícita nos textos longos | Atende |
| R7 nenhuma chave existente muda | script: todas as chaves da base existem no head com o mesmo valor, nos dois idiomas; o conjunto novo = exatamente as 8 | Atende |
| R8 `tests/test_hermetic.py` | `_UNIT_ARGS` ganha `("tests/test_setup_cmd.py", "-k", "hook")`; único hunk do arquivo (a tupla passou a várias linhas) | Atende |
| 13 testes com nome exato | script: os 13 `def test_` novos de `tests/test_setup_cmd.py` batem com a ET, na ordem, no fim do arquivo. Nenhum `skip`, `xfail`, `only`, `noqa`, `pragma` ou assert comentado nas linhas novas; nenhum teste da base removido | Atende |
| Conteúdo dos testes | 1 (`installed` + bytes = `render_hook`), 2 (`unchanged`, bytes e `st_mtime_ns`), 3 (`updated` com o conteúdo da ET, 0o755), 4 (`file`/`symlink`/`directory` → `preserved` + aviso, item intacto), 5 (`.husky`, `F` e `.husky` ausentes), 6 (`/fora/hooks/pre-push` por extenso), 7 (`BOB_HOME` com `a$b` → `hook_bad_path`, `F` ausente), 8 (`setup.step_reason` com `git.command_failed`), 9 (2 casos de `OSError`), 10 (en/pt-BR, exit 4, `setup.error` no stderr, `doctor_not_run` na última linha), 11 (`hook: ok`, `installed: pre-push hook (.git/hooks/pre-push)`, depois `installed: nothing`), 12 (en/pt-BR, `warning_line`, `preserved`, `warnings`), 13 (`[(git_project, c.home.bin_bob)]`). Git real isolado com `GIT_CONFIG_GLOBAL` vazio e `GIT_CONFIG_NOSYSTEM=1` | Atende |
| Contagem 18 + 16 + 1 | parametrizações 1+1+1+3+1+1+1+1+2+2+1+2+1 = 18; `_MESSAGES` +8 tuplas (16 casos en/pt-BR); `_UNIT_ARGS` +1. CI: `collected 4597` = 4562 da `main` + 35. Log 3.12: `tests/test_hermetic.py` com 3 casos | Atende |
| Só os ajustes da lista fechada | import de `hook_install` (em bloco com parênteses, ver Observações), `from bob_quality.hook_install import HookPathError, HookResult, render_hook` depois de `bob_quality.config`, `step_hook,` entre `step_gitleaks,` e `step_npm,`, `_SAMPLES["bob"] = "/b/bin/bob"`, +8 tuplas em `_MESSAGES`, `test_steps_follow_the_ct3_order` com `"hook"` e `assert dict(STEPS)["hook"] is step_hook`. Nenhum outro teste existente tem hunk. Novo só o auxiliar `_isolate_git` (não é teste) | Atende |
| `test_u5_tests_open_no_network[tests/test_setup_cmd.py]` | verde no CI (3.10 e 3.12; 3 casos em `test_hermetic.py`); o assert exige rc 0 e log vazio | Atende |
| Linhas novas ≤ 100 colunas (≤ 101 com o `+`) | script na box sobre os `patch` de `pulls/201/files`, `len` do Python: maior linha adicionada = 101 com o `+`; nenhuma acima | Atende |
| `CHANGELOG.md` | 2 parágrafos no topo de `## Unreleased`, acima da entrada da T1 (`New \`bob_quality.hook_install.install_hook\`…`); en e depois pt-BR, cada um seguido de linha vazia; unidos por espaço, iguais em bytes ao texto da ET; linhas com 100/100/9 e 98/95/25 colunas; quebras só em espaço | Atende |
| Suíte inteira 0 failed, 0 errors | CI: `4597 passed, 3 warnings` em 3.10 (1131.33 s) e 3.12 (776.34 s); os 3 warnings são o aviso já existente de `verify_requirements` em `tests/test_security_parse.py`. Corpo: `4597 passed` local; subconjunto `179 passed`; `rg … -l` → só `tests/test_setup_cmd.py` | Atende |
| `bob check` 5 gates → 0 | corpo: exit 0, os 5 gates passaram, 0 sobreviventes, 0 waivers novos, cobertura do diff 100%. Comentário do `bob` (CI, commit `fbd14d0`, 15:40 UTC-3): crap/dry/deps/mutate ✅, "No surviving mutants", "No mutants without tests"; foco `setup_cmd.py` (risk 6.0); os 16 waivers são de 2026-10-11 (nenhum novo) | Atende |
| E2e: `novo` | `SETUP:0`; `bob setup: hook: ok`; `installed: …, bob.yaml, pre-push hook (.git/hooks/pre-push)`; `-rwxr-xr-x`, 225 bytes; as 8 linhas do CT10 com `BOB="/tmp/tmp.qNxVVeELZx/home/.local/share/bob-quality/bin/bob"` (= `$L`, absoluto) | Atende |
| E2e: `alheio` | sha256 `306c6ca7…cb` antes (impresso pelo `case`, antes de `== alheio`) e depois; `preserved: .git/hooks/pre-push (pre-push hook without the bob marker)`; `bob setup: hook: warning: existing pre-push hook preserved (.git/hooks/pre-push). To use bob's, add: <$L> check --gates crap,dry,deps.`; `SETUP:0` | Atende |
| E2e: `hookspath` | `SETUP:0`; `.git/hooks/pre-push` e `.husky` não existem (`ls` e `sha256sum` sem o arquivo); `preserved: core.hooksPath=.husky (bob does not write there)`; aviso `core.hooksPath=.husky; hook not installed. Add to your hook manager: <$L> check …` | Atende |
| E2e: reexecução e push | reexecução em `novo`: `bob setup: hook: ok`, `SETUP:0`, `stat -c %Y` `1792690690` antes e depois; `BASE:0`; push `c288af0..1ae11b2`, `PUSH:0`; `remote.git` main = HEAD = `1ae11b25…e82`; `.bob/report.md` começa com `# bob report`, `Commit` = o SHA do push, `Tools: lizard, coverage.py, import-linter` (crap e deps rodaram; sem jscpd). Linhas dos gates, pelo texto do corpo: `✅ crap`, `⏭️ dry: not run (Node missing …)`, `✅ deps` (ver Observações) | Atende |
| 6 checks verdes no head | tabela abaixo | Atende |
| Corpo do PR | Resumo, Passo 0, Arquivos, Testes (13 nomes e ajustes), Comandos (cada um com a saída), E2e (saída inteira), `## Decisões tomadas: nenhuma`, `## Bloqueios` "Nenhum."; Referências: U5, CT3, CT10, ADR 0016, ADR 0017, FR5.1, FR5.2, FR5.3, NFR4, NFR5, US4.1, US3.2 | Atende |

## Checks no head `fbd14d0` (início 22/10 15:16 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| bob / check | bob, run 39829884025 | success | 24m22s |
| bob / cold | bob, run 39829884025 | success | 1m19s |
| CI / pytest (3.10) | CI, run 39829884109 | success, `4597 passed, 3 warnings` | 20m15s |
| CI / pytest (3.12) | CI, run 39829884109 | success, `4597 passed, 3 warnings` | 13m58s |
| package / dist | package, run 39829884019 | success | 1m16s |
| verify-install / linux-x64 | verify-install, run 39829884608 | success, 9 linhas `ok` (passos 1–5, 7, 8, 9a, 9b), passo 5 em 8 s | 3m49s |
| website / build | — | não se aplica (o PR não toca `docs/` nem `website/`) | — |

## Observações (não reprovam)
- Corpo, seção E2e: a Entrega pede "bloco e saída inteira". O corpo traz a saída inteira e diz "O bloco da ET, sem alteração", sem colar o bloco. A saída segue a ordem do bloco da ET linha a linha (inclusive o sha256 do `alheio` antes de `== alheio`).
- A ET usa `sed -n 1,6p .bob/report.md`, que só mostra o cabeçalho; as linhas de `crap`, `dry` e `deps` ficam abaixo. O corpo as descreve em texto. A linha `Tools:` (lizard, coverage.py, import-linter, sem jscpd) bate com isso. Imprecisão da ET: o comando não mostra o que o esperado pede. Na T3 (passo 6 do harness), vale mostrar as linhas dos gates.
- No push, o `dry` fica ⏭️ (`Node missing`) porque o push roda com `PATH=/usr/bin:/bin`, e o exit é 0. É o que o I43 previa pela leitura. Agora está medido.
- Na reexecução, `bob setup | grep -F 'hook'; echo "SETUP:$?"` mostra o exit do `grep`, não do `bob setup`. Imprecisão do bloco da ET. A linha `hook: ok` e o mtime igual sustentam o critério.
- A ET pede o import da l.21 como uma linha só. Com `hook_install`, ela teria 110 colunas e furaria o limite de 100. O agente usou um bloco com parênteses. Os nomes e a ordem são os da ET.
- `_isolate_git` é um auxiliar novo (não é teste) que aplica o `GIT_CONFIG_GLOBAL`/`GIT_CONFIG_NOSYSTEM` exigido pela ET.
- Teste 4, caso `directory`: confere só `hook.is_dir()`. A ET diz "a pasta não mudou". Basta para o critério: a pasta é criada vazia e o passo não lê nem grava.
- O corpo do E2e explica que o 1º `node` do `PATH` da máquina do agente não tinha `npm` e que o `PATH` do shell apontava para o Node 22.23.4. O `bob doctor` mostra `node expected >=22.18.0 <23 found 22.23.4`.
- O corpo cita `32 subtests passed` na corrida local; o CI não mostra subtests. A contagem de casos (4597) é a mesma.
- `mergeable_state: clean`: sem conflito e sem bloqueio de proteção no momento da consulta.

## Registro
- 22/10/2026 15:58 (UTC-3): rodada 1 (head `fbd14d0`): aprovado para checkpoint, sem desvios. `traceability.json` (U5 T2 `verified`, PR 201 `open`) e `trace.md` da U5 atualizados. O merge é do Emerson.
