# T1b — Emendas (E1–E3 aplicadas; E4 vai para a T1c)

Data: 2026-10-20 21:40 UTC-3. Origem: Q1 = A (Emerson, 2026-10-20 21:18 UTC-3) e a ET `T1b.md`.
Estado: aprovadas pelo Emerson em 2026-10-20 21:42 UTC-3 ("Aprovo a T1b e as emendas E1 a E3, com a T1c separada para a E4. Pode despachar a T1b."). E1–E3 **aplicadas** em 2026-10-20 21:50 UTC-3, com o texto exato abaixo e uma linha de registro da aprovação em cada uma. E4 **vai para a T1c** (`T1c.md`).

## Por que precisa de emenda
- O CT7 diz que, com o `bob.yaml` gerado, o `bob check` não muda em nada: "**`bob check`: o que muda.** Nada na CLI, nos gates nem nos códigos." (`inception/contracts/contract-summary.md:320`). A T1b muda dois gates (`crap` e `coverage`) quando não há código a medir.
- A ADR 0015 deixou como **Não verificado** o `include: ["."]` em execução nos gates (`inception/application-design/decisions.md:220`). O passo 0 da T2 mediu: `crap` sai `4` (PR #196). A Q1 decidiu o tratamento.
- Os códigos de saída (CT1, `docs/adr/0003-exit-codes.md`) não mudam de nome nem de número. Muda um caso: "nada a medir" deixa de ser `4` e passa a contribuir `0`, como já acontece com gate desconhecido e com `dry` sem ferramenta.

## E1 — `inception/application-design/decisions.md`, ADR 0015, "Consequências" (linha 220) — **APLICADA** (linhas 220-221; registro na 221)
Hoje:
> - `include: ["."]` com o resto do padrão: aceito por `load_config` pela leitura do código; **Não verificado** em execução nos gates. O 3.6 testa `bob check` nesse caso.

Proposto:
> - `include: ["."]` com o resto do padrão: aceito por `load_config`. Medido em 2026-10-20 (passo 0 da T2, PR #196, `main` @ `0d85510`): sem código, `crap` e `coverage` saíam `4` (`coverage.py: No data to report.`); `dry` e `deps` saem `0`. Decisão do Emerson (Q1 = A, 2026-10-20 21:18 UTC-3): sem código a medir, `crap` e `coverage` ficam ⏭️ `not_run` com o motivo "no code to measure" / "nenhum código a medir" e contribuem `0` (T1b). "Sem código" = `config.detect_languages(cwd, include, exclude)` vazio (mesmos sufixos e exclusão desta ADR, sem seguir symlink). Com código, erro de coverage segue `4`.

## E2 — `inception/contracts/contract-summary.md`, CT7 (linha 320) — **APLICADA** (texto na linha 322, registro na 324; o CT7 desceu 2 linhas por causa da E3)
Hoje:
> **`bob check`: o que muda.** Nada na CLI, nos gates nem nos códigos. Só passa a achar um `bob.yaml` que não sai `4` por configuração (FR4.4).

Proposto:
> **`bob check`: o que muda.** Nada na CLI nem nos códigos. Só passa a achar um `bob.yaml` que não sai `4` por configuração (FR4.4). Nos gates, uma mudança (T1b, Q1 = A): quando `detect_languages(cwd, paths.include, paths.exclude)` é vazio, `crap` e `coverage` não rodam ferramenta, ficam `not_run` com o motivo `check.no_code` (en "no code to measure", pt-BR "nenhum código a medir") e contribuem `0`. Com código, tudo segue igual.

Versão do CT7: o `contract-summary.md` é do Arquiteto. A E2 muda um código de saída (sem código, `crap` e `coverage` passam de `4` a `0`); pela regra de versionamento do arquivo, o CT7 subiu para v2 em 22/10/2026, com nota no "Registro".

## E3 — `inception/contracts/contract-summary.md`, CT1 (linhas 40-44), opcional — **APLICADA** (linhas 53-54, último item do bloco "Novo." do CT1; registro na 54)
Acréscimo proposto (uma linha):
> - Gate `not_run` contribui `0` quando não há o que medir: gate desconhecido (`check.gate_not_implemented`), `dry` sem ferramenta e, desde a T1b, `crap` e `coverage` sem código no `paths.include` (`check.no_code`). `not_run` por ferramenta ausente ou quebrada num projeto com código segue `4`.

## E4 — Docs do repo — **vai para a T1c** (`T1c.md`, depois da T3; decisão do Emerson às 21:42). O texto final da T1c substitui as frases abaixo.
- `docs/exit-codes.md`, seção "Exit 0", depois de "An unknown gate name is `not_run` and contributes `0`.": "With no code to measure (no `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` or `.cjs` file under `paths.include`, outside `paths.exclude`), `crap` and `coverage` are `not_run` with the reason \"no code to measure\" and contribute `0`. They run no tool."
- `website/i18n/pt-BR/docusaurus-plugin-content-docs/current/exit-codes.md`: a mesma frase em pt-BR ("Sem código a medir (…), `crap` e `coverage` ficam `not_run` com o motivo \"nenhum código a medir\" e contribuem `0`. Não rodam ferramenta.").
- `docs/adr/0003-exit-codes.md`, "Decisão", depois de "Um nome de gate desconhecido grava `not_run` e contribui 0. O processo pode sair 0.": "Sem código a medir no `paths.include`, `crap` e `coverage` gravam `not_run` (\"no code to measure\") e contribuem 0 (Q1 da U4, 2026-10-20)."
Não verifiquei se há teste de sincronia entre `docs/` e `website/`; a tarefa de docs deve conferir antes.

## O que não muda
- `exit_codes.py`, os 5 códigos e seus nomes; `docs/exit-codes.md:7-13` (tabela).
- CT7 em si (texto do `bob.yaml`, regra de `include`, estados); T1 e `init_config.py`.
- T2: regras, testes e contagens (só a base e o fluxo de retomada, na v3).
