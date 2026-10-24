# Comando único: `install.sh` + `bob setup`

Status: aceita pelo Emerson em 18/10/2026, na aprovação do desenho da aplicação. Publicada em `docs/adr/` na U9.

## Contexto

Não há comando único (2.1). A ADR 0004 diz que o instalador de skills não é subcomando de `bob` (`docs/adr/0004-empacotamento-quatro-agentes.md:23`).

## Decisão

- `install.sh` cuida só do que precede o pacote: SO, arquitetura, Python, Node, versão, wheel, venv, launcher.
- `bob setup` (subcomando novo) cuida do projeto, na ordem fixa de C02.
- `install.sh` termina com `exec bob setup`. O dev vê um comando só.
- `python -m bob_quality.install_skills` continua existindo. `bob setup` o chama como biblioteca.
- Supera a ADR 0004 só no ponto "não é subcomando": a instalação do projeto passa a ser subcomando.

## Alternativas

Tudo em shell (difícil testar, duplica lógica do doctor); tudo em Python sem bootstrap (sem como conferir Node e criar venv antes).

## Consequências

`bob setup` também serve para configurar outro projeto já com o bob instalado.
