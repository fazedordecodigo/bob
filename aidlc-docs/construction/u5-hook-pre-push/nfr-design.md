# U5 — Desenho dos NFR (3.3 leve)

| NFR | Como o desenho atende | Como se prova |
|---|---|---|
| U5-N1 | O hook chama o launcher estável por caminho absoluto (ADR 0013), com `bob` do `PATH` só como reserva; o `bob check` roda pelo venv do bob, sem ambiente ativo. | Passo 6 (push com `env -i HOME=$HOME PATH=/usr/bin:/bin`, remoto bare, `.bob/report.md`); e2e da T2; passo 0 da T3. |
| U5-N2 | Um template só, em bytes, montado de `HOOK_MARKER` e do caminho por `os.fsencode` (sem literal de codificação, sem mutante equivalente de `"utf-8"`); modo por uma constante `_MODE`. | `test_render_hook_is_the_ct10_text` (3 caminhos, inclusive com espaço e não ASCII); `test_hook_marker_is_line_2_of_the_template`; `test_install_creates_the_hook` (bytes e `S_IMODE == 0o755`); paridade harness × `render_hook`. |
| U5-N3 | O hook gerado é o mesmo comando do estático (H13), e `tests/test_hook.py` passa a instalá-lo com `install_hook(repo, Path(sys.executable).parent / "bob")`, o bob ao lado do Python que roda os testes. | `tests/test_hook.py` (6 testes existentes + `test_managed_hook_calls_the_bob_next_to_python`), no CI e no passo 12 (com o bob instalado pelo comando único). |
| U5-N4 | H5 e H6: link e não-arquivo nunca são lidos; arquivo só é do bob com a linha 2 exata. | Testes da T1 e da T2; passo 8. |
| U5-N5 | H3 antes de qualquer outra coisa (depois de H2): `core.hooksPath` com saída `0` encerra o passo. | Testes com `git config core.hooksPath` real em `tmp_path`; e2e da T2. |
| U5-N6 | H7 compara bytes e modo antes de gravar. | Testes da T1/T2; passo 7 (`digest` cobre `.git/hooks`; mtime do hook). |
| U5-N7 | H7: com a marca e diferente → grava o template. | `test_install_updates_a_bob_hook_that_differs`. |
| U5-N8 | H9: temporário na mesma pasta do destino, `os.replace` atômico, `unlink` em qualquer exceção. O nome do temporário é conferido por teste (mata o mutante do literal `".tmp-"`). | `test_write_error_leaves_no_temporary`, `test_temporary_is_next_to_the_hook`. |
| U5-N9 | H2 roda antes do git; H5 não lê. | Testes com `subprocess.run` e `Path.read_bytes` trocados por funções que falham o teste. |
| U5-N10 | 9 chaves novas no catálogo, texto exato nos dois idiomas. | `_MESSAGES` (+8 tuplas na T2); teste próprio de `git.command_failed` na T1. |
| U5-N11 | O passo 6 reaproveita o `BOB_HOME` do passo 2; o push só roda os 3 gates rápidos num projeto de 2 arquivos. | Medido no PR da T3. Não verificado até lá. |
| U5-N12 | O passo 12 reaproveita o venv do passo 2 (pacote e npm já prontos) e só instala o pin do pytest. | Medido no PR da T3. Não verificado até lá. |
| U5-N13 | +2 passos curtos. | Check `verify-install / linux-x64` da T3. |
| U5-N14 | Sem bashismos nas funções novas. | `test_verify_install_is_posix`. |
| U5-N15 | Funções pequenas (citar caminho, perguntar ao git, decidir, gravar), só stdlib + `messages`/`tools`. Nenhuma dependência nova. | Checks do PR; `bob check … crap,dry,deps,mutate,coverage` → 0. |
| U5-N16 | Guarda de rede carregada por `sitecustomize` em todo processo Python do pytest interno (inclusive subprocessos Python); grava cada tentativa e levanta `OSError`. O git dos testes só usa caminhos locais. O controle positivo prova que a guarda pega uma conexão. | `tests/test_hermetic.py` no CI (`pytest (3.10)`, `(3.12)`), com a contagem de linhas do log = 0. Limite declarado: processos não Python (git, node) não passam pela guarda; nos testes da U5 eles só tocam `tmp_path`. |
