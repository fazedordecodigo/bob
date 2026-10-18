# 2.3 Requirements — perguntas
Contexto: o intent pede instalar direto do GitHub (Q2 C) e atualizar para uma "versão nova" (Q5 B, critério 5). O repo não tem tags nem releases, e a versão é fixa em 0.1.0 (gap-analysis.md, critério 5).
Hoje a `main` sai com `bob doctor` = 4 (vitest, technology-stack.md, divergência 1). Sem definir qual versão o comando instala, não dá para escrever FR1.4, FR6.1 e o critério 5. Modo de coleta do projeto: chat (o Maestro apresenta com recomendações).

## Q1. [Product owner] Qual versão do bob o comando instala e para qual versão ele atualiza?
A. A última release marcada no GitHub (tag). Você cria as releases; a primeira seria a v0.1.0
B. O estado atual da branch `main`, sempre
C. A última release por padrão, e o dev pode pedir a `main` ou uma versão específica
X. Outra (especifique)
Recomendação: A — dá uma versão estável e "versão nova" fica mensurável; a `main` quebra (hoje o doctor sai 4). Criar tag e release continua exigindo o seu OK.
[Answer]: A — Emerson, via Maestro, 2026-10-18 17:19 (UTC-3): "Q1 A e confirmo as suposições R-S1 a R-S8."

## Suposições confirmadas
- R-S1 a R-S8 de `requirements.md`: confirmadas pelo Emerson, via Maestro, 2026-10-18 17:19 (UTC-3): "Q1 A e confirmo as suposições R-S1 a R-S8."

## Checagem de ambiguidade
- Respostas vagas: nenhuma. Q1 escolhe uma letra.
- Contradições entre respostas: nenhuma. Q1 A (release marcada) não conflita com R-S1 a R-S8.
- Conflito com estágios anteriores: nenhum.
  - Q1 A é coerente com I-Q2 C: a release fica no GitHub, sem PyPI.
  - Q1 A dá sentido a "versão nova" do critério 5 do intent.
  - Criar tag e release exige OK do Emerson (issue #10). Vira pré-condição em `requirements.md`, não pergunta.
- Lacunas: sem bloqueio.
  - Sem release publicada, o comando não tem o que instalar. Tratado como pré-condição (release v0.1.0).
  - Sem release mais nova, atualizar não muda nada. Tratado em FR6.5.

## Resumo das decisões
- Q1: A — o comando instala a última release marcada no GitHub; atualizar leva à release mais nova; a versão instalada fica visível. A primeira release (v0.1.0) depende de OK do Emerson.
- R-S1 a R-S8: confirmadas.
Confirmação do resumo: o Emerson respondeu Q1 e confirmou as suposições na mesma mensagem.
