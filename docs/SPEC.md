# SPEC: bob (plugin de qualidade para agentes; CLI `bob`, PyPI `bob-quality`, marketplaces `bob`) (aprovada pelo Emerson em 10/10/2026)

> Escrita com o método `to-spec` (síntese do que já foi decidido, no template da skill) mais uma rodada de `grill-me`/`grilling` (perguntas em aberto numeradas, cada uma com recomendação, redigidas para que "sim" aceite a recomendação). Fontes: https://github.com/mattpocock/skills/blob/main/skills/engineering/to-spec/SKILL.md e https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md
> Spec aprovada e publicada em `docs/SPEC.md`. Os tickets foram gerados com `to-tickets` (ver a issue `bob: Spec`).
> Pesquisa base: https://app.notion.com/p/3f6cc91c731d81c3bcb0d42894f5acc2 · Repo: https://github.com/fazedordecodigo/bob

## Problem Statement

O Emerson usa vários agentes de código (Cursor, Claude Code, Copilot, Devin). Eles produzem código mais rápido do que um humano consegue revisar, e o **review virou o gargalo**. Hoje não existe um sinal objetivo e barato que diga "este diff é seguro" ou "olhe aqui primeiro". As regras de qualidade escritas em prosa nos prompts são ignoradas ou burladas pelos agentes.

## Solution

Um plugin instalável nos quatro agentes que entrega duas coisas:
1. **Fluxo de trabalho**: as skills do Matt Pocock (MIT, copiadas com atribuição), com o fluxo leve de spec (`grill-me` → `to-spec` → `to-tickets` → `implement-spec`/`tdd`).
2. **Camada de verificação**: a CLI `bob`, que mede o diff com gates determinísticos inspirados no fluxo do Uncle Bob (CRAP, duplicação, mutação, dependências), sai com exit code, e gera um **relatório de review** de uma página que diz ao humano onde focar.

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
17. Como usuário, quero as skills do Pocock incluídas e atribuídas, para seguir o fluxo de spec leve.
18. Como mantenedor do CI, quero uma GitHub Action que roda todos os gates e comenta o relatório no PR.
19. Como Emerson, quero que merge e publicação no marketplace dependam da minha aprovação.
20. Como dev, quero uma mutação diferencial (só funções alteradas desde a última execução), para o CI ficar barato.
21. Como revisor, quero que um gate não executado (ferramenta ausente, sem cobertura) apareça como "não executado", e nunca como "passou".

## Implementation Decisions

**Módulos (seams)**
- **Núcleo (domínio)**: modelo `FunctionMetric {lang, module, name, file, start_line, end_line, cc, coverage, crap}`, `Mutant {id, function, file, line, operator, status: killed|survived|timeout|no_coverage, waiver?}`, `Clone`, `DepViolation`. Calcula CRAP (`CC² × (1 − cov)³ + CC`), aplica limiares, delta contra a base e veredito. Não conhece ferramentas.
- **Adaptadores** (um por ferramenta): `lizard` (radon opcional) → CC por função; `coverage.py` (JSON) e `c8`/istanbul (`coverage-final.json`/lcov) → cobertura por linha e branch; `mutmut` e `StrykerJS` (mutation-testing-report-schema JSON) → mutantes; `jscpd` (JSON) → clones; `import-linter` e `dependency-cruiser` (JSON) → violações. Cada adaptador recebe a saída bruta e devolve o modelo do núcleo.
- **Escopo de diff**: `git diff <base>...HEAD` → linhas e funções alteradas.
- **Renderização do relatório**: modelo → `report.md` + `report.json`.
- **CLI**: orquestra adaptador → núcleo → relatório → exit code.
- **Seam de teste principal (o mais alto)**: a CLI rodando sobre repositórios-fixture Python e TS. Seam secundário: os adaptadores, alimentados por saídas brutas gravadas (fixtures JSON) das ferramentas reais.

**Interfaces da CLI** (Python ≥ 3.10, distribuída via pip como `bob-quality`; adaptadores TS chamam ferramentas npm fixadas via `npx`; complexidade via lizard nas duas linguagens)
```
bob check   [--base REF] [--gates crap,dry,deps,mutate] [--config bob.yaml] [--format md|json|both] [--out .bob/]
bob crap    [--base REF] [--threshold N] [--coverage-file PATH]
bob dry     [--base REF]
bob deps
bob mutate  [--base REF] [--since-last-run] [--max-workers N]
bob report  [--in .bob/] [--out .bob/report.md]
bob waive   <mutant-id|function> --reason "texto de uma linha"
bob doctor  # verifica ferramentas e versões instaladas
bob <comando> [--lang en|pt-BR]  # idioma da saída (padrão: en)
```
Exit codes (inspirados no mutator do Bob):
- `0` passou
- `1` algum gate falhou (limite violado)
- `2` baseline quebrado (testes falham antes de medir)
- `3` mutante sobrevivente sem waiver
- `4` erro de configuração ou ferramenta ausente

Num monorepo com Python e TypeScript, a ausência do Node não é exit `4`. O Python continua medido. O TypeScript aparece no relatório como pulado, com aviso. O exit code é o dos gates que rodaram: `0` e veredito ⚠️ (não ✅) quando o CRAP medido cabe no limite; `1` e veredito ❌ quando estoura, e o motivo ainda cita o TypeScript pulado. Exit `4` continua quando a ferramenta ausente impede a medição pedida (repositório só TypeScript sem Node, ou configuração inválida).

Por padrão, `check` no hook local executa `crap,dry,deps`; no CI executa todos.

**Configuração `bob.yaml`**
```yaml
base: origin/main
language: en                      # idioma da saída: en ou pt-BR
languages: [python, typescript]   # autodetect se omitido
paths: { include: [src], exclude: [tests, node_modules, dist] }
crap: { max_per_function: 10, scope: changed }
mutation: { require_zero_unwaived_survivors: true, scope: changed, differential: true }
duplication: { tool: jscpd, min_tokens: 50, new_clones: warn }
dependencies: { python: .importlinter, typescript: .dependency-cruiser.cjs, violation: fail }
```

**Formato do relatório (`.bob/report.md`, espelhado em `report.json`)**
1. Cabeçalho: commit, base, data, versões das ferramentas.
2. Veredito por gate: ✅ passou / ⚠️ aviso / ❌ falhou / ⏭️ não executado (com motivo).
3. **Onde focar o review**: arquivos alterados ordenados por risco (maior CRAP + sobreviventes + clones).
4. Top 5 funções de maior CRAP no diff (função, arquivo:linha, CC, cobertura, CRAP, delta).
5. Mutantes sobreviventes (sem waiver = falha), mutantes sem teste (`no_coverage`) como ⚠️ agrupados por função e arquivo, e tabela de waivers com justificativa.
6. Clones novos (pares, similaridade, linhas).
7. Violações e ciclos de dependência.
8. Rodapé: como reproduzir localmente (comando exato).

O JSON segue um schema versionado (`schema_version: 1`). Os títulos e os textos do `report.md` seguem o idioma da saída. O `report.json` não muda com o idioma (decisão 12).

**Waivers**: arquivo `.bob/waivers.yaml` versionado no repo. Cada entrada tem id do mutante ou função, motivo de uma linha, autor e data. Um waiver sem motivo é inválido. Todo waiver aparece no relatório.

**Mutação diferencial**: um cache (`.bob/mutation-cache.json`, artefato do CI) guarda o hash do texto de cada função. Só remuta funções alteradas ou com sobreviventes. Para TS usa o `--incremental` nativo do Stryker. Para Python, filtra os mutantes do mutmut pelas funções do diff.

**Skills**:
- `bob`: quando rodar o check e como interpretar o JSON e iterar.
- `harden`: matar mutantes "dentro do razoável", com waiver justificado; nunca enfraquecer código de produção para matar mutante.
- `review-report`: gera e resume o relatório para o corpo do PR, integrada à skill `pr` do Pocock.
- As skills do Pocock vão em `skills/vendor/mattpocock/` com LICENSE MIT e NOTICE (commit de origem).
- **A implementação do próprio plugin usa `implement-spec` e `tdd` do Pocock.**

**Empacotamento**:
- manifests `.claude-plugin/`, `.cursor-plugin/` e `.plugin/` (Copilot);
- script de instalação que copia as skills para `.github/skills`, `.agents/skills` e a pasta de skills do Devin;
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
4. Clones novos geram ⚠️ e não falham. Uma violação de dependência gera ❌.
5. A mutação roda só no CI e só nas funções alteradas. Um sobrevivente sem waiver dá exit 3. Mutantes sem teste (`no_coverage`) aparecem como aviso (⚠️) e não mudam o exit code. Os waivers sem motivo são rejeitados.
6. Um gate não executado aparece como ⏭️ com motivo, nunca como ✅.
7. O hook local roda `crap,dry,deps` em menos de 60 s no repo-fixture.
8. A Action comenta e atualiza um único comentário com o relatório num PR de teste.
9. O plugin instala localmente no Claude Code e no Cursor, e as skills aparecem no Copilot (`.github/skills`) e no Devin.
10. As skills do Pocock estão incluídas com LICENSE MIT e NOTICE.
11. Todo o código do plugin foi escrito via `implement-spec`/`tdd`, com testes, e passa nos próprios gates.
12. Nada é publicado em marketplace nem mergeado sem OK do Emerson.

## Further Notes

- Os limiares refletem os posts recentes do Bob: CRAP < 10 para agentes (https://x.com/unclebobmartin/status/2108946115169030596) e matar mutantes "dentro do razoável" (https://www.aviator.co/podcast/uncle-bob-martin-ai-clean-code).
- As issues #1 a #5 continuam como rascunho de fatias ("aguardando spec"). Depois da aprovação, `to-tickets` vai regenerá-las ou ajustá-las.
- As pastas de skills do Devin vêm de uma fonte de terceiros e precisam de confirmação na doc oficial antes do empacotamento.

---

## Decisões fechadas (grill-me, rodada 1, aceitas pelo Emerson em 10/10/2026)

1. **Linguagem da CLI**: núcleo e CLI em Python, distribuídos via pip (`bob-quality`). As ferramentas npm ficam fixadas num `package.json` do próprio plugin e são chamadas via `npx`.
2. **Complexidade**: lizard para Python e TS, para contar o CC do mesmo jeito nas duas. Radon fica como adaptador opcional.
3. **Escopo**: os gates bloqueiam só pelas funções alteradas no diff. A dívida antiga aparece apenas como informação.
4. **Duplicação**: clones novos geram só aviso (⚠️) e nunca bloqueiam no MVP.
5. **Waivers**: o agente cria o waiver com justificativa de uma linha e o humano aprova no review do PR. Os waivers aparecem no topo do relatório.
6. **Dependências**: executa as regras que o repo já declara (`.importlinter` / `.dependency-cruiser`), mais uma regra padrão sempre ativa: proibido ciclo de dependência. Só bloqueia quando a origem, o destino, ou outro módulo do mesmo ciclo (componente fortemente conexo) foi alterado no diff. Ciclos e violações antigas aparecem no relatório como informação (`fora do diff; não bloqueia`) e não mudam o exit code.
7. **Distribuição**: CLI `bob`, PyPI `bob-quality`, marketplaces `bob`. A publicação acontece só depois do MVP aprovado pelo Emerson, com o nome reconfirmado como livre na véspera.
8. **Sequência**: tracer bullet primeiro (scaffold + CRAP + relatório + hook, em Python e depois TS). Depois vêm mutação, duplicação/dependências e empacotamento.
9. **Pasta de saída**: `.bob/` (relatórios, `waivers.yaml`, `mutation-cache.json`).
10. **Monorepo sem Node** (aprovada pelo Emerson em 11/10/2026): num repositório com Python e TypeScript, a ausência do Node não é exit 4. O Python continua medido. O TypeScript aparece no relatório como pulado, com aviso (⚠️). O exit code é o do que foi medido: 0 com aviso quando não há falha bloqueante, 1 quando há. Exit 4 continua quando a ferramenta ausente impede a medição pedida (repositório só TypeScript sem Node, ou configuração inválida).
11. **Mutantes sem teste** (Emerson, 11/10/2026): `no_coverage` aparece como aviso no `report.md` e no `report.json` (total e contagem por função e arquivo). O gate mutate fica ⚠️ quando não há sobrevivente sem waiver, e o exit code não muda. A fase 2 (testes de CLI no mesmo processo e `no_coverage` nas funções do diff falhando com exit 3) fica para depois (#31).
12. **Idioma da saída** (#38): `en` (padrão) ou `pt-BR`. Vale a primeira fonte definida: `--lang`, depois `BOB_LANG`, depois `language` no `bob.yaml`, depois `en`. Valor vazio conta como ausente, e a caixa importa. Um `--lang` ou `BOB_LANG` inválido que decide o idioma é erro de configuração: exit 4, a mensagem em inglês no stderr e nenhum relatório. Um `language` inválido no `bob.yaml` é erro de configuração como qualquer outro, e o relatório sai no idioma da flag, do ambiente ou em inglês. Um `language` válido continua valendo quando outra chave do arquivo é inválida, e o relatório desse erro sai nesse idioma. O idioma muda só o texto para humanos: saída da CLI, ajuda, `bob doctor`, o hook e o `report.md`. O `report.json` tem as mesmas chaves e os `reason` sempre em inglês, então a mesma entrada dá os mesmos bytes nos dois idiomas. Saída de ferramenta e nomes de regra (`Proibido ciclo de dependência`) passam como vieram. As mensagens ficam num catálogo (`src/bob_quality/messages.py`), e um teste de paridade exige as mesmas chaves e os mesmos placeholders nos dois idiomas.
