# SPEC: bob (plugin de qualidade para agentes; CLI `bob`, PyPI `bob-quality`, marketplaces `bob`) (aprovada pelo Emerson em 10/10/2026)

> Escrita como síntese do que já foi decidido, mais uma rodada de perguntas em aberto numeradas, cada uma com recomendação, redigidas para que "sim" aceite a recomendação.
> Spec aprovada e publicada em `docs/SPEC.md`. Os tickets saíram desta spec (ver a issue `bob: Spec`).
> Pesquisa base: https://app.notion.com/p/3f6cc91c731d81c3bcb0d42894f5acc2 · Repo: https://github.com/fazedordecodigo/bob

## Problem Statement

O Emerson usa vários agentes de código (Cursor, Claude Code, Copilot, Devin). Eles produzem código mais rápido do que um humano consegue revisar, e o **review virou o gargalo**. Hoje não existe um sinal objetivo e barato que diga "este diff é seguro" ou "olhe aqui primeiro". As regras de qualidade escritas em prosa nos prompts são ignoradas ou burladas pelos agentes.

## Solution

Um plugin instalável nos quatro agentes que entrega duas coisas:
1. **Camada de verificação**: a CLI `bob`, que mede o diff com gates determinísticos inspirados no fluxo do Uncle Bob (CRAP, duplicação, mutação, dependências), sai com exit code, e gera um **relatório de review** de uma página que diz ao humano onde focar.
2. **Skills**: dizem ao agente quando rodar cada gate, como reagir a um mutante sobrevivente e como levar o relatório ao corpo do PR.

As ferramentas de mercado (lizard, coverage.py, c8, mutmut, StrykerJS, jscpd, import-linter, dependency-cruiser) entram como **dependências com versão fixada (pip/npm)**, encapsuladas por **adaptadores próprios**. Nenhum código delas é copiado. A lógica do Bob (fórmula CRAP, limiares, escopo no diff, mutação diferencial, waivers justificados) vive no núcleo da CLI.

## User Stories

1. Como revisor, quero um relatório de uma página por PR, para decidir em minutos onde olhar.
2. Como revisor, quero ver as funções alteradas ordenadas por risco (CRAP), para revisar primeiro o código complexo e pouco testado.
3. Como revisor, quero ver os mutantes sobreviventes e as justificativas de waiver, para julgar só o que o agente não conseguiu provar.
4. Como revisor, quero ver clones novos e violações de dependência, para pegar erosão de arquitetura.
5. Como revisor, quero o delta em relação à branch base, para não ser punido por dívida antiga.
6. Como agente de código, quero rodar `bob check` e receber JSON + exit code, para iterar sozinho até passar.
7. Como agente, quero mensagens acionáveis (função, arquivo:linha, métrica, limite), para saber o que corrigir.
8. Como agente, quero uma skill que diga quando rodar cada gate e como reagir, para não depender de prosa no AGENTS.md.
9. Como agente, quero registrar um waiver com justificativa de uma linha, para os mutantes que não devem ser mortos.
10. Como dev, quero que o hook local rode só os gates rápidos (CRAP, duplicação, dependências), para não travar o commit/push.
11. Como dev, quero que a mutação rode só no CI, para não pagar o custo localmente.
12. Como mantenedor, quero configurar limiares e caminhos em um único `bob.yaml`, para adaptar a cada repo.
13. Como mantenedor, quero rodar em projetos Python e TypeScript (incluindo monorepo misto), para cobrir o MVP.
14. Como mantenedor, quero versões fixadas das ferramentas de mercado, para resultados reprodutíveis.
15. Como mantenedor, quero adicionar uma linguagem nova escrevendo só um adaptador, sem mexer no núcleo.
16. Como usuário do Cursor/Claude Code/Copilot/Devin, quero instalar o plugin pelo mecanismo nativo de cada um, para não ter passo manual.
17. Como usuário, quero que cada skill copiada para o meu projeto leve a licença do plugin, para manter a atribuição MIT na cópia achatada.
18. Como mantenedor do CI, quero uma GitHub Action que roda todos os gates e comenta o relatório no PR.
19. Como Emerson, quero que merge e publicação no marketplace dependam da minha aprovação.
20. Como dev, quero uma mutação diferencial (só funções alteradas desde a última execução), para o CI ficar barato.
21. Como revisor, quero que um gate não executado (ferramenta ausente, sem cobertura) apareça como "não executado", e nunca como "passou".

## Implementation Decisions

**Módulos (seams)**
- **Núcleo (domínio)**: modelo `FunctionMetric {lang, module, name, file, start_line, end_line, cc, coverage, crap}`, `Mutant {id, function, file, line, operator, status: killed|survived|timeout|no_coverage, waiver?}`, `Clone`, `DepViolation`. Calcula CRAP (`CC² × (1 − cov)³ + CC`), aplica limiares, delta contra a base e veredito. Não conhece ferramentas.
- **Adaptadores** (um por ferramenta): `lizard` → CC por função; `coverage.py` (JSON) e `c8`/istanbul (`coverage-final.json`/lcov) → cobertura por linha e branch; `mutmut` e `StrykerJS` (mutation-testing-report-schema JSON) → mutantes; `jscpd` (JSON) → clones; `import-linter` e `dependency-cruiser` (JSON) → violações. Cada adaptador recebe a saída bruta e devolve o modelo do núcleo.
- **Escopo de diff**: `git diff <base>...HEAD` → linhas e funções alteradas.
- **Renderização do relatório**: modelo → `report.md` + `report.json`.
- **CLI**: orquestra adaptador → núcleo → relatório → exit code.
- **Seam de teste principal (o mais alto)**: a CLI rodando sobre repositórios-fixture Python e TS. Seam secundário: os adaptadores, alimentados por saídas brutas gravadas (fixtures JSON) das ferramentas reais.

**Interfaces da CLI** (Python ≥ 3.10, distribuída via pip como `bob-quality`; adaptadores TS chamam ferramentas npm fixadas via `npx`; complexidade via lizard nas duas linguagens)
```
bob check   [--base REF] [--gates crap,dry,deps,mutate] [--config bob.yaml] [--format md|json|both] [--out .bob/] [--dry-fail] [--max-new-clones N]
bob crap    [--base REF] [--threshold N] [--coverage-file PATH]
bob dry     [--base REF] [--dry-fail] [--max-new-clones N]
bob deps
bob mutate  [--base REF] [--since-last-run] [--max-workers N]
bob report  [--in .bob/] [--out .bob/report.md]
bob waive   <file::function|Target> --reason "texto de uma linha"
bob doctor  # verifica ferramentas e versões instaladas
bob <comando> [--lang en|pt-BR]  # idioma da saída (padrão: en)
```
Exit codes (inspirados no mutator do Bob):
- `0` passou
- `1` algum gate falhou (limite violado)
- `2` baseline quebrado (testes falham antes de medir)
- `3` mutante sobrevivente sem waiver
- `4` erro de configuração ou ferramenta ausente

Um uso inválido da linha de comando sai com `4`, não grava relatório, e o stderr não menciona baseline. A ajuda (`-h`, `--help`) continua saindo com `0`.

Num monorepo com Python e TypeScript, a ausência do Node não é exit `4`. O Python continua medido. O TypeScript aparece no relatório como pulado, com aviso. O exit code é o dos gates que rodaram: `0` e veredito ⚠️ (não ✅) quando o CRAP medido cabe no limite; `1` e veredito ❌ quando estoura, e o motivo ainda cita o TypeScript pulado. Exit `4` continua quando a ferramenta ausente impede a medição pedida (repositório só TypeScript sem Node, ou configuração inválida).

Por padrão, `check` no hook local executa `crap,dry,deps`; no CI executa todos.

**Configuração `bob.yaml`**
```yaml
base: origin/main
language: en                      # idioma da saída: en ou pt-BR
languages: [python, typescript]
paths: { include: [src], exclude: [tests, node_modules, dist] }
crap: { max_per_function: 10, scope: changed }
duplication: { min_tokens: 50, new_clones: warn, max_new_clones: 0, min_similarity: 0, min_lines: 0 }
coverage: { min_percent: 80 }
dependencies: { python: .importlinter, typescript: .dependency-cruiser.cjs }
```

`crap.scope` é `changed` ou `all`. Cada item de `languages` é `python` ou `typescript`. Uma lista `languages` presente não é vazia, não repete item e não é reescrita pela detecção. A chave `languages` omitida ou nula é autodetectada pelos arquivos em `paths.include`, fora de `paths.exclude`. A varredura não segue symlink, então um ciclo de link não entra no alvo. `paths.exclude` casa por prefixo de caminho, não por glob. `.py` escolhe `python`. `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` e `.cjs` escolhem `typescript`. O resultado sai nessa ordem. Sem nenhum desses arquivos, o resultado é `python`. `crap.max_per_function` é um número finito maior que 0. Um inteiro que não cabe em float também não é finito. `duplication.min_tokens` é um inteiro maior que 0. `duplication.new_clones` é `warn` ou `fail`, e vazio continua `warn`. `duplication.max_new_clones` e `duplication.min_lines` são inteiros maiores ou iguais a 0. `duplication.min_similarity` é um número finito de 0 a 100. `coverage.min_percent` é um número finito de 0 a 100, e o padrão é 80. Igual ao piso passa. O gate `coverage` não entra no `bob check` sem `--gates`. Uma chave desconhecida sai com 4.

**Formato do relatório (`.bob/report.md`, espelhado em `report.json`)**
1. Cabeçalho: commit, base, data, versões das ferramentas.
2. Veredito por gate: ✅ passou / ⚠️ aviso / ❌ falhou / ⏭️ não executado (com motivo).
3. **Onde focar o review**: arquivos alterados ordenados por risco (maior CRAP + sobreviventes + clones).
4. Top 5 funções de maior CRAP no diff (função, arquivo:linha, CC, cobertura, CRAP, delta).
5. Mutantes sobreviventes (sem waiver = falha), mutantes sem teste (`no_coverage`) como ⚠️ agrupados por função e arquivo, e tabela de waivers com justificativa.
6. Clones novos (pares, similaridade, linhas).
7. Violações e ciclos de dependência.
8. Cobertura do diff, só quando o gate `coverage` rodou: percentual de cada linguagem medida e linhas descobertas. No JSON o campo é `diff_coverage`, omitido quando nenhuma linguagem mediu. `schema_version` continua 1.
9. Rodapé: como reproduzir localmente (comando exato).

O JSON segue um schema versionado (`schema_version: 1`). Os títulos e os textos do `report.md` seguem o idioma da saída. O `report.json` não muda com o idioma (decisão 12).

**Waivers**: arquivo `.bob/waivers.yaml` versionado no repo. Cada entrada tem id, motivo de uma linha, autor e data. Um waiver sem motivo é inválido. Todo waiver aparece no relatório. O id de um mutante tem duas formas. `arquivo::função` dispensa todo sobrevivente da função. `arquivo::função::<descrição>` dispensa um sobrevivente. A descrição é o operador do mutante, sem espaço nas pontas. No Python é o diff do `mutmut show`: as linhas removidas, ` -> ` e as linhas acrescentadas. No TypeScript é `{mutatorName}@{linha}:{coluna}-{linha}:{coluna}` do Stryker, mais ` -> {replacement}` quando o relatório traz o texto. A forma exata só existe quando nenhum outro sobrevivente da mesma função tem a mesma descrição. Mutante morto, com timeout ou sem teste não tem alvo. A coluna Alvo do relatório mostra a forma exata de cada sobrevivente, ou `—` quando ela não existe. O id da ferramenta (`__mutmut_N` ou `arquivo:número` do Stryker), o nome nu da função e `arquivo:função` não casam mais. `bob waive` só grava um alvo de um sobrevivente do último `.bob/mutation-cache.json` ou `.bob/stryker-mutants.json`. Outro alvo sai com 4 e nada é gravado. Um id editado à mão que não casa com nenhum sobrevivente deixa o sobrevivente sem waiver, e o gate sai com 3. No TypeScript, uma linha inserida acima do mutante muda a descrição. O waiver antigo deixa de casar e o gate sai com 3. Ele não passa para outro mutante. No Python a descrição é o texto do diff e não muda com uma linha inserida acima. Ver a [ADR 0006](adr/0006-chave-estavel-do-waiver.md).

**Mutação diferencial**: um cache (`.bob/mutation-cache.json`, artefato do CI) guarda o hash do texto de cada função, a versão do mutmut e uma impressão da suíte. A impressão é o hash dos arquivos versionados ou não ignorados que a suíte lê além das funções (`tests/`, `test/`, `conftest*`, `test_*.py`, `*_test.py`, configuração do pytest, lockfiles e o `also_copy` do mutmut). Só remuta funções alteradas ou com sobreviventes. Uma versão nova do mutmut ou uma impressão nova da suíte torna os resultados de mutantes guardados inelegíveis para reuso. A corrida remuta as funções alteradas e as funções que ainda têm um sobrevivente sem waiver nesse arquivo. Resultados que estão só como `killed`, com waiver ou `no_coverage`, fora do diff, não são copiados adiante. Para TS usa o `--incremental` nativo do Stryker. Para Python, filtra os mutantes do mutmut pelas funções do diff. O mutmut roda em `<--out>/mutmut/`, com um link simbólico para cada entrada do topo do repo, menos `.git` e `mutants`. Quando o bob injeta a configuração do mutmut, o `setup.cfg` dessa pasta é um arquivo próprio. O `setup.cfg` e o `mutants/` do repo nunca são escritos, nem quando o processo morre no meio.

**Skills**:
- `bob-check`: quando rodar o check e como interpretar o JSON e iterar.
- `harden`: matar mutantes "dentro do razoável", com waiver justificado; nunca enfraquecer código de produção para matar mutante.
- `review-report`: gera e resume o relatório para o corpo do PR, no molde Summary / Evidence / Merge Danger.
- **A implementação do próprio plugin é feita com TDD.**

**Empacotamento**:
- manifests `.claude-plugin/` (Claude Code; Copilot CLI e Devin também o leem) e `.cursor-plugin/` (Cursor). Não há `.plugin/`: o Copilot o leria antes de `.claude-plugin/`, e um segundo manifesto poderia divergir;
- o campo `skills` de `.claude-plugin/plugin.json` é a fonte única da lista de skills, com uma entrada por pasta de skill. `.cursor-plugin/plugin.json` repete a mesma lista. O instalador lê a lista de `.claude-plugin/plugin.json`. Esta spec não repete a lista. Uma pasta que agrupa skills não entra, porque o Copilot a percorre recursivamente e carregaria tudo o que houver abaixo dela;
- script de instalação que copia as skills listadas, achatadas pelo nome da pasta, para `.github/skills` (Copilot) ou `.agents/skills` (Devin, Cursor e Copilot). Cada uma leva o `LICENSE` mais próximo entre a pasta da skill e a raiz do plugin. O instalador não copia `NOTICE`. Ele apaga do destino uma pasta cujo nome está numa lista fechada de skills que o plugin deixou de distribuir só quando o `NOTICE` dela é um arquivo regular com o texto gravado pela instalação antiga. Um arquivo, um link simbólico, um `NOTICE` que é link simbólico ou uma pasta sem esse texto ficam, e o instalador avisa no stderr. Qualquer outra pasta fica;
- `AGENTS.md`;
- GitHub Action composta que comenta o relatório no PR (atualizando um único comentário).

## Testing Decisions

- **Bons testes testam comportamento externo**: dado um repo-fixture e um diff, a CLI produz este veredito, este exit code e estas linhas no relatório. Os testes não dependem da estrutura interna.
- **Núcleo**: testes unitários da fórmula CRAP (casos de cobertura 0%, 100% e CC 1), limiares, delta e veredito, e validação de waivers.
- **Adaptadores**: testes contra saídas brutas reais gravadas das versões fixadas, um fixture por ferramenta. Um teste de contrato falha se a versão fixada mudar o formato.
- **Ponta a ponta**: dois repos-fixture mínimos (Python/pytest e TS/vitest). Cada um tem casos que passam e casos que falham por CRAP, clone, dependência e mutante sobrevivente. As ferramentas reais rodam no CI.
- **Arte prévia**: os READMEs e as saídas do crapper e do mutator do Bob servem como referência de comportamento (0BSD); não há reuso de código.
- O próprio plugin passa nos seus gates: o repo do plugin roda `bob check` no próprio CI (dogfooding).

## Out of Scope (MVP)

- Linguagens além de Python e TypeScript/JavaScript.
- Visualizador estrutural/UML (estilo uml-viewer).
- Triagem de mutantes por agente (ideia do Bob, fica para depois).
- Dryer estrutural próprio (o MVP usa jscpd).
- CI fora do GitHub Actions (GitLab, Azure).
- Dashboard ou histórico entre PRs além do cache de mutação.
- Publicação nos marketplaces (exige OK do Emerson, depois do MVP).
- Orquestração de agentes em linha de montagem (o Bob a descartou; a supervisão é "gentil").
- Copiar código de ferramentas de terceiros.

## Critérios de aceite do MVP

1. `pip install bob-quality` com versões fixadas mais `bob doctor` mostrando o status de cada ferramenta.
2. Nos repos-fixture Py e TS, `bob check --base main` produz `report.md` e `report.json` válidos (schema v1) e o exit code correto em cada caso de falha.
3. CRAP é calculado por função alterada, com limite 10 configurável, e o top 5 aparece no relatório.
4. Por padrão, clones novos geram ⚠️ e não falham. Com `duplication.new_clones: fail` ou `--dry-fail`, mais clones novos que `duplication.max_new_clones` geram ❌ e exit 1. Uma violação de dependência gera ❌.
5. A mutação roda só no CI e só nas funções alteradas. Um sobrevivente sem waiver dá exit 3. Mutantes sem teste (`no_coverage`) aparecem como aviso (⚠️) e não mudam o exit code. Os waivers sem motivo são rejeitados.
6. Um gate não executado aparece como ⏭️ com motivo, nunca como ✅.
7. O hook local roda `crap,dry,deps` em menos de 60 s no repo-fixture.
8. A Action comenta e atualiza um único comentário com o relatório num PR de teste.
9. O plugin instala localmente no Claude Code e no Cursor, e as skills aparecem no Copilot (`.github/skills`) e no Devin.
10. O instalador copia cada skill do manifesto com o `LICENSE` mais próximo dela e avisa quando não acha nenhum.
11. Todo o código do plugin foi escrito com TDD, tem testes e passa nos próprios gates.
12. Nada é publicado em marketplace nem mergeado sem OK do Emerson.

## Further Notes

- Os limiares refletem os posts recentes do Bob: CRAP < 10 para agentes (https://x.com/unclebobmartin/status/2108946115169030596) e matar mutantes "dentro do razoável" (https://www.aviator.co/podcast/uncle-bob-martin-ai-clean-code).
- As issues #1 a #5 continuam como rascunho de fatias ("aguardando spec"). Depois da aprovação, elas serão regeneradas ou ajustadas a partir desta spec.
- A pasta de skills do Devin foi confirmada na doc oficial: `.agents/skills/<skill-name>/SKILL.md` é a recomendada (https://docs.devin.ai/product-guides/skills).

---

## Decisões fechadas (rodada 1, aceitas pelo Emerson em 10/10/2026)

1. **Linguagem da CLI**: núcleo e CLI em Python, distribuídos via pip (`bob-quality`). As ferramentas npm ficam fixadas num `package.json` do próprio plugin e são chamadas via `npx`.
2. **Complexidade**: lizard para Python e TS, para contar o CC do mesmo jeito nas duas.
3. **Escopo**: os gates bloqueiam só pelas funções alteradas no diff. A dívida antiga aparece apenas como informação.
4. **Duplicação** (Emerson, 12/10/2026). O padrão é aviso. `duplication.new_clones` é `warn` ou `fail`. Sem chave nova, um clone novo continua em aviso e o exit continua 0. `max_new_clones` padrão 0. No modo fail, um clone que passa em `min_similarity` e `min_lines` já falha, status `failed`, exit 1. Os dois filtros só escolhem quem entra na conta. Similaridade ausente conta como 100. No modo warn, nenhum limite numérico falha. O relatório cita `duplication.max_new_clones` e o inteiro no `reason`. `--dry-fail` e `--max-new-clones` existem em `bob dry` e `bob check`, vencem o arquivo nessa execução, e 0 é um teto de verdade. Não há flag para forçar warn. O hook não muda.
5. **Waivers**: o agente cria o waiver com justificativa de uma linha e o humano aprova no review do PR. Os waivers aparecem no topo do relatório. A chave do waiver de mutação é a da [ADR 0006](adr/0006-chave-estavel-do-waiver.md), decidida pelo Emerson em 12/10/2026.
6. **Dependências**: executa as regras que o repo já declara (`.importlinter` / `.dependency-cruiser`), mais uma regra padrão sempre ativa: proibido ciclo de dependência. Só bloqueia quando a origem, o destino, ou outro módulo do mesmo ciclo (componente fortemente conexo) foi alterado no diff. Ciclos e violações antigas aparecem no relatório como informação (`fora do diff; não bloqueia`) e não mudam o exit code.
7. **Distribuição**: CLI `bob`, PyPI `bob-quality`, marketplaces `bob`. A publicação acontece só depois do MVP aprovado pelo Emerson, com o nome reconfirmado como livre na véspera.
8. **Sequência**: tracer bullet primeiro (scaffold + CRAP + relatório + hook, em Python e depois TS). Depois vêm mutação, duplicação/dependências e empacotamento.
9. **Pasta de saída**: `.bob/` (relatórios, `waivers.yaml`, `mutation-cache.json`).
10. **Monorepo sem Node** (aprovada pelo Emerson em 11/10/2026): num repositório com Python e TypeScript, a ausência do Node não é exit 4. O Python continua medido. O TypeScript aparece no relatório como pulado, com aviso (⚠️). O exit code é o do que foi medido: 0 com aviso quando não há falha bloqueante, 1 quando há. Exit 4 continua quando a ferramenta ausente impede a medição pedida (repositório só TypeScript sem Node, ou configuração inválida).
11. **Mutantes sem teste** (Emerson, 11/10/2026): `no_coverage` aparece como aviso no `report.md` e no `report.json` (total e contagem por função e arquivo). O gate mutate fica ⚠️ quando não há sobrevivente sem waiver, e o exit code não muda. A fase 2 (testes de CLI no mesmo processo e `no_coverage` nas funções do diff falhando com exit 3) fica para depois (#31).
12. **Idioma da saída** (#38): `en` (padrão) ou `pt-BR`. Vale a primeira fonte definida: `--lang`, depois `BOB_LANG`, depois `language` no `bob.yaml`, depois `en`. A caixa importa. Um `--lang` ou `BOB_LANG` vazio é inválido e sai com 4. A mensagem em inglês vai para o stderr e nada é gravado. O mesmo vale para um `--lang` ou `BOB_LANG` inválido, um `bob.yaml` que não é mapeamento e um YAML com erro de sintaxe, em `check`, `doctor`, `waive` e nos outros comandos. Uma chave `language` vazia no `bob.yaml` continua ausente. Uma chave com tipo errado, como `crap: 5` ou `crap.max_per_function: abc`, sai com 4. A mensagem em inglês vai para o stderr e cita o arquivo e a chave. Nada é gravado, mesmo com `--lang` ou `language: pt-BR`. O mesmo vale para `paths`, `languages`, `base`, `dependencies` e as listas `include` e `exclude`, em `check`, `doctor`, `waive` e nos outros comandos. Um `duplication` inválido, uma chave desconhecida, um `language` numérico (`bob.yaml: language must be a string`), um `language` fora de `en` e `pt-BR` (`bob.yaml: language must be en or pt-BR`), um `crap.scope` que não é `changed` nem `all`, um item de `languages` que não é `python` nem `typescript`, uma lista `languages` vazia, um item de `languages` repetido, um `crap.max_per_function` que não é um número finito maior que 0 (um inteiro que não cabe em float também não é finito), um `duplication.min_tokens` que não é um inteiro maior que 0, um `waivers` igual a `0`, `false` ou `""`, e um `reason` vazio saem com 4 em `check`, `doctor` e `waive`. O stderr fica em inglês, cita o caminho e o campo, e nada é gravado. Um erro de sintaxe YAML em `.bob/waivers.yaml` também sai com 4, em inglês no stderr, sem gravar relatório e sem alterar o arquivo. Um YAML válido com formato errado faz o mesmo, em `check`, `doctor` e `waive`. A mensagem cita o caminho e o campo, como em `.bob/waivers.yaml: waivers[0].reason must be a string`, `.bob/waivers.yaml: unknown key waivers[0].note` e `.bob/waivers.yaml: waivers[1].id repeats waivers[0].id`. Isso cobre uma lista no topo, um `waivers` que não é lista, um item que não é mapeamento, um campo ausente, uma chave desconhecida dentro da entrada e um id repetido. O idioma muda o texto para humanos. Isso cobre a saída da CLI, a ajuda, `bob doctor`, o hook, o `report.md` e a nota de truncamento do comentário da Action. O `report.json` é o mesmo arquivo nos dois idiomas. O `reason`, o nome da regra de ciclo e o `reproduce` ficam em inglês nesse JSON. O `reproduce` do JSON não leva `--lang`. O `report.md` e o comentário do PR traduzem o nome da regra e incluem o `--lang` usado. Em inglês a regra de ciclo se chama `Forbidden dependency cycle`. Em `pt-BR` se chama `Proibido ciclo de dependência`. Uma regra do dependency-cruiser sem nome usa `dependency` no JSON e `dependência` no Markdown. O input `language` da GitHub Action repassa essa escolha ao `bob check` e ao comentário. Vazio deixa `BOB_LANG` e o `bob.yaml` decidirem. As mensagens ficam num catálogo (`src/bob_quality/messages.py`), e um teste de paridade exige as mesmas chaves e os mesmos placeholders nos dois idiomas.
