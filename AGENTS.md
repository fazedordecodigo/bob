# bob

Plugin de qualidade: fluxo de spec do Pocock + gates `bob check`.

## Skills

- **bob-check** (`skills/bob-check/SKILL.md`): ao verificar um diff ou quando um gate falhar.
- **harden** (`skills/harden/SKILL.md`): ao matar um mutante sobrevivente ou registrar um waiver.
- **review-report** (`skills/review-report/SKILL.md`): ao escrever o PR depois de `bob check`.
- **Pocock** (`skills/vendor/mattpocock/`): `grill-me` → `to-spec` → `to-tickets` → `implement-spec` / `tdd` → `code-review`. MIT: `NOTICE`.

## Verificar no Cloud Agent

Os workflows `.github/workflows/ci.yml` e `.github/workflows/bob.yml` são a fonte destes passos. O CI usa Python 3.10 e 3.12 com Node 22.14.0.

1. Use Python 3.10 ou superior. Os testes de pacote criam venvs, então a imagem precisa do `python3-venv`.
2. Instale o pacote com `python -m pip install -e '.[dev]'`. Sem venv, o pip grava o `bob` em `~/.local/bin`. Ponha essa pasta no `PATH`.
3. Instale as ferramentas npm fixadas com `npm ci` na raiz.
4. Rode `bob doctor`. Ele lista cada ferramenta com a versão esperada e a encontrada. `bob doctor --install` roda `npm ci` dentro do pacote instalado e serve para quem instalou o wheel. Num checkout editável, ele cria `src/bob_quality/node_modules`. O mutmut copia essa pasta sem os links de `.bin` e o teste `test_mutmut_dogfood.py` falha. Apague essa pasta antes do `pytest`.
5. Rode `python -m pytest`. A suíte inteira leva cerca de 12 minutos, porque o dogfood do mutmut gera `mutants/`.
6. Rode `bob check --base origin/main --gates crap,dry,deps,mutate`, como no CI. Sem `--gates`, o padrão é `crap,dry,deps`. O `mutate` roda a suíte como baseline e leva mais de 10 minutos. O relatório fica em `.bob/report.md` e `.bob/report.json`.

Gates:

- `crap` bloqueia função alterada com CRAP acima de `crap.max_per_function` no `bob.yaml`.
- `dry` só avisa sobre clones novos no diff e nunca muda o exit code.
- `deps` bloqueia ciclo de dependência ou violação de regra que toque o diff.
- `mutate` bloqueia mutante sobrevivente sem waiver em `.bob/waivers.yaml`.

Exit codes do `bob check`. Com vários gates, vale o maior:

- `0`: todos os gates pedidos passaram.
- `1`: um gate falhou, por exemplo CRAP acima do limite ou ciclo no diff.
- `2`: o baseline quebrou, ou seja, os testes falham antes da mutação.
- `3`: sobrou mutante sem waiver.
- `4`: a configuração é inválida ou falta uma ferramenta.

A SPEC completa da CLI fica em `docs/SPEC.md`.
