# U7 — Requisitos não funcionais (3.2 leve)

| Id | Requisito | Medida | Alvo | Prova | Origem |
|---|---|---|---|---|---|
| U7-N1 | Atualiza para a última publicada (FR6.1–6.4) | `bob --version` depois do `bob update` no passo 10 | as 2 linhas = v-nova; `.bob-version` = v-nova em 3 de 3 skills | passo 10 | pronto 1 |
| U7-N2 | Pré-release e rascunho ignorados (US7.2) | pedidos ao espelho com `v99.1.0` ou `v99.1.1` | 0 | passo 10 (lista exata de pedidos) | pronto 1 e 3 |
| U7-N3 | 2ª execução sem mudança (FR6.5, NFR4) | `digest` do projeto antes/depois; pedidos ao espelho | igual; exatamente 1 (`api`) | passo 11; `test_up_to_date_prints_and_changes_nothing` | pronto 2 |
| U7-N4 | Preservação (NFR5) | hash de `bob.yaml`, `.bob/waivers.yaml`, hook alheio e skill alheia do passo 8 | iguais em 4 de 4 | passo 10 | pronto 1 |
| U7-N5 | Integridade (NFR6) | `install.sh` com sha diferente, ou sem linha no `SHA256SUMS` | 0 execuções do script, `4` | `test_integrity_failures[3]`, `test_sums_first_matching_line_wins` | CT11, CT12 |
| U7-N6 | Rede (CT14) | tentativas por URL; pausa entre elas; `Accept` | 3 em rede/`5xx`, 1 em `4xx` (inclusive `429`); 1,0 s; `Accept` só na API; `timeout=30` | `test_api_errors_exit_4[5]`, `test_retry_then_success`, `test_download_errors[3]` | CT14 |
| U7-N7 | Tempo do `bob update` (NFR2) | `verify-install: passo 10: tempo <s> s` (só o `bob update`) | ≤ 300 s | job `verify-install / linux-x64` | ADR 0026 |
| U7-N8 | Tempo do "já está" | `verify-install: passo 11: tempo <s> s` | ≤ 30 s | job `verify-install / linux-x64` | ADR 0026 |
| U7-N9 | Harness inteiro | duração do `sh scripts/verify-install.sh` | ≤ 900 s (timeout do job 20 min) | job | U5-N13 |
| U7-N10 | Sem privilégio (NFR7) | `sudo` no código novo | 0 | `test_verify_install_shape` (existente); revisão | NFR7 |
| U7-N11 | Nunca falha calado (NFR9) | erros de `bob update` com mensagem no stderr e `4` | 100% dos caminhos de erro de U1–U6 com teste | testes da T2 | NFR9 |
| U7-N12 | Qualidade do diff | `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` | exit 0; CRAP < 10; 0 sobreviventes; 0 waivers novos; coverage ≥ 80,0 e 100% das linhas novas | CI `bob / check` | NFR do projeto |
| U7-N13 | Testes herméticos (U5-N16) | linhas no log da guarda em `pytest tests/test_project_version.py` e `tests/test_update.py` | 0 | `tests/test_hermetic.py` (2 parâmetros novos) | U5-N16 |

## Não se aplica à U7 (ou só em parte)
- NFR1 (≤ 5 min de instalação): vale para o comando único. O `bob update` reusa o `install.sh` e tem o alvo próprio U7-N7.
- NFR8 (hook): o hook não muda. O `bob setup` que o `install.sh` roda o reescreve só se diferir (U5).
