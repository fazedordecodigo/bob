# 2.6 Application Design — perguntas
Contexto: o bob fica instalado na conta do usuário, com o launcher em `~/.local/bin/bob` (ADR 0013). Em muitas máquinas, sobretudo macOS, essa pasta não está no `PATH`, e o comando `bob` não aparece no terminal.
O hook e o `bob setup` usam caminho absoluto e funcionam de qualquer jeito. A dúvida é só se o instalador pode editar arquivos de configuração do shell do dev, fora do projeto. Modo de coleta do projeto: chat (o Maestro apresenta com recomendações).

## Q1. [Product owner] Se `~/.local/bin` não está no `PATH`, o que o comando de instalação faz?
A. Acrescenta uma linha marcada ao arquivo de perfil do shell do dev (`~/.zshrc`, `~/.bashrc` ou `~/.profile`), uma vez só, e avisa no resumo qual arquivo mudou
B. Não edita nada fora do projeto; o resumo mostra a linha exata para o dev colar no perfil
X. Outra (especifique)
Recomendação: A — cumpre "comando `bob` disponível" (FR1.1) e "0 arquivos editados à mão" (NFR2); é o que fazem instaladores comuns de ferramentas de linha de comando, e o resumo diz o que mudou.
[Answer]: A — "Q1 A." (Emerson, via Maestro, recebida em 18/10/2026 18:18 UTC-3)

## Checagem de ambiguidade
- Resposta vaga: não. "Q1 A." escolhe uma opção, sem condição.
- Contradição entre respostas: não. Só há uma pergunta.
- Conflito com estágios anteriores: não. `requirements.md` e `stories.md` não restringem arquivos fora do projeto. NFR7 (sem `sudo`) segue: o perfil fica na pasta do usuário. NFR2 (0 arquivos editados à mão) fica mais forte. NFR4 (repetir sem efeito) é coberto pela marca `# managed-by: bob-quality`.
- Lacunas: qual shell, qual arquivo e o que fazer se ele não existe. São decisões técnicas, sem pergunta nova. Ficam na ADR 0013 (regra de detecção) e no `verification-command.md` (passo 13).
- Resultado: arquivo coerente. Nenhuma pergunta de acompanhamento.

## Resumo das decisões
- Q1: A — se `~/.local/bin` não está no `PATH`, o comando de instalação acrescenta uma linha marcada ao perfil do shell, uma vez só, e o resumo diz qual arquivo mudou (detalhe na ADR 0013).
