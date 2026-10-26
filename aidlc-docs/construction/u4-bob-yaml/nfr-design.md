# U4 — Desenho dos NFR (3.3 leve)

| NFR | Como o desenho atende | Como se prova |
|---|---|---|
| U4-N1 | `include` só lista pastas de arquivos que existem (R3), e `.` sempre existe. Assim o `load_config` passa por `config.py:428-434` (`include_missing`) e o `dry` acha as raízes (`dry_gate.py:139-142`). | Harness passo 5 (3 `bob check` ≠ 4). `test_init_config.py::test_generated_files_pass_load_config`. E2e da T2 (os 3 códigos colados). |
| U4-N2 | R4 + R5 sobre a lista do git (R2). | Passo 5 (`cmp` com `expected_bob_yaml`); `test_write_creates_src_when_src_has_code`, `test_write_lists_every_code_folder_in_code_point_order`, `test_no_code_is_dot_and_created_no_code`. |
| U4-N3 | Um template literal só (`render_config`), com 19 linhas do CT7; nenhuma chave vem de outro lugar. | `test_render_config_is_the_ct7_text` (3 casos); `test_verify_install.py::test_harness_expects_the_ct7_text` (paridade harness × `render_config`). |
| U4-N4 | `created_no_code` → `setup.warn_no_code` no `StepResult.warnings`; o `bob setup` imprime a linha do passo e a do resumo (CT3). | Passo 5; `test_setup_cmd.py::test_bob_yaml_step_no_code_warning_reaches_the_output[en,pt-BR]`. |
| U4-N5 | R1 (existir = do dev; 0 leituras) e R8 (waivers só por existência). | Passo 8 (sha dos dois + 2 linhas `  preserved:`); `test_existing_bob_yaml_is_preserved[file,link,dir]`; `test_bob_yaml_step_lists_existing_waivers`. |
| U4-N6 | A 2ª execução cai em R1. | Passo 7 (`digest` igual + linha `  preserved: bob.yaml …`); `test_second_write_is_preserved_and_changes_nothing`. |
| U4-N7 | R7: temporário no projeto (mesmo sistema de arquivos do destino), `os.replace` atômico, `unlink` em qualquer exceção. | `test_config_error_removes_the_temporary`, `test_rename_error_removes_the_temporary`, `test_write_error_leaves_no_temporary`. |
| U4-N8 | R1 roda antes de qualquer outra coisa. | `test_existing_bob_yaml_is_preserved` (git e `load_config` trocados por funções que falham o teste; `bob.yaml` inválido continua igual). |
| U4-N9 | 6 chaves novas no catálogo, com texto exato nos dois idiomas em `_MESSAGES`. | `test_setup_cmd.py::test_setup_messages_exist_in_both_languages` (+12 casos). |
| U4-N10 | O passo 5 reaproveita o `BOB_HOME` do passo 2 (venv, npm e gitleaks já prontos: só skills, `bob.yaml` e doctor rodam). | Medido no PR da T3 e no job `verify-install / linux-x64`. Não verificado até lá. |
| U4-N11 | +3 reexecuções curtas e 3 `bob check` com `--base HEAD`. | Check `verify-install / linux-x64` da T3. |
| U4-N12 | Sem bashismos nas funções novas. | `test_verify_install.py::test_verify_install_is_posix`. |
| U4-N13 | Funções pequenas (existência, lista, escolha, texto, gravação), só stdlib + `config`/`yaml_text`/`suite_fingerprint`. Nenhuma dependência nova. | Checks do PR; `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → 0. |
| U4-N14 | Repositórios git criados em `tmp_path`; nenhum download. | Comando da T1 (`rg -n "https?://" tests/test_init_config.py` → exit 1); os testes da T2 usam `git_project` e `tmp_path`. |
