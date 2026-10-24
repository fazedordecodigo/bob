# ADRs

[Index](../README.md) · [Technical overview](overview.md) · [SPEC](spec.md)

These records keep decisions the spec or a pull request already took. The pages do not rewrite a decision. Where later code is narrower or further along, the [technical overview](overview.md) and the guides document the code and point at the ADR.

| ADR | Decision |
|---|---|
| [0000](../adr/0000-architecture-review.md) | Architecture reading on 12/10/2026, at commit `246d2eb` |
| [0001](../adr/0001-adaptadores-sobre-ferramentas-de-mercado.md) | Market tools behind adapters. The core does not import them |
| [0002](../adr/0002-o-diff-filtra-o-veredito.md) | Tools measure the include tree. The diff chooses what can block |
| [0003](../adr/0003-exit-codes.md) | Exit codes `0`, `1`, `2`, `3`, and `4`, and the exceptions already approved |
| [0004](../adr/0004-empacotamento-quatro-agentes.md) | Package `bob-quality`, command `bob`, plugin name `bob`, four agents, one skill list |
| [0005](../adr/0005-modelo-de-gate-das-analises-novas.md) | Verdict, waiver, `bob.yaml` key, and report section for the later analyses |
| [0006](../adr/0006-chave-estavel-do-waiver.md) | A mutation waiver id is the file, the function, and the description |
| [0007](../adr/0007-gerador-do-site.md) | Docusaurus 3.x, Algolia DocSearch, English default, pt-BR second, GitHub Pages address now, custom domain in #163 |
| [0008](../adr/0008-fonte-unica-das-versoes-npm.md) | Single source for the npm versions: the packaged `package.json` |
| [0009](../adr/0009-skills-de-projeto-so-em-agents-skills.md) | Project skills only in `.agents/skills` |
| [0010](../adr/0010-skills-manifesto-e-license-no-wheel.md) | Skills, manifest, and LICENSE inside the wheel |
| [0011](../adr/0011-distribuicao-por-release-do-github.md) | Distribution by GitHub release with three assets: `install.sh`, the wheel, and `SHA256SUMS` |
| [0012](../adr/0012-comando-unico-install-sh-e-bob-setup.md) | One-line install: `install.sh` plus `bob setup` |
| [0013](../adr/0013-instalacao-na-conta-do-usuario.md) | Install in the user account with a stable launcher |
| [0014](../adr/0014-gitleaks-por-plataforma.md) | gitleaks 8.30.1 per platform, checked by sha256 |
| [0015](../adr/0015-geracao-do-bob-yaml.md) | `bob.yaml` generation and the `paths.include` rule |
| [0016](../adr/0016-hook-pre-push-gerenciado.md) | Managed pre-push hook |
| [0017](../adr/0017-preservacao-posse-e-idempotencia.md) | Preservation, ownership, and idempotence |
| [0018](../adr/0018-atualizacao-e-versao-visivel.md) | Update and visible version |
| [0019](../adr/0019-doctor-so-ferramentas-do-bob.md) | `bob doctor` checks only the bob tools |
| [0020](../adr/0020-docs-com-teste-de-paridade.md) | Docs with a version parity test |
| [0021](../adr/0021-bob-install-profile-already-marked.md) | `BOB_INSTALL_PROFILE` carries the file in `already-marked` too |
| [0022](../adr/0022-passo-perfil-do-install-sh.md) | The `perfil` step of `install.sh`: write, warning, and result |
| [0023](../adr/0023-linha-perfil-do-shell-no-setup.md) | Shell profile line in the `bob setup` summary |
| [0024](../adr/0024-versao-das-skills-do-projeto.md) | Project skills version: the `project_version` module |
| [0025](../adr/0025-bob-update-e-version.md) | `bob update` and `bob --version`: implementation |
| [0026](../adr/0026-harness-passos-10-11-e-13.md) | Harness: steps 10, 11, and 13 and the partial step 2 |
| [0027](../adr/0027-entrega-em-paralelo-e-changelog.md) | Parallel delivery: CHANGELOG per unit and mechanical rebase |
| [0028](../adr/0028-docs-u8-arquivos-e-links.md) | Install docs: file list, links, and parity |
| [0029](../adr/0029-u8-docs-paridade-e-passo-14.md) | Install docs shape, the parity test, and step 14 |

ADR 0007 was accepted by Emerson on 15/10/2026. The generator is Docusaurus 3.x because it is the most widely adopted and stable option, with native versioning and i18n. Search is Algolia DocSearch. The default language is English. The second language is pt-BR. The current address is `https://fazedordecodigo.github.io/bob/`. The custom domain `bob.fazedordecodigo.com` is the next step, [issue 163](https://github.com/fazedordecodigo/bob/issues/163). The site stays in `website/`, the existing `.md` files stay plain Markdown, and the Python package stays untouched. MkDocs is rejected because it has had no stable release since August 2024. Starlight is rejected because it is still pre-1.0.
