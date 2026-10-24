# `bob doctor` confere só as ferramentas do bob

Status: aceita pelo Emerson em 18/10/2026, na aprovação do desenho da aplicação. Publicada em `docs/adr/` na U9.

## Contexto

O doctor procura npm primeiro em `Path.cwd()/node_modules` (`doctor.py:358-360`) e binários em `Path.cwd()/node_modules/.bin` (`doctor.py:437-441`). Num projeto com vitest próprio, ele compara a versão do projeto (FR2.5).

## Decisão

- npm: só o prefixo do plugin (`npm_prefix()`), por `package.json` do pacote em `node_modules/<nome>`. Sem `cwd` e sem executável no `PATH`.
- Binários (gitleaks): `BOB_HOME/bin`, depois `PATH`.
- Python: sem mudança (lê do próprio venv).
- `--install`: npm e gitleaks.

## Alternativas

Manter o `cwd` como fallback (é a causa do problema).

## Consequências

Quem rodava o bob num clone com `npm ci` na raiz segue funcionando: no checkout editável o prefixo é a raiz (`docs/instalacao.md:43`).
