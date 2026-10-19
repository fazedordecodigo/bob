# Intent — bob: instalação e configuração sem plugin nativo

Pedido literal (Emerson, 2026-10-18 16:41 UTC-3): "Preciso disponibilizar uma forma de instalação e configuração da ferramenta para uso nos projetos, sem depender de ser um plugin nativo."
Profundidade: Minimal. Decisões: ver intent-questions.md (Q1–Q6, respondidas em 2026-10-18 16:49 UTC-3).

## Problema
- Hoje o bob só se instala a partir de um clone do repositório.
- São vários passos manuais: ambiente Python, dependências Python, ferramentas npm, `bob doctor`.
- As skills chegam ao agente por plugin nativo ou por um instalador que exige o clone (`--source`).
- O `bob.yaml` e o hook pre-push são criados à mão em cada projeto.
- Nada está publicado no PyPI nem em marketplace.
- Resultado: adotar o bob num projeto é lento, depende de plugin e é fácil errar.

## Usuário
- Qualquer dev da comunidade que encontre o repositório público (Q1 C).
- O Emerson é o primeiro usuário, nos projetos dele.
- O dev usa um ou mais destes agentes: Cursor, Claude Code, GitHub Copilot, Devin (Q4 A).

## Resultado esperado
- O dev obtém o bob direto do repositório GitHub, sem clonar à mão e sem plugin nativo (Q2 C).
- Com um comando, o projeto fica "configurado" (Q3 C):
  - comando `bob` disponível;
  - `bob.yaml` criado no projeto;
  - skills do bob dentro do projeto, lidas pelos quatro agentes;
  - hook pre-push ativo.
- O dev atualiza o bob para uma versão nova pelo mesmo caminho (Q5 B).
- `bob doctor` confirma que está tudo certo.

## Fora de escopo
- Publicar o `bob-quality` no PyPI nesta entrega (fica para a seguinte, Q2 C).
- Desinstalar (Q5 B).
- Codex (Q4 A).
- Publicação como plugin nos marketplaces (issues #145, #147, #148, #149).
- GitHub Action e workflow de CI no projeto (Q3 C; a Action já tem instalação própria).
- Mudar gates, limiares ou o formato do `bob.yaml`.

## Suposições (a confirmar)
- [SUPOSIÇÃO S1] Os pré-requisitos (Python e Node nas faixas que o `bob doctor` aceita) já estão na máquina. O tempo deles fica fora dos 5 minutos.
- [SUPOSIÇÃO S2] Num projeto que já tem `bob.yaml` ou hook pre-push, a instalação não sobrescreve sem avisar.
- [SUPOSIÇÃO S3] Atualizar preserva o `bob.yaml` e o `.bob/waivers.yaml` do projeto.
- [SUPOSIÇÃO S4] O `bob.yaml` criado usa os valores padrão já documentados no README.
- [SUPOSIÇÃO S5] Funciona em Linux e macOS. Windows não é alvo desta entrega.
- [SUPOSIÇÃO S6] O projeto-alvo é um repositório git (o bob mede o diff e o hook é do git).

## Critérios de sucesso
1. Num projeto novo, um único comando leva até `bob doctor` sair com 0 em até 5 minutos (Q6 A).
2. Depois desse comando, as skills do bob estão no projeto e aparecem no Cursor, no Claude Code, no GitHub Copilot e no Devin, sem plugin nativo instalado.
3. Depois desse comando, o projeto tem um `bob.yaml` válido (`bob check` não sai com 4 por configuração).
4. Depois desse comando, o hook pre-push está ativo e roda `bob check` num push.
5. Atualizar para uma versão nova funciona: depois dela, `bob doctor` sai com 0 e as skills estão na versão nova.
6. Nenhum passo exige clonar o repositório do bob à mão.

## Perguntas abertas
- Nenhuma bloqueante. Confirmar as suposições S1 a S6.
