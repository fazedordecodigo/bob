# bob

Plugin de qualidade: os gates do `bob check` e as skills que dizem ao agente quando rodá-los.

## Skills

- **bob-check** (`skills/bob-check/SKILL.md`): ao verificar um diff ou quando um gate falhar.
- **harden** (`skills/harden/SKILL.md`): ao matar um mutante sobrevivente ou registrar um waiver.
- **review-report** (`skills/review-report/SKILL.md`): ao escrever o PR depois de `bob check`.

## Verificar no Cloud Agent

Os workflows `.github/workflows/ci.yml` e `.github/workflows/bob.yml` são a fonte destes passos.

1. Use Python 3.10 ou superior. O CI roda 3.10 e 3.12. A imagem precisa do `python3-venv`.
2. Use o Node 22.14.0, o mesmo do CI. O `bob doctor` aceita `>=22.14.0 <23` e sai com `4` fora dessa faixa, o Node 20, o Node 24 e um sufixo `-rc` inclusive. Instale com `fnm install 22.14.0` ou `nvm install 22.14.0`, ou baixe o `.tar.gz` de <https://nodejs.org/dist/v22.14.0/>. Prefira o `.tar.gz` ao `.tar.xz`, porque a imagem pode não ter o `xz`.
3. Crie e ative um venv com `python3 -m venv .venv && . .venv/bin/activate`. O Python do sistema recusa o `pip install` pela PEP 668.
4. Instale o pacote com `python -m pip install -e '.[dev]'`.
5. Instale as ferramentas npm fixadas com `npm ci` na raiz.
6. Rode `bob doctor`. Ele lista cada ferramenta com a versão esperada e a encontrada, e sai com `0` só quando todas batem. `bob doctor --install` roda `npm ci` no pacote instalado e serve para quem instalou o wheel. Num checkout editável, `src/bob_quality/package.json` é um symlink para a raiz, e o comando instala nessa raiz, no mesmo lugar que `npm ci`. Se já existir `src/bob_quality/node_modules` de um `--install` antigo, apague essa pasta antes do `pytest`. Ela quebra `test_mutmut_dogfood.py`.
7. Rode `python -m pytest`. A suíte leva vários minutos, porque o dogfood do mutmut gera `mutants/`.
8. Rode `bob check --base origin/main --gates crap,dry,deps,mutate`, como no CI. Sem `--gates`, o padrão é `crap,dry,deps`. O `mutate` também leva vários minutos. O relatório fica em `.bob/report.md` e `.bob/report.json`.

Os gates e os exit codes estão em [`docs/SPEC.md`](docs/SPEC.md). Três pontos do comportamento atual:

- O gate `crap` bloqueia quando o CRAP de uma função alterada é maior ou igual a `crap.max_per_function`.
- O exit `2` também sai do `bob check` padrão. O gate `crap` roda a suíte para medir a cobertura e sai com `2` se a baseline quebra.
- Um `--config` inexistente, em `check`, `crap`, `dry`, `deps` e `mutate`, sai com `4`, com stderr em inglês que cita o caminho (`config file not found: <caminho>`), e não grava nada. `doctor` e `waive` não aceitam `--config`. Um `bob.yaml` que não é mapeamento, um YAML com erro de sintaxe, ou uma chave com tipo errado dão exit `4` com mensagem em inglês no stderr, e nada é gravado. O mesmo vale para um erro de sintaxe em `.bob/waivers.yaml` e para um YAML válido com formato errado, em `check`, `doctor` e `waive`. A mensagem do formato cita o caminho e o campo. Valores semânticos inválidos e um `duplication` inválido também saem com `4`, com stderr em inglês que cita o caminho e o campo, sem relatório, em `check`, `doctor` e `waive`.
