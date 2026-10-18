# Gates e waivers

[Índice](../README.md) · [Configuração](configuration.md) · [Códigos de saída](../exit-codes.md) · [Relatórios](reports.md) · [SPEC](SPEC.md)

Doze nomes de gate. Cada um devolve `passed`, `warn`, `failed` ou `not_run`. Em `report.md` esses são passed, warning, failed e not run, com ✅ ⚠️ ❌ ⏭️ (`GATE_MARK` em `src/bob_quality/report.py`). Um gate que não rodou mostra o motivo. Ele nunca aparece como passado.

`bob check` sem `--gates` roda `crap,dry,deps` (`DEFAULT_GATES` em `src/bob_quality/check.py`). O hook de pre-push roda os mesmos três. O input padrão da GitHub Action é `crap,dry,deps,mutate`. Os outros oito nomes só rodam quando `--gates` os lista. Não há `bob coverage`, `bob security` nem outro subcomando para eles. Churn não é um gate. É uma seção do relatório em todo check, e não tem linha de veredito.

O código de saída do processo é o código mais alto entre os gates. Um aviso contribui com `0`.

| Gate | Ferramentas | O que bloqueia | Exit quando bloqueia |
|---|---|---|---|
| `crap` | lizard, mais coverage.py ou c8/vitest | uma função no escopo com CRAP no limite ou acima | `1` |
| `dry` | jscpd | no modo fail, mais clones novos contados do que o teto. O modo warn não bloqueia nada | `1` no modo fail, `0` no modo warn |
| `cognitive` | complexipy, ou eslint com eslint-plugin-sonarjs | nada. Uma função alterada no limite avisa | `0` |
| `mutate` | mutmut (Python), Stryker (TypeScript) | um sobrevivente sem waiver numa linha alterada, ou `no_coverage` numa função alterada | `3` |
| `deps` | import-linter, grimp, dependency-cruiser, mais a regra de ciclo | uma violação cuja origem, destino ou outro módulo do ciclo está no diff | `1` |
| `coverage` | diff-cover 10.6.0 sobre `coverage.xml` ou lcov do c8 | um percentual de linguagem abaixo do piso | `1` |
| `test_smells` | AST do Python, e o eslint do repositório quando um plugin Jest ou Vitest está configurado | nada. Um cheiro num teste alterado avisa | `0` |
| `supply` | deptry, knip, PyPI, npm, OSV | um pacote novo que responde 404, um import não declarado, ou um advisory `HIGH`/`CRITICAL` numa linha que o diff adicionou | `1` |
| `security` | Bandit (Python), Semgrep (TypeScript) | um achado novo cuja severidade está em `security.fail_severities`, sem waiver | `1` |
| `typing` | o mypy, pyright ou tsc do repositório | um diagnóstico ou um escape numa linha nova do diff, sem waiver | `1` |
| `secrets` | gitleaks 8.30.1 | um segredo novo no diff | `1` |
| `dead_code` | vulture e knip | nada. Um símbolo não usado cuja definição está no diff avisa | `0` |

Versões pinadas, de `pyproject.toml`, `package.json` e `PINS` em `src/bob_quality/doctor.py`: lizard 1.24.1, deptry 0.25.1, coverage 7.16.2, diff-cover 10.6.0, c8 12.0.0, vitest 5.0.4, jscpd 5.4.1, mutmut 3.8.0, complexipy 8.0.1, `@stryker-mutator/core` 10.0.0, `@stryker-mutator/vitest-runner` 10.0.0, import-linter 2.15, grimp 3.17, dependency-cruiser 18.6.0, eslint 9.39.5, eslint-plugin-sonarjs 2.0.4, bandit 1.9.4, gitleaks 8.30.1, vulture 2.16, knip 6.41.0. O Node para o `bob doctor` é `>=22.18.0 <23`. mypy, pyright e tsc são os executáveis do repositório. O doctor não os pina. O Semgrep 1.180.0 não está em `PINS`. O gate de segurança roda `uvx --from semgrep==1.180.0`.

Um waiver fica em `.bob/waivers.yaml`. O formato do arquivo está em [Configuração](configuration.md). Cada gate lê ids com o próprio prefixo. O casamento da mutação ignora esses prefixos: um waiver de segredo ou um waiver de typing não casa com um mutante, a menos que o id inteiro já seja uma das chaves do mutante.

## CRAP

O CRAP combina complexidade ciclomática com a fração das linhas executáveis da função que os testes rodaram.

```text
CRAP = CC² × (1 − cov)³ + CC
```

`CC` vem do lizard, para Python e TypeScript. `cov` é uma fração de 0 a 1 (`calculate_crap` em `src/bob_quality/crap.py`). Uma função sem linhas executáveis no intervalo dela conta como totalmente coberta. Um arquivo sem dados de cobertura conta como 0 (`line_coverage` em `src/bob_quality/core.py`).

| CC | Cobertura | CRAP | No limite padrão de 10 |
|---|---|---|---|
| 4 | 50% | 16 × 0.125 + 4 = 6 | passa |
| 5 | 0% | 25 + 5 = 30 | falha |
| 10 | 100% | 0 + 10 = 10 | falha |

A comparação é `crap >= max_crap`. Uma função em 10 falha o limite padrão. Como o CRAP nunca fica abaixo do CC, CC 10 com cobertura total também falha esse limite. Mude o limite com `crap.max_per_function` ou com `bob crap --threshold`.

Com `crap.scope: changed` (o padrão), só funções alteradas são consideradas. `all` considera toda função medida. Qualquer outra string sai com `4` antes da execução. O [ADR 0002](adr/0002-o-diff-filtra-o-veredito.md) registrou uma regra mais larga. O código não.

O gate roda os testes para medir cobertura. Uma baseline quebrada sai com `2`. Pytest `0` e `5` contam como uma suíte boa (`pytest_passed` em `src/bob_quality/exit_codes.py`). O comentário nesse módulo diz que `5` significa que nenhum teste foi coletado. O Vitest aceita só `0`. Isso vale para o `bob check` padrão, porque esse comando inclui `crap`.

Python roda coverage.py em volta do pytest. TypeScript roda c8 em volta do vitest. A spec ainda menciona cobertura de branch e lcov na lista de adaptadores que alimenta o núcleo. A fração do CRAP são linhas de statement no intervalo da função. O gate `coverage` é o que lê o diff-cover. Ver [SPEC](../architecture/spec.md).

## DRY

Um clone é um bloco que repete outro bloco. O gate roda o jscpd com `duplication.min_tokens` (padrão 50) e fica com os clones em que pelo menos um lado toca uma linha alterada.

Dois filtros então escolhem quais clones novos contam, nos dois modos. Um clone conta quando tem pelo menos `duplication.min_lines` linhas (padrão 0) e pelo menos `duplication.min_similarity` por cento de similaridade (padrão 0). Um clone sem percentual conta como 100. O jscpd já descarta clones com menos de 5 linhas, o padrão dele, então um `min_lines` abaixo de 5 não os traz de volta. Um clone que não conta fica fora do relatório.

No modo `warn`, o padrão, um ou mais clones contados deixam o gate em `warn` e o exit em `0`. No modo `fail` o gate é `failed` e o exit é `1` quando a conta está acima de `duplication.max_new_clones` (padrão 0). O motivo nomeia a chave e o teto, como em `1 new clone exceeds duplication.max_new_clones 0`. No teto ou abaixo, o modo fail permanece `warn`. Sem clones contados, o status é `passed`.

O modo fail vem de `duplication.new_clones: fail` ou de `--dry-fail`. `--max-new-clones N` substitui o teto nessa execução. Um `--max-new-clones` negativo sai com `4` antes de qualquer relatório, com `--max-new-clones must be at least 0` no stderr.

Sem Node, ou sem jscpd, o status é `not_run` e o exit permanece `0`, também no modo fail. O jscpd precisa de Node também num repositório só de Python, quando `dry` está na lista.

## Complexidade cognitiva

`bob check --gates cognitive`. Uma função alterada com score maior ou igual a `cognitive.max_per_function` (padrão 15) deixa o gate em `warn`. O exit permanece `0` num aviso, num passe e quando a ferramenta falta.

O id do waiver é `cognitive:<file>:<name>`. O complexipy nomeia um método Python `Class::method`. TypeScript usa o mesmo `::`. Uma função sem nome é `anonymous@<line>`. O waiver `save` não cobre `Foo::save`.

Python mede com complexipy 8.0.1. TypeScript mede com ESLint 9.39.5 e eslint-plugin-sonarjs 2.0.4, regra `sonarjs/cognitive-complexity`. O número passado à regra é `limit - 1`, porque a regra só reporta acima do limiar dela. O bob fica com a função quando o score que lê ainda é `>= limit`. Se toda linguagem configurada falha, o status é `not_run` e o exit é `0`.

## Mutação

A cobertura mostra que uma linha rodou. Ela não mostra que um teste conferiu o resultado. O teste de mutação muda o código e roda os testes de novo. Se um teste falha, o mutante é `killed`. Se a suíte passa, ele `survived`. Os outros status no modelo são `timeout` e `no_coverage`. `no_coverage` significa que nenhum teste rodou o mutante. O adaptador do mutmut 3.8 mapeia "no tests", "skipped", "not checked" e "check was interrupted by user" para `no_coverage`.

Não há status separado para um mutante equivalente. Registre um waiver, como `skills/harden/SKILL.md` descreve.

O bob muta Python com mutmut e TypeScript com Stryker. O mutmut roda em `<--out>/mutmut/`, um diretório de symlinks para as entradas de primeiro nível do repositório, e nunca grava o `setup.cfg` nem o `mutants/` do repositório. O arquivo incremental do Stryker é `.bob/stryker-incremental.json` (ou `<--out>/stryker-incremental.json`). Os últimos mutantes do Stryker são gravados em `<--out>/stryker-mutants.json` para o `bob waive`. O [ADR 0001](adr/0001-adaptadores-sobre-ferramentas-de-mercado.md) registrou uma árvore que não tinha adaptador do Stryker. O código na `main` tem `src/bob_quality/adapters/stryker.py` e os pins acima.

A baseline roda primeiro. Se `crap` já mediu o pytest na mesma execução, esse código é reusado. Uma baseline quebrada deixa o gate `not_run` e sai com `2`.

A execução muta funções alteradas e funções em cache que ainda têm um sobrevivente sem waiver. O cache é `.bob/mutation-cache.json`. Cada função guarda um sha256 do texto dela, a versão do mutmut e a impressão da suíte. Se a versão do mutmut ou a impressão da suíte difere da chave do arquivo, o cache não é reusado. `--since-last-run` não muda isso. O reuso já é o padrão. A flag só aparece na linha de reprodução do relatório quando foi passada.

Um sobrevivente bloqueia quando é `survived`, não tem waiver e a linha dele está no lado novo do diff. Um sobrevivente sem arquivo, ou com uma linha em zero ou abaixo, também bloqueia. Qualquer um dos casos sai com `3`. Um sobrevivente sem waiver numa linha que o diff não mudou permanece na tabela, marcado fora do diff, e não muda o exit. `killed` e `timeout` não bloqueiam. Um waiver não cobre `no_coverage`. `no_coverage` numa função alterada também sai com `3`.

O id do waiver é `file::function` para todo sobrevivente dessa função, ou `file::function::<description>` para um sobrevivente. A descrição é o operador do mutante com os espaços externos removidos. Para Python é o diff do `mutmut show`. Para TypeScript é `{mutatorName}@{line}:{column}-{line}:{column}`, mais ` -> {replacement}` quando o Stryker reporta um. A forma exata só existe quando nenhum outro sobrevivente da função tem a mesma descrição. Ver [ADR 0006](adr/0006-chave-estavel-do-waiver.md).

## Dependências

O gate roda as regras que o repositório já declara e acrescenta uma regra que está sempre ligada e proíbe ciclos.

- Python, quando `python` está em `languages`: import-linter com `dependencies.python` (padrão `.importlinter`), mais ciclos do grafo do grimp.
- TypeScript, quando `typescript` está em `languages`: dependency-cruiser com `dependencies.typescript` (padrão `.dependency-cruiser.cjs`).

O nome da regra de ciclo no JSON é `Forbidden dependency cycle`. Em `pt-BR` o `report.md` traz `Proibido ciclo de dependência`. Uma regra do dependency-cruiser sem nome é `dependency` no JSON e `dependência` no Markdown.

Uma violação bloqueia quando a origem, o destino ou outro módulo do mesmo componente fortemente conexo está no diff. As outras aparecem como informação e não mudam o código de saída. Zero violações no diff é `passed` e exit `0`. Uma no diff é `failed` e exit `1`.

Uma ferramenta ausente que bloqueia a medição pedida deixa o gate `not_run` e sai com `4`. O mesmo `4` vale quando o JSON do dependency-cruiser não é um objeto ou não tem lista `violations`, e quando o import-linter sai com 0 mas a última linha `Contracts:` não é `N kept, 0 broken.`

## Cobertura do diff

`bob check --gates coverage`. O piso é `coverage.min_percent`, padrão 80. Um percentual abaixo do piso falha. Um percentual igual ao piso passa. Esse corte é o oposto do CRAP, que falha quando o número iguala o limite.

Cada linguagem em `languages` tem o próprio percentual. Uma linguagem sem linha nova cobrível conta como 100 e passa. Python lê o XML do coverage. TypeScript lê o lcov do c8. Cada linguagem chama o diff-cover 10.6.0 no próprio processo.

O waiver de linha é `coverage:<file>:<line>`. Ele tira a linha do numerador e do denominador. O waiver de arquivo é `coverage:<file>` e tira o arquivo inteiro. O gate lê só ids com o prefixo `coverage:`.

Uma suíte que quebra antes de o artefato existir sai com `2`. O JSON então não tem `diff_coverage`. Uma suíte boa com artefato ausente, e nenhuma outra linguagem medida, sai com `4`. Um diff-cover ausente sai com `4` antes de este gate pedir a suíte. Um gate `crap` na mesma lista ainda mede.

Se uma linguagem mede e a outra não tem ferramenta, o veredito é o percentual medido. O motivo nomeia a linguagem que ficou de fora.

## Cheiros de teste

`bob check --gates test_smells`. A contribuição para o exit é sempre `0`. O status é `passed`, `warn` ou `not_run`.

O gate ignora `paths.include` e `paths.exclude`. Um arquivo sob `tests/` é elegível mesmo quando `tests` está na lista de exclusão.

Python roda quando `python` está em `languages`. O nome do arquivo é `test_*.py` ou `*_test.py`. `conftest.py` e `__init__.py` ficam de fora. Um teste é uma função `test_*` no corpo do módulo, ou um método `test_*` numa classe de nível de módulo cujo nome começa com `Test`.

| Regra | Quando aparece |
|---|---|
| `empty-test` | O corpo é só uma docstring, `pass` e `...` |
| `missing-assert` | O corpo não tem asserção. Um corpo vazio é só `empty-test` |
| `disabled-test` | Uma linha alterada desabilita o teste com `skip`, `skipif`, `skipIf`, `skipUnless`, `xfail` ou `importorskip`. Um skip que o diff não tocou não conta. Um teste desabilitado também não emite `empty-test` nem `missing-assert` |
| `sleep` | Uma chamada de nome `sleep` numa linha alterada dentro do teste. `time.sleep`, `asyncio.sleep` e `trio.sleep` contam. `sleeping` não conta. Uma função fora do teste não conta |

Um arquivo que não faz parse não produz linha. Python permanece medido.

TypeScript roda quando `typescript` está em `languages`. O nome termina em `.test.ts`, `.test.tsx`, `.test.js`, `.test.jsx`, `.test.mjs`, `.test.cjs`, ou o mesmo com `.spec` no lugar de `.test`. Um arquivo sob `__tests__` também conta para esses sufixos. `*.d.ts` fica de fora.

O gate procura `eslint-plugin-jest`, `eslint-plugin-vitest`, `plugin:jest/` ou `plugin:vitest/` no texto da configuração. A busca pula `node_modules`, `dist`, `.git` e `.bob`. Em `package.json` só o valor de `eslintConfig` conta. Sem um marcador, TypeScript é pulado e o eslint não inicia. O binário é `node_modules/.bin/eslint`, com `--format json` e os caminhos alterados. Exit `0` ou `1` com uma lista JSON é uma medição. Qualquer outro exit, ou uma saída que não é essa lista, deixa TypeScript sem medição. Se nenhuma linguagem mediu, o status é `not_run` e o exit do processo permanece `0`. Uma metade TypeScript quebrada não muda o status do que já foi medido. O `bob doctor` não pina esse eslint.

O id do waiver é `tests:<file>:<line>:<rule>`. Uma linha com waiver mantém a linha na tabela e copia o motivo. O status é passed quando não resta linha sem waiver.

`test_smells: false` sai com `4` antes do gate, com `bob.yaml: test_smells accepts only true`, e não grava relatório. Omitir a chave, `null` e `true` são o mesmo. O gate não lê o campo.

## Dependências novas

`bob check --gates supply`. Ele olha o que o diff acrescenta.

Um nome direto conta quando o manifesto em `HEAD` o declara, o mesmo manifesto na base não declara, e a linha da declaração está no lado novo. Um bump de versão de um nome que a base já tem não conta. Imports não declarados são procurados sob `paths.include`. O pin direto permanece no manifesto da raiz (`pyproject.toml`, `requirements*.txt`, `package.json`), mesmo quando essa raiz está fora de `paths.include`. Um lockfile não acrescenta um nome.

Python usa deptry 0.25.1. `DEP001` e `DEP003` são imports não declarados. `DEP002`, `DEP004` e `DEP005` ficam de fora. TypeScript usa knip 6.41.0, achados `unlisted` e `unresolved`. Um especificador que começa com `.` ou `/` não conta.

O id do advisory vem de `POST https://api.osv.dev/v1/querybatch`. A severidade vem de `GET https://api.osv.dev/v1/vulns/{id}`, com o mesmo `supply.timeout_seconds`. Uma falha desse GET, ou um documento sem severidade publicada, avisa e permanece não verificado. osv-scanner não é executado.

- Um 404 do PyPI ou do npm bloqueia.
- Um import não declarado bloqueia, inclusive quando a rede está fora.
- Um advisory cuja severidade está em `supply.osv_fail_severities` bloqueia. O padrão é `HIGH` e `CRITICAL`. `MODERATE` e `LOW` avisam.
- Timeout, falha de DNS ou uma resposta que não decide avisa e permanece não verificado. Esse aviso não é exit `4`.

Os ids de waiver são `supply:missing:<index>:<name>`, `supply:undeclared:<file>:<module>` e `supply:osv:<advisory>`. O index é `pypi` ou `npm`. O id tem de ser igual. Um achado não verificado não tem waiver.

Qualquer linha que bloqueia deixa o gate `failed` e o exit `1`. Sem linha que bloqueia, um aviso é `warn` e exit `0`. Se uma linguagem configurada mede e a outra não, o veredito é o da que mediu. Exit `4`, com relatório, só acontece quando nenhuma linguagem configurada mediu.

## Segurança

`bob check --gates security`. Não está no check padrão, no hook nem no padrão da Action.

Python roda Bandit (`python -m bandit`). TypeScript roda Semgrep 1.180.0 com `uvx --from semgrep==1.180.0 semgrep scan`. O pacote bob não instala o Semgrep. Sem `uvx` no `PATH`, essa linguagem fica sem medição e o motivo é `semgrep runner missing: uvx`. Uma linguagem que não está em `languages` não roda e não conta como ferramenta ausente.

Um achado falha quando o intervalo de linhas dele sobrepõe o diff, a severidade está em `security.fail_severities` e nenhum waiver casa. A lista padrão é `HIGH`, `CRITICAL` e `ERROR`. `ERROR` é a palavra que regras antigas do Semgrep emitem. Ela não é reescrita para `HIGH`. Qualquer outra coisa no diff é `warn` e o exit permanece `0`. Um achado fora do diff é `off_diff` e não muda o exit. A confiança do Bandit não filtra.

O id de waiver `sast:<tool>:<rule>` cobre essa regra no diff inteiro. O id `sast:<tool>:<rule>:<file>:<line>` cobre a linha primária do achado. A comparação é igualdade das duas strings.

O Semgrep recebe `--baseline-commit` com o SHA de `git merge-base <base> HEAD`. O scan roda num worktree destacado de `HEAD`, apagado no fim. Uma árvore suja não aborta o gate. As regras são o diretório `.semgrep/` versionado na raiz. Sem um `.yml` ou `.yaml` ali, o Semgrep não inicia e o motivo é `missing rules directory: .semgrep`. Não há id de registry e não há download de regra. `uvx` baixa só o wheel pinado do Semgrep.

O Bandit varre o diretório de trabalho. Um arquivo `.bandit` do projeto não escolhe a severidade. O bob passa `--ini` apontando para um arquivo vazio. `# nosec` e `nosem` permanecem visíveis para o waiver (`--ignore-nosec` e `--disable-nosem`).

Se uma linguagem mede e a outra não, um passe vira `warn` com exit `0`. Uma falha permanece `failed` com exit `1`. Se toda linguagem pedida está sem medição, o gate é `not_run`, o exit é `4` e o relatório é gravado. Um exit de ferramenta fora de `0` e `1`, um JSON que não faz parse, ou um binário ausente conta como sem medição. O bob não copia o inteiro da ferramenta.

## Tipagem

`bob check --gates typing`. mypy, pyright e tsc são os executáveis do repositório. O bob não os pina, não os instala e não os chama com `python -m` nem `npx`.

Não há limiar de type-coverage. A chave `typing` não tem filhos e não liga o gate. O [ADR 0005](adr/0005-modelo-de-gate-das-analises-novas.md) registra essa decisão.

Um diagnóstico de checker ou um escape numa linha nova do diff, sem waiver, é `failed` e exit `1`. O id é `typing:<file>:<line>:<code>`, comparado como a string inteira. O código de ignore do Python guardado no achado é `type: ignore`, inclusive para `# type: ignore[arg-type]` e `# type:ignore`, então esse id vai entre aspas no YAML. Um achado fora do diff é `off_diff` e não muda o exit.

Os escapes são `Any` e `type: ignore` em `.py` e `.pyi`, e `as any`, `@ts-ignore` e `@ts-expect-error` em `.ts` e `.tsx`. `.js` não é varrido em busca de escapes. `@ts-ignore` dentro de uma string não conta.

Sem config de checker, a linguagem é `not_run`, contribui com `0`, e o motivo é `no checker config`.

- mypy roda quando existe `mypy.ini`, `.mypy.ini`, `[mypy]` em `setup.cfg` ou `[tool.mypy]` em `pyproject.toml`.
- pyright roda quando existe `pyrightconfig.json` ou `[tool.pyright]`.
- Se os dois existem, os dois rodam.
- tsc roda quando o `tsconfig.json` da raiz é um arquivo. Um `tsconfig` aninhado não conta. Sem o arquivo da raiz, TypeScript é `not_run` e contribui com `0`.

Config presente e executável ausente deixa esse checker sem medição. Exit `4` só acontece quando o gate foi pedido e nenhum checker mediu. Se um mediu e o outro não, o exit é o resultado medido.

Os exits medidos são mypy `0` e `1`, pyright `0` e `1`, e tsc `0`, `1` e `2`. mypy `2`, pyright `2`, `3` e `4`, e tsc `3` e `4` estão fora da medição. Exit `0` com uma linha de erro, ou um exit de erro sem linha de diagnóstico, não pode ser interpretado. Uma linha do tsc sem arquivo é ignorada.

## Segredos

`bob check --gates secrets`. Ele roda `gitleaks detect --no-git` com gitleaks 8.30.1 nas raízes de `paths.include`.

Um segredo numa linha nova do diff, sem waiver, deixa o gate `failed` e sai com `1`. O id do waiver é a string inteira `secret:<rule>:<file>:<line>`. O id não carrega o valor do segredo. O relatório lista o arquivo, a linha e o id da regra. Ele não imprime o segredo. A saída bruta do gitleaks fica fora de `.bob/`.

Um achado fora do diff aparece no Markdown e não muda o exit. Um achado com waiver não está em nenhuma das duas listas.

A chave `secrets` é um mapeamento vazio. Ela não liga o gate. Um arquivo `.gitleaksignore` sob uma raiz de include deixa o gate `not_run` e sai com `4`, antes de o binário ser chamado. Essas entradas pertencem a `.bob/waivers.yaml`.

## Código morto

`bob check --gates dead_code`. O gate avisa e não muda o código de saída. Python roda `python -m vulture` com vulture 2.16. TypeScript roda knip 6.41.0. O knip não recebe `dead_code.min_confidence`.

Um símbolo conta quando a linha da definição dele está no lado novo do diff. Uma edição que toca só o corpo, e não essa linha, não avisa. Um símbolo fora de `paths.include`, ou com um componente de `paths.exclude` no caminho, fica de fora.

O id do waiver é `dead:<file>:<line>:<name>`. O mesmo id não dispensa um mutante.

Quando `dead_code.min_confidence` não está definido ou é null, o bob não passa `--min-confidence`. O Vulture usa o próprio padrão, inclusive `[tool.vulture]` no repositório. No vulture pinado, `DEFAULTS` usa 0. O valor `0`, quando a chave está presente, passa `--min-confidence 0` e sobrepõe `pyproject.toml`. A chave é um inteiro de 0 a 100.

Se uma linguagem mediu e a outra não, o status segue o registro medido. Um registro limpo é `passed`. Um símbolo no diff sem waiver é `warn`. A linguagem ausente permanece no motivo do gate. Isso não força `warn` e não usa exit `4`. Sem medição, o status é `not_run` e o exit permanece `0`. O relatório é gravado nos dois casos.

## Python e TypeScript juntos

Quando as duas linguagens estão configuradas, um Node ausente não é exit `4` para CRAP nem para deps. Python ainda é medido. O motivo de TypeScript é acrescentado. Se o veredito de Python era `passed`, o gate vira `warn`. Se já era uma falha, a falha permanece e o motivo nomeia os dois. Esta é a decisão 10 da spec, implementada em `crap_gate.py` e `deps_gate.py`.

Um repositório só de TypeScript sem Node sai com `4`, porque a ferramenta ausente bloqueia a medição pedida.

O DRY sozinho trata um Node ausente como `not_run` com exit `0`, inclusive num repositório só de Python e inclusive no modo fail.

O gate de segurança usa a mesma divisão. Um Semgrep ausente num repositório que também mediu Python não sai com `4`. As duas linguagens sem medição saem com `4`.
