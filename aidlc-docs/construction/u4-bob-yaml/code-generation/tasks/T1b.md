# ET-u4-bob-yaml-T1b: Gates crap e coverage sem código a medir saem 0
Projeto: bob | Unit: u4-bob-yaml | Plano: aidlc-docs/construction/u4-bob-yaml/code-generation/code-generation-plan.md (passos P9, P7)
Repo: https://github.com/fazedordecodigo/bob | Branch base: `main` @ `0d85510b8fd9d578619ce6e7adbde231b66bdd85` (T1 mergeada, #195) | Branch da tarefa: `aidlc/u4-bob-yaml/t1b-no-code`
Versão: v1 (2026-10-20 21:45 UTC-3; aprovada pelo Emerson às 21:42). Roda depois da T1 e antes da T2. Origem: passo 0 da T2 (PR #196, rascunho, commit vazio `d90c24d` sobre `0d85510`): `bob check --base HEAD --gates crap` saiu `4` num projeto sem código com `include: ["."]` ("⏭️ `crap`: not run (coverage.py: No data to report.)"). Decisão Q1 = A do Emerson (2026-10-20 21:18 UTC-3): "Opção A: tratar como nada a medir (crap pulado, bob check sai 0), com uma ET nova antes da T2."

## Modo de execução
Você executa esta especificação de forma mecânica. Não tome decisões de produto, arquitetura, nomenclatura, biblioteca ou estrutura que não estejam escritas aqui. Se algo faltar, for contraditório, ou o código existente não bater com o descrito, NÃO improvise: pare, abra o PR como rascunho com o que estiver pronto e descreva o bloqueio na seção "Bloqueios".

Esta ET fixa o contrato (nomes, textos, regra de "sem código", estados e testes). O corpo de cada função é seu, desde que cumpra as regras e os testes.

## Objetivo
Quando `paths.include` não tem código a medir, o `bob check` marca os gates `crap` e `coverage` como ⏭️ `not_run` com o motivo "no code to measure" / "nenhum código a medir", sem rodar ferramenta e sem contar como erro de ferramenta: contribuem `0`, e o `bob check` sai `0` se nenhum outro gate falhar. Num projeto com código, nada muda (erro real de coverage segue `4`).

## Causa no código (lida em `0d85510`; não mude estes arquivos)
- `tools.py:157-177`: `_run` chama o coverage com `check=True`; saída ≠ 0 vira `ToolError(exc.stderr or exc.stdout)`. Num projeto sem código, o pytest sai `5` (aceito por `pytest_passed`), o `coverage combine` passa (`tools.py:136-141`) e o `coverage json` (`tools.py:121-133`) sai ≠ 0 com `No data to report.`.
- `suite_memo.py:157-168` (`_read_export`) guarda e relança o `ToolError`.
- `python_probe.py:39-43`: `ToolError` de `memo.python_json` → `ProbeResult.not_run(versions, msg("tool.detail", tool="coverage.py", detail=reason(exc)), CONFIG_OR_TOOL)` → `GateResult("crap", "not_run", "coverage.py: No data to report.\n")` (`probe.py:28-41`), devolvido com exit `4` por `crap_gate.py:33-37` e `:68-77`, e somado por `check.py:336-344` (`_worse`).
- O mesmo `ToolError` derruba o gate `coverage`: `coverage_gate.py:156-159` (`memo.python_xml` → `LanguageMiss("python", "tool", …)`) → `_judge` sem linguagem medida → `_unmeasured` (`coverage_gate.py:239-245`) → `not_run` com exit `4`.
- `dry` (`dry_gate.py:54-60`, `:101-102`): toda falha de ferramenta vira `not_run` com `0`. `deps` (`deps_gate.py:62-96`): sem pacote Python no include, `_cycle_components` e `_python_violations` não rodam o import-linter nos módulos e o veredito é `passed` com `0`; só sai `4` se o import-linter estiver ausente (`deps_gate.py:304-313`). Pela leitura: `dry` e `deps` saem `0` num projeto sem código; `crap` e `coverage` saem `4`. O passo 0 confirma isso medindo.

## Passo 0 — medir os gates num projeto sem código (antes de qualquer código)
Meça com o `bob` da `main` (`0d85510`), sem mudar nenhum arquivo do repo. Na raiz do checkout da branch da tarefa, ainda sem mudanças:
```sh
E=$(mktemp -d); H=$E/home; mkdir -p "$H"
python3 -m venv "$E/venv" && "$E/venv/bin/pip" install -q .
P="$E/venv/bin:/usr/bin:/bin"
if command -v node >/dev/null; then P="$(dirname "$(command -v node)"):$P"; fi
mkdir -p "$E/p0" && cd "$E/p0" && git init -q -b main
git config user.email e2e@example.invalid && git config user.name e2e
printf '%s\n' '# leia' > README.md && git add -A && git commit -qm init
env -i HOME="$H" LANG=C.UTF-8 PATH="$P" "$E/venv/bin/python" -c \
  'from pathlib import Path; from bob_quality.init_config import write_default_config as w; print(w(Path(".")))'
cat bob.yaml
for g in crap dry deps coverage crap,dry,deps,coverage padrao; do
  if [ "$g" = padrao ]; then set --; else set -- --gates "$g"; fi
  env -i HOME="$H" LANG=C.UTF-8 PATH="$P" bob check --base HEAD "$@"; echo "== $g EXIT:$?"
  grep -E '^- (✅|⚠️|❌|⏭️) ' .bob/report.md
done
cd -
```
Esperado pela leitura do código: `ConfigResult(state='created_no_code', include=('.',))`; `== crap EXIT:4`, `== dry EXIT:0`, `== deps EXIT:0`, `== coverage EXIT:4`, `== crap,dry,deps,coverage EXIT:4`, `== padrao EXIT:4`.
- `dry` ou `deps` com `EXIT:` ≠ `0`: PARE. Esta ET não cobre esse gate. Não implemente nada, não contorne (não mude `bob.yaml`, gates, ambiente nem o comando). Faça um commit vazio na branch da tarefa (`git commit --allow-empty -m "ET-u4-bob-yaml-T1b: passo 0 bloqueado"`), abra o PR como rascunho com o título da Entrega e ponha em "Bloqueios" o bloco de comandos, a saída inteira (stdout, stderr e as linhas do relatório) e os `EXIT:`. Termine aí.
- `crap` ou `coverage` com `EXIT:` fora de {`0`, `4`}: PARE do mesmo jeito.
- Caso contrário: cole o bloco e a saída na seção "Passo 0" do corpo do PR e siga com o resto da ET. Se `crap` ou `coverage` já saírem `0`, registre isso no "Passo 0" e siga mesmo assim.

## Leia antes (somente leitura)
- `src/bob_quality/check.py` (números de `0d85510`): imports (linhas 9-44; `from bob_quality.config import Config, ConfigError, load_config` na linha 11), `DEFAULT_GATES` (linha 46), `_measure` (linhas 162-196; o laço `for gate in gates:` nas linhas 179-193), `_absorb` (199-262), `_absorb_remaining` (301-316: precedente de `not_run` com `PASSED`), `_record` (336-344), `_worse` (407-408).
- `src/bob_quality/config.py`: `_SUFFIX_LANGUAGE` (linhas 25-33: `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`), `detect_languages` (320-326), `_scan` (387-400: não segue symlink, pula o que casa com `exclude`, ignora raiz de include que não existe), `_note` (410-414), `_excluded` (417-425). É a mesma varredura que define `languages` quando o `bob.yaml` não grava a chave (`_detected`, linhas 380-384).
- `src/bob_quality/messages.py`: `"check.gate_not_implemented"` (en linha 88, pt-BR linha 485); `status.not_run` (en 224 "not run", pt-BR 624 "não executado"); `report.gate_reason` (en 233, pt-BR 633: ``- {mark} `{name}`: {status} ({reason})``).
- `src/bob_quality/report.py`: `GATE_MARK` (`"not_run": "⏭️"`).
- `tests/test_check_dispatch.py`: imports (linhas 3-28), `_forbid` (linhas 34-50), `test_absorb_unknown_gate_stays_not_run_and_exit_0` (linhas 579-608, modelo de asserção de `not_run`).
- `tests/test_check_report.py`: `test_a_missing_coverage_file_stays_a_tool_failure` (linhas 96-110; guarda de não regressão do `crap`, não muda), `_payload` (486-487), `_function_repo` (490-504), `_write` (507-510), `_git` (513-521).
- `tests/test_mutation_branches.py`: `test_absorb_records_every_gate_argument_and_result` (linhas 381-566; chama `check_mod._measure` nas linhas 443 e 538 com `tmp_path` vazio).

## Regras de comportamento
| # | Regra |
|---|---|
| R1 | "Sem código a medir" = `detect_languages(cwd, config.include, config.exclude)` devolve `()`: nenhum arquivo com sufixo de `_SUFFIX_LANGUAGE` sob as raízes de `config.include`, fora de `config.exclude`, sem seguir symlink. Use `config.include` e `config.exclude` como estão. A regra não lê saída de ferramenta nem compara texto de erro. |
| R2 | Constante nova em `check.py`, logo abaixo de `DEFAULT_GATES`: `_NEEDS_CODE = ("crap", "coverage")`. |
| R3 | Função privada nova em `check.py`, logo depois de `_measure`: `_skipped_without_code(state: _Measured, gate: str, cwd: Path, config: Config) -> bool`, docstring `"""Sem código no include, crap e coverage não têm o que medir: ⏭️ e exit 0."""`. Gate fora de `_NEEDS_CODE` → `False`, sem chamar `detect_languages`. Gate em `_NEEDS_CODE` com código (R1 falso) → `False`. Gate em `_NEEDS_CODE` sem código → `_record(state, GateResult(gate, "not_run", msg("check.no_code")), PASSED, {})` e `True`. |
| R4 | No laço de `_measure`, antes de `_absorb`: `if _skipped_without_code(state, gate, cwd, config): continue`. O resto de `_measure` não muda (o `SuiteMemo` continua criado com os mesmos argumentos e fechado no `finally`). Gate pulado não chama `run_crap_gate` nem `run_coverage_gate`: `state.metrics` fica `[]`, `state.baseline` fica `None`, `state.diff_coverage` fica `None`, e nenhuma versão de ferramenta entra em `state.versions`. |
| R5 | Chave nova `check.no_code` em `messages.py`, logo depois de `"check.gate_not_implemented"`, em `_EN` e em `_PT_BR`: en `no code to measure`; pt-BR `nenhum código a medir`. No relatório: ``- ⏭️ `crap`: not run (no code to measure)`` (en) e ``- ⏭️ `crap`: não executado (nenhum código a medir)`` (pt-BR); idem para `coverage`. |
| R6 | Import: a linha 11 de `check.py` vira `from bob_quality.config import Config, ConfigError, detect_languages, load_config`. Nenhum outro import muda. |
| R7 | Com código (R1 falso), o caminho é o de hoje, byte a byte: `crap_gate.py`, `coverage_gate.py`, `python_probe.py`, `suite_memo.py`, `tools.py`, `probe.py`, `exit_codes.py`, `config.py` e `report.py` não mudam. `coverage.py: No data to report.` num projeto com código segue `not_run` com exit `4`. Os códigos de saída e seus nomes não mudam. Os gates `dry`, `deps` e os demais não mudam. |

## Arquivos a modificar (lista fechada: 6 arquivos)
1. `src/bob_quality/check.py` — R2, R3, R4, R6.
2. `src/bob_quality/messages.py` — R5 (2 entradas).
3. `tests/test_check_dispatch.py` — ajustes de import e testes 1-3.
4. `tests/test_check_report.py` — testes 4 e 5.
5. `tests/test_mutation_branches.py` — ajuste abaixo.
6. `CHANGELOG.md` — no topo de `## Unreleased`, dois parágrafos (en, depois pt-BR), cada um seguido de linha em branco:
   - en: "`bob check` no longer exits `4` when `paths.include` has no code to measure (no `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` or `.cjs` file outside `paths.exclude`): the `crap` and `coverage` gates are skipped with the reason \"no code to measure\" and do not count as a tool failure (U4)."
   - pt-BR: "O `bob check` não sai mais `4` quando o `paths.include` não tem código a medir (nenhum arquivo `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` ou `.cjs` fora de `paths.exclude`): os gates `crap` e `coverage` são pulados com o motivo \"nenhum código a medir\" e não contam como falha de ferramenta (U4)."

## Arquivos proibidos
Qualquer outro. Em especial: `crap_gate.py`, `coverage_gate.py`, `python_probe.py`, `suite_memo.py`, `tools.py`, `probe.py`, `exit_codes.py`, `config.py`, `report.py`, `init_config.py`, `setup_cmd.py`, `docs/**`, `website/**`, `README*.md`, `scripts/` e a configuração de CI e de cobertura.

## Ajustes em testes existentes (lista fechada)
- `tests/test_check_dispatch.py`, imports: a linha 11 vira `from bob_quality.check import _Measured, _absorb, _assemble, _measure`; linha nova `from bob_quality.coverage_gate import CoverageOutcome` logo depois de `from bob_quality.config import Config` (linha 13).
- `tests/test_mutation_branches.py::test_absorb_records_every_gate_argument_and_result`: duas linhas novas logo depois de `from bob_quality import check as check_mod` (linha 384), antes de `config = …`: `(tmp_path / "src").mkdir()` e `(tmp_path / "src" / "app.py").write_text("X = 1\n")`. Nada mais muda no teste. Motivo: o teste mede `crap` e `coverage` por `_measure` num `tmp_path` sem código, e com a R4 esses gates passariam a ser pulados.
- `tests/test_check_report.py::test_a_missing_coverage_file_stays_a_tool_failure` passa SEM edição (projeto com código + erro real de coverage → `4`, motivo `coverage.py: No data to report.\n`). Se falhar, pare e descreva em "Bloqueios".
- Nenhum outro teste existente muda. Se outro teste quebrar por causa da R4 (por exemplo, um que meça `crap` ou `coverage` num diretório sem código), NÃO o edite: abra o PR como rascunho e ponha em "Bloqueios" o nome do teste, a falha e o ajuste proposto.

## Testes a escrever (nomes exatos; 5 funções, 10 casos coletados)
Em `tests/test_check_dispatch.py`, no fim do arquivo. `_run(tmp_path, config, gates)` abaixo é só abreviação de `_measure(tmp_path, config, "main", {}, 10.0, None, gates, tmp_path / "out", None, False, None)`; escreva a chamada inteira em cada teste (não crie helper). Todos chamam `_forbid(monkeypatch)` antes de qualquer `monkeypatch.setattr` dos gates.

| # | Teste | Dado / Quando / Então |
|---|---|---|
| 1 | test_measure_skips_crap_and_coverage_without_code | Dado `tmp_path / "README.md"` = `"# leia\n"`, `config = Config(include=(".",))`, `_forbid`, `check.run_dry_gate` = `dry(**kwargs)` que faz `seen.append("dry")` e devolve `(GateResult("dry", "passed"), [], 0, {"jscpd": "5.4.1"})`, `check.run_deps_gate` = `deps(*args)` que faz `seen.append("deps")` e devolve `(GateResult("deps", "passed"), 0, {"import-linter": "2.15"}, [])` → Quando `state = _run(tmp_path, config, ["crap", "coverage", "dry", "deps"])` → Então `state.gates == [GateResult("crap", "not_run", msg("check.no_code")), GateResult("coverage", "not_run", msg("check.no_code")), GateResult("dry", "passed"), GateResult("deps", "passed")]`; `state.exit_code == 0`; `seen == ["dry", "deps"]`; `state.metrics == []`; `state.baseline is None`; `state.diff_coverage is None`; `state.versions == {"jscpd": "5.4.1", "import-linter": "2.15"}`; `render(state.gates[0].reason, "en") == "no code to measure"`; `render(state.gates[0].reason, "pt-BR") == "nenhum código a medir"`. |
| 2 | test_measure_finds_no_code_outside_the_include_rule | `@pytest.mark.parametrize("case", ["fora-do-include", "excluido", "link", "outro-sufixo"])`. Dado, por caso: `fora-do-include`: `scripts/run.py` = `"X = 1\n"` e `src/README.md` = `"# leia\n"`, `Config(include=("src",))`; `excluido`: `tests/test_app.py` = `"X = 1\n"`, `Config(include=(".",), exclude=("tests",))`; `link`: `real/app.py` = `"X = 1\n"` e `src/app.py` symlink para `tmp_path / "real" / "app.py"`, `Config(include=("src",))`; `outro-sufixo`: `src/app.rb` = `"puts 1\n"` e `src/app.py.txt` = `"X = 1\n"`, `Config(include=("src",))`. `_forbid` → Quando `state = _run(tmp_path, config, ["crap", "coverage"])` → Então `state.gates == [GateResult("crap", "not_run", msg("check.no_code")), GateResult("coverage", "not_run", msg("check.no_code"))]` e `state.exit_code == 0`. |
| 3 | test_measure_runs_crap_and_coverage_when_there_is_code | `@pytest.mark.parametrize("path", ["src/app.py", "src/app.ts", "src/deep/app.cjs"])`. Dado `tmp_path / path` = `"X = 1\n"` (crie as pastas), `config = Config(include=("src",))`, `_forbid`, `check.run_crap_gate` = `crap(**kwargs)` que faz `seen.append("crap")` e devolve `(GateResult("crap", "not_run", msg("tool.detail", tool="coverage.py", detail="No data to report.\n")), [], 4, {"lizard": "1.24.1"}, 0)`, `check.run_coverage_gate` = `coverage(*args)` que faz `seen.append("coverage")` e devolve `CoverageOutcome(GateResult("coverage", "not_run", "No data to report.\n"), 4, {"diff-cover": "10.6.0"}, None)` → Quando `state = _run(tmp_path, config, ["crap", "coverage"])` → Então `seen == ["crap", "coverage"]`; `state.exit_code == 4`; `[gate.name for gate in state.gates] == ["crap", "coverage"]`; `render(state.gates[0].reason, "en") == "coverage.py: No data to report.\n"`; `state.versions == {"lizard": "1.24.1", "diff-cover": "10.6.0"}`. |

Em `tests/test_check_report.py`, logo depois de `test_a_missing_coverage_file_stays_a_tool_failure` (linha 110), usando os helpers `_git`, `_write`, `_payload` e `_function_repo` do arquivo:

| # | Teste | Dado / Quando / Então |
|---|---|---|
| 4 | test_a_repo_without_code_skips_crap_and_coverage_and_exits_0 | Dado `repo = tmp_path / "repo"` (criado), `_git(repo, "init", "-b", "main")`, `_git(repo, "config", "user.email", "bob-test@example.com")`, `_git(repo, "config", "user.name", "bob-test")`, `_write(repo, "README.md", "# leia\n")`, `_write(repo, "bob.yaml", 'paths:\n  include: ["."]\n')`, `_git(repo, "add", ".")`, `_git(repo, "commit", "-m", "base")` → Quando `run_check(repo, base="HEAD", gates=["crap", "coverage"])` → Então `== 0`; `_payload(repo)["gates"] == [{"name": "crap", "status": "not_run", "reason": "no code to measure"}, {"name": "coverage", "status": "not_run", "reason": "no code to measure"}]`; `_payload(repo)["exit_code"] == 0`; as linhas ``- ⏭️ `crap`: not run (no code to measure)`` e ``- ⏭️ `coverage`: not run (no code to measure)`` estão em `(repo / ".bob" / "report.md").read_text(encoding="utf-8").splitlines()`. Depois, Quando `run_check(repo, base="HEAD", lang="pt-BR")` (gates padrão) → Então `== 0`; `[gate["name"] for gate in _payload(repo)["gates"]] == ["crap", "dry", "deps"]`; `_payload(repo)["gates"][0]["status"] == "not_run"`; `_payload(repo)["exit_code"] == 0`; a linha ``- ⏭️ `crap`: não executado (nenhum código a medir)`` está nas linhas do `report.md`. |
| 5 | test_a_missing_coverage_file_keeps_the_coverage_gate_a_tool_failure | Dado `repo, base, _tip = _function_repo(tmp_path)` (tem `src/old.py` e `src/new.py`) → Quando `run_check(repo, base=base, gates=["coverage"], coverage_file=repo / "missing.coverage")` → Então `== 4`; `gate = _payload(repo)["gates"][0]`; `gate["name"] == "coverage"`; `gate["status"] == "not_run"`; `gate["reason"].strip() == "No data to report."`. |

## Comandos a rodar e resultado esperado
- `python -m pytest -q tests/test_check_dispatch.py tests/test_check_report.py tests/test_mutation_branches.py` → exit 0; `0 failed`.
- `python -m pytest -q` → exit 0; `0 failed`; sem `error`.
- `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → exit 0.
- `git diff --name-only origin/main...HEAD | sort` → exatamente `CHANGELOG.md`, `src/bob_quality/check.py`, `src/bob_quality/messages.py`, `tests/test_check_dispatch.py`, `tests/test_check_report.py`, `tests/test_mutation_branches.py`.
- E2e (cole no PR o script e a saída inteira). Na raiz do checkout da branch, com as mudanças:
  ```sh
  E=$(mktemp -d); H=$E/home; mkdir -p "$H"
  python3 -m venv "$E/venv" && "$E/venv/bin/pip" install -q .
  P="$E/venv/bin:/usr/bin:/bin"
  if command -v node >/dev/null; then P="$(dirname "$(command -v node)"):$P"; fi
  mkdir -p "$E/vazio" && cd "$E/vazio" && git init -q -b main
  git config user.email e2e@example.invalid && git config user.name e2e
  printf '%s\n' '# leia' > README.md && git add -A && git commit -qm init
  env -i HOME="$H" LANG=C.UTF-8 PATH="$P" "$E/venv/bin/python" -c \
    'from pathlib import Path; from bob_quality.init_config import write_default_config as w; print(w(Path(".")))'
  cat bob.yaml
  for g in crap dry deps coverage crap,dry,deps,coverage padrao; do
    if [ "$g" = padrao ]; then set --; else set -- --gates "$g"; fi
    env -i HOME="$H" LANG=C.UTF-8 PATH="$P" bob check --base HEAD "$@"; echo "== $g EXIT:$?"
    grep -E '^- (✅|⚠️|❌|⏭️) ' .bob/report.md
  done
  env -i HOME="$H" LANG=C.UTF-8 PATH="$P" bob check --base HEAD --lang pt-BR; echo "== pt-BR EXIT:$?"
  grep -E '^- (✅|⚠️|❌|⏭️) ' .bob/report.md
  cd -
  ```
  Esperado: os 7 `EXIT:` são `0`; nas rodadas com `crap` aparece ``- ⏭️ `crap`: not run (no code to measure)``; nas com `coverage`, ``- ⏭️ `coverage`: not run (no code to measure)``; na rodada `pt-BR`, ``- ⏭️ `crap`: não executado (nenhum código a medir)``. Se algum `EXIT:` não for `0`: não mude código fora da lista; abra como rascunho com a rodada, o `EXIT:` e as linhas do relatório em "Bloqueios".

## Critérios de aceite (todos binários)
- [ ] Passo 0 colado no corpo, com `dry` e `deps` em `EXIT:0` (se não, o PR é o rascunho do passo 0 e nenhum outro critério se aplica).
- [ ] O PR muda exatamente os 6 arquivos.
- [ ] `_NEEDS_CODE == ("crap", "coverage")`; `_skipped_without_code` existe com a assinatura e a docstring da R3 e é chamada só no laço de `_measure`; a linha 11 de `check.py` é a da R6.
- [ ] `check.no_code` existe em `_EN` e `_PT_BR`, logo depois de `check.gate_not_implemented`, com os textos exatos.
- [ ] Os 5 testes novos existem com os nomes exatos e passam (10 casos); só os ajustes listados mudaram em testes existentes; `test_a_missing_coverage_file_stays_a_tool_failure` está sem edição e passa.
- [ ] Suíte inteira: 0 failed, 0 errors.
- [ ] E2e colado: 7 `EXIT:0` e as linhas ⏭️ com os textos exatos em en e pt-BR.
- [ ] `bob check … crap,dry,deps,mutate,coverage`: exit 0.
- [ ] Checks do PR verdes (os 6: `bob / check`, `bob / cold`, `CI / pytest (3.10)`, `CI / pytest (3.12)`, `package / dist`, `verify-install / linux-x64`).
- [ ] Corpo do PR cita U4, Q1 (Emerson, 2026-10-20 21:18 UTC-3), PR #196 (passo 0 da T2), CT7, ADR 0015, `docs/adr/0003-exit-codes.md`, FR4.4, US3.1, e traz "Decisões tomadas: nenhuma".
- [ ] O PR não foi mergeado pelo agente.

## Restrições
- ≤ 100 colunas nas linhas novas de código e testes; no CHANGELOG.md, cada entrada pode quebrar em várias linhas de ≤ 100 colunas, mantendo o texto exato da ET (quebra só em espaço).
- Literais que geram mutante equivalente: não escreva argumento com o valor padrão, conversão redundante nem comparação desnecessária. Em especial: teste de verdade direto (`if detect_languages(cwd, config.include, config.exclude):`), sem `len(...)`, sem `== ()`, sem `bool(...)`, sem `tuple(...)` em volta de `config.include`/`config.exclude`; `GateResult(gate, "not_run", msg("check.no_code"))` posicional, sem `reason=`; nenhum parâmetro novo com valor padrão.
- Não mudar mensagens existentes, a ordem dos gates, `DEFAULT_GATES` nem os códigos de saída.
- Não pular, desabilitar nem marcar testes como skip/only.
- Lista de testes fechada. Se o gate `mutate` deixar mutante sobrevivente que só um teste fora da lista mataria, NÃO acrescente o teste: abra o PR como rascunho e descreva em "Bloqueios" o mutante (arquivo, linha, mutação) e o teste proposto (nome e Dado / Quando / Então).
- Nenhum waiver novo.
- Bloqueio que surgir depois de o PR estar aberto vai só na seção Bloqueios do corpo; não tente voltar o PR para rascunho.

## Fora de escopo
- Docs de exit codes (`docs/exit-codes.md`, `docs/adr/0003-exit-codes.md`, `website/i18n/pt-BR/…/exit-codes.md`) e README: vão para a T1c (ET separada, depois da T3).
- Os gates `mutate`, `typing`, `security`, `supply`, `cognitive`, `test_smells`, `secrets` e `dead_code` num projeto sem código.
- Código só em pasta que o coverage não acha (por exemplo, `.py` dentro de pasta com ponto sob `include: ["."]`): R1 conta como código, e o caminho segue o de hoje.
- O passo `bob.yaml` do `bob setup` (T2) e o harness (T3).

## Entrega
PR para `main` com título "ET-u4-bob-yaml-T1b: Gates crap e coverage sem código a medir saem 0". Corpo: "Resumo", "Passo 0" (comandos, saída e os `EXIT:`), "Arquivos", "Testes" (os 5 nomes, os 10 casos e os ajustes), "Comandos" (cada comando com a saída), "E2e" (o script e a saída inteira), "Decisões tomadas: nenhuma", "Bloqueios" (vazio ou a lista), e as referências U4, Q1 (Emerson, 2026-10-20 21:18 UTC-3), PR #196, CT7, ADR 0015, `docs/adr/0003-exit-codes.md`, FR4.4, US3.1. Sem bloqueio, abra o PR pronto para revisão (não como rascunho); rascunho só quando houver item em "Bloqueios".
