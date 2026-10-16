# Contribuição

[Índice](README.md) · [Instalação](getting-started/installation.md) · [SPEC](architecture/spec.md) · [Changelog](changelog.md)

Não há `CONTRIBUTING.md` neste repositório. O que segue é o que o [AGENTS.md](https://github.com/fazedordecodigo/bob/blob/main/AGENTS.md), os workflows e o [SPEC.md](SPEC.md) já pedem de quem altera o código. A licença é MIT (`LICENSE`, copyright 2026 Emerson Delatorre).

A spec diz que merge e publicação em marketplace dependem da aprovação do Emerson. Publicação no PyPI e nos marketplaces está fora do que a `main` faz hoje. O workflow `package` gera um sdist e um wheel, roda `twine check --strict dist/*` e roda `bob doctor`. Ele não publica.

## Ambiente

Os passos do [AGENTS.md](https://github.com/fazedordecodigo/bob/blob/main/AGENTS.md), alinhados com `.github/workflows/ci.yml` e `.github/workflows/bob.yml`:

1. Python 3.10 ou mais novo. O CI roda 3.10 e 3.12. A imagem precisa do `python3-venv`.
2. Node `>=22.18.0 <23`, a faixa que o `bob doctor` aceita. O Node 20, o Node 24 e um sufixo `-rc` saem com `4`. O CI instala 22.18.0.
3. `python3 -m venv .venv && . .venv/bin/activate`.
4. `python -m pip install -e '.[dev]'`.
5. `npm ci` na raiz.
6. `bob doctor`. Ele sai com `0` só quando toda ferramenta bate com o pin dela. Num checkout editável, `bob doctor --install` instala na raiz, no mesmo lugar que `npm ci`. Apague `src/bob_quality/node_modules` se um `--install` antigo o criou. Esse diretório quebra `tests/test_mutmut_dogfood.py`.
7. `python -m pytest`. A suíte leva vários minutos. O dogfood do mutmut gera `mutants/`.
8. `bob check --base origin/main --gates crap,dry,deps,mutate`, como o CI faz. Sem `--gates`, o padrão é `crap,dry,deps`. O relatório é `.bob/report.md` e `.bob/report.json`.

## O que os testes cobrem

A spec pede testes pelo comportamento externo. A suíte é `tests/`.

- `tests/test_cli.py`, `test_ts_cli.py`, `test_mixed_cli.py`, `test_deps_cli.py`, `test_language_cli.py`, `test_invalid_config.py`: a CLI em fixtures e em config inválida.
- `tests/fixtures/python_app`, `ts_app` e `mixed_app`: repositórios mínimos. `tests/fixtures/raw` guarda saída das ferramentas pinadas.
- `tests/test_crap.py` e o núcleo: fórmula, limite, delta.
- `tests/test_adapters.py` e os testes de deps: adaptadores contra um fixture gravado.
- `tests/test_mutate.py`, `test_no_coverage.py`, `test_mutmut_dogfood.py`: mutação, a falha `no_coverage` e o pacote sob o mutmut.
- `tests/test_skills_contract.py`: as skills listadas nos dois manifestos.
- `tests/test_hook.py`: o hook de pre-push termina em menos de 60 segundos no fixture.

A spec diz que a implementação do plugin é feita com TDD. Um teste de paridade em `messages.py` exige as mesmas chaves e os mesmos placeholders em `en` e `pt-BR`.

## Skills que o repositório pede ao agente

O [AGENTS.md](https://github.com/fazedordecodigo/bob/blob/main/AGENTS.md) aponta três skills:

- `skills/bob-check/SKILL.md`: rode `bob check`, leia o JSON, itere até o exit `0`.
- `skills/harden/SKILL.md`: mate um mutante sobrevivente ou registre um waiver. Não enfraqueça código de produção para matar um mutante.
- `skills/review-report/SKILL.md`: resuma o relatório no corpo do pull request, no formato Summary / Evidence / Merge Danger.

`bob report` está implementado. A interface está na [CLI](reference/cli.md#bob-report). As skills ainda apontam para `docs/exit-codes.md#exit-4` no uso inválido da CLI.

## Onde mudar as coisas

| Mudança | Lugar |
|---|---|
| Fórmula, limite, veredito | `src/bob_quality/core.py`, `crap.py` |
| Um gate | o `*_gate.py` correspondente, ou `mutate.py` |
| Uma ferramenta externa | `src/bob_quality/adapters/` |
| Texto para humanos | `src/bob_quality/messages.py` (os dois idiomas) |
| Config e waivers | `config.py`, `waivers.py` |
| Relatório | `report.py`, `schemas/report_v1.json` |
| Códigos de saída | `exit_codes.py` |
| Skills do plugin | `skills/*/SKILL.md` e a lista em `.claude-plugin/plugin.json` e `.cursor-plugin/plugin.json` |

A spec pede que uma linguagem nova entre por um adaptador, sem mudar o núcleo. Os probes concretos hoje são `python_probe.py` e `typescript_probe.py`. Uma lista `languages` explícita é mantida como foi escrita. Uma chave omitida ou nula é detectada. Ver [Schema de configuração](reference/configuration.md#linguagens-e-caminhos).

## Documentação

Os guias neste diretório descrevem comportamento conferido contra o código. [SPEC.md](SPEC.md) permanece a spec aprovada. Quando o comportamento muda, atualize o guia correspondente e, quando a mudança é comportamento de produto, os dois READMEs e o [CHANGELOG.md](https://github.com/fazedordecodigo/bob/blob/main/CHANGELOG.md). Cada nota do changelog está em inglês e em português. Não mude o texto de decisão de um ADR existente, e não edite `SPEC.md`, sem a aprovação do Emerson.
