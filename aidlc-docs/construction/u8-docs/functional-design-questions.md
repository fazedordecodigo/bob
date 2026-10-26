# U8 — Perguntas do desenho funcional (3.1)

Arquivo de perguntas do estágio 3.1 da U8. Responda na linha `[Answer]:` de cada pergunta. Só a Q1 está aberta.

## Q1 — Instruções de plugin nos docs de usuário
[Product]

**Contexto.** Hoje `docs/getting-started/agents.md` (en e pt-BR) e a seção "Installing in the agents" / "Instalação nos agentes" dos 2 READMEs ensinam a instalar o bob como plugin:
- Claude Code e Copilot: `claude plugin install`, `copilot plugin install`;
- Cursor: `git clone`/`git archive` em `~/.cursor/plugins/local/bob`;
- e o `install_skills.py` a partir de um clone.

Com o comando único (FR1.2, FR1.3: sem clone, sem plugin), as skills vão para `.agents/skills` pelo `bob setup`. O plugin em paralelo faria o agente carregar as skills duas vezes (o próprio `agents.md` já avisa isso para o Devin). O CT17 exige que nada de clone ou plugin venha antes do comando único, mas não diz se essas instruções continuam depois.

Qual destino dar às instruções de plugin?

- A) Tirar dos docs de usuário: `agents.md` e as seções dos READMEs passam a descrever só a pasta única `.agents/skills`, o RA1 e `bob --version`/`bob update`. A publicação do plugin continua em `docs/publishing.md` (para quem mantém o bob).
- B) Manter depois do comando único, numa seção "Advanced: plugin from a clone (not needed)" / "Avançado: plugin a partir de um clone (não é preciso)", com um aviso de skills duplicadas.
- C) Manter só no `agents.md` (seção avançada como em B) e tirar dos READMEs.
- D) Manter tudo como está, só acrescentando o comando único no topo.
- E) Adiar: a T3 sai sem mexer em plugin (só acrescenta o comando único no topo, como D), e a decisão vira item do backlog.
- X) Outra (descreva).

**Recomendação: A.**
- É o que FR1.3 e FR3.2 pedem: sem plugin e uma pasta só.
- Evita skills duplicadas.
- Deixa os docs curtos.
- O `publishing.md` já cobre quem mantém o bob.

[Answer]: A

## Resumo das decisões
| # | Pergunta | Resposta | Efeito |
|---|---|---|---|
| Q1 | Instruções de plugin nos docs | **A** (2026-10-22 22:17 UTC-3, Emerson via Maestro) | Com **A**, a T3 vale como está escrita (textos D8 e "Installing in the agents" da ET). Com **B, C, D ou E**, eu escrevo a T3 v2 (textos do `agents.md` e das seções dos READMEs, `_NOT_BEFORE` e os testes `test_no_clone_or_plugin_before_the_one_liner` e `test_agents_doc_names_the_single_folder_and_ra1`). A T1, a T2 e a T4 não dependem da resposta. |
