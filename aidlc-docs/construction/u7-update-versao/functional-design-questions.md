# U7 — Perguntas do desenho funcional

Unit: u7-update-versao | Estágio: 3.1 (desenho funcional) | Data: 2026-10-22 (UTC-3)
Quem responde: Emerson. Preencha `[Answer]:` com a letra (ou `X` e o texto). Q1 respondida com **A** em 2026-10-22 22:17 (UTC-3), Emerson via Maestro. A U7 T1 pode ser despachada.

## Q1 — [Product] Como mostrar skills do bob que estão só em parte no projeto?
**Contexto.** O CT8 e o CT11 dão 3 textos: `<v> (.agents/skills)`, `not installed` e `mixed (<v1>, <v2>)`. Não dizem o que mostrar quando algumas skills do bob têm `.bob-version` e outras não. Exemplos: o dev apagou uma pasta, ou uma skill nova do manifesto ainda não foi instalada no projeto. O `bob update` usa o mesmo estado para decidir se roda o `bob setup`. Nas 3 opções abaixo, um projeto incompleto nunca é "atual", então o `bob update` sempre o completa. A escolha muda só o texto que o dev lê no `bob doctor` e no `bob --version`.

- **A)** Mostrar a falta: `mixed (0.1.0, not installed)` / `misturadas (0.1.0, não instaladas)`. Com 2 versões e uma falta: `mixed (0.1.0, 0.2.0, not installed)`.
- **B)** Mostrar só as versões achadas: uma versão e uma falta viram `mixed (0.1.0)`; com 2 versões, `mixed (0.1.0, 0.2.0)`.
- **C)** Ignorar as que faltam: uma versão e uma falta viram `0.1.0 (.agents/skills)`, como se estivesse completo.
- **D)** Tratar qualquer falta como `not installed`.
- **E)** Outra regra de texto, sem mudar os 3 textos do CT8.
- **X)** Outra (descreva).

**Recomendação: A.**
- É o único texto que diz ao dev o que de fato está no disco: há uma versão e há falta.
- B esconde a falta atrás de "mixed" com uma versão só, o que confunde.
- C mente: diz completo quando não está.
- D esconde a versão que existe.
- A é compatível com o CT8: acrescenta uma variação de `mixed` e não muda as 3 existentes.

[Answer]: A

## Resumo das decisões
| # | Pergunta | Resposta | Efeito |
|---|---|---|---|
| Q1 | Skills em parte ausentes | **A** (2026-10-22 22:17 UTC-3, Emerson via Maestro) | ET U7 T1 v1 como está |
