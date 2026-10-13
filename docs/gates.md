# Gates

[Índice](README.md) · [Visão geral](visao-geral.md) · [CLI](cli.md) · [Configuração](configuracao.md) · [Exit codes](exit-codes.md) · [Relatórios](relatorios.md) · [SPEC](SPEC.md)

Seis gates. Cada um devolve um status `passed`, `warn`, `failed` ou `not_run`. O Markdown traduz para passou, aviso, falhou e não executado, com ✅ ⚠️ ❌ ⏭️ (`GATE_MARK` em `src/bob_quality/report.py`). Um gate que não rodou fica ⏭️ com motivo. Ele não aparece como ✅.

O exit code do `bob check` é o maior entre os gates que rodaram. Aviso não aumenta o código. Ver [Exit codes](exit-codes.md).

| Gate | Ferramenta | O que bloqueia | Exit quando bloqueia |
|---|---|---|---|
| [CRAP](#crap) | lizard + coverage.py ou c8/vitest | função no escopo com CRAP ≥ limite | `1` |
| [DRY](#dry) | jscpd | nada; clone novo é aviso | `0` |
| [Mutação](#mutação) | mutmut (Python), StrykerJS (TypeScript) | sobrevivente sem waiver | `3` |
| [Dependências](#dependências) | import-linter, dependency-cruiser, mais a regra de ciclo | violação cuja origem, destino ou outro módulo do ciclo está no diff | `1` |
| [Segredos](#segredos) | gitleaks | segredo novo no diff | `1` |
| [Código morto](#código-morto) | vulture e knip | nada; símbolo morto cuja definição está no diff é aviso | `0` |

Versões pinadas: lizard 1.24.1, coverage 7.16.2, c8 12.0.0, vitest 5.0.3, jscpd 5.4.1, mutmut 3.8.0, `@stryker-mutator/core` 10.0.0, `@stryker-mutator/vitest-runner` 10.0.0, import-linter 2.15, grimp 3.17, dependency-cruiser 18.5.0, gitleaks 8.30.1, vulture 2.16, knip 6.41.0. Node `>=22.14.0 <23`. Fonte: `pyproject.toml`, `package.json` e `doctor.py`. O doctor lê os pinos pip do Requires-Dist instalado.

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

## Mutação

A cobertura mostra que a linha rodou. A mutação altera o código e roda a suíte de novo. Se um teste falha, o mutante morreu (`killed`). Se a suíte passa, ele sobreviveu (`survived`). Os outros status no modelo são `timeout` e `no_coverage` (`models.py`). `no_coverage` significa que nenhum teste executou o mutante. O adaptador do mutmut 3.8 mapeia “no tests”, “skipped”, “not checked” e “check was interrupted by user” para `no_coverage`.

Não há status separado para mutante equivalente. A skill `harden` manda registrar um waiver. O waiver é `arquivo::função`, para todo sobrevivente da função, ou o Alvo da tabela de sobreviventes, `arquivo::função::<descrição>`, para um só. A descrição é o operador do mutante. `bob waive` recusa com exit `4` um alvo que nenhum sobrevivente do último relatório tem. Ver a [ADR 0006](adr/0006-chave-estavel-do-waiver.md).

O bob muta Python com mutmut e TypeScript com Stryker. O mutmut roda em `<--out>/mutmut/`, uma pasta de links simbólicos para o topo do repo, e nunca escreve o `setup.cfg` nem o `mutants/` do repo. O arquivo incremental do Stryker fica em `.bob/stryker-incremental.json` (ou `<--out>/stryker-incremental.json`). Ele não entra em `.bob/mutation-cache.json`. Os mutantes do último relatório do Stryker ficam em `<--out>/stryker-mutants.json`, para `bob waive`. A Action restaura só o cache do mutmut.

Antes de mutar, a baseline roda. Se o `crap` já mediu o pytest na mesma execução, esse código é reusado. Baseline quebrada: o gate fica `not_run` e o exit é `2`.

Entram na mutação as funções alteradas no diff e as funções do cache que ainda têm sobrevivente sem waiver (`_candidate_keys`). O cache é `.bob/mutation-cache.json` (ou `<--out>/mutation-cache.json`). Cada função guarda o sha256 do texto entre `start_line` e `end_line`, a versão do mutmut e a impressão da suíte. A impressão (`suite_fingerprint`) é o sha256 dos arquivos versionados ou não ignorados que a suíte lê: diretórios `tests/` e `test/`, `conftest*`, `test_*.py`, `*_test.py`, `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, lockfiles (`uv.lock`, `poetry.lock`, `Pipfile.lock`, `pdm.lock`) e o `also_copy` do mutmut. `__pycache__`, `mutants/` e `.bob/` ficam de fora.

Se a versão do mutmut ou a impressão da suíte diferir da chave do arquivo, `_read_cache` devolve vazio e o cache inteiro deixa de ser reusado. Função com hash diferente, ou com sobrevivente ainda sem waiver, é mutada de novo. `--since-last-run` não liga nem desliga isso; o cache já é o caminho padrão.

A Action restaura e publica o artefato `bob-mutation-cache` com esse JSON (`.github/actions/bob/action.yml`) e o guarda por 7 dias (`retention-days: 7`). Falha ao restaurar não interrompe o check (`restore_cache.py || echo ...` no workflow da action). A action também instala o Node `22.14.0` e o jscpd `5.4.1` antes do check, senão o dry fica `not_run`.

O limite efetivo é zero sobreviventes sem waiver numa linha do lado novo do diff (`git diff --unified=0`, âncora de hunk vazio incluída) e zero `no_coverage` nas funções do diff. Um sobrevivente nessas linhas, ou um `no_coverage` nessas funções, deixa o gate `failed` e o exit `3`. Sobrevivente sem waiver fora dessas linhas continua na tabela, com a nota `fora do diff; não bloqueia`, e não muda o exit. Sem arquivo, ou com linha menor ou igual a zero, o sobrevivente sem waiver ainda bloqueia. `killed` e `timeout` não entram nessa lista. Sobrevivente com waiver continua na tabela de sobreviventes, com a justificativa, e não conta para o `3`. Um waiver não cobre `no_coverage`. A seleção do que mutar continua por função (`_candidate_keys`).

`no_coverage` nas funções medidas muda o status do gate para `failed` quando não há sobrevivente que bloqueia, e o relatório ganha a seção “Mutantes sem teste”, com total e contagem por função e arquivo (`no_coverage_summary`, `_no_coverage_lines`). A linha do total diz que bloqueia. O exit é `3`. `tests/test_mutate.py` cobre essa falha. A decisão 11 da [SPEC](SPEC.md) é essa regra.

## Dependências

O gate roda as regras que o repositório já declara e soma uma regra sempre ativa que proíbe ciclo.

- Python, se `python` está em `languages`: import-linter com o arquivo `dependencies.python` (padrão `.importlinter`), mais ciclos pelo grafo do grimp (`deps_gate.py`).
- TypeScript, se `typescript` está em `languages`: dependency-cruiser com `dependencies.typescript` (padrão `.dependency-cruiser.cjs`).

O nome da regra de ciclo no JSON (sempre inglês) é `Forbidden dependency cycle`. No `report.md` em `pt-BR` é `Proibido ciclo de dependência`. Uma regra do dependency-cruiser sem nome fica `dependency` no JSON e `dependência` no Markdown.

Uma violação bloqueia quando a origem, o destino, ou outro módulo do mesmo componente fortemente conexo, está no diff (`_edge_in_diff`). As outras aparecem em “Informação (dependências fora do diff)” e não mudam o exit code. Zero violações no diff: `passed` e exit `0`. Uma no diff: `failed` e exit `1`.

Ferramenta ausente que impede a medição pedida deixa o gate `not_run` e o exit `4` (`ToolError` em `run_deps_gate`). O mesmo exit `4` vale para um JSON do dependency-cruiser que não é objeto ou não traz a lista `violations`, e para o import-linter com exit 0 cuja última linha `Contracts:` não é `N kept, 0 broken.`

## Segredos

Este gate não entra na lista padrão do `bob check`. O comando é `bob check --gates secrets`. Ele roda `gitleaks detect --no-git` com o gitleaks 8.30.1 nas raízes de `paths.include`.

Um segredo numa linha nova do diff, sem waiver, deixa o gate `failed` e o exit `1`. O id do waiver é a string inteira `secret:<regra>:<arquivo>:<linha>`. O id não leva o valor. `bob waive` grava esse id em `.bob/waivers.yaml`.

Um achado fora do diff aparece no Markdown e não muda o exit. O status fica `passed` e o exit fica `0`. Um achado com waiver não entra em nenhuma das duas listas.

A chave `secrets` no `bob.yaml` fica vazia. Ausente, `secrets:`, `secrets: null` e `secrets: {}` são o mesmo mapeamento e não ligam o gate.

O JSON inclui `secrets` só quando o gate mediu. O array traz os achados que bloqueiam. Cada objeto tem `file`, `line` e `rule_id`. Sem medição, a chave não aparece.

A seção `## Segredos` fica depois de `## Mutantes sem teste` e antes de `## Código morto`, quando esse gate rodou, e antes de `## Como reproduzir`. Sem medição, a seção não aparece. A saída bruta do gitleaks fica fora de `.bob/`.

Um arquivo `.gitleaksignore` numa raiz de include deixa o gate `not_run` e o exit `4`, antes de chamar o binário. As entradas vão para `.bob/waivers.yaml`.

## Código morto

O nome em `--gates` é `dead_code`. Ele não entra em `DEFAULT_GATES` (`crap,dry,deps`), no hook `pre-push` nem no default da Action. Não há subcomando `bob dead_code`.

O gate avisa e não muda o exit code. Python roda `python -m vulture` com o vulture 2.16. TypeScript roda `npx --no-install --prefix <pacote do bob> knip --reporter json --no-progress` com o knip 6.41.0. O knip não recebe `dead_code.min_confidence`.

Entra no ledger o símbolo cuja linha de definição está no lado novo do diff. Uma edição só do corpo, que não toca essa linha, não avisa. Símbolo fora de `paths.include`, ou com um componente de `paths.exclude` no caminho, fica de fora. O relatório lista os símbolos que restam, um por linha. No Markdown em `pt-BR` o tipo sai traduzido (`função`, `exportação`, `código inalcançável`). O campo `kind` do JSON guarda o token em inglês.

`dead_code.min_confidence` ausente ou nulo não passa `--min-confidence`. O vulture usa o próprio default, inclusive `[tool.vulture]` do repositório. Em `vulture.config.DEFAULTS` da versão pinada esse default é 0. O valor `0`, quando a chave está presente, passa `--min-confidence 0` e vale mais que o `pyproject.toml`. A chave é um inteiro de 0 a 100. `101`, `-1`, `true` e `1.5` fazem `check`, `doctor` e `waive` saírem com `4`, em inglês no stderr, sem gravar relatório.

Um waiver com o id exato `dead:<arquivo>:<linha>:<nome>` tira esse símbolo do aviso. O mesmo id não dispensa um mutante.

Exit 3 do vulture, com o relatório parseado, é medição. O bob não copia esse 3. Exit 0 com stdout só de espaço em branco é medição vazia. Exit 0 com outra saída, exit 1, exit 2, outro exit ou uma linha ilegível deixam a metade Python sem medição.

Exit 0 ou 1 do knip com JSON válido é medição, inclusive quando o knip sai 1 porque achou algo. O bob não copia esse 1. Exit 1 sem JSON, exit 2, crash ou documento inválido deixam a metade TypeScript sem medição. Arquivo, dependência e as outras chaves que não são símbolo ficam de fora. As listas de símbolo são `exports`, `types`, `enumMembers`, `namespaceMembers`, `nsExports` e `nsTypes`.

Se uma linguagem mediu e a outra não, o status segue o ledger medido. Ledger limpo é `passed`. Símbolo no diff sem waiver é `warn`. O motivo da linguagem que faltou continua na linha do gate. Isso não força `warn` e não usa exit `4`. Sem nenhuma medição, o status é `not_run` e o exit continua `0`. O relatório é gravado nos dois casos.

A seção `## Código morto` sai só quando o gate foi pedido, depois de `## Segredos` quando essa seção existe, e antes de `## Como reproduzir`. O JSON traz `dead_code` depois de `exit_code` nesse caso e omite a chave quando o gate não rodou. `schema_version` continua 1. O `reason` do JSON fica em inglês.

## Monorepo e Node ausente

Decisão 10 da [SPEC](SPEC.md), implementada em `crap_gate.py` e `deps_gate.py`:

- Com Python e TypeScript na lista, falta de Node não é exit `4` para o CRAP nem para deps. Python segue medido. O motivo do TypeScript é anexado. Se o veredito Python era `passed`, o gate passa a `warn`. Se já era falha, o status de falha permanece e o motivo cita os dois.
- Repositório só TypeScript sem Node: a ferramenta ausente impede a medição pedida e o exit é `4`.

O DRY, sozinho, trata Node ausente como `not_run` com exit `0`, também num repo só Python.
