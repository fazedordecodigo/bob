# U6 — Desenho dos NFR (3.3 leve)

| Id | Como o desenho atende | Onde se prova |
|---|---|---|
| U6-N1 | A linha usa `$HOME` sem expandir na escrita (aspas simples em `PROFILE_LINE`). O shell do dev a expande ao ler, então vale para qualquer `HOME`. | passo 13 (sourcing com `env -i`) |
| U6-N2 | `grep -qF "$_mark"` antes de qualquer escrita. A marca sai de `PROFILE_LINE`, sem 2º literal. | passo 13; `test_second_run_is_already_marked` |
| U6-N3 | Só `>>` (append). O `\n` antes da linha sai de `tail -c 1`. Nunca reescreve o arquivo. | `test_profile_append_keeps_the_bytes[no-newline/newline]` |
| U6-N4 | Toda escrita fica num grupo `{ …; } 2>"$work/perfil.err" >>"$_pf"`. Falha vira resultado, nunca `fail`. | `test_unwritable_profile_warns_and_exits_0[en/pt-BR]`; passo 13 (e) |
| U6-N5 | Só `grep`, `tail`, `chmod`, `printf` e redirecionamento, todos dentro do `HOME`. | `_ALLOWED` do teste (lista fechada de ferramentas) |
| U6-N6 | `_profile_text` é pura e recebe o valor. Os textos vêm do catálogo (CT1), com o mesmo formato de `setup.preserved`. | testes da T2 |
| U6-N7 | `BOB_HOME` compartilhado com o passo 2: o `pacote` reusa o venv (`.complete` igual) e o `bob setup` acha o npm e o gitleaks prontos. Na U5, o passo 7 reusando levou 1 s. | job `verify-install / linux-x64` |
| U6-N10 | A guarda roda `-k "hook or profile"`. Os testes novos da T2 têm `profile` no nome e não abrem socket (só `monkeypatch.setenv`). | `tests/test_hermetic.py` |
