# Verificação: ET-u3-gitleaks-T1 × PR #191
Verificado em 20/10/2026 02:1x (UTC-3, contra a v1) e reavaliado às 02:20 (contra a v2), só com leituras remotas (cursor-github), sem clone.
PR: https://github.com/fazedordecodigo/bob/pull/191 | branch `aidlc/u3-gitleaks/t1-gitleaks-module` → `main` | head `041208d7a6eb242f4828987f6e12bea9d1b44694` | base `387b0b6` (igual ao HEAD conferido na ET) | aberto, não draft, não mergeado, `mergeable: true` (`mergeable_state: blocked`, aguardando review) | 3 commits, +1108/−0.

## Veredito: Aprovado para checkpoint (contra a ET v2)
Reavaliado em 20/10/2026 02:20 (UTC-3) contra a ET-u3-gitleaks-T1 **v2**. A 1ª verificação, de 02:1x, foi contra a v1 e terminou em "Escalar para desenho". Decisão do dono da estratégia de testes: a lacuna é da ET, não do PR. Os 6 testes extras cobrem ramos que a própria ET define (R7, R8, R10) e são necessários para o `mutate` com 0 sobreviventes. Nada foi rebaixado e não mudou escopo nem decisão aprovada. A v2 incorpora os 6 testes (32 no total) e corrige "6 funções públicas" para 5. O código do PR não mudou (head `041208d`).

## Desvios (contra a v1) e situação
| # | Evidência | Regra da ET v1 | Situação |
|---|---|---|---|
| 1 | `tests/test_gitleaks.py@041208d`: 32 `def test_`. A mais: `test_write_error_without_filename_names_the_destination` (l.698), `test_timeout_error_is_retried_twice` (l.720), `test_extractfile_none_fails_extraction` (l.738), `test_rollback_removes_temporary_binary` (l.750), `test_rollback_removes_temporary_link` (l.770), `test_write_error_keeps_an_existing_destination` (l.792). | "Testes a escrever (nomes exatos)" (26) | **Lacuna da ET, corrigida na v2.** A lista de 26 não cobria R7 (`TimeoutError`), R8 (`extractfile` → `None`) e R10 (`filename` `None`, `dest_existed`, limpeza dos `.tmp`), e a ET exige `mutate` 0. A v2 lista os 32. |
| 2 | A ET v1 dizia "6 funções públicas"; "Assinaturas" lista 5. O PR tem as 5. | Critério 2; "Restrições" | **Lacuna da ET, corrigida na v2** ("5 funções públicas", "além das 5 listadas"). |

## Critério → evidência
| Critério | Evidência | Resultado |
|---|---|---|
| Exatamente 4 arquivos | `list_pull_request_files`: `CHANGELOG.md` (+4), `src/bob_quality/gitleaks.py` (+252, novo), `src/bob_quality/messages.py` (+42), `tests/test_gitleaks.py` (+810, novo); `changed_files: 4` | Atende |
| Constantes, classe, 5 funções públicas, assinaturas, docstrings; `_TIMEOUT_S=30`, `_ATTEMPTS=3`, `_PAUSE_S=1.0` | `gitleaks.py` l.1, 25–48, 68–69, 72–73, 82–83, 93–94, 98–99, 119–120 iguais à ET; l.46–48 | Atende |
| 4 sha256 da R1 | `gitleaks.py` l.27–44 = R1, letra a letra; o teste l.266–284 confere | Atende |
| R2–R12 (leitura do código) | `platform_key` com mapa exato e `platform.system()`/`.machine()`; `base_url` com regex `fullmatch` (rejeita `127.0.0.1.example.com` e `localhost.example.com`); `_fetch` com 3 tentativas, só 5xx/rede, `time.sleep(_PAUSE_S)`; `_regular_member` com 1 membro `isreg`; `extractfile`; `_install`/`_rollback`/`_write_error` conforme R9/R10; link com `VERSION` (l.222) | Atende |
| 32 testes com nomes exatos (ET v2) | os 32 da v2 presentes, sem extras | Atende |
| Sem skip/xfail/only/asserts comentados | `grep` sem ocorrência | Atende |
| 6 chaves en/pt-BR com texto exato, antes de `setup.*` | diff: en l.374–394 e pt-BR l.772–792 do `messages.py@041208d`, logo antes de `setup.step_ok`; os 12 textos batem com a tabela da ET (comparação literal) | Atende |
| CHANGELOG | 2 parágrafos exatos no topo de `## Unreleased` | Atende |
| Sem `print`/`sys.std`/`extract(`/`extractall` | `grep` em `gitleaks.py`: nada | Atende |
| Linhas novas `.py` ≤ 100 | nenhuma linha `+` com mais de 100 colunas nos 3 `.py` | Atende |
| Só stdlib | imports: stdlib + `bob_quality.{messages,tools,user_dirs}`; nada no `pyproject.toml` | Atende |
| 6 checks verdes no head | `list_check_runs_for_ref 041208d`: 6/6 success (abaixo); `linux-x64` é do workflow `verify-install` (`.github/workflows/verify-install.yml`, run 39371286097) | Atende |
| pytest / e2e / bob check colados | "82 passed in 15.27s" (alvo); "4394 passed, 3 warnings, 32 subtests passed in 531.04s"; e2e "/tmp/tmpivxxn36r/bin/gitleaks 8.30.1"; `bob check …` "EXIT 0" | Atende (e2e manual, sem como reproduzir remotamente) |
| `rg` dos sha256 e do `https://` | corpo: `gitleaks.py` e `doctor.py`; `https://` só nas l.262 e 336 do teste (constante e caso de `base_url`); confere com o arquivo | Atende |
| Corpo cita U3, CT9, CT14, ADR 0014, FR2.2, FR2.3, US1.3, pronto 1, "Decisões tomadas: nenhuma" | todos presentes (Decisões tomadas como seção, com "nenhuma") | Atende |
| Não mergeado | `merged: false`, `state: open` | Atende |

## Checks no head `041208d` (início 20/10 01:45:47 UTC-3)
| Check | Resultado | Duração |
|---|---|---|
| check | success | 27m52s |
| pytest (3.12) | success | 16m47s |
| pytest (3.10) | success | 12m45s |
| verify-install / linux-x64 | success | 2m41s |
| dist | success | 1m27s |
| cold | success | 1m12s |

## Registro
- 20/10/2026 02:20 (UTC-3): ET v2 aplicada; `traceability.json` (U3 T1: `verified`, PR 191, `et_version` v2) e `trace.md` atualizados. Entregue ao Maestro. Merge é do Emerson.
