# U3 — Perguntas do plano de geração de código

Só entram aqui decisões de produto ou de política do Emerson. As decisões técnicas estão no plano (D1–D24). Responda na linha `[Answer]:` de cada pergunta.

## Q1 — I15: o `install.sh` pode repetir o `429` do GitHub? [Product owner]
Contexto: o CT14 diz que limite de taxa (`403`/`429`) não tem retry. O `CURL_OPTS` do `install.sh` (CT18, já na `main`) usa `--retry 2`, e o `curl` repete o `429` (não repete o `403`). Detalhe, prós e contras na seção "I15" do `code-generation-plan.md`. Nenhuma opção muda o código da U3 (`gitleaks.py` já segue o CT14).

- A. Manter `--retry 2`. O Maestro ajusta o texto do CT14: `403` sem retry; `429` com até 2 retries do `curl`, depois `4` e "tente de novo mais tarde". Sem código, sem PR.
- B. Seguir o CT14 no código: o `curl` da API passa a não ter `--retry`, com retry manual só em rede/`5xx`. Uma tarefa nova no `install.sh` e no CT18 (+1 PR).
- C. Pôr teto: `CURL_OPTS` ganha `--retry-max-time 30`; CT14 ajustado como em A. Uma tarefa de 1 linha, depois de conferir o comportamento do `curl` no macOS e no `ubuntu-latest`.
- X. Outra (descreva).

Recomendação: **A**. O limite que um dev sem token encontra é o `403`, e esse já não é repetido. O `429` é o limite secundário, que o GitHub manda esperar e tentar de novo. A mantém a fonte única do CT18 e a paridade da U8 sem custo. Custo de A: até 2 pedidos extras no `429`.

[Answer]: A — Emerson, via Maestro, 2026-10-19 23:10 UTC-3: "Q1 A, Q2 A." Mantém o `CURL_OPTS` com `--retry 2` (sem mudança de código) e ajusta o texto do CT14: no `install.sh`, `429` até 2 retries do `curl`, `403` nunca; no Python, `4xx` (inclusive `429`) sem retry. Texto aplicado no CT14 em 2026-10-19 23:1x UTC-3 (Registro do `contract-summary.md`). I15 resolvida.

## Q2 — `bob check --gates secrets` deve achar o gitleaks que o `bob setup` instala? [Arquiteto]
Contexto: depois da U3, quem instala pelo comando único tem o gitleaks só em `BOB_HOME/bin` (fora do `PATH`; `~/.local/bin` só tem o `bob`). O `bob doctor` passa a olhar `BOB_HOME/bin` (CT8), mas o gate `secrets` (`secrets_gate.py:125`) usa só `shutil.which("gitleaks")` e sai `4` com "missing tool: gitleaks". O gate `secrets` não está no padrão (`crap,dry,deps`); só roda quando pedido. A `unit-of-work.md` lista para a U3 só C02 e C08, não o gate. Sem a mudança, o FR2.1 ("ficam disponíveis todas as ferramentas que o doctor confere") fica pela metade para o `secrets`.

- A. Sim, na U3: T4 (3 arquivos: `secrets_gate.py` passa a usar `user_dirs.locate_binary("gitleaks")`, teste novo, CHANGELOG), depois da T3.
- B. Não na U3: registrar como pendência para uma unit futura (por exemplo, a U4 ou a U7) e seguir com T1–T3.
- X. Outra (descreva).

Recomendação: **A**. É a mesma regra do CT8/ADR 0019, uma linha de código e um teste. Sem ela, o primeiro `bob check --gates secrets` num projeto instalado pelo comando único falha com "missing tool", apesar de o `bob doctor` dizer `0`. Custo: +1 PR pequeno.

[Answer]: A — Emerson, via Maestro, 2026-10-19 23:10 UTC-3: "Q1 A, Q2 A." A T4 entra na U3 como tarefa normal, depois da T3 (4 PRs sequenciais, T1–T4). I16 resolvida.

## Resumo
| Q | Tema | Recomendação | Resposta |
|---|---|---|---|
| Q1 | I15: `429` com `--retry 2` | A | A (2026-10-19 23:10 UTC-3) |
| Q2 | Gate `secrets` acha `BOB_HOME/bin/gitleaks` (T4) | A | A (2026-10-19 23:10 UTC-3) |
