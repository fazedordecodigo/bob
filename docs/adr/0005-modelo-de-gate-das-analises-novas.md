# O modelo de gate das análises novas

Status: proposta em 12/10/2026. O merge espera o OK do Emerson. As licenças e a rede citadas abaixo já estão aprovadas.

## Contexto

A issue #86 pede o modelo comum das análises N5 a N8 e N11 a N15, da pesquisa de 12/10/2026. Cada análise diz se bloqueia com exit 1 ou se fica em aviso, qual é o waiver, qual é a chave no `bob.yaml` e qual seção aparece no relatório.

O diff continua escolhendo o que pode bloquear, como na [0002](0002-o-diff-filtra-o-veredito.md). Os códigos continuam 0, 1, 2, 3 e 4, como na [0003](0003-exit-codes.md). O código de produção permanece o da base.

A #91 (N9) instala Node e jscpd na Action do gate DRY que já existe. Fica fora daqui.

## Decisão

Um aviso contribui 0. O status do gate fica `warn`. Um achado que bloqueia, restrito ao diff, sai com 1 (`GATE_FAILED`), o mesmo inteiro do CRAP e das dependências. O 2 continua reservado à suíte que quebra antes da medição. O 3 continua só no sobrevivente sem waiver. O 4 continua em configuração inválida e em ferramenta ausente que impede uma medição pedida. `check.py` fica com o maior código.

As ferramentas medem a árvore de `paths.include`. Só entra no veredito o achado cuja linha cai no lado novo do diff. O resto pode aparecer no relatório e não muda o exit.

O waiver continua em `.bob/waivers.yaml`, com `id`, `reason` de uma linha, `author` e `date`. Sem motivo de uma linha, o preflight sai com 4, em inglês no stderr, e não grava relatório. Cada gate só lê ids com o próprio prefixo. O casamento dos mutantes ignora esses prefixos. Um waiver de segredo ou de tipo não casa com um mutante.

O `schema_version` permanece 1. Os campos novos são opcionais no `report_v1.json`. O JSON fica em inglês. O Markdown traduz o título da seção. As seções novas entram depois de `## Mutantes sem teste` e antes de `## Como reproduzir`. A tabela `## Waivers` é a mesma de hoje.

Nenhum gate novo entra em `DEFAULT_GATES`. O `bob check` sem `--gates` continua `crap,dry,deps`. O hook continua esses três. A Action, sem inputs, continua `crap,dry,deps,mutate`. Ligar um gate novo nessas listas é uma issue de implementação, depois do pin.

A issue que implementa a ferramenta adiciona o pin na lista que `bob doctor` já confere. Versão diferente sai com 4. `bob doctor --install` continua no caminho npm que já existe. Um pin pip entra no pacote como o lizard. Esta ADR não escolhe o número da versão. Ferramenta com licença GPL não entra.

Até a issue de implementação estender o schema, a chave nova é desconhecida e o `bob check` sai com 4. O comportamento de tipo errado, chave desconhecida e valor semântico inválido permanece o da [0003](0003-exit-codes.md).

### Já aprovado em 12/10/2026

O comentário do Emerson nas issues, às 17h06, fecha três pontos. Esta ADR não reabre.

- #88. A LGPL-2.1 do Semgrep CE e as licenças das regras do registry estão aprovadas. O par do gate é Bandit e Semgrep CE.
- #92. A LGPL-3.0 do eslint-plugin-sonarjs está aprovada.
- #90. O gate pode acessar PyPI, npm e OSV. Timeout e modo offline são aviso.

### Por análise

| Issue | Veredito | Waiver | Chave no `bob.yaml` | Relatório |
|---|---|---|---|---|
| [#87](https://github.com/fazedordecodigo/bob/issues/87) N5 | exit 1 | `coverage:<arquivo>` ou `coverage:<arquivo>:<linha>` | `coverage.min_percent`, padrão 80 | `## Cobertura do diff`, campo `diff_coverage` |
| [#88](https://github.com/fazedordecodigo/bob/issues/88) N6 | exit 1 | `sast:<ferramenta>:<regra>` e o mesmo id com arquivo e linha | `security.fail_severities` | `## Segurança`, campo `security` |
| [#89](https://github.com/fazedordecodigo/bob/issues/89) N7 | exit 1 | `secret:<regra>:<arquivo>:<linha>` | `secrets`, sem limiar | `## Segredos`, campo `secrets` |
| [#90](https://github.com/fazedordecodigo/bob/issues/90) N8 | exit 1, com exceção | `supply:missing`, `supply:undeclared` ou `supply:osv` | `supply.osv_fail_severities` e `supply.timeout_seconds` | `## Dependências novas`, campo `supply` |
| [#92](https://github.com/fazedordecodigo/bob/issues/92) N11 | aviso | `cognitive:<arquivo>:<função>` | `cognitive.max_per_function`, padrão 15 | `## Complexidade cognitiva`, campo `cognitive` |
| [#93](https://github.com/fazedordecodigo/bob/issues/93) N12 | exit 1, com exceção | `typing:<arquivo>:<linha>:<código>` | `typing`, sem filhos | `## Tipos`, campo `typing` |
| [#94](https://github.com/fazedordecodigo/bob/issues/94) N13 | aviso | `tests:<arquivo>:<linha>:<regra>` | `test_smells`, sem limiar | `## Testes do diff`, campo `test_smells` |
| [#95](https://github.com/fazedordecodigo/bob/issues/95) N14 | aviso | `dead:<arquivo>:<linha>:<nome>` | `dead_code.min_confidence` | `## Código morto`, campo `dead_code` |
| [#96](https://github.com/fazedordecodigo/bob/issues/96) N15 | não muda o exit | não há | `churn.window_days`, padrão 90 | `## Churn`, campo `churn` |

Os nomes em `--gates` são `coverage`, `security`, `secrets`, `supply`, `cognitive`, `typing`, `test_smells` e `dead_code`. `churn` não é gate e não ganha linha no veredito.

**#87, cobertura do diff.** O limiar é piso. Percentual abaixo de `coverage.min_percent` falha. Percentual igual ao piso passa. O percentual é o que o diff-cover calcula nas linhas novas, a partir do `coverage.xml` do coverage.py e do lcov do c8. Linguagens medidas em separado. Uma abaixo do piso falha o gate. Linguagem sem linha nova cobrível passa. Linha com waiver sai do numerador e do denominador. Waiver de arquivo tira o arquivo inteiro. A suíte que quebra antes de produzir a cobertura sai com 2, como o CRAP. diff-cover ausente, com o gate pedido, sai com 4.

**#88, segurança no diff.** Bandit no Python. Semgrep CE com `--baseline-commit` igual à base do diff. O bob ainda descarta achado fora de `changed_lines`. Falha o que a ferramenta classifica como `HIGH`, `CRITICAL` ou `ERROR` e não tem waiver. `ERROR` entra porque o Semgrep usa essa palavra no lugar de `HIGH`. O resto no diff é aviso. O padrão de `security.fail_severities` é `["HIGH", "CRITICAL", "ERROR"]`. O id sem arquivo cobre a regra no diff inteiro. O id com arquivo e linha cobre um achado. Confiança do Bandit não filtra.

**#89, segredos.** A ferramenta é o gitleaks. Segredo novo no diff falha. A chave `secrets` não tem limiar nem filhos. A allowlist versionada é o waiver. O id não carrega o valor. O relatório mostra arquivo, linha e id da regra. O objeto em `secrets` só tem `file`, `line` e `rule_id`. O teste da implementação falha se o valor aparecer em `.bob/report.md` ou em `.bob/report.json`. A saída bruta do gitleaks fica fora de `.bob/`.

**#90, dependência nova.** O gate falha em três casos, todos no que o diff acrescenta. Um pacote novo falha quando o PyPI ou o npm responde que ele não existe. Um import novo não declarado falha. deptry cobre Python e knip cobre TypeScript. Um advisory OSV `HIGH` ou `CRITICAL` falha quando está ligado a um pacote acrescentado no diff. `MODERATE` e `LOW` ficam em aviso. O padrão de `supply.osv_fail_severities` é `["HIGH", "CRITICAL"]`. `supply.timeout_seconds` tem padrão 30. Timeout, falha de DNS ou resposta que não decide se o pacote existe viram aviso, e o achado fica como não verificado. Um 404 do registro continua falha. O import não declarado sai com 1 mesmo com a rede fora. Os ids são `supply:missing:<índice>:<nome>`, `supply:undeclared:<arquivo>:<módulo>` e `supply:osv:<advisory>`. O índice é o token `pypi` ou o token `npm`.

**#92, complexidade cognitiva.** Métrica extra, aviso, exit 0. complexipy no Python. eslint-plugin-sonarjs no TypeScript, com a LGPL-3.0 já aprovada. Função alterada com valor maior ou igual a `cognitive.max_per_function` deixa o gate em `warn`. O padrão é 15. O valor igual ao limite já entra no aviso, no mesmo corte em que o CRAP falha. Ferramenta ausente neste gate é `not_run` e exit 0, como o jscpd, porque o gate não bloqueia.

**#93, tipos.** Exit 1 para erro novo numa linha do diff, e para escape novo sem waiver. Os escapes são `Any`, `type: ignore`, `as any`, `@ts-ignore` e `@ts-expect-error`. No Python o bob roda o checker que o repositório já configura. mypy roda quando existe `mypy.ini`, `.mypy.ini`, `[mypy]` no `setup.cfg` ou `[tool.mypy]` no `pyproject.toml`. pyright roda quando existe `pyrightconfig.json` ou `[tool.pyright]`. Se os dois existem, os dois rodam. No TypeScript, `tsc` usa o `tsconfig.json` da raiz. Sem essa config, essa linguagem fica `not_run` e contribui 0. O executável é o do repositório. Config presente e executável ausente, com o gate pedido, sai com 4. O bob usa o checker do repositório, sem pin próprio de mypy, pyright ou `tsc`.

**#94, testes do diff.** Aviso. Só regras estáticas, só em teste alterado. A suíte não roda de novo. pytest-randomly não entra. No Python as regras são assert ausente, `sleep`, teste vazio e teste desabilitado (`skip` ou `xfail` acrescentado no diff). No TypeScript entra o eslint-plugin-jest ou o eslint-plugin-vitest que o repositório já configura. Sem o plugin, a metade TypeScript não roda e não falha.

**#95, código morto.** Aviso. Só símbolo cuja definição está no diff. vulture no Python, knip no TypeScript. Com `dead_code.min_confidence` ausente, o bob não passa `--min-confidence`. O vulture aplica o próprio default, inclusive `[tool.vulture]` do repositório. Sem essa tabela, o default em `DEFAULTS` de `vulture/config.py`, lido no main do vulture em 12/10/2026, é 0. Confiança 0 reporta os achados, porque a confiança de cada achado começa em 60. A issue de implementação testa o default da versão pinada. A chave, quando presente, é um inteiro de 0 a 100 e vale mais que o `pyproject.toml`, como a CLI do vulture. knip ignora essa chave.

**#96, churn.** A seção é informativa. Ela sai em todo `bob check` e não tem linha no veredito. Falha de `git log` deixa a seção sem números e o exit permanece o dos outros gates. Churn de um arquivo é o número de commits que o `git log` lista para esse arquivo na janela. A janela tem `churn.window_days` dias, padrão 90, e termina na data do commit de `HEAD`, para o mesmo commit gerar o mesmo número. Hotspot de uma função alterada é esse churn vezes a complexidade ciclomática que o lizard já calcula (`FunctionMetric.cc`). Difusão é o número de arquivos alterados dentro de `paths.include` e o número de diretórios pais distintos desses arquivos. A contagem usa `git log`.

### Ferramenta ausente

Gate que pode sair 1 (`coverage`, `security`, `secrets`, `supply`, `typing`), pedido e sem a ferramenta, sai com 4 e grava o relatório, como o CRAP sem a ferramenta de medição. A exceção da #93 é a ausência de config, que não roda e não falha. Gate que só avisa (`cognitive`, `test_smells`, `dead_code`) segue o jscpd. Ferramenta ausente fica `not_run` e contribui 0.

## Consequências

O exit 1 passa a ter mais donos do que `crap_verdict` e `deps_verdict`. O inteiro não muda. Um 1 junto de um 3 continua saindo 3. Um 4 de ferramenta ausente continua maior do que os dois.

A #87 lê o `coverage.xml` e o lcov que a cobertura já gera. A fração que entra no CRAP permanece a da [0001](0001-adaptadores-sobre-ferramentas-de-mercado.md) e da [0002](0002-o-diff-filtra-o-veredito.md). A mesma execução do knip serve a #90 e a #95.

Colocar estas chaves no `bob.yaml` antes da issue que estende o schema faz o check sair 4. Os guias em `docs/gates.md` e `docs/configuracao.md` só mudam na issue que implementa o gate. Descrever aqui um comando que o código ainda não tem repetiria o desvio que a [0000](0000-architecture-review.md) já marca na spec.

O que espera o OK do Emerson, além do merge:

- A coluna de veredito da tabela. Aviso na #92, na #94 e na #95. Exit 1 na #87 e na #93.
- `coverage.min_percent` é piso. 80 passa. Abaixo de 80 falha.
- `ERROR` em `security.fail_severities`, junto de `HIGH` e `CRITICAL`.
- `@ts-expect-error` no grupo de `@ts-ignore`.
- `tsconfig.json` só na raiz. Um monorepo sem esse arquivo deixa o `tsc` em `not_run`.
- `supply.timeout_seconds` em 30 e `churn.window_days` em 90.
- Gates novos fora do `DEFAULT_GATES`, do hook e da Action, até uma issue posterior.
- A contagem da #96 usa `git log`.
