# 3.5 Code Generation U4 (T2): perguntas
Contexto: o passo 0 da T2 (PR #196, rascunho, commit vazio d90c24d) confirmou o risco R1 do plano (ADR 0015). Num projeto git sem código, o `bob.yaml` gerado pela T1 tem `include: ["."]`. Com ele, `bob check --base HEAD --gates crap` sai 4, com stdout e stderr vazios, e o `.bob/report.md` diz "⏭️ crap: not run (coverage.py: No data to report.)". A T2 está parada até esta decisão.

## Q1. [Product owner] Num projeto sem código medível, o que o `bob check` deve fazer no gate crap?
A. Tratar como "nada a medir": o gate fica ⏭️ com o motivo "no code to measure" e o `bob check` sai 0. Uma ET nova corrige isso no bob antes da T2. CT7 e T1 não mudam, e o e2e da T2 continua esperando EXIT ≠ 4.
B. Manter a saída 4. O `bob setup` passa a avisar que o `bob check` sai 4 até o projeto ter código, e o e2e da T2 passa a esperar 4 no caso sem código.
C. Num projeto sem código, o `init_config` grava um `bob.yaml` que não roda o crap. Isso muda a T1 já mergeada e o contrato CT7.
X. Outra (especifique)
Recomendação: A. O 4 significa erro de ferramenta, e um projeto recém-criado não tem erro, só não tem nada a medir. Com a A, as US3.1/US3.2 funcionam no primeiro uso sem mexer no que já foi aprovado.
[Answer]: Opção A: tratar como nada a medir (crap pulado, bob check sai 0), com uma ET nova antes da T2. (Emerson, 2026-10-20 21:18 UTC-3)

## Resumo das decisões
- Q1 = A (Emerson, 2026-10-20 21:18 UTC-3): projeto sem código medível é "nada a medir"; o crap fica ⏭️ com motivo próprio e não conta como erro de ferramenta, e o `bob check` sai 0 se nenhum outro gate falhar. ET nova `T1b` antes da T2; CT7 e a T1 não mudam; o e2e da T2 segue esperando EXIT ≠ 4.
