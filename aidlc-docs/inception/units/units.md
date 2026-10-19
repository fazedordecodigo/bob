# 2.7 Units — Índice (bob)

Profundidade: Minimal. Data: 2026-10-18 (UTC-3). Detalhe: `unit-of-work.md`. DAG: `unit-of-work-dependency.md`. Mapa: `unit-of-work-story-map.md`. Máquina: `traceability.json`. Perguntas: `units-questions.md`.
Ordem de entrega: não decidida aqui (Maestro, 2.9).

| ID | Nome | Kind | Dono de | Depende de | Walking skeleton? |
|---|---|---|---|---|---|
| U1 | u1-walking-skeleton | packaging | C01, C02, C03, C04, C13 | U2 | **sim** |
| U2 | u2-doctor-fonte-unica (P1) | library | C08, C09 | — | não |
| U3 | u3-gitleaks | library | C07 | U1, U2 | não |
| U4 | u4-bob-yaml | library | C05 | U1 | não |
| U5 | u5-hook-pre-push | library | C06 | U1 | não |
| U6 | u6-perfil-shell | packaging | — (estende C01, C02) | U1 | não |
| U7 | u7-update-versao | library | C10 | U1, U2 | não |
| U8 | u8-docs | spec | C12 | U1–U7 | não |
| U9 | u9-release-v0-1-0 | packaging | C11 | U1–U8 | não (fluxo da release: pré-release → verificação nos 5 agentes → promoção pelo Emerson; Q1 A) |

## Comando de Verificação do projeto
O do 2.6, sem mudança de passos:
```sh
python3 -m venv /tmp/dev && /tmp/dev/bin/pip install -e '.[dev]' && /tmp/dev/bin/pytest \
  && sh scripts/verify-install.sh
```
Ajustes que as units exigem:
- `scripts/verify-install.sh` nasce no U1 e cresce por unit (cada unit só fica pronta com os seus passos e sem regressão nos já existentes).
- Até o U3, o harness põe o gitleaks 8.30.1 no `PATH` (fixture). Depois, o passo 2 roda sem fixture.
- Passo 9 ganha o caso (b): wheel com sha256 errado no espelho → sai `4`, nada instalado (prova NFR6 do lado do wheel, U1).
- Passo 10 ganha um critério: o comando único num `HOME` novo, com uma pré-release mais nova no espelho, instala a release publicada (US7.2 crit. 1).
- Passo 14 (2.8, CT15/CT18; aprovado no 2.9 com os passos 1–14): instalação pelo `install.sh` (A) e pelos blocos do prompt de IA (B) dão o mesmo manifesto, `bob doctor` = 0 nos dois, 0 pedidos de `install.sh`. Acrescentado pela U8 (L1).

| Unit | Passos que a provam |
|---|---|
| U1 | 1, 2 (parcial), 3, 4, 7, 8 (parcial), 9 (b) |
| U2 | pytest; 8 (parcial) |
| U3 | 2, 7, 9 (a) |
| U4 | 5, 7, 8 (parcial) |
| U5 | 6, 7, 8 (parcial), 12 |
| U6 | 13 |
| U7 | 2 (parcial), 10, 11 |
| U8 | pytest (`tests/test_docs_pins.py`, com a paridade do CT18); 14 |
| U9 | 1–14 na matriz + verificação manual por release (com "Prompt de IA") |

## 2.8 Contratos
Recomendação: **entrar, em Minimal.** Há 9 units e contratos entre elas, além de APIs externas:
- Internos: registro de passos e resumo do `bob setup` (U1 ↔ U3, U4, U5, U6); códigos de saída `0`/`4` e formato de erro; layout de `BOB_HOME` (U1 ↔ U3, U5, U7); `.bob-version` (U1 ↔ U2, U7); `BOB_INSTALL_PROFILE` (U6 ↔ U1); marca `managed-by: bob-quality` (U5, U6); formato de release: nomes dos assets, `SHA256SUMS`, tag `vX.Y.Z` (U1, U7 consomem; U9 produz); `pinned_npm_versions()`/`node_range()` (U2 ↔ U1, U8).
- Externos: GitHub REST `releases/latest` e downloads de asset (U1, U7, U9); assets do gitleaks v8.30.1 (U3); registro npm (`npm ci`, U1) e PyPI (dependências do wheel, U1).
- Sem 2.8, U3–U7 e U9 seriam escritos contra interfaces só descritas em prosa no 2.6.

## Registro
- Correção L1 (2026-10-18 20:29 UTC-3; origem: `verification/phase-check-inception.md`, lacuna L1, via Maestro; Emerson aprovou o 2.9 e os passos 1–14 às 20:28 UTC-3): Adendo A1 (US1.5; FR1.6, FR1.7, FR1.8, FR8.4, FR8.5; NFR10, NFR11) e passo 14 trazidos do 2.8 (CT15, CT17, CT18) para o 2.7. DAG sem mudança. Aqui: passo 14 na lista de ajustes; linhas U8 e U9 da tabela de passos.
