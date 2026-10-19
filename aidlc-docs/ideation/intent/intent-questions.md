# 1.1 Intent — perguntas
Contexto: hoje o bob só se instala a partir de um clone (venv + pip -e + npm ci) e as skills chegam por plugin nativo ou por `install_skills.py --source <clone>`; nada está no PyPI.
O pedido é instalar e configurar o bob nos projetos sem depender de plugin nativo. Estas perguntas definem para quem, até onde vai "configurado" e como medir sucesso.
Modo de coleta do projeto: chat (o Maestro apresenta com recomendações). Reutilizar nos próximos estágios.

## Q1. [Product owner] Quem é o usuário-alvo desta forma de instalação?
A. Só o Emerson, nos projetos dele
B. Times com quem o Emerson trabalha (clientes, colegas)
C. Qualquer dev da comunidade que encontre o repositório público
X. Outra (especifique)
Recomendação: C — o repo é público, MIT, tem site e publicação planejada; o Emerson continua sendo o primeiro usuário.
[Answer]: C — Emerson, 2026-10-18 16:49 (UTC-3), via chat com o Maestro: "Aceito todas as recomendações: Q1 C, Q2 C, Q3 C, Q4 A, Q5 B, Q6 A."

## Q2. [Product owner] De onde o usuário obtém o bob nesta entrega?
A. Direto do repositório GitHub, sem publicar nada
B. Do PyPI, com a publicação do `bob-quality` dentro do escopo
C. Do repositório GitHub agora; PyPI fica para uma entrega seguinte
X. Outra (especifique)
Recomendação: C — tira a dependência do clone já, e a publicação exige release com OK seu, que pode vir depois.
[Answer]: C — Emerson, 2026-10-18 16:49 (UTC-3), via chat com o Maestro: "Aceito todas as recomendações: Q1 C, Q2 C, Q3 C, Q4 A, Q5 B, Q6 A."

## Q3. [Product owner] O que conta como "bob configurado" num projeto?
A. Comando `bob` disponível e `bob.yaml` criado
B. A + skills do bob dentro do projeto, lidas pelos agentes
C. B + hook pre-push ativo
D. C + workflow de CI com a GitHub Action do bob
X. Outra (especifique)
Recomendação: C — cobre tudo o que hoje é passo manual na máquina do dev; a Action já tem caminho próprio de instalação.
[Answer]: C — Emerson, 2026-10-18 16:49 (UTC-3), via chat com o Maestro: "Aceito todas as recomendações: Q1 C, Q2 C, Q3 C, Q4 A, Q5 B, Q6 A."

## Q4. [Product owner] Quais agentes precisam receber as skills sem plugin nativo?
A. Os quatro atuais: Cursor, Claude Code, GitHub Copilot e Devin
B. Os quatro atuais + Codex
C. Nenhum agente específico; basta o AGENTS.md e as skills na pasta padrão do projeto
X. Outra (especifique)
Recomendação: A — são os quatro do README e da ADR 0004; Codex só aparece nas issues de publicação (#145, #148).
[Answer]: A — Emerson, 2026-10-18 16:49 (UTC-3), via chat com o Maestro: "Aceito todas as recomendações: Q1 C, Q2 C, Q3 C, Q4 A, Q5 B, Q6 A."

## Q5. [Product owner] Quais etapas do ciclo de vida entram no escopo?
A. Só instalar e configurar
B. Instalar, configurar e atualizar para uma versão nova
C. Instalar, configurar, atualizar e desinstalar
X. Outra (especifique)
Recomendação: B — sem atualização o projeto fica preso a ferramentas pinadas antigas; desinstalar é raro e pode ser manual.
[Answer]: B — Emerson, 2026-10-18 16:49 (UTC-3), via chat com o Maestro: "Aceito todas as recomendações: Q1 C, Q2 C, Q3 C, Q4 A, Q5 B, Q6 A."

## Q6. [Product owner] Qual é o critério de sucesso principal?
A. Num projeto novo, um único comando e até 5 minutos até `bob doctor` sair com 0
B. Até 3 passos documentados e até 10 minutos até o primeiro `bob check` rodar
C. Um agente consegue instalar e configurar sozinho, sem intervenção humana, seguindo as instruções
X. Outra (especifique)
Recomendação: A — é mensurável, curto e usa o `bob doctor`, que já existe para dizer se está tudo certo.
[Answer]: A — Emerson, 2026-10-18 16:49 (UTC-3), via chat com o Maestro: "Aceito todas as recomendações: Q1 C, Q2 C, Q3 C, Q4 A, Q5 B, Q6 A."

## Checagem de ambiguidade
- Respostas vagas: nenhuma. Todas escolhem uma letra.
- Contradições entre respostas: nenhuma. Q1 C (comunidade) com Q2 C (GitHub, sem PyPI) é coerente: o repo é público.
- Conflito com estágios anteriores: nenhum. O plano em aidlc-state.md já prevê o usuário "dev que instala e configura o bob no projeto".
- Lacunas: sem bloqueio. Pontos com resposta padrão razoável viram suposições no intent.md (S1–S6; principais abaixo):
  - S1. Os pré-requisitos (Python e Node) já estão na máquina e ficam fora dos 5 minutos da Q6.
  - S2. Num projeto que já tem bob.yaml ou hook pre-push, a instalação não sobrescreve sem avisar.
  - S3. Atualizar (Q5) preserva bob.yaml e .bob/waivers.yaml do projeto.

## Resumo das decisões
- Q1: C — usuário-alvo é qualquer dev da comunidade; o Emerson é o primeiro usuário.
- Q2: C — obter direto do repositório GitHub agora; PyPI fica para a entrega seguinte.
- Q3: C — configurado = comando bob + bob.yaml + skills no projeto + hook pre-push ativo.
- Q4: A — skills para Cursor, Claude Code, GitHub Copilot e Devin, sem plugin nativo.
- Q5: B — escopo: instalar, configurar e atualizar.
- Q6: A — projeto novo, um comando, até 5 minutos até bob doctor sair com 0.
Confirmação do resumo: o Emerson aceitou todas as recomendações na mesma resposta.
