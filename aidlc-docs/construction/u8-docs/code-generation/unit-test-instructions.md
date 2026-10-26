# U8 — Instruções de testes unitários

**Despacho só depois dos merges da U6 e da U7.** As contagens supõem a `main` com a U6 e a U7 inteiras.

## Preparação
- Python 3.10+ com `pip install -e '.[dev]'` (como no CI). `/bin/sh` POSIX e `dash` (o teste usa `dash -n` quando ele existe).
- Node `>=22.18.0 <23` e `npm ci` em `website/` para o build do site (T1–T3).
- Rede: não precisa nos testes. O harness (passo 14) usa o espelho local e o índice de pacotes, como o passo 2.
- `tests/test_docs_pins.py` só lê arquivos do repo e roda `sh`/`dash` locais.

## Comando por tarefa
| Tarefa | Comando | Esperado |
|---|---|---|
| T1 | `python -m pytest -q tests/test_docs_pins.py tests/test_hermetic.py` | exit 0; `25 passed` (19 + 6) |
| T2 | o mesmo | exit 0; `53 passed` (47 + 6) |
| T3 | o mesmo | exit 0; `75 passed` (69 + 6) |
| T4 | `python -m pytest -q tests/test_verify_install.py` e `sh scripts/verify-install.sh --only 14` | exit 0; `54 passed`; harness com `… passo 14: tempo <s> s` (≤ 360) e `… passo 14: ok` |
| T1–T3 | `cd website && npm ci && npm run build && npm test` | exit 0 |

## Hermeticidade (U5-N16)
- `python -m pytest -q tests/test_hermetic.py` → exit 0, com `test_u5_tests_open_no_network[tests/test_docs_pins.py]`.
- Medida manual: `BOB_NET_GUARD_LOG=$(mktemp) PYTHONPATH=tests/net_guard python -m pytest -q -p no:cacheprovider tests/test_docs_pins.py` → exit 0, com o log de 0 bytes.

## Regressão
- `python -m pytest -q` → exit 0, `0 failed`, sem `error`, em toda tarefa.
- `tests/test_verify_install.py`: os 46 casos existentes passam com A1–A5 da T4. A4 e A5 mantêm as saídas esperadas da U6 e da U7.
- Harness inteiro no check `verify-install / linux-x64`: 14 linhas `ok` na T1, na T2 e na T3; 15 a partir da T4.

## Comando de Verificação (subconjunto U8)
- **Passo 14:** `sh scripts/verify-install.sh --only 14` → `ok 14`. Cobre a instalação A, a instalação B com 4 pedidos exatos ao espelho e 0 de `install.sh`, `sudo.log` vazio, manifesto igual e B2 com 2 `reused`.
- **`VERIFY_REMOTE=1`:** o passo 14 imprime "não se aplica (VERIFY_REMOTE=1)" e sai 0.

## Metas
- `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` → exit 0, com 0 waivers novos.
- `src/` não muda: sem mutante novo; a cobertura global fica ≥ 80,0.
- `website / build` verde na T1, na T2 e na T3.

## Mapa pronto → teste
| Pronto | Teste |
|---|---|
| Docs começam pelo comando único (FR8.1) | `test_install_docs_start_with_the_one_liner[4]`, `test_agent_and_hook_docs_start_with_the_one_liner[4]` |
| Requisitos reais (FR8.2) | `test_install_docs_cite_the_pinned_requirements[4]`, `test_docs_cite_only_the_pinned_versions[8]` |
| Atualizar e ver a versão (FR8.3) | `test_update_section_shows_update_and_version[4]` |
| Principal e alternativa (FR8.4, CT17) | `test_alternative_comes_after_the_one_liner_once[4]`, `test_alternative_links_the_prompt_in_the_doc_language[4]` |
| Paridade do prompt (FR8.5, CT18) | os 13 testes da T1 |
| Sem clone nem plugin (FR1.2, FR1.3) | `test_no_clone_or_plugin_before_the_one_liner[8]`, `test_agents_doc_names_the_single_folder_and_ra1[2]` |
| Mesmo resultado sem `install.sh` (NFR10, NFR11) | passo 14 |
