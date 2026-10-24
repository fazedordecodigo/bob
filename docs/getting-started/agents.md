# Agents

[Index](../README.md) · [Installation](installation.md) · [Pre-push hook](../guides/pre-push.md)

Install bob with the one-line install, at the root of your project:

```bash
curl -fsSL https://github.com/fazedordecodigo/bob/releases/latest/download/install.sh | sh
```

The one-line install runs `bob setup`, which copies the three skills to one folder of the project, `.agents/skills`:

- `bob-check`
- `harden`
- `review-report`

There is no plugin to install and no copy in another folder. Each agent loads each skill once, from that folder:

| Agent | Folder | Note |
|---|---|---|
| Cursor | `.agents/skills` | |
| Claude Code | `.agents/skills` | accepted risk RA1 |
| GitHub Copilot | `.agents/skills` | |
| Devin | `.agents/skills` | CLI and web |

**Claude Code (accepted risk RA1).** The Claude Code docs name only `.claude/skills` for project skills. With the single folder `.agents/skills`, Claude Code may not see the bob skills. The project keeps one folder and accepts this risk.

Skills from other sources in `.agents/skills` stay as they are. `bob setup` replaces only the bob skills.

## Skills version

```bash
bob --version
```

The second line shows the version of the skills in `.agents/skills`. `bob update` installs the latest release and refreshes the skills. See [Installation](installation.md).
