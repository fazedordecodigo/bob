# 2.6 Application Design — Rastreabilidade

Base: `stories.md` (13 US) e `requirements.md` (34 FR, 9 NFR). Componentes: `components.md`. ADRs: `decisions.md`.

## US → componentes → FR
| US | Componentes | FR | ADR |
|---|---|---|---|
| US1.1 Instalar com um comando | C01, C02, C03, C04, C05, C06, C07, C08, C09, C11, C13 | FR1.1, FR1.2, FR1.3, FR1.4, FR1.5, FR2.1, FR2.2 | 0008, 0011, 0012, 0013, 0014 |
| US1.2 Saber antes se falta pré-requisito | C01, C02 | FR7.2, FR7.3 | 0008, 0012 |
| US1.3 Confiar nos binários baixados | C07, C01 | FR2.3 | 0011, 0014 |
| US1.4 Não mexer nas ferramentas do projeto | C02, C08, C09, C13 | FR2.4, FR2.5 | 0013, 0019 |
| US2.1 Skills no agente sem plugin | C03, C04, C02 | FR1.3, FR3.1, FR3.2, FR3.3, FR3.4 | 0009, 0010, 0017 |
| US3.1 `bob.yaml` que funciona | C05, C02 | FR4.1, FR4.2, FR4.3, FR4.4, FR4.5 | 0015 |
| US3.2 Manter o que já configurei | C05, C06, C03, C02 | FR4.6, FR5.3, FR6.3 | 0016, 0017 |
| US4.1 Gates a cada push | C06, C13 | FR5.1, FR5.2 | 0013, 0016 |
| US5.1 Atualizar para a release mais nova | C10, C01, C02, C03 | FR6.1, FR6.2, FR6.3, FR6.5 | 0011, 0017, 0018 |
| US5.2 Saber a versão instalada | C10, C03, C08 | FR6.4 | 0018 |
| US6.1 Entender o que aconteceu | C02, C01 | FR7.1, FR7.2 | 0012, 0017 |
| US7.1 Caminho certo na documentação | C12 | FR8.1, FR8.2, FR8.3 | 0020 |
| US7.2 Pré-release sem afetar quem usa | C01, C10, C11 | FR1.4, FR6.1, FR6.5 | 0011, 0018 |

Conferência: 13 US, todas com componente. Nenhuma órfã.

## FR → componente (cobertura)
| FR | Componente(s) |
|---|---|
| FR1.1 | C01, C02 |
| FR1.2 | C01, C11 |
| FR1.3 | C03 |
| FR1.4 | C01, C11 |
| FR1.5 | C02, C08 |
| FR2.1 | C02, C08, C09 |
| FR2.2 | C07 |
| FR2.3 | C07, C01 |
| FR2.4 | C02, C13 |
| FR2.5 | C08 |
| FR3.1 | C03, C04 |
| FR3.2 | C03 |
| FR3.3 | C03 |
| FR3.4 | C03 |
| FR4.1 | C05 |
| FR4.2 | C05 |
| FR4.3 | C05 |
| FR4.4 | C05 |
| FR4.5 | C05 |
| FR4.6 | C05 |
| FR5.1 | C06 |
| FR5.2 | C06, C13 |
| FR5.3 | C06 |
| FR6.1 | C10, C01 |
| FR6.2 | C10, C02, C03 |
| FR6.3 | C02, C03, C05, C06 |
| FR6.4 | C10 |
| FR6.5 | C10 |
| FR7.1 | C02 |
| FR7.2 | C01, C02 |
| FR7.3 | C01, C02 |
| FR8.1 | C12 |
| FR8.2 | C12, C09 |
| FR8.3 | C12 |

Conferência: 34 FR, todos com componente.

## NFR → componente / ADR
| NFR | Componente(s) | ADR | Como se garante |
|---|---|---|---|
| NFR1 Tempo ≤ 5 min | C01, C02, C07, C09 | 0011, 0013, 0014 | Wheel pronto (sem build), gitleaks binário, `npm ci` com lock. Medido no Comando de Verificação, passo 2. |
| NFR2 Esforço 1/1/0/0 | C01, C10 | 0012, 0013, 0018 | Um comando instala; `bob update` atualiza; nada clonado nem editado à mão (o `PATH` vai no perfil pelo instalador, Q1 A; passo 13). |
| NFR3 Plataformas | C01, C07, C13 | 0014 | Tabela das 4 plataformas; verificação em 4 runners. |
| NFR4 Repetição segura | C02, C03, C05, C06 | 0017 | Comparar antes de escrever. |
| NFR5 Preservação | C02, C03, C05, C06 | 0017 | Escrever só no que tem marcador ou não existe. |
| NFR6 Integridade | C01, C07, C10 | 0011, 0014 | sha256 antes de usar; falha não instala. |
| NFR7 Sem `sudo` | C01, C13 | 0013 | Tudo em `BOB_HOME` e no projeto. |
| NFR8 Hook < 60 s | C06 | 0016 | Mesmo comando do hook atual; `tests/test_hook.py`. |
| NFR9 Clareza de erro | C01, C02, C07, C10 | 0012 | Formato `<passo>: <falha>. <ação>.` em toda saída de erro. |

## Pré-condições → ADR
| Pré-condição | Situação |
|---|---|
| P1 doctor = 4 (vitest) | Resolvida no desenho pela ADR 0008. A correção entra na construção. |
| P2 release v0.1.0 | Fora do 2.6. Workflow `release` (C11, ADR 0011) pronto para o Emerson disparar no 2.9. |
| P3 pastas por agente | Decidida pela ADR 0009: só `.agents/skills` (pedido do Emerson, 18/10/2026 18:25 UTC-3). Docs confirmam Cursor, Copilot, Devin CLI e Devin web. **Claude Code: a doc não cita `.agents/skills`; FR3.2, US2.1 e o critério 2 do intent ficam em risco (Não verificado).** Verificação manual por release. |

## Impacto da ADR 0009 (`.agents/skills`) nos artefatos do Analista
**Risco aceito:** o Emerson aceitou o risco em 18/10/2026 18:31 UTC-3, literal via Maestro: "Aceito o risco no Claude Code e mantenho .agents/skills." Para o Claude Code, o critério 2 do intent, o FR3.2 e o US2.1 crit. 1 seguem a verificação manual por release (`verification-command.md`; evidência em `docs/release-checks/vX.Y.Z.md`; ADR 0009, Risco 1). Para os outros quatro agentes, a meta segue igual.

Só leitura; nada foi editado lá. Tensão porque a doc oficial do Claude Code (https://code.claude.com/docs/en/skills, reconferida em 18/10/2026) não cita `.agents/skills`.

| Ref. | Texto | Situação |
|---|---|---|
| `ideation/intent/intent.md:24` | "skills do bob dentro do projeto, lidas pelos quatro agentes;" | Em risco no Claude Code |
| `ideation/intent/intent.md:47` (critério 2) | "...aparecem no Cursor, no Claude Code, no GitHub Copilot e no Devin, sem plugin nativo instalado." | **Não verificado / em risco** no Claude Code |
| `ideation/intent/intent-questions.md:68` | "Q4: A — skills para Cursor, Claude Code, GitHub Copilot e Devin, sem plugin nativo." | Em risco no Claude Code |
| `inception/requirements/requirements.md:38` (FR3.2) | "Cursor, Claude Code, GitHub Copilot e Devin enxergam as skills sem plugin nativo." | Em risco no Claude Code |
| `inception/requirements/requirements.md:88` (critério 2) | "as três skills aparecem uma vez em cada agente: Cursor, Claude Code, GitHub Copilot, Devin." | Em risco no Claude Code |
| `inception/requirements/requirements.md:108` (R-S4) | "As skills vão sempre para os quatro agentes." | Em risco no Claude Code |
| `inception/requirements/requirements.md:127` (P3) | "...que o Cursor lê `.agents/skills` e o Copilot lê `.github/skills`, e onde o Claude Code lê skills de projeto." | Respondida: Claude Code lê `.claude/skills`, não usada |
| `inception/user-stories/stories.md:65` (US2.1 crit. 1) | "...quando abro o projeto em Cursor, Claude Code, GitHub Copilot e Devin, então cada um lista `bob-check`, `harden` e `review-report`." | Em risco no Claude Code |
| `inception/user-stories/stories.md:213` | "P3: pastas lidas por Cursor e Copilot (e Claude Code) confirmadas no 2.6. Bloqueia US2.1 crit. 1." | Claude Code não confirmado |
| `inception/requirements/requirements.md:39` (FR3.3), `stories.md:66` | uma vez por agente, sem duplicata no Devin | Sem tensão: pasta única |
