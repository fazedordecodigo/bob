# Agents

[Index](../README.md) · [Installation](installation.md) · [Pre-push hook](../guides/pre-push.md)

The plugin ships three skills, listed in `.claude-plugin/plugin.json` and repeated in `.cursor-plugin/plugin.json`:

- `./skills/bob-check`
- `./skills/harden`
- `./skills/review-report`

Nothing is published to a marketplace. The commands below start from a clone. [ADR 0004](../adr/0004-empacotamento-quatro-agentes.md) records the packaging decision for Claude Code, Cursor, GitHub Copilot, and Devin.

## Cursor

Cursor reads `.cursor-plugin/`. Copy the clone to `~/.cursor/plugins/local/bob` as a real directory. Cursor ignores a symlink whose target is outside that folder. Then run **Developer: Reload Window**.

```bash
rm -rf ~/.cursor/plugins/local/bob
mkdir -p ~/.cursor/plugins/local/bob
git archive HEAD | tar -x -C ~/.cursor/plugins/local/bob
```

`git clone` into that path is the same requirement: the result has to be a real directory. Flattened skills inside a project go to `.agents/skills` (the installer target `agents`). The plugin under `~/.cursor/plugins/local/bob` and the skills copied into a project are different installs.

Publishing the plugin to the Cursor marketplace is a manual form. The workflow that validates the tree is [Publishing the Cursor plugin](../publishing.md).

## Claude Code

Claude Code reads `.claude-plugin/`. From the clone:

```bash
claude plugin marketplace add <clone path>
claude plugin install bob@bob
```

For one session, run `claude --plugin-dir <clone path>`.

The installer has no Claude Code target. The skills stay in the clone, at `skills/<name>/SKILL.md`.

## Codex

The repository does not ship a Codex manifest or a `codex` installer target. `src/bob_quality/install_skills.py` says `.agents/skills` is read by Cursor, Copilot, Devin, and Codex. The `agents` target writes that folder:

```bash
python3 <clone path>/src/bob_quality/install_skills.py --project <project> agents
```

The same module runs as `python -m bob_quality.install_skills`. A pip-installed `bob-quality` does not carry the skills, so pass `--source <clone path>`.

## Devin

Devin reads `.agents/skills` and `.github/skills`. The installer targets are:

| Target | Folder | Readers named in the installer |
|---|---|---|
| `agents` | `.agents/skills` | Cursor, Copilot, Devin, Codex |
| `devin` | `.agents/skills` | Devin (same directory as `agents`) |
| `copilot` | `.github/skills` | Copilot and Devin |

`devin` and `agents` write the same directory. Installing `copilot` and `devin` in one project puts every skill in both folders. Devin then loads each skill twice, so pick one target.

## GitHub Copilot

The Copilot CLI reads `.claude-plugin/`, with the same commands as Claude Code:

```bash
copilot plugin marketplace add <clone path>
copilot plugin install bob@bob
```

Repository skills for Copilot go to `.github/skills` (target `copilot`). There is no `.plugin/` directory. [ADR 0004](../adr/0004-empacotamento-quatro-agentes.md) records why a second manifest would diverge.

## What the installer does

`install_skills.py` reads the skill list from `.claude-plugin/plugin.json` and copies each folder, flattened by name, with the nearest `LICENSE` from the skill folder up to the plugin root. It does not copy `NOTICE`.

Without a manifest, the installer prints the path it read and exits `4`. When a skill has no `LICENSE` from its folder up to the plugin root, the installer warns on stderr and still installs the skill.

Running the installer again replaces the skills named in the manifest. A folder from the fixed list of skills the plugin no longer ships is deleted only when that folder's `NOTICE` is a regular file with the text the old installer wrote. A file, a symlink, a `NOTICE` that is a symlink, or a folder without that text stays, and the installer warns on stderr. Every other folder stays.
