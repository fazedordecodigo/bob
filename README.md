# bob

Quality gates (CRAP, DRY, mutação, dependências) + skills para agentes de codificação (Cursor, Claude Code, GitHub Copilot, Devin), inspirados no fluxo do Uncle Bob e nas skills do Matt Pocock.

- CLI: `bob` (`bob check | crap`; os demais comandos da spec entram nas fatias seguintes)
- Pacote PyPI: `bob-quality` (ainda não publicado)
- Nome nos marketplaces: `bob` (ainda não publicado)
- Configuração: `bob.yaml`
- Relatórios: `.bob/report.md` e `.bob/report.json` (schema v1)

> Status: fatia fina Python (issue #1) e GitHub Action (issue #5). Mutação, TypeScript e publicação ficam para os tickets seguintes.

Skills (issue #7):

- Fluxo de spec do Pocock (MIT, atribuído): `skills/vendor/mattpocock/`
- `skills/bob-check/` — quando e como rodar `bob check`
- `skills/review-report/` — resumir `.bob/report.md` no PR
- Índice para agentes: `AGENTS.md`

Licença: MIT.

## Instalação (desenvolvimento)

```bash
pip install -e ".[dev]"
```

Isso instala o comando `bob` e as dependências pinadas `lizard==1.24.1` e `coverage==7.16.2`.

## Uso

Num repositório Python com `bob.yaml` e pytest:

```bash
bob check --base main
bob crap --base main
```

Os dois gravem `.bob/report.md` e `.bob/report.json`. Exit codes desta fatia: `0` passou, `1` CRAP acima do limite numa função alterada, `2` testes da baseline falharam, `4` config/ferramenta.

Gate não executado (ex.: `dry`, `deps` no `check` padrão) aparece como ⏭️ com motivo, nunca como ✅. Só funções do diff bloqueiam; a dívida antiga vai para a seção informativa.

## Hook pre-push

O script `src/bob_quality/hooks/pre-push` roda `bob check --gates crap` (gate rápido, < 60 s no fixture):

```bash
cp src/bob_quality/hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## Testes

```bash
pytest
```

O repo-fixture está em `tests/fixtures/python_app` (caso que passa e caso que falha por CRAP > 10).

O CI (`.github/workflows/ci.yml`) roda essa suíte em pull requests e em pushes para `main`.

## GitHub Action

A action composta em `.github/actions/bob` instala o `bob`, roda `bob check` com `crap,dry,deps,mutate` (o que ainda não existe no CLI aparece como ⏭️), restaura e publica o artefato `bob-mutation-cache` (`.bob/mutation-cache.json`) e cria ou atualiza um único comentário no PR com `.bob/report.md`. O exit code do job é o do `bob`.

Este repositório a usa em `.github/workflows/bob.yml`. `bob-quality` ainda não está no PyPI: no checkout deste repo a action faz `pip install .[dev]`; em outro repo, instala o git da action. Publicação no Marketplace não faz parte desta fatia.
