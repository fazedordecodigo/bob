# Agentes

[Índice](../README.md) · [Instalação](installation.md) · [Hook pre-push](../guides/pre-push.md)

Instale o bob com o comando único, na raiz do seu projeto:

```bash
curl -fsSL https://github.com/fazedordecodigo/bob/releases/latest/download/install.sh | sh -s -- --lang pt-BR
```

O comando único roda o `bob setup`, que copia as três skills para uma única pasta do projeto, `.agents/skills`:

- `bob-check`
- `harden`
- `review-report`

Não há plugin para instalar nem cópia em outra pasta. Cada agente carrega cada skill uma vez, dessa pasta:

| Agente | Pasta | Nota |
|---|---|---|
| Cursor | `.agents/skills` | |
| Claude Code | `.agents/skills` | risco aceito RA1 |
| GitHub Copilot | `.agents/skills` | |
| Devin | `.agents/skills` | CLI e web |

**Claude Code (risco aceito RA1).** A doc do Claude Code só cita `.claude/skills` para skills de projeto. Com a pasta única `.agents/skills`, o Claude Code pode não enxergar as skills do bob. O projeto mantém uma pasta só e aceita esse risco.

Skills de outras origens em `.agents/skills` ficam como estão. O `bob setup` substitui só as skills do bob.

## Versão das skills

```bash
bob --version
```

A segunda linha mostra a versão das skills em `.agents/skills`. O `bob update` instala a última release e atualiza as skills. Ver [Instalação](installation.md).
