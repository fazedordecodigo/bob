# Skills de projeto só em `.agents/skills` (P3)

Status: aceita pelo Emerson em 18/10/2026, na aprovação do desenho da aplicação. Publicada em `docs/adr/` na U9.

## Origem

Pedido de mudança do Emerson no portão do 2.6, rodada 1, literal via Maestro (18/10/2026 18:25 UTC-3): "As skills devem ir para .agents/skills essa pasta é padrão para todos os agentes. Não precisa duplicar em várias pastas." Substitui a versão anterior desta ADR (`.claude/skills`).

## Contexto

Fontes oficiais, todas reconferidas em 18/10/2026 (UTC-3):

| Agente | Pastas de projeto que a doc cita | Confirma `.agents/skills`? | Fonte oficial |
|---|---|---|---|
| Cursor | `.agents/skills/`, `.cursor/skills/`; e, "for compatibility", `.claude/skills/` e `.codex/skills/` | **Sim** | https://cursor.com/docs/skills |
| Claude Code | `.claude/skills/<skill>/SKILL.md` (projeto), `~/.claude/skills/` (pessoal), `<subdir>/.claude/skills/` | **Não**. A página não cita `.agents` em nenhum ponto (busca por `.agents` e `agents/skills`: 0 ocorrências) | https://code.claude.com/docs/en/skills |
| GitHub Copilot | `.github/skills`, `.claude/skills` ou `.agents/skills` | **Sim** | https://docs.github.com/en/copilot/concepts/agents/about-agent-skills ; https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills |
| Devin CLI | `.agents/skills/<name>/SKILL.md`, `.devin/skills`, `.windsurf/skills` (projeto) | **Sim** | https://docs.devin.ai/cli/extensibility/skills/overview |
| Devin web | `.agents/skills` (recomendada), `.devin`, `.github`, `.claude`, `.cognition`, `.windsurf`; "All six paths are scanned in every repo" | **Sim** | https://docs.devin.ai/product-guides/skills |

- `.agents/skills` é confirmada por 4 dos 5 alvos. O Claude Code é a exceção.
- Gravar em mais de uma pasta faz Cursor, Copilot e Devin acharem cada skill duas vezes (FR3.3). O Emerson pediu pasta única.

## Decisão

- O `bob setup` grava as skills só em `.agents/skills/<nome>/`.
- Usa o alvo `agents` que já existe no instalador (`src/bob_quality/install_skills.py:17-21`). Nenhum alvo novo. Os alvos `copilot` e `devin` ficam para uso manual (`devin` aponta para a mesma pasta).
- Sem `.claude/skills`, sem `.devin/skills`, sem symlink e sem cópia extra. Não há plano B de duplicação.
- `bob setup` avisa quando acha cópia do bob em `.claude/skills` ou `.github/skills` (duplicata provável, ex.: instalação antiga ou manual). Não apaga (FR3.4).
- Se um risco abaixo se confirmar, a saída é levar ao Emerson. A pasta não muda sem nova decisão dele.

## Alternativas

- Só `.claude/skills` (versão anterior desta ADR): citada por 4 dos 5 docs (falta o Devin CLI), e o Cursor a lê só "for compatibility". Cobriria o Claude Code pela doc. Rejeitada pelo Emerson.
- `.agents/skills` + `.claude/skills` (cópia ou symlink): cobre o Claude Code pela doc, mas duplica em Cursor, Copilot e Devin web. Rejeitada pelo Emerson ("Não precisa duplicar").
- `.agents/skills` + `.devin/skills`: duplica no Devin web. Rejeitada.

## Consequências e riscos

- A fala do Emerson diz que `.agents/skills` "é padrão para todos os agentes". As docs confirmam para 4 dos 5; para o Claude Code, não (Risco 1).
- Fica alinhada à ADR 0004 do repo (alvos `agents`/`devin`, "Claude Code não tem alvo").
- **Risco 1 (Claude Code), alto — ACEITO pelo Emerson** em 18/10/2026 18:31 UTC-3, literal via Maestro: "Aceito o risco no Claude Code e mantenho .agents/skills." A doc oficial do Claude Code só cita `.claude/skills`. Pela doc, o Claude Code **não** acharia as skills do bob em `.agents/skills`. Situação real: **Não verificado**. Em tensão com FR3.2, US2.1 crit. 1 e o critério 2 do intent (ver `traceability.md`, "Impacto da ADR 0009"). A pasta continua `.agents/skills`; a verificação manual por release continua valendo para o Claude Code.
- **Risco 2 (Cursor, Copilot, Devin CLI, Devin web), baixo.** As docs confirmam `.agents/skills`. Falta ver na prática.
- Verificação: manual a cada release, nos 5 agentes (`verification-command.md`, "Verificação manual por release"). No projeto do passo 2, listar as skills em cada agente. Evidência (data UTC-3, versão do bob, versão do agente, saída do terminal ou captura de tela) em `docs/release-checks/vX.Y.Z.md`, no PR da release.
- Gatilho: algum dos 5 agentes não lista uma ou mais das três skills (`bob-check`, `harden`, `review-report`), ou lista em duplicata.
- Resposta ao gatilho: registrar em `docs/release-checks/vX.Y.Z.md` e levar ao Emerson, com a evidência. Sem mudar a pasta e sem duplicar por conta própria.
- `bob --version` e `bob doctor` mostram a versão das skills lida de `.agents/skills/<skill>/.bob-version`.
