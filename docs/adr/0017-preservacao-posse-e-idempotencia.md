# Preservação, posse e idempotência

Status: aceita pelo Emerson em 18/10/2026, na aprovação do desenho da aplicação. Publicada em `docs/adr/` na U9.

## Contexto

I-S2, R-S3 (preservar e avisar, sem perguntar), FR3.4, FR6.3, NFR4, NFR5.

## Decisão

- O bob só escreve no que é dele: pasta de skill com `.bob-version`, hook com `# managed-by: bob-quality`, `bob.yaml` que ele cria quando não existe.
- Nunca escreve em `bob.yaml` existente, `.bob/waivers.yaml`, hook alheio, skill sem marcador, manifestos e lockfiles do projeto.
- Toda escrita compara antes. Igual: não escreve. Segunda execução seguida: 0 arquivos alterados.
- Todo item preservado entra no resumo, com o motivo.
- Escritas por arquivo temporário + rename.

## Alternativas

Manifesto de instalação único em `.bob/` (mais um arquivo e estado a reconciliar); comparar com hash de versões conhecidas (exige tabela de hashes por release).

## Consequências

Uma skill do bob editada à mão pelo dev (com marcador) é sobrescrita na atualização. O resumo avisa. A marca está documentada.
