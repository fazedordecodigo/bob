# U1 — Desenho dos NFR (3.3 leve)

| NFR | Como o desenho atende | Como se prova |
|---|---|---|
| U1-N1 | Um venv, um `pip install` do wheel (dependências do PyPI), um `npm ci` com o lock empacotado. Sem build no cliente. | Harness passo 2: `elapsed ≤ 300` (relógio do `date +%s` antes e depois). |
| U1-N2 | `curl … | sh` faz tudo; `install.sh` termina com `exec bob setup`. | Harness passo 2 roda só o one-liner. |
| U1-N3 | Tudo em `$BOB_HOME` e `~/.local/bin`; `pip` só no venv; `npm ci --prefix` no pacote ou no cache do usuário (já existente). | Harness: `sudo` falso no `PATH` grava `sudo.log`; passo 3 confere 0 bytes. `tests/test_install_sh.py::test_install_sh_never_mentions_sudo` (`rg` no script). |
| U1-N4 | `.complete` = sha do wheel → reusa venv (CT5). Passo `npm` pula quando o prefixo já tem as versões pinadas. Skills: compara bytes e conjunto de caminhos; igual = 0 escritas. | Harness passo 7 (digest do projeto igual, `ls versions` = 1, `mtime` do `node_modules/.package-lock.json` do prefixo do bob igual). `test_project_skills.py::test_second_install_writes_nothing`. `test_setup_cmd.py::test_npm_step_skips_npm_ci_when_the_prefix_matches`. |
| U1-N5 | `install_project_skills` só toca pastas do manifesto com marcador. `bob setup` não abre `package.json` nem `node_modules` do projeto. O doctor já ignora o projeto (U2). | Harness passo 8 (sha256 antes = depois). `test_project_skills.py::test_foreign_folder_is_preserved_byte_for_byte`. |
| U1-N6 | `integridade` antes de `pacote`; o wheel vai para o temporário; `versions/<v>` só nasce em `pacote`. | Harness passo 9b. `test_install_sh.py::test_tampered_wheel_exits_4_and_creates_no_version`. |
| U1-N7 | Todas as mensagens Python no catálogo (`setup.*`, en e pt-BR, mesmos placeholders: `test_messages.py`). `install.sh` tem a função `say` com as duas línguas lado a lado. | Testes por idioma em `test_setup_cmd.py` e `test_install_sh.py` (tabelas das ETs T3 e T4). |
| U1-N8 | Ordem dos passos do CT2; `BOB_HOME` só é criado em `pacote`; temporário com `mktemp -d` no `TMPDIR`. | Harness passo 1. `test_install_sh.py::test_failed_prerequisite_writes_nothing` (parametrizado por passo). |
| U1-N9 | `install_project_skills` grava só em `.agents/skills`; cópia com `shutil.copy2` de arquivos regulares (sem `copytree` de symlink). | Harness passo 4. `test_project_skills.py::test_install_creates_only_agents_skills`. |
| U1-N10 | `plugin/` com symlinks para a raiz; `package-data` explícito. | `test_package.py::test_wheel_ships_the_plugin_skills_manifest_and_license`. Job `package / dist`. |
| U1-N11 | Sem bashismos; `set -u`; `main "$@"` na última linha. | `test_install_sh.py::test_install_sh_is_posix`, `test_verify_install.py::test_verify_install_is_posix`. |
| U1-N12 | Um build do wheel por execução; cache do tar.gz do gitleaks em `~/.cache/bob-verify-install`; npm reaproveita o cache do npm entre passos (mesmo `npm_config_cache` do runner). | Medido no PR da T5 (`time sh scripts/verify-install.sh`). Não verificado até lá. |
| U1-N13 | Mesmo que U1-N4 (nada reinstala). | Harness passo 7: `elapsed ≤ 60`. |
| U1-N14 | Funções pequenas por passo (CCN ≤ 6 previsto). `install_skills.py` só stdlib. | Checks do PR; `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → 0. |
| U1-N15 | Nenhum segredo; nenhum token lido (CT14). | gitleaks do CI. |
| U1-N16 | Linhas de fonte única no topo do `install.sh` (CT18 + `NODE_FLOOR`, `NODE_BELOW`, `PYTHON_FLOOR`); função `resolve_bob_home` isolada. | `test_install_sh.py::test_node_and_python_ranges_match_the_package` e `::test_bob_home_matches_user_dirs` (I9). |
| U1-N17 | Só `DEFAULT_API`/`DEFAULT_DOWNLOAD` ou `BOB_RELEASES_URL`; `pip` e `npm` usam os índices do dev. | Harness passo 2: `mirror.log` tem exatamente os GETs esperados. |
