# Verificação: ET-u5-hook-pre-push-T1 (v2) × PR #200
Verificada em 22/10/2026 13:30 (UTC-3) contra `T1.md` (v2; v1 em `T1-v1.md`; base `main` @ `b142631`). Só leituras remotas, sem clone nem fetch: API pública do GitHub por curl, `raw.githubusercontent.com` (os 7 arquivos e `src/bob_quality/hooks/pre-push` no head e na base) e cursor-github (check runs e logs dos jobs).

PR: https://github.com/fazedordecodigo/bob/pull/200 | branch `aidlc/u5-hook-pre-push/t1-hook-install` → `main` | head `7b97bc050f90b4ad6aaf15efced7cb36527ab973` | base `b142631935df7cad40f241501969dfea03595057` | aberto, pronto para revisão (`draft: false`), não mergeado, `mergeable: true` (`mergeable_state: clean`) | 3 commits, +678/−7, 7 arquivos.
Commits: `c53aea6` (22/10 11:06 UTC-3, pai `b142631`) "Instalar o hook pre-push gerenciado"; `538498e` (11:26) "Conferir o argumento de HookPathError"; `7b97bc0` (12:14) "Matar partition com a primeira quebra de linha". PR aberto em 22/10 12:11 (UTC-3). Agente: `bc-120d0358-fc94-5c1c-b52a-f77b9bbb79b7`.

## Veredito: Aprovado para checkpoint
Os critérios de aceite, R1–R11 e os 23 testes da ET v2 atendem. Os 6 checks obrigatórios do head estão verdes. Nenhum desvio. As duas lacunas da v1 (mutantes `partition`→`rpartition`) foram fechadas pela própria ET v2, não pelo agente; conto 0 rodadas de correção contra a v2. O merge é do Emerson.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u5-hook-pre-push-T1: Instalador do hook pre-push (hook_install.py)`; `aidlc/u5-hook-pre-push/t1-hook-install` → `main`; `base.sha` = `b142631…` (a da ET); pai do 1º commit = `b142631` | Atende |
| Fora de rascunho; não mergeado pelo agente | `draft: false`, `state: open`, `merged: false`, `merged_by: null` | Atende |
| Passo 0 colado | corpo, "Passo 0", sobre `b142631…`: `git version 2.43.0` (≥ 2.32); `RC:1`; `.git/hooks` + `RC:0`; `.husky` + `RC:0`; `.husky` + `RC:0`; `6 passed in 8.85s` + `EXIT:0` | Atende |
| Exatamente 7 arquivos | `pulls/200/files`: `CHANGELOG.md` +9/−0, `src/bob_quality/hook_install.py` (novo) +148, `src/bob_quality/messages.py` +2/−0, `tests/net_guard/sitecustomize.py` (novo) +31, `tests/test_hermetic.py` (novo) +56, `tests/test_hook.py` +15/−7, `tests/test_hook_install.py` (novo) +417. Os 4 novos não existem na base. Nenhum proibido (`hooks/pre-push`, `setup_cmd.py`, `scripts/`, `docs/**`, `website/**`, `README*`, `.github/workflows/`, `pyproject.toml`, `tests/conftest.py`, `tests/helpers.py`) | Atende |
| Hook estático sem mudança | `sha256` de `src/bob_quality/hooks/pre-push` calculado na box, base e head: `2b4a14b541ddf0baf87cedac37a8a4129a8b10a5e0512971da33ebc5b9d79ef6` nos dois; o corpo traz o mesmo valor | Atende |
| R1 nomes e imports | docstring `"""Hook pre-push gerenciado pelo bob (CT10, ADR 0016)."""`; só stdlib + `bob_quality.messages.msg` + `bob_quality.tools.ToolError`; `HOOK_MARKER = b"# managed-by: bob-quality"`, `HookState` com os 5 literais, `_MODE = 0o755`, `_UNSAFE` com as 5 sequências da ET (aspas duplas, `$`, crase, barra invertida e quebra de linha) | Atende |
| R2 tipos | `class HookPathError(ValueError)`; `@dataclass(frozen=True) HookResult(state, path, hooks_path="")` | Atende |
| R3 `render_hook` | não absoluto → `HookPathError(str(bob_bin))`; `os.fsencode(str(bob_bin))`; qualquer item de `_UNSAFE` → `HookPathError(str(bob_bin))`; 8 linhas em bytes, linha 6 `BOB="<raw>"`, linha 8 `exec "$BOB" check --gates crap,dry,deps </dev/null` | Atende |
| R4 ordem e `partition` | `install_hook` renderiza antes de chamar git (l.41); `config --get core.hooksPath`: rc 0 → `completed.stdout.partition("\n")[0]` (l.72) e `HookResult("preserved_hookspath", project / v, v)`; rc ≠ 1 → `ToolError(msg("git.command_failed", …))`; `rev-parse --git-path hooks` com `completed.stdout.partition("\n")[0]` (l.94) e `/ "pre-push"`. `partition` mantido nas duas linhas | Atende |
| R5 `_git` | `subprocess.run(["git", *args], cwd=project, capture_output=True, text=True, check=False)`; `OSError` → `ToolError(msg("tool.missing", tool="git"))` | Atende |
| R6 estados | link → `preserved` sem ler; existe e não é arquivo → `preserved` sem ler; marca fora da linha 2 → `preserved`; bytes e modo iguais → `unchanged`; senão `updated`; não existe → `mkdir(exist_ok=True)` sem `parents` → `created` | Atende |
| R7 gravação | `pre-push.tmp-{os.getpid()}` ao lado do destino; `write_bytes` → `os.chmod(tmp, _MODE)` → `os.replace`; `except BaseException` → `tmp.unlink(missing_ok=True)` e `raise` | Atende |
| R8 mensagem | `messages.py`: en l.93 `"git.command_failed": "git {command} failed: {detail}"` logo depois de `git.ls_files_failed` (l.92); pt-BR l.502 `"git {command} falhou: {detail}"` logo depois de `git.ls_files_failed` (l.501). Só 2 linhas adicionadas | Atende |
| R9 `tests/test_hook.py` | sai `import shutil` e `HOOK = …`; entram `import sys`, `from bob_quality.hook_install import install_hook`, `BOB = Path(sys.executable).parent / "bob"`; `_install_hook` = `install_hook(repo, BOB)` + `assert result.state == "created"` + `return repo / ".git" / "hooks" / "pre-push"`. Os 6 testes existentes sem hunk. Entra também `import os` (ver Observações) | Atende |
| R10 guarda de rede | `tests/net_guard/sitecustomize.py`: ativa só com `BOB_NET_GUARD_LOG`; `socket.socket.connect`/`connect_ex` negam AF_INET/AF_INET6; `socket.getaddrinfo` nega sempre; grava `<função> <repr>` no log e levanta `OSError("bob net guard: …")` | Atende |
| R11 `tests/test_hermetic.py` | `_ROOT`, `_GUARD`, `_UNIT_ARGS = (("tests/test_hook_install.py",),)`, `_guarded_env` (prefixa `PYTHONPATH` e define `BOB_NET_GUARD_LOG`) | Atende |
| 23 testes com nome exato | script na box: os 20 `def test_` de `test_hook_install.py` batem com os testes 1–18, 22 e 23, na ordem da ET; teste 19 em `test_hook.py`; testes 20 e 21 em `test_hermetic.py`. Os 23 nomes estão no corpo. Nenhum `skip`, `xfail`, `only`, `noqa` ou `pragma` | Atende |
| Asserções da v2 | teste 2: `issubclass(HookPathError, ValueError)` e `caught.value.args == (str(p),)`; teste 22: `.husky\nignored\n` → `HookResult("preserved_hookspath", repo / ".husky", ".husky")` e `.husky` não criada; teste 23: `.git/hooks\nignored\n` → `created` em `.git/hooks/pre-push` | Atende |
| Contagem de casos 39 / 1 / 2 | parametrizações: 3, 6, 1, 1, 1, 1, 1, 2, 5, 2, 2, 1, 3, 1, 1, 3, 1, 2, 1, 1 = 39. Log do CI 3.12: `tests/test_hook_install.py` com 39 pontos, `tests/test_hook.py` com 7 (6 + 1), `tests/test_hermetic.py` com 2 | Atende |
| `test_hook.py`: 7 passed, os dois tempos < 60 s | corpo, `--durations=0` em `7b97bc0`: `test_pre_push_hook_runs_crap_gate_under_60s` 1.19s; `test_pre_push_hook_blocks_when_changed_function_exceeds_crap_10` 1.15s; CI: 7 passados | Atende |
| Guarda de rede: rc 0 e log vazio | teste 21 verde no CI (3.10 e 3.12); o assert exige rc 0 e log ausente ou vazio; `rg -n "https?://" tests/test_hook_install.py` → `RC:1` (corpo; conferido na box: 0 ocorrências de `http`) | Atende |
| Suíte inteira 0 failed | CI: `4562 passed, 3 warnings` em 3.10 (1112.95 s) e 3.12 (676.67 s). 4520 da `main` + 42 novos (39 + 1 + 2). Os 3 warnings são o aviso já existente de `verify_requirements` em `tests/test_security_parse.py`. Corpo: `4562 passed` local, `PYTEST_EXIT:0` | Atende |
| `bob check` com 5 gates → 0 | corpo: `BOB_EXIT:0`, crap/dry/deps/mutate/coverage ✅, 0 sobreviventes, 0 sem teste, diff coverage python 100%. Comentário do `bob` (CI, commit `7b97bc0`, 16:18Z): 4 ✅, "No surviving mutants", "No mutants without tests", nenhuma violação de dependência, nenhum clone novo; maior CRAP do diff 5.0 (`_preserved`, 100% de cobertura); os 16 waivers são de 2026-10-11 (nenhum novo) | Atende |
| Linhas novas ≤ 100 colunas (≤ 101 com o `+`) | script na box sobre os `patch` de `pulls/200/files`, com `len` do Python: maior linha adicionada = 100 com o `+`. Nenhuma acima de 101 | Atende |
| `CHANGELOG.md` | as 2 entradas no topo de `## Unreleased`, antes da entrada da U4 T3; en e depois pt-BR, cada uma seguida de linha vazia; unidas por espaço, iguais em bytes ao texto da ET (script na box); linhas com 93/99/96/5 e 94/93/95 colunas; quebras só em espaço | Atende |
| 6 checks verdes no head | tabela abaixo | Atende |
| Corpo do PR | Resumo, Passo 0, Arquivos, Testes (23 nomes e casos 39/1/2), Comandos (subconjunto, tempos, suíte, `bob check`, `git diff --name-only`, `sha256`, colunas), `## Decisões tomadas: nenhuma`, `## Bloqueios` sem bloqueio; Referências: U5, CT10, ADR 0016, ADR 0017, FR5.1, FR5.3, NFR4, NFR5, NFR8, US4.1 | Atende |

## Checks no head `7b97bc0` (início 22/10 12:57 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| bob / check | bob, run 39809735226 | success | 20m26s |
| bob / cold | bob, run 39809735226 | success | 1m13s |
| CI / pytest (3.10) | CI, run 39809734988 | success, `4562 passed, 3 warnings` | 19m58s |
| CI / pytest (3.12) | CI, run 39809734988 | success, `4562 passed, 3 warnings` | 12m09s |
| package / dist | package, run 39809734904 | success | 1m14s |
| verify-install / linux-x64 | verify-install, run 39809735002 | success, 9 linhas `ok` (passos 1–5, 7, 8, 9a, 9b), passo 5 em 7 s | 4m11s |
| website / build | — | não se aplica (o PR não toca `docs/` nem `website/`) | — |

## Observações (não reprovam)
- `tests/test_hook.py` ganha `import os`, fora da lista do R9. O teste 19 da própria ET usa `os.fsencode` e `os.access`, então o import é necessário. Fica como imprecisão da ET.
- A ET diz "pt-BR 501 depois da inserção" para a chave nova. Na base, `git.ls_files_failed` pt-BR está na l.500; com a linha en inserida antes, ela vai para a l.501 e a chave nova fica na l.502. A regra que vale ("logo depois de `git.ls_files_failed`") atende; o número da ET está deslocado em 1.
- Testes 13 e 16: a ET diz "nenhum `pre-push*` na pasta de hooks", mas o `git init` com template padrão cria `pre-push.sample`. O teste compara a lista antes e depois (`before`), o que prova que nada novo foi criado. É a leitura correta.
- `_preserved` e `_current` leem o arquivo duas vezes, onde o R6 descreve uma leitura (`data = dest.read_bytes()`). O comportamento é o mesmo e o corpo das funções é livre.
- O commit `7b97bc0` (12:14 UTC-3) é anterior ao carimbo da ET v2 (12:20 UTC-3). Os testes 22 e 23 e a asserção de `args` batem com a v2 em nome e conteúdo.
- O corpo cita `32 subtests passed` na corrida local; o CI não mostra subtests. A contagem de casos (4562) é a mesma.
- No corpo, a linha "Referências" fica logo abaixo do título `## Bloqueios`, sem item de bloqueio. Leio Bloqueios como vazio.
- `mergeable_state: clean`: sem conflito e sem bloqueio de proteção no momento da consulta.

## Registro
- 22/10/2026 13:30 (UTC-3): rodada 1 contra a v2 (head `7b97bc0`): aprovado para checkpoint, sem desvios. `traceability.json` (U5 T1 `verified`, PR 200 `open`) e `trace.md` da U5 atualizados. O merge é do Emerson.
