# 2.7 Units — Mapa US / FR / NFR → unit

Fonte única: `traceability.json` (gerado e validado com `python -m json.tool`). "Dona" = unit responsável; "contribui" = outra unit cujo pronto também prova parte.

## US → unit (14 US, nenhuma órfã)
| US | Dona | Contribui | Passos |
|---|---|---|---|
| US1.1 Instalar com um comando | U1 | U2 (crit. 5, npm), U3 (crit. 1 e 5, gitleaks), U6 (crit. 2), U7 (crit. 3, `--version`), U9 (crit. 1 em cada plataforma) | 2, 3, 7 |
| US1.2 Pré-requisito antes | U1 | — | 1 |
| US1.3 Binários conferidos | U3 | U1 (wheel) | 9 |
| US1.4 Não mexer nas ferramentas do projeto | U2 | U1 (crit. 1, manifestos) | 8 |
| US2.1 Skills sem plugin | U1 | U9 (verificação manual; RA1 no Claude Code) | 4, manual |
| US3.1 `bob.yaml` que funciona | U4 | — | 5 |
| US3.2 Manter o que já configurei | U4 | U5 (hook), U7 (crit. 3 na atualização) | 8, 10 |
| US4.1 Gates a cada push | U5 | — | 6, 12 |
| US5.1 Atualizar | U7 | — | 10, 11 |
| US5.2 Ver a versão | U7 | — | 2, 10 |
| US6.1 Entender o que aconteceu | U1 | U3, U4, U5, U6 (linhas do resumo e erros do próprio passo) | 1, 2, 9 |
| US7.1 Docs | U8 | — | pytest |
| US7.2 Pré-release sem afetar | U7 | U1 (crit. 1, `install.sh`), U9 (input `prerelease`) | 10, 11 |
| US1.5 Pedir ao agente de IA para instalar (A1) | U8 | U9 (crit. 7, agente real por release) | pytest, 14, manual |

## FR → unit (39 FR, nenhum órfão)
| FR | Unit | FR | Unit | FR | Unit |
|---|---|---|---|---|---|
| FR1.1 | U1 | FR3.1 | U1 | FR6.1 | U7 |
| FR1.2 | U1 | FR3.2 | U1 | FR6.2 | U7 |
| FR1.3 | U1 | FR3.3 | U1 | FR6.3 | U7 |
| FR1.4 | U1 | FR3.4 | U1 | FR6.4 | U7 |
| FR1.5 | U1 | FR4.1 | U4 | FR6.5 | U7 |
| FR2.1 | U2 | FR4.2 | U4 | FR7.1 | U1 |
| FR2.2 | U3 | FR4.3 | U4 | FR7.2 | U1 |
| FR2.3 | U3 | FR4.4 | U4 | FR7.3 | U1 |
| FR2.4 | U1 | FR4.5 | U4 | FR8.1 | U8 |
| FR2.5 | U2 | FR4.6 | U4 | FR8.2 | U8 |
|  |  | FR5.1 | U5 | FR8.3 | U8 |
|  |  | FR5.2 | U5 |  |  |
|  |  | FR5.3 | U5 | FR8.4 | U8 |
| FR1.6 | U8 | FR1.7 | U8 | FR8.5 | U8 |
| FR1.8 | U8 |  |  |  |  |

FR1.6–FR1.8, FR8.4, FR8.5: Adendo A1 (prompt CT18 e docs CT17), dona U8; U9 contribui com a verificação manual por release (FR1.7, FR8.5).

Contribuições sem posse: FR1.1 (U3, U4, U5, U6 completam o "configurado"), FR1.2 e FR1.4 (U9 publica a release real), FR3.2 (U9, verificação manual nos 5 agentes, RA1), FR7.1 (U6, linha do perfil).

## NFR → units
| NFR | Units | Onde se prova |
|---|---|---|
| NFR1 Tempo ≤ 5 min | U1, U3, U9 | passo 2 (U1 com fixture; U3 sem fixture; U9 nos 4 runners) |
| NFR2 Esforço 1/1/0/0 | U1, U6, U7 | passos 2, 13, 10 |
| NFR3 Plataformas | U1, U3, U9 | U9: todos os passos na matriz |
| NFR4 Repetição segura | U1, U4, U5, U6, U7 | passos 7, 11, 13 |
| NFR5 Preservação | U1, U2, U4, U5, U6, U7 | passos 8, 10, 13 |
| NFR6 Integridade | U1 (wheel), U3 (gitleaks) | passo 9 (casos b e a) |
| NFR7 Sem `sudo` | U1, U6 | passos 3, 13 |
| NFR8 Hook < 60 s | U5 | passo 12 |
| NFR9 Clareza de erro | U1, U3, U6, U7 | passos 1, 9, 13 |
| NFR10 Paridade dos caminhos (A1) | U8, U9 | passo 14 (U8; U9 na matriz); manual "Prompt de IA" (U9) |
| NFR11 Independência do `install.sh` (A1) | U8, U9 | pytest (item 10 do CT18), passo 14 (log do espelho) |

## Registro
- Correção L1 (2026-10-18 20:29 UTC-3; origem: `verification/phase-check-inception.md`, lacuna L1, via Maestro; Emerson aprovou o 2.9 e os passos 1–14 às 20:28 UTC-3): Adendo A1 (US1.5; FR1.6, FR1.7, FR1.8, FR8.4, FR8.5; NFR10, NFR11) e passo 14 trazidos do 2.8 (CT15, CT17, CT18) para o 2.7. DAG sem mudança.
