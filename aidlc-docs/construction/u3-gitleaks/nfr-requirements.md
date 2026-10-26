# U3 — Requisitos não funcionais (3.2 leve)

Só os NFR que tocam a U3, cada um com alvo numérico. Nenhuma meta existente do repo nem da U1 foi rebaixada (U1-N1, N3, N4, N12, N13 e N14 seguem valendo com o gitleaks dentro).

| ID | Requisito | Métrica | Alvo | Origem |
|---|---|---|---|---|
| U3-N1 | Tempo de instalação com gitleaks (NFR1, RE-Q1 A) | Wall clock do passo 2 do harness, já sem fixture (download do gitleaks dentro), Linux x64, espelho local | ≤ 300 s | NFR1, pronto 2, passo 2 |
| U3-N2 | Integridade do gitleaks (NFR6, FR2.3) | Downloads conferidos por sha256 antes de sair do temporário | 100% | NFR6, US1.3 crit. 1 |
| U3-N3 | Falha de integridade não instala (NFR6) | Com tar.gz +1 byte: exit; entradas em `BOB_HOME/tools/gitleaks`; `BOB_HOME/bin/gitleaks`; arquivos do projeto alterados; tentativas de download | `4`; 0 (a pasta não existe); não existe; 0; 1 | pronto 3, passo 9a, US1.3 crit. 2 |
| U3-N4 | 2ª execução não baixa (NFR4) | Pedidos `/gitleaks/` ao espelho no passo 7; `st_mtime_ns` do binário | 0; igual | pronto 4, passo 7 |
| U3-N5 | Leveza da 2ª execução | Tempo do passo 7 com o gitleaks já instalado | ≤ 60 s (= U1-N13) | U1-N13 |
| U3-N6 | Plataformas (NFR3) | Entradas da tabela com asset e sha256 da release oficial | 4 de 4 (linux/darwin × x64/arm64) | NFR3, ADR 0014, pronto 1 |
| U3-N7 | Fonte única (ADR 0014) | Arquivos de `src/` com qualquer dos 4 sha256 literais | 1 (`gitleaks.py`) | ADR 0014 |
| U3-N8 | Clareza de erro (NFR9) | Mensagens `gitleaks.*`, `setup.item_gitleaks`, `doctor.bob_home_relative` com teste exato em en e pt-BR | 100% (8 chaves × 2 idiomas) | NFR9, CT1 |
| U3-N9 | Rede (CT14) | Timeout por requisição; tentativas máximas em rede/`5xx`; tentativas em `4xx`; hosts no modo espelho além de `127.0.0.1`, PyPI e npm | 30 s; 3; 1; 0 | CT14 |
| U3-N10 | Atomicidade | Depois de qualquer `GitleaksError`: arquivos `*.tmp` em `BOB_HOME`; pastas `bob-gitleaks-*` no `TMPDIR`; `tools/gitleaks` criado pela chamada | 0; 0; 0 | CT9 |
| U3-N11 | Sem fixture | Diretórios do `PATH` do harness com `gitleaks` | 0 (o harness falha o passo se achar) | pronto 2, bolt B3 |
| U3-N12 | Sem privilégio (NFR7) | Chamadas ao `sudo` falso nos passos 1, 2, 7, 8, 9a, 9b | 0 | NFR7, passo 3 |
| U3-N13 | Tempo do harness | `sh scripts/verify-install.sh` (passos 1, 2, 3, 4, 7, 8, 9a, 9b), Linux x64, cache do gitleaks frio | ≤ 900 s (= U1-N12; workflow com `timeout-minutes: 20`) | U1-N12 |
| U3-N14 | POSIX | `sh -n` e `dash -n` em `scripts/verify-install.sh` | exit 0 nos dois | U1-N11 |
| U3-N15 | Qualidade do código | `failed` + `errors` no CI `pytest` (3.10, 3.12); CRAP por função alterada; sobreviventes sem waiver; linhas novas de `src/` cobertas | 0; < 10; 0 (0 waivers novos); 100% (piso 80,0 mantido) | DoD 2, `bob.yaml`, U1-N14 |
| U3-N16 | Segredos | Achados do gitleaks no PR | 0 | CI |
| U3-N17 | Testes sem internet | Requisições de `tests/test_gitleaks.py` fora de `127.0.0.1` | 0 | NFR14 (hermético), D21 da U1 |

## Não se aplica à U3 (ou só em parte)
- NFR3 em macOS e arm64: o código cobre as 4 chaves e os testes cobrem o mapeamento; a prova automática é só Linux x64. A matriz é da U9.
- NFR2, NFR5, NFR8, NFR10, NFR11: sem mudança pela U3 (NFR5 segue provado pelo passo 8).
