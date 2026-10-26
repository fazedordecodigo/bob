# U2 — Requisitos não funcionais (3.2 leve)

Só os NFR que tocam a U2. Cada um com alvo numérico. Nenhuma meta existente do repo foi rebaixada.

| ID | Requisito | Métrica | Alvo | Origem |
|---|---|---|---|---|
| U2-N1 | Preservação (NFR5) | Bytes alterados no diretório do projeto por `bob doctor` (sha256 de cada arquivo antes e depois) | 0 | NFR5, US1.4 crit. 1 |
| U2-N2 | Isolamento do projeto (FR2.5) | Linhas do doctor que mostram a versão do `node_modules` do projeto, com vitest 4.1.0 no cwd | 0; exit 0 | US1.4 crit. 2, Pronto 4 |
| U2-N3 | Fonte única (ADR 0008) | Versões npm literais em `src/bob_quality/doctor.py` e `tests/test_npm_pin.py` | 0 | Pronto 1 |
| U2-N4 | Custo de bump npm | Arquivos de código e de teste a tocar num bump de versão npm | 0 (só `package.json` e `package-lock.json`) | ADR 0008 |
| U2-N5 | Paridade lock | Dependências com versão diferente entre `package.json` e `package-lock.json` aceitas pelo teste | 0 | Pronto 3 |
| U2-N6 | Leitura mínima | Subprocessos do doctor sem `--install` | 2 (`node`, `gitleaks`) | ADR 0019 |
| U2-N7 | Tempo | `bob doctor` no Linux x64 do CI, wall clock | ≤ 3,0 s | novo; base de NFR1 (≤ 5 min de instalação) |
| U2-N8 | Clareza de erro (NFR9) | Falhas de leitura do `package.json` empacotado que saem em uma linha no stderr, no formato CT1, com exit 4, em en e pt-BR | 100% (7 de 7 casos de `functional-design.md`) | NFR9, CT1, CT8 |
| U2-N9 | Suíte verde | Testes `failed` + `errors` no CI `pytest` (3.10 e 3.12) | 0 (linha de base na `main`: 18 failed) | DoD 2 |
| U2-N10 | Empacotamento | Job `package/dist`: `python -m build`, `twine check --strict`, `bob doctor` | exit 0 em cada passo | Pronto 5 |
| U2-N11 | CRAP (gate do repo) | CRAP por função alterada em `src` | < 10 (`crap.max_per_function: 10`, mantido) | `bob.yaml` |
| U2-N12 | Mutação (gate do repo) | Sobreviventes sem waiver nas funções alteradas | 0; 0 waivers novos | CI `bob.yml` (`mutate` sai 3) |
| U2-N13 | Cobertura de diff | Linhas alteradas em `src` cobertas | 100% (piso do repo `coverage.min_percent` 80,0, mantido) | `bob.yaml`, decisão da U2 |
| U2-N14 | Segredos | Achados do gitleaks no PR | 0 | CI |

## Não se aplica à U2
- NFR1, NFR2, NFR4, NFR6, NFR7, NFR8: tratam de instalação, gitleaks, privilégio e hook. U2 não muda nenhum desses fluxos.
- NFR3 (Linux e macOS): o CI do repo roda só Linux. U2 não tem código por plataforma. A medida em macOS fica com U1 (harness, I7).
