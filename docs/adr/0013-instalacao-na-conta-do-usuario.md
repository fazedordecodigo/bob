# Instalação na conta do usuário e launcher estável

Status: aceita pelo Emerson em 18/10/2026, na aprovação do desenho da aplicação. Publicada em `docs/adr/` na U9.

## Contexto

NFR7: sem `sudo`. FR2.4: não mexer nas dependências do projeto. FR5.2: hook sem ativar ambiente. O hook atual chama `bob` pelo `PATH` (`src/bob_quality/hooks/pre-push:5`).

## Decisão

- `BOB_HOME` = `$BOB_HOME` ou `${XDG_DATA_HOME:-$HOME/.local/share}/bob-quality`.
- `BOB_HOME/versions/<v>/venv`: um venv por versão. As ferramentas npm vão para o pacote dentro desse venv (`bob doctor --install`, como hoje).
- `BOB_HOME/current` → `versions/<v>`, trocado por rename atômico só depois do venv pronto.
- `BOB_HOME/bin/bob` → `current/venv/bin/bob`. Caminho estável usado pelo hook.
- `~/.local/bin/bob` → `BOB_HOME/bin/bob`.
- `PATH` do shell (Q1 A, `application-design-questions.md`). Quem faz: `install.sh` (C01), depois do passo `pacote` e antes do `bob setup`.
  - Precisa? Só se `:$PATH:` não contém `:$HOME/.local/bin:`. Se contém, não toca em nada.
  - Shell: nome base de `$SHELL` (shell de login do usuário). Não usa o shell que roda o `install.sh`, porque o one-liner roda em `sh`.
    - `zsh` → `${ZDOTDIR:-$HOME}/.zshrc`.
    - `bash` → `~/.bashrc`.
    - qualquer outro ou `$SHELL` vazio → `~/.profile`.
  - Linha (uma só, com a marca no fim):
    `export PATH="$HOME/.local/bin:$PATH" # managed-by: bob-quality`
  - Idempotência: se o arquivo já tem `# managed-by: bob-quality`, não escreve. Repetir não duplica a linha.
  - Perfil não existe: cria o arquivo só com a linha (modo `0644`). Não cria o perfil de outro shell.
  - Perfil existe: acrescenta no fim. Se o arquivo não termina em quebra de linha, põe uma antes. O conteúdo anterior fica byte a byte igual.
  - Perfil é symlink (gerenciador de dotfiles): escreve no destino, como o shell leria.
  - Não consegue gravar (permissão ou disco): não falha a instalação. Avisa e mostra a linha para colar. Código de saída segue o do `bob setup`. O hook e o `bob setup` não dependem do `PATH` (usam `BOB_HOME/bin/bob`).
  - Resumo: o `install.sh` passa o resultado ao `bob setup` pela variável interna `BOB_INSTALL_PROFILE` (`<arquivo>`, `already-on-path`, `already-marked` ou `failed:<arquivo>`). O resumo ganha a linha `perfil do shell:` (texto em `component-interfaces.md`).
  - `bob update` não mexe no perfil: o caminho do launcher não muda.
- Versões antigas: ficam. Desinstalar está fora de escopo.

## Alternativas

Venv no projeto (`.venv` do dev: fere FR2.4); `pip install --user` (mistura com o Python do sistema; PEP 668 bloqueia).

## Consequências

- Ubuntu sem `python3-venv` faz `python3 -m venv` falhar. O `install.sh` confere antes e cita o pacote do SO a instalar (fora do comando, é pré-requisito I-S1).
- O `PATH` só vale num terminal novo ou depois de `. <arquivo>`. O resumo diz isso.
- Risco aceito: no macOS, bash de login lê `~/.bash_profile`, não `~/.bashrc`. O shell padrão do macOS é zsh, e o caso bash no macOS não é coberto. O aviso do resumo mostra a linha e o arquivo, para o dev ajustar.
- Shells com outra sintaxe (ex.: fish) caem em `~/.profile`, que eles não leem. Mesma mitigação: o resumo mostra a linha.
