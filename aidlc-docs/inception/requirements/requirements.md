# 2.3 Requirements — bob: instalação e configuração sem plugin nativo

Profundidade: Minimal. Autor: Analista de Produto. Data: 2026-10-18 (UTC-3).
Insumos: `ideation/intent/intent.md`, `ideation/intent/intent-questions.md`, `inception/reverse-engineering/*` (2.1), `inception/requirements/requirements-questions.md` (respondido em 2026-10-18 17:19 UTC-3).
Este documento diz o quê e por quê. Não escolhe mecanismo, linguagem nem formato técnico.

Legenda de origem:
- `I-Cn`: critério de sucesso n do intent. `I-Qn`: pergunta n do 1.1. `I-Sn`: suposição n do intent.
- `RE-Qn`: pergunta n do 2.1. `RE-GA`: `gap-analysis.md`. `RE-TS`: `technology-stack.md`. `RE-CO`: `components.md`.
- `R-Sn`: suposição nova deste estágio (confirmada). `RQ-Q1`: pergunta 1 deste estágio. `G-2.3`: decisão do Emerson no portão do 2.3. `D-2.6`: decisão do Emerson no 2.6 (pasta das skills). `A1`: adendo A1 (pedido do Emerson na rodada 1 do 2.8). `CT18`: contrato do prompt de IA.

## Refinamentos vindos do 2.1 (o intent.md não foi editado)
- **RE-Q1 A**: o comando instala e confere o gitleaks 8.30.1 em Linux e macOS. Isso conta dentro dos 5 minutos. O gitleaks não é pré-requisito. A I-S1 vale só para Python e Node.
- **RE-Q2 B**: o `bob.yaml` criado usa os padrões do README, exceto `paths.include`, que vem das pastas de código do projeto. Isso estreita a I-S4.

## Decisão do portão (2.3)
- Emerson, via Maestro, 2026-10-18 ~17:22 (UTC-3): "Aprovo o 2.3, contando só release publicada como última release. Pode seguir para o 2.4 Histórias."
- Efeito: pré-release e rascunho de release não contam como "última release" (FR1.4, FR6.1, P2). Fecha a lacuna de pré-release apontada no fechamento do 2.3.

## Requisitos funcionais

### FR1 — Instalação por um comando
- **FR1.1** Um único comando, rodado na raiz do projeto, deixa o projeto "configurado": comando `bob`, ferramentas, skills, `bob.yaml` e hook pre-push. Origem: I-C1, I-Q3 C, I-Q6 A.
- **FR1.2** O dev obtém o bob direto do repositório GitHub. Não clona à mão. Não usa o PyPI para o `bob-quality`. Origem: I-Q2 C, I-C6.
- **FR1.3** Nenhum plugin nativo de agente é necessário, em nenhum passo. Origem: pedido literal, I-Q4 A, I-C2.
- **FR1.4** O comando instala a última release publicada (tag) do bob no GitHub. Pré-release e rascunho não contam. Origem: RQ-Q1 A, G-2.3, I-Q2 C, RE-GA (critério 5).
- **FR1.5** Ao final, o comando roda `bob doctor` e mostra o resultado. Origem: I-C1.

### FR2 — Ferramentas
- **FR2.1** Ficam disponíveis todas as ferramentas que o `bob doctor` confere, nas versões pinadas. Origem: I-C1, RE-CO §7.
- **FR2.2** O comando baixa e confere o gitleaks 8.30.1 em Linux e macOS. Origem: RE-Q1 A.
- **FR2.3** Se a conferência de integridade de um binário baixado falhar, o binário não é instalado e o comando para com erro. Origem: RE-Q1 A ("baixa e confere").
- **FR2.4** O comando não altera as dependências do próprio projeto (por exemplo `package.json`, lockfiles, `requirements`). Origem: I-S2, RE-GA (riscos extras).
- **FR2.5** Num projeto que tem ferramentas próprias com outras versões (por exemplo vitest ou eslint), o `bob doctor` confere as ferramentas do bob, não as do projeto. Origem: RE-GA (riscos extras), I-C1.

### FR3 — Skills
- **FR3.1** As três skills do bob (`bob-check`, `harden`, `review-report`) ficam dentro do projeto. Origem: I-Q3 C, I-C2, RE-CO §4.
- **FR3.2** As skills ficam numa única pasta do projeto, `.agents/skills`, sem cópia em outras pastas. Cursor, Claude Code, GitHub Copilot e Devin devem enxergá-las dali, sem plugin nativo. No Claude Code isso fica sob risco aceito (RA1). Origem: I-Q4 A, I-C2, RE-GA (achado 3), D-2.6.
- **FR3.3** Cada agente carrega cada skill uma única vez. Nada de duplicata no Devin. Origem: RE-GA (decisão 4), ADR 0004 (consequências).
- **FR3.4** Skills de outras origens no projeto ficam intactas. Origem: I-S2, RE-CO §3.

### FR4 — `bob.yaml`
- **FR4.1** Se o projeto não tem `bob.yaml`, o comando cria um. Origem: I-Q3 C, I-C3.
- **FR4.2** Todas as chaves usam os padrões do README, exceto `paths.include`. Origem: RE-Q2 B, I-S4.
- **FR4.3** `paths.include` lista as pastas de código que existem no projeto. Origem: RE-Q2 B.
- **FR4.4** O `bob.yaml` criado é válido: `bob check` não sai com 4 por configuração. Origem: I-C3.
- **FR4.5** Se o projeto não tem nenhuma pasta de código reconhecível, o comando ainda cria um `bob.yaml` válido e avisa o dev disso. Origem: I-C3, RE-GA (decisão 11).
- **FR4.6** Se o `bob.yaml` já existe, o comando não o altera e avisa o dev. Origem: I-S2, R-S3.

### FR5 — Hook pre-push
- **FR5.1** O hook pre-push fica ativo e roda `bob check --gates crap,dry,deps`. Origem: I-Q3 C, I-C4, RE-CO §6.
- **FR5.2** O hook funciona num `git push` comum, sem o dev ativar ambiente nenhum antes. Origem: I-C4, RE-GA (critério 4).
- **FR5.3** Se já existe um hook pre-push, o comando não o altera e avisa o dev. Origem: I-S2, R-S3.

### FR6 — Atualização
- **FR6.1** Um único comando atualiza o bob no projeto para a release publicada mais nova do GitHub. Pré-release e rascunho não contam. Origem: RQ-Q1 A, G-2.3, I-Q5 B, I-C5.
- **FR6.2** Depois da atualização, `bob doctor` sai com 0 e as skills do projeto são as da versão nova. Origem: I-C5.
- **FR6.3** A atualização preserva o `bob.yaml`, o `.bob/waivers.yaml`, hooks e skills de outras origens. Origem: I-S3, I-S2.
- **FR6.4** O dev consegue ver qual versão (release) do bob está instalada no projeto. Origem: RQ-Q1 A, I-C5.
- **FR6.5** Se o projeto já está na release mais nova, o comando de atualização avisa, não altera nada e sai com 0. Origem: RQ-Q1 A, NFR4.

### FR7 — Mensagens e erros
- **FR7.1** Ao final, o comando mostra um resumo: o que instalou, o que preservou e o resultado do `bob doctor`. Origem: I-S2 ("avisar"), I-C1.
- **FR7.2** Em falha, o comando diz qual passo falhou e o que o dev deve fazer. Sai com código diferente de 0. Origem: I-Q1 C (comunidade), README (exit codes).
- **FR7.3** Antes de instalar, o comando confere Python e Node. Fora da faixa, para e cita a versão exigida. Origem: I-S1, RE-TS (runtimes).

### FR8 — Documentação
- **FR8.1** O README (pt-BR e en) e os docs de instalação mostram o comando único como caminho principal. Origem: I-C6, I-Q1 C.
- **FR8.2** Os docs listam os requisitos reais (Python e Node; gitleaks entra pelo comando) e as versões pinadas certas. Origem: RE-TS (divergências 3 a 7), RE-Q1 A.
- **FR8.3** Os docs explicam como atualizar e como ver a versão instalada. Origem: I-Q5 B, FR6.4.

## Requisitos não funcionais

| ID | Requisito | Métrica | Alvo | Origem |
|---|---|---|---|---|
| NFR1 | Tempo de instalação | Minutos do início do comando até `bob doctor` = 0, em projeto novo, com Python e Node presentes | ≤ 5 min em Linux e em macOS (R-S6) | I-Q6 A, I-C1, RE-Q1 A |
| NFR2 | Esforço do dev | Comandos para instalar; comandos para atualizar; clones manuais; arquivos editados à mão | 1; 1; 0; 0 | I-C1, I-C5, I-C6 |
| NFR3 | Plataformas | Critérios de aceitação que passam em cada plataforma | 100% em Linux e em macOS (arquiteturas: R-S1) | I-S5, RE-Q1 A |
| NFR4 | Repetição segura | Segunda execução seguida do comando de instalação | Sai com 0; 0 arquivos do dev alterados; 0 skills duplicadas | I-S2, I-S3 |
| NFR5 | Preservação | Bytes alterados em `bob.yaml`, `.bob/waivers.yaml`, hook pre-push e dependências do projeto já existentes, na instalação e na atualização | 0 | I-S2, I-S3, FR2.4 |
| NFR6 | Integridade | Binários baixados conferidos antes do uso; binários instalados quando a conferência falha | 100%; 0 | RE-Q1 A |
| NFR7 | Privilégio | Passos que pedem `sudo` ou senha de administrador | 0 (R-S2) | R-S2 |
| NFR8 | Hook rápido | Duração do hook pre-push no repo-fixture | < 60 s (mesmo alvo de hoje) | I-C4, README (`tests/test_hook.py`) |
| NFR9 | Clareza de erro | Falhas do comando que citam o passo e a ação a tomar | 100% | FR7.2, I-Q1 C |

## Critérios de aceitação (verificáveis)
1. Num projeto novo (R-S8), em Linux e em macOS, um comando leva até `bob doctor` = 0 em ≤ 5 min. (FR1, FR2, NFR1)
2. Depois disso, as três skills, só em `.agents/skills`, aparecem uma vez em cada agente: Cursor, Claude Code, GitHub Copilot, Devin. Sem plugin. (FR3) Para o Claude Code, este critério (e o critério 2 do intent) fica sob risco aceito pelo Emerson (RA1); o intent.md não foi editado.
3. `bob check` não sai com 4 por configuração, com e sem pasta `src/`. (FR4)
4. Um `git push` dispara o hook e roda `bob check --gates crap,dry,deps`, sem ativar ambiente. (FR5)
5. Depois de sair uma release mais nova no GitHub, um comando atualiza o projeto para ela. A versão mostrada é a nova. `bob doctor` = 0, skills novas, `bob.yaml` e waivers intactos. (FR6)
6. Nenhum passo clona o repo do bob à mão nem instala plugin. (FR1.2, FR1.3)
7. Num projeto com `bob.yaml` e hook já existentes, os dois ficam byte a byte iguais e o dev é avisado. (FR4.6, FR5.3, NFR5)

## Suposições
Herdadas do intent (aprovadas em 2026-10-18 16:52 UTC-3), com refinamento:
- **I-S1** Python e Node presentes, fora dos 5 min. Refinada por RE-Q1 A: gitleaks não é pré-requisito.
- **I-S2** Não sobrescrever `bob.yaml` ou hook sem avisar. Detalhada em R-S3.
- **I-S3** Atualizar preserva `bob.yaml` e `.bob/waivers.yaml`.
- **I-S4** `bob.yaml` com padrões do README. Estreitada por RE-Q2 B (`paths.include` derivado).
- **I-S5** Linux e macOS. Windows fora. Detalhada em R-S1.
- **I-S6** O projeto é um repositório git.

Novas deste estágio (**confirmadas pelo Emerson**, via Maestro, 2026-10-18 17:19 UTC-3: "Q1 A e confirmo as suposições R-S1 a R-S8."):
- **[SUPOSIÇÃO R-S1]** "Linux e macOS" quer dizer x64 e arm64 nas duas.
- **[SUPOSIÇÃO R-S2]** Nada pede `sudo`. Tudo fica na conta do usuário ou no projeto.
- **[SUPOSIÇÃO R-S3]** "Não sobrescrever sem avisar" (I-S2) quer dizer: sempre preservar e avisar. O comando não pergunta nada. Não há modo de forçar nesta entrega.
- **[SUPOSIÇÃO R-S4]** As skills vão sempre para os quatro agentes, numa única pasta: `.agents/skills` (D-2.6). O dev não escolhe agentes.
- **[SUPOSIÇÃO R-S5]** A máquina tem acesso à internet: GitHub, registro npm e PyPI (para as dependências pinadas; o `bob-quality` não vem do PyPI).
- **[SUPOSIÇÃO R-S6]** Os 5 min são medidos numa máquina comum de CI (um runner Linux e um macOS padrão), com rede normal.
- **[SUPOSIÇÃO R-S7]** As mensagens do comando seguem a regra de idioma do bob: inglês por padrão, pt-BR por `--lang` ou `BOB_LANG`.
- **[SUPOSIÇÃO R-S8]** "Projeto novo" = repo git com pelo menos um commit e algum código, sem `bob.yaml`, sem hook pre-push e sem skills do bob.

## Fora de escopo
- Publicar o `bob-quality` no PyPI nesta entrega. Origem: I-Q2 C.
- Desinstalar. Origem: I-Q5 B.
- Codex como alvo. Origem: I-Q4 A. Se uma pasta de skills que o Codex também lê for usada, isso é efeito colateral, não requisito.
- Publicação como plugin em marketplaces (#145, #147, #148, #149). Origem: intent.
- GitHub Action e workflow de CI no projeto do dev. Origem: I-Q3 C.
- Windows. Origem: I-S5.
- Mudar gates, limiares ou o formato do `bob.yaml`. Origem: intent.
- Escolher agentes na instalação e modo de forçar sobrescrita. Origem: R-S3, R-S4.

## Pré-condições e dependências
- **P1** Hoje a `main` sai com `bob doctor` = 4 (vitest 5.0.5 no `package.json` vs. 5.0.4 no doctor). Precisa ser corrigido antes da release, senão o critério 1 não passa. Origem: RE-TS (divergência 1), aidlc-state.md (pendência). Afeta: FR1.5, FR2.1, NFR1.
- **P2** Precisa existir uma release publicada no GitHub (não pré-release, não rascunho). A primeira é a v0.1.0. A ação vai para o plano de entrega (2.9) e exige OK do Emerson (issue #10: release e tags). Origem: RQ-Q1 A. Afeta: FR1.4, FR6.1, critérios 1 e 5. Depende de P1.
- **P3** **Resolvida no 2.6** (D-2.6, 2026-10-18 ~18:31 UTC-3): pasta única `.agents/skills` para os quatro agentes. Risco do Claude Code registrado em RA1. Origem: RE-GA (critério 2, achado 3). Afeta: FR3.2, FR3.3, critério 2.

## Riscos aceitos
- **RA1** A doc do Claude Code só cita `.claude/skills` para skills de projeto. Com a pasta única `.agents/skills`, o Claude Code pode não enxergar as skills do bob. Isso afeta FR3.2, o critério 2 deste documento e o critério 2 do intent. Aceito pelo Emerson no 2.6, via Maestro, 2026-10-18 ~18:31 (UTC-3): "Aceito o risco no Claude Code e mantenho .agents/skills."

## Adendo A1 — instalação por prompt de IA (2.8 rodada 1)
Origem: Emerson, via Maestro, 18/10/2026 (UTC-3; 19:14 e 19:15 segundo o CT18, repassado ao Analista ~19:33): (1) "Adicione um prompt que orie te um modelo de IA a como instalar passo a passo o pacote sem depender de um arquivo .sh"; (2) "Deve haver as duas opções a principal sendo o arquivo .sh". Contrato: `inception/contracts/contract-summary.md`, CT18.
Itens aprovados antes não foram reescritos. As notas abaixo só dizem como eles se aplicam ao caminho novo.

### Requisitos funcionais novos
- **FR1.6** Além do comando único (caminho principal), o bob oferece um prompt que guia um agente de IA a instalar e configurar o bob no projeto, passo a passo, sem baixar nem executar o `install.sh`. É alternativa, nunca substituto. Origem: A1 (1) e (2), CT18.
- **FR1.7** O prompt chega ao mesmo resultado do comando único: última release publicada (FR1.4), ferramentas e gitleaks conferidos (FR2.1, FR2.2, FR2.3), skills só em `.agents/skills` (FR3.2, RA1), `bob.yaml` (FR4), hook (FR5), preservação do que já existe (FR2.4, FR4.6, FR5.3), sem clone, sem plugin (FR1.2, FR1.3) e sem `sudo` (NFR7). Em divergência, vale o comando único. Origem: A1 (2), CT18 ("Mesmo resultado", "Posição").
- **FR1.8** O prompt manda o agente parar no primeiro passo que falhar, mostrar ao humano a saída completa e não tentar contornar. No fim, o agente mostra a saída da configuração e da verificação. Origem: A1 (1) ("passo a passo"), CT18 (Regras 6 e 7), NFR9.
- **FR8.4** Os docs de instalação (README pt-BR e en, `docs/instalacao.md`, `docs/getting-started/installation.md`) mostram primeiro o comando único, como caminho principal. Depois, numa seção marcada como alternativa, mostram o prompt, dizem que ele chega ao mesmo resultado e que, em divergência, vale o comando único. Origem: A1 (2), CT18, CT17.
- **FR8.5** O prompt faz parte da documentação do repo, em pt-BR e en, na mesma versão do código. Quando o comando único muda o resultado, o prompt muda na mesma release. Origem: A1 (1), CT18 ("Arquivos", "Posição").

### Requisitos não funcionais novos

| ID | Requisito | Métrica | Alvo | Origem |
|---|---|---|---|---|
| NFR10 | Paridade dos caminhos | Itens do resultado final iguais entre prompt e comando único (versão, ferramentas, skills, `bob.yaml`, hook, preservação), por release | 100% | A1 (2), CT18 ("Mesmo resultado") |
| NFR11 | Independência do `install.sh` | Passos do prompt que citam `install.sh` ou `sudo`; downloads ou execuções do `install.sh` numa instalação pelo prompt | 0; 0 | A1 (1), CT18 (Regras 1 e 2) |

### Notas sobre itens aprovados (texto original mantido)
- **NFR1** (≤ 5 min) e **NFR2** (1 comando) medem só o caminho principal. O prompt não conta como "comando" e não tem meta de tempo (A1-S1).
- **NFR3**, **NFR5**, **NFR6**, **NFR7** e **NFR9** valem também para o prompt.
- Atualizar (**FR6**) segue só pelo comando de atualização. O prompt cobre só a instalação (A1-S2).
- **R-S7** (idioma): no prompt, as mensagens dos passos ficam em inglês; só a configuração e a verificação seguem `BOB_LANG` (A1-S3).
- **RA1** vale igual: o prompt usa a mesma pasta `.agents/skills`.

### Suposições do adendo (confirmadas pelo Emerson)
- **[SUPOSIÇÃO A1-S1 — CONFIRMADA 18/10/2026 ~20:24]** NFR1 e NFR2 valem só para o comando único. O tempo do prompt depende do agente; não há meta.
- **[SUPOSIÇÃO A1-S2 — CONFIRMADA 18/10/2026 ~20:24]** O prompt cobre só instalar. Atualizar segue pelo comando do FR6.1. O CT18 não trata de atualização.
- **[SUPOSIÇÃO A1-S3 — CONFIRMADA 18/10/2026 ~20:24]** No prompt, as mensagens dos passos ficam só em inglês, exceto configuração e verificação, que seguem `BOB_LANG`. Exceção à R-S7, aceita pelo CT18 como "diferença permitida".
- **[SUPOSIÇÃO A1-S4 — CONFIRMADA 18/10/2026 ~20:24]** O agente que recebe o prompt consegue rodar comandos de shell na raiz do projeto.
- **[SUPOSIÇÃO A1-S5 — CONFIRMADA 18/10/2026 ~20:24]** A paridade com agente real é conferida à mão a cada release, com pelo menos um agente (CT18, verificação manual).
- Confirmação do Emerson, via Maestro (18/10/2026 ~20:24 UTC-3): "Confirmo as suposições A1-S1 a A1-S5."

## Rastreabilidade

| Origem | Requisitos |
|---|---|
| Pedido literal | FR1.3 |
| I-C1 | FR1.1, FR1.5, FR2.1, FR2.5, FR7.1, NFR1, NFR2 |
| I-C2 | FR1.3, FR3.1, FR3.2 |
| I-C3 | FR4.1, FR4.4, FR4.5 |
| I-C4 | FR5.1, FR5.2, NFR8 |
| I-C5 | FR6.1, FR6.2, FR6.4, NFR2 |
| I-C6 | FR1.2, FR8.1, NFR2 |
| I-Q1 C | FR7.2, FR8.1, NFR9 |
| I-Q2 C | FR1.2, FR1.4 |
| I-Q3 C | FR1.1, FR3.1, FR4.1, FR5.1 |
| I-Q4 A | FR1.3, FR3.2 |
| I-Q5 B | FR6.1, FR8.3 |
| I-Q6 A | FR1.1, NFR1 |
| I-S1 | FR7.3 |
| I-S2 | FR2.4, FR3.4, FR4.6, FR5.3, FR6.3, FR7.1, NFR4, NFR5 |
| I-S3 | FR6.3, NFR4, NFR5 |
| I-S4 | FR4.2 |
| I-S5 | NFR3 |
| RE-Q1 A | FR2.2, FR2.3, FR8.2, NFR1, NFR3, NFR6 |
| RE-Q2 B | FR4.2, FR4.3 |
| RE-GA | FR1.4, FR2.4, FR2.5, FR3.2, FR3.3, FR4.5, FR5.2 |
| RE-TS | FR7.3, FR8.2 |
| R-S1..R-S8 | NFR3, NFR7, FR4.6, FR5.3, critérios 1 e 7 |
| RQ-Q1 A | FR1.4, FR6.1, FR6.4, FR6.5, critério 5, P2 |
| G-2.3 | FR1.4, FR6.1, P2 |
| D-2.6 | FR3.2, R-S4, P3, RA1 |
| A1 (CT18) | FR1.6, FR1.7, FR1.8, FR8.4, FR8.5, NFR10, NFR11, A1-S1..A1-S5 |
| NFR9 | FR1.8 |
| NFR4 | FR6.5 |

## Registro de alterações
- 2026-10-18 ~17:22 (UTC-3): portão G-2.3 — "última release" passa a ser só release publicada (sem pré-release e rascunho) em FR1.4, FR6.1 e P2; IDs mantidos.
- 2026-10-18 ~18:31 (UTC-3): decisão D-2.6 do Emerson, via Maestro: "As skills devem ir para .agents/skills essa pasta é padrão para todos os agentes. Não precisa duplicar em várias pastas." e "Aceito o risco no Claude Code e mantenho .agents/skills." FR3.2, critério 2, R-S4 e P3 ajustados; RA1 criado; FR3.3 sem mudança (pasta única é coerente com "sem duplicata"); IDs mantidos.
- 2026-10-18 ~19:33 (UTC-3): Adendo A1 (2.8 rodada 1). Emerson, via Maestro: "Adicione um prompt que orie te um modelo de IA a como instalar passo a passo o pacote sem depender de um arquivo .sh" e "Deve haver as duas opções a principal sendo o arquivo .sh" Novos: FR1.6, FR1.7, FR1.8, FR8.4, FR8.5, NFR10, NFR11, A1-S1 a A1-S5; notas sobre NFR1, NFR2, FR6, R-S7 e RA1 sem alterar o texto original.
- 2026-10-18 ~20:24 (UTC-3): Adendo A1 — Emerson confirmou A1-S1 a A1-S5 ("Confirmo as suposições A1-S1 a A1-S5."). Só marcação de status; textos inalterados.
