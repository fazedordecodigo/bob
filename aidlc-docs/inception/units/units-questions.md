# 2.7 Units — perguntas
Contexto: a verificação manual por release (5 agentes, evidência em `docs/release-checks/vX.Y.Z.md`) usa contas do Emerson (Devin web, Copilot, Claude Code, Cursor) e uma instalação real. O U9 termina em "pronto para o Emerson disparar"; falta saber em que momento da v0.1.0 essa verificação acontece. Modo de coleta: chat.

## Q1. [Product owner] Quando é feita a verificação manual nos 5 agentes da v0.1.0?
A. O Emerson dispara o workflow com `prerelease: true`; instala com `BOB_VERSION=v0.1.0` (a pré-release não vira "última release", US7.2), verifica os 5 agentes, registra a evidência e só então marca a release como publicada
B. O Emerson dispara já como release publicada; a verificação manual vem depois, e um problema vira v0.1.1
C. Antes do disparo, numa instalação feita pelo espelho local (`BOB_RELEASES_URL`), sem release no GitHub
X. Outra (especifique)
Recomendação: A — prova a release real (assets e URLs do GitHub) antes de qualquer Dev recebê-la, usa o próprio fluxo de pré-release do US7.2 e não exige espelho na máquina do Emerson.
[Answer]: A — "Q1 A." (Emerson, via Maestro, recebida em 18/10/2026 18:43 UTC-3)

## Checagem de ambiguidade
- Resposta vaga: não. Uma opção, sem condição.
- Contradição: não. Só há uma pergunta.
- Conflito com estágios anteriores: não. Usa o fluxo de pré-release do US7.2 e FR1.4 (pré-release não conta como última release). Cumpre o 2.6: a verificação manual acontece antes de a release ficar pronta para os Devs (`verification-command.md`, "Verificação manual por release"). Mantém P2: disparo e publicação são do Emerson.
- Lacunas: como promover e o que fazer se a verificação falhar. São decisões técnicas, sem pergunta nova. Ficam no U9 (`unit-of-work.md`).
- Resultado: arquivo coerente. Nenhuma pergunta de acompanhamento.

## Resumo das decisões
- Q1: A — v0.1.0 sai como pré-release; o Emerson instala com `BOB_VERSION=v0.1.0`, verifica os 5 agentes, registra a evidência em `docs/release-checks/v0.1.0.md` e só então promove para publicada.
