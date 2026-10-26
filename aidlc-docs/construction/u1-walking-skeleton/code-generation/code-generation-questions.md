# U1 — Perguntas do plano de geração de código

Só entram aqui decisões de produto ou de política do Emerson. As decisões técnicas estão no plano (D1–D31). Responda na linha `[Answer]:` de cada pergunta.

## Q1 — Rodar o harness no CI em todo PR?
Contexto: o `scripts/verify-install.sh` (T5) instala o bob de verdade num `HOME` limpo, com PyPI e npm. Meta U1-N12: ≤ 15 min por execução. Hoje o CI tem 5 checks (`pytest` 3.10 e 3.12, `package / dist`, `bob / check`, `bob / cold`). O harness é o DoD 3 da U1 e de todas as units seguintes (cada uma acrescenta passos).

- A. Sim: workflow novo `.github/workflows/verify-install.yml` (T6), em todo PR e no push da `main`, Linux x64, sem segredos. Você decide depois se ele vira check obrigatório na proteção da `main`.
- B. Não: o harness roda só à mão (o agente cola a saída no PR, e o Arquiteto confere na `main` antes de cada checkpoint). Sem T6.
- X. Outra (descreva).

Recomendação: **A**. Cada PR das units U3–U9 mexe no caminho de instalação; sem o harness no CI, uma regressão só aparece no checkpoint. Custo: mais um job de ~10–15 min por PR, sem segredos e com permissão só de leitura.

[Answer]: A — Emerson, via Maestro, 2026-10-19 02:46 UTC-3: "Q1 A, Q2 A."

## Q2 — Entrega da U1 em 5 PRs?
Contexto: a U1 tem 5 tarefas (T1 wheel, T2 skills, T3 `bob setup`, T4 `install.sh`, T5 harness; T6 se Q1 = A). Cada uma tem ≤ 8 arquivos e deixa a suíte verde sozinha.

- A. Um PR por tarefa, em sequência; você faz o merge de cada um; a ET seguinte só é despachada depois do merge. Checkpoint da U1 no fim, com o harness verde na `main`.
- B. Um PR só com as 5 tarefas (≈ 25 arquivos), um merge, um checkpoint.
- X. Outra (descreva).

Recomendação: **A**. PRs pequenos são revisáveis e cada um prova algo sozinho (wheel, skills, `bob setup`, `install.sh`, harness). Custo: 5 merges seus em vez de 1.

[Answer]: A — Emerson, via Maestro, 2026-10-19 02:46 UTC-3: "Q1 A, Q2 A." Com Q1 = A, a entrega fica em 6 PRs sequenciais (T1–T6), um por tarefa.

## Resumo
| Q | Tema | Recomendação | Resposta |
|---|---|---|---|
| Q1 | Harness no CI em todo PR | A | |
| Q2 | 5 PRs sequenciais | A | |
