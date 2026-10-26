# U6 — Requisitos não funcionais (3.2 leve)

| Id | Requisito | Medida | Alvo | Prova | Origem |
|---|---|---|---|---|---|
| U6-N1 | Comando `bob` disponível num terminal novo (FR1.1) | `sh -c '. <perfil>; command -v bob'` com `env -i HOME PATH=/usr/bin:/bin`, casos (a)–(c) | `= $HOME/.local/bin/bob` em 3 de 3 | passo 13 | US1.1 crit. 2, pronto da U6 |
| U6-N2 | Linha única (NFR4) | `grep -c 'managed-by: bob-quality' <perfil>` depois de 2 execuções | `1` em (a)–(c) | passo 13; `test_second_run_is_already_marked` | pronto da U6 |
| U6-N3 | Preservação do perfil (NFR5) | bytes anteriores do perfil existente | iguais em 100% (b); arquivo inteiro igual em (d) e (e) | passo 13; `test_profile_append_keeps_the_bytes` | CT16 |
| U6-N4 | Nunca falha (NFR9) | código do comando único com perfil sem escrita | `0` (com `bob setup` 0) e 1 aviso com a linha para colar | passo 13 (e); `test_unwritable_profile_warns_and_exits_0` | CT16 |
| U6-N5 | Sem privilégio (NFR7) | `sudo` no passo `perfil`, arquivos fora do `HOME` | 0; 0 | `test_install_sh_never_mentions_sudo` (existente); passo 3 | NFR7 |
| U6-N6 | Resumo claro (FR7.1) | linha `perfil do shell:` antes de `bob doctor:` para os 4 valores válidos; 0 linhas para valor inválido | 4 de 4; 0 | `test_profile_text_maps_each_value` (14 casos), `test_profile_line_sits_before_the_doctor_line` | CT3 |
| U6-N7 | Tempo do passo 13 | `verify-install: passo 13: tempo <s> s` | ≤ 180 s (10 execuções com pacote reusado) | job `verify-install / linux-x64` | ADR 0026 |
| U6-N8 | Harness inteiro | duração do `sh scripts/verify-install.sh` | ≤ 900 s (timeout do job 20 min) | job `verify-install / linux-x64` | U5-N13 |
| U6-N9 | Qualidade do diff | `bob check --base origin/main --gates crap,dry,deps,mutate,coverage` | exit 0; CRAP < 10; 0 sobreviventes; 0 waivers novos; coverage ≥ 80.0 e 100% das linhas novas | CI `bob / check` | NFR do projeto |
| U6-N10 | Testes herméticos (U5-N16) | linhas no log da guarda em `pytest tests/test_setup_cmd.py -k "hook or profile"` | 0 | `tests/test_hermetic.py` | U5-N16 |
| U6-N11 | POSIX | `sh -n` e `dash -n` em `scripts/install.sh` e `scripts/verify-install.sh` | exit 0 | `test_install_sh_is_posix`, `test_verify_install_is_posix` | CT2 |

## Não se aplica à U6 (ou só em parte)
- NFR1 (≤ 5 min de instalação): o passo `perfil` faz 1 `grep` e no máximo 2 escritas. Não muda o tempo do passo 2.
- NFR8 (hook): fora da unit.
- Testes de `tests/test_install_sh.py` usam servidor local (`127.0.0.1`), então não entram na guarda de rede. É a mesma exceção que a U5 tinha para os testes com espelho.
