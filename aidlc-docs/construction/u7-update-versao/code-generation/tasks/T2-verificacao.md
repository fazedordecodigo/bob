# Verificação: ET-u7-update-versao-T2 (v3) × PR #206
Verificada em 23/10/2026 19:58 (UTC-3) contra `T2.md` (v3; v2 em `T2-v2.md`; v1 em `T2-v1.md`; CORRECAO-v2.md e CORRECAO-v3.md). Só leituras remotas, sem clone nem fetch: `gh`/API GitHub (PR, files, patches, check runs, logs, comentário `bob-report`), `raw.githubusercontent.com` no head e o corpo do PR.

PR: https://github.com/fazedordecodigo/bob/pull/206 | branch `aidlc/u7-update-versao/t2-update` → `main` | head `4c99ff2196665d9d5c63fc2170c511b7468c7936` | base `675d933188b09bb2f23b88257c40efc850cca632` | `draft: false` | 3 commits (`284bd28` v1, `ca859f0` rodada 1 / dublê seletivo, `4c99ff2` rodada 2 / R7 v3 + testes 23–26), +1158/−2, 6 arquivos.
Agente: `bc-299592e7-2065-55c6-8890-8ab0ddc6d5c4`. `correction_round` 2 (rodada 1: teste 15 dublê seletivo, ET v2; rodada 2: R7 + testes 23–26 do `mutate`, ET v3).
**Merge:** mergeado pelo Emerson (`fazedordecodigo`) em 23/10/2026 19:57 (UTC-3), durante a verificação; merge commit `377b855daecb1f0354254c19f1ae62fb36800bab` (main agora `377b855`). A verificação foi concluída sobre o head mergeado `4c99ff2`.

## Veredito: Aprovado para checkpoint (já mergeado)
R1–R16, A1–A3 e os 26 testes (82 casos) da ET v3 atendem. Os 6 checks obrigatórios do head estão verdes. Escopo exatamente os 6 arquivos. Bloqueios vazio; "Decisões tomadas: nenhuma". Nenhum desvio que reprove.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Título, branch e base | `ET-u7-update-versao-T2: bob update e bob --version`; `aidlc/u7-update-versao/t2-update` → `main`; `baseRefOid` = `675d933…` | Atende |
| Fora de rascunho; não mergeado pelo agente | `isDraft: false`; merge feito por `fazedordecodigo` (Emerson) 19:57 UTC-3, não pelo agente | Atende |
| Passo 0 colado e igual ao esperado | corpo: `675d933…`; `RC:2`; `10`; `0`; `13:    ("tests/test_project_version.py",),`; `_COMMANDS = (… "setup")`; `EXIT:0`; `126 passed in 2.48s`; `['check', …, 'waive']` (itens 1–9) | Atende |
| Exatamente 6 arquivos | API files: `cli.py` (+39), `messages.py` (+47), `update.py` (added, +214), `test_hermetic.py` (+1), `test_update.py` (added, +841), `test_usage_exit.py` (+16/−2). Nenhum proibido (`gitleaks.py`, `setup_cmd.py`, `project_version.py`, `CHANGELOG.md`, `scripts/**`, `pyproject.toml` etc.) | Atende |
| R1 módulo / imports / nomes públicos | `update.py:1` docstring exata; imports só stdlib + `project_version, setup_cmd, user_dirs, exit_codes, messages`; `DEFAULT_API`, `DEFAULT_DOWNLOAD`, `UpdateError`, `run_update`, `version_lines` | Atende |
| R2 constantes | `update.py:25-57`: valores exatos, incluindo `_ALLOWED_URL` igual ao de `gitleaks` (teste 22), `_RETRYABLE` na ordem, `_SUMS_SEP = b"  "`, `_FIRST_SERVER_ERROR = 500`, `_TMP_PREFIX = "bob-update."` | Atende |
| R3–R6 | `UpdateError(Exception)`; `version_lines` 64-68; `_urls` 71-78 (tira 1 barra, `fullmatch`); `_status` 81-86; `_read` 89-92 (context manager, `timeout=_TIMEOUT_S`); `_fetch` 95-105 (só `_RETRYABLE`, `code < 500` não repete, `sleep(_PAUSE_S)` entre tentativas) | Atende |
| **R7 (foco v3)** | `update.py:112-117`: `except ValueError:` → `raise UpdateError(msg("update.api_failed", status=msg("update.bad_response")))` de imediato, sem `data = None`; `tag = data.get(_TAG_KEY) if isinstance(data, dict) else None` (sem default); `_TAG_RE.fullmatch` | Atende |
| R8–R11 | `_numbers` 124-128; `_download` 131-140 (404 → `download_missing`, outra → `download_failed`); `_sum_for` 143-148 (`partition`, 1ª linha); `_install` 151-178 (`mkdtemp(prefix=…)`, `try/finally shutil.rmtree(tmp)` sem `ignore_errors`, sha256 antes do `write_bytes`, `subprocess.run([_SH, str(path), _LANG_FLAG, lang], cwd=project, env={**os.environ, _PIN_ENV: tag}, check=False)`) | Atende |
| R12–R13 | `run_update` 181-186 (só `UpdateError`, `CONFIG_OR_TOOL`); `_run` 189-214 na ordem R13a–d (`error is not None`, `state == "installed"`, `versions[0]`) | Atende |
| Proibidos (literais) | sem `decode(`, `strip`/`rstrip("/")`, `ignore_errors`, `status == "failed"`, `data = None` em `update.py` | Atende |
| R14 `cli.py` | import `run_update, version_lines` na linha 18 (logo após `run_setup`); `_Version(argparse.Action)` 37-61 logo após `_Parser` (`nargs=0`, `default=argparse.SUPPRESS`, `self.lang`, `parser.exit()`); `--version` logo após `_add_lang(parser, lang)` 91-97; subparser `update` + `_add_lang` 161-162; `main`: `if args.command == "update": return run_update(Path.cwd(), lang)` 262-263, logo após `setup` | Atende |
| R15 mensagens | patch: `cli.update`, `cli.version` após `cli.setup`; `version.bob` + 12 `update.*` após `version.mixed_missing`, na ordem, en e pt-BR; textos idênticos à tabela "Mensagens" do `functional-design.md` (15 chaves × 2) | Atende |
| R16 hermetic | `("tests/test_update.py",),` logo após `("tests/test_project_version.py",),` | Atende |
| A1–A3 | `_COMMANDS` termina em `"update"` (reformatado em várias linhas, mesma tupla); `_TOP_HELP` `{…,setup,update}` + 2 frases após a do setup; `_SUB_HELP["update"] = ("usage: bob update", "--lang LANG")` após `setup` | Atende |
| 26 testes com nome exato (82 casos) | `tests/test_update.py`: 26 `def test_` com os nomes da tabela, na ordem 1–26; parametrizações somam 82; teste 21 com as 15 chaves; testes 23–26 presentes (`test_http_500_is_retried`, `test_install_passes_check_false`, `test_setup_context_receives_home_lang_version`, `test_version_default_is_suppressed`) conforme Dado/Quando/Então; teste 15 com dublê seletivo (`argv[0] == "sh"`). Nenhum `skip`/`xfail`/`only` | Atende |
| Contagens locais (corpo) | `176 passed` (82+79+5+10); net guard `82 passed`, log 0; `rg` URLs → `2`; `bob --version` → `bob 0.1.0` / `project skills: not installed`; suíte `4782 passed, 3 warnings` | Atende |
| `bob check … crap,dry,deps,mutate,coverage` | corpo: EXIT:0, coverage passed, 0 waivers novos. Comentário CI `bob-report` no `4c99ff2`: crap ✅ (máx `main` 8.0, todas 100% cobertura), dry ⚠️ 1 clone novo `gitleaks.py:148-159 ↔ update.py:78-89` (esperado, ADR 0025), deps ✅, mutate ✅; **0 sobreviventes no diff**: os 2 sobreviventes são `cli.py:269` (`_dispatch` / `_resolve_config`), "outside the diff; does not block"; "No mutants without tests" | Atende |
| Colunas | 0 linhas > 100 em `update.py` e `test_update.py` (raw no head); corpo: comando `awk` → `0` | Atende |
| 6 checks verdes | tabela abaixo; pytest 3.10 e 3.12: `4782 passed, 3 warnings`; verify-install: 11 linhas `ok` | Atende |
| Corpo do PR | Resumo, Passo 0, Arquivos, Testes (26 nomes + A1–A3 + R16), Comandos (com linha do `dry`), "Decisões tomadas: nenhuma", `## Bloqueios` vazio, refs U7, CT1, CT11, CT12, CT14, ADR 0011, ADR 0018, ADR 0025, FR6.1–FR6.5, US5.1, US5.2, US7.2, NFR9 | Atende |

## Checks no head `4c99ff2` (início 23/10 13:17 UTC-3)
| Check | Workflow / run | Resultado | Fim (UTC-3) |
|---|---|---|---|
| bob / check | bob, run 39985507654 | success (`dry-after warn 1 new clone`, jscpd 5.4.1) | 13:47:25 |
| bob / cold | bob, run 39985507654 | success (`cold-dry warn 5.4.1`) | 13:17:47 |
| CI / pytest (3.10) | CI, run 39985507589 | success, `4782 passed, 3 warnings` | 13:34:39 |
| CI / pytest (3.12) | CI, run 39985507589 | success, `4782 passed, 3 warnings` | 13:33:40 |
| package / dist | package, run 39985507594 | success | 13:17:49 |
| verify-install / linux-x64 | verify-install, run 39985507600 | success, passos 1–9b e 12 `ok` (11 linhas) | 13:19:05 |

## Observações (não reprovam)
- `_COMMANDS` foi reformatado em várias linhas (formatador); conteúdo = A1.
- Algumas mensagens viraram literais concatenadas entre parênteses (limite de 100 colunas); o texto resultante é o da tabela (teste 21 confere).
- Pytest 4668 (pós U7 T1) → 4782 inclui também a U6 T2 já na base; o delta desta tarefa é 82 + 1 hermetic.
- O CI do `bob / check` roda `crap,dry,deps,mutate` (sem `coverage`); a evidência do `coverage` está no corpo do PR e o CRAP do CI mostra 100% nas funções do diff.
- Merge pelo Emerson aconteceu às 19:57 (UTC-3), antes desta verificação ser gravada; head mergeado = head verificado.

## Registro
- 23/10/2026 19:58 (UTC-3): rodada contra a v3 (head `4c99ff2`, base `675d933`): aprovado para checkpoint, sem desvios. `correction_round` 2. PR já mergeado pelo Emerson (19:57 UTC-3, `377b855`). `traceability.json` (U7 T2 `merged`, PR 206 `merged`) atualizado. Status da unit sem mudança (`plan_approved`).
