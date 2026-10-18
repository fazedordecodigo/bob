# 2.8 Contratos — Rastreabilidade

Fonte: `contract-summary.md`. DAG: `../units/unit-of-work-dependency.md`. Passos: `../application-design/verification-command.md` (mais 9b e o critério extra do 10, do 2.7).

## Contrato → units → requisitos → passos
| Contrato | Nome | Dona | Consumidoras | US | FR | NFR | Passos |
|---|---|---|---|---|---|---|---|
| CT1 | Saída, erros, idioma, códigos | U1 | U3, U4, U5, U6, U7, U9 | US1.2, US6.1 | FR7.1, FR7.2 | NFR9 | 1, 9 |
| CT2 | CLI install.sh | U1 | U6, U7, U8, U9 | US1.1, US1.2, US7.2 | FR1.1, FR1.2, FR1.4, FR7.3, FR2.4 | NFR1, NFR2, NFR6, NFR7 | 1, 2, 3, 7, 9b |
| CT3 | bob setup: passos e resumo | U1 | U3, U4, U5, U6, U7, U8 | US1.1, US3.2, US6.1 | FR1.1, FR1.5, FR7.1, FR7.2 | NFR4, NFR9 | 2, 7, 8 |
| CT4 | Skills e .bob-version | U1 | U7, U8 | US2.1, US5.1 | FR1.3, FR3.1, FR3.2, FR3.3, FR3.4, FR6.2 | NFR4, NFR5 | 4, 7, 8, 10; manual |
| CT5 | Layout e marcadores | U1 | U3, U5, U6, U7, U8 | US1.1, US4.1 | FR1.1, FR5.2 | NFR4, NFR7 | 2, 3, 6, 13 |
| CT6 | Variáveis de ambiente | U1 | U3, U6, U7, U8, U9 | US1.1, US7.2 | FR1.4 | NFR3 | todos (harness) |
| CT7 | bob.yaml gerado | U4 | U8, U9 | US3.1, US3.2 | FR4.1, FR4.2, FR4.3, FR4.4, FR4.5, FR4.6 | NFR4, NFR5 | 5, 7, 8 |
| CT8 | bob doctor e versões npm | U2 | U1, U3, U7, U8, U9 | US1.1, US1.4 | FR1.5, FR2.1, FR2.5 | NFR5 | pytest, 2, 8 |
| CT9 | gitleaks | U3 | U8, U9 | US1.3, US1.1 | FR2.2, FR2.3 | NFR1, NFR3, NFR6, NFR9 | 2, 9a |
| CT10 | Hook pre-push | U5 | U8, U9 | US4.1, US3.2 | FR5.1, FR5.2, FR5.3 | NFR8, NFR5 | 6, 8, 12 |
| CT11 | bob update e --version | U7 | U8, U9 | US5.1, US5.2, US7.2 | FR6.1, FR6.2, FR6.3, FR6.4, FR6.5 | NFR2, NFR4, NFR5 | 2, 10, 11 |
| CT12 | Formato de release | U1 | U7, U8, U9 | US1.1, US7.2 | FR1.2, FR1.4, FR6.1 | NFR6 | 2, 9b, 10 |
| CT13 | release.yml e release-check | U9 | — (Emerson) | US7.2, US2.1, US1.5 (crit. 7) | FR1.4, FR3.2, FR1.7, FR8.5 | NFR3, NFR10 | 1-13 na matriz; manual; E1-E6 |
| CT14 | APIs externas | U1 | U3, U7, U8, U9 | US1.1, US1.3, US5.1, US7.2 | FR1.2, FR1.4, FR2.1, FR2.2, FR6.1 | NFR1, NFR6 | 2, 9, 10; VERIFY_REMOTE=1 |
| CT15 | Harness verify-install.sh | U1 | U3, U4, U5, U6, U7, U8, U9 | todas com passo | FR1.7 (passo 14 proposto) | NFR3, NFR10, NFR11 | todos; 14 (proposto) |
| CT16 | Perfil do shell | U6 | U8, U9 | US1.1, US6.1 | FR1.1, FR7.1 | NFR2, NFR4, NFR5, NFR7, NFR9 | 13 |
| CT17 | Docs e paridade | U8 | U9 | US7.1, US1.5 (crit. 6) | FR8.1, FR8.2, FR8.3, FR8.4, FR8.5 | NFR11 | pytest (tests/test_docs_pins.py) |
| CT18 | Prompt para agente de IA, sem install.sh (alternativa ao CT2) | U8 | U9 | US1.5 (crit. 1–5, 7) | FR1.6, FR1.7, FR1.8, FR8.5; FR1.4 (só última publicada) | NFR10, NFR11, NFR7 | pytest (tests/test_docs_pins.py, 11 itens); 14 (proposto); manual por release (CT13) |

Nenhum contrato sem unit: todos têm dona; só CT13 não tem consumidora unit (é usado pelo Emerson no fluxo E1–E6 da release).

## Arestas do DAG → contratos que as sustentam
Regra: a aresta A → B é sustentada por um contrato com dona B e A entre as consumidoras.

| Aresta | Contratos |
|---|---|
| U1 → U2 | CT8 |
| U3 → U1 | CT1, CT3, CT5, CT6, CT14, CT15 |
| U3 → U2 | CT8 |
| U4 → U1 | CT1, CT3, CT15 |
| U5 → U1 | CT1, CT3, CT5, CT15 |
| U6 → U1 | CT1, CT2, CT3, CT5, CT6, CT15 |
| U7 → U1 | CT1, CT2, CT3, CT4, CT5, CT6, CT12, CT14, CT15 |
| U7 → U2 | CT8 |
| U8 → U1 | CT2, CT3, CT4, CT5 |
| U8 → U2 | CT8 |
| U8 → U3 | CT9 |
| U8 → U4 | CT7 |
| U8 → U5 | CT10 |
| U8 → U6 | CT16 |
| U8 → U7 | CT11 |
| U9 → U1 | CT1, CT2, CT6, CT12, CT14, CT15 |
| U9 → U2 | CT8 |
| U9 → U3 | CT9 |
| U9 → U4 | CT7 |
| U9 → U5 | CT10 |
| U9 → U6 | CT16 |
| U9 → U7 | CT11 |
| U9 → U8 | CT17, CT18 |

Conferência (script sobre as tabelas acima, 2026-10-18): 23 arestas, 0 sem contrato; 59 pares dona→consumidora (com CT18 e U8 em CT6, CT12, CT14, CT15; refeita 2026-10-18 19:17 UTC-3), 0 contra a direção do DAG (consumidora que não depende da dona).

## Cobertura de requisitos
- FR: 34/34 citados por algum contrato. Faltando: nenhum.
- NFR: 9/9. Faltando: nenhum.
- US: 13/13. Faltando: nenhuma.

## Observação sobre o U2 (I7)
- O U2 não consome contrato de outra unit (não tem dependência). A prova dele é `pytest` (CT8). O passo 8 do harness (CT15, dono U1) reprova o mesmo comportamento quando o U1 existir.

## CT18 (prompt de IA, sem install.sh)
- Origem: Emerson, via Maestro, 18/10/2026 19:14 (UTC-3), literal: (1) "Adicione um prompt que orie te um modelo de IA a como instalar passo a passo o pacote sem depender de um arquivo .sh"; (2) "Deve haver as duas opções a principal sendo o arquivo .sh"
- Posição: alternativa ao CT2, nunca substituto; em divergência, o CT2 manda. Docs: one-liner primeiro, link para o prompt depois (CT17).
- Dona U8 (depende de U1–U7). Consome CT2, CT3, CT5, CT6, CT12, CT14, CT15 (U1), CT8 (U2), CT9 (U3), CT16 (U6): as arestas U8 → U1, U2, U3, U6 já existem. Consumidora U9 (U9 → U8 já existe). Nenhuma aresta nova.
- Prova: `pytest` (paridade, 10 itens); passo 14 do harness (proposto ao Maestro); manual por release (CT13).

## Cobertura do Adendo A1 (requirements.md / stories.md)
| ID | Contrato(s) | Prova |
|---|---|---|
| FR1.6 | CT18 (Posição, passos) | pytest itens 2, 10; passo 14 |
| FR1.7 | CT18 (Mesmo resultado), CT3, CT7, CT10 (preservação via `bob setup`) | passo 14; manual (CT13) |
| FR1.8 | CT18 (Regras 6, 7; `fail` → `4`) | pytest (formato dos blocos); manual (CT13) |
| FR8.4 | CT17 (Ordem dos caminhos) | pytest (ordem, link) |
| FR8.5 | CT18 (Arquivos), CT17 (link por idioma), CT13 (manual por release) | pytest itens 1–9 (falha se o CT2 muda sem o prompt) |
| NFR10 | CT18 (Mesmo resultado), CT15 (passo 14 proposto), CT13 | passo 14; manual |
| NFR11 | CT18 (Posição; item 10), CT15 (log do espelho no passo 14) | pytest item 10; passo 14 |
| US1.5 | CT18 (crit. 1–5), CT17 (crit. 6), CT13 (crit. 7) | idem |
- Nenhum FR/NFR do A1 fica sem contrato. Ressalva: FR1.7 e NFR10/NFR11 só têm prova automática ponta a ponta se o Maestro aceitar o passo 14 (proposto, fora do 2.6/2.7); sem ele, a prova é pytest + manual por release.
- Origem do A1: Emerson, via Maestro, 18/10/2026 19:14 (UTC-3), duas falas (ver CT18).
