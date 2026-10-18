# 2.1 Reverse Engineering — perguntas
Contexto: o código mostra duas coisas que o intent não cobre. O `bob doctor` exige gitleaks, fora dos pré-requisitos da S1. E o `bob.yaml` padrão da S4 quebra o critério 3 em projeto sem `src/`.
Cada pergunta muda o escopo do comando de instalação. Modo de coleta do projeto: chat (o Maestro apresenta com recomendações).

## Q1. [Product owner] O gitleaks 8.30.1 é pré-requisito do dev ou o comando de instalação o instala?
Evidência: o `bob doctor` sai `4` sem gitleaks 8.30.1 (`src/bob_quality/doctor.py:91-97`). Os docs de requisitos não o citam (`docs/instalacao.md:7-11`). A S1 só fala de Python e Node. O critério 1 pede `bob doctor` = 0.
A. O comando de instalação baixa e confere o gitleaks (Linux e macOS), dentro dos 5 minutos
B. O gitleaks vira pré-requisito, como Python e Node: fica fora dos 5 minutos e entra nos docs
X. Outra (especifique)
Recomendação: A — o gitleaks não costuma estar na máquina do dev; deixá-lo manual quebra o "um comando" para a comunidade (Q1 C).
[Answer]: A — Emerson, via Maestro (recebido em 2026-10-18 17:12 UTC-3): "Aceito as recomendações: Q1 A, Q2 B."

## Q2. [Product owner] Num projeto sem pasta `src/`, que `paths.include` o `bob.yaml` criado usa?
Evidência: o padrão do README é `paths.include: [src]` (`README.pt-BR.md:187`). Um `include` que não existe faz `bob check` sair `4` por configuração (`src/bob_quality/config.py:428-434`). Isso fere o critério 3. A S4 manda usar os padrões do README.
A. Padrões do README sem mudança, mesmo sem `src/` (o critério 3 falha nesses projetos)
B. Padrões do README, com `paths.include` trocado pelas pastas de código que existem no projeto
C. O comando pergunta ao dev quais pastas incluir
X. Outra (especifique)
Recomendação: B — mantém a S4 em todo o resto e garante o critério 3 sem interação.
[Answer]: B — Emerson, via Maestro (recebido em 2026-10-18 17:12 UTC-3): "Aceito as recomendações: Q1 A, Q2 B."

## Checagem de ambiguidade
- Respostas vagas: nenhuma. As duas escolhem uma letra.
- Contradições entre respostas: nenhuma. Q1 trata do gitleaks; Q2 do `bob.yaml`.
- Conflito com estágios anteriores: nenhum bloqueante.
  - Q1 A é coerente com a S1: o gitleaks não vira pré-requisito; entra no comando e nos 5 minutos do critério 1.
  - Q2 B refina a S4: os padrões do README valem em tudo, menos `paths.include`. O texto da S4 em `ideation/intent/intent.md` não foi alterado (não é artefato deste estágio).
- Lacunas: sem bloqueio. Os pontos abaixo são técnicos e vão para o 2.6, não viram pergunta:
  - Q1: plataformas além de Linux x64 e macOS (ex.: arm64), URL e sha256 de cada uma, pasta de destino do binário.
  - Q2: regra de derivação das pastas de código e o que fazer quando o projeto não tem nenhuma.

## Resumo das decisões
- Q1: A — o comando de instalação baixa e confere o gitleaks 8.30.1 (Linux e macOS), dentro da meta de 5 minutos.
- Q2: B — o `bob.yaml` gerado usa os padrões do README, com `paths.include` derivado das pastas de código que existem no projeto.
Confirmação do resumo: o Emerson aceitou as duas recomendações na mesma resposta.
