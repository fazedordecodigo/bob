# Publishing the Cursor plugin

[Index](README.md) · [Agents](getting-started/agents.md) · [SPEC](SPEC.md)

The `cursor` job in [`.github/workflows/publish-plugins.yml`](https://github.com/fazedordecodigo/bob/blob/main/.github/workflows/publish-plugins.yml) checks the plugin tree. The marketplace listing stays manual. Emerson submits the repository at [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish).

Story 19, acceptance criterion 12, and the out-of-scope line in [SPEC.md](SPEC.md) leave marketplace publication for his approval.

## Check the tree

At the clone root, with the `dev` extra installed:

```bash
python scripts/validate_cursor_plugin.py --root . --tag v0.1.0
```

An empty list and exit `0` mean the manifest, the version, and the checklist match the tag. A JSON list and exit `1` name each failure. Exit `2` is invalid usage, and the message is on stderr.

The script reads `scripts/cursor_plugin.schema.json`. That file is a byte-for-byte copy of [`schemas/plugin.schema.json`](https://github.com/cursor/plugins/blob/5229aad76c37451561c5b81a9b5072ae1c549a5b/schemas/plugin.schema.json) at commit `5229aad76c37451561c5b81a9b5072ae1c549a5b` of `cursor/plugins`. The test `test_schema_bytes_match_the_pinned_cursor_plugins_commit` locks the SHA-256.

## What a tag triggers

The workflow runs in three cases.

- A push of a `v*` tag.
- A release of type `published`.
- `workflow_dispatch`, with the boolean input `dry_run`. The default is `true`.

The job installs the `dev` extra and runs the same script. On a tag or a release it passes `--tag` with the tag name. On a dispatch from a branch it omits `--tag` and compares only `.cursor-plugin/plugin.json` with `[project].version` in `pyproject.toml`.

The log prints `dry_run=`. Both values walk the same steps. The job does not submit the plugin anywhere.

`permissions` is `contents: read`. The file does not reference `secrets`. There is no secret to create for this phase.

A job for another platform is a sibling of `cursor`, in the same `jobs`.

## Send the first listing

Open [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish) with Emerson's account. The submission asks for the public repository `https://github.com/fazedordecodigo/bob`.

The page [Plugins reference](https://cursor.com/docs/reference/plugins) lists what review checks. In this repository each item points at a file.

- Manifest `.cursor-plugin/plugin.json`, name `bob`.
- `description` in the same file.
- Skills `./skills/bob-check`, `./skills/harden`, and `./skills/review-report`, each with `name` and `description` in the frontmatter.
- The committed logo `assets/logo.svg`, field `logo` with that relative path.
- `README.md`, section `Usage`, with `bob check` and `bob.yaml`.
- Manifest paths that are relative, with no `..`.

The form itself did not return the field labels in the session that wrote this page. What the public page asks for is the repository link. Check the signed-in screen for any further text it asks for.

## After the listing

The page [Marketplace security](https://cursor.com/help/security-and-privacy/marketplace-security) answers "Are plugin updates reviewed?" with this sentence: "Plugins in the marketplace are not automatically updated from source code." Each update goes through manual review.

A `v*` tag puts the manifest, `pyproject.toml`, and the tag on the same version. The public marketplace receives that version only after Cursor's review. The tag does not replace the form or a new review round.

The decision that stays with Emerson is to accept that manual review for every version. The documentation used above does not describe a publish API.

The plugin name stays `bob`. Issue #145 already records that this name can collide in review.

## Load it in local Cursor

The copy at `~/.cursor/plugins/local/bob` has to be a real directory. Cursor ignores a symlink whose target is outside that folder. Source: [Test plugins locally](https://cursor.com/docs/plugins).

```bash
rm -rf ~/.cursor/plugins/local/bob
mkdir -p ~/.cursor/plugins/local/bob
git archive HEAD | tar -x -C ~/.cursor/plugins/local/bob
test ! -L ~/.cursor/plugins/local/bob
test -f ~/.cursor/plugins/local/bob/.cursor-plugin/plugin.json
test -f ~/.cursor/plugins/local/bob/assets/logo.svg
test -f ~/.cursor/plugins/local/bob/skills/bob-check/SKILL.md
```

Then run **Developer: Reload Window** and open Customize. This checkout does not open the IDE, so that reload is for a person with Cursor open.
