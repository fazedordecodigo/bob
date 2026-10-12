# Empacotamento para quatro agentes

Status: aceita no PR #44, com o corte das skills do Pocock no PR #52. Registrada em 12/10/2026.

## Contexto

O README do commit `80de90c`, na noite de 10/10/2026, já nomeia Cursor, Claude Code, GitHub Copilot e Devin, a CLI `bob`, o pacote `bob-quality` e o marketplace `bob`. A pesquisa inclui Codex na tabela de instalação e marca os caminhos de skill do Devin como não verificados na doc oficial.

A issue #10 pede `.claude-plugin/`, `.cursor-plugin/`, `.plugin/` para o Copilot, e uma cópia das skills para `.github/skills`, `.agents/skills` e a pasta do Devin. Também pede atribuição ao Pocock. Nada é publicado.

O PR #16 vendoriza as skills do Pocock. A issue #47, fechada, registra o pedido do Emerson em 11/10/2026. O Poteto Mode substitui essas skills como método. O PR #52 as remove. O changelog diz que o bob distribui `bob-check`, `harden` e `review-report`.

A página Notion do ticket 47 ainda estava "In progress" em 12/10/2026, com o PR #52 descrito como aberto. O PR #52 está mergeado em `246d2eb`.

## Decisão

O pacote pip se chama `bob-quality`. O comando é `bob`. O nome de marketplace é `bob`. Publicar continua fora do MVP. O workflow `package` gera sdist e wheel, roda `twine check` e `bob doctor`, e não envia o pacote.

`.claude-plugin/plugin.json` é a lista de skills que o instalador lê. Claude Code, o Copilot CLI e o Devin leem essa árvore. Não existe `.plugin/`. O PR #44 mede o motivo. O Copilot consulta o manifesto legado antes de `.claude-plugin/`, e um segundo arquivo poderia divergir.

`.cursor-plugin/plugin.json` repete o mesmo array e acrescenta `displayName`. O teste de empacotamento falha se os arrays divergirem.

O instalador é `python -m bob_quality.install_skills`. Não é subcomando de `bob`.

- `copilot` grava `.github/skills`.
- `devin` e `agents` gravam `.agents/skills`. É o mesmo diretório.
- Claude Code não tem alvo no instalador. As skills ficam no clone, em `skills/<nome>/SKILL.md`.

Cada pasta instalada leva o `LICENSE` mais próximo, da pasta da skill até a raiz do plugin. `NOTICE` não é arquivo de atribuição. Uma pasta aposentada só é apagada quando o `NOTICE` é um arquivo regular com o texto antigo.

As skills não entram no wheel. De um pacote instalado, `--source` precisa ser um clone. A issue #45, aberta, é o trabalho pós-MVP de colocá-las no wheel. O texto dela ainda fala em LICENSE e NOTICE do Pocock.

## Consequências

Instalar `copilot` e `devin` no mesmo projeto grava cada skill duas vezes. O PR #44 avisa que o Devin pode carregar as duas.

A Action composta instala o pacote e roda `bob check`. Ela não instala skills. O comentário no PR é o `.bob/report.md` sob o marcador `<!-- bob-report -->`. A skill `review-report` pede outro texto no corpo do PR, com Summary, Evidence e Merge Danger.

O hook em `src/bob_quality/hooks/pre-push` roda `bob check --gates crap,dry,deps`. A spec, a skill `skills/bob-check/SKILL.md` e `bob check` sem `--gates` descrevem os mesmos três gates. A Action, sem inputs, roda `crap,dry,deps,mutate`. A mutação continua fora do hook e do `bob check` sem `--gates`.

A issue #54 e o pull request #55 tratam de `rmtree` em skill que é link simbólico.
