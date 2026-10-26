# Verificação: ET-u3-gitleaks-T4 (v1) × PR #194
Verificado em 20/10/2026 15:20 (UTC-3) contra a ET v1. É a ET despachada (`/workspace/dispatch/u3-t4/T4.md`), idêntica byte a byte à do repositório de docs. Só leituras remotas (cursor-github), sem clone.
PR: https://github.com/fazedordecodigo/bob/pull/194 | branch `aidlc/u3-gitleaks/t4-secrets-gate` → `main` | head `85b35a2b86096620b5744d98b8e394970a5d0671` | base `e481ef6` | aberto, **pronto para revisão** (`draft: false`), não mergeado, `mergeable: true` (`mergeable_state: blocked`) | 1 commit (`85b35a2`, 20/10 13:28 UTC-3), +84/−2. PR aberto em 20/10 14:48 UTC-3.

## Veredito: Aprovado para checkpoint (contra a ET v1), com uma ressalva
Todos os critérios de aceite, R1 e R2 atendem. 0 rodadas de correção. A ressalva é a quebra de linha no CHANGELOG (ressalva 1), que é lacuna da ET, não desvio do PR.

## Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Exatamente 3 arquivos | `CHANGELOG.md` (+6), `src/bob_quality/secrets_gate.py` (+2/−2), `tests/test_secrets_scan.py` (+76/−0); `changed_files: 3`; o corpo traz `git diff --name-only` com os 3 | Atende |
| R1 | l.124 `binary = user_dirs.locate_binary("gitleaks")` no lugar de `shutil.which("gitleaks")`; `from bob_quality import user_dirs` entre os imports de `bob_quality`; `shutil` ficou sem uso (não aparece no arquivo no head) e o `import shutil` saiu; nada mais mudou no arquivo | Atende |
| R2 | `if binary is None: return _unmeasured(msg("tool.missing", tool="gitleaks"))` intacto; as únicas linhas removidas no diff são `import shutil` e a linha do `which` | Atende |
| Sem `which("gitleaks")` em src | `search_code` na `main` (e481ef6) acha só `src/bob_quality/secrets_gate.py`, e o diff tira essa ocorrência; `which(` não aparece no arquivo no head; o corpo traz `rg … src/` → EXIT 1 | Atende |
| Fixture `_empty_bob_home` | `@pytest.fixture(autouse=True)`, `def _empty_bob_home(monkeypatch, tmp_path)`, `monkeypatch.setenv("BOB_HOME", str(tmp_path / "bob-home"))`, exata | Atende |
| `test_gitleaks_in_bob_home_is_used_before_the_path` | stub em `BOB_HOME/bin` (imprime `8.30.1`, grava argv em `calls.jsonl`); stub no `PATH` com `exit 99`; afirma `versions == {"gitleaks": "8.30.1"}`, `calls[0]["argv"] == [binary, "--version"]`, todas as chamadas no binário de `BOB_HOME` e o stub do `PATH` não chamado | Atende |
| `test_gitleaks_only_in_bob_home_is_not_a_missing_tool` | `PATH` vazio, gitleaks só em `BOB_HOME`; `_seen(run) !=` o resultado de `tool.missing` (exit 4, `not_run`, `missing tool: gitleaks`) | Atende |
| Lista fechada; nenhum teste existente alterado | `tests/test_secrets_scan.py` +76/−0; os únicos `def test_` novos são os 2 da ET; o resto é ajudante (`_BOB_HOME_STUB`, `_install_bob_home`), sem teste extra | Atende |
| CHANGELOG | no topo de `## Unreleased`, en e pt-BR. Com os espaços normalizados, o texto é idêntico ao da ET. Cada parágrafo está quebrado em 2 linhas (ressalva 1) | Atende (com ressalva) |
| Linhas novas ≤ 100 colunas | a maior linha nova do diff tem 79 colunas | Atende |
| Suíte: 0 failed | CI `4430 passed, 3 warnings` em 3.10 e em 3.12 (4428 da T3 + 2); o corpo traz a suíte local `4430 passed`, EXIT 0 | Atende |
| Comandos focados e `BOB_HOME=/nao/existe` | o corpo traz os 3 arquivos com `74 passed`. `test_secrets_scan.py` dá `45 passed`, e `BOB_HOME=/nao/existe` dá `45 passed`, a mesma contagem | Atende |
| E2e manual | `bob setup` sem gitleaks no `PATH` (`command -v gitleaks` vazio) instala `gitleaks 8.30.1 in BOB_HOME/bin`; `bob check --gates secrets` → EXIT 0, sem `missing tool: gitleaks`, relatório com `Tools: gitleaks 8.30.1` e `secrets: passed` (exit ≠ 4) | Atende |
| `bob check … crap,dry,deps,mutate,coverage` → 0 | o corpo dá EXIT 0 e os 5 gates `passed`, `mutate` com 0 sobreviventes e 0 `no_coverage`, `coverage` 100%. No CI, o job `check` (`BOB_GATES: crap,dry,deps,mutate`) roda `run_check.sh` (`outcome=success`) e depois `propagate_exit.sh`, logo o `bob check` saiu 0 | Atende |
| 6 checks verdes | tabela abaixo, todos `success` no head `85b35a2` | Atende |
| Citações no corpo | U3, CT8, ADR 0019, FR2.1 e Q2 = A no Summary; "Decisões tomadas: nenhuma"; "Bloqueios: nenhum" | Atende |
| Entrega: pronto para revisão, sem rascunho | `draft: false`, sem Bloqueios | Atende |
| Não mergeado | `merged: false`, `state: open` | Atende |

## Checks no head `85b35a2` (início 20/10 14:48 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| bob / check | bob, run 39469330571 | success | 17m10s |
| bob / cold | bob, run 39469330571 | success | 1m23s |
| CI / pytest (3.10) | CI, run 39469330620 | success, `4430 passed, 3 warnings` | 19m35s |
| CI / pytest (3.12) | CI, run 39469330620 | success, `4430 passed, 3 warnings` | 13m06s |
| package / dist | package, run 39469330428 | success | 1m23s |
| verify-install / linux-x64 | verify-install, run 39469330431 | success, 8 linhas `ok` (passos 1, 2, 3, 4, 7, 8, 9a, 9b) | 3m12s |

## Ressalvas
1. **CHANGELOG em 2 linhas por parágrafo (lacuna da ET).** O texto de cada parágrafo tem 121 colunas, e a ET pede o texto exato e também "linhas novas ≤ 100 colunas", sem limitar a regra aos `.py`. O agente quebrou cada parágrafo em 2 linhas, o que no Markdown renderiza o mesmo texto. As entradas anteriores do CHANGELOG ficam numa linha só, acima de 100 colunas. Para as próximas ETs, vale dizer se a regra de largura vale para o CHANGELOG.

## Observações (não reprovam)
- No e2e, o agente acrescentou `src/a.py` e a ref `origin/main` para que o `bob check` chegasse à procura do binário: sem `src`, a config sai 4 antes do gate. É preparo do ambiente, não mudança no repo.
- O e2e foi colado em prosa com os resultados (EXIT, stdout e stderr vazios, trechos do relatório), não como bloco de saída bruta. Com stdout e stderr vazios, não havia mais o que colar.
- A contagem de sobreviventes do `mutate` não aparece no log do CI; a evidência é o exit 0 propagado mais o corpo do PR.

## Registro
- 20/10/2026 15:20 (UTC-3): aprovado contra a ET v1; `traceability.json` (U3 T4: `verified`, PR 194, `et_version` v1, `correction_rounds` 0) e `trace.md` (l.48) atualizados. Entregue ao Maestro. O merge é do Emerson.
