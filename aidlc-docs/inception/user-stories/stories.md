# 2.4 User Stories — bob: instalação e configuração sem plugin nativo

Profundidade: Minimal. Autor: Analista de Produto. Data: 2026-10-18 (UTC-3).
Insumos: `ideation/intent/`, `inception/reverse-engineering/`, `inception/requirements/requirements.md` (aprovado no portão G-2.3).
Histórias dizem o quê e por quê. Não escolhem mecanismo.

## Personas
- **Dev**: dev da comunidade (I-Q1 C). Usa Cursor, Claude Code, GitHub Copilot ou Devin (I-Q4 A). Tem Python e Node na máquina (I-S1). Quer o bob rodando no projeto sem estudar o repo do bob. O Emerson é o primeiro Dev.
- **Mantenedor**: o Emerson, dono do repo `fazedordecodigo/bob`. Publica as releases (P2) e responde pela documentação.

Termos usados nos critérios:
- "Projeto novo": R-S8 (repo git com commit e código, sem `bob.yaml`, sem hook pre-push, sem skills do bob).
- "Plataformas": Linux e macOS, x64 e arm64 (I-S5, R-S1).
- "Última release": a release publicada mais nova do GitHub. Pré-release e rascunho não contam (G-2.3).

## Épico 1 — Instalar

### US1.1 Instalar o bob com um comando
Como Dev, quero instalar e configurar o bob no meu projeto com um único comando, para começar a usar os gates sem clonar nada nem instalar plugin.

Critérios de aceite:
1. Dado um projeto novo, em cada plataforma, quando rodo o comando de instalação na raiz, então em até 5 minutos o `bob doctor` sai com 0.
2. Dado o mesmo cenário, quando conto meus passos, então rodei 1 comando, clonei 0 repositórios, editei 0 arquivos e instalei 0 plugins.
3. Dado o mesmo cenário, quando o comando termina, então a versão instalada é a última release publicada do bob.
4. Dado o mesmo cenário, quando o comando roda, então nenhum passo pede `sudo` ou senha de administrador.
5. Dado o mesmo cenário, quando o comando termina, então o gitleaks 8.30.1 e todas as ferramentas que o `bob doctor` confere estão nas versões pinadas.
6. Dado um projeto já instalado, quando rodo o comando de novo, então ele sai com 0, altera 0 arquivos meus e não duplica nenhuma skill.

Cobre: FR1.1, FR1.2, FR1.3, FR1.4, FR1.5, FR2.1, FR2.2, NFR1, NFR2, NFR3, NFR4, NFR7.

### US1.2 Saber antes se falta pré-requisito
Como Dev, quero ser avisado antes da instalação quando meu Python ou Node está fora da faixa, para corrigir sem ficar com o projeto pela metade.

Critérios de aceite:
1. Dado um Python ou Node fora da faixa que o `bob doctor` aceita, quando rodo o comando de instalação, então ele para antes de instalar qualquer coisa.
2. Dado esse cenário, quando leio a mensagem, então ela cita a ferramenta, a versão encontrada e a versão exigida.
3. Dado esse cenário, quando o comando termina, então o código de saída é diferente de 0 e 0 arquivos do projeto foram alterados.

Cobre: FR7.3, FR7.2, NFR9, NFR5.

### US1.3 Confiar nos binários baixados
Como Dev, quero que todo binário baixado seja conferido antes do uso, para não rodar no meu projeto algo adulterado.

Critérios de aceite:
1. Dado um download do gitleaks, quando o comando o recebe, então ele confere a integridade antes de usar (100% dos binários baixados).
2. Dado um binário cuja conferência falha, quando o comando termina, então 0 binários foram instalados, a mensagem cita o passo e a ação, e o código de saída é diferente de 0.

Cobre: FR2.3, NFR6, NFR9.

### US1.4 Não mexer nas ferramentas do meu projeto
Como Dev com um projeto que já tem ferramentas próprias (por exemplo vitest ou eslint em outra versão), quero que o bob não as altere nem se confunda com elas, para o meu build continuar igual.

Critérios de aceite:
1. Dado um projeto com dependências próprias, quando instalo o bob, então 0 bytes mudam nos manifestos e lockfiles de dependências do projeto.
2. Dado um projeto com vitest ou eslint em versão diferente da pinada pelo bob, quando rodo `bob doctor`, então ele confere as ferramentas do bob e sai com 0.

Cobre: FR2.4, FR2.5, NFR5.

### US1.5 Pedir ao meu agente de IA para instalar o bob (Adendo A1)
Como Dev, quero pedir ao meu agente de IA para instalar o bob passo a passo, com um prompt, para instalar sem rodar o `install.sh`.
Origem: Adendo A1 em `requirements.md` (2.8 rodada 1, CT18).

Critérios de aceite:
1. Dado um projeto novo, em cada plataforma, e um agente que roda comandos de shell (A1-S4), quando ele segue o prompt até o fim, então `bob doctor` sai com 0, a versão mostrada é a última release publicada e as skills (só em `.agents/skills`), o `bob.yaml` e o hook batem com os do comando único (100% dos itens do resultado). No Claude Code, a leitura das skills fica sob RA1.
2. Dado o mesmo cenário, quando confiro o que o agente fez, então houve 0 downloads e 0 execuções do `install.sh`, 0 usos de `sudo`, 0 clones do repo do bob e 0 plugins instalados.
3. Dado um passo do prompt que falha, quando o agente o roda, então ele para nesse passo, mostra ao humano a saída completa, não roda os passos seguintes, e a mensagem cita o passo que falhou.
4. Dado um binário baixado cuja conferência de integridade falha, quando o agente roda esse passo, então 0 binários são instalados e o agente para, como no critério 3.
5. Dado um projeto com `bob.yaml`, hook pre-push e `.bob/waivers.yaml` próprios, quando o agente segue o prompt, então os três ficam com 0 bytes alterados (mesmo hash antes e depois) e a saída final os lista como preservados.
6. Dado os 4 docs de instalação (README pt-BR e en, `docs/instalacao.md`, `docs/getting-started/installation.md`), quando os leio, então o comando único aparece antes da alternativa, a alternativa aparece 1 vez, diz que em divergência vale o comando único e aponta o prompt no idioma do doc.
7. Dado uma release nova que muda o resultado do comando único, quando ela é publicada, então o prompt em pt-BR e en foi atualizado na mesma release e a paridade (critério 1) foi conferida com pelo menos 1 agente real (A1-S5).

Cobre: FR1.6, FR1.7, FR1.8, FR8.4, FR8.5, FR1.4, FR2.3, FR4.6, FR5.3, NFR3, NFR5, NFR6, NFR7, NFR9, NFR10, NFR11.

## Épico 2 — Skills nos agentes

### US2.1 Ter as skills do bob no meu agente sem plugin
Como Dev, quero que meu agente encontre as skills do bob dentro do projeto, para ele saber quando rodar os gates sem eu instalar plugin.

Critérios de aceite:
1. Dado um projeto recém-instalado, com as skills só em `.agents/skills`, quando abro o projeto em Cursor, Claude Code, GitHub Copilot e Devin, então cada um lista `bob-check`, `harden` e `review-report`. No Claude Code, este critério fica sob risco aceito (RA1 em `requirements.md`: a doc dele só cita `.claude/skills`).
2. Dado o mesmo cenário, quando conto as skills do bob em cada agente, então cada skill aparece exatamente 1 vez (inclusive no Devin).
3. Dado um projeto com skills de outras origens, quando instalo ou atualizo o bob, então essas skills ficam byte a byte iguais.

Cobre: FR1.3, FR3.1, FR3.2, FR3.3, FR3.4.
Dependência: P3 resolvida no 2.6 (pasta única `.agents/skills`). Risco aceito RA1 no Claude Code.

## Épico 3 — Configuração do projeto

### US3.1 Ganhar um `bob.yaml` que funciona
Como Dev, quero que a instalação crie um `bob.yaml` adequado ao meu projeto, para o primeiro `bob check` rodar sem eu editar configuração.

Critérios de aceite:
1. Dado um projeto novo com pasta `src/`, quando instalo, então existe `bob.yaml`, `paths.include` lista `src` e `bob check` não sai com 4 por configuração.
2. Dado um projeto novo sem `src/` e com código em outras pastas, quando instalo, então `paths.include` lista só pastas de código que existem e `bob check` não sai com 4 por configuração.
3. Dado o mesmo cenário, quando comparo com os padrões do README, então todas as chaves, exceto `paths.include`, têm o valor padrão.
4. Dado um projeto sem nenhuma pasta de código reconhecível, quando instalo, então ainda existe um `bob.yaml` válido e o resumo final avisa que não achou código.

Cobre: FR4.1, FR4.2, FR4.3, FR4.4, FR4.5.

### US3.2 Manter o que já configurei
Como Dev que já tem `bob.yaml` ou hook pre-push, quero que a instalação e a atualização não os alterem, para não perder minha configuração.

Critérios de aceite:
1. Dado um projeto com `bob.yaml` e hook pre-push próprios, quando instalo, então os dois ficam byte a byte iguais e o resumo final avisa que foram preservados.
2. Dado esse cenário, quando o comando roda, então ele não me pergunta nada e sai com 0.
3. Dado um projeto com `.bob/waivers.yaml`, quando instalo ou atualizo, então 0 bytes mudam nesse arquivo.

Cobre: FR4.6, FR5.3, FR6.3, NFR5, NFR4.

## Épico 4 — Hook pre-push

### US4.1 Ter os gates rápidos rodando a cada push
Como Dev, quero que o hook pre-push fique ativo na instalação, para os gates rodarem antes do código sair da minha máquina.

Critérios de aceite:
1. Dado um projeto recém-instalado, quando faço `git push` num terminal novo, sem ativar ambiente, então o hook roda `bob check --gates crap,dry,deps`.
2. Dado o repo-fixture do bob, quando o hook roda, então termina em menos de 60 s.

Cobre: FR5.1, FR5.2, NFR8.

## Épico 5 — Atualizar

### US5.1 Atualizar para a release mais nova
Como Dev, quero atualizar o bob do projeto com um comando, para ter correções e skills novas sem refazer a instalação.

Critérios de aceite:
1. Dado um projeto numa release antiga e uma release publicada mais nova, quando rodo o comando de atualização, então o projeto passa para essa release.
2. Dado o mesmo cenário, quando a atualização termina, então `bob doctor` sai com 0 e as skills do projeto são as da release nova.
3. Dado o mesmo cenário, quando conto meus passos, então rodei 1 comando e editei 0 arquivos.
4. Dado um projeto já na release mais nova, quando rodo a atualização, então ela avisa, altera 0 arquivos e sai com 0.
5. Dado um projeto com `bob.yaml` e `.bob/waivers.yaml` editados pelo Dev e uma release mais nova publicada, quando ele roda o comando de atualizar, então os dois arquivos ficam com 0 bytes alterados (mesmo hash antes e depois), os itens de terceiros seguem intactos e o resumo final lista o que foi preservado.

Cobre: FR6.1, FR6.2, FR6.3, FR6.5, NFR2, NFR4, NFR5.

### US5.2 Saber qual versão está instalada
Como Dev, quero ver qual release do bob está no meu projeto, para saber se preciso atualizar.

Critérios de aceite:
1. Dado um projeto instalado, quando peço a versão, então vejo o número da release instalada.
2. Dado uma atualização concluída, quando peço a versão, então vejo o número da release nova.

Cobre: FR6.4.

## Épico 6 — Retorno ao Dev

### US6.1 Entender o que aconteceu
Como Dev, quero um resumo ao fim e erros claros, para saber o que mudou no projeto e o que fazer se algo falhar.

Critérios de aceite:
1. Dado qualquer instalação concluída, quando o comando termina, então o resumo lista o que instalou, o que preservou e o resultado do `bob doctor`.
2. Dado qualquer falha, quando o comando termina, então a mensagem cita o passo que falhou e a ação a tomar (100% das falhas) e o código de saída é diferente de 0.

Cobre: FR7.1, FR7.2, NFR9.

## Épico 7 — Documentação e releases

### US7.1 Achar o caminho certo na documentação
Como Dev, quero que o README e os docs mostrem o comando único, os requisitos reais e como atualizar, para eu não seguir o caminho antigo com clone.

Critérios de aceite:
1. Dado o README (pt-BR e en) e os docs de instalação, quando os leio, então o primeiro caminho de instalação é o comando único, sem clone e sem plugin.
2. Dado esses docs, quando confiro os requisitos, então eles citam Python e Node com as faixas reais e dizem que o gitleaks vem pelo comando.
3. Dado esses docs, quando confiro as versões pinadas listadas, então 100% batem com as do pacote.
4. Dado esses docs, quando procuro como atualizar e ver a versão, então acho as duas instruções.

Cobre: FR8.1, FR8.2, FR8.3.

### US7.2 Publicar pré-release sem afetar quem usa
Como Mantenedor, quero que só releases publicadas contem como "última release", para testar pré-releases e rascunhos sem que a instalação ou a atualização dos Devs os peguem.

Critérios de aceite:
1. Dado uma release publicada e uma pré-release mais nova, quando um Dev instala, então recebe a release publicada.
2. Dado um projeto na última release publicada e um rascunho de release mais novo, quando o Dev atualiza, então nada muda e o comando avisa que já está na mais nova.

Cobre: FR1.4, FR6.1, FR6.5.

## Cobertura FR/NFR → US

| Req. | Destino | Tipo | Verificado em |
|---|---|---|---|
| FR1.1 | US1.1 | história | US1.1 crit. 1, 2 |
| FR1.2 | US1.1 | história | US1.1 crit. 2 |
| FR1.3 | US1.1, US2.1 | história | US1.1 crit. 2; US2.1 crit. 1 |
| FR1.4 | US1.1, US7.2, US1.5 | história | US1.1 crit. 3; US7.2 crit. 1; US1.5 crit. 1 |
| FR1.5 | US1.1 | história | US1.1 crit. 1 |
| FR1.6 | US1.5 | história (Adendo A1) | US1.5 crit. 1, 2 |
| FR1.7 | US1.5 | história (Adendo A1) | US1.5 crit. 1, 4, 5 |
| FR1.8 | US1.5 | história (Adendo A1) | US1.5 crit. 3 |
| FR2.1 | US1.1 | história | US1.1 crit. 5 |
| FR2.2 | US1.1 | história | US1.1 crit. 5 |
| FR2.3 | US1.3, US1.5 | história | US1.3 crit. 1, 2; US1.5 crit. 4 |
| FR2.4 | US1.4 | história | US1.4 crit. 1 |
| FR2.5 | US1.4 | história | US1.4 crit. 2 |
| FR3.1 | US2.1 | história | US2.1 crit. 1 |
| FR3.2 | US2.1 | história | US2.1 crit. 1 (P3 resolvida; RA1 no Claude Code) |
| FR3.3 | US2.1 | história | US2.1 crit. 2 |
| FR3.4 | US2.1 | história | US2.1 crit. 3 |
| FR4.1 | US3.1 | história | US3.1 crit. 1 |
| FR4.2 | US3.1 | história | US3.1 crit. 3 |
| FR4.3 | US3.1 | história | US3.1 crit. 1, 2 |
| FR4.4 | US3.1 | história | US3.1 crit. 1, 2 |
| FR4.5 | US3.1 | história | US3.1 crit. 4 |
| FR4.6 | US3.2, US1.5 | história | US3.2 crit. 1; US1.5 crit. 5 |
| FR5.1 | US4.1 | história | US4.1 crit. 1 |
| FR5.2 | US4.1 | história | US4.1 crit. 1 |
| FR5.3 | US3.2, US1.5 | história | US3.2 crit. 1; US1.5 crit. 5 |
| FR6.1 | US5.1, US7.2 | história | US5.1 crit. 1; US7.2 crit. 2 |
| FR6.2 | US5.1 | história | US5.1 crit. 2 |
| FR6.3 | US3.2, US5.1 | história | US3.2 crit. 3; US5.1 crit. 5 |
| FR6.4 | US5.2 | história | US5.2 crit. 1, 2 |
| FR6.5 | US5.1, US7.2 | história | US5.1 crit. 4; US7.2 crit. 2 |
| FR7.1 | US6.1 | história | US6.1 crit. 1 |
| FR7.2 | US6.1, US1.2 | história | US6.1 crit. 2; US1.2 crit. 3 |
| FR7.3 | US1.2 | história | US1.2 crit. 1, 2 |
| FR8.1 | US7.1 | história | US7.1 crit. 1 |
| FR8.2 | US7.1 | história | US7.1 crit. 2, 3 |
| FR8.3 | US7.1 | história | US7.1 crit. 4 |
| FR8.4 | US1.5 | história (Adendo A1) | US1.5 crit. 6 |
| FR8.5 | US1.5 | história (Adendo A1) | US1.5 crit. 7 |
| NFR1 | US1.1 | critério em história | US1.1 crit. 1 (≤ 5 min) |
| NFR2 | US1.1, US5.1 | critério em história | US1.1 crit. 2; US5.1 crit. 3 |
| NFR3 | US1.1, US1.5 | transversal: vale para todas as US; sem história própria | US1.1 crit. 1 e US1.5 crit. 1 rodam em cada plataforma; os demais critérios também |
| NFR4 | US1.1, US3.2, US5.1 | transversal: repetição segura | US1.1 crit. 6; US5.1 crit. 4 |
| NFR5 | US1.4, US3.2, US1.2, US5.1, US1.5 | transversal: preservação | US1.4 crit. 1; US3.2 crit. 1, 3; US1.2 crit. 3; US5.1 crit. 5; US1.5 crit. 5 |
| NFR6 | US1.3, US1.5 | critério em história | US1.3 crit. 1, 2; US1.5 crit. 4 |
| NFR7 | US1.1, US1.5 | transversal: privilégio, sem história própria | US1.1 crit. 4; US1.5 crit. 2 |
| NFR8 | US4.1 | critério em história | US4.1 crit. 2 (< 60 s) |
| NFR9 | US6.1, US1.2, US1.3, US1.5 | transversal: clareza de erro | US6.1 crit. 2; US1.2 crit. 2; US1.3 crit. 2; US1.5 crit. 3 |
| NFR10 | US1.5 | critério em história (Adendo A1) | US1.5 crit. 1, 7 |
| NFR11 | US1.5 | critério em história (Adendo A1) | US1.5 crit. 2 |

## Pré-condições (de `requirements.md`)
- P1: `bob doctor` = 4 na `main` (vitest). Bloqueia US1.1 crit. 1 e US5.1 crit. 2.
- P2: release v0.1.0 publicada, com OK do Emerson. Bloqueia US1.1 crit. 3, US5.1 e US7.2.
- P3: resolvida no 2.6 (D-2.6): pasta única `.agents/skills` para os quatro agentes. Não bloqueia mais. Risco aceito RA1 no Claude Code (US2.1 crit. 1).

## Fora de escopo
Igual a `requirements.md`: PyPI nesta entrega, desinstalar, Codex, publicação como plugin (#145–#149), GitHub Action no projeto do dev, Windows, mudar gates, escolher agentes, forçar sobrescrita.

## Suposições novas
- Nenhuma. As histórias usam só I-S1–I-S6, R-S1–R-S8 e G-2.3.
- Adendo A1: a US1.5 usa A1-S1 a A1-S5 (`requirements.md`, a confirmar pelo Emerson).

## Registro de alterações
- 2026-10-18 ~17:37 (UTC-3): portão 2.4, rodada 1. Emerson: "Quero o critério de preservação na história de atualizar (US5.1)." Acrescentado US5.1 crit. 5; NFR5 na lista Cobre da US5.1; tabela de cobertura atualizada em FR6.3 e NFR5.
- 2026-10-18 ~18:31 (UTC-3): decisão D-2.6 do Emerson, via Maestro: "As skills devem ir para .agents/skills essa pasta é padrão para todos os agentes. Não precisa duplicar em várias pastas." e "Aceito o risco no Claude Code e mantenho .agents/skills." US2.1 crit. 1, dependência da US2.1, pré-condição P3 e linha FR3.2 da cobertura ajustadas.
- 2026-10-18 ~19:33 (UTC-3): Adendo A1 (2.8 rodada 1). Emerson, via Maestro: "Adicione um prompt que orie te um modelo de IA a como instalar passo a passo o pacote sem depender de um arquivo .sh" e "Deve haver as duas opções a principal sendo o arquivo .sh" Nova US1.5 (7 critérios); cobertura com FR1.6, FR1.7, FR1.8, FR8.4, FR8.5, NFR10, NFR11 e US1.5 acrescentada em FR1.4, FR2.3, FR4.6, FR5.3, NFR3, NFR5, NFR6, NFR7, NFR9.
