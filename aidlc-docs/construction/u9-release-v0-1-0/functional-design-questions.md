# U9 — Perguntas do Functional Design

Responda em `[Answer]:` com a letra. As ETs v1 já assumem a recomendação.

## Q1. Quais ADRs entram em `docs/adr/` nesta unit?

O pronto 4 da U9 pede 0008–0020. Desde então, 0021–0029 foram aceitas (U6–U8).

A. Só 0008–0020, como está no pronto 4.
B. 0008–0029, tudo o que já foi aceito.
C. 0008–0020 agora; 0021–0029 numa unit depois.
X. Outra (descreva)

Recomendação: **B**. As 22 já estão geradas. Deixar 9 de fora cria um índice público incompleto. O custo extra é nulo.
A ET v1 (T3) assume **B**.

[Answer]: B (aprovado pelo Emerson em 24/10/2026 12:41 UTC-3: "U9 Q1: B (publicar ADRs 0008 a 0029).")

## Q2. Quem dispara o `dry_run` (E0) depois do merge da T1?

O pronto 1 só fecha com um run real nas 4 plataformas. Disparar workflow é ação no GitHub.

A. Você dispara (`gh workflow run release.yml … -f dry_run=true`) e me manda o link do run.
B. Você autoriza por escrito um agente a disparar só o `dry_run` (sem publicar).
C. Fica para o dia da release, junto do E1.
X. Outra (descreva)

Recomendação: **A**. Mantém a regra "nenhum agente publica nem dispara". O `dry_run` não cria tag, mas falhas em macOS/arm aparecem antes do dia da release.
As ETs v1 assumem **A** (o E0 está no `v0.1.0.md` como passo do Emerson).

[Answer]: A (aprovado pelo Emerson em 24/10/2026 12:41 UTC-3: "U9 Q2: A (eu disparo ou autorizo o dry_run depois dos merges).")

## Checagem de ambiguidade

- Q1 e Q2 têm uma escolha cada. Sem "talvez". Se a resposta for X, volto com nova pergunta.

## Suposições (não são perguntas)

- `publish-plugins.yml` fica como está. Ele só valida.
- O CHANGELOG segue em `## Unreleased`. As notas da release são o release-check.
- GitHub Pages fica fora da U9.
- ADR 0030 (`VERIFY_DIST`) entra na Plan Approval. É adição compatível ao CT15.

## Resumo das decisões

| Q | Recomendação | Assumido nas ETs v1 |
|---|---|---|
| Q1 | B (0008–0029) | sim (T3) |
| Q2 | A (Emerson dispara o E0) | sim (T2, `v0.1.0.md`) |
