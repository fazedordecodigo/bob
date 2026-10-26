# Verificação: ET-u4-bob-yaml-T1 (v2) × PR #195
Rodada 2 verificada em 20/10/2026 20:3x (UTC-3) contra a ET v2 (`T1.md`; v1 em `T1-v1.md`), base `main` @ `0b4c6ec`. Só leituras remotas (cursor-github), sem clone.
PR: https://github.com/fazedordecodigo/bob/pull/195 | branch `aidlc/u4-bob-yaml/t1-init-config` → `main` | head `49cd38b0dcee8eb19aa65624c6045b3e3e4e52c8` | base `0b4c6ec4e61f653fe8235b3ed20306a69ca46bcc` | aberto, pronto para revisão (`draft: false`), não mergeado, `mergeable: true` (`mergeable_state: blocked`) | 3 commits, +529/−0.
Commits: `c8e4f52` (20/10 17:50 UTC-3, entrega), `4fea23f` (19:02, correção 1: `json.dumps` e `encode("utf-8")`), `49cd38b` (19:37, correção 2: `encode()` e teste 24, conforme a ET v2).

## Veredito: Aprovado para checkpoint (contra a ET v2)
Os dois desvios da rodada 1 estão resolvidos e todos os critérios da v2 atendem. 2 rodadas de correção. A 2ª veio da mudança da ET (v2: R7 com `.encode()` e teste 24 para o mutante `ensure_ascii=False → None`), não de nova falha do agente.

## Rodada 2: critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Desvio 1 (R6) resolvido | `init_config.py:72-73`: `def _quote(item: str) -> str: return json.dumps(item, ensure_ascii=False)`; sem `JSONEncoder`, sem a guarda e sem `RuntimeError` no arquivo | Atende |
| R7 (v2) com `.encode()` | `init_config.py:132`: `tmp.write_bytes(render_config(include).encode())`; o resto de R7 é igual ao da rodada 1 (l.129-137) | Atende |
| Teste 24 conforme a ET | `test_quote_passes_ensure_ascii_false` (fim do arquivo): espião em `init_config.json.dumps` grava os kwargs e chama o `json.dumps` real; `render_config(("true",))`; `len(seen) == 1`, `seen[0]["ensure_ascii"] is False`, linha 4 `'  include: ["true"]'`; `import json` novo no arquivo de testes | Atende |
| Os outros 23 testes não mudaram | entre o head `c8e4f52` e o `49cd38b`, `tests/test_init_config.py` só ganhou `import json` e o teste 24 (+16 linhas, 0 alteradas); 24 `def test_`; coleta `46 tests collected` (45 + 1) | Atende |
| Restante do módulo inalterado | entre os dois heads, `init_config.py` só trocou as l.73-75 pela l.73 (−2 linhas); `CHANGELOG.md` idêntico ao da rodada 1 | Atende |
| Exatamente 3 arquivos | `changed_files: 3` (`CHANGELOG.md` +8, `init_config.py` +137, `test_init_config.py` +384); diff contra a base sem linhas removidas | Atende |
| Larguras, URLs, skips | maior linha nova: 88 (módulo) e 95 (testes); CHANGELOG 99/99/36 e 100/100/29, quebrado só em espaço; nenhum `https?://`, `skip`, `xfail`, `noqa` ou `pragma` | Atende |
| Contrato, R1–R5, texto do render, testes 1–23 | inalterados desde a rodada 1, onde atenderam (ver abaixo) | Atende |
| Suíte: 0 failed | CI `4476 passed, 3 warnings` em 3.10 e em 3.12 (4475 + 1); o corpo traz `4476 passed`, exit 0 | Atende |
| `bob check … mutate …` → 0 | o corpo dá exit 0, os 5 gates `passed`, 0 sobreviventes, 0 sem teste, cobertura do diff 100%, nenhum waiver novo; job `check` com `BOB_GATES: crap,dry,deps,mutate`, 11× `outcome=success` | Atende |
| 6 checks verdes no head novo | tabela abaixo, todos `success` em `49cd38b` | Atende |
| Corpo do PR | lista os 24 testes; saídas novas (46 coletados/passados, 4476 passed, paridade `True`, `rg` exit 1, `bob check` exit 0, `git diff` com 3 arquivos); "Decisões tomadas: nenhuma"; "Bloqueios" vazio; referências U4, C05, CT7, ADR 0015, ADR 0017, FR4.1–FR4.6, NFR4, NFR5 | Atende |
| Pronto para revisão, não mergeado | `draft: false`, `merged: false`, `state: open` | Atende |

## Checks no head `49cd38b` (início 20/10 20:00 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| bob / check | bob, run 39512129591 | success | 23m44s |
| bob / cold | bob, run 39512129591 | success | 1m17s |
| CI / pytest (3.10) | CI, run 39512129741 | success, `4476 passed, 3 warnings` | 16m28s |
| CI / pytest (3.12) | CI, run 39512129741 | success, `4476 passed, 3 warnings` | 20m06s |
| package / dist | package, run 39512129894 | success | 1m11s |
| verify-install / linux-x64 | verify-install, run 39512129700 | success, 8 linhas `ok` (1, 2, 3, 4, 7, 8, 9a, 9b; passo 2 em 63 s, passo 7 em 1 s) | 3m37s |

## Registro
- 20/10/2026 18:5x (UTC-3): rodada 1 (ET v1, head `c8e4f52`): Correção, desvios R6 e R7.
- 20/10/2026 20:3x (UTC-3): rodada 2 (ET v2, head `49cd38b`): aprovado para checkpoint. `traceability.json` (U4 T1 `verified`, 24 testes, PR 195 com `et_version` v2 e `correction_rounds` 2) e `trace.md` (l.38) atualizados. Entregue ao Maestro. O merge é do Emerson.

---

## Rodada 1 (ET v1, head `c8e4f52`, 20/10 18:5x UTC-3): Correção
Dois desvios de conteúdo em `src/bob_quality/init_config.py`, os dois em regras da ET (R6 e R7). Todo o resto atende: arquivos, contrato, texto do render, os 23 testes, CHANGELOG, larguras, checks e corpo. Não marquei nada como `verified`, e `traceability.json` e `trace.md` ficam como estavam.

### Desvios
1. **R6, `init_config.py:72-75`.** A ET pede `json.dumps(item, ensure_ascii=False)`. O PR usa `json.JSONEncoder(ensure_ascii=False).encode(item)` e, na linha 74, `if encoder.ensure_ascii is not False: raise RuntimeError`. Esse é um ramo que nunca executa, fora da ET, numa linha com dois comandos. Pelo jeito, serve para matar um mutante. A ET manda outra coisa nesse caso: abrir o PR como rascunho e descrever em "Bloqueios" o mutante e o teste proposto, sem mexer no código. Correção: `_quote` passa a devolver `json.dumps(item, ensure_ascii=False)`, sem a guarda. Se o `mutate` deixar sobrevivente, siga a restrição da lista fechada.
2. **R7, `init_config.py:134`.** A ET pede `tmp.write_bytes(render_config(include).encode("utf-8"))`; o PR usa `.encode()`. O resultado é o mesmo, mas a chamada não é a da regra. Correção: `.encode("utf-8")`.

### Critério → evidência
| Critério / regra | Evidência | Resultado |
|---|---|---|
| Exatamente 3 arquivos | `changed_files: 3`: `CHANGELOG.md` (+8), `src/bob_quality/init_config.py` (novo, +139), `tests/test_init_config.py` (novo, +368); o corpo traz o `git diff --name-only` com os 3 | Atende |
| Contrato: nomes e assinaturas | `CONFIG_NAME = "bob.yaml"` (l.16), `ConfigState` (l.17), `ConfigResult(state, include)` congelada (l.20-23), `render_config(include: Sequence[str]) -> str` (l.49), `write_default_config(project: Path) -> ConfigResult` (l.54) | Atende |
| Docstrings | módulo (l.1) e `write_default_config` (l.55), iguais às da ET; docstring do arquivo de testes (l.1) igual | Atende |
| Imports permitidos | `json`, `os`, `Sequence`, `dataclass`, `Path`, `Literal`, `yaml`, `from bob_quality import suite_fingerprint`, `from bob_quality.config import DEFAULT_EXCLUDE, _SUFFIX_LANGUAGE, _excluded, load_config`, `parse_yaml`. Nenhum outro. `_listed_files` por atributo (l.107), `load_config` pelo nome (l.135), `os.replace` (l.136) | Atende |
| R1 | `_already_there`: `target.exists() or target.is_symlink()` (l.86-87), antes de qualquer outra ação (l.57-58) | Atende |
| R2 | `suite_fingerprint._listed_files(project)` (l.107); `ToolError` não é capturado | Atende |
| R3 | `_is_code` (l.122-128): sufixo em `_SUFFIX_LANGUAGE`, `is_file()` e não link, `not _excluded(Path(name), tuple(DEFAULT_EXCLUDE))` | Atende |
| R4 | `_absorb` (l.113-119): sem `/` → código na raiz; senão 1º componente, se não começa com `.` | Atende |
| R5 | `_selection` (l.90-96) e `_dot_state` (l.99-101): `src` › `sorted` › `"."` `created` › `"."` `created_no_code` | Atende |
| R6 | `.` → `"."` (l.65-66); plano via `parse_yaml("[" + item + "]") == [item]`, com `yaml.YAMLError` → False (l.78-83); aspas por `JSONEncoder` com guarda morta (l.72-75) | **Não atende** (desvio 1) |
| R7 | `bob.yaml.tmp-{os.getpid()}` (l.132); `write_bytes` → `load_config(tmp, project)` → `os.replace` dentro do `try`; `except Exception: tmp.unlink(missing_ok=True); raise` (l.133-139); `.encode()` sem `"utf-8"` (l.134) | **Não atende** (desvio 2) |
| Texto do render | `_BODY` (l.26-46), com `{include}` no lugar de `<INCLUDE>`, é igual byte a byte ao bloco da ET; 19 linhas, LF, `\n` no fim | Atende |
| Paridade com o README | o corpo traz o comando da ET → `True` | Atende |
| 23 testes, nomes exatos | 23 `def test_`, nomes iguais aos da ET; coleta `45 tests collected` (3+9+1+1+7+1+1+2+1+2+1+1+1+1+3+1+1+1+1+3+1+1+1 = 45) | Atende |
| Parametrizações e asserções | conferidas uma a uma contra a tabela: 1 (3 casos, literal, `\n`, 19 linhas, sem `languages`/`\r`), 2 (9 casos, linha 4 e leitura de volta), 3–14, 15 (file/link/dir, git e `load_config` proibidos, sem temporário), 16 (espião: caminho, cwd, texto, `False`; `bob.yaml` existe, temporário não), 17–19, 20 (3 casos, `include`, `exclude`, `base`, `language`), 21 (espião chamado com `repo`), 22 (`git.ls_files_failed`, sem `bob.yaml`), 23 (bytes e `st_mtime_ns`) | Atende |
| Sem teste extra; nenhum existente alterado | só ajudantes (`_git`, `repo`, `_write`, `_temps`, `_CT7`); o diff não tem linhas removidas | Atende |
| Sem skip/only | nenhum `skip`, `xfail`, `only`, `noqa`, `pragma` nem assert comentado | Atende |
| CHANGELOG | no topo de `## Unreleased`, en e pt-BR, cada um seguido de linha em branco. Juntando as quebras, o texto é idêntico ao da ET. Linhas de 99, 99, 36, 100, 100 e 29 colunas, quebradas só em espaço, sem espaço no fim | Atende |
| Linhas novas ≤ 100 colunas | maior linha: 88 em `init_config.py`, 95 nos testes | Atende |
| Sem URL nos testes | nenhuma ocorrência de `https?://` em `tests/test_init_config.py`; o corpo traz `rg` → exit 1 | Atende |
| Suíte: 0 failed | CI `4475 passed, 3 warnings` em 3.10 e em 3.12 (4430 da `main` + 45); o corpo traz `4475 passed`, exit 0 | Atende |
| `bob check … crap,dry,deps,mutate,coverage` → 0 | o corpo dá exit 0, os 5 gates `passed`, CRAP máx. 4.0, 0 sobreviventes, cobertura do diff 100%, nenhum waiver novo; job `check` com `BOB_GATES: crap,dry,deps,mutate`, `outcome=success` | Atende |
| 6 checks verdes | tabela abaixo, todos `success` no head `c8e4f52` | Atende |
| Corpo do PR | U4, C05, CT7, ADR 0015, ADR 0017, FR4.1–FR4.6, NFR4, NFR5; "Decisões tomadas: nenhuma"; "Bloqueios" vazio; a saída de cada comando | Atende |
| Pronto para revisão, não mergeado | `draft: false`, `merged: false`, `state: open` | Atende |

### Checks no head `c8e4f52` (início 20/10 18:37 UTC-3)
| Check | Workflow / run | Resultado | Duração |
|---|---|---|---|
| bob / check | bob, run 39501918611 | success | 15m09s |
| bob / cold | bob, run 39501918611 | success | 1m19s |
| CI / pytest (3.10) | CI, run 39501918519 | success, `4475 passed, 3 warnings` | 13m22s |
| CI / pytest (3.12) | CI, run 39501918519 | success, `4475 passed, 3 warnings` | 13m21s |
| package / dist | package, run 39501918600 | success | 1m03s |
| verify-install / linux-x64 | verify-install, run 39501918510 | success, 8 linhas `ok` (1, 2, 3, 4, 7, 8, 9a, 9b; passo 2 em 64 s, passo 7 em 1 s) | 3m59s |

### Observações (não reprovam)
- `_dot_state` (l.99-101) usa um dicionário `{True: …, False: …}` no lugar de um `if`. O comportamento é o de R5, e o corpo da função é do agente.
- `init_config.py` não tem `from __future__ import annotations`. A ET não pede, e as anotações rodam no 3.10.

### Registro da rodada 1
- 20/10/2026 18:5x (UTC-3): rodada 1, veredito Correção (desvios 1 e 2). Nada marcado como `verified`. A mensagem de correção vai ao MESMO agente pelo Maestro.
