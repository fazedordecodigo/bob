# U4 — Requisitos não funcionais (3.2 leve)

Só os NFR que tocam a U4, cada um com alvo numérico. Nenhuma meta existente do repo, da U1 nem da U3 foi rebaixada: U1-N12/U3-N13 (harness ≤ 900 s), U1-N13/U3-N5 (passo 7 ≤ 60 s), U3-N1 (passo 2 ≤ 300 s) e U3-N15 (qualidade) seguem valendo, agora com o passo `bob.yaml` dentro.

| ID | Requisito | Métrica | Alvo | Origem |
|---|---|---|---|---|
| U4-N1 | `bob.yaml` gerado é válido (FR4.4) | Código de saída de `bob check --base HEAD --gates crap,dry,deps` nos 3 projetos do passo 5 (`src`, `app`, `sem-codigo`) | ≠ `4` em 3 de 3 | FR4.4, US3.1 crit. 1, 2 e 4, pronto 1, passo 5 |
| U4-N2 | `paths.include` derivado (FR4.3, FR4.5) | `paths.include` gravado nos 3 projetos | `[src]`, `[app]`, `["."]` (3 de 3) | pronto 1, passo 5 |
| U4-N3 | Padrões do README (FR4.2) | Bytes do `bob.yaml` gerado que diferem do texto CT7 com o `<INCLUDE>` esperado | 0 (nos 3 projetos do passo 5 e nos testes); chaves fora do README: 0; chave `languages`: ausente | pronto 3, CT7 |
| U4-N4 | Aviso de pasta sem código (FR4.5) | Projetos do passo 5 com a linha `bob setup: bob.yaml: warning: no code folder found; paths.include: ["."].` | 1 de 3 (só `sem-codigo`) | pronto 2, US3.1 crit. 4 |
| U4-N5 | Preservação (NFR5, FR4.6) | Bytes alterados em `bob.yaml` e `.bob/waivers.yaml` já existentes; linhas `  preserved:` no resumo para os dois | 0; 2 | pronto 4, passo 8, US3.2 crit. 1 e 3 |
| U4-N6 | Repetição segura (NFR4) | Arquivos do projeto alterados na 2ª execução; `st_mtime_ns` do `bob.yaml` | 0; igual | passo 7, US3.2 crit. 2 |
| U4-N7 | Atomicidade | Depois de qualquer falha do gerador: arquivos `bob.yaml.tmp-*` no projeto; `bob.yaml` criado | 0; 0 | CT7 passo 6, ADR 0017 |
| U4-N8 | Leitura mínima do que é do dev | Chamadas ao git, leituras e escritas quando `bob.yaml` já existe | 0; 0; 0 | CT7, ADR 0017 |
| U4-N9 | Clareza de erro (NFR9) | Chaves novas `setup.*` com teste exato em en e pt-BR | 100% (6 chaves × 2 idiomas) | NFR9, CT1 |
| U4-N10 | Tempo do passo 5 | `verify-install: passo 5: tempo <s> s` (3 comandos únicos com `BOB_HOME` já pronto + 3 `bob check`), Linux x64 | ≤ 180 s (medido no PR da T3; o harness imprime, não falha) | U1-N13 (≤ 60 s por reexecução) |
| U4-N11 | Harness inteiro | `sh scripts/verify-install.sh` (passos 1, 2, 3, 4, 5, 7, 8, 9a, 9b), Linux x64 | ≤ 900 s (= U1-N12; workflow com `timeout-minutes: 20`) | U1-N12, U3-N13 |
| U4-N12 | POSIX | `sh -n` e `dash -n` em `scripts/verify-install.sh` | exit 0 nos dois | U1-N11 |
| U4-N13 | Qualidade do código | `failed` + `errors` no CI `pytest` (3.10, 3.12); CRAP por função alterada; sobreviventes sem waiver; linhas novas de `src/` cobertas | 0; < 10; 0 (0 waivers novos); 100% (piso 80,0 mantido) | DoD, `bob.yaml` do repo, U3-N15 |
| U4-N14 | Testes herméticos | Requisições de rede em `tests/test_init_config.py` e nos testes novos de `test_setup_cmd.py` | 0 (só `git` local em `tmp_path`) | D21 da U1 |

## Não se aplica à U4 (ou só em parte)
- NFR1, NFR2, NFR3, NFR6, NFR7, NFR8: sem mudança pela U4. NFR7 segue provado pelo passo 3, que também cobre o passo 5, porque o `sudo` falso fica no `PATH` de todos os passos.
- NFR5 para hook e dependências: U5 e U1 (passo 8 existente).
