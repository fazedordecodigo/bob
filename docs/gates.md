# Gates

[Índice](README.md) · [Visão geral](visao-geral.md) · [CLI](cli.md) · [Configuração](configuracao.md) · [Exit codes](exit-codes.md) · [Relatórios](relatorios.md) · [SPEC](SPEC.md)

Cinco gates. `test_smells` só roda quando `--gates` o pede. Cada um devolve um status `passed`, `warn`, `failed` ou `not_run`. O Markdown traduz para passou, aviso, falhou e não executado, com ✅ ⚠️ ❌ ⏭️ (`GATE_MARK` em `src/bob_quality/report.py`). Um gate que não rodou fica ⏭️ com motivo. Ele não aparece como ✅.

O exit code do `bob check` é o maior entre os gates que rodaram. Aviso não aumenta o código. Ver [Exit codes](exit-codes.md).

| Gate | Ferramenta | O que bloqueia | Exit quando bloqueia |
|---|---|---|---|
| [CRAP](#crap) | lizard + coverage.py ou c8/vitest | função no escopo com CRAP ≥ limite | `1` |
| [DRY](#dry) | jscpd | nada; clone novo é aviso | `0` |
| [Mutação](#mutação) | mutmut (Python), StrykerJS (TypeScript) | sobrevivente sem waiver | `3` |
| [Dependências](#dependências) | import-linter, dependency-cruiser, mais a regra de ciclo | violação cuja origem, destino ou outro módulo do ciclo está no diff | `1` |
| [Testes do diff](#testes-do-diff) | ast do Python e o eslint do repositório | nada; cheiro no diff é aviso | `0` |

Versões pinadas: lizard 1.24.1, coverage 7.16.2, c8 12.0.0, vitest 5.0.3, jscpd 5.4.1, mutmut 3.8.0, `@stryker-mutator/core` 10.0.0, `@stryker-mutator/vitest-runner` 10.0.0, import-linter 2.15, grimp 3.17, dependency-cruiser 18.5.0. Node 22.14.0. Fonte: `pyproject.toml`, `package.json` e `doctor.py`. O doctor lê os pinos pip do Requires-Dist instalado.

## CRAP

CRAP junta a complexidade ciclomática com a fração das linhas executáveis que os testes executaram. O núcleo está em `src/bob_quality/crap.py`:

```text
CRAP = CC² × (1 − cov)³ + CC
```

`CC` vem do lizard, nas duas linguagens. `cov` é uma fração de 0 a 1. Sem linhas executáveis no intervalo da função, a cobertura conta como 1 (`line_coverage` em `core.py`). Sem dados de cobertura para o arquivo, a fração é 0.

| CC | Cobertura | CRAP | Com limite 10 |
|---|---|---|---|
| 4 | 50% | 16 × 0,125 + 4 = 6 | passa |
| 5 | 0% | 25 + 5 = 30 | falha |
| 10 | 100% | 0 + 10 = 10 | falha |

O limite padrão é 10 (`crap.max_per_function`). A comparação é `crap >= max_crap` (`crap_verdict`). Uma função com CRAP 10 falha. Como o CRAP nunca fica abaixo do CC, CC 10 com cobertura total também falha no limite padrão. `--threshold` em `bob crap` substitui o limite nessa execução.

Com `crap.scope: changed` (padrão), só funções alteradas entram no veredito. Outro texto em `scope` inclui todas as funções medidas. Funções fora do diff com CRAP no limite ou acima vão para a seção informativa de dívida antiga e não mudam o exit code.

O gate roda a suíte para medir cobertura. Baseline quebrada (pytest com código fora de `0` e `5`; o `5` é “nenhum teste coletado” e conta como passou, `pytest_passed` em `exit_codes.py`) sai com `2`. Isso vale no `bob check` padrão, porque ele inclui `crap`.

Python: coverage.py rodando pytest. TypeScript: c8 rodando vitest. Os dois caminhos estão em `python_probe.py` e `typescript_probe.py`, escolhidos por `crap_gate.py` conforme `languages`.

## DRY

Um clone é um bloco que repete outro. O gate roda o jscpd com `duplication.min_tokens` (padrão 50) e fica com os clones em que pelo menos um lado toca uma linha alterada (`_new_clones` em `dry_gate.py`).

Um ou mais clones novos deixam o gate em `warn` e o exit em `0`. A linha do relatório traz os dois lados (`arquivo:início-fim`), a quantidade de linhas, os tokens e a similaridade (`85%`, ou `exata` quando o clone é `exact` e não há percentual). Sem clones novos, o status é `passed`.

Sem Node, ou sem o jscpd instalado, o status é `not_run` e o exit continua `0` (o retorno de `_skipped` é `PASSED`). O jscpd precisa de Node também num repositório só Python, se `dry` estiver na lista.

A spec marca clones novos como aviso no MVP. O código faz isso no gate. `duplication.new_clones` não está no schema: sai com `4`. Ver [Configuração](configuracao.md#chaves-que-o-loader-recusa).

## Testes do diff

O comando é `bob check --gates test_smells`. Não há subcomando `bob test_smells`. O nome fica fora de `DEFAULT_GATES`, do hook `pre-push` e do padrão da Action.

A contribuição de exit é sempre `0`. O status é `passed`, `warn` ou `not_run`.

O gate ignora `paths.include` e `paths.exclude`. Um arquivo em `tests/` entra mesmo com `tests` na lista de exclusão.

Python entra quando `python` está em `languages`. O nome do arquivo é `test_*.py` ou `*_test.py`. `conftest.py` e `__init__.py` ficam de fora. Um teste é uma função `test_*` no corpo do módulo, ou um método `test_*` numa classe de módulo cujo nome começa com `Test`.

| Regra | Quando aparece |
|---|---|
| `empty-test` | O corpo só tem docstring, `pass` e `...` |
| `missing-assert` | O corpo não tem asserção. Um corpo vazio fica só em `empty-test` |
| `disabled-test` | Uma linha alterada desliga o teste com `skip`, `skipif`, `skipIf`, `skipUnless`, `xfail` ou `importorskip`. Um skip que o diff não tocou não entra. O teste desligado não emite `empty-test` nem `missing-assert` |
| `sleep` | Uma chamada cujo nome é `sleep`, numa linha alterada dentro do teste. `time.sleep`, `asyncio.sleep` e `trio.sleep` contam. `sleeping` não conta. Uma função fora do teste não entra |

Um arquivo que não parseia não gera linha. Python continua medido.

TypeScript entra quando `typescript` está em `languages`. O nome termina em `.test.ts`, `.test.tsx`, `.test.js`, `.test.jsx`, `.test.mjs`, `.test.cjs`, ou o mesmo com `.spec` no lugar de `.test`. Um arquivo sob `__tests__` também entra quando o sufixo é `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` ou `.cjs`. `*.d.ts` fica de fora.

O gate procura no texto da configuração `eslint-plugin-jest`, `eslint-plugin-vitest`, `plugin:jest/` ou `plugin:vitest/`. A busca deixa de lado `node_modules`, `dist`, `.git` e `.bob`. Em `package.json` só o valor de `eslintConfig` conta. Sem marcador, o TypeScript é pulado e o eslint não inicia. Com marcador e sem teste alterado, a medição fica vazia e o eslint não inicia. O binário é `node_modules/.bin/eslint`, com `--format json` e os caminhos alterados. O `bob doctor` não pina esse eslint.

Exit `0` ou `1` com uma lista JSON entra na medição. Qualquer outro exit, ou uma saída que não é essa lista, deixa o TypeScript quebrado. Se nenhuma linguagem mediu, o status é `not_run` e o exit do processo continua `0`. Um TypeScript quebrado não muda o status do que já foi medido. O motivo do gate guarda o detalhe.

Cada linha do relatório está numa linha alterada do arquivo. O id do waiver é `tests:<arquivo>:<linha>:<regra>`. O waiver mantém a linha, copia o motivo e o status passa quando não sobra linha sem waiver. Esse id só casa com um mutante quando o id do mutante é a string inteira.

`test_smells: false`, `{}` e qualquer outro valor saem com `4` antes do gate, com stderr `bob.yaml: test_smells accepts only true` e sem relatório. Omitir a chave, `null` e `true` são o mesmo. O gate não lê o campo. Ver [Configuração](configuracao.md).

## Mutação

A cobertura mostra que a linha rodou. A mutação altera o código e roda a suíte de novo. Se um teste falha, o mutante morreu (`killed`). Se a suíte passa, ele sobreviveu (`survived`). Os outros status no modelo são `timeout` e `no_coverage` (`models.py`). `no_coverage` significa que nenhum teste executou o mutante. O adaptador do mutmut 3.8 mapeia “no tests”, “skipped”, “not checked” e “check was interrupted by user” para `no_coverage`.

Não há status separado para mutante equivalente. A skill `harden` manda registrar um waiver.

O bob muta Python com mutmut e TypeScript com Stryker. O arquivo incremental do Stryker fica em `.bob/stryker-incremental.json` (ou `<--out>/stryker-incremental.json`). Ele não entra em `.bob/mutation-cache.json`. A Action restaura só o cache do mutmut.

Antes de mutar, a baseline roda. Se o `crap` já mediu o pytest na mesma execução, esse código é reusado. Baseline quebrada: o gate fica `not_run` e o exit é `2`.

Entram na mutação as funções alteradas no diff e as funções do cache que ainda têm sobrevivente sem waiver (`_candidate_keys`). O cache é `.bob/mutation-cache.json` (ou `<--out>/mutation-cache.json`). Cada função guarda o sha256 do texto entre `start_line` e `end_line`, a versão do mutmut e a impressão da suíte. A impressão (`suite_fingerprint`) é o sha256 dos arquivos versionados ou não ignorados que a suíte lê: diretórios `tests/` e `test/`, `conftest*`, `test_*.py`, `*_test.py`, `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, lockfiles (`uv.lock`, `poetry.lock`, `Pipfile.lock`, `pdm.lock`) e o `also_copy` do mutmut. `__pycache__`, `mutants/` e `.bob/` ficam de fora.

Se a versão do mutmut ou a impressão da suíte diferir da chave do arquivo, `_read_cache` devolve vazio e o cache inteiro deixa de ser reusado. Função com hash diferente, ou com sobrevivente ainda sem waiver, é mutada de novo. `--since-last-run` não liga nem desliga isso; o cache já é o caminho padrão.

A Action restaura e publica o artefato `bob-mutation-cache` com esse JSON (`.github/actions/bob/action.yml`) e o guarda por 7 dias (`retention-days: 7`). Falha ao restaurar não interrompe o check (`restore_cache.py || echo ...` no workflow da action). A action também instala o Node `22.14.0` e o jscpd `5.4.1` antes do check, senão o dry fica `not_run`.

O limite efetivo é zero sobreviventes sem waiver. Qualquer um deixa o gate `failed` e o exit `3`. `killed`, `timeout` e `no_coverage` não entram nessa lista. Sobrevivente com waiver continua na tabela de sobreviventes, com a justificativa, e não conta para o `3`.

`no_coverage` muda o status do gate para `warn` quando não há sobrevivente sem waiver, e o relatório ganha a seção “Mutantes sem teste”, com total e contagem por função e arquivo (`no_coverage_summary`, `_no_coverage_lines`). O exit code não muda. `tests/test_mutate.py` cobre “warn without changing the exit code”. O [README.pt-BR.md](../README.pt-BR.md), na seção Status, ainda chama esse aviso de planejado. A decisão 11 da [SPEC](SPEC.md) separa o aviso (já no código) da fase 2, em que `no_coverage` nas funções do diff falharia com exit `3`. Essa fase 2 não está em `_finish`.

## Dependências

O gate roda as regras que o repositório já declara e soma uma regra sempre ativa que proíbe ciclo.

- Python, se `python` está em `languages`: import-linter com o arquivo `dependencies.python` (padrão `.importlinter`), mais ciclos pelo grafo do grimp (`deps_gate.py`).
- TypeScript, se `typescript` está em `languages`: dependency-cruiser com `dependencies.typescript` (padrão `.dependency-cruiser.cjs`).

O nome da regra de ciclo no JSON (sempre inglês) é `Forbidden dependency cycle`. No `report.md` em `pt-BR` é `Proibido ciclo de dependência`. Uma regra do dependency-cruiser sem nome fica `dependency` no JSON e `dependência` no Markdown.

Uma violação bloqueia quando a origem, o destino, ou outro módulo do mesmo componente fortemente conexo, está no diff (`_edge_in_diff`). As outras aparecem em “Informação (dependências fora do diff)” e não mudam o exit code. Zero violações no diff: `passed` e exit `0`. Uma no diff: `failed` e exit `1`.

Ferramenta ausente que impede a medição pedida deixa o gate `not_run` e o exit `4` (`ToolError` em `run_deps_gate`). O mesmo exit `4` vale para um JSON do dependency-cruiser que não é objeto ou não traz a lista `violations`, e para o import-linter com exit 0 cuja última linha `Contracts:` não é `N kept, 0 broken.`

## Monorepo e Node ausente

Decisão 10 da [SPEC](SPEC.md), implementada em `crap_gate.py` e `deps_gate.py`:

- Com Python e TypeScript na lista, falta de Node não é exit `4` para o CRAP nem para deps. Python segue medido. O motivo do TypeScript é anexado. Se o veredito Python era `passed`, o gate passa a `warn`. Se já era falha, o status de falha permanece e o motivo cita os dois.
- Repositório só TypeScript sem Node: a ferramenta ausente impede a medição pedida e o exit é `4`.

O DRY, sozinho, trata Node ausente como `not_run` com exit `0`, também num repo só Python.
