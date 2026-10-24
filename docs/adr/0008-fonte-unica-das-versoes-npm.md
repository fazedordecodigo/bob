# Fonte única das versões npm (P1)

Status: aceita pelo Emerson em 18/10/2026, na aprovação do desenho da aplicação. Publicada em `docs/adr/` na U9.

## Contexto

- Hoje a versão do vitest está em três lugares: `package.json:15` (5.0.5), `src/bob_quality/doctor.py:70` (5.0.4) e `tests/test_npm_pin.py:30` (5.0.4).
- O bump do Dependabot (#180, `d2e26bd`) mudou só o `package.json` e o lock. O `bob doctor` saiu `4` no workflow `package` (run 39159800688, 2026-10-18 16:41 UTC-3).
- A faixa do Node também se repete: `package.json:6` e `doctor.py:62`.

## Decisão

- O `package.json` empacotado é a fonte única das versões npm e da faixa do Node.
- O doctor lê `dependencies` (exigindo `x.y.z`) e `engines.node` (exigindo `>=A.B.C <N`) do `package.json` do prefixo do plugin (`npm_prefix()`).
- `PINS` do doctor guarda só nome exibido, executável e pacote npm. Sem versão.
- `tests/test_npm_pin.py` deixa de ter a lista fixa. Confere: todo spec é `x.y.z`; o lock (`packages["node_modules/<n>"].version`) bate com o spec; o `package.json` da raiz e o do pacote são o mesmo.
- O `install.sh` repete as faixas de Python e Node (é shell, não lê o pacote antes de instalar). Um teste confere paridade com `pyproject.toml` e `package.json`.
- Correção imediata de P1: com a ADR, o doctor passa a esperar 5.0.5 sem editar número nenhum.

## Alternativas

- Doctor ler o `package-lock.json`: o lock tem a versão resolvida, mas mistura dependências transitivas. O `package.json` exato basta e o teste garante o lock igual.
- Só alinhar o número no doctor: resolve hoje e quebra no próximo bump.
- Gerar `doctor.py` no build: mais peças, sem ganho.

## Consequências

- Um bump do Dependabot passa a exigir só `package.json` e lock. O teste de paridade pega lock divergente.
- Erro de leitura do `package.json` vira `4` com mensagem que cita o arquivo.
