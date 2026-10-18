# 2.9 Delivery Planning — Bolt Plan (bob)

Profundidade: Minimal. Autor: Maestro AI-DLC. Data: 2026-10-18 (UTC-3).
Insumos (aprovados): `inception/units/` (2.7, DAG sem ciclo), `inception/contracts/` (2.8, CT1–CT18), `inception/application-design/verification-command.md` (2.6), `requirements.md` + Adendo A1, `stories.md` (14 US).

## Regras de entrega
- Um bolt = uma unit = um ou mais PRs para `main`, abertos pelo cloud agent que o Arquiteto despacha.
- Ordem sequencial. Um bolt só começa depois que o Emerson fez o merge do anterior. Isso evita conflito em `install.sh`, `bob setup` e no harness, que são compartilhados.
- Cada bolt passa por: 3.1 desenho (leve), plano de código + ETs, **Plan Approval do Emerson**, despacho, PR verificado pelo Arquiteto, **checkpoint do Emerson**, merge pelo Emerson.
- Falha: PR reprovado 2 vezes, build vermelho ou agente parado → paro o fluxo e levo ao Emerson: tentar de novo, pular (com efeito nos dependentes) ou abortar.

## Definition of Done (vale para todo bolt)
1. Os critérios "Pronto quando" da unit (`unit-of-work.md`) passam.
2. O Comando de Verificação aprovado sai `0`: `pytest` verde e todos os passos do `scripts/verify-install.sh` que já existem passando, sem regressão.
3. Os passos da unit rodam com `sh scripts/verify-install.sh --only <passos>` (CT15) e o resultado vai no PR.
4. Os contratos dos quais a unit é dona estão implementados como no 2.8. Os que ela consome não foram alterados.
5. O PR cita a unit, os FR/US/CT cobertos e não tem segredo.
6. Merge feito pelo Emerson.

## Ordem dos bolts
| Bolt | Unit | Depende de | Por que nesta posição | Passos do Comando | DoD específico |
|---|---|---|---|---|---|
| B1 | U2 u2-doctor-fonte-unica | — | Pré-requisito do walking skeleton (U1 depende de U2). Corrige a `main` quebrada (P1: vitest 5.0.5 vs 5.0.4). Pequeno. | `pytest`; 8 (parcial) | `bob doctor` = 0 com vitest 5.0.5; nenhuma versão npm literal em `doctor.py` e `test_npm_pin.py`; job de empacotamento da `main` verde |
| B2 | U1 u1-walking-skeleton | U2 | **Walking skeleton**: menor fatia ponta a ponta (comando único → wheel → `bob setup` → skills em `.agents/skills` → `bob doctor: 0`). Nasce o harness com espelho local. | 1, 2 (parcial), 3, 4, 7, 8 (parcial), 9 (b) | os 9 critérios de pronto do U1; ≤ 300 s no Linux x64; fixture do gitleaks no `PATH` |
| B3 | U3 u3-gitleaks | U1, U2 | Tira a fixture do gitleaks; fecha o critério 1 do intent sem atalho. | 2 (completo), 7, 9 (a) | 4 sha256 da ADR 0014; tar.gz adulterado → `4` e nada instalado; 2ª execução sem download |
| B4 | U4 u4-bob-yaml | U1 | Configuração do projeto (intent C3). | 5, 7, 8 (parcial) | `paths.include` = `[src]`, `[app]`, `["."]`; preservação de `bob.yaml` e waivers |
| B5 | U5 u5-hook-pre-push | U1 | Hook (intent C4). Depois do U4 porque o hook roda `bob check`, que usa o `bob.yaml`. | 6, 7, 8 (parcial), 12 | push dispara o hook; `test_hook.py` < 60 s; hook alheio e `core.hooksPath` preservados |
| B6 | U6 u6-perfil-shell | U1 | Perfil do shell (Q1 A do 2.6). Independente, curto. | 13 | casos (a)–(e); linha marcada = 1 depois de 2 execuções |
| B7 | U7 u7-update-versao | U1, U2 | Atualização (intent C5). Precisa do layout e do `.bob-version` estáveis. | 2 (parcial), 10 (com o critério do 2.7), 11 | update preserva tudo; ignora pré-release e rascunho |
| B8 | U8 u8-docs | U1–U7 | Docs descrevem o que já existe. Inclui o prompt de IA (CT18), dois idiomas, e o teste de paridade. | `pytest` (`test_docs_pins.py`, paridade CT18); **14** | comando único primeiro nos docs; prompt como alternativa; `install-prompt.en.md` e `.pt-BR.md`; paridade A = B |
| B9 | U9 u9-release-v0-1-0 | U1–U8 | Fecha a construção. Pronto = **pronto para o Emerson disparar**. | 1–14 na matriz (Linux/macOS × x64/arm64) + verificação manual por release | `dry_run` verde nos 4 runners; 3 assets com `SHA256SUMS` OK; `docs/release-checks/v0.1.0.md` com roteiro E1–E6, os 5 agentes e o item "prompt de IA" |

Depois de B9: 3.6 (verificação de construção) e 3.7. O disparo da release v0.1.0 (E1–E6) é do Emerson (P2).

## Sequência e riscos
- Caminho crítico: U2 → U1 → U3/U7 → U8 → U9. U4, U5 e U6 não estão no caminho crítico, mas vão em sequência para não brigar no `bob setup` (CT3) e no harness (CT15).
- Paralelismo possível (não proposto): depois do B2, U4, U5 e U6 poderiam rodar juntos. Fica sequencial na POC por simplicidade de revisão e merge.
- Risco RA1 (Claude Code e `.agents/skills`): aceito; aparece só na verificação manual (B9/E4) e não bloqueia a promoção.
- Risco de rede/terceiros (GitHub API, npm, PyPI, assets do gitleaks): o harness usa espelho local; só o modo `VERIFY_REMOTE=1` e o E2–E6 dependem da rede.
- Não verificado (herdado do 2.8, para 3.6/3.7): gates com `include ["."]`, `test_hook.py` com o template novo, rótulos dos runners da matriz.

## Dependências externas
| Externo | Usado em | Controle |
|---|---|---|
| GitHub REST `releases/latest` e downloads | U1, U7, U9 | espelho local no harness; real só em `VERIFY_REMOTE=1` e E2–E6 |
| Assets do gitleaks v8.30.1 | U3 | sha256 fixos (ADR 0014, CT9), conferidos no 2.8 |
| Registro npm | U1 | versões do `package.json` (ADR 0008) |
| PyPI (dependências do wheel) | U1 | `pip` com `PIP_OPTS` (CT2) |
| Runners macOS/arm64 | U9 | rótulos a fixar no 3.7 |

## Comando de Verificação (para aprovação do Emerson neste portão)
Proposto pelo Arquiteto no 2.6, ajustado no 2.7 e no 2.8:
```sh
python3 -m venv /tmp/dev && /tmp/dev/bin/pip install -e '.[dev]' && /tmp/dev/bin/pytest \
  && sh scripts/verify-install.sh
```
- Passos 1–13 de `verification-command.md` (2.6).
- Ajustes do 2.7: passo 9 caso (b), wheel adulterado; passo 10, instalação nova ignora pré-release (US7.2 crit. 1); o harness nasce no U1 e cresce por unit.
- **Passo 14** (2.8, CT15/CT18): instala pelo `install.sh` (A) e pelos blocos do prompt de IA (B) no mesmo `HOME` recriado; A = B no manifesto; `bob doctor` = 0 nos dois; nenhum pedido de `install.sh` no log do espelho; 2ª execução não muda nada.
- Fora da automação: verificação manual por release nos 5 agentes e com um agente de IA real seguindo o prompt (`docs/release-checks/vX.Y.Z.md`).
- Saída: `0` se tudo passa; `1` no primeiro passo que falha (`verify-install: passo <n>: <motivo>`).
