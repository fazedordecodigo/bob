# Geração do `bob.yaml` e regra de `paths.include`

Status: aceita pelo Emerson em 18/10/2026, na aprovação do desenho da aplicação. Publicada em `docs/adr/` na U9.

## Contexto

FR4.1–FR4.5, RE-Q2 B. O padrão `include: [src]` sai `4` num projeto sem `src/` (`config.py:428-434`). A detecção de linguagem existente usa os sufixos de `_SUFFIX_LANGUAGE` e `_excluded` (`config.py:320-326`, `:387-425`).

## Decisão — conteúdo

- Chaves e valores do README (`README.pt-BR.md:182-203`): `base: origin/main`, `language: en`, `paths.exclude: [tests, node_modules, dist]`, `crap`, `duplication`, `coverage`, `dependencies`.
- A chave `languages` não é gravada. Omitida, ela é detectada, que é o padrão documentado (`README.pt-BR.md:180`).
- `paths.include`: regra abaixo.

## Decisão — regra exata de `paths.include`

1. Arquivos candidatos: saída de `git ls-files --cached --others --exclude-standard` (rastreados e não ignorados). Assim `node_modules`, `.venv` e afins ignorados pelo `.gitignore` ficam fora.
2. Arquivo de código: sufixo em `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs` (os mesmos de `_SUFFIX_LANGUAGE`). Symlinks não contam.
3. Descarta todo arquivo cujo caminho casa com `paths.exclude` padrão, pela mesma função `_excluded` (prefixo ou componente).
4. Pastas candidatas: o primeiro componente do caminho de cada arquivo que sobrou. Pastas que começam com `.` não contam.
5. Se `src` está entre as candidatas: `include: [src]` (o padrão do README).
6. Senão, se há candidatas: todas, em ordem alfabética.
7. Senão, se há arquivo de código na raiz: `include: ["."]`.
8. Senão (nenhum código): `include: ["."]` e aviso "nenhuma pasta de código encontrada" no resumo (FR4.5).

## Decisão — validação

- Gera o texto, grava num temporário no projeto, chama `load_config(temp, cwd)`. Passa por `config.py:428-434` porque toda pasta listada veio de arquivos que existem, e `.` sempre existe.
- `ConfigError` aqui é bug: não grava `bob.yaml`, sai `4` com a mensagem do erro.
- Só então rename atômico para `bob.yaml`.

## Alternativas

Listar todas as pastas com código mesmo com `src/` (aumenta o escopo do gate em relação ao padrão); varrer o disco sem `git` (pega `node_modules` e `.venv` não excluídos).

## Consequências

- `include: ["."]` com o resto do padrão: aceito por `load_config`. Medido em 2026-10-20 (passo 0 da T2, PR #196, `main` @ `0d85510`): sem código, `crap` e `coverage` saíam `4` (`coverage.py: No data to report.`); `dry` e `deps` saem `0`. Decisão do Emerson (Q1 = A, 2026-10-20 21:18 UTC-3): sem código a medir, `crap` e `coverage` ficam ⏭️ `not_run` com o motivo "no code to measure" / "nenhum código a medir" e contribuem `0` (T1b). "Sem código" = `config.detect_languages(cwd, include, exclude)` vazio (mesmos sufixos e exclusão desta ADR, sem seguir symlink). Com código, erro de coverage segue `4`.
  - Emenda E1 (T1b), aprovada pelo Emerson em 2026-10-20 21:42 UTC-3 ("Aprovo a T1b e as emendas E1 a E3, com a T1c separada para a E4."); origem: Q1 = A e `construction/u4-bob-yaml/code-generation/tasks/T1b-emenda.md`.
- `base: origin/main` não é adaptado. Projeto com outra branch padrão mantém o padrão do README (FR4.2).
