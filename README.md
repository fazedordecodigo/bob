# bob

Quality gates (CRAP, DRY, mutação, dependências) + skills para agentes de codificação (Cursor, Claude Code, GitHub Copilot, Devin), inspirados no fluxo do Uncle Bob e nas skills do Matt Pocock.

- CLI: `bob` (`bob check | crap | dry`; os demais comandos da spec entram nas fatias seguintes)
- Pacote PyPI: `bob-quality` (ainda não publicado)
- Nome nos marketplaces: `bob` (ainda não publicado)
- Configuração: `bob.yaml`
- Relatórios: `.bob/report.md` e `.bob/report.json` (schema v1)

> Status: fatia fina Python (issue #1). Mutação, TypeScript, Action e publicação ficam para os tickets seguintes.

Skills (issue #7):

- Fluxo de spec do Pocock (MIT, atribuído): `skills/vendor/mattpocock/`
- `skills/bob-check/` — quando e como rodar `bob check`
- `skills/review-report/` — resumir `.bob/report.md` no PR
- Índice para agentes: `AGENTS.md`

Licença: MIT.

## Instalação (desenvolvimento)

```bash
pip install -e ".[dev]"
npm ci
```

Isso instala o comando `bob`, as dependências pinadas `lizard==1.24.1` e `coverage==7.16.2`, e as ferramentas npm pinadas (`c8`, `vitest`, `jscpd`).

## Uso

Num repositório Python com `bob.yaml` e pytest:

```bash
bob check --base main
bob crap --base main
bob dry --base main
```

Os comandos gravam `.bob/report.md` e `.bob/report.json`. Exit codes desta fatia: `0` passou, `1` CRAP acima do limite numa função alterada, `2` testes da baseline falharam, `4` config/ferramenta.

`bob dry` lista clones novos (aviso) e não muda o exit code. Gate não executado (ex.: `deps` no `check` padrão) aparece como ⏭️ com motivo, nunca como ✅. Só funções do diff bloqueiam; a dívida antiga vai para a seção informativa.

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
