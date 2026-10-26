# U8 — Desenho dos NFR (3.3, kind spec)

| NFR | Mecanismo |
|---|---|
| U8-N1, N3, N4 | O teste acha o 1º bloco de shell pela regex `^```(\w+)[^\n]*\n(.*?)^```$` (com `re.M \| re.S`) e a 1ª palavra em `{bash, sh, shell, console}`. Mede posições com `str.index` no texto do arquivo (comando único < título da alternativa < título de atualizar). |
| U8-N2 | O teste lê os pins pelas funções do pacote (`npm_tools.pinned_npm_versions`, `npm_tools.node_range`, `gitleaks.VERSION`) e o piso de `pyproject.toml` (`requires-python = ">=X.Y"`). Nenhum valor fica escrito no teste. |
| U8-N4, N9 | Link por arquivo, fixado na ADR 0028. A página pt-BR usa `/install-prompt.pt-BR.md`, que o Docusaurus resolve nos content paths. O teste resolve: com `/`, a partir de `docs/`; senão, a partir da pasta do arquivo. O `website / build` é o check que prova o site. |
| U8-N5, N6, N8 | Os 11 itens do CT18 viram testes de 1 caso (ou 1 por idioma). A extração usa só a regex do CT18. O `sh -n` e o `dash -n` rodam num `subprocess` local. |
| U8-N7, N10, N11 | Passo 14 com `npm_config_cache` fora do `HOME` (1 download do npm para A, B e B2). Pacote e gitleaks reusados em B2. O manifesto normaliza a linha `bob-quality @ file://…` do `pip freeze`, que muda com a pasta do wheel. |
| U8-N12 | `("tests/test_docs_pins.py",)` entra no `_UNIT_ARGS` da guarda (`tests/test_hermetic.py`), depois do item da U7 T2. |
| U8-N13 | Sem código em `src/`: os gates não têm linha nova. Shell e docs são provados por teste e pelo harness. |
