# ET-u4-bob-yaml-T1c: Documentar o not_run "no code to measure" com exit 0
Projeto: bob | Unit: u4-bob-yaml | Plano: aidlc-docs/construction/u4-bob-yaml/code-generation/code-generation-plan.md (passo P10)
Repo: https://github.com/fazedordecodigo/bob | Branch base: `main` em `bb08a2c0fd2ceed93223c3f4cd052b86b7cce5de` (merge do #198, T3) | Branch da tarefa: `aidlc/u4-bob-yaml/t1c-docs-no-code`
Versão: v1 (2026-10-20 21:50 UTC-3; SHA fixado em 2026-10-22 06:56 UTC-3, aprovação do Emerson às 06:55: "Aprovo a ET T1c. Pode despachar sobre a main bb08a2c."). Origem: emenda E4 de `T1b-emenda.md`; o Emerson decidiu às 21:42 (UTC-3): "Aprovo a T1b e as emendas E1 a E3, com a T1c separada para a E4. Pode despachar a T1b." Ordem aprovada: T1b → T2 v3 (no #196) → T3 → T1c. Depende da T1b (comportamento que estes docs descrevem) já na `main`.

## Modo de execução
Você executa esta especificação de forma mecânica. Não tome decisões de produto, arquitetura, nomenclatura, biblioteca ou estrutura que não estejam escritas aqui. Se algo faltar, for contraditório, ou o código existente não bater com o descrito, NÃO improvise: pare, abra o PR como rascunho com o que estiver pronto e descreva o bloqueio na seção "Bloqueios".

Esta ET só muda documentação. Os parágrafos novos estão aqui com o texto exato; copie byte a byte.

## Objetivo
Os docs de exit codes (en, pt-BR, ADR 0003) e os dois READMEs passam a dizer que, sem código a medir no `paths.include`, os gates `crap` e `coverage` ficam ⏭️ `not_run` com o motivo "no code to measure" / "nenhum código a medir" e contribuem `0`, e que, num projeto com código, falha do coverage continua `4`.

## Passo 0 — conferir que o comportamento já está na `main` (antes de editar)
Na raiz do checkout da branch, ainda sem mudanças:
```sh
grep -n '"check.no_code"' src/bob_quality/messages.py
grep -n '_NEEDS_CODE = ("crap", "coverage")' src/bob_quality/check.py
```
Esperado: 2 linhas no primeiro (`"check.no_code": "no code to measure",` e `"check.no_code": "nenhum código a medir",`) e 1 no segundo. Se faltar alguma, PARE: a T1b não está na base. Faça um commit vazio (`git commit --allow-empty -m "ET-u4-bob-yaml-T1c: passo 0 bloqueado"`), abra o PR como rascunho com o título da Entrega e ponha em "Bloqueios" a saída dos dois comandos e `git log -1 --format=%H`. Se estiver tudo lá, cole a saída na seção "Passo 0" do corpo do PR e siga.

## Leia antes (somente leitura)
- `docs/exit-codes.md` (en): "## Exit 0" (linha 15; o parágrafo âncora "An unknown gate name is `not_run` and contributes `0`." na linha 19); "### During measurement, with a report" (linha 92; o parágrafo âncora "A warning-only gate (`cognitive`, `test_smells`, `dead_code`) treats a missing or broken tool as `not_run` and contributes `0`. …" na linha 98). Números de `0d85510`; T1b, T2 e T3 não mudam este arquivo. Ache pelo texto da âncora.
- `website/i18n/pt-BR/docusaurus-plugin-content-docs/current/exit-codes.md` (espelho pt-BR): "## Saída 0" (linha 15; âncora "Um nome de gate desconhecido é `not_run` e contribui com `0`." na linha 19); "### Durante a medição, com relatório" (linha 92; âncora "Um gate só de aviso (`cognitive`, `test_smells`, `dead_code`) trata uma ferramenta ausente ou quebrada como `not_run` e contribui com `0`. …" na linha 98).
- `docs/adr/0003-exit-codes.md` (em pt-BR no repo; o site usa o mesmo arquivo nos dois idiomas, sem espelho em `website/i18n`): seção "## Decisão", âncora "Um nome de gate desconhecido grava `not_run` e contribui 0. O processo pode sair 0." (linha 30).
- `README.md`: tabela de exit codes (linhas 142-150); âncora "When more than one gate fails, `bob check` exits with the highest code." (linha 154).
- `README.pt-BR.md`: mesma tabela (linhas 142-150); âncora "Quando mais de um gate falha, `bob check` sai com o código mais alto." (linha 154).
- Como os docs são testados (não mude nada disto):
  - `website/docusaurus.config.js`: lê `../docs` no lugar (`path: '../docs'`), locales `en` e `pt-BR`, `onBrokenLinks: 'throw'`, `onBrokenAnchors: 'throw'` e `onBrokenMarkdownLinks` próprio: link ou âncora quebrada derruba o build.
  - `website/tests/site.test.mjs` (`npm test`): build em en e pt-BR a partir de `docs/`, sidebar, links e âncoras.
  - `.github/workflows/website.yml`: check `website / build` (`npm ci`, `npm run build`, `npm test`) em todo PR que toca `docs/**` ou `website/**`.
  - `tests/test_gate_publications.py`: frases proibidas em `docs/exit-codes.md` e no espelho pt-BR (`test_guides_do_not_say_invalid_duplication_writes_a_report`) e textos fixos dos READMEs (`test_readmes_publish_the_fast_hook_command`).
  - `tests/test_skills_contract.py`: a skill `bob-check` cita `docs/exit-codes.md#exit-4`; o título "## Exit 4" não pode mudar.
  - Não há teste de paridade linha a linha entre `docs/` e `website/i18n/` nem entre os READMEs; a paridade aqui é por esta ET (mesma posição, mesmo conteúdo).

## Regras
| # | Regra |
|---|---|
| R1 | Cada texto novo é um parágrafo novo, numa linha só (os docs do repo não quebram parágrafo), inserido logo depois do parágrafo âncora e separado dele e do seguinte por uma linha em branco. Nenhuma linha existente muda. |
| R2 | Sem link novo e sem âncora nova (o build quebra com âncora errada; o slug em pt-BR tem acento). Nenhum título muda. |
| R3 | Sem `CHANGELOG.md`: ele registra mudança de comportamento (`docs/changelog.md`), e a T1b já registrou esta. |

## Textos exatos a inserir
| # | Arquivo | Depois do parágrafo âncora | Parágrafo novo (exato) |
|---|---|---|---|
| D1 | `docs/exit-codes.md` | "An unknown gate name is `not_run` and contributes `0`." (Exit 0) | ``With no code to measure, `crap` and `coverage` are `not_run` with the reason `no code to measure` and contribute `0`. No code means no `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, or `.cjs` file under `paths.include` and outside `paths.exclude`, without following symlinks. Those two gates then run no tool, and the report shows ⏭️.`` |
| D2 | `docs/exit-codes.md` | "A warning-only gate (`cognitive`, …) … in fail mode too." (During measurement) | ``In a project with code, a coverage tool failure stays `4`. For example, coverage.py's `No data to report.` leaves `crap` or `coverage` `not_run` with exit `4`. Only a project with no code to measure gets the `0` described under Exit 0.`` |
| D3 | `website/i18n/pt-BR/docusaurus-plugin-content-docs/current/exit-codes.md` | "Um nome de gate desconhecido é `not_run` e contribui com `0`." (Saída 0) | ``Sem código a medir, `crap` e `coverage` ficam `not_run` com o motivo `nenhum código a medir` e contribuem com `0`. Sem código quer dizer nenhum arquivo `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` ou `.cjs` sob `paths.include` e fora de `paths.exclude`, sem seguir symlinks. Esses dois gates então não rodam ferramenta, e o relatório mostra ⏭️.`` |
| D4 | `website/i18n/pt-BR/docusaurus-plugin-content-docs/current/exit-codes.md` | "Um gate só de aviso (`cognitive`, …) … também no modo fail." (Durante a medição) | ``Num projeto com código, falha da ferramenta de cobertura continua `4`. Por exemplo, o `No data to report.` do coverage.py deixa `crap` ou `coverage` em `not_run` com exit `4`. Só um projeto sem código a medir recebe o `0` descrito em Saída 0.`` |
| D5 | `docs/adr/0003-exit-codes.md` | "Um nome de gate desconhecido grava `not_run` e contribui 0. O processo pode sair 0." (Decisão) | ``Sem código a medir no `paths.include` (nenhum arquivo `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` ou `.cjs` fora de `paths.exclude`), `crap` e `coverage` gravam `not_run` com o motivo "no code to measure" e contribuem 0. Decisão do Emerson em 20/10/2026 (Q1 da U4), entregue na T1b. Com código, falha do coverage segue 4.`` |
| D6 | `README.md` | "When more than one gate fails, `bob check` exits with the highest code." | ``A gate with nothing to measure does not raise the exit code. With no code under `paths.include` (outside `paths.exclude`), `crap` and `coverage` show ⏭️ `not run (no code to measure)`, and the run can exit `0`.`` |
| D7 | `README.pt-BR.md` | "Quando mais de um gate falha, `bob check` sai com o código mais alto." | ``Um gate sem nada a medir não aumenta o exit code. Sem código sob `paths.include` (fora de `paths.exclude`), `crap` e `coverage` mostram ⏭️ `não executado (nenhum código a medir)`, e a execução pode sair com `0`.`` |

Os textos acima vão sem as crases duplas de fora da célula (elas só delimitam o texto nesta tabela). As crases simples internas fazem parte do texto.

## Arquivos a modificar (lista fechada: 5 arquivos)
1. `docs/exit-codes.md` — D1, D2.
2. `website/i18n/pt-BR/docusaurus-plugin-content-docs/current/exit-codes.md` — D3, D4.
3. `docs/adr/0003-exit-codes.md` — D5.
4. `README.md` — D6.
5. `README.pt-BR.md` — D7.

## Arquivos proibidos
Qualquer outro. Em especial: `CHANGELOG.md` (R3), `src/**`, `tests/**`, `skills/**`, `scripts/**`, `website/docusaurus.config.js`, `website/tests/**`, `website/sidebars.js`, os demais arquivos de `docs/` e de `website/i18n/`, e `aidlc-docs/**`.

## Sobreposição com a T2 e a T3
Nenhuma. A T2 muda `CHANGELOG.md`, `src/bob_quality/messages.py`, `src/bob_quality/setup_cmd.py` e `tests/test_setup_cmd.py`; a T3 muda `scripts/verify-install.sh`, `tests/test_verify_install.py` e `CHANGELOG.md`; a T1b mudou `CHANGELOG.md`, `check.py`, `messages.py` e três arquivos de teste. A T1c não toca nenhum deles (por isso não tem `CHANGELOG.md`, R3). Se, na base fixada, algum dos 5 arquivos não tiver a âncora com o texto exato acima, pare e descreva em "Bloqueios".

## Testes a escrever
Nenhum. Esta ET não cria nem muda teste. A verificação é por comando (abaixo).

## Comandos a rodar e resultado esperado
- Posição e texto, para cada D1–D7: `grep -nFx -- '<parágrafo âncora inteiro>' <arquivo>` dá a linha `N`, e `sed -n "$((N+2))p" <arquivo>` imprime exatamente o parágrafo novo; `sed -n "$((N+1))p;$((N+3))p" <arquivo>` imprime duas linhas vazias. Cole as 7 saídas.
- `grep -cF 'no code to measure' docs/exit-codes.md README.md docs/adr/0003-exit-codes.md` → `docs/exit-codes.md:2` (D1 e D2), `README.md:1`, `docs/adr/0003-exit-codes.md:1` (em `0d85510` os três davam `0`).
- `grep -cF 'nenhum código a medir' website/i18n/pt-BR/docusaurus-plugin-content-docs/current/exit-codes.md README.pt-BR.md` → `…/exit-codes.md:1` (só D3), `README.pt-BR.md:1` (em `0d85510` os dois davam `0`).
- `git diff --numstat origin/main...HEAD` → só os 5 arquivos, com `0` linhas removidas em cada; `exit-codes.md` (en e pt-BR) com `4` linhas adicionadas, os outros três com `2`.
- `python -m pytest -q tests/test_gate_publications.py tests/test_skills_contract.py` → exit 0; `0 failed`.
- `python -m pytest -q` → exit 0; `0 failed`; sem `error`.
- `cd website && npm ci && npm run build && npm test` (Node `>=22.18.0 <23`) → os três com exit 0; nenhum aviso de link ou âncora quebrada.
- `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → exit 0.

## Critérios de aceite (todos binários)
- [ ] Passo 0 colado no corpo, com as 3 linhas esperadas.
- [ ] O PR muda exatamente os 5 arquivos, só com linhas adicionadas (numstat acima).
- [ ] D1–D7 estão nas posições da R1, com o texto exato (7 saídas de `grep`/`sed` coladas).
- [ ] Nenhum título, link ou âncora novo ou mudado.
- [ ] Suíte inteira: 0 failed, 0 errors; `test_gate_publications.py` e `test_skills_contract.py` passam sem edição.
- [ ] `npm run build` e `npm test` do `website/`: exit 0.
- [ ] `bob check … crap,dry,deps,mutate,coverage`: exit 0.
- [ ] Checks do PR verdes: os 6 (`bob / check`, `bob / cold`, `CI / pytest (3.10)`, `CI / pytest (3.12)`, `package / dist`, `verify-install / linux-x64`) e mais `website / build`, que roda porque o PR toca `docs/**` e `website/**`.
- [ ] Corpo do PR cita U4, T1b, Q1 (Emerson, 2026-10-20 21:18 UTC-3), a decisão de 21:42 (T1c separada para a E4), CT1, CT7, ADR 0015, `docs/adr/0003-exit-codes.md`, e traz "Decisões tomadas: nenhuma".
- [ ] O PR não foi mergeado pelo agente.

## Restrições
- ≤ 100 colunas nas linhas novas de código e testes; no CHANGELOG.md, cada entrada pode quebrar em várias linhas de ≤ 100 colunas, mantendo o texto exato da ET (quebra só em espaço). Nesta ET não há código, teste nem CHANGELOG: os parágrafos de docs ficam numa linha só (R1), como o resto dos docs.
- Literais que geram mutante equivalente: não se aplica a docs, mas não mexa em `src/` para "alinhar" texto; mensagem e doc divergentes são Bloqueio, não correção.
- Não pular, desabilitar nem marcar testes como skip/only.
- Lista de testes fechada. Se o gate `mutate` deixar mutante sobrevivente que só um teste fora da lista mataria, NÃO acrescente o teste: abra o PR como rascunho e descreva em "Bloqueios" o mutante (arquivo, linha, mutação) e o teste proposto (nome e Dado / Quando / Então).
- Nenhum waiver novo.
- Bloqueio que surgir depois de o PR estar aberto vai só na seção Bloqueios do corpo; não tente voltar o PR para rascunho.

## Fora de escopo
- `docs/guides/gates-and-waivers.md`, `docs/reference/cli.md` e os demais docs; a skill `bob-check`.
- Mudar comportamento, mensagens ou testes (T1b).
- `CHANGELOG.md` (R3).

## Entrega
PR para `main` com título "ET-u4-bob-yaml-T1c: Documentar o not_run \"no code to measure\" com exit 0". Corpo: "Resumo", "Passo 0" (comandos e saída), "Arquivos", "Textos" (D1–D7 com as saídas de `grep`/`sed`), "Comandos" (cada comando com a saída; do `npm`, o fim da saída), "Decisões tomadas: nenhuma", "Bloqueios" (vazio ou a lista), e as referências U4, T1b, Q1, a decisão de 21:42, CT1, CT7, ADR 0015, `docs/adr/0003-exit-codes.md`. Sem bloqueio, abra o PR pronto para revisão (não como rascunho); rascunho só quando houver item em "Bloqueios".
