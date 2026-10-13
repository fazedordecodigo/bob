# O modelo de gate das análises novas

Status: aceita em 12/10/2026, às 17h55 (São Paulo).

## Contexto

A issue #86 pede o modelo comum das análises N5 a N8 e N11 a N15, da pesquisa de 12/10/2026. Cada análise diz se bloqueia com exit 1 ou se fica em aviso, qual é o waiver, qual é a chave no `bob.yaml` e qual seção aparece no relatório.

O diff continua escolhendo o que pode bloquear, como na [0002](0002-o-diff-filtra-o-veredito.md). Os códigos continuam 0, 1, 2, 3 e 4, como na [0003](0003-exit-codes.md). O código de produção permanece o da base.

A #91 (N9) instala Node e jscpd na Action do gate DRY que já existe. Fica fora daqui.

## Decisão

Um aviso contribui 0. O status do gate fica `warn`. Um achado que bloqueia, restrito ao diff, sai com 1 (`GATE_FAILED`), o mesmo inteiro do CRAP e das dependências. O 2 deste modelo é `BASELINE_BROKEN`, a suíte que quebra antes da medição. O 4 do `ArgumentParser`, quando falta subcomando ou a flag é ilegal, continua o da [0003](0003-exit-codes.md) e não é baseline. O Emerson deu o OK em 13/10/2026, às 15:05. O 3 sai do sobrevivente sem waiver e do `no_coverage` nas funções do diff. Um waiver não cobre `no_coverage`. O 4 continua em configuração inválida e em ferramenta ausente que impede a medição pedida. `check.py` fica com o maior código.

As ferramentas medem a árvore de `paths.include`. Só entra no veredito o achado cuja linha cai no lado novo do diff. O resto pode aparecer no relatório e não muda o exit.

O waiver continua em `.bob/waivers.yaml`, com `id`, `reason` de uma linha, `author` e `date`. Sem motivo de uma linha, o preflight sai com 4, em inglês no stderr, e não grava relatório. Cada gate só lê ids com o próprio prefixo. O casamento dos mutantes ignora esses prefixos. Um waiver de segredo ou de tipo não casa com um mutante.

O `schema_version` permanece 1. Os campos novos são opcionais no `report_v1.json`. O JSON fica em inglês. O Markdown traduz o título da seção. As seções novas entram depois de `## Mutantes sem teste` e antes de `## Como reproduzir`. A tabela `## Waivers` é a mesma de hoje.

Nenhum gate novo entra em `DEFAULT_GATES`. O `bob check` sem `--gates` continua `crap,dry,deps`. O hook continua esses três. A Action, sem inputs, continua `crap,dry,deps,mutate`. Ligar um gate novo nessas listas é uma issue de implementação, depois do pin.

A issue que implementa a ferramenta adiciona o pin na lista que `bob doctor` já confere. Versão diferente sai com 4. `bob doctor --install` continua no caminho npm que já existe. Um pin pip entra no pacote como o lizard. Esta ADR não escolhe o número da versão. Ferramenta com licença GPL não entra.

Um nome ainda desconhecido em `--gates` continua `not_run` e contribui 0, como hoje. `coverage` e os outros nomes desta ADR seguem esse caminho até a issue que registra o gate. A chave no `bob.yaml` é outro caminho. Até o schema conhecê-la, ela é desconhecida e o `bob check` sai com 4. Tipo errado, chave desconhecida e valor semântico inválido permanecem os da [0003](0003-exit-codes.md).

### Já aprovado em 12/10/2026

O comentário do Emerson nas issues, às 17h06, fecha três pontos. Esta ADR não reabre.

- #88. A LGPL-2.1 do Semgrep CE e as licenças das regras do registry estão aprovadas. O par do gate é Bandit e Semgrep CE.
- #92. A LGPL-3.0 do eslint-plugin-sonarjs está aprovada.
- #90. O gate pode acessar PyPI, npm e OSV. Timeout e modo offline são aviso.

### Por análise

| Issue | Veredito | Waiver | Chave no `bob.yaml` | Relatório |
|---|---|---|---|---|
| [#87](https://github.com/fazedordecodigo/bob/issues/87) N5 | exit 1 | `coverage:<arquivo>` ou `coverage:<arquivo>:<linha>` | `coverage.min_percent`, padrão 80 | `## Cobertura do diff`, campo `diff_coverage` |
| [#88](https://github.com/fazedordecodigo/bob/issues/88) N6 | exit 1 | `sast:<ferramenta>:<regra>` ou `sast:<ferramenta>:<regra>:<arquivo>:<linha>` | `security.fail_severities` | `## Segurança`, campo `security` |
| [#89](https://github.com/fazedordecodigo/bob/issues/89) N7 | exit 1 | `secret:<regra>:<arquivo>:<linha>` | `secrets`, sem limiar | `## Segredos`, campo `secrets` |
| [#90](https://github.com/fazedordecodigo/bob/issues/90) N8 | exit 1, com exceção | `supply:missing:<índice>:<nome>`, `supply:undeclared:<arquivo>:<módulo>` ou `supply:osv:<advisory>` | `supply.osv_fail_severities` e `supply.timeout_seconds` | `## Dependências novas`, campo `supply` |
| [#92](https://github.com/fazedordecodigo/bob/issues/92) N11 | aviso | `cognitive:<arquivo>:<função>` | `cognitive.max_per_function`, padrão 15 | `## Complexidade cognitiva`, campo `cognitive` |
| [#93](https://github.com/fazedordecodigo/bob/issues/93) N12 | exit 1, com exceção | `typing:<arquivo>:<linha>:<código>` | `typing`, sem filhos | `## Tipos`, campo `typing` |
| [#94](https://github.com/fazedordecodigo/bob/issues/94) N13 | aviso | `tests:<arquivo>:<linha>:<regra>` | `test_smells`, sem limiar | `## Testes do diff`, campo `test_smells` |
| [#95](https://github.com/fazedordecodigo/bob/issues/95) N14 | aviso | `dead:<arquivo>:<linha>:<nome>` | `dead_code.min_confidence` | `## Código morto`, campo `dead_code` |
| [#96](https://github.com/fazedordecodigo/bob/issues/96) N15 | não muda o exit | não há | `churn.window_days`, padrão 90 | `## Churn`, campo `churn` |

Os nomes em `--gates` são `coverage`, `security`, `secrets`, `supply`, `cognitive`, `typing`, `test_smells` e `dead_code`. `churn` não é gate e não ganha linha no veredito.

**#87, cobertura do diff.** O limiar é piso. Percentual abaixo de `coverage.min_percent` falha. Percentual igual ao piso passa. Esse corte é o inverso do CRAP, que falha no igual. O Emerson aprovou o piso em 12/10/2026, às 17h55. O percentual é o que o diff-cover calcula nas linhas novas. Python lê `coverage.xml`. TypeScript lê o lcov do c8. Cada linguagem tem o próprio percentual. Uma abaixo do piso falha o gate. Linguagem sem linha nova cobrível passa. O campo `diff_coverage` traz esses percentuais e a lista `uncovered`, com `file` e `line`. Linha com waiver sai do numerador e do denominador, então dispensar linha descoberta sobe o percentual. Waiver de arquivo tira o arquivo inteiro. A suíte que quebra antes de produzir a cobertura sai com 2, como o CRAP. Suíte boa e artefato ausente sai com 4, o mesmo papel do `coverage-final.json` ausente no CRAP de hoje. diff-cover ausente, com o gate pedido e nenhuma linguagem medida, sai com 4.

**#88, segurança no diff.** Bandit no Python. Semgrep CE com `--baseline-commit` igual à base do diff. As regras do Semgrep ficam versionadas no repositório. A corrida não baixa regra. A rede aprovada em 12/10/2026 é a da #90, para PyPI, npm e OSV. Um achado falha quando alguma linha que a ferramenta reporta cruza `changed_lines` e a severidade está em `security.fail_severities`, sem waiver. O padrão dessa lista é `["HIGH", "CRITICAL", "ERROR"]`. `ERROR` fica na lista porque regras antigas do Semgrep usam essa palavra. A issue que pinar o Semgrep confere os nomes que a versão emite. Falha de parse da ferramenta não é severidade de regra. O resto no diff é aviso. O id sem arquivo cobre a regra no diff inteiro. O id `sast:<ferramenta>:<regra>:<arquivo>:<linha>` cobre um achado. Confiança do Bandit não filtra.

**#89, segredos.** A ferramenta é o gitleaks. Segredo novo no diff falha. A chave `secrets` não tem limiar nem filhos. A allowlist versionada é o waiver. O id não carrega o valor. O relatório mostra arquivo, linha e id da regra. O objeto em `secrets` só tem `file`, `line` e `rule_id`. O teste da implementação falha se o valor aparecer em `.bob/report.md` ou em `.bob/report.json`. A saída bruta do gitleaks fica fora de `.bob/`.

**#90, dependência nova.** O gate falha em três casos, todos no que o diff acrescenta. Um pacote novo falha quando o PyPI ou o npm responde que ele não existe. Um import novo não declarado falha. deptry cobre Python e knip cobre TypeScript. Um advisory OSV `HIGH` ou `CRITICAL` falha quando está ligado a um pacote acrescentado no diff. `MODERATE` e `LOW` ficam em aviso. O padrão de `supply.osv_fail_severities` é `["HIGH", "CRITICAL"]`. `supply.timeout_seconds` tem padrão 30. A issue não fixava esse número. O Emerson aprovou o 30 em 12/10/2026, às 17h55. Timeout, falha de DNS ou resposta que não decide se o pacote existe viram aviso, e o achado fica como não verificado. Um 404 do registro continua falha. O import não declarado sai com 1 mesmo com a rede fora. Os ids são `supply:missing:<índice>:<nome>`, `supply:undeclared:<arquivo>:<módulo>` e `supply:osv:<advisory>`. O índice é o token `pypi` ou o token `npm`.

**#92, complexidade cognitiva.** Métrica extra, aviso, exit 0. complexipy no Python. eslint-plugin-sonarjs no TypeScript, com a LGPL-3.0 já aprovada. Função alterada com valor acima de `cognitive.max_per_function` deixa o gate em `warn`. Valor igual ao limite já gera aviso. O padrão é 15. O corte do igual é o mesmo do CRAP, que falha quando o número é igual ao limite. O Emerson aprovou essa regra de empate em 12/10/2026, às 17h55. Ferramenta ausente neste gate é `not_run` e exit 0, como o jscpd, porque o gate não bloqueia.

**#93, tipos.** Exit 1 para erro novo numa linha do diff, e para escape novo sem waiver. Os escapes são `Any`, `type: ignore`, `as any`, `@ts-ignore` e `@ts-expect-error`. No Python o bob roda o checker que o repositório já configura. mypy roda quando existe `mypy.ini`, `.mypy.ini`, `[mypy]` no `setup.cfg` ou `[tool.mypy]` no `pyproject.toml`. pyright roda quando existe `pyrightconfig.json` ou `[tool.pyright]`. Se os dois existem, os dois rodam. No TypeScript, `tsc` usa o `tsconfig.json` da raiz. Sem ele, o TypeScript fica `not_run` e contribui 0. O aceite da #93 nomeia `@ts-ignore`. `@ts-expect-error` entra no mesmo grupo. A #93 cita type-coverage no título. Esta ADR descarta essa métrica. O critério fechado na triagem é zero erro novo no diff, mais escape novo sem waiver. Um percentual de tipos seria um segundo limiar, e `Any` novo já falha como escape. O executável é o do repositório. Config presente e executável ausente conta como ferramenta ausente dessa linguagem. O bob usa o checker do repositório, sem pin próprio de mypy, pyright ou `tsc`.

**#94, testes do diff.** Aviso. Só regras estáticas, só em teste alterado. A suíte não roda de novo. pytest-randomly não entra. No Python as regras são assert ausente, `sleep`, teste vazio e teste desabilitado (`skip` ou `xfail` acrescentado no diff). No TypeScript entra o eslint-plugin-jest ou o eslint-plugin-vitest que o repositório já configura. Sem o plugin, a metade TypeScript não roda e não falha.

**#95, código morto.** Aviso. Só símbolo cuja definição está no diff. vulture no Python, knip no TypeScript. Com `dead_code.min_confidence` ausente, o bob não passa `--min-confidence`. O vulture aplica o próprio default, inclusive `[tool.vulture]` do repositório. Sem essa tabela, o default em `DEFAULTS` de `vulture/config.py`, lido no main do vulture em 12/10/2026, é 0. Confiança 0 reporta os achados, porque a confiança de cada achado começa em 60. A issue de implementação testa o default da versão pinada. A chave, quando presente, é um inteiro de 0 a 100 e vale mais que o `pyproject.toml`, como a CLI do vulture. knip ignora essa chave.

**#96, churn.** A seção é informativa. Ela sai em todo `bob check` e não tem linha no veredito. Falha de `git log` deixa a seção sem números e o exit permanece o dos outros gates. Churn de um arquivo é o número de commits que o `git log` lista para esse arquivo na janela. A janela tem `churn.window_days` dias, padrão 90, e termina na data do commit de `HEAD`, para o mesmo commit gerar o mesmo número. A issue não fixava o 90. A #96 também chama o churn de relativo. O número aqui é a contagem de commits na janela, não uma taxa. Hotspot de uma função alterada é esse churn vezes a complexidade ciclomática que o lizard já calcula (`FunctionMetric.cc`). Difusão é o número de arquivos alterados dentro de `paths.include` e o número de módulos. Módulo é o diretório pai de cada um desses arquivos. A contagem usa `git log`.

### Ferramenta ausente

Cada linguagem usa a própria ferramenta. Se uma falta e outra linguagem de `languages` mediu o gate, a linguagem sem ferramenta fica de fora e o veredito é o da que rodou. Isso segue a decisão 10 da [0003](0003-exit-codes.md), em que Node ausente não zera o Python. Exit 4, com relatório gravado, só quando o gate que pode sair 1 foi pedido e nenhuma linguagem produziu medição. A exceção da #93 permanece. Sem config, a linguagem não roda e não falha. Config presente e executável ausente conta como ferramenta ausente dessa linguagem.

O exit da ferramenta e o exit do bob não são o mesmo número. mypy, tsc, bandit, gitleaks, deptry e semgrep com `--error` saem com código diferente de 0 quando acham algo. diff-cover faz o mesmo abaixo do piso. Quando esse código está no conjunto que a issue de implementação documenta para a ferramenta, e a saída é parseada, o código não é ferramenta ausente. O veredito lê os achados parseados que cruzam o diff, como as linhas da tabela para a #87, a #88, a #89, a #90, a #92 e a #93. Achado que bloqueia sai 1. Achado de gate que só avisa deixa o gate em `warn` e o exit do bob em 0. O bob não copia o inteiro da ferramenta.

Crash, saída que não parseia, ou exit fora desse conjunto documentado equivalem a ferramenta ausente. No gate que pode sair 1, isso é exit 4 e o relatório é gravado, como a ferramenta ausente do CRAP, do deps e da mutação na [0003](0003-exit-codes.md). No gate que só avisa (`cognitive`, `test_smells`, `dead_code`), ferramenta ausente ou quebrada fica `not_run` e contribui 0, como o jscpd quebrado, que não usa 4.

## Consequências

O exit 1 passa a ter mais donos do que `crap_verdict` e `deps_verdict`. O inteiro não muda. Um 1 junto de um 3 continua saindo 3. Um 4 de ferramenta ausente continua maior do que os dois.

A #87 lê o `coverage.xml` e o lcov que a cobertura já gera. A fração que entra no CRAP permanece a da [0001](0001-adaptadores-sobre-ferramentas-de-mercado.md) e da [0002](0002-o-diff-filtra-o-veredito.md). A mesma execução do knip serve a #90 e a #95.

Colocar estas chaves no `bob.yaml` antes da issue que estende o schema faz o check sair 4. Os guias em `docs/gates.md` e `docs/configuracao.md` só mudam na issue que implementa o gate. Descrever aqui um comando que o código ainda não tem repetiria o desvio que a [0000](0000-architecture-review.md) já marca na spec.

Aprovado pelo Emerson em 12/10/2026, às 17h55 (São Paulo).

- Aviso na #92, na #94 e na #95. Exit 1 na #87 e na #93.
- Na #92, valor igual a `cognitive.max_per_function` já gera aviso. O padrão é 15. O corte do igual é o mesmo do CRAP.
- A #93 descarta o type-coverage. O critério é zero erro novo no diff e escape novo sem waiver.
- `coverage.min_percent` é piso. 80 passa. Abaixo de 80 falha.
- `ERROR` em `security.fail_severities`, junto de `HIGH` e `CRITICAL`.
- `@ts-expect-error` entra no grupo de `@ts-ignore`.
- O `tsc` usa o `tsconfig.json` da raiz. Um monorepo sem esse arquivo deixa o `tsc` em `not_run`.
- `supply.timeout_seconds` fica em 30. `churn.window_days` fica em 90.
- Churn é a contagem de commits na janela.
- Módulo da difusão é o diretório pai do arquivo alterado.
- Os gates novos ficam fora do `DEFAULT_GATES`, do hook e da Action, até uma issue posterior.
- A contagem da #96 usa `git log`.
