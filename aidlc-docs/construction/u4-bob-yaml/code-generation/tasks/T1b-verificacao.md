# Verificação: ET-u4-bob-yaml-T1b (v1) × PR #197
Verificada em 20/10/2026 23:50 (UTC-3) contra `T1b.md` (v1, aprovada pelo Emerson às 21:42), base `main` @ `0d85510`. Só leituras remotas (cursor-github: PR, diff, arquivos no head, check runs, logs dos jobs, comentário do `bob`), sem clone.
PR: https://github.com/fazedordecodigo/bob/pull/197 | branch `aidlc/u4-bob-yaml/t1b-no-code` → `main` | head `953f91be2002a8dcfa8d90cf785e2499b12297d2` | base `0d85510b8fd9d578619ce6e7adbde231b66bdd85` | aberto, pronto para revisão (`draft: false`), não mergeado, `mergeable: true` (`mergeable_state: blocked`, aguardando revisão) | 1 commit, +239/−2, 6 arquivos.
Commit: `953f91b` (20/10 22:55 UTC-3, pai `0d85510`). PR aberto às 23:16 (UTC-3). Agente: `bc-2343a08e-5bb5-5621-8b6b-b94b3c494a0e`.

## Veredito: Aprovado para checkpoint
Todos os critérios de aceite, R1–R7, os 5 testes (10 casos), os ajustes, o CHANGELOG, o corpo e os 6 checks atendem. 0 rodadas de correção. O merge é do Emerson.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Existência, título, base | PR #197 da branch da ET para `main`; título "ET-u4-bob-yaml-T1b: Gates crap e coverage sem código a medir saem 0" igual ao da Entrega; base `0d85510` | Atende |
| Passo 0 colado, `dry`/`deps` `EXIT:0`, `crap`/`coverage` `EXIT:4` | corpo, seção "Passo 0": script igual ao da ET; `ConfigResult(state='created_no_code', include=('.',))`; `== crap EXIT:4`, `== dry EXIT:0`, `== deps EXIT:0`, `== coverage EXIT:4`, `== crap,dry,deps,coverage EXIT:4`, `== padrao EXIT:4`; linhas `- ⏭️ \`crap\`: not run (coverage.py: No data to report.` | Atende |
| Exatamente os 6 arquivos | `changed_files: 6`: `CHANGELOG.md` +9, `check.py` +14/−1, `messages.py` +2, `test_check_dispatch.py` +163/−1, `test_check_report.py` +49, `test_mutation_branches.py` +2; as 2 remoções são as 2 linhas de import trocadas (R6 e ajuste de import); corpo traz o `git diff --name-only` com os 6 | Atende |
| R6: linha 11 | `check.py:11` = `from bob_quality.config import Config, ConfigError, detect_languages, load_config`; nenhum outro import muda | Atende |
| R2: `_NEEDS_CODE` | `check.py:47` = `_NEEDS_CODE = ("crap", "coverage")`, logo abaixo de `DEFAULT_GATES` (l.46, inalterado) | Atende |
| R3: assinatura e docstring | `check.py:202` `def _skipped_without_code(state: _Measured, gate: str, cwd: Path, config: Config) -> bool:`; l.203 docstring idêntica; logo depois de `_measure` (l.163-199) e antes de `_absorb` (l.212); corpo: fora de `_NEEDS_CODE` → `False` sem `detect_languages`; com código → `False`; sem código → `_record(state, GateResult(gate, "not_run", msg("check.no_code")), PASSED, {})` e `True` | Atende |
| R4: chamada só no laço | `check.py:181-182` `if _skipped_without_code(state, gate, cwd, config): continue` antes de `_absorb`; única chamada no arquivo; `SuiteMemo(...)` (l.177) e `finally: memo.close()` (l.197-198) inalterados | Atende |
| R1 e literais de mutante equivalente | `if detect_languages(cwd, config.include, config.exclude):` direto; sem `len(`, `== ()`, `bool(`, `tuple(` nem `reason=` nas linhas novas; `GateResult` posicional; nenhum parâmetro novo com padrão | Atende |
| R5: `check.no_code` | `messages.py:89` `"check.no_code": "no code to measure",` logo depois de `check.gate_not_implemented` (l.88, `_EN`); `messages.py:487` `"check.no_code": "nenhum código a medir",` logo depois da l.486 (`_PT_BR`) | Atende |
| R7: caminho com código inalterado | nenhum arquivo proibido no diff (`crap_gate.py`, `coverage_gate.py`, `python_probe.py`, `suite_memo.py`, `tools.py`, `probe.py`, `exit_codes.py`, `config.py`, `report.py` intactos); `test_a_missing_coverage_file_stays_a_tool_failure` passa sem edição | Atende |
| Teste 1 | `test_measure_skips_crap_and_coverage_without_code`: README `# leia`, `Config(include=(".",))`, `_forbid`, `dry(**kwargs)`/`deps(*args)` com os retornos da ET; chamada `_measure` inteira; as 9 asserções da tabela, na ordem | Atende |
| Teste 2 (4 casos) | `test_measure_finds_no_code_outside_the_include_rule`, `parametrize("case", ["fora-do-include", "excluido", "link", "outro-sufixo"])`; arquivos e `Config` por caso iguais à ET (symlink `src/app.py` → `tmp_path / "real" / "app.py"`); `state.gates` com os 2 `not_run` e `exit_code == 0` | Atende |
| Teste 3 (3 casos) | `test_measure_runs_crap_and_coverage_when_there_is_code`, `parametrize("path", ["src/app.py", "src/app.ts", "src/deep/app.cjs"])`; `crap(**kwargs)` devolve a tupla de 5 da ET, `coverage(*args)` o `CoverageOutcome` da ET; asserções `seen`, `exit_code == 4`, nomes, `render(...) == "coverage.py: No data to report.\n"`, `versions` | Atende |
| Teste 4 | `test_a_repo_without_code_skips_crap_and_coverage_and_exits_0`, logo depois de `test_a_missing_coverage_file_stays_a_tool_failure` (l.110); git init/config/README/`bob.yaml`/commit; `run_check(... gates=["crap", "coverage"]) == 0`; payload com os 2 dicts; `exit_code == 0`; as 2 linhas ⏭️ en; depois `lang="pt-BR"` → `0`, nomes `["crap", "dry", "deps"]`, `status == "not_run"`, `exit_code == 0`, linha ⏭️ pt-BR | Atende |
| Teste 5 | `test_a_missing_coverage_file_keeps_the_coverage_gate_a_tool_failure`: `_function_repo`; `run_check(..., gates=["coverage"], coverage_file=repo / "missing.coverage") == 4`; `name`, `status`, `reason.strip() == "No data to report."` | Atende |
| 10 casos | 1 + 4 + 3 + 1 + 1 = 10; CI `4486 passed` = 4476 da `main` + 10 | Atende |
| Ajustes em testes existentes | `test_check_dispatch.py`: l.11 `from bob_quality.check import _Measured, _absorb, _assemble, _measure` e `from bob_quality.coverage_gate import CoverageOutcome` logo depois de `from bob_quality.config import Config`; `test_mutation_branches.py`: só `(tmp_path / "src").mkdir()` e `(tmp_path / "src" / "app.py").write_text("X = 1\n")` depois do import `check_mod` e antes de `config = …`; nenhum outro hunk | Atende |
| Guarda intocada | `test_a_missing_coverage_file_stays_a_tool_failure`: o diff de `test_check_report.py` só insere depois da l.110, sem tocar as l.96-110 | Atende |
| Sem skip/only | nenhum `skip`, `xfail`, `.only`, assert comentado, mudança de limite de cobertura ou lint (as ocorrências de "skip" são só nomes de teste/função) | Atende |
| CHANGELOG | topo de `## Unreleased`, en e pt-BR, cada um seguido de linha em branco; juntando as quebras com espaço, texto idêntico ao da ET; linhas de 93, 96, 95 e 94, 97, 97, 5 colunas, quebra só em espaço | Atende |
| ≤ 100 colunas | maior linha nova: 90 (`check.py`), 45 (`messages.py`), 92 (`test_check_dispatch.py`), 89 (`test_check_report.py`), 55 (`test_mutation_branches.py`) | Atende |
| Suíte: 0 failed | CI `4486 passed, 3 warnings` em 3.12 (job 119000297346) e 3.10 (job 119000297561); corpo: `4486 passed, 3 warnings, 32 subtests passed`, exit 0; arquivos da ET `67 passed` | Atende |
| E2e: 7 `EXIT:0` e linhas ⏭️ | corpo, seção "E2e": script igual ao da ET; `crap`, `dry`, `deps`, `coverage`, `crap,dry,deps,coverage`, `padrao`, `pt-BR` todos `EXIT:0`; ``- ⏭️ `crap`: not run (no code to measure)``, ``- ⏭️ `coverage`: not run (no code to measure)`` e ``- ⏭️ `crap`: não executado (nenhum código a medir)`` | Atende |
| `bob check … crap,dry,deps,mutate,coverage` → 0 | corpo: exit 0 em `953f91b`, 5 gates `passed`, diff coverage 100%, 0 sobreviventes, 0 sem teste; comentário do `bob` no PR (CI, `crap,dry,deps,mutate`): 4 ✅, `_measure` CRAP 4.0 e `_skipped_without_code` CRAP 3.0 (CC 3, 100%), "No surviving mutants", "No mutants without tests" | Atende |
| Nenhum waiver novo | tabela de waivers do comentário: 16 entradas, todas de 2026-10-11 | Atende |
| 6 checks verdes no head | tabela abaixo, todos `success` em `953f91b` | Atende |
| Corpo: referências | U4 (P9, P7, D14), Q1 = A (Emerson, 2026-10-20 21:18 UTC-3), PR #196 (passo 0 da T2), CT7, ADR 0015, `docs/adr/0003-exit-codes.md`, FR4.4, US3.1 | Atende |
| "Decisões tomadas: nenhuma" e Bloqueios | título `## Decisões tomadas: nenhuma`; `## Bloqueios` com "Nenhum." | Atende |
| Pronto para revisão, não mergeado | `draft: false`, `merged: false`, `state: open` | Atende |

## Checks no head `953f91b` (início 20/10 23:17 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| bob / check | bob, run 39532145546 | success (`BOB_GATES: crap,dry,deps,mutate`) | 27m12s |
| bob / cold | bob, run 39532145546 | success | 1m23s |
| CI / pytest (3.10) | CI, run 39532145544 | success, `4486 passed, 3 warnings` | 20m01s |
| CI / pytest (3.12) | CI, run 39532145544 | success, `4486 passed, 3 warnings` | 19m59s |
| package / dist | package, run 39532145583 | success | 1m25s |
| verify-install / linux-x64 | verify-install, run 39532145594 | success, 8 linhas `ok` (1, 2, 3, 4, 7, 8, 9a, 9b) | 3m48s |

## Observações (não reprovam)
- No passo 0 e no e2e do agente, `dry` saiu ⏭️ `not_run` com `0` por falta das dependências npm do plugin no ambiente dele. É o `0` que a ET aceita para `dry`; no CI, `dry` passou.
- Um 7º check, `Graphify Formal Verification` (app externo `graphify-labs`), deu `neutral` ("0/1 PR-changed function(s) verified · 1 not verified (1 unsupported)"). Não é um dos 6 exigidos.
- `mergeable_state: blocked` é a proteção da branch esperando revisão; não é conflito (`mergeable: true`).
- Não existe `source-manifest.json` em `aidlc-docs/`; a skill pede atualizá-lo, mas não há arquivo. Só o `traceability.json` foi atualizado.

## Registro
- 20/10/2026 23:50 (UTC-3): rodada 1 (ET v1, head `953f91b`): aprovado para checkpoint. `traceability.json` (U4 T1b `verified`, PR 197), `trace.md`, `code-generation-plan.md` e `T2.md` (v3, preparada para a base com a T1b) atualizados. O merge é do Emerson.
