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

ADR 0007 was accepted by Emerson on 15/10/2026. The generator is Docusaurus 3.x because it is the most widely adopted and stable option, with native versioning and i18n. Search is Algolia DocSearch. The default language is English. The second language is pt-BR. The current address is `https://fazedordecodigo.github.io/bob/`. The custom domain `bob.fazedordecodigo.com` is the next step, [issue 163](https://github.com/fazedordecodigo/bob/issues/163). The site stays in `website/`, the existing `.md` files stay plain Markdown, and the Python package stays untouched. MkDocs is rejected because it has had no stable release since August 2024. Starlight is rejected because it is still pre-1.0.
