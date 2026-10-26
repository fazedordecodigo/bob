# U3 — Desenho dos NFR (3.3 leve)

| NFR | Como o desenho atende | Como se prova |
|---|---|---|
| U3-N1 | Um download (~7 MB do espelho local; do GitHub no modo remoto), sha em streaming, extração de um membro. Nenhum build. | Harness passo 2: `tempo ≤ 300` (já existente; agora com o gitleaks dentro). |
| U3-N2 | `ensure_gitleaks` só cria `tools/` depois de `sha256` e extração no temporário (fluxo, etapas 4–7). | `test_gitleaks.py::test_tampered_archive_fails_integrity_and_installs_nothing`, `::test_ensure_installs_the_binary_and_the_link`. |
| U3-N3 | Integridade e extração rodam no `TemporaryDirectory`; erro de sha não tem retry (R9). | Harness passo 9a (exit 4, stderr, `tools/gitleaks` ausente, 1 GET). Mesmo teste de U3-N2. |
| U3-N4 | `installed_version(home) == VERSION` antes de qualquer rede (R7). O passo do `bob setup` nem chama `ensure_gitleaks` quando já está ok. | Harness passo 7 (0 GETs `/gitleaks/`, mtime igual). `test_second_ensure_downloads_nothing`, `test_setup_cmd.py::test_gitleaks_step_is_unchanged_when_present`. |
| U3-N5 | Reuso custa um `gitleaks --version`. | Harness passo 7: `tempo ≤ 60`. |
| U3-N6 | `ASSETS` literal com os 4 pares do CT9/ADR 0014. | `test_assets_are_the_four_adr_0014_entries`; `test_platform_key_maps_the_ct9_table` (6 casos). |
| U3-N7 | `doctor.py` deriva o `BinaryPin` de `gitleaks.ASSETS`/`asset_url`; o harness mantém a cópia dele, conferida por teste. | `rg -l -F` dos 4 sha em `src/` → só `src/bob_quality/gitleaks.py` (comando nas ETs T1 e T2); `test_verify_install.py::test_gitleaks_constants_match_the_gitleaks_table`. |
| U3-N8 | Todas as mensagens no catálogo; `test_messages.py` já confere as mesmas chaves e placeholders nos dois idiomas. | `test_gitleaks_messages_exist_in_both_languages` (6 chaves), `test_setup_cmd.py::test_setup_messages_exist_in_both_languages` (+1), `test_doctor_install_gitleaks_failure_exits_4[en,pt-BR]`. |
| U3-N9 | `_TIMEOUT_S = 30`, `_ATTEMPTS = 3`, `_PAUSE_S = 1.0`; `HTTPError` < 500 sai na hora. | `test_download_uses_a_30_s_timeout`, `test_http_4xx_is_not_retried[404,429]`, `test_5xx_is_retried_twice`, `test_network_error_is_retried_twice`. Harness passo 2 (`mirror.log` exato). |
| U3-N10 | `TemporaryDirectory` como gerenciador de contexto; limpeza de `*.tmp` e de `tools/gitleaks` novo em `OSError` (R6). | `test_write_error_leaves_nothing_in_tools`; todos os testes de falha conferem `tools/gitleaks` ausente e nenhum `bob-gitleaks-*` no `TMPDIR`. |
| U3-N11 | `tool_path` sem `fixture-bin`; `run_oneliner` falha se `command -v gitleaks` acha algo no `PATH` do passo. | Harness (todos os passos); `test_verify_install.py::test_harness_has_no_gitleaks_fixture`. |
| U3-N12 | Tudo em `BOB_HOME`; nada de `sudo`. | Harness passo 3. |
| U3-N13 | +1 instalação completa (9a, até o passo `gitleaks`); o cache do tar.gz continua. | Medido no PR da T3 (`time sh scripts/verify-install.sh`) e no job `verify-install / linux-x64`. Não verificado até lá. |
| U3-N14 | Sem bashismos nas funções novas. | `test_verify_install.py::test_verify_install_is_posix`. |
| U3-N15 | Funções pequenas (download, sha, extração, instalação, link separados; CCN ≤ 5 previsto). Só stdlib. | Checks do PR; `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → 0. |
| U3-N16 | Nenhum segredo; nenhum token (CT14). | gitleaks do CI. |
| U3-N17 | Servidor HTTP local em thread e tar.gz sintético (script `gitleaks` de shell), `ASSETS` e `platform_key` trocados por `monkeypatch`. | Critério de aceite da T1: toda chamada a `ensure_gitleaks` nos testes usa `BOB_GITLEAKS_BASE_URL=http://127.0.0.1:<porta>` ou um `urlopen` trocado por `monkeypatch`; `rg -n "https://" tests/test_gitleaks.py` só acha a linha do teste de `DEFAULT_BASE_URL` e os casos de `base_url`. |
