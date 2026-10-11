---
name: review-report
description: "Resumir `.bob/report.md` no corpo do PR. Use ao escrever ou atualizar um pull request depois de `bob check`, ou quando a skill `pr` precisar do relatório de review."
---

# review-report

Companheira da `pr` (`skills/vendor/mattpocock/engineering/pr/SKILL.md`). Mantenha o molde Summary / Evidence / Merge Danger. O relatório do bob entra em Evidence.

Fonte do formato: `docs/SPEC.md`. Rode `bob-check` antes, para existirem `.bob/report.md` e `.bob/report.json` (`schema_version: 1`).

## Quando

- Escrever o corpo do PR com `pr`
- Atualizar um PR depois de um novo `bob check`

## Passos

1. Confirmar `.bob/report.md`. Se faltar, `bob check --format both` ou `bob report  [--in .bob/] [--out .bob/report.md]`.
2. Ler o relatório na ordem da spec (abaixo).
3. Colocar os vereditos e **Onde focar o review** em Evidence (antes/depois: último `bob check` que falhou vs a corrida que passou).
4. Apontar o caminho `.bob/report.md` para a página completa. O corpo do PR fica o resumo de uma página.

Conclusão: o PR tem vereditos, a lista de foco e o caminho para `.bob/report.md`.

## Formato do relatório

1. Cabeçalho: commit, base, data, versões das ferramentas.
2. Veredito por gate: ✅ passou / ⚠️ aviso / ❌ falhou / ⏭️ não executado (com motivo).
3. **Onde focar o review**: arquivos alterados ordenados por risco (maior CRAP + sobreviventes + clones).
4. Top 5 funções de maior CRAP no diff (função, arquivo:linha, CC, cobertura, CRAP, delta).
5. Mutantes sobreviventes (sem waiver = falha) e tabela de waivers com justificativa.
6. Clones novos (pares, similaridade, linhas).
7. Violações e ciclos de dependência.
8. Rodapé: como reproduzir localmente (comando exato).

⏭️ permanece ⏭️, com o motivo.

## Evidence (na `pr`)

- **Before:** exit e linhas do `bob check` que falhou.
- **After:** exit `0` e os vereditos atuais.

Waivers aparecem no relatório e no resumo.

## Merge Danger

Gates ❌ ou sobreviventes sem waiver aumentam o blast radius. Porta de duas vias: reverter o PR. Liste ⚠️ de clones e cada waiver para o humano julgar.
