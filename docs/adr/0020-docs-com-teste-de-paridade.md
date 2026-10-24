# Docs com teste de paridade de versões

Status: aceita pelo Emerson em 18/10/2026, na aprovação do desenho da aplicação. Publicada em `docs/adr/` na U9.

## Contexto

Divergências 2 a 7 do 2.1 (`technology-stack.md`). FR8.1–FR8.3.

## Decisão

- Caminho principal nos READMEs e docs: o `curl ... | sh`, depois `bob update` e `bob --version`. O caminho com clone vira seção "Desenvolvimento".
- Requisitos: Python e Node com as faixas reais; gitleaks vem pelo comando; `python3-venv` no Ubuntu.
- `tests/test_docs_pins.py`: toda ocorrência `nome==x` ou `nome@x` ou "nome x.y.z" de uma ferramenta pinada nos docs listados em C12 bate com `pyproject.toml`/`package.json`. Também confere que a lista de ferramentas nos docs é completa.

## Alternativas

Gerar os trechos de docs (mais tooling); revisão manual (é como divergiu).

## Consequências

Bump de dependência passa a exigir doc certa, ou o teste falha.
