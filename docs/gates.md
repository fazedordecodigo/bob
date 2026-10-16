# Gates

[Índice](README.md) · [Visão geral](visao-geral.md) · [CLI](cli.md) · [Configuração](configuracao.md) · [Exit codes](exit-codes.md) · [Relatórios](relatorios.md) · [SPEC](SPEC.md)

Doze gates. Cada um devolve um status `passed`, `warn`, `failed` ou `not_run`. O Markdown traduz para passou, aviso, falhou e não executado, com ✅ ⚠️ ❌ ⏭️ (`GATE_MARK` em `src/bob_quality/report.py`). Um gate que não rodou fica ⏭️ com motivo. Ele não aparece como ✅.

`coverage`, `test_smells`, `cognitive`, `supply`, `security`, `typing`, `dead_code` e `secrets` são opt-in. Eles só rodam quando `--gates` os pede. O `bob check` sem `--gates` continua `crap,dry,deps`. O hook `pre-push` e a Action também não incluem esses gates.

O exit code do `bob check` é o maior entre os gates que rodaram. Aviso não aumenta o código. Ver [Exit codes](exit-codes.md).

| Gate | Ferramenta | O que bloqueia | Exit quando bloqueia |
|---|---|---|---|
| [CRAP](#crap) | lizard + coverage.py ou c8/vitest | função no escopo com CRAP ≥ limite | `1` |
| [DRY](#dry) | jscpd | no modo fail, mais clones novos que `duplication.max_new_clones`. No modo warn, o padrão, nada | `1` no modo fail, `0` no warn |
| [Complexidade cognitiva](#complexidade-cognitiva) | complexipy ou eslint com eslint-plugin-sonarjs | nada; função alterada no limite é aviso | `0` |
| [Mutação](#mutação) | mutmut (Python), StrykerJS (TypeScript) | sobrevivente sem waiver | `3` |
| [Dependências](#dependências) | import-linter, dependency-cruiser, mais a regra de ciclo | violação cuja origem, destino ou outro módulo do ciclo está no diff | `1` |
| [Cobertura do diff](#cobertura-do-diff) | diff-cover 10.6.0 sobre `coverage.xml` ou lcov do c8 | percentual de uma linguagem abaixo do piso | `1` |
| [Testes do diff](#testes-do-diff) | ast do Python e o eslint do repositório | nada; cheiro no diff é aviso | `0` |
| [Dependências novas](#dependências-novas) | deptry, knip, PyPI, npm e OSV | pacote novo com 404, import não declarado, ou advisory `HIGH`/`CRITICAL` numa linha nova | `1` |
| [Segurança](#segurança) | Bandit no Python, Semgrep no TypeScript | achado novo cuja severidade está em `security.fail_severities`, sem waiver | `1` |
| [Tipos](#tipos) | mypy, pyright ou tsc do próprio repositório | diagnóstico ou escape numa linha nova do diff, sem waiver | `1` |
| [Segredos](#segredos) | gitleaks | segredo novo no diff | `1` |
| [Código morto](#código-morto) | vulture e knip | nada; símbolo morto cuja definição está no diff é aviso | `0` |

`coverage`, `test_smells`, `cognitive` e `supply` não entram no `bob check` sem `--gates`, nem no hook, nem na Action. O comando é `bob check --gates coverage`, `bob check --gates test_smells`, `bob check --gates cognitive` ou `bob check --gates supply`. O mesmo vale para `typing`, `security`, `secrets` e `dead_code`.

Versões pinadas: lizard 1.24.1, deptry 0.25.1, coverage 7.16.2, diff-cover 10.6.0, c8 12.0.0, vitest 5.0.3, jscpd 5.4.1, mutmut 3.8.0, complexipy 8.0.1, `@stryker-mutator/core` 10.0.0, `@stryker-mutator/vitest-runner` 10.0.0, import-linter 2.15, grimp 3.17, dependency-cruiser 18.5.0, eslint 9.39.5, eslint-plugin-sonarjs 2.0.4, bandit 1.9.4, gitleaks 8.30.1, vulture 2.16, knip 6.41.0. Node `>=22.18.0 <23`. Fonte: `pyproject.toml`, `package.json` e `doctor.py`. O doctor lê os pinos pip do Requires-Dist instalado. mypy, pyright e tsc ficam de fora dessa lista. O gate de tipos usa o executável que o `PATH` do repositório resolver, e o doctor não confere a versão. O Semgrep 1.180.0 também fica de fora do doctor. O gate de security chama `uvx --from semgrep==1.180.0`.

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

Dois filtros escolhem quais clones novos entram na conta, nos dois modos. O clone precisa de pelo menos `duplication.min_lines` linhas (padrão 0) e de pelo menos `duplication.min_similarity` por cento de similaridade (padrão 0). Um clone sem percentual, como o `exact`, conta como 100. O jscpd já descarta clones com menos de 5 linhas (o `--min-lines` padrão dele), então um `min_lines` abaixo de 5 não traz esses clones de volta. Clone fora da conta não aparece no relatório.

No modo warn, o padrão, um ou mais clones na conta deixam o gate em `warn` e o exit em `0`. No modo fail, o gate fica `failed` e o exit `1` quando a conta passa de `duplication.max_new_clones` (padrão 0). Com o teto 0, um clone na conta já falha. O motivo cita a chave e o teto, como em `1 new clone exceeds duplication.max_new_clones 0`. Até o teto, o modo fail fica em `warn`. A linha do relatório traz os dois lados (`arquivo:início-fim`), a quantidade de linhas, os tokens e a similaridade (`85%`, ou `exata` quando o clone é `exact` e não há percentual). Sem clones na conta, o status é `passed`.

O modo fail vem de `duplication.new_clones: fail` ou de `--dry-fail`. `--max-new-clones N` substitui `duplication.max_new_clones` nessa execução, e `0` é um teto de verdade. As duas flags existem em `bob dry` e `bob check`. Não há flag para forçar warn. Um `--max-new-clones` negativo sai com `4` antes de gravar relatório. O hook continua `crap,dry,deps`, sem essas flags.

Sem Node, ou sem o jscpd instalado, o status é `not_run` e o exit continua `0` (o retorno de `_skipped` é `PASSED`), também no modo fail. O jscpd precisa de Node também num repositório só Python, se `dry` estiver na lista.

A decisão 4 da [SPEC](SPEC.md), revista em 12/10/2026, define os dois modos. As chaves estão em [Configuração](configuracao.md#duplication).

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

## Complexidade cognitiva

O gate avisa quando uma função alterada tem complexidade cognitiva maior ou igual a `cognitive.max_per_function`. O padrão é 15. A comparação é `score >= limit` em `cognitive_verdict`. O exit fica `0` no aviso, no passe e quando a ferramenta falta.

Entra no veredito a função cujo intervalo inclusivo toca o diff (`function_is_changed`). O id do waiver é `cognitive:<arquivo>:<nome>`, montado só por `waiver_id()`. `complexipy` nomeia um método `Classe::metodo`. TypeScript usa o mesmo `::` (`Foo::save`, `outer::inner`). Uma função sem nome fica `anonymous@<linha>`. O waiver `save` não cobre `Foo::save`.

Python mede com `complexipy` 8.0.1. A chamada é `file_complexity(path, no_ignore=True)`, importada dentro do medidor. `check_script` fica no padrão, falso. Sem o pacote, esse idioma não entra no veredito. TypeScript mede com ESLint 9.39.5 e `eslint-plugin-sonarjs` 2.0.4, regra `sonarjs/cognitive-complexity`. O número passado à regra é `limit - 1`, porque a regra só reporta acima do limiar. O bob guarda a função se o score lido ainda é `>= limit`. Um arquivo que o ESLint não analisa é pulado. Se todos os arquivos falham, o idioma não entra. Se todo idioma configurado falha, o status é `not_run` e o exit é `0`.

O gate não entra em `DEFAULT_GATES`, no hook `pre-push` nem na Action. Quem pede `bob check --gates cognitive` é que o roda.

## Mutação

A cobertura mostra que a linha rodou. A mutação altera o código e roda a suíte de novo. Se um teste falha, o mutante morreu (`killed`). Se a suíte passa, ele sobreviveu (`survived`). Os outros status no modelo são `timeout` e `no_coverage` (`models.py`). `no_coverage` significa que nenhum teste executou o mutante. O adaptador do mutmut 3.8 mapeia “no tests”, “skipped”, “not checked” e “check was interrupted by user” para `no_coverage`.

Não há status separado para mutante equivalente. A skill `harden` manda registrar um waiver. O waiver é `arquivo::função`, para todo sobrevivente da função, ou o Alvo da tabela de sobreviventes, `arquivo::função::<descrição>`, para um só. A descrição é o operador do mutante. `bob waive` recusa com exit `4` um alvo que nenhum sobrevivente do último relatório tem. Ver a [ADR 0006](adr/0006-chave-estavel-do-waiver.md).

O bob muta Python com mutmut e TypeScript com Stryker. O mutmut roda em `<--out>/mutmut/`, uma pasta de links simbólicos para o topo do repo, e nunca escreve o `setup.cfg` nem o `mutants/` do repo. O arquivo incremental do Stryker fica em `.bob/stryker-incremental.json` (ou `<--out>/stryker-incremental.json`). Ele não entra em `.bob/mutation-cache.json`. Os mutantes do último relatório do Stryker ficam em `<--out>/stryker-mutants.json`, para `bob waive`. A Action restaura e publica os dois arquivos no artefato `bob-mutation-cache`.

Antes de mutar, a baseline roda. Se o `crap` já mediu o pytest na mesma execução, esse código é reusado. Baseline quebrada: o gate fica `not_run` e o exit é `2`.

Entram na mutação as funções alteradas no diff e as funções do cache que ainda têm sobrevivente sem waiver (`_candidate_keys`). O cache é `.bob/mutation-cache.json` (ou `<--out>/mutation-cache.json`). Cada função guarda o sha256 do texto entre `start_line` e `end_line`, a versão do mutmut e a impressão da suíte. A impressão (`suite_fingerprint`) é o sha256 dos arquivos versionados ou não ignorados que a suíte lê: diretórios `tests/` e `test/`, `conftest*`, `test_*.py`, `*_test.py`, `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, lockfiles (`uv.lock`, `poetry.lock`, `Pipfile.lock`, `pdm.lock`) e o `also_copy` do mutmut. `__pycache__`, `mutants/` e `.bob/` ficam de fora.

Se a versão do mutmut ou a impressão da suíte diferir da chave do arquivo, `_read_cache` devolve vazio e o cache inteiro deixa de ser reusado. Função com hash diferente, ou com sobrevivente ainda sem waiver, é mutada de novo. `--since-last-run` não liga nem desliga isso; o cache já é o caminho padrão.

A Action restaura e publica o artefato `bob-mutation-cache` com esse JSON e com `.bob/stryker-incremental.json` (`.github/actions/bob/action.yml`) e o guarda por 7 dias (`retention-days: 7`). Falha ao restaurar não interrompe o check (`restore_cache.py || echo ...` no workflow da action). A action também instala o Node `22.14.0` e o jscpd `5.4.1` antes do check, senão o dry fica `not_run`.

O limite efetivo é zero sobreviventes sem waiver numa linha do lado novo do diff (`git diff --unified=0`, âncora de hunk vazio incluída) e zero `no_coverage` nas funções do diff. Um sobrevivente nessas linhas, ou um `no_coverage` nessas funções, deixa o gate `failed` e o exit `3`. Sobrevivente sem waiver fora dessas linhas continua na tabela, com a nota `fora do diff; não bloqueia`, e não muda o exit. Sem arquivo, ou com linha menor ou igual a zero, o sobrevivente sem waiver ainda bloqueia. `killed` e `timeout` não entram nessa lista. Sobrevivente com waiver continua na tabela de sobreviventes, com a justificativa, e não conta para o `3`. Um waiver não cobre `no_coverage`. A seleção do que mutar continua por função (`_candidate_keys`).

`no_coverage` nas funções medidas muda o status do gate para `failed` quando não há sobrevivente que bloqueia, e o relatório ganha a seção “Mutantes sem teste”, com total e contagem por função e arquivo (`no_coverage_summary`, `_no_coverage_lines`). A linha do total diz que bloqueia. O exit é `3`. `tests/test_mutate.py` cobre essa falha. A decisão 11 da [SPEC](SPEC.md) é essa regra.

## Dependências

O gate roda as regras que o repositório já declara e soma uma regra sempre ativa que proíbe ciclo.

- Python, se `python` está em `languages`: import-linter com o arquivo `dependencies.python` (padrão `.importlinter`), mais ciclos pelo grafo do grimp (`deps_gate.py`).
- TypeScript, se `typescript` está em `languages`: dependency-cruiser com `dependencies.typescript` (padrão `.dependency-cruiser.cjs`).

O nome da regra de ciclo no JSON (sempre inglês) é `Forbidden dependency cycle`. No `report.md` em `pt-BR` é `Proibido ciclo de dependência`. Uma regra do dependency-cruiser sem nome fica `dependency` no JSON e `dependência` no Markdown.

Uma violação bloqueia quando a origem, o destino, ou outro módulo do mesmo componente fortemente conexo, está no diff (`_edge_in_diff`). As outras aparecem em “Informação (dependências fora do diff)” e não mudam o exit code. Zero violações no diff: `passed` e exit `0`. Uma no diff: `failed` e exit `1`.

Ferramenta ausente que impede a medição pedida deixa o gate `not_run` e o exit `4` (`ToolError` em `run_deps_gate`). O mesmo exit `4` vale para um JSON do dependency-cruiser que não é objeto ou não traz a lista `violations`, e para o import-linter com exit 0 cuja última linha `Contracts:` não é `N kept, 0 broken.`

## Cobertura do diff

O nome em `--gates` é `coverage`. Sem ele, o check não mede cobertura do diff.

O piso é `coverage.min_percent`, padrão 80. Percentual abaixo do piso falha. Percentual igual ao piso passa. Esse corte é o inverso do CRAP, que falha quando o número é igual ao limite. A comparação mora em `below_floor`, ao lado de `crap_verdict` em `core.py`.

Cada linguagem de `languages` tem o próprio percentual. Uma abaixo do piso falha o gate. Linguagem sem linha nova cobrível fica em 100 e passa.

Python lê o XML do Cobertura. O `coverage xml` grava esse XML a partir do mesmo arquivo de dados do `coverage json`. TypeScript lê o lcov do c8, gravado na mesma execução do vitest. Cada linguagem chama o diff-cover 10.6.0 num processo separado. XML e lcov não entram no mesmo processo.

O gate grava o próprio `git diff --unified=0 <base>...HEAD` e passa esse arquivo ao diff-cover. Esse comando não altera o diff que o CRAP já usa.

O waiver de linha é `coverage:<arquivo>:<linha>`. Ele tira a linha do numerador e do denominador. O waiver de arquivo é `coverage:<arquivo>` e tira o arquivo inteiro. O gate só lê ids com o prefixo `coverage:`. O trecho depois do último `:` é uma linha quando contém só dígitos. Qualquer outro texto depois do prefixo é um arquivo. O casamento dos mutantes continua exato e ignora esse prefixo.

Suíte que quebra antes de existir artefato sai com `2`. O JSON não traz `diff_coverage`. Suíte boa com artefato ausente, e nenhuma outra linguagem medida, sai com `4`. diff-cover ausente sai com `4` antes de o gate de cobertura pedir a suíte. Um `crap` na mesma lista ainda mede.

Se uma linguagem mede e a outra não tem a ferramenta, o veredito é o percentual medido. O exit segue esse percentual. O motivo cita a linguagem que ficou de fora. O status continua `passed` ou `failed`.

## Dependências novas

O gate só roda com `bob check --gates supply`. Ele olha o que o diff acrescenta.

Um nome direto entra quando o manifesto em `HEAD` o declara, o mesmo manifesto na base não o tem, e a linha dessa declaração está no lado novo. Um bump de versão de um nome que a base já tem não entra. O gate só olha `paths.include` (padrão `src`) para o import não declarado. O pin direto continua no manifesto da raiz (`pyproject.toml`, `requirements*.txt`, `package.json`), mesmo quando essa raiz fica fora de `paths.include`. Caminho em `paths.exclude` não conta. Lockfile não acrescenta nome. Ele só preenche a versão quando a linha não tem pin exato.

Python usa o deptry 0.25.1. `DEP001` e `DEP003` são imports não declarados. `DEP002`, `DEP004` e `DEP005` ficam de fora. TypeScript usa o knip 6.41.0, nos achados `unlisted` e `unresolved`. Um specifier que começa com `.` ou `/` não entra. O id do advisory vem de `POST https://api.osv.dev/v1/querybatch`. Essa resposta traz `id` e `modified`. A severidade vem de `GET https://api.osv.dev/v1/vulns/{id}`, com o mesmo `supply.timeout_seconds`. Falha nesse GET deixa o advisory não verificado e só avisa. Um documento obtido sem severidade publicada também só avisa. O texto diz que a severidade não foi publicada. O osv-scanner não é executado.

O veredito, em `judge`:

- 404 do PyPI ou do npm bloqueia.
- Import não declarado bloqueia, mesmo com a rede fora.
- Advisory cuja severidade está em `supply.osv_fail_severities` bloqueia. O padrão é `HIGH` e `CRITICAL`. `MODERATE` e `LOW` avisam.
- Timeout, falha de DNS ou resposta que não decide avisam e ficam não verificados. Esse aviso não é exit `4`.
- Waiver com id `supply:missing:<índice>:<nome>`, `supply:undeclared:<arquivo>:<módulo>` ou `supply:osv:<advisory>`. O id tem de ser igual. Um achado não verificado não tem waiver.
- Qualquer linha que bloqueia deixa o gate `failed` e o exit `1`. Sem bloqueio, um aviso deixa `warn` e exit `0`. Um bloqueio dispensado mais um `MODERATE` que ficou é `warn` e exit `0`, e a linha dispensada continua na tabela.

Se uma linguagem configurada mede e a outra não, o veredito é o da que mediu. A que não mediu aparece como linha própria e não muda o status. Exit `4`, com relatório, só quando nenhuma linguagem configurada mediu. A seção markdown é `## New dependencies` ou `## Dependências novas`, depois de mutantes sem teste e antes de segredos, de código morto e de como reproduzir. O JSON omite a chave `supply` quando o gate não rodou. `schema_version` continua `1`.

## Segurança

O gate só entra com `--gates security`. O `bob check` sem `--gates` continua `crap,dry,deps`. O hook `pre-push` e a Action, sem inputs, também não o incluem.

Python roda o Bandit (`python -m bandit`). TypeScript roda o Semgrep 1.180.0 num ambiente isolado, com `uvx --from semgrep==1.180.0 semgrep scan`. O pacote do bob não instala o Semgrep. Sem `uvx` no `PATH`, a linguagem fica sem medição e o motivo é `semgrep runner missing: uvx`. O gate não segue em silêncio. Uma linguagem fora de `languages` não roda e não conta como ferramenta ausente. Repositório só Python não chama o Semgrep.

O achado falha quando o intervalo de linhas cruza `changed_lines`, a severidade está em `security.fail_severities` e nenhum waiver casa. O padrão da lista é `HIGH`, `CRITICAL` e `ERROR`. `ERROR` é a palavra que regras antigas do Semgrep emitem. Não vira `HIGH`. O resto no diff fica em `warn` e o exit continua `0`. Achado fora do diff aparece no relatório como `off_diff` e não muda o exit. A confiança do Bandit (`issue_confidence`) não filtra.

O waiver fica em `.bob/waivers.yaml`. O id `sast:<ferramenta>:<regra>` cobre essa regra em todo o diff. O id `sast:<ferramenta>:<regra>:<arquivo>:<linha>` cobre a linha primária do achado, inclusive fora do diff. A comparação é igualdade das duas strings. Um id de regra com `:` continua inteiro. Quando os dois casam, o motivo gravado é o do id com arquivo e linha.

O Semgrep recebe `--baseline-commit` com o SHA de `git merge-base <base> HEAD`, o mesmo merge-base do diff. A execução é num worktree destacado de `HEAD`, apagado no fim. Árvore suja, índice sujo e arquivo não commitado não entram nesse scan e não abortam o gate. As regras são o diretório `.semgrep/` commitado na raiz. Sem `.yml` ou `.yaml` ali, o Semgrep não inicia e essa linguagem fica sem medição, com o motivo `missing rules directory: .semgrep`. O gate só fica `not_run` quando nenhuma linguagem pedida mediu. Não há id de registry e não há download de regra. O `uvx` baixa só o wheel pinado do Semgrep, fora do ambiente do projeto.

O Bandit varre o diretório de trabalho. Um `.bandit` do projeto não escolhe a severidade. O bob passa `--ini` num arquivo vazio. `# nosec` e `nosem` continuam visíveis para o waiver (`--ignore-nosec` e `--disable-nosem`).

Se uma linguagem mede e a outra não, a que faltou sai do veredito. Um passe vira `warn` com exit `0`. Uma falha continua `failed` com exit `1`, e o motivo junta os dois com `probe.joined`. Se toda linguagem pedida fica sem medição, o gate é `not_run`, o exit é `4` e o relatório é gravado. Exit da ferramenta fora de `0` e `1`, JSON que não parseia, ou binário ausente contam como sem medição. O bob não copia o inteiro da ferramenta.

## Tipos

O gate roda com `bob check --gates typing`. O `bob check` sem `--gates` continua `crap,dry,deps` (`DEFAULT_GATES`). O hook `src/bob_quality/hooks/pre-push` passa esses três. A Action `.github/actions/bob/action.yml`, sem inputs, continua `crap,dry,deps,mutate`. Nenhum dos três inclui `typing`.

mypy, pyright e tsc são os executáveis do repositório. O bob não os pina, não os instala e não os chama com `python -m` nem com `npx`. A primeira linha não vazia de `--version` vai para `tool_versions`. Se o processo não chegou a subir, a chave desse checker não entra.

Não há limiar de type-coverage. A chave `typing` no `bob.yaml` não tem filhos. `typing: {}` é aceito e não liga o gate. Quem liga é `--gates typing`. Ver [Configuração](configuracao.md#typing).

Bloqueia, com status `failed` e exit `1`, um diagnóstico do checker ou um escape que esteja numa linha nova do diff e não tenha waiver. O id é `typing:<arquivo>:<linha>:<código>`, comparado pelo texto inteiro. O motivo do gate, quando falha, é o primeiro id. O relatório lista o resto. Um achado fora do diff entra na tabela com disposição `off_diff` e não muda o exit.

Os escapes são `Any` e `type: ignore` em `.py` e `.pyi`, e `as any`, `@ts-ignore` e `@ts-expect-error` em `.ts` e `.tsx`. Não entra `.js`. O código gravado de um ignore do Python é sempre `type: ignore`, inclusive em `# type: ignore[arg-type]` e `# type:ignore`. `@ts-ignore` dentro de uma string não conta. O escape só é lido em arquivo do diff, dentro de `paths.include`, e só se a linguagem tiver config de checker.

A linguagem vem de `languages`. Sem config de checker, ela fica `not_run`, contribui `0`, e o motivo do gate é `no checker config`.

- mypy roda quando existe `mypy.ini`, `.mypy.ini`, a seção `[mypy]` no `setup.cfg`, ou `[tool.mypy]` no `pyproject.toml`.
- pyright roda quando existe `pyrightconfig.json` ou `[tool.pyright]`.
- Se os dois existem, os dois rodam.
- tsc roda quando o `tsconfig.json` da raiz é um arquivo. Um `tsconfig` aninhado não conta. Sem o arquivo da raiz, TypeScript fica `not_run` e contribui `0`.

Config presente e executável ausente deixa esse checker sem medição (`missing_executable`). Exit `4` só quando o gate foi pedido e nenhum checker mediu. Se um mediu e o outro não, o exit é o da medição, e o motivo de um passe continua vazio.

Contam como medição os exits `0` e `1` do mypy, `0` e `1` do pyright, e `0`, `1` e `2` do tsc. O `2` do mypy, os exits `2`, `3` e `4` do pyright, e os exits `3` e `4` do tsc ficam `exit_outside_measurement`. Exit `0` com uma linha de erro, ou um exit de erro sem linha de diagnóstico, fica `unparseable_output`. Uma linha do tsc sem arquivo é ignorada. Os diagnósticos que têm arquivo permanecem. Stdout e stderr entram os dois na leitura.

O `report.md` ganha `## Types` ou `## Tipos` depois dos mutantes sem teste e antes de `## Segredos`, também quando a lista de achados está vazia. O `report.json` ganha o objeto `typing`. `schema_version` continua `1`, e `typing` não é obrigatório no schema.

## Segredos

Este gate não entra na lista padrão do `bob check`. O comando é `bob check --gates secrets`. Ele roda `gitleaks detect --no-git` com o gitleaks 8.30.1 nas raízes de `paths.include`.

Um segredo numa linha nova do diff, sem waiver, deixa o gate `failed` e o exit `1`. O id do waiver é a string inteira `secret:<regra>:<arquivo>:<linha>`. O id não leva o valor. `bob waive` grava esse id em `.bob/waivers.yaml`.

Um achado fora do diff aparece no Markdown e não muda o exit. O status fica `passed` e o exit fica `0`. Um achado com waiver não entra em nenhuma das duas listas.

A chave `secrets` no `bob.yaml` fica vazia. Ausente, `secrets:`, `secrets: null` e `secrets: {}` são o mesmo mapeamento e não ligam o gate.

O JSON inclui `secrets` só quando o gate mediu. O array traz os achados que bloqueiam. Cada objeto tem `file`, `line` e `rule_id`. Sem medição, a chave não aparece.

A seção `## Segredos` fica depois de `## Dependências novas` e de `## Tipos`, quando essas seções existem, e antes de `## Código morto` e de `## Como reproduzir`. Sem medição, a seção não aparece. A saída bruta do gitleaks fica fora de `.bob/`.

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

A seção `## Código morto` sai só quando o gate foi pedido, depois de `## Tipos`, de `## Segredos` e de `## Complexidade cognitiva` quando essas seções existem, e antes de `## Segurança` e de `## Rotatividade`. A seção `## Segurança` sai só quando o gate foi pedido, antes de `## Rotatividade` e de `## Como reproduzir`. O JSON segue a ordem do render. Depois de `mutation` vêm `test_smells` quando o gate rodou, `supply` quando o gate mediu, `diff_coverage` quando ao menos uma linguagem mediu, `typing` quando o gate de tipos foi pedido, `secrets` quando o gate de segredos mediu, `cognitive` quando o gate cognitivo foi pedido, `dead_code` quando esse gate foi pedido e `security` quando esse gate foi pedido. `churn` sai sempre, antes de `reproduce`. Sem o gate, a chave não existe. `schema_version` continua 1. O `reason` do JSON fica em inglês.

## Monorepo e Node ausente

Decisão 10 da [SPEC](SPEC.md), implementada em `crap_gate.py` e `deps_gate.py`:

- Com Python e TypeScript na lista, falta de Node não é exit `4` para o CRAP nem para deps. Python segue medido. O motivo do TypeScript é anexado. Se o veredito Python era `passed`, o gate passa a `warn`. Se já era falha, o status de falha permanece e o motivo cita os dois.
- Repositório só TypeScript sem Node: a ferramenta ausente impede a medição pedida e o exit é `4`.

O DRY, sozinho, trata Node ausente como `not_run` com exit `0`, também num repo só Python.

O gate `security` usa o mesmo corte entre linguagens. Semgrep ausente num repositório que também mediu o Python não sai `4`. As duas linguagens sem medição saem `4`.
