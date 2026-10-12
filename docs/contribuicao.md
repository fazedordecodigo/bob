# Contribuição

[Índice](README.md) · [Instalação](instalacao.md) · [Visão geral](visao-geral.md) · [SPEC](SPEC.md)

Não há um `CONTRIBUTING.md` neste repositório. O que segue é o que [AGENTS.md](../AGENTS.md), os workflows e a [SPEC](SPEC.md) já pedem de quem altera o código. A licença é MIT (`LICENSE`, copyright 2026 Emerson Delatorre).

A spec diz que merge e publicação em marketplace dependem da aprovação do Emerson (história 19 e critério 12). Publicação no PyPI e nos marketplaces está fora do que a `main` faz hoje. Ver [Visão geral](visao-geral.md#o-que-a-main-já-faz).

## Ambiente

Os passos do [AGENTS.md](../AGENTS.md), alinhados a `.github/workflows/ci.yml` e `.github/workflows/bob.yml`:

1. Python 3.10 ou superior. O CI roda 3.10 e 3.12. A imagem precisa de `python3-venv`.
2. Node 22.14.0, a versão exata que `bob doctor` exige.
3. `python3 -m venv .venv && . .venv/bin/activate`.
4. `python -m pip install -e '.[dev]'`.
5. `npm ci` na raiz.
6. `bob doctor`. Sai com `0` só quando cada ferramenta coincide com o pino. `bob doctor --install` num checkout editável cria `src/bob_quality/node_modules` e o teste `tests/test_mutmut_dogfood.py` falha ([#34](https://github.com/fazedordecodigo/bob/issues/34)). Apague essa pasta antes do pytest.
7. `python -m pytest`. A suíte leva vários minutos: o dogfood do mutmut gera `mutants/`.
8. `bob check --base origin/main --gates crap,dry,deps,mutate`, como o CI. Sem `--gates`, o padrão é `crap,dry,deps`. O relatório fica em `.bob/report.md` e `.bob/report.json`.

O workflow `package.yml` gera sdist e wheel (`python -m build`), roda `twine check --strict dist/*` e `bob doctor`. Não publica.

## O que os testes cobrem

A spec pede teste pelo comportamento externo. A suíte está em `tests/`.

- `tests/test_cli.py`, `test_ts_cli.py`, `test_mixed_cli.py`, `test_deps_cli.py`, `test_language_cli.py`, `test_invalid_config.py`: a CLI sobre fixtures e sobre config inválida.
- `tests/fixtures/python_app`, `ts_app` e `mixed_app`: repositórios mínimos. `tests/fixtures/raw` guarda saída das ferramentas pinadas.
- `tests/test_crap.py` e o núcleo: fórmula, limiar, delta.
- `tests/test_adapters.py` e os testes de deps: adaptadores contra fixture gravada.
- `tests/test_mutate.py`, `test_no_coverage.py`, `test_mutmut_dogfood.py`: mutação, aviso de `no_coverage` e o próprio pacote sob mutmut.
- `tests/test_skills_contract.py`: as skills listadas nos dois manifestos.
- `tests/test_hook.py`: o pre-push termina em menos de 60 s no fixture.

A spec diz que a implementação do plugin é feita com TDD. Um teste de paridade em `messages.py` exige as mesmas chaves e os mesmos placeholders em `en` e `pt-BR` (decisão 12 da spec).

## Skills que o repositório pede ao agente

[AGENTS.md](../AGENTS.md) aponta três skills:

- `skills/bob-check/SKILL.md`: rodar `bob check`, ler o JSON, iterar até exit `0`.
- `skills/harden/SKILL.md`: matar mutante sobrevivente ou registrar waiver. Não enfraquecer código de produção para matar mutante.
- `skills/review-report/SKILL.md`: resumir o relatório no corpo do PR, no molde Summary / Evidence / Merge Danger.

Essas skills citam a interface da spec, inclusive `bob report`, que a CLI ainda não implementa. O comportamento executável está em [CLI](cli.md).

## Onde mexer

| Mudança | Lugar |
|---|---|
| Fórmula, limiar, veredito | `src/bob_quality/core.py`, `crap.py` |
| Um gate | `crap_gate.py`, `dry_gate.py`, `deps_gate.py`, `mutate.py` |
| Ferramenta externa | `src/bob_quality/adapters/` |
| Texto para humanos | `src/bob_quality/messages.py` (os dois idiomas) |
| Config e waivers | `config.py`, `waivers.py` |
| Relatório | `report.py`, `schemas/report_v1.json` |
| Exit codes | `exit_codes.py` |
| Skills do plugin | `skills/*/SKILL.md` e a lista em `.claude-plugin/plugin.json` e `.cursor-plugin/plugin.json` |

A spec pede que uma linguagem nova entre por adaptador, sem mudar o núcleo. Hoje os probes concretos são `python_probe.py` e `typescript_probe.py`, e `languages` é uma lista explícita. Ver a nota em [languages](configuracao.md#languages).

## Documentação

Os guias desta pasta descrevem o comportamento conferido no código. [SPEC.md](SPEC.md) é a spec aprovada e permanece a referência do que foi decidido, inclusive do que ainda não está na CLI. Ao mudar comportamento, atualize o guia correspondente e, quando a mudança for de produto, o README nos dois idiomas e o `CHANGELOG.md`, que hoje traz cada nota em inglês e em português.
